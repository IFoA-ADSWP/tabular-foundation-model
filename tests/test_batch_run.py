"""The missing set is the queue (#430).

The 2026-11-05 campaign drove a fixed queue: batch 1..16 in order. A batch that died was
skipped and its range was never measured; a batch that wrote another range's seeds left the
range it *thought* it had covered missing. Neither was visible until someone diffed the run
directories against the design, and a quarter of the spend bought nothing.

`batch_run.sh` removes that failure mode rather than the symptom: it asks the run directories
what is banked and launches what is missing, so a dead or wrong batch is simply still missing
on the next pass.

The seams are the harness CLI and the launcher it drives. Nothing here talks to Vast: the
launcher is a recording double that writes the `meta.json` tree a real launch would bank, so a
"dead batch" is a double that exits non-zero and writes nothing -- which is exactly what a
killed launch looks like from here.

Run:  python -m pytest tests/test_batch_run.py -v
"""

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GH = REPO_ROOT / "scripts" / "gpu_helpers"
BATCH_RUN = GH / "batch_run.sh"
FIT_GUARD = GH / "fit_guard.sh"
BANKED = GH / "banked_seeds.py"

DATASET = "eudirectlapse"
ARMS = "A_raw,B_ft30"

# The double. It reads what the harness asked for and writes the tree a real launch would
# bank -- nothing else. Behaviour is driven by environment variables so one script covers
# "succeeds", "dies once", "dies always", "refuses for free" and "banks a partial range".
DOUBLE = r"""#!/bin/bash
set -uo pipefail
printf '%s\n' "$*" >> "${DOUBLE_LOG:?}"
seeds=""; dataset=""; arms=""; train_size=""; test_size=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --seeds) seeds="${2:-}"; shift 2 ;;
        --dataset) dataset="${2:-}"; shift 2 ;;
        --arms) arms="${2:-}"; shift 2 ;;
        --train-size) train_size="${2:-}"; shift 2 ;;
        --test-size) test_size="${2:-}"; shift 2 ;;
        *) shift ;;
    esac
done
mkdir -p "${DOUBLE_STATE:?}"

# A directory is an atomic lock: if a second launch is alive, this is how the test finds out.
if [ -n "${DOUBLE_LOCK:-}" ]; then
    if ! mkdir "$DOUBLE_LOCK" 2>/dev/null; then
        printf "OVERLAP\n" >> "$DOUBLE_LOG"
        exit 9
    fi
    trap 'rmdir "$DOUBLE_LOCK"' EXIT
fi

if [ "${DOUBLE_REFUSE:-0}" = "1" ]; then
    echo "REFUSING: stub launcher was told to refuse" >&2
    exit 2
fi
if [ "${DOUBLE_ALWAYS_FAIL:-0}" = "1" ]; then
    echo "stub launcher died" >&2
    exit 1
fi
if [ -n "${DOUBLE_FAIL_ONCE:-}" ] && [ "$seeds" = "$DOUBLE_FAIL_ONCE" ]; then
    if [ ! -f "$DOUBLE_STATE/failed_once" ]; then
        : > "$DOUBLE_STATE/failed_once"
        echo "stub launcher died (first time only)" >&2
        exit 1
    fi
fi

# A launch number, so two passes never overwrite each other's tree.
n=$(( $(cat "$DOUBLE_STATE/launches" 2>/dev/null || echo 0) + 1 ))
printf '%s\n' "$n" > "$DOUBLE_STATE/launches"

# The manifest the box writes into its own tree: `manifest_<run_id>.json` at the top.
mkdir -p "${VAST_OUTDIR:?}/runs/launch$n"
{
    printf '{"run_id": "launch%d", "dry_run": false' "$n"
    [ -n "$train_size" ] && printf ', "train_size": %s' "$train_size"
    [ -n "$test_size" ] && printf ', "test_size": %s' "$test_size"
    printf '}\n'
} > "${VAST_OUTDIR:?}/runs/launch$n/manifest_launch$n.json"

if [ "${DOUBLE_BANK_ONLY_FIRST:-0}" = "1" ]; then
    seeds="${seeds%%,*}"
fi

IFS=',' read -ra SEED_LIST <<< "$seeds"
IFS=',' read -ra ARM_LIST <<< "$arms"
IFS=',' read -ra DATASET_LIST <<< "$dataset"
for ds in "${DATASET_LIST[@]}"; do
    for arm in "${ARM_LIST[@]}"; do
        for seed in "${SEED_LIST[@]}"; do
            d="${VAST_OUTDIR:?}/runs/launch$n/$ds/$arm/seed${seed}_foldNone"
            mkdir -p "$d"
            printf '{"dataset": "%s", "arm": "%s", "seed": %s}\n' "$ds" "$arm" "$seed" \
                > "$d/meta.json"
        done
    done
done
exit 0
"""


def _harness(tmp_path, *args, extra_env=None):
    """Run the real harness against the recording double; return (log lines, process)."""
    bindir = tmp_path / "bin"
    bindir.mkdir(parents=True, exist_ok=True)
    launcher = bindir / "fake-launcher"
    launcher.write_text(DOUBLE)
    launcher.chmod(0o755)

    state = tmp_path / "double-state"
    state.mkdir(parents=True, exist_ok=True)
    log = tmp_path / "launches.txt"
    log.write_text("")

    env = {
        **os.environ,
        "VAST_OUTDIR": str(tmp_path / "out"),
        "DOUBLE_LOG": str(log),
        "DOUBLE_STATE": str(state),
        "TMPDIR": str(tmp_path),
        **(extra_env or {}),
    }
    env.pop("VAST_OUTDIR_SAVED", None)

    result = subprocess.run(
        [
            "bash", str(BATCH_RUN),
            # Before the operator's arguments, so an argument list that ends in `--`
            # cannot capture it and send the harness at the real launcher.
            "--launcher", str(launcher),
            *args,
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(tmp_path),
    )
    lines = [line for line in log.read_text().splitlines() if line.strip()]
    launches = []
    for line in lines:
        argv = line.split()
        if "--seeds" in argv:
            # Operator arguments precede the harness's own and the launcher is last-wins,
            # so the last `--seeds` on the line is the batch that actually ran.
            launches.append(argv[len(argv) - 1 - argv[::-1].index("--seeds") + 1])
    return launches, result


def _seed_ints(spec):
    return [int(part) for part in spec.split(",") if part]


def _bank(tmp_path, seeds, dataset=DATASET, arms=ARMS.split(","), launch="pre"):
    """Pre-seed the runs tree the way an earlier launch would have."""
    for arm in arms:
        for seed in seeds:
            d = tmp_path / "out" / "runs" / launch / dataset / arm / f"seed{seed}_foldNone"
            d.mkdir(parents=True)
            (d / "meta.json").write_text(
                json.dumps({"dataset": dataset, "arm": arm, "seed": seed})
            )


def _manifest(tmp_path, launch, **fields):
    """The manifest the box writes into its own run tree -- what says whether it counts.

    `emit_artifacts.sh` ships `manifest_<run_id>.json` at the top of the returned tree, and
    it is where `dry_run`, `train_size` and `test_size` are recorded. A launch with no
    manifest is the pre-manifest case: counted, unless a size was asked for.
    """
    d = tmp_path / "out" / "runs" / launch
    d.mkdir(parents=True, exist_ok=True)
    (d / f"manifest_{launch}.json").write_text(
        json.dumps({"run_id": launch, **fields})
    )


# --------------------------------------------------------------------------
# 1. The loop -- batch, retry, complete
# --------------------------------------------------------------------------
def test_forty_seeds_in_twelve_seed_batches_run_four_launches(tmp_path):
    """The issue's acceptance case. 40 seeds, batches of 12 -> 12,12,12,4 and COMPLETE."""
    launches, result = _harness(
        tmp_path,
        "225", "264", "12",
        "--dataset", DATASET, "--arms", ARMS,
        # 12 x 170 + 900 = 2940 s; the default 40-minute window would refuse it (and does,
        # see the sizing test), so the window is widened rather than the guard bypassed.
        "--poll-minutes", "120",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "BATCH COMPLETE:" in result.stdout
    assert len(launches) == 4, launches
    assert [len(_seed_ints(spec)) for spec in launches] == [12, 12, 12, 4]
    assert sorted(s for spec in launches for s in _seed_ints(spec)) == list(range(225, 265))


def test_a_batch_killed_mid_run_comes_back_on_the_next_pass(tmp_path):
    """The failure the fixed queue could not see: a dead range returns, and only it returns.

    Pass 2 must relaunch 225-230 and nothing else -- the seeds that did bank are the exit
    condition, so re-running them would be the duplicate range the campaign also paid for.
    """
    launches, result = _harness(
        tmp_path,
        "225", "236", "6",
        "--dataset", DATASET, "--arms", ARMS,
        "--poll-minutes", "120",
        extra_env={"DOUBLE_FAIL_ONCE": "225,226,227,228,229,230"},
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "BATCH FAIL:" in result.stdout
    assert launches == ["225,226,227,228,229,230", "231,232,233,234,235,236",
                        "225,226,227,228,229,230"], launches


def test_a_complete_range_is_never_launched(tmp_path):
    """A seed already banked for every arm is not launched again."""
    _bank(tmp_path, range(225, 230))

    launches, result = _harness(
        tmp_path,
        "225", "234", "3",
        "--dataset", DATASET, "--arms", ARMS,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert sorted(s for spec in launches for s in _seed_ints(spec)) == list(range(230, 235))


def test_a_seed_banked_on_one_arm_only_is_still_missing(tmp_path):
    """Completeness is per (dataset, arm): one arm's meta.json is not a banked seed."""
    _bank(tmp_path, [225], arms=["A_raw"])

    launches, result = _harness(
        tmp_path,
        "225", "225", "1",
        "--dataset", DATASET, "--arms", ARMS,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert launches == ["225"], launches


def test_an_already_complete_range_launches_nothing(tmp_path):
    _bank(tmp_path, range(225, 228))

    launches, result = _harness(
        tmp_path,
        "225", "227", "3",
        "--dataset", DATASET, "--arms", ARMS,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert launches == [], launches
    assert "BATCH COMPLETE:" in result.stdout


def test_a_dry_run_tree_does_not_bank_a_seed(tmp_path):
    """A mock costs nothing, so it measured nothing -- and a false COMPLETE is the failure.

    The launcher marks a mock in its record, not in `meta.json`, so the tree looks exactly
    like a paid launch's. Counting it would let a smoke test retire a range nobody ran.
    """
    _bank(tmp_path, range(225, 228), launch="dry1")
    _manifest(tmp_path, "dry1", dry_run=True)

    launches, result = _harness(
        tmp_path,
        "225", "227", "3",
        "--dataset", DATASET, "--arms", ARMS,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert launches == ["225,226,227"], launches


def test_a_real_record_with_the_same_tree_banks_the_seed(tmp_path):
    """The other half of the pair: the exclusion is the launch, not the shape of the tree."""
    _bank(tmp_path, range(225, 228), launch="paid1")
    _manifest(tmp_path, "paid1", dry_run=False)

    launches, result = _harness(
        tmp_path,
        "225", "227", "3",
        "--dataset", DATASET, "--arms", ARMS,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert launches == [], launches


def test_the_default_runs_one_launch_at_a_time(tmp_path):
    """`--parallel 1` is the default, and the default is what a test has to hold.

    Two live launchers are the failure #431 exists to test (#426); a regression that ran the
    four batches concurrently would pass every other test in this file.
    """
    launches, result = _harness(
        tmp_path,
        "225", "240", "4",
        "--dataset", DATASET, "--arms", ARMS,
        "--poll-minutes", "120",
        extra_env={"DOUBLE_LOCK": str(tmp_path / "live-launch.lock")},
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert len(launches) == 4, launches
    assert "OVERLAP" not in (tmp_path / "launches.txt").read_text()


def test_each_dataset_is_its_own_launch(tmp_path):
    """`--dataset a,b` must not reach the launcher: it runs one dataset, and `a,b` is none.

    Measured cost of getting this wrong: a paid boot that prints "Unknown dataset 'a,b'",
    writes nothing, and exits 0 -- the harness would see a stall with no diagnostic.
    """
    launches, result = _harness(
        tmp_path,
        "225", "225", "1",
        "--dataset", f"{DATASET},uslapseagent", "--arms", "A_raw",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert launches == ["225", "225"], launches
    recorded = (tmp_path / "launches.txt").read_text()
    assert f"--dataset {DATASET} " in recorded, recorded
    assert "--dataset eudirectlapse,uslapseagent" not in recorded, recorded


def test_a_banked_launch_at_another_row_size_does_not_count(tmp_path):
    """A row count is part of the design: 2,000 rows must not retire a 10,000-row seed."""
    _bank(tmp_path, [225], arms=[ARMS.split(",")[0]])
    _bank(tmp_path, [225], arms=[ARMS.split(",")[1]])
    _manifest(tmp_path, "pre", run_id="pre", train_size=2000, test_size=1000)

    launches, result = _harness(
        tmp_path,
        "225", "225", "1",
        "--dataset", DATASET, "--arms", ARMS,
        "--train-size", "10000", "--test-size", "10000",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert launches == ["225"], launches
    assert "train_size 2000 is not 10000" in result.stdout, result.stdout


def test_the_same_tree_banks_when_the_row_size_matches(tmp_path):
    _bank(tmp_path, [225])
    _manifest(tmp_path, "pre", run_id="pre", train_size=10000, test_size=10000)

    launches, result = _harness(
        tmp_path,
        "225", "225", "1",
        "--dataset", DATASET, "--arms", ARMS,
        "--train-size", "10000", "--test-size", "10000",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert launches == [], launches


def test_the_separator_cannot_replace_the_batch(tmp_path):
    """`-- --seeds 1-2` must not change what was launched: the batch wins, last argument."""
    launches, result = _harness(
        tmp_path,
        "225", "225", "1",
        "--dataset", DATASET, "--arms", ARMS,
        "--", "--seeds", "1-2",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert launches == ["225"], launches


def test_macos_notifications_are_a_real_sink(tmp_path):
    """`--notify-macos` shells out to osascript, which a stub on PATH can prove."""
    stub_dir = tmp_path / "notifybin"
    stub_dir.mkdir()
    sink = tmp_path / "osascript.args"
    stub = stub_dir / "osascript"
    stub.write_text(f'#!/bin/bash\nprintf "%s\\n" "$*" >> "{sink}"\n')
    stub.chmod(0o755)

    _, result = _harness(
        tmp_path,
        "225", "225", "1",
        "--dataset", DATASET, "--arms", ARMS,
        "--notify-macos",
        extra_env={"PATH": f"{stub_dir}:{os.environ['PATH']}"},
    )

    assert result.returncode == 0, result.stdout + result.stderr
    calls = sink.read_text()
    assert "display notification" in calls, calls
    assert "BATCH COMPLETE: 225-225 banked" in calls, calls


def test_launcher_arguments_after_the_separator_reach_the_launcher(tmp_path):
    """The harness passes what it guarded with, and forwards the operator's own flags."""
    launches, result = _harness(
        tmp_path,
        "225", "225", "1",
        "--dataset", DATASET, "--arms", ARMS,
        "--poll-minutes", "120", "--estimate-sec-per-seed", "150",
        "--", "--max-dph", "0.40", "--gpu-allow", "RTX 4090",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert len(launches) == 1, launches
    line = (tmp_path / "launches.txt").read_text().splitlines()[0]
    # The same operands the pre-spend guard used, so the two cannot disagree at launch time.
    assert "--poll-minutes 120" in line, line
    assert "--estimate-sec-per-seed 150" in line, line
    assert "--max-dph 0.40" in line, line
    assert "--arms A_raw,B_ft30" in line, line
    assert "--dataset eudirectlapse" in line, line


# --------------------------------------------------------------------------
# 2. The stopping conditions
# --------------------------------------------------------------------------
def test_two_empty_passes_stall_the_queue(tmp_path):
    """A queue that pays twice for the same nothing stops; a single dead batch gets its retry.

    One empty pass is not a stall -- the issue asks for a killed batch to come back on the
    next pass, and a campaign with one batch per pass would otherwise never get that retry.
    Two in a row is a set that is not moving, and a third would be the same money again.
    """
    launches, result = _harness(
        tmp_path,
        "225", "230", "6",
        "--dataset", DATASET, "--arms", ARMS,
        "--max-passes", "5",
        extra_env={"DOUBLE_ALWAYS_FAIL": "1"},
    )

    assert result.returncode == 4, result.stdout + result.stderr
    assert "BATCH STALL:" in result.stdout
    assert len(launches) == 2, launches   # two attempts, not five


def test_the_pass_limit_exits_three_and_prints_what_is_missing(tmp_path):
    """Slow convergence is not a stall; it is still a failure to finish, and it names the gap."""
    launches, result = _harness(
        tmp_path,
        "225", "230", "6",
        "--dataset", DATASET, "--arms", ARMS,
        "--max-passes", "2",
        extra_env={"DOUBLE_BANK_ONLY_FIRST": "1"},
    )

    assert result.returncode == 3, result.stdout + result.stderr
    assert "BATCH STOP:" in result.stdout
    assert "227-230" in result.stdout, result.stdout
    assert len(launches) == 2, launches


def test_a_launcher_refusal_stops_the_pass_immediately(tmp_path):
    """rc=2 costs nothing and would repeat identically; retrying into it is a wasted pass."""
    launches, result = _harness(
        tmp_path,
        "225", "230", "3",
        "--dataset", DATASET, "--arms", ARMS,
        extra_env={"DOUBLE_REFUSE": "1"},
    )

    assert result.returncode == 2, result.stdout + result.stderr
    assert "BATCH STOP:" in result.stdout
    assert "refused" in result.stdout
    assert len(launches) == 1, launches   # the second batch is not attempted


# --------------------------------------------------------------------------
# 3. Refusals that must happen before anything is rented
# --------------------------------------------------------------------------
def test_parallel_above_one_is_refused_until_the_concurrency_test_exists(tmp_path):
    """Two live launchers shared one output file and pulled each other's artifacts (#426)."""
    launches, result = _harness(
        tmp_path,
        "225", "230", "3",
        "--dataset", DATASET, "--arms", ARMS,
        "--parallel", "2",
    )

    assert result.returncode == 2, result.stdout + result.stderr
    assert "#431" in result.stderr, result.stderr
    assert launches == [], launches


def test_a_batch_too_large_for_the_poll_window_is_refused_before_spending(tmp_path):
    """The launcher would discard it, so the harness refuses it before anything is rented.

    20 seeds x 170 s + 900 s = 4300 s against a 2400 s window. Twelve seeds are also refused
    by default (2940 s): the 40-minute window admits eight, which is why the acceptance case
    above raises it rather than the guard being bypassed.
    """
    launches, result = _harness(
        tmp_path,
        "225", "244", "20",
        "--dataset", DATASET, "--arms", ARMS,
    )

    assert result.returncode == 2, result.stdout + result.stderr
    assert "cannot finish inside the poll window" in result.stderr
    assert "20 seed(s)" in result.stderr
    assert "most 8 seed(s)" in result.stderr
    assert launches == [], launches

    twelve, refused = _harness(
        tmp_path / "twelve",
        "225", "236", "12",
        "--dataset", DATASET, "--arms", ARMS,
    )
    assert refused.returncode == 2, refused.stdout + refused.stderr
    assert "12 seed(s) x 170s + 900s boot = 2940s" in refused.stderr, refused.stderr
    assert twelve == [], twelve


def test_the_design_is_required_not_guessed(tmp_path):
    """A harness that inferred the pairs would report COMPLETE over a range nobody ran."""
    _, no_dataset = _harness(tmp_path / "a", "225", "230", "3", "--arms", ARMS)
    assert no_dataset.returncode == 2
    assert "--dataset is required" in no_dataset.stderr

    _, no_arms = _harness(tmp_path / "b", "225", "230", "3", "--dataset", DATASET)
    assert no_arms.returncode == 2
    assert "--arms is required" in no_arms.stderr


def test_usage_errors_are_refused(tmp_path):
    for args, expected in (
        (("230", "225", "3"), "before START"),
        (("225", "230", "0"), "at least 1"),
        (("225", "230", "x"), "whole number"),
    ):
        _, result = _harness(
            tmp_path / str(expected).replace(" ", "-"),
            *args, "--dataset", DATASET, "--arms", ARMS,
        )
        assert result.returncode == 2, (args, result.stdout + result.stderr)
        assert expected in result.stderr, (args, result.stderr)


# --------------------------------------------------------------------------
# 4. It announces itself -- a twenty-hour run must not need polling
# --------------------------------------------------------------------------
def test_completion_and_failure_announce_to_the_log(tmp_path):
    log = tmp_path / "notifications.log"
    _, result = _harness(
        tmp_path,
        "225", "230", "3",
        "--dataset", DATASET, "--arms", ARMS,
        "--notify-log", str(log),
        extra_env={"DOUBLE_FAIL_ONCE": "225,226,227"},
    )

    assert result.returncode == 0, result.stdout + result.stderr
    text = log.read_text()
    assert "BATCH FAIL:" in text, text
    assert "BATCH COMPLETE:" in text, text
    assert text.strip().splitlines()[-1].endswith(
        "banked for every pair, in 2 pass(es)"
    ), text
    assert "BATCH COMPLETE:" in text.strip().splitlines()[-1], text


def test_stall_announces_to_the_log_and_to_a_command(tmp_path):
    """--notify is the webhook/macOS seam: the line arrives as an argument and an env var."""
    log = tmp_path / "notifications.log"
    sink = tmp_path / "sink.txt"
    notify = tmp_path / "notify.sh"
    notify.write_text(
        f'#!/bin/bash\nprintf "%s|%s\\n" "$BATCH_KIND" "$BATCH_MESSAGE" >> "{sink}"\n'
    )
    notify.chmod(0o755)

    _, result = _harness(
        tmp_path,
        "225", "230", "3",
        "--dataset", DATASET, "--arms", ARMS,
        "--notify-log", str(log), "--notify", str(notify),
        extra_env={"DOUBLE_ALWAYS_FAIL": "1"},
    )

    assert result.returncode == 4, result.stdout + result.stderr
    assert "BATCH STALL:" in log.read_text()
    lines = sink.read_text().strip().splitlines()
    assert lines[-1].startswith("STALL|BATCH STALL:"), lines


# --------------------------------------------------------------------------
# 5. The harness and the launcher size a batch with ONE sum
# --------------------------------------------------------------------------
def test_the_guard_the_harness_applies_is_the_launcher_s(tmp_path):
    """`fit_guard.sh` is the only place the sum exists, and both callers agree at the boundary.

    8 seeds at the defaults are 2260 s inside a 2400 s window; 9 are 2430 s and do not fit.
    """
    capacity = subprocess.run(
        ["bash", "-c", f'. "{FIT_GUARD}"; batch_capacity 170 900 40'],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert capacity == "8", capacity

    fits = subprocess.run(
        ["bash", "-c",
         f'. "{FIT_GUARD}"; batch_fits "$1" 170 900 40; echo "$?"; '
         'batch_fits "$2" 170 900 40; echo "$?"', "_", "8", "9"],
        capture_output=True, text=True, check=True,
    ).stdout.split()
    assert fits == ["0", "1"], fits

    # And the launcher refuses the count the helper calls over-capacity, from free.
    from tests.test_pilot2_seed_passthrough import _launch

    nine = ",".join(str(seed) for seed in range(93, 102))
    state, result = _launch(tmp_path, "--seeds", nine, "--arms", "A_raw")
    assert result.returncode == 2, result.stdout + result.stderr
    assert "cannot finish inside the poll window" in result.stderr
    assert "9 seed(s) x 170s + 900s boot = 2430s" in result.stderr, result.stderr
    assert not (state / "created.txt").exists()


# --------------------------------------------------------------------------
# 6. The banked-set reader is a CLI because #432 will need the same numbers
# --------------------------------------------------------------------------
def test_banked_seeds_reports_per_pair_gaps(tmp_path):
    _bank(tmp_path, [225, 226], arms=["A_raw"])
    _bank(tmp_path, [225], arms=["B_ft30"])

    result = subprocess.run(
        ["python3", str(BANKED),
         "--runs-dir", str(tmp_path / "out" / "runs"),
         "--seeds", "225-227", "--dataset", DATASET, "--arms", ARMS],
        capture_output=True, text=True,
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert "BANKED 1/3" in result.stdout, result.stdout
    assert "MISSING 226-227" in result.stdout, result.stdout
    assert f"GAP {DATASET}/A_raw: 227" in result.stdout, result.stdout
    assert f"GAP {DATASET}/B_ft30: 226-227" in result.stdout, result.stdout


def test_banked_seeds_skips_a_dry_run_launch(tmp_path):
    """The CLI says so out loud, so an operator can see why a full tree is still 'missing'."""
    _bank(tmp_path, [225], launch="dry1")
    _manifest(tmp_path, "dry1", dry_run=True)

    result = subprocess.run(
        ["python3", str(BANKED),
         "--runs-dir", str(tmp_path / "out" / "runs"),
         "--seeds", "225", "--dataset", DATASET, "--arms", ARMS],
        capture_output=True, text=True,
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert "SKIPPED dry1 (dry run: zero cost, not evidence)" in result.stdout, result.stdout
    assert "BANKED 0/1" in result.stdout


def test_banked_seeds_on_a_missing_runs_tree_reports_everything_missing(tmp_path):
    """The first pass of a campaign has no tree at all; that is not an error."""
    result = subprocess.run(
        ["python3", str(BANKED),
         "--runs-dir", str(tmp_path / "does-not-exist"),
         "--seeds", "225-226", "--dataset", DATASET, "--arms", ARMS],
        capture_output=True, text=True,
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert "BANKED 0/2" in result.stdout
    assert "MISSING 225-226" in result.stdout
