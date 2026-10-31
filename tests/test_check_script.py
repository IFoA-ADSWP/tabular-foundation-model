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
import shutil
import stat
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check.sh"

# Enough of a PATH to find git, which the script uses to locate the repo root,
# without finding the real check tools.
MINIMAL_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"


def run(args, path=None, cwd=None, extra_env=None):
    env = dict(os.environ)
    # `all` includes the evidence check. Defaulting its base to HEAD keeps these tests
    # independent of whichever refs the ambient checkout happens to have, and clearing the
    # override keeps them independent of the caller's environment -- otherwise a gate run with
    # EVIDENCE_CHANGE_OK=1 makes the tests that assert refusal silently pass instead.
    env.setdefault("EVIDENCE_BASE", "HEAD")
    env.pop("EVIDENCE_CHANGE_OK", None)
    if path is not None:
        env["PATH"] = path
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [str(SCRIPT), *args], capture_output=True, text=True, env=env, cwd=cwd
    )


def shim(bin_dir: Path, name: str, exit_code: int, body: str = "") -> None:
    """Put an executable named `name` on a directory we control."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    path = bin_dir / name
    path.write_text(f"#!/bin/sh\n{body}\nexit {exit_code}\n")
    path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def toolchain(tmp_path: Path) -> Path:
    """A PATH containing git (the script needs it to find the repo root) and nothing else.

    Symlinking git rather than borrowing MINIMAL_PATH makes "the check tools are
    absent" true on every machine, including one with ruff in /usr/bin.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    # bash and basename are the script's own dependencies; git locates the repo root.
    for name in ("bash", "basename", "git"):
        found = shutil.which(name)
        assert found, f"{name} is required to test the script"
        os.symlink(found, bin_dir / name)
    return bin_dir


# ---- the script itself -----------------------------------------------------


def test_script_exists_and_is_executable():
    assert SCRIPT.is_file(), f"missing {SCRIPT}"
    assert os.access(SCRIPT, os.X_OK), "check.sh is not executable"


def test_unknown_check_is_a_usage_error(tmp_path):
    result = run(["not-a-check"], path=str(toolchain(tmp_path)))
    assert result.returncode == 2
    assert "usage:" in result.stderr


# ---- dispatch: a failing tool must fail the check ---------------------------


def test_failing_ruff_fails_the_check(tmp_path):
    shim(tmp_path, "ruff", 1)
    result = run(["ruff"], path=f"{tmp_path}:{MINIMAL_PATH}")
    assert result.returncode == 1, result.stdout + result.stderr


def test_failing_pytest_fails_the_check(tmp_path):
    shim(tmp_path, "pytest", 1)
    result = run(["pytest"], path=f"{tmp_path}:{MINIMAL_PATH}")
    assert result.returncode == 1, result.stdout + result.stderr


def test_failing_doclinks_fails_the_check(tmp_path):
    shim(tmp_path, "python3", 1)
    result = run(["doclinks"], path=f"{tmp_path}:{MINIMAL_PATH}")
    assert result.returncode == 1, result.stdout + result.stderr


def test_failing_docstatus_fails_the_check(tmp_path):
    shim(tmp_path, "python3", 1)
    result = run(["docstatus"], path=f"{tmp_path}:{MINIMAL_PATH}")
    assert result.returncode == 1, result.stdout + result.stderr


def test_failing_shellcheck_fails_the_check(tmp_path):
    shim(tmp_path, "shellcheck", 1)
    result = run(["shellcheck"], path=f"{tmp_path}:{MINIMAL_PATH}")
    assert result.returncode == 1, result.stdout + result.stderr


# ---- honest absence: a missing tool is never a silent pass -----------------


def test_missing_tool_is_named_and_not_a_pass(tmp_path):
    result = run(["ruff"], path=str(toolchain(tmp_path)))
    assert result.returncode == 3
    assert "ruff" in result.stderr
    assert "not installed" in result.stderr


# ---- all: every check runs, and any failure decides the result --------------


def test_all_passes_when_every_check_passes(tmp_path):
    for name in ("ruff", "pytest", "shellcheck", "python3"):
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


def test_all_runs_every_check_when_a_tool_is_missing(tmp_path):
    """A missing ruff must not hide pytest and shellcheck behind it."""
    bin_dir = toolchain(tmp_path)
    shim(bin_dir, "pytest", 0, body='echo "pytest ran"')
    shim(bin_dir, "shellcheck", 0, body='echo "shellcheck ran"')
    result = run([], path=str(bin_dir))
    assert result.returncode == 3, result.stdout + result.stderr
    assert "pytest ran" in result.stdout
    assert "shellcheck ran" in result.stdout
    assert "ruff" in result.stderr and "not installed" in result.stderr


def test_all_reports_failure_ahead_of_a_missing_tool(tmp_path):
    """A real failure is more useful than the absence of another tool."""
    bin_dir = toolchain(tmp_path)
    shim(bin_dir, "pytest", 1)
    shim(bin_dir, "shellcheck", 0)
    result = run([], path=str(bin_dir))
    assert result.returncode == 1, result.stdout + result.stderr


# ---- evidence: the committed-evidence guard (#317 retro) --------------------


def evidence_repo(tmp_path):
    """A throwaway repo with an `origin/main` ref and one file under outputs/."""
    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*args):
        return subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
        )

    git("init", "-q", "-b", "main")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "test")
    (repo / "outputs").mkdir()
    (repo / "outputs" / "meta.json").write_text("{}\n")
    git("add", "-A")
    git("commit", "-q", "-m", "base")
    git("update-ref", "refs/remotes/origin/main", "HEAD")
    git("checkout", "-q", "-b", "feature")
    return repo, git


def test_evidence_passes_on_a_clean_branch(tmp_path):
    repo, _ = evidence_repo(tmp_path)
    result = run(
        ["evidence"],
        path=str(toolchain(tmp_path)),
        cwd=repo,
        extra_env={"EVIDENCE_BASE": "origin/main"},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "unchanged" in result.stdout


def test_evidence_fails_when_a_commit_changes_evidence(tmp_path):
    repo, git = evidence_repo(tmp_path)
    (repo / "outputs" / "meta.json").write_text('{"changed": true}\n')
    git("add", "-A")
    git("commit", "-q", "-m", "change evidence")

    result = run(
        ["evidence"], path=str(toolchain(tmp_path)), cwd=repo,
        extra_env={"EVIDENCE_BASE": "origin/main"},
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "meta.json" in result.stderr


def test_evidence_sees_a_staged_change_that_is_not_committed(tmp_path):
    """A commit-range diff is blind to a staged deletion -- which is how one reached a commit."""
    repo, git = evidence_repo(tmp_path)
    git("rm", "-q", "outputs/meta.json")

    result = run(
        ["evidence"], path=str(toolchain(tmp_path)), cwd=repo,
        extra_env={"EVIDENCE_BASE": "origin/main"},
    )
    assert result.returncode == 1, result.stdout + result.stderr


def test_evidence_allows_a_deliberate_change_when_named(tmp_path):
    repo, git = evidence_repo(tmp_path)
    (repo / "outputs" / "meta.json").write_text('{"changed": true}\n')
    git("add", "-A")
    git("commit", "-q", "-m", "change evidence")

    result = run(
        ["evidence"], path=str(toolchain(tmp_path)), cwd=repo,
        extra_env={"EVIDENCE_BASE": "origin/main", "EVIDENCE_CHANGE_OK": "1"},
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_evidence_reports_a_missing_base_as_a_failure(tmp_path):
    repo, _ = evidence_repo(tmp_path)
    result = run(
        ["evidence"], path=str(toolchain(tmp_path)), cwd=repo,
        extra_env={"EVIDENCE_BASE": "no-such-ref"},
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "no-such-ref" in result.stderr
