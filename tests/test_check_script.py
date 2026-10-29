"""The gate's own tests (issue #257).

The contract under test is the script's dispatch and its exit codes, not the
individual tools. CI calls this script with a check name, so what has to hold is:
a failing check propagates a failure, a missing tool is named rather than skipped,
and an unknown name is a usage error.

Tools are shimmed on PATH. That keeps these tests offline, fast, and independent
of which of ruff/pytest/shellcheck happen to be installed where they run — and it
lets the failure path be tested deliberately, which is the part that matters: a
test that only ever asserts success cannot tell a working gate from an inert one.
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check.sh"

# Enough of a PATH to find git, which the script uses to locate the repo root,
# without finding the real check tools.
MINIMAL_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"


def run(args, path=None):
    env = dict(os.environ)
    if path is not None:
        env["PATH"] = path
    return subprocess.run(
        [str(SCRIPT), *args], capture_output=True, text=True, env=env
    )


def shim(bin_dir: Path, name: str, exit_code: int, body: str = "") -> None:
    """Put an executable named `name` on a directory we control."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    path = bin_dir / name
    path.write_text(f"#!/bin/sh\n{body}\nexit {exit_code}\n")
    path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


# ---- the script itself -----------------------------------------------------


def test_script_exists_and_is_executable():
    assert SCRIPT.is_file(), f"missing {SCRIPT}"
    assert os.access(SCRIPT, os.X_OK), "check.sh is not executable"


def test_unknown_check_is_a_usage_error():
    result = run(["not-a-check"], path=MINIMAL_PATH)
    assert result.returncode == 2
    assert "usage:" in result.stderr


# ---- duration: a failing tool must fail the check ---------------------------


def test_failing_ruff_fails_the_check(tmp_path):
    shim(tmp_path, "ruff", 1)
    result = run(["ruff"], path=f"{tmp_path}:{MINIMAL_PATH}")
    assert result.returncode == 1, result.stdout + result.stderr


def test_failing_pytest_fails_the_check(tmp_path):
    shim(tmp_path, "pytest", 1)
    result = run(["pytest"], path=f"{tmp_path}:{MINIMAL_PATH}")
    assert result.returncode == 1, result.stdout + result.stderr


def test_failing_shellcheck_fails_the_check(tmp_path):
    shim(tmp_path, "shellcheck", 1)
    result = run(["shellcheck"], path=f"{tmp_path}:{MINIMAL_PATH}")
    assert result.returncode == 1, result.stdout + result.stderr


# ---- honest absence: a missing tool is never a silent pass -----------------


def test_missing_tool_is_named_and_not_a_pass(tmp_path):
    result = run(["ruff"], path=MINIMAL_PATH)
    if result.returncode == 0:
        # The real ruff is on this machine's minimal PATH; skip rather than
        # assert something untrue about the environment.
        import pytest

        pytest.skip("ruff is installed on the minimal PATH")
    assert result.returncode == 3
    assert "ruff" in result.stderr
    assert "not installed" in result.stderr


# ---- all: every check runs, and any failure decides the result --------------


def test_all_passes_when_every_check_passes(tmp_path):
    for name in ("ruff", "pytest", "shellcheck"):
        shim(tmp_path, name, 0)
    result = run([], path=f"{tmp_path}:{MINIMAL_PATH}")
    assert result.returncode == 0, result.stdout + result.stderr


def test_all_fails_when_one_check_fails(tmp_path):
    shim(tmp_path, "ruff", 0)
    shim(tmp_path, "pytest", 0)
    shim(tmp_path, "shellcheck", 1)
    result = run([], path=f"{tmp_path}:{MINIMAL_PATH}")
    assert result.returncode == 1, result.stdout + result.stderr


def test_all_runs_every_check_even_after_a_failure(tmp_path):
    """A red ruff must not hide a broken shell script."""
    shim(tmp_path, "ruff", 1)
    shim(tmp_path, "pytest", 0)
    shim(tmp_path, "shellcheck", 0, body='echo "shellcheck ran"')
    result = run([], path=f"{tmp_path}:{MINIMAL_PATH}")
    assert result.returncode == 1
    assert "shellcheck ran" in result.stdout
