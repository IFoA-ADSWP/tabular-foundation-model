#!/usr/bin/env bash
# Re-emit a kept instance's finished captures WITHOUT re-fitting (#568).
#
# WHY. The two halves of a paid fair test fail independently. On 2026-11-21 the `severity_french`
# fits finished and sealed on the box, and the launcher died of local fork exhaustion before it
# could pull. The instance was kept, but no later poll could order the payload: the declaration
# (`__ARTIFACTS_INFO__`) had scrolled out of the log window, so the capture could not be
# hash-verified and $1.26 bought nothing.
#
# THE CHANNEL. There is no exec channel -- `vastai execute` runs only ls/rm/du, and the team
# context refuses SSH keys. The instance LIFECYCLE is one: a restart re-runs the launch's own
# onstart against the same disk. Measured 2026-11-21 on a $0.0285/hr probe: four reboots, a
# /workspace counter reading 1..4, and a container log that accumulates across restarts. The
# bootstrap's re-emit guard (section 2b) is what turns the restart into an emit instead of a fit.
#
# WHAT IT REFUSES. It reboots only when the tail of the box's log carries evidence that a payload
# was emitted (`__ART__`, `__ART_CHUNK__`, `__ARTIFACTS_INFO__`/`__ARTIFACTS_END__`, or an `EMIT`
# marker). The declaration and the EMIT markers sit at the HEAD of a payload of ~150k log lines, so
# a late poller never sees them -- the chunk lines and the end marker are what survives.
#
# A LIMIT WORTH KNOWING. Only a box whose ONSTART already contains section 2b can be recovered.
# The onstart payload is frozen into the instance at create, so the box that motivated this ticket
# cannot use it; a reboot of such a box starts a full paid launch, which this script detects and
# stops (it destroys the box unless --keep-fitting).
#
# Usage:
#   reemit_captures.sh --instance ID [--seeds 1001,1002] [--poll-minutes N] [--keep-fitting] [--yes]
#
# It never creates an instance, never selects an offer, and never runs a fit.
set -uo pipefail
umask 077

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

INSTANCE=""
SEEDS=""
POLL_MINUTES=""
POLL_TAIL="${POLL_TAIL:-8000}"
# A knob so a mock-driven test does not pay ten seconds per poll; real runs use the launcher's 10 s.
POLL_SECONDS="${REEMIT_POLL_SECONDS:-10}"
KEEP=0
KEEP_FITTING=0
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
        --keep-fitting) KEEP_FITTING=1; shift ;;
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
RECORD="$OUTDIR/reemit_${INSTANCE}_${STAMP}.json"

# The chunk accumulator PERSISTS per instance. A transfer that outruns the ceiling can then be
# resumed by running the command again -- the chunks already merged are not thrown away, which is
# the difference between a retry and a second full emission.
STATE_DIR="$OUTDIR/reemit-$INSTANCE"
CHUNKS="$STATE_DIR/chunks"
mkdir -p "$CHUNKS" || { echo "FATAL: cannot write $CHUNKS" >&2; exit 2; }

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/tfm-reemit.XXXXXX")" || exit 2
trap 'rm -rf "$TMP_DIR"' EXIT

# Bounded poll, the same shape as the launcher's: one `vastai logs` call must not consume the whole
# ceiling. The launcher uses 45 s; this is longer because a re-emit's window also carries a reboot.
POLL_TIMEOUT="${POLL_TIMEOUT:-90}"
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

record_run() {
    python3 - "$RECORD" "$INSTANCE" "${LABEL:-}" "${DPH:-0}" "$T_START" "${RESTORED:-}" <<'PY'
import json, os, sys
record, instance, label, dph, started, restored = sys.argv[1:7]
wall_minutes = round((__import__("time").time() - float(started)) / 60.0, 2)
rec = {
    "instance_id": int(instance),
    "label": label or None,
    "dph_total": float(dph or 0),
    "wall_minutes": wall_minutes,
    "est_cost_usd": round(wall_minutes / 60.0 * float(dph or 0), 4),
    "restored": [r for r in restored.split() if r],
}
with open(record, "w") as f:
    json.dump(rec, f, indent=2)
print(f"[cost] re-emit {wall_minutes} min x ${dph or 0}/hr -> {record}")
PY
}

# One exit path for every failure after the reboot. The box is NOT destroyed -- except when it has
# started fitting, where leaving it running bills for a second full launch.
keep_and_die() {
    record_run
    echo >&2
    echo "REFUSING: $1" >&2
    echo "          The instance is KEPT ($INSTANCE) and its disk is untouched." >&2
    echo "          Last polled window: $LOG_FILE" >&2
    echo "          Chunks merged so far: $CHUNKS (a retry resumes from them)" >&2
    echo "          Destroy it by hand when you have what you need:" >&2
    echo "            vastai destroy instance $INSTANCE -y" >&2
    echo "          It BILLS until you do." >&2
    exit 1
}

fit_started() {
    record_run
    if [ "$KEEP_FITTING" -eq 1 ]; then
        echo >&2
        echo "REFUSING: $1" >&2
        echo "          --keep-fitting: leaving the box running. It is now executing a FULL launch" >&2
        echo "          (four targets, ~105 minutes at the measured rate) and will keep billing." >&2
        echo "            vastai destroy instance $INSTANCE -y    # to stop it" >&2
        exit 1
    fi
    echo >&2
    echo "REFUSING: $1" >&2
    echo "          Destroying the box to stop a paid re-fit; its sealed captures go with it." >&2
    if vastai destroy instance "$INSTANCE" -y >/dev/null 2>&1; then
        echo "          released instance $INSTANCE" >&2
    else
        echo "          the destroy FAILED -- release it by hand: vastai destroy instance $INSTANCE -y" >&2
    fi
    exit 1
}

# ---- 0. Is this the box a launch kept? ----
# One API call before any money is spent. A wrong-but-real id whose log happens to carry a payload
# line would otherwise be rebooted, and destroyed on success, for somebody else's work.
echo "=== 0/4 checking instance $INSTANCE ==="
if ! vastai show instance "$INSTANCE" --raw > "$TMP_DIR/instance.json" 2>"$TMP_DIR/show.err"; then
    echo "FATAL: no readable instance $INSTANCE:" >&2
    head -3 "$TMP_DIR/show.err" >&2
    exit 2
fi
LABEL="$(python3 -c 'import json,sys
try: print(json.load(open(sys.argv[1])).get("label") or "")
except Exception: print("")' "$TMP_DIR/instance.json")"
DPH="$(python3 -c 'import json,sys
try: print(json.load(open(sys.argv[1])).get("dph_total") or 0)
except Exception: print(0)' "$TMP_DIR/instance.json")"
case "$LABEL" in
    ""|tabpfn-pilot*) ;;
    *) echo "REFUSING: instance $INSTANCE is labelled '$LABEL', not a launch's tabpfn-pilot-* box." >&2
       echo "          Re-emit only attaches to the box a launch kept, and it reboots and destroys it." >&2
       exit 2 ;;
esac
echo "    label=${LABEL:-<none>} dph=\$${DPH}/hr"

T_START="$(date -u +%s)"
# The CEILING follows the number of targets, like the launcher's, because a paced transfer is
# ~18 min per target and the shipped settings emit each chunk twice over two passes. The COUNT the
# verifier is given still comes from the box (below): a canary launch is one target, not four.
TARGET_COUNT=4
if [ -n "${TFM_FAIRTEST_TARGETS:-}" ]; then
    TARGET_COUNT=0
    for _t in $TFM_FAIRTEST_TARGETS; do TARGET_COUNT=$(( TARGET_COUNT + 1 )); done
fi
POLL_GIVEN=0
[ -n "$POLL_MINUTES" ] && POLL_GIVEN=1
if [ -z "$POLL_MINUTES" ]; then
    POLL_MINUTES=$(( 15 + 30 * TARGET_COUNT ))
fi

# ---- 1. Pre-flight: did this box ever get a payload onto the wire? ----
# The tail, not the head: `__ARTIFACTS_INFO__` and the EMIT markers are the FIRST lines of a
# ~150k-line emission, so a recovery from a scrolled window can only ever see chunk lines, the end
# marker, or a later pass's header. Measured 2026-11-21: one 9.6 MB capture produced 109,897 lines
# and its last 8,000 contained no INFO line and no EMIT marker.
echo "=== 1/4 reading the box's log (no reboot yet) ==="
PRE="$TMP_DIR/preflight.log"
if ! poll_logs "$PRE" "$TMP_DIR/preflight.err"; then
    echo "FATAL: could not read the instance's log:" >&2
    head -3 "$TMP_DIR/preflight.err" >&2
    exit 2
fi
if ! grep -aqE '^__ART__|^__ART_CHUNK__|^__ARTIFACTS_(INFO|END)__|^########## EMIT ' "$PRE"; then
    {
        echo "REFUSING: the box has nothing to re-emit."
        echo "  Looked for: a payload line in the last $POLL_TAIL lines of"
        echo "              \`vastai logs $INSTANCE --tail $POLL_TAIL\` -- __ART__, __ART_CHUNK__,"
        echo "              __ARTIFACTS_INFO__/__ARTIFACTS_END__, or an '########## EMIT' marker. The"
        echo "              launch's results/<run id>/capture.json is what would be sent, but this"
        echo "              driver has no way to read the box's disk (no exec channel)."
        echo "  Nothing was rebooted and nothing was spent. A launch that never emitted a capture"
        echo "  has to be fitted again; that is a new launch, not a re-emit."
    } >&2
    exit 2
fi
echo "    the tail carries payload evidence -- there is something to resend"

# The newest boot marker in a log. The container log accumulates across restarts, so this is how
# the driver tells "this boot says PARTIAL" from "the previous boot said it".
box_check_ts() {
    sed -n 's/^########## REEMIT CHECK \([0-9][0-9]*\).*/\1/p' "$1" 2>/dev/null | tail -1
}
PRE_CHECK="$(box_check_ts "$PRE")"

# ---- 2. Reboot: re-runs the launch's onstart, which takes the re-emit path on this disk ----
echo "=== 2/4 rebooting $INSTANCE (the onstart re-runs; nothing is fitted) ==="
if ! vastai reboot instance "$INSTANCE"; then
    echo "FATAL: the reboot was refused. The instance is untouched and still holds the captures;" >&2
    echo "       retry, or read its log: vastai logs $INSTANCE --tail $POLL_TAIL" >&2
    exit 1
fi

# ---- 3. Poll: merge chunks, and verify until the payload is complete ----
echo "=== 3/4 polling the log (ceiling ${POLL_MINUTES} min) ==="
WINDOW="$TMP_DIR/window.log"
RAW="$TMP_DIR/artifacts.raw"
RESTORE="$TMP_DIR/restore"
mkdir -p "$RESTORE"
: > "$LOG_FILE"
VERIFIED=0
RESTORED=""
EMPTY_STREAK=0
EXPECTED=0
DEADLINE=$(( T_START + POLL_MINUTES * 60 ))
while [ "$(date -u +%s)" -lt "$DEADLINE" ]; do
    sleep "$POLL_SECONDS"
    [ -s "$WINDOW" ] || : > "$WINDOW"
    if poll_logs "$WINDOW" "$TMP_DIR/poll.err"; then
        if [ -s "$WINDOW" ]; then
            # The LAST window, not an append of every poll: four captures emitted twice is tens of
            # megabytes per poll, and this machine also carries the repo's data.
            cp "$WINDOW" "$LOG_FILE" 2>/dev/null || true
            EMPTY_STREAK=0

            # Only text from THIS boot counts. The log accumulates, so a stale PARTIAL or
            # dependency-install line would otherwise stop a recovery that is going fine.
            NOW_CHECK="$(box_check_ts "$WINDOW")"
            THIS_BOOT=0
            if [ -n "$NOW_CHECK" ] && { [ -z "$PRE_CHECK" ] || [ "$NOW_CHECK" -gt "$PRE_CHECK" ]; }; then
                THIS_BOOT=1
            fi
            CURRENT=""
            if [ "$THIS_BOOT" -eq 1 ]; then
                CURRENT="$(awk '/^########## REEMIT CHECK /{buf=""} {buf=buf $0 "\n"} END{printf "%s", buf}' "$WINDOW")"
            fi
            case "$CURRENT" in
                *"########## PARTIAL:"*)
                    fit_started "the box is only PARTLY sealed, so it is fitting the launch again.
          That is a paid re-fit, not a re-emit; this script does not wait it out." ;;
                *"--- installing deps"*)
                    fit_started "the box started its dependency install, so its onstart predates the
          re-emit path and it is running a full launch. Nothing was recovered." ;;
                *"########## REEMIT INCOMPLETE"*)
                    keep_and_die "the box could not re-emit a capture it has. Retrying the same box
          would fail the same way; inspect the window above before destroying it." ;;
            esac
            BOX_SEALED="$(printf '%s' "$CURRENT" | sed -n 's/^########## REEMIT: \([0-9][0-9]*\) sealed.*/\1/p' | tail -1)"
            [ -n "$BOX_SEALED" ] && EXPECTED="$BOX_SEALED"
            # The transfer is paced, so its time follows the chunk count the box declares (#701).
            # Without this the ceiling was sized from the target count: 45 minutes for a capture
            # measured at 182 chunks and ~2 hours for its first pass.
            DECLARED_CHUNKS="$(printf '%s' "$WINDOW" | grep -ao 'chunks=[0-9][0-9]*' | head -1 | cut -d= -f2)"
            if [ -n "$DECLARED_CHUNKS" ] && [ "$POLL_GIVEN" -eq 0 ]; then
                IMPLIED="$(python3 "$SCRIPT_DIR/transfer_minutes.py" --chunks "$DECLARED_CHUNKS" \
                    --pause "${TFM_CHUNK_PAUSE:-20}" --repeat "${TFM_CHUNK_REPEAT:-2}" \
                    --passes "${TFM_CHUNK_PASSES:-2}" 2>/dev/null)"
                if [ -n "$IMPLIED" ] && [ "$(( IMPLIED + 15 ))" -gt "$POLL_MINUTES" ]; then
                    POLL_MINUTES=$(( IMPLIED + 15 ))
                    DEADLINE=$(( T_START + POLL_MINUTES * 60 ))
                    echo "  the box declares $DECLARED_CHUNKS chunks: ~${IMPLIED} min to send them" >&2
                    echo "  once at the shipped pacing; ceiling extended to ${POLL_MINUTES} min" >&2
                fi
            fi

            python3 "$SCRIPT_DIR/collect_chunks.py" merge --window "$WINDOW" --state "$CHUNKS" >/dev/null 2>&1 || true
            if [ "$EXPECTED" -gt 0 ] && python3 "$SCRIPT_DIR/collect_chunks.py" assemble --state "$CHUNKS" --out "$RAW" >/dev/null 2>&1; then
                SEED_ARGS=()
                [ -n "$SEEDS" ] && SEED_ARGS=(--expect-seeds "$SEEDS")
                # Restore into a scratch tree: a partial or refused restore must not write into the
                # tracked results/ tree that `check.sh evidence` compares.
                if python3 "$SCRIPT_DIR/verify_artifacts.py" --raw "$RAW" \
                        --dest "$RESTORE" --expect-captures "$EXPECTED" \
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
    [ -n "$PROG" ] && echo "  [$PROG]" 
done

# ---- 4. Outcome ----
if [ "$VERIFIED" -ne 1 ]; then
    keep_and_die "the re-emit did not verify within ${POLL_MINUTES} min.
          Retry with a bigger --poll-minutes; the merged chunks are kept and a retry resumes."
fi

mkdir -p "$REPO_DIR/results"
for _dir in "$RESTORE"/*/; do
    [ -d "$_dir" ] || continue
    _id="$(basename "$_dir")"
    rm -rf "$REPO_DIR/results/$_id"
    mv "$_dir" "$REPO_DIR/results/$_id" || {
        echo "FATAL: verified, but moving $_id into results/ failed" >&2
        exit 1
    }
    RESTORED="$RESTORED $_id"
done
# The verifier said success; if it wrote nothing, that is a contradiction to stop on, not a reason
# to delete the chunks and the box.
if [ -z "$RESTORED" ]; then
    keep_and_die "the verifier reported success but no capture reached results/. Nothing was moved."
fi
rm -rf "$CHUNKS"

echo "=== 4/4 verified -- captures restored into $REPO_DIR/results ==="
echo "    restored:$RESTORED"
[ -z "$SEEDS" ] && echo "    NOTE: --seeds was not given, so the seed range was verified against the captures, not against the launch."
record_run

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
