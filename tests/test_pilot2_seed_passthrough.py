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
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GH = REPO_ROOT / "scripts" / "gpu_helpers"
VAST_RUN = GH / "vast_run.sh"
BOOTSTRAP = GH / "bootstrap_pilot.sh"
PILOT = REPO_ROOT / "scripts" / "run_pilot.py"
MOCK = GH / "mock_vastai.sh"
VERIFIER = GH / "verify_artifacts.py"


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


def _launch(tmp_path, *launcher_args, extra_env=None):
    """Run the real launcher against the mock; return (state dir, completed process).

    Nothing is provisioned: `vastai` here is the mock, so a run either refuses for free or
    writes its onstart payload into the mock's state directory.
    """
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
    env.update(extra_env or {})
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

    return state, result


def _payload_after_launch(tmp_path, *launcher_args):
    """Run the real launcher against the mock and return the onstart payload it built."""
    state, result = _launch(tmp_path, *launcher_args)
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


# --------------------------------------------------------------------------
# 3. A batch that cannot finish inside the poll window is refused (#414)
# --------------------------------------------------------------------------
def test_a_batch_that_cannot_finish_is_refused_before_provisioning(tmp_path):
    """The failure this prevents is not lateness -- it is total loss.

    Past the poll the launcher exits non-zero, the EXIT trap destroys the instance, and the
    box ships its payload only on completion, so the compute is discarded. Measured once:
    thirty seeds took 46 min against a 40 min ceiling, $0.2051 and 46 minutes for nothing.
    """
    seeds = ",".join(str(seed) for seed in range(93, 123))  # 30 seeds
    state, result = _launch(tmp_path, "--seeds", seeds)

    assert result.returncode == 2, result.stdout + result.stderr
    assert "cannot finish inside the poll window" in result.stderr
    assert "30 seed(s)" in result.stderr          # the arithmetic is shown, not implied
    assert "--poll-minutes" in result.stderr      # and the way out is named
    # Nothing was rented: the refusal happens before an offer is even picked.
    assert not (state / "created.txt").exists()


def test_raising_the_poll_window_lets_the_same_batch_through(tmp_path):
    """A refusal must be answerable. The operator raises the window, and the batch proceeds."""
    seeds = ",".join(str(seed) for seed in range(93, 123))
    # 30 seeds x 170s + 900s startup = 6000s = 100 min, so the window must clear that.
    state, result = _launch(tmp_path, "--seeds", seeds, "--poll-minutes", "120")

    assert "cannot finish inside the poll window" not in result.stderr
    assert (state / "created.txt").exists(), result.stdout + result.stderr


def test_the_estimate_can_be_lowered_for_a_faster_rung(tmp_path):
    """The estimate is a property of the batch, so a cheaper rung can fit what the default refuses.

    Twelve seeds at the 170 s default plus a 900 s startup is 2940 s -- over the 2400 s window --
    so the same twelve seeds are refused by default and admitted at 60 s/seed. That is the pair the
    flag exists for: the refusal is answerable in both directions.
    """
    seeds = ",".join(str(seed) for seed in range(93, 105))  # 12 seeds

    refused_state, refused = _launch(tmp_path / "refused", "--seeds", seeds)
    assert refused.returncode == 2, refused.stdout + refused.stderr
    assert not (refused_state / "created.txt").exists()

    state, result = _launch(
        tmp_path / "admitted", "--seeds", seeds, "--estimate-sec-per-seed", "60"
    )
    assert "cannot finish inside the poll window" not in result.stderr
    assert (state / "created.txt").exists(), result.stdout + result.stderr


# --------------------------------------------------------------------------
# 4. A batch proves the seeds it wrote (#429)
# --------------------------------------------------------------------------
def _box_tree(root, seeds, dataset="eudirectlapse", arm="A_raw"):
    """A returned tree the verifier accepts, whose metas record `seeds`.

    Every seed gets its own predictions/meta pair with a hash the verifier can recompute,
    so the only thing the seed check has to object to is the seed set itself. That keeps
    the test honest: it cannot pass because the hashes failed first.
    """
    import hashlib
    import json

    import numpy as np

    for seed in seeds:
        d = root / dataset / arm / f"seed{seed}_foldNone"
        d.mkdir(parents=True)
        y = np.linspace(0.0, 1.0, 16, dtype=np.float32) + seed
        np.save(d / "predictions.npy", y)
        np.save(d / "ground_truth.npy", (y > 0.5).astype(np.int64))
        (d / "meta.json").write_text(
            json.dumps(
                {
                    "schema_version": 4,
                    "run_id": f"{dataset}_{arm}_seed{seed}",
                    "dataset": dataset,
                    "arm": arm,
                    "seed": seed,
                    "fold": None,
                    "predictions_sha256": hashlib.sha256(
                        np.ascontiguousarray(y).tobytes()
                    ).hexdigest(),
                }
            )
        )
    return root


def _requested(*seeds):
    return ",".join(str(seed) for seed in seeds)


def test_a_batch_that_wrote_another_launchs_seeds_is_refused(tmp_path):
    """Measured 2026-11-05: two launches asked for one range and wrote another's.

    `waveC-3` asked 225-236 and `waveC-4` asked 237-248; both wrote 141-152, and both
    reported `verified=24 mismatched=0`. Every existing check passed. The count was right,
    the hashes were right, the range was wrong -- so the only way to catch it is to compare
    the seed set against the launch's request.
    """
    tree = _box_tree(tmp_path / "wrong-tree", seeds=range(141, 153))
    requested = _requested(*range(225, 237))

    _, result = _launch(
        tmp_path,
        "--arms", "A_raw",
        "--seeds", requested,
        "--poll-minutes", "60",
        extra_env={"MOCK_OUTPUT_TREE": str(tree)},
    )
    combined = result.stdout + result.stderr

    assert result.returncode != 0, combined
    assert "requested=225-236" in combined, combined
    assert "written=141-152" in combined, combined
    assert "REFUSING" in result.stderr, combined
    # The pull happened first, so the wrong tree is on disk for inspection rather than
    # destroyed with the instance.
    returned = list((tmp_path / "returned").rglob("meta.json"))
    assert len(returned) == 12, returned


def test_a_correct_batch_passes_unchanged(tmp_path):
    """The new check must not cost a good batch its exit code.

    A guard that refuses everything is indistinguishable from a broken pipeline, so the
    healthy path is pinned beside the refusal: same tree, requested seeds, exit 0.
    """
    tree = _box_tree(tmp_path / "right-tree", seeds=[141, 142, 143])
    _, result = _launch(
        tmp_path,
        "--arms", "A_raw",
        "--seeds", _requested(141, 142, 143),
        extra_env={"MOCK_OUTPUT_TREE": str(tree)},
    )
    combined = result.stdout + result.stderr

    assert result.returncode == 0, combined
    assert "SEEDS requested=141-143 written=141-143" in combined, combined


def test_a_partial_batch_is_refused_not_silently_accepted(tmp_path):
    """Fewer seeds than requested is the same failure as the wrong range, one shape on.

    A stopped batch that wrote 2 of 3 seeds used to pass every check: the two records were
    consistent, and the count was never compared with the request.
    """
    tree = _box_tree(tmp_path / "partial-tree", seeds=[141, 142])
    _, result = _launch(
        tmp_path,
        "--arms", "A_raw",
        "--seeds", _requested(141, 142, 143),
        extra_env={"MOCK_OUTPUT_TREE": str(tree)},
    )
    combined = result.stdout + result.stderr

    assert result.returncode != 0, combined
    assert "requested=141-143 written=141-142" in combined, combined
    assert "MISSING seeds: 143" in combined, combined


def test_the_verifier_renders_a_sparse_seed_set_as_ranges(tmp_path):
    """Twelve numbers a reader has to diff by eye is how 141-152 went unnoticed."""
    tree = _box_tree(tmp_path / "sparse-tree", seeds=[141, 143, 150, 151, 152])
    result = subprocess.run(
        [sys.executable, str(VERIFIER), "--verify-only", "--raw", "/dev/null",
         "--dest", str(tree), "--expect-seeds", "141,143,150-152"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "requested=141,143,150-152 written=141,143,150-152" in result.stdout


def test_a_tree_that_records_no_seeds_is_a_mismatch_not_a_pass(tmp_path):
    """Absence is not agreement: an older meta schema must not read as "requested satisfied"."""
    import json

    tree = _box_tree(tmp_path / "unseeded-tree", seeds=[141])
    meta_path = next(tree.rglob("meta.json"))
    meta = json.loads(meta_path.read_text())
    del meta["seed"]
    meta_path.write_text(json.dumps(meta))

    result = subprocess.run(
        [sys.executable, str(VERIFIER), "--verify-only", "--raw", "/dev/null",
         "--dest", str(tree), "--expect-seeds", "141"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 6, result.stdout + result.stderr
    assert "written=(none)" in result.stdout
    assert "MISSING seeds: 141" in result.stdout


def test_an_arm_that_missed_a_seed_is_refused(tmp_path):
    """The union can be right while an arm is short: B_at seed 142 of 141-143.

    That is the same failure the issue records one level up -- a batch that looks complete
    and is not -- so the group compared is `(dataset, arm)`, not the whole tree.
    """
    tree = tmp_path / "arm-tree"
    _box_tree(tree, seeds=[141, 142, 143], arm="A_raw")
    _box_tree(tree, seeds=[141, 142], arm="B_in_domain")

    result = subprocess.run(
        [sys.executable, str(VERIFIER), "--verify-only", "--raw", "/dev/null",
         "--dest", str(tree), "--expect-seeds", "141-143"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 6, result.stdout + result.stderr
    assert "INCOMPLETE eudirectlapse/B_in_domain" in result.stdout
    assert "missing 143" in result.stdout


def test_a_seed_recorded_as_a_string_is_still_that_seed(tmp_path):
    """A schema variant writing "141" must not read as "no seed written"."""
    import json

    tree = _box_tree(tmp_path / "string-seed-tree", seeds=[141])
    meta_path = next(tree.rglob("meta.json"))
    meta = json.loads(meta_path.read_text())
    meta["seed"] = "141"
    meta_path.write_text(json.dumps(meta))

    result = subprocess.run(
        [sys.executable, str(VERIFIER), "--verify-only", "--raw", "/dev/null",
         "--dest", str(tree), "--expect-seeds", "141"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "written=141" in result.stdout


def test_an_unusable_seed_list_is_a_usage_error_not_a_skipped_check(tmp_path):
    """`--expect-seeds ""` must not quietly mean "don't check".

    That is the failure `vast_run.sh` already refuses for `--seeds ""` (#429's guard), and
    a reversed range would otherwise expand to nothing and blame every written seed.
    """
    tree = _box_tree(tmp_path / "usage-tree", seeds=[141])
    for spec in ("", "236-225", "141,abc"):
        result = subprocess.run(
            [sys.executable, str(VERIFIER), "--verify-only", "--raw", "/dev/null",
             "--dest", str(tree), "--expect-seeds", spec],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 2, f"{spec!r}: {result.stdout}{result.stderr}"
        assert "not a seed list" in result.stdout, result.stdout


def test_a_batch_whose_hashes_do_not_match_is_refused_too(tmp_path):
    """Exit 5 was a warning while exit 6 is a refusal; both mean "do not trust this set"."""
    import json

    tree = _box_tree(tmp_path / "bad-hash-tree", seeds=[141])
    meta_path = next(tree.rglob("meta.json"))
    meta = json.loads(meta_path.read_text())
    meta["predictions_sha256"] = "0" * 64
    meta_path.write_text(json.dumps(meta))

    _, result = _launch(
        tmp_path,
        "--arms", "A_raw",
        "--seeds", "141",
        extra_env={"MOCK_OUTPUT_TREE": str(tree)},
    )
    combined = result.stdout + result.stderr

    assert result.returncode != 0, combined
    assert "REFUSING: predictions arrived but failed hash verification" in result.stderr


def test_the_ssh_transport_is_verified_too():
    """Both transports have to answer "is this the batch I asked for".

    The ssh path pulls files directly and has nothing to unpack, so it was the one place
    where no verification ran at all -- not even the hash check that predates #429.
    """
    script = VAST_RUN.read_text()
    pull = script.split("=== pulling artifacts ===", 1)[1]
    ssh_branch = pull.split('if [ "$TRANSPORT" = "ssh" ]; then', 1)[1].split(
        "\nelse", 1
    )[0]

    assert "--verify-only" in ssh_branch, ssh_branch
    assert '--raw /dev/null' in ssh_branch, ssh_branch
    # ...and the call itself is shared, after the branch, so the seed list reaches it.
    assert '"${SEED_ARGS[@]+"${SEED_ARGS[@]}"}"' in script


# --------------------------------------------------------------------------
# 5. A launch owns its temp files (#426)
# --------------------------------------------------------------------------
def test_the_launcher_shares_no_temp_file_between_launches():
    """The container log IS the artifact transfer channel, so a shared path is a data bug.

    Measured 2026-11-05: two of three concurrent batches wrote another batch's seeds and still
    reported `verified=24`, because both launchers read/wrote /tmp/vast_run_out.txt. A launch that
    names its own directory cannot do that.
    """
    script = VAST_RUN.read_text()

    assert "/tmp/vast_" not in script, (
        "a fixed /tmp/vast_* path is shared by every concurrent launcher; "
        "route it through $LAUNCH_TMP instead (#426)"
    )
    assert 'LAUNCH_TMP="$(mktemp -d' in script
    assert 'RUN_OUT="$LAUNCH_TMP/run_out.txt"' in script


# ---------------------------------------------------------------------------
# Every path on the box forwards the seeds (#450)
# ---------------------------------------------------------------------------
def test_every_runner_invocation_forwards_the_launchs_seeds():
    """The seed subset must survive BOTH paths, not just the per-arm one.

    `bootstrap_pilot.sh` runs the runner two ways: one process per named arm, and one
    process letting the declaration name them. The second dropped `--seeds`, so a batch the
    launcher pre-flighted at three seeds ran the whole declared range -- ten of them, at four
    arms -- inside a poll window sized for three. Nothing failed; the run was simply eight
    times the compute it was authorised for.

    Asserted over the source because the alternative is provisioning a box to watch a number.
    """
    text = BOOTSTRAP.read_text()
    # Join backslash continuations, so a command split across lines is judged as one.
    joined = text.replace("\\\n", " ")
    invocations = [
        line for line in joined.splitlines()
        if "run_pilot.py" in line
        and not line.lstrip().startswith("#")
        # The aggregator reads finished records; it runs no arm and takes no seeds.
        and "--aggregate" not in line
    ]
    assert len(invocations) >= 2, invocations

    for line in invocations:
        assert '${SEEDS:+--seeds "$SEEDS"}' in line, (
            "a run_pilot.py invocation drops the launch's seeds: " + line.strip()
        )


# ---------------------------------------------------------------------------
# The environment seam (#450) -- the class, not the instances
# ---------------------------------------------------------------------------
# Variables the box computes for itself, or the launcher sets from its own arguments. Everything
# else the box READS must be forwarded when the operator sets it, or the box silently substitutes
# its default and the operator's setting is a belief rather than a fact.
_LAUNCHER_OWNED = {
    "TABPFN_TOKEN", "EXPERIMENT", "ARMS", "DATASET", "TRAIN_SIZE", "TEST_SIZE", "SEEDS",
    "TFM_DRY_RUN", "TFM_RUN_STAMP", "TFM_COMMIT_SHA", "BRANCH", "TFM_IMAGE_REF",
    "TFM_MACHINE_ID", "TFM_HOST_ID", "TFM_BOOTSTRAP_B64",
}
_BOX_COMPUTED = {
    "WORKDIR", "REPO", "MISSING", "PREFLIGHT_RC", "WEIGHTS_CACHED", "WEIGHTS_JSON",
    "WEIGHTS_OUT", "WEIGHTS_RC", "ARMS_OK", "ARMS_FAILED", "_BOOTSTRAP_DONE", "TMPDIR",
}
# Read by the box and deliberately overridden there: forwarding them would be a control that
# cannot move, which reads like a control. Each is listed with why, so removing the entry is a
# decision rather than a tidy-up.
_BOX_ENFORCED = {
    "TFM_REQUIRE_CLEAN_TREE",  # hard-exported to 1 by bootstrap_pilot.sh; the box always wants it
}


def _env_reads(path):
    """Every $VAR / ${VAR} a shell script reads."""
    import re

    text = path.read_text()
    return set(re.findall(r"\$\{?([A-Z_][A-Z0-9_]{2,})\}?", text))


def _python_env_reads(path):
    import re

    return set(re.findall(r'os\.environ(?:\.get)?\(?"([A-Z_][A-Z0-9_]{2,})"', path.read_text()))


def _launcher_forwards():
    """The names the launcher's pass-through loop covers."""
    import re

    text = VAST_RUN.read_text()
    block = text[text.index("for _passthrough in"):]
    block = block[: block.index("done")]
    return set(re.findall(r"\b(TFM_[A-Z0-9_]+|TABPFN_[A-Z0-9_]+|[A-Z][A-Z0-9_]*_PIN)\b", block))


def test_every_variable_the_box_reads_is_forwarded_or_launcher_owned():
    """One audit, so a new setting cannot be silently dropped at the seam.

    This is the class behind both defects shipped on 2026-11-06: `bootstrap_pilot.sh` accepted
    `--seeds` and dropped it, and a diagnostic's `main` accepted `--seed-range` and dropped it.
    Both ends were individually correct; only the seam was wrong, so nothing failed.

    `TFM_EXPECT_CHECKPOINT` was a third instance: the box defaults it to v3_default and the
    launcher never forwarded it, so an operator who set it was overridden without a word -- which
    is why D18's "asserted before every launch" was an assertion of the default.
    """
    reads = _env_reads(BOOTSTRAP) | _python_env_reads(PILOT)
    forwarded = _launcher_forwards()

    # Membership, not a name-prefix filter. The filter meant every allowlist entry whose name did
    # not start TFM_/TABPFN_ could never match -- a list that reads like a control and cannot fire.
    dropped = {
        name for name in reads
        if name not in forwarded
        and name not in _LAUNCHER_OWNED
        and name not in _BOX_COMPUTED
        and name not in _BOX_ENFORCED
    }
    assert not dropped, (
        "the box reads variables the launcher never forwards, so each falls back to a default "
        f"silently: {sorted(dropped)}"
    )


def test_the_passthrough_list_has_no_dead_entries():
    """A forwarded name the box never reads is a comment pretending to be a control."""
    reads = _env_reads(BOOTSTRAP) | _python_env_reads(PILOT)
    dead = {name for name in _launcher_forwards() if name not in reads}
    assert not dead, f"forwarded but never read by the box: {sorted(dead)}"
