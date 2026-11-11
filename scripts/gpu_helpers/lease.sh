#!/usr/bin/env bash
# lease.sh — one owner for a paid instance's record and release (#325).
#
# Sourced by vast_run.sh. The launcher mints the id before provisioning, writes the
# record before the instance exists, and calls release from its one EXIT trap and from
# the retry path. The record is the artifact a later process (or a test) reads; the
# return value is an outcome, never a boolean.
#
# Outcomes: released · already_gone · failed:<reason>.
# A failed release keeps the instance id in hand and prints a one-line destroy command.

# A retry re-execs with these two in the environment; preserve them. Everything else is
# derived by lease_begin.
LEASE_LAUNCH_ID="${LEASE_LAUNCH_ID:-}"
LEASE_ATTEMPT="${LEASE_ATTEMPT:-1}"
LEASE_INSTANCE_ID=""
LEASE_LABEL=""
LEASE_IMAGE=""
LEASE_FILE=""
LEASE_STATE="idle"

# Record fields beyond launch/instance/state are read by adoption (#327) and the
# watchdog (#328); until then they are written for those consumers, not this slice.
lease_write() { # lease_write <state> <outcome> <reason>
    local state="$1" outcome="${2:-}" reason="${3:-}"
    [ -n "$LEASE_FILE" ] || return 1
    mkdir -p "$(dirname "$LEASE_FILE")" || return 1
    python3 - "$LEASE_FILE" "$LEASE_LAUNCH_ID" "$LEASE_INSTANCE_ID" "$LEASE_LABEL" \
        "$LEASE_IMAGE" "$state" "$outcome" "$reason" "${RUN_STAMP:-}" "$LEASE_ATTEMPT" <<'PY'
import json
import os
import sys
import time

(path, launch, instance, label, image, state, outcome, reason, run_id,
 attempt_no) = sys.argv[1:11]
now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
try:
    with open(path) as fh:
        record = json.load(fh)
except (FileNotFoundError, json.JSONDecodeError):
    record = {}
record.update({
    "schema_version": 1,
    "launch_id": launch,
    "instance_id": instance,
    "label": label,
    "image": image,
    "state": state,
    "outcome": outcome or None,
    "reason": reason or None,
    "run_id": run_id,
    "updated_at": now,
})
record.setdefault("created_at", now)
attempts = record.setdefault("attempts", [])
attempt = next((a for a in attempts if a.get("attempt") == int(attempt_no)), None)
if attempt is None:
    attempt = {"attempt": int(attempt_no), "instance_id": "", "state": "acquiring",
               "started_at": now}
    attempts.append(attempt)
attempt.update({"instance_id": instance, "state": state, "outcome": outcome or None,
                "reason": reason or None, "updated_at": now})
if state == "acquired":
    attempt.setdefault("acquired_at", now)
if state in ("released", "failed"):
    attempt["ended_at"] = now
if state == "acquired":
    record.setdefault("acquired_at", now)
if state in ("released", "failed"):
    record["released_at"] = now
tmp = path + ".tmp"
with open(tmp, "w") as fh:
    fh.write(json.dumps(record, indent=2) + "\n")
os.replace(tmp, path)
PY
    chmod 600 "$LEASE_FILE" 2>/dev/null || true
}

lease_begin() { # lease_begin <outdir> <image>
    local outdir="$1"
    LEASE_IMAGE="$2"
    if [ -n "${LEASE_LAUNCH_ID:-}" ] && [ -f "$outdir/leases/$LEASE_LAUNCH_ID.json" ]; then
        # A retry re-execs with the same id; append an attempt to the existing record.
        LEASE_ATTEMPT="${LEASE_ATTEMPT:-1}"
        LEASE_LABEL="tabpfn-pilot-$LEASE_LAUNCH_ID"
        LEASE_FILE="$outdir/leases/$LEASE_LAUNCH_ID.json"
        LEASE_INSTANCE_ID=""
        LEASE_STATE="acquiring"
        lease_write acquiring "" "" || return 1
        export LEASE_LAUNCH_ID LEASE_LABEL LEASE_FILE LEASE_ATTEMPT
        echo "[lease] launch=$LEASE_LAUNCH_ID attempt=$LEASE_ATTEMPT (retry)"
        return 0
    fi
    LEASE_LAUNCH_ID="$(date -u +%Y%m%dT%H%M%SZ)-$(python3 -c 'import secrets; print(secrets.token_hex(3))')"
    LEASE_LABEL="tabpfn-pilot-$LEASE_LAUNCH_ID"
    LEASE_FILE="$outdir/leases/$LEASE_LAUNCH_ID.json"
    LEASE_ATTEMPT=1
    LEASE_INSTANCE_ID=""
    LEASE_STATE="acquiring"
    lease_write acquiring "" "" || return 1
    export LEASE_LAUNCH_ID LEASE_LABEL LEASE_FILE LEASE_ATTEMPT
    echo "[lease] launch=$LEASE_LAUNCH_ID attempt=1 label=$LEASE_LABEL"
}

lease_acquired() { # lease_acquired <instance id>
    LEASE_INSTANCE_ID="$1"
    LEASE_STATE="acquired"
    lease_write acquired "" ""
}

lease_keep() { # the operator asked to keep the instance; it is still billing
    LEASE_STATE="acquired"
    lease_write acquired kept "kept by --keep"
}

lease_release() { # lease_release [reason]
    local reason="${1:-}"
    if [ "$LEASE_STATE" = "released" ]; then
        echo "already_gone"
        return 0
    fi
    if [ -z "$LEASE_INSTANCE_ID" ]; then
        LEASE_STATE="released"
        lease_write released "already_gone" "$reason" || true
        echo "already_gone"
        return 0
    fi
    echo "--- releasing instance $LEASE_INSTANCE_ID ---"
    # -y is required. Without it the CLI asks for confirmation, which in a
    # non-interactive script reads EOF, aborts, and leaves the instance running and
    # billing. Verified: 'vastai destroy instance' has '-y, --yes  Skip confirmation'.
    local destroy_out rc
    destroy_out="$(vastai destroy instance "$LEASE_INSTANCE_ID" -y 2>&1)"
    rc=$?
    printf '%s\n' "$destroy_out"
    if [ "$rc" -eq 0 ]; then
        LEASE_STATE="released"
        lease_write released "released" "$reason" || true
        LEASE_INSTANCE_ID=""
        echo "released"
        return 0
    fi
    # "No such container" means it is already gone; treating that as failure would print
    # a false STILL BILLING and exit non-zero for a released instance.
    if printf '%s' "$destroy_out" | grep -Eqi 'no such container|not found|does not exist'; then
        LEASE_STATE="released"
        lease_write released "already_gone" "$reason" || true
        LEASE_INSTANCE_ID=""
        echo "already_gone"
        return 0
    fi
    LEASE_STATE="failed"
    lease_write failed "failed:destroy" "$reason" || true
    echo "WARNING: DESTROY FAILED -- $LEASE_INSTANCE_ID is STILL BILLING." >&2
    echo "         launch:   $LEASE_LAUNCH_ID" >&2
    echo "         instance: $LEASE_INSTANCE_ID" >&2
    echo "         run:      vastai destroy instance $LEASE_INSTANCE_ID -y" >&2
    echo "failed:destroy"
    return 1
}

lease_state() {
    [ -n "$LEASE_FILE" ] && [ -f "$LEASE_FILE" ] || return 1
    python3 - "$LEASE_FILE" <<'PY'
import json
import sys
with open(sys.argv[1]) as fh:
    print(json.load(fh).get("state", ""))
PY
}
