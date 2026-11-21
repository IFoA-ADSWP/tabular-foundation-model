"""A kept instance re-emits its captures without re-fitting (#568).

`severity_french` was fitted, sealed, and then lost: the launcher died before it could pull, and
every later poll read a window that had scrolled past the payload's header, so the capture could
not be ordered or hash-verified. The box was kept, because the fits are the expensive half -- but
keeping it bought nothing, there was no way to ask it again.

There is no exec channel (`vastai execute` runs only ls/rm/du; SSH keys are refused by the team
context). The instance LIFECYCLE is one, and it was measured on 2026-11-21: a restart re-runs the
launch's onstart against the same disk. These tests drive the real launcher and the real driver
against `mock_vastai.sh`, so nothing is provisioned and nothing is spent.

  1. A refused launch leaves its instance; `--fairtest reemit` restores the same captures from it
     without creating an instance or fitting anything.
  2. The re-emit refuses BEFORE rebooting when the box's log has no EMIT marker, naming what it
     looked for.
  3. The bootstrap's sealed-capture fast path emits and does NOT fit or reach the GPU check.
  4. A partial seal re-fits only the missing target.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from tests.test_pilot2_seed_passthrough import _launch, _payload_after_launch

GH = Path(__file__).resolve().parents[1] / "scripts" / "gpu_helpers"
BOOTSTRAP = GH / "bootstrap_pilot.sh"


def _target_tree(tmp_path, count=4):
    """`count` sealed v4 captures, laid out as the box leaves them under results/."""
    from tests.test_chunked_capture_transport import _slot

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from run_capture import build_capture, render_capture

    tree = tmp_path / "captures"
    ids = [f"20261112T09000{index}Z" for index in range(count)]
    for run_id in ids:
        run = tree / run_id
        run.mkdir(parents=True)
        _slot(run, 0)
        (run / "capture.json").write_text(render_capture(build_capture(run)))
    return tree, ids


def test_reemit_restores_the_captures_without_creating_or_fitting(tmp_path):
    """The whole point: the same four captures, from the box that already fitted them."""
    tree, ids = _target_tree(tmp_path)

    state, result = _launch(
        tmp_path,
        "--fairtest", "reemit",
        "--instance", "55500011",
        "--poll-minutes", "1",
        extra_env={
            "MOCK_OUTPUT_TREE": str(tree),
            "MOCK_PER_TARGET": "1",
            "MOCK_EMIT_MARKERS": "1",
            "TFM_CHUNK_LINES": "3",
            "TFM_CHUNK_PAUSE": "0",
            "TFM_CHUNK_REPEAT": "1",
            "TFM_CHUNK_PASSES": "1",
            "REEMIT_POLL_SECONDS": "0",
        },
    )
    combined = result.stdout + result.stderr

    assert result.returncode == 0, combined
    results = tmp_path / "repo" / "results"
    assert sorted(path.name for path in results.iterdir()) == sorted(ids), combined
    for run_id in ids:
        assert (results / run_id / "capture.json").is_file(), combined

    # The recovery used the lifecycle, not a new box: one reboot, no create, and it released it.
    assert (state / "reboot_attempts").read_text().strip() == "1", combined
    assert not (state / "created.txt").exists(), "re-emit created an instance"
    assert (state / "destroyed.txt").read_text().strip() == "55500011", combined
    assert "Rebooting instance 55500011." in combined, combined


def test_reemit_refuses_before_rebooting_when_the_box_sealed_nothing(tmp_path):
    """Refusing is free and names both things it looked for; the alternative is a paid re-fit."""
    tree, _ = _target_tree(tmp_path)

    state, result = _launch(
        tmp_path,
        "--fairtest", "reemit",
        "--instance", "55500011",
        "--poll-minutes", "1",
        extra_env={"MOCK_OUTPUT_TREE": str(tree), "MOCK_PER_TARGET": "1"},
    )
    combined = result.stdout + result.stderr

    assert result.returncode == 2, combined
    assert "REFUSING" in combined, combined
    assert "results/*/capture.json" in combined, combined
    assert "EMIT" in combined, combined
    assert not (state / "reboot_attempts").exists(), "the box was rebooted before the refusal"
    assert not (state / "destroyed.txt").exists(), "the refusal destroyed the instance"


def test_reemit_requires_an_instance_and_yes(tmp_path):
    """`--fairtest reemit` without `--instance` is a mistake, not a request for a new box."""
    state, result = _launch(tmp_path, "--fairtest", "reemit", "--poll-minutes", "1")
    combined = result.stdout + result.stderr

    assert result.returncode == 2, combined
    assert "--instance" in combined, combined
    assert not (state / "created.txt").exists()
    assert not (state / "reboot_attempts").exists()


def test_the_onstart_payload_keeps_its_headroom_under_the_api_ceiling(tmp_path):
    """The inlined bootstrap is gzipped into a field the API caps at 16,384 bytes (#3471).

    The launcher refuses above 16,000. #568's first cut took the payload to 16,568 -- over the cap,
    so EVERY launch would have failed at create with nothing local to blame. A recovery path is not
    worth a launch that cannot start, so the headroom is a test, not a comment.
    """
    payload = _payload_after_launch(
        tmp_path, "--fairtest", "primary", "--poll-minutes", "180"
    ).encode()

    assert len(payload) < 16000, (
        f"the onstart payload is {len(payload)} bytes; the launcher refuses above 16,000 and the "
        "API above 16,384. Move code out of bootstrap_pilot.sh rather than trimming it."
    )


# --------------------------------------------------------------------------
# The box side: the bootstrap's sealed-capture fast path
# --------------------------------------------------------------------------
STUB_NVIDIA_SMI = "#!/bin/bash\necho 'NVIDIA RTX A6000, 49140 MiB, 550.54'\n"

# Every python3 call is a no-op EXCEPT the run-id arithmetic, which the target loop needs in
# order to recognise an already-sealed directory. `-c` scripts are all either that arithmetic or
# a paid-work probe the stub is meant to pass without doing anything.
STUB_PYTHON3 = (
    "#!/bin/bash\n"
    'if [ "${1:-}" = "-c" ]; then\n'
    '  case "${2:-}" in\n'
    '    *datetime*) exec __PYTHON__ "$@" ;;\n'
    '    *) exit 0 ;;\n'
    "  esac\n"
    "fi\n"
    'for a in "$@"; do\n'
    '  case "$a" in\n'
    '    *run_fair_test.py*) printf "%s\\n" "$*" >> "$TFM_TEST_ARGV" ;;\n'
    "  esac\n"
    "done\n"
    "exit 0\n"
).replace("__PYTHON__", sys.executable)

# Only `git clone --branch <b> <url> <dir>` matters: the "remote" is a fixture tree.
STUB_GIT = (
    "#!/bin/bash\n"
    'if [ "${1:-}" = "clone" ]; then\n'
    '  for last; do :; done\n'
    '  mkdir -p "$last"\n'
    '  cp -R "$TFM_TEST_TREE"/. "$last"/\n'
    "fi\n"
    "exit 0\n"
)

STUB_EMITTER = "#!/bin/bash\necho \"__ARTIFACTS_INFO__ bytes=0 sha256=- lines=0 files=0\"\necho EMITTED \"$1\"\n"


def _stub_box(tmp_path, sealed_count):
    """A fake box whose clone already holds `sealed_count` sealed captures."""
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    for name, body in (
        ("nvidia-smi", STUB_NVIDIA_SMI),
        ("python3", STUB_PYTHON3),
        ("git", STUB_GIT),
    ):
        (stubs / name).write_text(body)
        (stubs / name).chmod(0o755)

    tree = tmp_path / "remote"
    (tree / "scripts" / "gpu_helpers").mkdir(parents=True)
    (tree / "scripts" / "run_fair_test.py").write_text("# stub\n")
    (tree / "scripts" / "gpu_helpers" / "fetch_weights.py").write_text("# stub\n")
    (tree / "scripts" / "gpu_helpers" / "emit_artifacts.sh").write_text(STUB_EMITTER)
    # The real on-box re-emit logic: a copy, so the test exercises the file the box would run.
    (tree / "scripts" / "gpu_helpers" / "reemit_on_box.sh").write_text(
        (GH / "reemit_on_box.sh").read_text()
    )
    for index in range(sealed_count):
        run = tree / "results" / f"20261112T09000{index}Z"
        run.mkdir(parents=True)
        (run / "capture.json").write_text("{}")

    record = tmp_path / "fit-argv.txt"
    record.write_text("")
    return stubs, tree, record


def _run_bootstrap(tmp_path, sealed_count):
    stubs, tree, record = _stub_box(tmp_path, sealed_count)
    env = {
        "PATH": f"{stubs}:/usr/bin:/bin:/usr/sbin:/sbin",
        "HOME": str(tmp_path / "home"),
        "TABPFN_TOKEN": "pk_stub_not_a_real_token",
        "WORKDIR": str(tmp_path / "workspace" / "tfm"),
        "FAIRTEST": "primary",
        "TFM_RUN_STAMP": "20261112T090000Z",
        "TFM_TEST_TREE": str(tree),
        "TFM_TEST_ARGV": str(record),
        "TFM_CHUNK_LINES": "0",
    }
    (tmp_path / "home").mkdir()
    result = subprocess.run(
        ["bash", str(BOOTSTRAP)],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(tmp_path),
    )
    return result, record


def test_a_fully_sealed_box_reemits_and_never_fits(tmp_path):
    """The recovery is the emit path alone: no GPU check, no deps, no runner invocation."""
    result, record = _run_bootstrap(tmp_path, sealed_count=4)
    combined = result.stdout + result.stderr

    assert result.returncode == 0, combined
    assert "REEMIT: 4 sealed capture(s)" in combined, combined
    assert combined.count("########## EMIT ") == 4, combined
    # The paid half is what must be skipped: no dependency install, no weights, no fit.
    assert "--- installing deps" not in combined, "the fast path reached the paid work"
    assert "PREFLIGHT" not in combined, "the fast path reached the paid work"
    assert "########## FAIRTEST primary" not in combined, combined
    assert record.read_text() == "", f"a fit was invoked on a sealed box: {record.read_text()}"


def test_a_partial_seal_declines_and_falls_through_to_the_normal_path(tmp_path):
    """A partly-sealed box is NOT re-emitted: the on-box check declines, loudly.

    Re-emitting a subset would hand the launcher fewer captures than it expects, and the verify
    would refuse them anyway. The fallback is a normal boot, which fits the launch again -- costly,
    so the PARTIAL line says so rather than leaving it to be inferred from a bill.
    """
    result, record = _run_bootstrap(tmp_path, sealed_count=3)
    combined = result.stdout + result.stderr

    assert "PARTIAL: 3 of 4 capture(s) sealed" in combined, combined
    # The normal path ran: one fit invocation per target. The sealed captures are still sent (the
    # loop emits any target whose capture exists), but they were fitted again -- which is why a
    # partial seal is a costly fallback rather than a recovery.
    assert len(record.read_text().splitlines()) == 4, record.read_text()
    assert combined.count("########## EMIT ") == 3, combined


def test_reemit_stops_when_the_box_starts_fitting_again(tmp_path):
    """An old box (or a partly-sealed one) takes the normal path. Do not wait out a paid re-fit.

    The reboot is what triggers the fit, so the driver cannot prevent it -- but it must notice, say
    so, keep the box, and stop. Polling for thirty minutes would look like a slow transfer while the
    instance billed through a second full launch.
    """
    tree, _ = _target_tree(tmp_path)

    state, result = _launch(
        tmp_path,
        "--fairtest", "reemit",
        "--instance", "55500011",
        "--poll-minutes", "1",
        extra_env={
            "MOCK_OUTPUT_TREE": str(tree),
            "MOCK_PER_TARGET": "1",
            "MOCK_EMIT_MARKERS": "1",
            "MOCK_FITTING": "1",
            "REEMIT_POLL_SECONDS": "0",
        },
    )
    combined = result.stdout + result.stderr

    assert result.returncode == 1, combined
    assert "started its dependency install" in combined or "PARTLY sealed" in combined, combined
    assert "KEPT" in combined, combined
    assert not (state / "destroyed.txt").exists(), "the refusal destroyed the box"


def _run_on_box(tmp_path, sealed_count):
    """Run the on-box script exactly as the bootstrap does: cwd is the clone."""
    box = tmp_path / "box"
    (box / "scripts" / "gpu_helpers").mkdir(parents=True)
    (box / "scripts" / "gpu_helpers" / "emit_artifacts.sh").write_text(STUB_EMITTER)
    for index in range(sealed_count):
        run = box / "results" / f"20261112T09000{index}Z"
        run.mkdir(parents=True)
        (run / "capture.json").write_text("{}")
    env = {**os.environ, "TFM_CHUNK_LINES": "0"}
    return subprocess.run(
        ["bash", str(GH / "reemit_on_box.sh")],
        env=env,
        cwd=str(box),
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_the_on_box_check_emits_every_sealed_capture(tmp_path):
    result = _run_on_box(tmp_path, sealed_count=4)
    combined = result.stdout + result.stderr

    assert result.returncode == 0, combined
    assert combined.count("########## EMIT ") == 4, combined
    assert combined.count("EMITTED ") == 4, combined


def test_the_on_box_check_declines_an_empty_or_partial_box(tmp_path):
    """Exit 1 is the contract the bootstrap branches on: 'do not skip the fit'."""
    empty = _run_on_box(tmp_path / "empty", sealed_count=0)
    assert empty.returncode == 1, empty.stdout + empty.stderr
    assert "EMIT" not in empty.stdout, empty.stdout

    partial = _run_on_box(tmp_path / "partial", sealed_count=3)
    assert partial.returncode == 1, partial.stdout + partial.stderr
    assert "PARTIAL: 3 of 4" in partial.stdout, partial.stdout
    assert "########## EMIT " not in partial.stdout, partial.stdout
