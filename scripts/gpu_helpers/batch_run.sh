#!/bin/bash
# A self-healing batch harness: the missing set is the queue (#430).
#
#   bash scripts/gpu_helpers/batch_run.sh START END BATCH_SIZE \
#        --dataset NAME[,NAME] --arms LIST [options] [-- LAUNCHER_ARGS...]
#
# WHY THIS EXISTS. A fixed queue (batch 1..16, in order) skips a dead range and moves on, and
# a batch that writes another range's seeds leaves the range it *thought* it had covered
# missing. Neither is visible until someone diffs the run directories against the design; on
# the 2026-11-05 campaign that was a quarter of the spend buying nothing. So this harness does
# not carry a plan at all:
#
#   loop, at most --max-passes:
#     read the run directories   -> which seeds in [START,END] lack a meta.json for every
#                                   (dataset, arm) pair?
#     if none                    -> announce COMPLETE, exit 0
#     split the missing seeds into batches of BATCH_SIZE, one launch per dataset
#     run them, one at a time    -> a dead or wrong batch is simply still missing next pass
#
# There is no plan to drift from, and a duplicated range cannot happen because "already on
# disk" is the exit condition.
#
# THE DESIGN IS PASSED IN, NOT GUESSED (`--dataset`, `--arms`, both required). A harness that
# inferred the pair set from what is already banked would report COMPLETE over a range it has
# never launched -- exactly the failure this ticket removes. Both values are passed verbatim
# to every launch, so the harness's notion of a complete seed and the launcher's notion of
# what it will write are the same list by construction.
#
# ONE LAUNCH PER DATASET. `vast_run.sh --dataset` runs ONE dataset; handing it `a,b` makes the
# runner print "Unknown dataset 'a,b'" and return nothing while the box is already paid for.
# So a comma list here means several launches per batch, each with one dataset.
#
# YOU KNOW A LAUNCH SUCCEEDED BY THE TREE, NOT THE EXIT CODE. The launcher verifies the seeds
# it wrote (#429) and refuses on a mismatch, but it deliberately tolerates an absent payload
# (exit 3 warning) and a box whose arms all died, both of which exit 0. That is why the
# harness recomputes what is missing after every pass instead of trusting rc: a batch that
# looked healthy and banked nothing simply comes back.
#
# Options:
#   --dataset LIST   datasets the campaign covers          (REQUIRED)
#   --arms LIST      arms the campaign covers              (REQUIRED)
#   --max-passes N   passes before giving up                (default 3)
#   --poll-minutes M the launcher's poll window             (default 40, as vast_run.sh)
#   --estimate-sec-per-seed N  measured per-seed time       (default 170, as vast_run.sh)
#   --train-size N   training rows: forwarded to the launcher AND required of every launch
#                    already on disk before its seeds count as banked
#   --test-size N    test rows, the same way
#   --launcher PATH  the launcher to drive                  (default scripts/gpu_helpers/vast_run.sh)
#   --runs-dir DIR   where the launch trees live            (default $VAST_OUTDIR/runs)
#   --parallel N     concurrent launches                    (default 1; >1 is #431's, not this)
#   --notify CMD     run CMD once per announcement, with the line in $BATCH_MESSAGE and the
#                    kind in $BATCH_KIND
#   --notify-macos   also post a macOS notification (the harness runs on the operator's laptop)
#   --notify-log F   the announcement file                  (default $VAST_OUTDIR/batch_notifications.log)
#   --               everything after this goes to the launcher, BEFORE the harness's own
#                    arguments -- so the batch being run always wins
#
# THE SIZE GUARD IS THE LAUNCHER'S OWN (fit_guard.sh). A batch that cannot finish inside the
# poll window is refused HERE, before anything is rented, with the same text the launcher
# would use -- and both operands are also passed to every launch, so the guard applied and
# the guard the launcher applies cannot disagree. At the 170 s/900 s defaults a 40-minute
# window admits 8 seeds; a 12-seed batch needs a window of about 49 minutes (34 min of fits
# plus the startup allowance). Rule 1 of the runbook is why: 170 s is a measured RTX PRO 4000
# figure, and a 3090 ran 753-837 s/seed, so pin `--gpu-allow` to a class whose timing was
# measured or the estimate is fiction.
#
# ATTENTION. On COMPLETE, failure and stall this writes ONE line to the announcement log, and
# to --notify CMD / a macOS notification when given. A twenty-hour run should interrupt a
# human instead of being polled. It cannot announce its own death (SIGKILL, a sleeping laptop);
# that is #433's box-side guard, not this.
#
# Exit codes:
#   0  COMPLETE -- every seed in [START,END] banked for every (dataset, arm)
#   2  usage error, or a refusal: `--parallel` above 1, a batch too large for the poll window,
#      or the launcher exiting 2 -- which means either a free pre-flight refusal or a release
#      that could not confirm the instance was gone. Either way nothing further is launched,
#      and the launcher's own output says which it was
#   3  the pass limit was reached with seeds still missing; they are printed
#   4  STALL -- two consecutive passes banked nothing; the harness stops instead of renting
#      again for a set that is not moving
#
# Two empty passes, not one, because the issue asks for a dead batch to come back on the next
# pass: a campaign whose only batch died would otherwise never get its retry.

set -uo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GH="$REPO_DIR/scripts/gpu_helpers"
OUTDIR="${VAST_OUTDIR:-$REPO_DIR/outputs/gpu-pilot}"

# shellcheck source=fit_guard.sh
. "$GH/fit_guard.sh"

LAUNCHER="$GH/vast_run.sh"
RUNS_DIR="$OUTDIR/runs"
DATASET=""
ARMS=""
TRAIN_SIZE=""
TEST_SIZE=""
MAX_PASSES=3
# Both mirrored from vast_run.sh, which owns the measured values (runbook rule 1). They are
# passed to every launch explicitly, so a change there cannot leave the harness sizing
# batches against a window the launcher no longer uses.
POLL_MINUTES="${POLL_MINUTES:-40}"
EST_SEC_PER_SEED="${EST_SEC_PER_SEED:-170}"
BOOT_EST_SECONDS="${BOOT_EST_SECONDS:-900}"
PARALLEL=1
NOTIFY_CMD=""
NOTIFY_MACOS=0
NOTIFY_LOG="$OUTDIR/batch_notifications.log"

usage() {  # [exit code], default 2; 0 goes to stdout so --help can be piped
    local rc="${1:-2}" stream=2
    [ "$rc" -eq 0 ] && stream=1
    cat >&"$stream" <<'USAGE'
usage: batch_run.sh START END BATCH_SIZE --dataset NAME[,NAME] --arms LIST [options]
                   [-- LAUNCHER_ARGS...]

  --dataset LIST              datasets the campaign covers          (REQUIRED)
  --arms LIST                 arms the campaign covers              (REQUIRED)
  --max-passes N              passes before giving up                (default 3)
  --poll-minutes M            the launcher's poll window             (default 40)
  --estimate-sec-per-seed N   measured per-seed time                (default 170)
  --train-size N              training rows: forwarded, and required of banked launches
  --test-size N               test rows, the same way
  --launcher PATH             launcher to drive (default vast_run.sh)
  --runs-dir DIR              where the launch trees live (default $VAST_OUTDIR/runs)
  --parallel N                concurrent launches (default 1; >1 is #431's, not this)
  --notify CMD                run CMD per announcement; line in $BATCH_MESSAGE/$BATCH_KIND
  --notify-macos              also post a macOS notification
  --notify-log FILE           announcement file (default $VAST_OUTDIR/batch_notifications.log)

Exit: 0 COMPLETE, 2 usage/refusal, 3 pass limit hit with seeds missing, 4 STALL.
The header of this file explains why each of these exists.
USAGE
    exit "$rc"
}

usage_error() {
    echo "USAGE: $*" >&2
    usage
}

# One readable line, to the log and to the sinks a human actually sees. Every terminal event
# goes through here: the reason this exists is that a twenty-hour run must not need polling.
announce() {  # KIND message...
    local kind="$1" line
    shift
    line="BATCH ${kind}: $*"
    printf '%s\n' "$line"
    mkdir -p "$(dirname "$NOTIFY_LOG")" 2>/dev/null || true
    printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$line" >> "$NOTIFY_LOG" 2>/dev/null || true
    if [ -n "$NOTIFY_CMD" ]; then
        # The line arrives as $BATCH_MESSAGE (plus $BATCH_KIND), not as an argument: a
        # webhook command is usually a pipeline or ends in a redirect, and appending an
        # argument to that would land it on whichever command came last. So:
        #   --notify 'curl -fsS -d "$BATCH_MESSAGE" https://hooks.example/tfm'
        BATCH_MESSAGE="$line" BATCH_KIND="$kind" sh -c "$NOTIFY_CMD" || \
            echo "WARNING: --notify command failed; the announcement is still in $NOTIFY_LOG" >&2
    fi
    if [ "$NOTIFY_MACOS" -eq 1 ] && command -v osascript >/dev/null 2>&1; then
        osascript -e 'on run argv' \
                  -e 'display notification (item 1 of argv) with title "tabular-foundation-model"' \
                  -e 'end run' -- "$line" >/dev/null 2>&1 || true
    fi
}

# Read the runs tree for one dataset list into PLAN_* globals. Returns banked_seeds.py's
# status: 0 complete, 1 missing, 2 usage.
read_plan() {  # DATASET_LIST
    PLAN_TEXT="$(python3 "$GH/banked_seeds.py" \
        --runs-dir "$RUNS_DIR" --seeds "$START-$END" \
        --dataset "$1" --arms "$ARMS" \
        "${SIZE_ARGS[@]+"${SIZE_ARGS[@]}"}")"
    PLAN_RC=$?
    PLAN_BANKED="$(printf '%s\n' "$PLAN_TEXT" | awk -F'[/ ]' '/^BANKED /{print $2; exit}')"
    PLAN_TOTAL="$(printf '%s\n' "$PLAN_TEXT" | awk -F'[/ ]' '/^BANKED /{print $3; exit}')"
    PLAN_MISSING="$(printf '%s\n' "$PLAN_TEXT" | awk '/^MISSING /{sub(/^MISSING /,""); print; exit}')"
    return "$PLAN_RC"
}

# The missing range as one seed per line, through #429's own parser: `229-231,240` and
# `229,230,231,240` must mean the same thing here as they do to the verifier.
expand_seeds() {  # RANGE_SPEC -> "229 230 231 240"
    PYTHONPATH="$GH" python3 -c \
        'import sys; from verify_artifacts import parse_seeds; \
print(" ".join(str(s) for s in parse_seeds(sys.argv[1])))' "$1"
}

# ---- arguments -----------------------------------------------------------------------
START=""
END=""
BATCH_SIZE=""
while [ "$#" -gt 0 ]; do
    # Every option below takes a value; `shift 2` past the end silently loops forever on
    # some shells, so say what is missing instead.
    case "$1" in
        --dataset|--arms|--max-passes|--poll-minutes|--estimate-sec-per-seed|\
        --train-size|--test-size|--launcher|--runs-dir|--parallel|--notify|--notify-log)
            [ "$#" -ge 2 ] || usage_error "$1 needs a value" ;;
    esac
    case "$1" in
        --dataset) DATASET="${2:-}"; shift 2 ;;
        --arms) ARMS="${2:-}"; shift 2 ;;
        --max-passes) MAX_PASSES="${2:-}"; shift 2 ;;
        --poll-minutes) POLL_MINUTES="${2:-}"; shift 2 ;;
        --estimate-sec-per-seed) EST_SEC_PER_SEED="${2:-}"; shift 2 ;;
        --train-size) TRAIN_SIZE="${2:-}"; shift 2 ;;
        --test-size) TEST_SIZE="${2:-}"; shift 2 ;;
        --launcher) LAUNCHER="${2:-}"; shift 2 ;;
        --runs-dir) RUNS_DIR="${2:-}"; shift 2 ;;
        --parallel) PARALLEL="${2:-}"; shift 2 ;;
        --notify) NOTIFY_CMD="${2:-}"; shift 2 ;;
        --notify-macos) NOTIFY_MACOS=1; shift ;;
        --notify-log) NOTIFY_LOG="${2:-}"; shift 2 ;;
        --help|-h) usage 0 ;;
        --) shift; break ;;
        -*) usage_error "unknown option $1" ;;
        *)
            if [ -z "$START" ]; then START="$1"
            elif [ -z "$END" ]; then END="$1"
            elif [ -z "$BATCH_SIZE" ]; then BATCH_SIZE="$1"
            else usage_error "unexpected argument $1"
            fi
            shift ;;
    esac
done
LAUNCHER_ARGS=("$@")

[ -n "$START" ] && [ -n "$END" ] && [ -n "$BATCH_SIZE" ] || \
    usage_error "START END BATCH_SIZE are all required"
for n in "$START" "$END" "$BATCH_SIZE" "$MAX_PASSES" "$POLL_MINUTES" \
         "$EST_SEC_PER_SEED" "$PARALLEL"; do
    case "$n" in
        ''|*[!0-9]*) usage_error "expected a whole number, got '$n'" ;;
    esac
done
for n in "$TRAIN_SIZE" "$TEST_SIZE"; do
    # Empty means "not asked for"; the launcher's own default applies.
    [ -z "$n" ] && continue
    case "$n" in
        *[!0-9]*) usage_error "expected a whole number of rows, got '$n'" ;;
    esac
done
[ "$END" -ge "$START" ] || usage_error "END ($END) is before START ($START)"
[ "$BATCH_SIZE" -ge 1 ] || usage_error "BATCH_SIZE must be at least 1"
[ "$MAX_PASSES" -ge 1 ] || usage_error "--max-passes must be at least 1"
# An estimate of 0 disables the guard while looking like it applied one.
[ "$EST_SEC_PER_SEED" -ge 1 ] || usage_error "--estimate-sec-per-seed must be at least 1"
[ "$PARALLEL" -ge 1 ] || usage_error "--parallel must be at least 1"
[ -n "$DATASET" ] || usage_error "--dataset is required: the harness cannot report COMPLETE
  for a design it was not told about (see the header)"
[ -n "$ARMS" ] || usage_error "--arms is required: a seed is complete only for the arms the
  launch will write, and this harness must not guess which those are"
# #431 is the test that two live launchers cannot collide (runbook rule 4). Until it exists,
# a second concurrent launcher is the failure that pulled another launch's artifacts (#426),
# so the flag exists and refuses rather than silently ignoring what was asked for.
if [ "$PARALLEL" -ne 1 ]; then
    echo "REFUSING: --parallel $PARALLEL is #431's, not built yet." >&2
    echo "  Two concurrent launchers once shared one output file and pulled each other's" >&2
    echo "  artifacts, both reporting success (#426). Run one at a time until #431 lands." >&2
    exit 2
fi
if [ ! -f "$LAUNCHER" ]; then
    echo "FATAL: launcher not found: $LAUNCHER" >&2
    exit 2
fi
# Refuse before renting: the same sum and the same text the launcher would print (#414).
if ! batch_fits "$BATCH_SIZE" "$EST_SEC_PER_SEED" "$BOOT_EST_SECONDS" "$POLL_MINUTES"; then
    batch_refuse "$BATCH_SIZE" "$EST_SEC_PER_SEED" "$BOOT_EST_SECONDS" "$POLL_MINUTES"
    echo "  (no batch this harness built could ever be launched: this window admits at" >&2
    echo "   most $(batch_capacity "$EST_SEC_PER_SEED" "$BOOT_EST_SECONDS" "$POLL_MINUTES")" \
         "seed(s). Lower BATCH_SIZE or raise --poll-minutes.)" >&2
    exit 2
fi

IFS=',' read -ra DATASETS <<< "$DATASET"
SIZE_ARGS=()
[ -n "$TRAIN_SIZE" ] && SIZE_ARGS+=(--train-size "$TRAIN_SIZE")
[ -n "$TEST_SIZE" ] && SIZE_ARGS+=(--test-size "$TEST_SIZE")

echo "=== batch_run: seeds $START-$END, batches of $BATCH_SIZE, up to $MAX_PASSES pass(es) ==="
echo "    runs:  $RUNS_DIR"
echo "    size:  ${EST_SEC_PER_SEED}s/seed + ${BOOT_EST_SECONDS}s boot vs a ${POLL_MINUTES} min window"

PASS=1
EMPTY_PASSES=0
while [ "$PASS" -le "$MAX_PASSES" ]; do
    read_plan "$DATASET"
    PLAN_RC=$?
    if [ "$PLAN_RC" -eq 2 ]; then
        echo "FATAL: banked_seeds.py rejected the request; nothing was launched." >&2
        printf '%s\n' "$PLAN_TEXT" >&2
        exit 2
    fi
    printf '%s\n' "$PLAN_TEXT"
    if [ "$PLAN_RC" -eq 0 ]; then
        announce COMPLETE "$START-$END banked for every pair, in $((PASS - 1)) pass(es)"
        exit 0
    fi
    BANKED_BEFORE="$PLAN_BANKED"

    for ds in "${DATASETS[@]}"; do
        read_plan "$ds"
        DS_RC=$?
        if [ "$DS_RC" -eq 2 ]; then
            echo "FATAL: banked_seeds.py rejected dataset '$ds'; nothing was launched." >&2
            printf '%s\n' "$PLAN_TEXT" >&2
            exit 2
        fi
        # Nothing to do for this dataset this pass; another one is still behind.
        [ "$DS_RC" -eq 0 ] && continue

        SEEDS="$(expand_seeds "$PLAN_MISSING")" || {
            echo "FATAL: could not expand the missing range '$PLAN_MISSING'" >&2
            exit 2
        }
        BATCHES=()
        CURRENT=""
        COUNT=0
        for seed in $SEEDS; do
            CURRENT="${CURRENT:+$CURRENT,}$seed"
            COUNT=$((COUNT + 1))
            if [ "$COUNT" -eq "$BATCH_SIZE" ]; then
                BATCHES+=("$CURRENT")
                CURRENT=""
                COUNT=0
            fi
        done
        [ -n "$CURRENT" ] && BATCHES+=("$CURRENT")

        echo "--- pass $PASS/$MAX_PASSES: $ds $PLAN_BANKED/$PLAN_TOTAL banked, ${#BATCHES[@]} batch(es) to run"

        i=0
        for batch in "${BATCHES[@]}"; do
            i=$((i + 1))
            echo "--- pass $PASS batch $i/${#BATCHES[@]}: $ds seeds $batch"
            # Operator arguments come FIRST: `vast_run.sh` is last-wins, so a `--` argument
            # must not be able to replace the seeds, dataset or window this batch was
            # planned with. --yes is the unattended default, and it deliberately does NOT
            # answer the leak preflight (#423): an instance still billing from an earlier
            # launch is exactly the condition a queue should stop on, not continue past.
            bash "$LAUNCHER" "${LAUNCHER_ARGS[@]+"${LAUNCHER_ARGS[@]}"}" --yes \
                --seeds "$batch" --arms "$ARMS" --dataset "$ds" \
                --poll-minutes "$POLL_MINUTES" --estimate-sec-per-seed "$EST_SEC_PER_SEED" \
                "${SIZE_ARGS[@]+"${SIZE_ARGS[@]}"}"
            rc=$?
            case "$rc" in
                0) ;;
                2) # Either a free refusal or a release that could not confirm the instance
                   # was gone. Both want a human, and both would repeat identically.
                   announce STOP "launcher exited 2 on $ds seeds=$batch (pass $PASS); nothing further will be launched -- read the launcher's output to see whether it refused for free or could not confirm a release"
                   exit 2 ;;
                *) announce FAIL "$ds seeds=$batch exited rc=$rc on pass $PASS; those seeds stay missing and come back next pass" ;;
            esac
        done
    done

    read_plan "$DATASET"
    PLAN_RC=$?
    if [ "$PLAN_RC" -eq 2 ]; then
        echo "FATAL: banked_seeds.py rejected the request after pass $PASS." >&2
        printf '%s\n' "$PLAN_TEXT" >&2
        exit 2
    fi
    if [ "$PLAN_RC" -eq 0 ]; then
        announce COMPLETE "$START-$END banked for every pair, in $PASS pass(es)"
        exit 0
    fi
    if [ "$PLAN_BANKED" -gt "$BANKED_BEFORE" ]; then
        EMPTY_PASSES=0
        echo "--- pass $PASS banked $((PLAN_BANKED - BANKED_BEFORE)) seed(s): $PLAN_BANKED/$PLAN_TOTAL"
    else
        EMPTY_PASSES=$((EMPTY_PASSES + 1))
        echo "--- pass $PASS banked nothing: $PLAN_BANKED/$PLAN_TOTAL ($EMPTY_PASSES empty pass(es))"
        if [ "$EMPTY_PASSES" -ge 2 ]; then
            announce STALL "two passes in a row banked nothing ($PLAN_BANKED/$PLAN_TOTAL); missing $PLAN_MISSING. Stopped rather than renting again"
            exit 4
        fi
    fi
    PASS=$((PASS + 1))
done

announce STOP "$MAX_PASSES pass(es) used and $PLAN_MISSING still missing ($PLAN_BANKED/$PLAN_TOTAL banked)"
exit 3
