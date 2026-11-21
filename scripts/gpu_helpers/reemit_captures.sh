#!/usr/bin/env bash
# Re-emit a kept instance's finished captures WITHOUT re-fitting (#568).
#
# WHY. The two halves of a paid fair test fail independently. On 2026-11-21 the `severity_french`
# fits finished and sealed on the box, and the launcher died of local fork exhaustion before it
# could pull. The instance was kept, but no later poll could order the payload: the header
# (`__ARTIFACTS_INFO__`) had scrolled out of the log window, so the capture could not be
# hash-verified and $1.26 bought nothing.
#
# THE CHANNEL. There is no exec channel -- `vastai execute` runs only ls/rm/du, and the team
# context refuses SSH keys. The instance LIFECYCLE is one: a restart re-runs the launch's own
# onstart against the same disk. Measured 2026-11-21 on a $0.0285/hr probe: four reboots, a
# /workspace counter reading 1..4, and a container log that accumulates across restarts. The
# bootstrap's re-emit fast path (bootstrap_pilot.sh, section 2b) is what turns the restart into an
# emit instead of a second fit.
#
# WHAT IT REFUSES. It reboots only when the launch's own `########## EMIT <target> (<id>)` markers
# are in the box's log, so a box that sealed nothing is not restarted and nothing is spent. The
# refusal names both things it looked for.
#
# Usage:
#   reemit_captures.sh --instance ID [--seeds 1001,1002] [--poll-minutes 30] [--keep] [--yes]
#
# It never creates an instance, never selects an offer, and never runs a fit.
set -uo pipefail
umask 077

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

INSTANCE=""
SEEDS=""
POLL_MINUTES="${POLL_MINUTES:-30}"
POLL_TAIL="${POLL_TAIL:-8000}"
# The poll interval is a knob so a mock-driven test does not pay ten seconds per poll. Real
# launches use the same 10 s the primary poll loop uses.
POLL_SECONDS="${REEMIT_POLL_SECONDS:-10}"
KEEP=0
ASSUME_YES=0

usage() {
    sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'
}

while [ $# -gt 0 ]; do
    case "$1" in
        --instance) INSTANCE="$2"; shift 2 ;;
        --seeds) SEEDS="$2"; shift 2 ;;
        --poll-minutes) POLL_MINUTES="$2"; shift 2 ;;
        --poll-tail) POLL_TAIL="$2"; shift 2 ;;
        --keep) KEEP=1; shift ;;
        --yes) ASSUME_YES=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done

if [ -z "$INSTANCE" ]; then
    echo "FATAL: --instance is required; reemit attaches to an instance a launch already kept." >&2
    exit 2
fi
case "$INSTANCE" in
    ''|*[!0-9]*) echo "FATAL: --instance must be numeric (got '$INSTANCE')." >&2; exit 2 ;;
esac
if [ "$ASSUME_YES" -ne 1 ]; then
    echo "FATAL: non-interactive re-emit needs --yes (it reboots a billing instance)." >&2
    exit 2
fi
command -v vastai >/dev/null 2>&1 || { echo "FATAL: vastai is not on PATH." >&2; exit 2; }

OUTDIR="${VAST_OUTDIR:-$REPO_DIR/outputs/gpu-pilot}"
LOG_DIR="$OUTDIR/logs"
mkdir -p "$LOG_DIR" || { echo "FATAL: cannot write $LOG_DIR" >&2; exit 2; }
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_FILE="$LOG_DIR/reemit-${INSTANCE}-${STAMP}.log"

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/tfm-reemit.XXXXXX")" || exit 2
CHUNKS="$TMP_DIR/chunks"
mkdir -p "$CHUNKS"
trap 'rm -rf "$TMP_DIR"' EXIT

# Bounded poll. `vastai logs` once sat in flight for 13 minutes while the window moved past three
# chunks; a recovery loop that can hang is no recovery. The same shape as the launcher's poll.
POLL_TIMEOUT="${POLL_TIMEOUT:-120}"
poll_logs() {
    local out="$1" err="$2" waited=0 pid
    vastai logs "$INSTANCE" --tail "$POLL_TAIL" > "$out" 2> "$err" &
    pid=$!
    while kill -0 "$pid" 2>/dev/null && [ "$waited" -lt "$POLL_TIMEOUT" ]; do
        sleep 2
        waited=$(( waited + 2 ))
    done
    if kill -0 "$pid" 2>/dev/null; then
        kill "$pid" 2>/dev/null
        wait "$pid" 2>/dev/null
        return 124
    fi
    wait "$pid"
}

# One exit path for every failure after the reboot: the box is never destroyed by them, because the
# captures are the reason this script exists.
keep_and_die() {
    echo >&2
    echo "REFUSING: $1" >&2
    echo "          The instance is KEPT ($INSTANCE) and its disk is untouched." >&2
    echo "          Last polled window: $LOG_FILE" >&2
    echo "          Destroy it by hand when you have what you need:" >&2
    echo "            vastai destroy instance $INSTANCE -y" >&2
    echo "          It BILLS until you do." >&2
    exit 1
}

# The count is NOT taken from the local target list: the launch may have been a one-target canary,
# and the window we just read may have scrolled past some of its markers. The box states it when it
# boots ("REEMIT: N sealed"), and that statement is what the verifier is given.
EXPECTED=0

# ---- Pre-flight: is there anything on the box to re-emit? ----
# Read the box's log BEFORE restarting it. The bootstrap prints one `########## EMIT <target>
# (<id>)` line per sealed capture, so the markers are the box's own statement that a capture
# exists. Without them a restart would find nothing sealed and would FIT -- which is the one
# outcome this script exists to prevent.
echo "=== 1/4 reading the box's log (no reboot yet) ==="
PRE="$TMP_DIR/preflight.log"
if ! poll_logs "$PRE" "$TMP_DIR/preflight.err"; then
    echo "FATAL: could not read the instance's log:" >&2
    head -3 "$TMP_DIR/preflight.err" >&2
    exit 2
fi
EMIT_MARKERS="$(grep -ac '^########## EMIT ' "$PRE" 2>/dev/null || true)"
case "$EMIT_MARKERS" in ''|*[!0-9]*) EMIT_MARKERS=0 ;; esac
# ONE marker is enough, not one per target. This is the box we are recovering from: its window has
# scrolled past the payload, and the markers sit AHEAD of the payload, so requiring all of them
# would refuse on exactly the instance whose capture needs resending. A single marker proves the
# box sealed something; how much it sealed is the box's own sealed-directory check when it boots.
if [ "$EMIT_MARKERS" -lt 1 ]; then
    {
        echo "REFUSING: the box has nothing to re-emit."
        echo "  Looked for: an '########## EMIT <target> (<id>)' marker in"
        echo "              \`vastai logs $INSTANCE --tail $POLL_TAIL\` (found none), which is what"
        echo "              the bootstrap writes per SEALED capture, and the sealed run directories"
        echo "              results/*/capture.json on the box."
        echo "  Nothing was rebooted and nothing was spent. A launch that never sealed a capture"
        echo "  has to be fitted again; that is a new launch, not a re-emit."
    } >&2
    exit 2
fi
echo "    $EMIT_MARKERS EMIT marker(s) in the window; the box will state how many it sealed"

# ---- Reboot: re-runs the launch's onstart, which takes the re-emit path on this disk ----
echo "=== 2/4 rebooting $INSTANCE (the onstart re-runs; nothing is fitted) ==="
if ! vastai reboot instance "$INSTANCE"; then
    echo "FATAL: the reboot was refused. The instance is untouched and still holds the captures;" >&2
    echo "       retry, or read its log: vastai logs $INSTANCE --tail $POLL_TAIL" >&2
    exit 1
fi

# ---- Poll: merge chunks, and verify until the payload is complete ----
echo "=== 3/4 polling the log (ceiling ${POLL_MINUTES} min) ==="
WINDOW="$TMP_DIR/window.log"
RAW="$TMP_DIR/artifacts.raw"
: > "$LOG_FILE"
VERIFIED=0
EMPTY_STREAK=0
for i in $(seq 1 $(( POLL_MINUTES * 3 ))); do
    sleep "$POLL_SECONDS"
    if poll_logs "$WINDOW" "$TMP_DIR/poll.err"; then
        if [ -s "$WINDOW" ]; then
            # The LAST window, not an append of every poll: four captures emitted twice is tens of
            # megabytes per poll, and this machine also carries the repo's data. 8,000 lines keeps
            # the newest evidence without filling the disk.
            cp "$WINDOW" "$LOG_FILE" 2>/dev/null || true
            EMPTY_STREAK=0

            # The box says what it is doing, and either answer can be final. Taken from the box
            # rather than from the local target list because the log window may have scrolled past
            # some markers, and a canary launch is one target rather than four.
            if grep -aq '^########## PARTIAL:' "$WINDOW"; then
                keep_and_die "the box is only PARTLY sealed, so it is fitting the launch again.
          That is a paid re-fit, not a re-emit; this script does not wait it out."
            fi
            if grep -aq '^--- installing deps' "$WINDOW"; then
                keep_and_die "the box started its dependency install, so its checkout predates the
          re-emit path (or it is not fully sealed) and it is fitting again. Nothing was recovered."
            fi
            BOX_SEALED="$(sed -n 's/^########## REEMIT: \([0-9][0-9]*\) sealed.*/\1/p' "$WINDOW" | tail -1)"
            [ -n "$BOX_SEALED" ] && EXPECTED="$BOX_SEALED"

            python3 "$SCRIPT_DIR/collect_chunks.py" merge --window "$WINDOW" --state "$CHUNKS" >/dev/null 2>&1 || true
            if [ "$EXPECTED" -gt 0 ] && python3 "$SCRIPT_DIR/collect_chunks.py" assemble --state "$CHUNKS" --out "$RAW" >/dev/null 2>&1; then
                SEED_ARGS=()
                [ -n "$SEEDS" ] && SEED_ARGS=(--expect-seeds "$SEEDS")
                if python3 "$SCRIPT_DIR/verify_artifacts.py" --raw "$RAW" \
                        --dest "$REPO_DIR/results" --expect-captures "$EXPECTED" \
                        "${SEED_ARGS[@]+"${SEED_ARGS[@]}"}"; then
                    VERIFIED=1
                    break
                fi
            fi
        else
            EMPTY_STREAK=$(( EMPTY_STREAK + 1 ))
            if [ "$EMPTY_STREAK" -eq 3 ]; then
                echo "  WARNING: log capture empty 3x -- is the box rebooting?" >&2
            fi
        fi
    fi
    PROG="$(grep -aE '^##########|__ARTIFACTS_INFO__' "$WINDOW" 2>/dev/null | tail -1)"
    [ -n "$PROG" ] && echo "  [$i] $PROG"
done

# ---- Outcome ----
if [ "$VERIFIED" -ne 1 ]; then
    keep_and_die "the re-emit did not verify within ${POLL_MINUTES} min.
          Retry with a bigger --poll-minutes; the box still holds the captures."
fi

echo "=== 4/4 verified -- captures restored into $REPO_DIR/results ==="
if [ "$KEEP" -eq 1 ]; then
    echo "--keep: NOT destroying $INSTANCE"
    echo "    destroy manually:  vastai destroy instance $INSTANCE -y"
    echo "    (the instance is BILLING until you do)"
else
    if vastai destroy instance "$INSTANCE" -y >/dev/null 2>&1; then
        echo "released instance $INSTANCE"
    else
        echo "WARNING: the destroy failed; release it by hand:" >&2
        echo "           vastai destroy instance $INSTANCE -y" >&2
    fi
fi
exit 0
