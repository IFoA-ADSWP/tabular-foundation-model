"""PR-8 acceptance test: a full mock run of the runner's own path, at $0.

Covers create -> onstart -> poll -> artifact return -> destroy against
`mock_vastai.sh`, with the New payload (per-arm predictions + manifest) and the hash
verification. R1 spent roughly half its budget on failures a zero-cost mock run would
have caught, so this is the gate before any paid run.

Three properties are asserted, because each has failed before:

  1. The run COMPLETES and tears down -- `destroy instance -y` is recorded by the mock.
     A mock that only prints cannot prove the trap ran.
  2. The artifacts come back AND verify: every arm's predictions match the hash its
     meta.json recorded, checked by the real `verify_artifacts.py`.
  3. The mock cannot drift from reality: its `logs` branch calls the REAL
     `emit_artifacts.sh` rather than emitting a private format. An earlier mock
     invented markers the verifier did not look for, and thereby validated a wire
     format that no longer existed.

Run:  python -m pytest tests/test_pilot2_mock_run.py -v
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from tests import run_artifact_guard

REPO_ROOT = Path(__file__).resolve().parents[1]
GH = REPO_ROOT / "scripts" / "gpu_helpers"
VAST_RUN = GH / "vast_run.sh"
MOCK = GH / "mock_vastai.sh"
EMITTER = GH / "emit_artifacts.sh"
VERIFIER = GH / "verify_artifacts.py"

# An offer the runner's allow-list accepts (RTX 4090, enough VRAM, under max dph).
# Note the fixture must NOT be a Tesla V100: `--pick value` excludes Volta/sm_70.
OFFERS = [
    {
        "id": 99001122,
        "gpu_name": "RTX 4090",
        "dph_total": 0.44,
        "gpu_ram": 49140,
        "cpu_ram": 128000,
        "disk_space": 200.0,
        "reliability": 0.9979,
        "dlperf": 42.0,
        "cuda_max_good": 13.0,
        "machine_id": 555001,
        "host_id": 777001,
        "inet_down": 900.0,
        "inet_up": 850.0,
    }
]


def _sha(arr):
    import hashlib

    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()


def build_box_output_tree(root: Path, run_id="20260912T230000Z"):
    """Mimic what the box leaves in outputs/finetune/pilot before emitting."""
    rng = np.random.default_rng(21)
    for run_path in ("coil2000/A_raw", "coil2000/B_in_domain", "uslapseagent/A_raw"):
        d = root / run_path
        d.mkdir(parents=True, exist_ok=True)
        y_prob = rng.random(1000)
        np.save(d / "predictions.npy", y_prob)
        np.save(d / "ground_truth.npy", (rng.random(1000) < 0.3).astype(np.int64))
        (d / "meta.json").write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "run_id": run_path.replace("/", "_") + "_seed42",
                    "predictions_sha256": _sha(y_prob),
                    "inference_context": {"rows": 2000, "mechanism": "test fixture"},
                }
            )
        )
    (root / "pilot_metrics.parquet").write_bytes(
        rng.integers(0, 256, size=20_000, dtype=np.uint8).tobytes()
    )
    # The runner writes a manifest per invocation; the mock must prove it returns.
    manifest = {
        "schema_version": 2,
        "run_id": run_id,
        "status": "success",
        "config": {"epochs": 3, "learning_rate": 1e-05, "n_estimators": 2},
        "dataset_fingerprints": {"coil2000": {"sha256": "a" * 64}},
    }
    (root / f"manifest_{run_id}.json").write_text(json.dumps(manifest))
    return run_id


REMOTE_BRANCH = "main"


def _run_launcher(env, *args):
    """Run the real launcher through the mock, returning (completed process, output)."""
    result = subprocess.run(
        ["bash", str(VAST_RUN), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(REPO_ROOT),
    )
    return result, result.stdout + result.stderr


def _commit_on_remote_main() -> str:
    """A commit the box could actually check out, so the launcher's guard can pass.

    The guard asks whether the commit it would send is an ancestor of `origin/$BRANCH`.
    In a test run that is usually false -- pre-push the local branch is ahead, and PR CI
    checks out a merge ref -- so it refuses before provisioning (#256). Inject the real
    answer rather than weakening the guard: fail loudly if the remote branch is
    unavailable, because a silent fallback to HEAD would restore the bug invisibly.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--verify",
             f"origin/{REMOTE_BRANCH}^{{commit}}"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        pytest.fail(
            f"cannot resolve origin/{REMOTE_BRANCH}, so the commit guard cannot be "
            f"satisfied: {exc}"
        )
    return proc.stdout.strip()


def _local_head() -> str:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _commit_nowhere_near_the_remote() -> str:
    """A real commit object that no remote branch contains.

    Not a fabricated sha: `merge-base --is-ancestor` returns 128 for a bad object and 1 for
    "real commit, not an ancestor", so a fake sha would pass the refusal test without
    exercising the case it names.
    """
    tree = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "write-tree"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    # A runner has no user.name/user.email, and commit-tree refuses without one. Pass an
    # explicit identity rather than depending on the machine's git config.
    proc = subprocess.run(
        ["git", "-C", str(REPO_ROOT),
         "-c", "user.name=gate test", "-c", "user.email=gate@example.invalid",
         "commit-tree", tree, "-m", "unreachable test commit"],
        capture_output=True, text=True, check=True,
    )
    return proc.stdout.strip()


@pytest.fixture
def mock_env(tmp_path):
    """A self-contained mock environment: mock CLI, offers, state dir, output tree."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    target = bindir / "vastai"
    shutil.copy(MOCK, target)
    target.chmod(0o755)

    offers = tmp_path / "offers.json"
    offers.write_text(json.dumps(OFFERS))

    state = tmp_path / "state"
    state.mkdir()
    tree = state / "finetune" / "pilot"
    tree.mkdir(parents=True)
    run_id = build_box_output_tree(tree)

    outdir = tmp_path / "returned"
    # A token FILE, not an exported token: the runner prefers the file and warns when an
    # exported value differs from it. Written here so the test is hermetic -- it used to
    # depend on the developer's real ~/.config/tfm/keys.env, which CI does not have, so
    # the suite was green locally and red on every pull request.
    keys = tmp_path / "keys.env"
    keys.write_text("TABPFN_TOKEN=dummy-token-for-a-mock-run\n")
    env = {
        **os.environ,
        "PATH": f"{bindir}:{os.environ['PATH']}",
        "TABPFN_FILE": str(keys),
        # The mock provisions no GPU, so there is no rental for the licence gate to
        # protect -- and that gate makes a live API call, which a hermetic test cannot.
        "SKIP_LICENSE_CHECK": "1",
        "MOCK_STATUS": "running",
        "MOCK_OFFERS": str(offers),
        "MOCK_STATE_DIR": str(state),
        "MOCK_OUTPUT_TREE": str(tree),
        "MOCK_EMITTER": str(EMITTER),
        "VAST_OUTDIR": str(outdir),
        "MOCK_SEQ_FILE": str(state / "seq"),
        # The launcher refuses to provision when HEAD is not an ancestor of origin/$BRANCH
        # (#256). On a feature branch -- and in PR CI, where the checkout is a merge ref --
        # it legitimately is not, so the guard would stop the mock before it ran. Answer
        # its question truthfully with a commit the box could check out; do not weaken it.
        "TFM_COMMIT_SHA": _commit_on_remote_main(),
        # Pin the branch the guard consults, so an ambient BRANCH in the caller's shell
        # cannot make the injected commit and the compared ref disagree.
        "BRANCH": REMOTE_BRANCH,
    }
    # Deliberately NOT exporting TABPFN_TOKEN: the runner prefers the file named by
    # TABPFN_FILE and warns when an exported value differs from it. The mock needs no
    # token, and the runner's env-vs-file guard is exercised separately.
    env.pop("TABPFN_TOKEN", None)
    return {"env": env, "state": state, "tree": tree, "outdir": outdir, "run_id": run_id}


def test_mock_run_completes_verifies_and_tears_down(mock_env):
    """The whole path, once: provision -> emit -> return -> verify -> destroy.

    It also covers where the saved container log lands (#280) — the log directory is the
    one path that used to escape VAST_OUTDIR.
    """
    env, state, outdir = mock_env["env"], mock_env["state"], mock_env["outdir"]
    # Fingerprinted, not listed by name: a same-named rewrite inside the real log directory
    # must fail too, and an absent directory must not pass as "unchanged".
    repo_logs = REPO_ROOT / "outputs" / "gpu-pilot" / "logs"
    repo_logs_before = run_artifact_guard.run_artifacts((repo_logs,))

    result, combined = _run_launcher(
        env, "--yes", "--arms", "A_raw,B_in_domain", "--max-attempts", "1"
    )

    # 0. The remote-commit guard ran and was satisfied with the commit we injected (#256),
    #    and it named that commit rather than some other one. Without this, a future
    #    weakening of the guard would go unnoticed.
    injected = env["TFM_COMMIT_SHA"]
    assert f"commit {injected} is on origin/{REMOTE_BRANCH}" in combined, combined

    # 1. The instance was created and -- critically -- destroyed.
    assert (state / "created.txt").exists(), f"no create recorded:\n{combined}"
    assert (state / "destroyed.txt").exists(), f"TEARDOWN DID NOT FIRE:\n{combined}"
    destroyed = (state / "destroyed.txt").read_text().split()
    assert destroyed, "destroy recorded an empty instance id"

    # 2. The artifacts came back and verify against their recorded hashes.
    rc = subprocess.run(
        [sys.executable, str(VERIFIER), "--verify-only", "--raw", "/dev/null", "--dest", str(outdir)],
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0, f"{rc.stdout}\n{rc.stderr}"
    assert "verified=3" in rc.stdout, rc.stdout
    assert "mismatched=0" in rc.stdout and "missing=0" in rc.stdout

    # 3. The manifest returned too -- PR-1 depends on it.
    #    Since #184 artifacts land under runs/<id>/ rather than directly in $OUTDIR, so this
    #    searches recursively instead of pinning the flat layout. Asserting the run_id keeps it
    #    specific: the point is that the manifest the BOX wrote came back, not that some JSON did.
    manifests = sorted(outdir.rglob("manifest_*.json"))
    assert len(manifests) == 1, f"expected one returned manifest, found {manifests}:\n{combined}"
    returned = json.loads(manifests[0].read_text())
    assert returned["run_id"] == mock_env["run_id"], (
        f"wrong manifest returned: {returned.get('run_id')!r} != {mock_env['run_id']!r}"
    )

    # 4. The container log is saved beside the launch's other records, not in the real log
    #    directory (#280). `outputs/gpu-pilot/logs/**` is kept on purpose, so a mock writing
    #    there would leave a fake box log a reader could not tell from a paid one.
    saved = sorted((outdir / "logs").glob("*.log"))
    assert len(saved) == 1, f"expected one log beside the launch's records:\n{combined}"
    assert run_artifact_guard.run_artifacts((repo_logs,)) == repo_logs_before, (
        "the mock launch wrote into the real outputs/gpu-pilot/logs"
    )


def test_a_real_launch_still_logs_beside_the_paid_run_records():
    """AC2 (#280): with no VAST_OUTDIR, the log belongs in outputs/gpu-pilot/logs.

    Nothing is launched. A mock with VAST_OUTDIR unset would write into the tree this fix
    exists to keep clean, and a dry run has no instance so it saves no log at all. So this
    evaluates the launcher's own default lines in a subshell: the answer comes from the
    file, so re-pointing the default fails here instead of silently moving real logs.
    """
    source = VAST_RUN.read_text()
    outdir_line = re.search(r"^OUTDIR=.*$", source, re.MULTILINE).group(0)
    log_line = re.search(r"^\s*LOG_DIR=.*$", source, re.MULTILINE).group(0).strip()

    def resolved_log_dir(**overrides):
        env = {k: v for k, v in os.environ.items() if k != "VAST_OUTDIR"}
        env["P_REPO"] = str(REPO_ROOT)
        env.update(overrides)
        probe = "\n".join([
            'REPO_DIR="$P_REPO"  # the launcher derives this from its own location',
            outdir_line,
            log_line,
            'printf %s "$LOG_DIR"',
        ])
        result = subprocess.run(["bash", "-c", probe], env=env, capture_output=True,
                                text=True, check=True)
        return Path(result.stdout)

    assert resolved_log_dir() == REPO_ROOT / "outputs" / "gpu-pilot" / "logs"
    # ...and the override still wins, which is the half the mock run proves behaviourally.
    assert resolved_log_dir(VAST_OUTDIR=str(REPO_ROOT / "tmp-out")) == REPO_ROOT / "tmp-out" / "logs"


def test_mock_run_reports_the_artifact_verification(mock_env):
    """The runner must surface the verification result, not just restore silently."""
    result = subprocess.run(
        ["bash", str(VAST_RUN), "--yes", "--arms", "A_raw", "--max-attempts", "1"],
        env=mock_env["env"],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(REPO_ROOT),
    )
    combined = result.stdout + result.stderr
    assert "VERIFY predictions verified=" in combined, combined[-2000:]
    # No warning of a short read, a bad checksum, or failed verification.
    assert "TRUNCATED" not in combined, combined[-2000:]
    assert "MISMATCH" not in combined, combined[-2000:]


def test_mock_refuses_to_run_when_not_the_resolved_cli(tmp_path):
    """The interlock: a dry run that silently calls the real CLI is worse than none.

    Getting this wrong once created three real instances that stayed billing.
    """
    real = tmp_path / "vastai"
    shutil.copy(MOCK, real)
    real.chmod(0o755)
    # Invoke it while a DIFFERENT path resolves as `vastai`.
    otherdir = tmp_path / "other"
    otherdir.mkdir()
    (otherdir / "vastai").write_text("#!/bin/sh\necho real\n")
    (otherdir / "vastai").chmod(0o755)
    env = {**os.environ, "PATH": f"{otherdir}:{os.environ['PATH']}"}
    r = subprocess.run(
        ["bash", str(real), "show", "instances"], env=env, capture_output=True, text=True
    )
    assert r.returncode == 99
    assert "REFUSING" in r.stderr


def test_mock_models_the_execute_constraint(mock_env):
    """`vastai execute` accepts only ls/rm/du -- the mock must not accept a shell."""
    env = mock_env["env"]
    bad = subprocess.run(
        ["vastai", "execute", "1", "echo hello"], env=env, capture_output=True, text=True
    )
    assert "Invalid command given" in bad.stdout
    good = subprocess.run(
        ["vastai", "execute", "1", "ls"], env=env, capture_output=True, text=True
    )
    assert "Invalid command given" not in good.stdout


def test_guard_still_refuses_a_commit_that_is_not_on_the_remote(mock_env):
    """The override answers the guard's question; it does not bypass it (#256).

    A real commit that no remote branch contains must be refused exactly as before, so the
    safety that stopped a $0.0039 mistake still holds for every real run.
    """
    unreachable = _commit_nowhere_near_the_remote()
    env = {**mock_env["env"], "TFM_COMMIT_SHA": unreachable}

    result, combined = _run_launcher(
        env, "--yes", "--arms", "A_raw", "--max-attempts", "1"
    )

    assert result.returncode == 2, combined
    assert unreachable in combined, combined
    assert "REFUSING" in combined, combined
    assert not (mock_env["state"] / "created.txt").exists(), "guard let a create through"


def test_guard_resolves_head_when_the_override_is_absent(mock_env):
    """Unset, the launcher resolves HEAD and says so (#256, AC1).

    Whether HEAD is on the remote decides only which branch this takes -- refusal or the
    mock run -- and both name the resolved commit.
    """
    env = {k: v for k, v in mock_env["env"].items() if k != "TFM_COMMIT_SHA"}
    head = _local_head()

    result, combined = _run_launcher(
        env, "--yes", "--arms", "A_raw", "--max-attempts", "1"
    )

    assert result.returncode in (0, 2), combined
    assert head in combined, f"launcher did not resolve HEAD ({head}):\n{combined}"


# --- the lease (#325): one record, three outcomes, no stranded instance -------


def _lease(mock_env):
    leases = sorted((mock_env["outdir"] / "leases").glob("*/lease.json"))
    assert leases, f"no lease record written under {mock_env['outdir']}/leases"
    return json.loads(leases[0].read_text())


def _launch(mock_env, *extra, env=None):
    return _run_launcher(
        env or mock_env["env"], "--yes", "--arms", "A_raw", "--max-attempts", "1", *extra
    )


def test_a_normal_exit_records_released_and_destroys_once(mock_env):
    result, combined = _launch(mock_env)
    assert result.returncode == 0, combined

    lease = _lease(mock_env)
    assert lease["state"] == "released"
    assert lease["outcome"] == "released"
    assert lease["instance_id"] == (mock_env["state"] / "created.txt").read_text().split()[0]
    # The launch id is the provider label, and it is in the record rather than only in a log.
    assert lease["label"] == "tfm-" + lease["launch_id"], "the leak check matches the tfm- prefix"
    assert (mock_env["state"] / "destroyed.txt").read_text().split() == [lease["instance_id"]]
    assert len((mock_env["state"] / "destroy_attempts.txt").read_text().split()) == 1


def test_a_failed_destroy_keeps_the_id_and_exits_nonzero(mock_env):
    """The bug this exists for: a swallowed destroy left an instance billing, unfindable."""
    env = {**mock_env["env"], "MOCK_DESTROY_FAIL_TIMES": "2"}
    result, combined = _launch(mock_env, env=env)

    assert result.returncode != 0, combined
    lease = _lease(mock_env)
    assert lease["state"] == "failed"
    assert lease["outcome"] == "failed"
    assert lease["instance_id"], "the id was cleared, so nothing could destroy it"
    assert "STILL BILLING" in combined
    assert lease["instance_id"] in combined and lease["launch_id"] in combined
    assert not (mock_env["state"] / "destroyed.txt").exists(), "a failed destroy was recorded as success"


def test_a_teardown_retries_once_and_succeeds(mock_env):
    """One blip at teardown must not strand a machine; the second attempt is the point."""
    env = {**mock_env["env"], "MOCK_DESTROY_FAIL_TIMES": "1"}
    result, combined = _launch(mock_env, env=env)

    assert result.returncode == 0, combined
    lease = _lease(mock_env)
    assert lease["state"] == "released"
    attempts = (mock_env["state"] / "destroy_attempts.txt").read_text().split()
    assert len(attempts) == 2, f"expected one retry, saw {attempts}"


def test_a_launch_that_never_created_records_aborted(mock_env):
    """A spend-gate refusal must not look like a torn-down run."""
    env = {**mock_env["env"], "MAX_DPH": "0.01"}  # below the fixture offer: refusal before create
    result, combined = _launch(mock_env, "--max-dph", "0.01", env=env)

    assert result.returncode != 0, combined
    lease = _lease(mock_env)
    assert lease["state"] == "aborted"
    assert lease["outcome"] == "no_instance"
