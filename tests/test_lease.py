"""The paid-run lease: record before create, one destroy, an honest outcome (#325)."""

from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEASE = ROOT / "scripts/gpu_helpers" / "lease.sh"

MOCK = """#!/bin/sh
case "$1 $2" in
  "destroy instance")
      n=$(cat "$MOCK_STATE_DIR/attempts" 2>/dev/null || echo 0)
      n=$((n + 1))
      printf '%s\\n' "$n" > "$MOCK_STATE_DIR/attempts"
      if [ -n "${GONE:-}" ]; then
          echo "No such container: $3" >&2
          exit 1
      fi
      if [ -n "${FAIL_ONCE:-}" ] && [ "$n" -eq 1 ]; then
          echo "mock: destroy failed once" >&2
          exit 1
      fi
      printf '%s\\n' "$3" >> "$MOCK_STATE_DIR/destroyed.txt"
      exit 0
      ;;
esac
exit 0
"""


def _mock(tmp_path: Path) -> tuple[Path, Path, dict[str, str]]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    tool = bin_dir / "vastai"
    tool.write_text(MOCK)
    tool.chmod(tool.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    state = tmp_path / "state"
    state.mkdir()
    out = tmp_path / "out"
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["MOCK_STATE_DIR"] = str(state)
    return out, state, env


def _run(body: str, env: dict[str, str]) -> subprocess.CompletedProcess:
    script = f"set -uo pipefail\nsource '{LEASE}'\n{body}"
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=env)


def _record(out: Path) -> dict:
    files = list((out / "leases").glob("*.json"))
    assert len(files) == 1, files
    return json.loads(files[0].read_text())


def test_a_normal_release_writes_the_record_then_destroys_once(tmp_path):
    out, state, env = _mock(tmp_path)

    result = _run(f'''
lease_begin "{out}" "img:tag"
echo "begin=$(lease_state)"
lease_acquired 12345678
echo "acquired=$(lease_state)"
lease_release
lease_release
echo "end=$(lease_state)"
''', env)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "begin=acquiring" in result.stdout
    assert "acquired=acquired" in result.stdout
    assert "end=released" in result.stdout
    assert (state / "destroyed.txt").read_text().split() == ["12345678"]

    record = _record(out)
    assert record["state"] == "released"
    assert record["outcome"] == "released"
    assert record["instance_id"] == "12345678"
    assert record["label"].startswith("tabpfn-pilot-")
    assert record["launch_id"] in record["label"]


def test_a_failed_release_keeps_the_id_then_a_second_attempt_succeeds(tmp_path):
    out, state, env = _mock(tmp_path)
    env["FAIL_ONCE"] = "1"

    result = _run(f'''
lease_begin "{out}" "img:tag"
lease_acquired 42
if lease_release; then echo "unexpected-success"; fi
echo "first=$(lease_state)"
lease_release
echo "second=$(lease_state)"
''', env)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "unexpected-success" not in result.stdout
    assert "first=failed" in result.stdout
    assert "second=released" in result.stdout
    assert "vastai destroy instance 42 -y" in result.stderr
    assert (state / "destroyed.txt").read_text().split() == ["42"]

    record = _record(out)
    assert record["state"] == "released"
    assert record["instance_id"] == "42"
    assert (state / "attempts").read_text().strip() == "2"


def test_keep_records_that_the_instance_is_still_billing(tmp_path):
    out, _state, env = _mock(tmp_path)

    result = _run(f'''
lease_begin "{out}" "img:tag"
lease_acquired 7
lease_keep
lease_state
''', env)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip().endswith("acquired")
    record = _record(out)
    assert record["state"] == "acquired"
    assert record["outcome"] == "kept"


def test_an_already_gone_instance_is_not_reported_as_billing(tmp_path):
    out, _state, env = _mock(tmp_path)
    env["GONE"] = "1"

    result = _run(f'''
lease_begin "{out}" "img:tag"
lease_acquired 99
lease_release
lease_state
''', env)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "already_gone" in result.stdout
    assert "STILL BILLING" not in result.stderr
    record = _record(out)
    assert record["state"] == "released"
    assert record["outcome"] == "already_gone"


# --- #326: a retry is a new attempt under ONE launch ------------------------------


def test_a_retry_across_processes_reuses_the_launch_id(tmp_path):
    """The seam that matters: a second PROCESS, with the id carried in the environment.

    The first version of this test faked the exec in one shell and passed while production was
    broken -- sourcing lease.sh reset the id. Crossing the process boundary is the whole test.
    """
    out, _state, env = _mock(tmp_path)
    id_file = tmp_path / "launch_id"

    first = _run(
        f'lease_begin "{out}" "img" && lease_acquired 1111 && lease_release "attempt one" >/dev/null '
        f'&& printf "%s" "$LEASE_LAUNCH_ID" > "{id_file}"',
        env,
    )
    assert first.returncode == 0, first.stdout + first.stderr
    launch_id = id_file.read_text()
    assert launch_id

    second_env = {**env, "LEASE_LAUNCH_ID": launch_id, "ATTEMPT": "2"}
    second = _run(
        f'lease_begin "{out}" "img" && [ "$LEASE_LAUNCH_ID" = "{launch_id}" ] '
        f'&& lease_acquired 2222 && lease_release "attempt two" >/dev/null',
        second_env,
    )
    assert second.returncode == 0, second.stdout + second.stderr

    record = _record(out)
    assert record["launch_id"] == launch_id
    assert sorted(record["attempts"]) == ["1", "2"]
    assert record["attempts"]["1"]["instance_id"] == "1111"
    assert record["attempts"]["2"]["instance_id"] == "2222"
    assert len(list((out / "leases").glob("*.json"))) == 1


def test_an_inherited_id_with_no_record_is_refused(tmp_path):
    """A stray export must not graft a new launch onto another launch's file."""
    out, _state, env = _mock(tmp_path)
    result = _run(
        f'lease_begin "{out}" "img"',
        {**env, "LEASE_LAUNCH_ID": "not-a-launch"},
    )
    assert result.returncode != 0
    assert "REFUSING inherited launch id" in result.stderr
    assert not list((out / "leases").glob("*.json"))
