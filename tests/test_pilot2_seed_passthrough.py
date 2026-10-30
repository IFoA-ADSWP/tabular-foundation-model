"""The seed survives the trip from the launcher to the runner (#263).

`run_pilot.py` has always accepted `--seeds`, but nothing in the paid-run path ever
forwarded it -- so a two-seed replication (Stage 1 of the funded design) could not be
launched at all, and a single-seed run was the only thing the money could buy.

The change is plumbing, so the tests are plumbing: they assert the two places the value
can be lost, and they assert it END TO END rather than by grepping the scripts -- a grep
would keep passing if the line stayed in the file but moved out of the payload that
actually ships to the box.

  1. The generated onstart payload EXPORTS `SEEDS` (what the box receives at boot).
  2. `bootstrap_pilot.sh` forwards it to `scripts/run_pilot.py`, and forwards nothing
     when it is unset -- so today's invocation is unchanged for today's runs.

Neither test provisions anything: test 1 drives the real `vast_run.sh` against
`mock_vastai.sh` in a throwaway repo (no real token, no network, no instance); test 2
runs the real `bootstrap_pilot.sh` against a stubbed box whose whole "GPU", "clone" and
"python3" are three four-line scripts.

Run:  python -m pytest tests/test_pilot2_seed_passthrough.py -v
"""

import shutil
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GH = REPO_ROOT / "scripts" / "gpu_helpers"
VAST_RUN = GH / "vast_run.sh"
BOOTSTRAP = GH / "bootstrap_pilot.sh"
MOCK = GH / "mock_vastai.sh"


# --------------------------------------------------------------------------
# 1. The onstart payload -- what the box is actually told to run
# --------------------------------------------------------------------------
def _launcher_repo(tmp_path):
    """A scratch repo holding a copy of the launcher, so nothing here can spend.

    `vast_run.sh` derives REPO_DIR from its own location and refuses to run unless its
    HEAD is an ancestor of `origin/<branch>` (the commit guard). Copying the helper
    scripts into a throwaway repo with that ref pointing at its own single commit makes
    the guard satisfied by construction instead of by whatever branch this test suite
    happens to be running on -- and keeps the real repo's token and history out of it.
    """
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    shutil.copytree(GH, repo / "scripts" / "gpu_helpers")
    # keys.sh owns reading the secrets. Replace it with a stub so this test needs no
    # ~/.config/tfm/keys.env, makes no auth call, and cannot leak a live token into a
    # payload that the mock then writes to disk.
    (repo / "scripts" / "gpu_helpers" / "keys.sh").write_text(
        "#!/bin/bash\n"
        'case "${1:-}" in\n'
        '  get) echo "pk_stub_not_a_real_token" ;;\n'
        '  licence) echo "licence accepted (stub)" ;;\n'
        "esac\n"
    )
    git = ["git", "-C", str(repo)]
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(
        git
        + [
            "-c", "user.email=test@example.com",
            "-c", "user.name=test",
            "-c", "commit.gpgsign=false",
            "commit", "-q", "--allow-empty", "-m", "scratch repo for the launcher",
        ],
        check=True,
    )
    subprocess.run(git + ["update-ref", "refs/remotes/origin/main", "HEAD"], check=True)
    return repo


def _payload_after_launch(tmp_path, *launcher_args):
    """Run the real launcher against the mock and return the onstart payload it built."""
    repo = _launcher_repo(tmp_path)
    # The directory name contains "mock" on purpose: vast_run.sh records DRY_RUN=1 from
    # the resolved CLI's path, so a mock-driven run is labelled as one in its own record.
    bindir = tmp_path / "bin-mock"
    bindir.mkdir()
    (bindir / "vastai").write_text(MOCK.read_text())
    (bindir / "vastai").chmod(0o755)

    state = tmp_path / "state"
    state.mkdir()
    tree = tmp_path / "box-tree"
    tree.mkdir()

    env = {
        **os.environ,
        "PATH": f"{bindir}:{os.environ['PATH']}",
        "HOME": str(tmp_path / "home"),
        # Pinned, not inherited: the scratch repo's only ref is origin/main, so a caller
        # auditing another branch (BRANCH=... in the environment) must not change which
        # ref the commit guard checks here.
        "BRANCH": "main",
        "MOCK_STATE_DIR": str(state),
        "MOCK_STATUS": "running",
        "MOCK_OUTPUT_TREE": str(tree),
        "MOCK_EMITTER": str(GH / "emit_artifacts.sh"),
        "VAST_OUTDIR": str(tmp_path / "returned"),
        "TMPDIR": str(tmp_path / "tmp"),
    }
    # The stub keys.sh owns the token here; an exported one would only add a warning.
    env.pop("TABPFN_TOKEN", None)
    (tmp_path / "tmp").mkdir()
    (tmp_path / "home").mkdir()

    result = subprocess.run(
        [
            "bash",
            str(repo / "scripts" / "gpu_helpers" / "vast_run.sh"),
            "--offer-id", "99001122",
            "--yes",
            "--max-attempts", "1",
            *launcher_args,
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(repo),
    )

    # The payload is written by `create instance` and deleted by the launcher's cleanup
    # trap on every exit path, so the mock's copy is the only surviving evidence.
    assert (state / "created.txt").exists(), (
        f"the launcher never reached create:\n{result.stdout}\n{result.stderr}"
    )
    payload = state / "onstart.sh"
    assert payload.exists(), (
        f"the mock did not capture the onstart payload:\n{result.stdout}\n{result.stderr}"
    )
    return payload.read_text()


def _payload_export(payload, name):
    """Read one variable back the way the box's shell will, not as the text spells it.

    `printf %q` shell-quotes for re-parsing, but it does not escape commas: `printf '%q' "43,44"`
    emits `43,44` unchanged. Asserting on the text would test printf's spelling rather than the
    value the box ends up with; evaluating only the `export` lines (the rest of the payload starts
    the bootstrap, which is what the mock replaces) tests the environment the bootstrap actually
    inherits.
    """
    exports = "\n".join(
        line for line in payload.splitlines() if line.startswith("export ")
    )
    result = subprocess.run(
        ["bash", "-c", f'{exports}\nprintf "%s" "${{{name}-<unset>}}"'],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def test_onstart_payload_exports_the_seeds(tmp_path):
    """A comma-separated list arrives intact -- not truncated to the first value.

    Truncation is the specific failure worth guarding against: `--seeds 42,43` split on
    whitespace looks identical to a one-seed run, and the replication would silently be
    a single seed that cost the same money.
    """
    payload = _payload_after_launch(tmp_path, "--arms", "A_raw", "--seeds", "42,43")

    assert "export SEEDS=" in payload, payload
    assert _payload_export(payload, "SEEDS") == "42,43", payload
    # The box is told it is a double, which is why the mock directory is named "mock".
    assert _payload_export(payload, "TFM_DRY_RUN") == "1", payload
    # Nothing live reaches the record: the mock redacts the token it captured.
    assert "TABPFN_TOKEN=REDACTED" in payload, payload


def test_an_explicitly_empty_seed_list_is_refused(tmp_path):
    """`--seeds ""` is a mistake, not a request for the default.

    Before the guard it fell through every `${SEEDS:+...}` expansion and ran one seed at the
    runner's default -- the exact silent single-seed run this flag exists to prevent. The guard
    runs before any provider call, so this test needs no mock and cannot spend.
    """
    repo = _launcher_repo(tmp_path)
    result = subprocess.run(
        ["bash", str(repo / "scripts" / "gpu_helpers" / "vast_run.sh"), "--seeds", "", "--yes"],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(repo),
    )
    combined = result.stdout + result.stderr
    assert result.returncode == 2, combined
    assert "empty value" in combined, combined


def test_onstart_payload_omits_seeds_when_unset(tmp_path):
    """Unset means absent, not empty: the runner's own DEFAULT_SEED still owns it.

    An `export SEEDS=` line would be a launcher-side default by another name, and the
    record would then claim a seed the runner never chose.
    """
    payload = _payload_after_launch(tmp_path, "--arms", "A_raw")

    assert "export SEEDS=" not in payload, payload
    assert _payload_export(payload, "SEEDS") == "<unset>", payload


# --------------------------------------------------------------------------
# 2. The bootstrap -- what the runner is actually invoked with
# --------------------------------------------------------------------------
STUB_NVIDIA_SMI = "#!/bin/bash\necho 'NVIDIA RTX A6000, 49140 MiB, 550.54'\n"

# Every python3 call is a no-op, but the runner's argv is recorded. `$*` is the argv
# after the shell has split it, which is exactly what the runner receives.
STUB_PYTHON3 = (
    "#!/bin/bash\n"
    'for a in "$@"; do\n'
    '  case "$a" in\n'
    '    *run_pilot.py*) printf "%s\\n" "$*" >> "$TFM_TEST_ARGV" ;;\n'
    "  esac\n"
    "done\n"
    "exit 0\n"
)

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


def _runner_invocations(tmp_path, seeds):
    """Run the real bootstrap on a stubbed box; return every run_pilot.py argv."""
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    for name, body in (
        ("nvidia-smi", STUB_NVIDIA_SMI),
        ("python3", STUB_PYTHON3),
        ("git", STUB_GIT),
    ):
        (stubs / name).write_text(body)
        (stubs / name).chmod(0o755)

    # The "remote": a clone the fake git copies into WORKDIR. It needs only the files the
    # bootstrap runs by path, so `emit_artifacts.sh` and `fetch_weights.py` are stubs too.
    tree = tmp_path / "remote"
    (tree / "scripts" / "gpu_helpers").mkdir(parents=True)
    (tree / "scripts" / "run_pilot.py").write_text("# stub: the stub python3 records argv\n")
    (tree / "scripts" / "gpu_helpers" / "fetch_weights.py").write_text("# stub\n")
    (tree / "scripts" / "gpu_helpers" / "emit_artifacts.sh").write_text(
        "#!/bin/bash\necho '__ARTIFACTS_INFO__ bytes=0 sha256=- lines=0 files=0'\n"
    )

    record = tmp_path / "runner-argv.txt"
    record.write_text("")
    env = {
        "PATH": f"{stubs}:/usr/bin:/bin:/usr/sbin:/sbin",
        "HOME": str(tmp_path / "home"),
        "TABPFN_TOKEN": "pk_stub_not_a_real_token",
        "WORKDIR": str(tmp_path / "workspace" / "tfm"),
        "ARMS": "A_raw,B_in_domain",
        "TFM_TEST_TREE": str(tree),
        "TFM_TEST_ARGV": str(record),
    }
    if seeds is not None:
        env["SEEDS"] = seeds
    (tmp_path / "home").mkdir()

    result = subprocess.run(
        ["bash", str(BOOTSTRAP)],
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(tmp_path),
    )
    assert "BOOTSTRAP FINISHED" in result.stdout, (
        f"the bootstrap did not run to completion:\n{result.stdout}\n{result.stderr}"
    )
    return [line for line in record.read_text().splitlines() if "--arms" in line]


def test_bootstrap_forwards_the_seeds_to_the_runner(tmp_path):
    """One forwarded list, applied per arm -- the runner expands it into seeds x folds."""
    lines = _runner_invocations(tmp_path, seeds="42,43")

    assert len(lines) == 2, lines  # one per arm: A_raw, B_in_domain
    for line in lines:
        assert "--seeds 42,43" in line, line
        # The list is a single argument, not two: `--seeds 42 43` would make 43 the
        # positional argument and drop the second seed without complaint.
        assert line.count("42") == 1 and line.count("43") == 1, line


def test_bootstrap_invokes_the_runner_exactly_as_before_when_seeds_are_unset(tmp_path):
    """The unchanged path: adding the flag must not alter today's invocation."""
    lines = _runner_invocations(tmp_path, seeds=None)

    assert len(lines) == 2, lines
    for line in lines:
        assert "--seeds" not in line, line
