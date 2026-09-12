#!/bin/bash
# Destroy stray 'tabpfn-pilot' instances.
#
#   bash scripts/gpu_helpers/vast_watchdog.sh [--max-age-min N] [--dry-run] [--all-labels]
#
# WHY THIS EXISTS: vast_run.sh destroys its instance in an EXIT trap, but a trap
# only fires on a normal exit. SIGKILL, a closed terminal, a sleeping laptop, or
# a crashed shell skip it entirely -- and a leaked instance bills storage for
# every second it exists, even when stopped. Vast's own docs are explicit:
# "Stopping an instance does not avoid storage costs" and instances are only
# *stopped* (not destroyed) when your balance hits zero, so a zero balance is
# not a backstop. This is the out-of-band control that does not depend on the
# run process surviving.
#
# Intended to run from cron every 5 minutes:
#   */5 * * * * /bin/bash <repo>/scripts/gpu_helpers/vast_watchdog.sh >> /tmp/vast_watchdog.log 2>&1
#
# Safety: only touches instances carrying the pilot's label, and refuses to act
# unless it can read an age for them (unknown age => report only, never destroy).

set -uo pipefail

command -v vastai >/dev/null 2>&1 || \
    export PATH="$HOME/.local/share/uv/tools/vastai/bin:$PATH"

# DO NOT export VAST_API_KEY here -- measured, and it breaks auth.
# Supplying the key explicitly (env var OR --api-key) returns
#   401 "requires you to have logged in using Two Factor Authentication"
# even when the value is byte-identical to the CLI's own config file (verified by
# sha256), while letting the CLI read that file succeeds. The 2FA session is bound
# to the key the CLI loads from its config file, so an explicit key is a different
# auth context with no session.
# Consequence: the keychain CANNOT be the single store for the Vast key. That file
# is the CLI's store; keep it at mode 600.

LABEL="${LABEL:-tabpfn-pilot}"
MAX_AGE_MIN="${MAX_AGE_MIN:-90}"
DRY=0

while [ $# -gt 0 ]; do
    case "$1" in
        --max-age-min) MAX_AGE_MIN="$2"; shift 2 ;;
        --dry-run)     DRY=1; shift ;;
        --label)       LABEL="$2"; shift 2 ;;
        -h|--help)     sed -n '2,20p' "$0"; exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done

STAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Distinguish "cannot authenticate" from "nothing to do" -- and say so loudly.
# Previously both paths were quiet, so an inert guard was indistinguishable from a
# healthy one in the log. A guard you only *believe* is running is worse than none.
AUTH_OUT="$(vastai show user --raw 2>&1 || true)"
if printf '%s' "$AUTH_OUT" | grep -qiE '"error"[[:space:]]*:[[:space:]]*true|two.factor|401|Authorization Error'; then
    echo "$STAMP !! WATCHDOG UNAUTHENTICATED -- NO LEAK PROTECTION IS ACTIVE"
    echo "$STAMP !!   $(printf '%s' "$AUTH_OUT" | tr '\n' ' ' | cut -c1-140)"
    echo "$STAMP !!   refresh the session:  bash scripts/gpu_helpers/vast_login.sh"
    exit 0
fi

vastai show instances --raw 2>/dev/null > /tmp/vast_watchdog_instances.json || {
    echo "$STAMP could not list instances -- skipping"
    exit 0
}

# Emit: <id>|ARGS|reason   where ARGS is DESTROY or REPORT
python3 - "$LABEL" "$MAX_AGE_MIN" "$STAMP" "$DRY" <<'PY' > /tmp/vast_watchdog_plan.txt
import json, sys, time

label, max_age_min, stamp, dry = sys.argv[1], float(sys.argv[2]), sys.argv[3], sys.argv[4] == "1"

try:
    d = json.load(open("/tmp/vast_watchdog_instances.json"))
except Exception:
    print(f"{stamp} unreadable instance list -- skipping")
    raise SystemExit
insts = d if isinstance(d, list) else d.get("instances", [])

mine = [i for i in insts if (i.get("label") or "") == label]
if not mine:
    print(f"{stamp} clean: no '{label}' instances")
    raise SystemExit

now = time.time()
for i in mine:
    iid = i.get("id")
    # Age from the earliest usable timestamp; several field names appear across
    # API versions, so accept any. No age => report only, never destroy.
    age_min = None
    for k in ("start_date", "created_at", "last_updated", "duration"):
        v = i.get(k)
        if isinstance(v, (int, float)) and v > 0:
            cand = (now - v) / 60.0 if v > 1e6 else v
            if 0 <= cand < 60 * 24 * 30:
                age_min = cand if age_min is None else min(age_min, cand)
    status = i.get("actual_status")
    if age_min is None:
        print(f"{stamp} REPORT id={iid} status={status} age=UNKNOWN -- not destroyed (age unreadable)")
        continue
    if age_min >= max_age_min:
        verb = "WOULD DESTROY" if dry else "DESTROY"
        print(f"{stamp} {verb} id={iid} status={status} age={age_min:.1f}min >= {max_age_min:g}min")
        print(f"DESTROY {iid}")
    else:
        print(f"{stamp} keep id={iid} status={status} age={age_min:.1f}min < {max_age_min:g}min")
PY

cat /tmp/vast_watchdog_plan.txt

grep -E '^DESTROY ' /tmp/vast_watchdog_plan.txt | while read -r _ iid; do
    [ -z "$iid" ] && continue
    # -y is mandatory: without it destroy prompts and aborts non-interactively.
    if vastai destroy instance "$iid" -y >/dev/null 2>&1; then
        echo "$STAMP destroyed $iid"
    else
        echo "$STAMP FAILED to destroy $iid -- destroy manually: vastai destroy instance $iid -y"
    fi
done

exit 0
