#!/usr/bin/env bash
# watch_run.sh — what a paid launch is doing, in one pane.
#
#   bash scripts/gpu_helpers/watch_run.sh [log] [--interval N] [--once]
#
# Reads only: it never creates, stops or destroys anything. It answers four questions and
# no others — is the batch alive, is credit moving, is more than one instance billing, and
# how far through is it.
#
#   log         the launcher's log; default is the newest /tmp/batch*.log or /tmp/probe*.log
#   --interval  seconds between redraws (default 30)
#   --once      print one frame and exit, for a script or a test
#
# A counter that stands still is usually the rung, not a hang: a 30-epoch fit takes ~155s on
# 10,000 rows, so the arm count moves about once every two and a half minutes. The age of the
# last write is the signal to trust.

set -uo pipefail

export PATH="$HOME/.local/bin:$PATH"

INTERVAL=30
ONCE=0
LOG=""
while [ $# -gt 0 ]; do
    case "$1" in
        --interval) INTERVAL="${2:-30}"; shift 2 ;;
        --once)     ONCE=1; shift ;;
        -h|--help)  sed -n '2,18p' "$0"; exit 0 ;;
        *)          LOG="$1"; shift ;;
    esac
done

if [ -z "$LOG" ]; then
    # shellcheck disable=SC2012  # names here are controlled (batch*.log, probe*.log)
    LOG="$(ls -t /tmp/batch*.log /tmp/probe*.log 2>/dev/null | head -1)"
fi

credit() {
    python3 - <<'PY'
import json, subprocess
try:
    out = subprocess.run(["vastai", "show", "user", "--raw"],
                         capture_output=True, text=True, timeout=20)
    print(round(json.loads(out.stdout).get("credit", 0.0), 4))
except Exception:
    print("?  (vastai not answering)")
PY
}

instances() {
    python3 - <<'PY'
import json, subprocess
try:
    out = subprocess.run(["vastai", "show", "instances", "--raw"],
                         capture_output=True, text=True, timeout=20)
    data = json.loads(out.stdout)
    rows = data if isinstance(data, list) else data.get("instances", [])
    mine = [i for i in rows if (i.get("label") or "").startswith("tabpfn-pilot")]
    if not mine:
        print("  none billing")
    for i in mine:
        print(f"  {i.get('id')}  {i.get('actual_status')}  {i.get('gpu_name')}  {i.get('label')}")
except Exception:
    print("  ?  (vastai not answering)")
PY
}

last_write() {
    python3 - "$1" <<'PY'
import os, sys, time
try:
    mtime = os.path.getmtime(sys.argv[1])
except OSError:
    print("-")
    raise SystemExit
print(f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))}  ({int(time.time() - mtime)}s ago)")
PY
}

frame() {
    date
    printf -- '--- credit (USD): %s\n' "$(credit)"
    printf -- '--- instances (one while running, none between):\n'
    instances
    if [ -n "$LOG" ] && [ -f "$LOG" ]; then
        printf -- '--- following: %s\n' "$LOG"
        # Result lines are one per arm x seed, but the poll repeats some, so treat the count as
        # indicative. The authoritative total arrives at the end as
        # "VERIFY predictions verified=N", and N is the number to reconcile against.
        printf -- '--- arms (launcher): %s\n' \
            "$(sed -n 's/.*arms=\([^ ]*\) transport=.*/\1/p' "$LOG" | head -1)"
        printf -- '--- result lines: %s (one per arm x seed, some repeated by the log poll)\n' \
            "$(grep -c 'logloss=' "$LOG" || true)"
        printf -- '--- last write: %s\n' "$(last_write "$LOG")"
        printf -- '--- last line: %s\n' "$(tail -1 "$LOG")"
    else
        printf -- '--- no launcher log found; pass one, or start a launch\n'
        printf -- '    expected at /tmp/batch*.log or /tmp/probe*.log\n'
    fi
}

if [ "$ONCE" -eq 1 ]; then
    frame
    exit 0
fi

while true; do
    clear
    frame
    sleep "$INTERVAL"
done
