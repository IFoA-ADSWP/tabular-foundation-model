#!/bin/bash
# End-to-end pilot run on Vast.ai: pick offer -> create -> bootstrap -> pull -> destroy.
#
#   bash scripts/gpu_helpers/vast_run.sh [options]
#
# Options:
#   --offer-id N     use a specific offer (skips selection)
#   --query 'Q'      extra offer search filters
#   --pick HOW       value | cheapest | fastest      (default: value = dlperf/$)
#   --max-dph N      hard price ceiling in $/hr      (default 0.60)
#   --min-vram N     minimum VRAM in GB              (default 23)
#   --gpu-allow L    comma list of allowed gpu_name  (default: modern-only list)
#   --disk N         local disk GB                   (default 60)
#   --arms LIST      arms to run                     (default all four)
#   --image NAME     override the docker image
#   --transport T    execute | ssh                   (default: execute)
#   --keep           do NOT destroy on exit
#   --yes            skip the confirmation prompt
#
# WHY `execute` AND NOT SSH: this account is in a TEAM context, and Vast
# refuses account-level SSH keys there --
#   "Team SSH keys are not supported. SSH keys can only be created in personal
#    context."
# `vastai execute <id> '<cmd>'` runs commands over the API, so it needs no
# registered key at all. SSH is kept as an opt-in for when a key exists.
#
# WHY AN ARCHITECTURE WHITELIST: ranking purely by dlperf/$ favours ancient
# cheap GPUs. `cheapest` selected a Tesla V100; Volta/sm_70 is dropped by
# recent PyTorch builds, so the run would fail after the instance was paid for.
#
# Cost safety: a trap destroys the instance on ANY exit unless --keep.

set -uo pipefail

# Temp files below (/tmp/vast_*.json, /tmp/vast_run_out.txt, artifacts) are created
# world-readable by default. This run handles a licence token and experiment data, so
# keep everything owner-only. The token itself is never written to disk here -- it is
# only ever exported into the remote command.
umask 077

# Only add the uv-tool location if vastai is not already resolvable. Prepending
# unconditionally shadows any test double, which meant a mocked test run
# invoked the REAL CLI and created real, billing instances.
command -v vastai >/dev/null 2>&1 || \
    export PATH="$HOME/.local/share/uv/tools/vastai/bin:$PATH"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

DEFAULT_QUERY='num_gpus=1 gpu_ram>=23 cpu_ram>=32 disk_space>=60 reliability>=0.98 inet_down>200 dph<0.80'
# Ampere / Ada / Hopper only. Deliberately excludes Volta (V100), Pascal
# (P40/P100) and Turing (T4, Q RTX 8000), whose kernels recent PyTorch
# builds no longer ship. RTX 5090 (Blackwell) excluded too: it needs
# CUDA 12.8+, which pins the image choice more tightly than is worth it.
DEFAULT_ALLOW='RTX 3090,RTX 3090 Ti,RTX 4090,RTX 4090D,RTX 6000Ada,A5000,A6000,A100 PCIE,A100 SXM4,A100 SXM,L40S,RTX PRO 4000,RTX PRO 5000'

OFFER_ID=""
QUERY="$DEFAULT_QUERY"
PICK="value"
MAX_DPH="0.60"
MIN_VRAM="23"
GPU_ALLOW="$DEFAULT_ALLOW"
DISK=60
ARMS="A_raw,B_in_domain,E_glm,F_catboost"
IMAGE=""
TRANSPORT="onstart"
KEEP=0
ASSUME_YES=0

while [ $# -gt 0 ]; do
    case "$1" in
        --offer-id)  OFFER_ID="$2"; shift 2 ;;
        --query)     QUERY="$2"; shift 2 ;;
        --pick)      PICK="$2"; shift 2 ;;
        --max-dph)   MAX_DPH="$2"; shift 2 ;;
        --min-vram)  MIN_VRAM="$2"; shift 2 ;;
        --gpu-allow) GPU_ALLOW="$2"; shift 2 ;;
        --disk)      DISK="$2"; shift 2 ;;
        --arms)      ARMS="$2"; shift 2 ;;
        --image)     IMAGE="$2"; shift 2 ;;
        --transport) TRANSPORT="$2"; shift 2 ;;
        --keep)      KEEP=1; shift ;;
        --yes)       ASSUME_YES=1; shift ;;
        -h|--help)   sed -n '2,30p' "$0"; exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done

# DO NOT export VAST_API_KEY -- it silently breaks authentication.
# Measured: supplying the key explicitly (env var or --api-key) yields
#   401 "requires you to have logged in using Two Factor Authentication"
# even when the value is byte-identical to the CLI's config file (sha256-verified),
# while letting the CLI read that file succeeds. The 2FA session is bound to the key
# loaded from the config file. So `~/.config/vastai/vast_api_key` (mode 600) is the
# CLI's store and must stay -- the keychain is used for the TabPFN token only.
#
# Secrets now follow ONE RULE: each is a mode-600 file under ~/.config (FileVault is
# on, so that is encrypted at rest). keys.sh owns reading them.

# TabPFN token: read from its key file via keys.sh so the parsing lives in one place.
if [ -z "${TABPFN_TOKEN:-}" ] && [ -f "$REPO_DIR/scripts/gpu_helpers/keys.sh" ]; then
    TABPFN_TOKEN="$(bash "$REPO_DIR/scripts/gpu_helpers/keys.sh" get tabpfn 2>/dev/null || true)"
    [ -n "$TABPFN_TOKEN" ] && echo "[auth] TABPFN_TOKEN <- ~/.config/tfm/keys.env"
fi

: "${TABPFN_TOKEN:?No TABPFN_TOKEN. Store it with:
    bash scripts/gpu_helpers/keys.sh add tabpfn   (copy the key first)}"

INSTANCE_ID=""
T_CREATE=""; T_RUNNING=""; T_END=""
GPU_NAME=""; DPH=""; GPU_RAM=""; CPU_RAM="${CPU_RAM:-}"; REL=""; CUDA=""
BOOTSTRAP_RC=""

# Record what a run actually cost, so the cost model in the runbook can be
# replaced with measurements instead of assumptions. Writes one JSON per run
# plus an appended CSV ledger we can aggregate across runs.
record_run() {
    [ -z "$INSTANCE_ID" ] && return 0
    [ -z "$T_CREATE" ] && return 0

    local end="${T_END:-$(date -u +%s)}"
    local wall_s=$(( end - T_CREATE ))
    [ "$wall_s" -lt 0 ] && wall_s=0

    mkdir -p "$REPO_DIR/outputs/gpu-pilot"
    RUN_STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

    python3 - "$REPO_DIR" "$RUN_STAMP" "$wall_s" <<PY
import csv, json, os, sys
repo, stamp, wall_s = sys.argv[1], sys.argv[2], int(sys.argv[3])
outdir = os.path.join(repo, "outputs", "gpu-pilot")
os.makedirs(outdir, exist_ok=True)

rec = {
    "run_id": stamp,
    "instance_id": "$INSTANCE_ID",
    "gpu_name": "$GPU_NAME",
    "dph_total": float("$DPH" or 0),
    "gpu_ram_gb": float("$GPU_RAM" or 0),
    "cpu_ram_gb": float("$CPU_RAM" or 0),
    "reliability": "$REL",
    "cuda_max_good": "$CUDA",
    "image": "$IMAGE",
    "transport": "$TRANSPORT",
    "arms": "$ARMS",
    "disk_requested_gb": "$DISK",
    "t_create": "$T_CREATE",
    "t_running": "$T_RUNNING",
    "t_end": "$end",
    "wall_seconds": wall_s,
    "wall_minutes": round(wall_s / 60.0, 2),
    "est_cost_usd": round(wall_s / 3600.0 * float("$DPH" or 0), 4),
    "bootstrap_rc": "$BOOTSTRAP_RC",
}

with open(os.path.join(outdir, f"run_{stamp}.json"), "w") as f:
    json.dump(rec, f, indent=2)

ledger = os.path.join(outdir, "run_ledger.csv")
exists = os.path.exists(ledger)
with open(ledger, "a", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rec))
    if not exists:
        w.writeheader()
    w.writerow(rec)

# NB: %-formatting, not f-strings, on the lines below. This heredoc is
# UNQUOTED, so the shell performs parameter expansion on its body before Python
# ever sees it. Dollar-brace expressions referencing rec[...] are not valid
# shell variables, so they expand to nothing and the line prints blank.
print("[cost] wall %s min x $%s/hr = $%s"
      % (rec['wall_minutes'], rec['dph_total'], rec['est_cost_usd']))
print("[cost] recorded -> outputs/gpu-pilot/run_%s.json + run_ledger.csv" % stamp)
PY
}

cleanup() {
    # Record BEFORE destroying: the record must survive a failed destroy.
    record_run
    if [ -n "$INSTANCE_ID" ]; then
        if [ "$KEEP" -eq 1 ]; then
            echo; echo "--- --keep: NOT destroying $INSTANCE_ID ---"
            echo "    destroy manually:  vastai destroy instance $INSTANCE_ID -y"
            echo "    (the instance is BILLING until you do)"
        else
            echo
            echo "--- destroying instance $INSTANCE_ID ---"
            # -y is REQUIRED. Without it the CLI asks for confirmation, which in
            # a non-interactive script reads EOF, aborts, and leaves the
            # instance running and billing -- the exact failure this trap is
            # supposed to prevent. Verified: 'vastai destroy instance' has a
            # '-y, --yes  Skip confirmation prompt' flag.
            if ! vastai destroy instance "$INSTANCE_ID" -y; then
                echo "WARNING: DESTROY FAILED -- $INSTANCE_ID is STILL BILLING." >&2
                echo "         run: vastai destroy instance $INSTANCE_ID -y" >&2
            fi
        fi
    fi
}
trap cleanup EXIT

# ---- 1. Auth ----
echo "=== 1/7 auth ==="
if ! vastai show user >/dev/null 2>&1; then
    echo "no 2FA session; launching vast_login.sh"
    bash "$REPO_DIR/scripts/gpu_helpers/vast_login.sh" || exit 2
fi
echo "session OK"

# Preflight: surface any instance left over from a previous run. A leaked
# instance bills continuously, so it is worth one extra API call to catch here.
LEAKS="$(vastai show instances --raw 2>/dev/null | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    raise SystemExit
insts = d if isinstance(d, list) else d.get('instances', [])
for i in insts:
    if (i.get('label') or '') == 'tabpfn-pilot':
        print('  id=%s status=%s gpu=%s dph=%s' % (i.get('id'), i.get('actual_status'),
                                                  i.get('gpu_name'), i.get('dph_total')))
" 2>/dev/null)"
if [ -n "$LEAKS" ]; then
    echo "WARNING: 'tabpfn-pilot' instances from an earlier run still exist and are BILLING:" >&2
    echo "$LEAKS" >&2
    echo "         destroy with:  vastai destroy instance <id> -y" >&2
    printf 'Continue anyway? [y/N] '
    read -r _leak_reply
    case "$_leak_reply" in [yY]*) ;; *) echo "aborted"; exit 2 ;; esac
fi

# ---- 2. Select an offer (restricted to usable architectures) ----
echo "=== 2/7 selecting offer (pick=$PICK ceiling=\$$MAX_DPH/hr min-vram=${MIN_VRAM}GB) ==="

if [ -z "$OFFER_ID" ]; then
    vastai search offers "$QUERY" -o dph --raw 2>/dev/null > /tmp/vast_candidates.json
    SELECTOR_OUT="$(python3 "$REPO_DIR/scripts/gpu_helpers/select_offer.py" \
        "$PICK" "$MAX_DPH" "$GPU_ALLOW" "$MIN_VRAM" /tmp/vast_candidates.json)"
    read -r OFFER_ID GPU_NAME DPH CUDA DLPERF CPU_RAM GPU_RAM DISK_SP REL <<< "$SELECTOR_OUT"
    if [ -z "$OFFER_ID" ]; then
        echo "FATAL: no usable offer within \$$MAX_DPH/hr. Widen with --max-dph / --gpu-allow." >&2
        exit 2
    fi
    echo "selected: id=$OFFER_ID gpu=$GPU_NAME \$$DPH/hr dlperf=$DLPERF cuda<=$CUDA ram=${CPU_RAM}GB vram=${GPU_RAM}GB disk=${DISK_SP}GB rel=$REL"
else
    echo "using caller-supplied offer id $OFFER_ID"
    CUDA="${CUDA:-12.4}"
fi

# ---- 3. Image matched to host CUDA ----
if [ -z "$IMAGE" ]; then
    # Image selection logic and the tag matrix live in pick_image.py -- see that
    # file for the two constraints (CUDA <= host ceiling, torch >= 2.5).
    IMAGE="$(python3 "$REPO_DIR/scripts/gpu_helpers/pick_image.py" "${CUDA:-12.4}")"
fi
echo "=== 3/7 image: $IMAGE (host cuda<=${CUDA:-?}) ==="

# ---- 4. SSH key (only needed for the ssh transport) ----
if [ "$TRANSPORT" = "ssh" ]; then
    echo "=== 4/7 ssh key (required for --transport ssh) ==="
    SSH_KEY_OUT="$(vastai create ssh-key "$(cat "$HOME/.ssh/id_ed25519.pub" 2>/dev/null || echo '')" 2>&1)"
    if printf '%s' "$SSH_KEY_OUT" | grep -q "Failed with error"; then
        echo "FATAL: could not register an ssh key --" >&2
        printf '%s' "$SSH_KEY_OUT" | grep -o 'Failed with error.*' | head -1 >&2
        echo "       'Team SSH keys are not supported' means the API key is team-scoped." >&2
        echo "       Switch with 'vastai set api-key <PERSONAL_KEY>' or drop --transport ssh." >&2
        exit 2
    fi
    echo "ssh key registered"
else
    echo "=== 4/7 ssh key: SKIPPED (api-only transport; no key needed) ==="
fi

# ---- 5. Create ----
echo "=== 5/7 creating instance (disk=${DISK}GB arms=$ARMS transport=$TRANSPORT) ==="
if [ "$ASSUME_YES" -eq 0 ]; then
    printf 'Proceed? [y/N] '
    read -r REPLY
    case "$REPLY" in [yY]*) ;; *) echo "aborted"; exit 0 ;; esac
fi

# ---- 5b. Build the onstart script ----
# THE TRANSPORT: `vastai execute` is NOT a shell -- it runs only ls/rm/du, so
# shipping a script through it fails with 400 "Invalid command given". A
# team-context account also cannot register an SSH key (show ssh-keys -> []).
# That leaves --onstart, which runs at container boot. --onstart takes a FILENAME
# (unlike --onstart-cmd, which is one argument capped around 4048 chars), so
# length is not a concern.
ONSTART_FILE="$REPO_DIR/scripts/gpu_helpers/.onstart.$$.sh"
{
    echo '#!/bin/bash'
    echo "# generated by vast_run.sh; contains a secret, never commit or keep"
    printf 'export TABPFN_TOKEN=%q\n' "$TABPFN_TOKEN"
    printf 'export ARMS=%q\n' "$ARMS"
    cat "$REPO_DIR/scripts/gpu_helpers/bootstrap_pilot.sh"
} > "$ONSTART_FILE"
# umask 077 is set at the top of this script, so the file is already owner-only.

CREATE_OUT="$(vastai create instance "$OFFER_ID" \
    --image "$IMAGE" --disk "$DISK" --ssh --direct \
    --onstart "$ONSTART_FILE" \
    --label "tabpfn-pilot" --raw 2>&1)"
rm -f "$ONSTART_FILE"   # it held the token; do not leave it on disk
echo "$CREATE_OUT"
INSTANCE_ID="$(printf '%s' "$CREATE_OUT" | python3 -c "
import json,sys,re
m=re.search(r'\{.*\}', sys.stdin.read(), re.S)
try: print(json.loads(m.group(0)).get('new_contract','') if m else '')
except Exception: print('')
")"
[ -z "$INSTANCE_ID" ] && { echo "FATAL: no instance id in the create response." >&2; exit 2; }
T_CREATE="$(date -u +%s)"
echo "instance id: $INSTANCE_ID  (billing starts now)"

# ---- 6. Wait for running ----
echo "=== 6/7 waiting for the instance ==="
HOST=""; PORT=""
# 'unknown' is NORMAL for the first ~minute after create: the API returns it
# while the instance is still being provisioned, and an empty poll just means the
# record is not readable yet. Treating those as terminal destroyed healthy
# instances on the first poll. Only 'exited' is definitively terminal; the others
# must persist past a grace period with no provisioning state to count as dead.
GRACE_SECS="${GRACE_SECS:-90}"
SAW_PROVISIONING=0
for i in $(seq 1 60); do
    INFO="$(vastai show instance "$INSTANCE_ID" --raw 2>/dev/null)"
    # `show instance` is the only source of these facts that works for BOTH the
    # selected-offer and caller-supplied --offer-id paths.
    IFS='|' read -r STATUS HOST PORT _GN _DP _GR _CR _RL _CU < <(printf '%s' "$INFO" | python3 -c "
import json,sys
try: d=json.load(sys.stdin)
except Exception: print('unknown|||||||'); raise SystemExit
def g(*ks):
    for k in ks:
        v=d.get(k)
        if v not in (None,''): return str(v)
    return ''
print('|'.join([g('actual_status') or 'unknown', g('ssh_host'), g('ssh_port'),
                g('gpu_name','gpu_names').replace(' ','_'),
                g('dph_total'), g('gpu_ram'), g('cpu_ram'),
                g('reliability'), g('cuda_max_good')]))
")
    [ -n "$_GN" ] && GPU_NAME="$_GN"
    [ -n "$_DP" ] && DPH="$_DP"
    [ -n "$_GR" ] && GPU_RAM="$(python3 -c "print(f'{float(\"$_GR\")/1000:.1f}')" 2>/dev/null || echo "$_GR")"
    [ -n "$_CR" ] && CPU_RAM="$(python3 -c "print(int(float(\"$_CR\")/1000))" 2>/dev/null || echo "$_CR")"
    [ -n "$_RL" ] && REL="$_RL"
    [ -n "$_CU" ] && CUDA="$_CU"
    echo "  [$i] status=$STATUS"
    if [ "$STATUS" = "running" ]; then
        T_RUNNING="$(date -u +%s)"
        break
    fi
    # Terminal states never become 'running' -- but only 'exited' is definitively
    # terminal. 'unknown'/'offline'/empty are normal during provisioning, so they
    # must persist past GRACE_SECS with no provisioning state to count as dead.
    case "$STATUS" in
        exited)
            echo "FATAL: container 'exited' -- it will never become running." >&2
            echo "       Destroying and aborting; retry with a different offer." >&2
            exit 2
            ;;
        loading|created|starting|pulling|provisioning)
            SAW_PROVISIONING=1
            ;;
        unknown|offline|"")
            AGE=$(( $(date -u +%s) - T_CREATE ))
            if [ "$AGE" -ge "$GRACE_SECS" ] && [ "$SAW_PROVISIONING" -eq 0 ]; then
                echo "FATAL: instance stayed '$STATUS' for ${AGE}s with no provisioning state." >&2
                echo "       Destroying and aborting; retry with a different offer." >&2
                exit 2
            fi
            ;;
    esac
    sleep 10
done
[ "$STATUS" = "running" ] || { echo "FATAL: instance never reached 'running'." >&2; exit 2; }

# ---- 7. Run the pilot ----
echo "=== 7/7 running pilot ==="
RUN_RC=0

if [ "$TRANSPORT" = "ssh" ]; then
    SSH_OPTS=(-o StrictHostKeyChecking=accept-new -o ConnectTimeout=20 -o ServerAliveInterval=30)
    ssh -p "$PORT" "${SSH_OPTS[@]}" "root@$HOST" \
        "TABPFN_TOKEN='$TABPFN_TOKEN' ARMS='$ARMS' bash -s" \
        < "$REPO_DIR/scripts/gpu_helpers/bootstrap_pilot.sh"
    RUN_RC=$?
else
    # The bootstrap already started at container boot via --onstart, so there is
    # nothing to launch here: watch the container log until it reports completion.
    echo "running via: --onstart (bootstrap began at container boot)"
    : > /tmp/vast_run_out.txt
    BOOTSTRAP_DONE=0
    for i in $(seq 1 180); do   # 180 x 20s = 60 min ceiling
        sleep 20
        vastai logs "$INSTANCE_ID" --tail 200000 > /tmp/vast_run_out.txt 2>/dev/null
        if grep -q "BOOTSTRAP FINISHED" /tmp/vast_run_out.txt 2>/dev/null; then
            BOOTSTRAP_DONE=1
            break
        fi
        # Surface progress without flooding: the most recent milestone line.
        PROG="$(grep -aE '^##########|PILOT RESULTS|ROC=|EXITED rc=' /tmp/vast_run_out.txt 2>/dev/null | tail -1)"
        [ -n "$PROG" ] && echo "  [$i] $PROG"
    done
    if [ "$BOOTSTRAP_DONE" != "1" ]; then
        echo "WARNING: bootstrap did not report BOOTSTRAP FINISHED within 60 min" >&2
        RUN_RC=1
    fi
    echo "--- log tail ---"
    tail -40 /tmp/vast_run_out.txt
fi

BOOTSTRAP_RC="$RUN_RC"
T_END="$(date -u +%s)"

# ---- pull artifacts ----
echo "=== pulling artifacts ==="
mkdir -p "$REPO_DIR/outputs/gpu-pilot"
if [ "$TRANSPORT" = "ssh" ]; then
    scp -P "$PORT" -o StrictHostKeyChecking=accept-new -r \
        "root@$HOST:/workspace/tfm/outputs/finetune/pilot/*" \
        "$REPO_DIR/outputs/gpu-pilot/" || \
        echo "WARNING: scp failed -- re-run with --keep" >&2
else
    # The bootstrap printed its payload between markers on stdout, so the container
    # log -- already captured in /tmp/vast_run_out.txt -- IS the transfer channel.
    # (`vastai execute` cannot read files; it only runs ls/rm/du.)
    cp /tmp/vast_run_out.txt /tmp/vast_artifacts.raw 2>/dev/null || : > /tmp/vast_artifacts.raw
    python3 - <<'PY' > /tmp/vast_artifacts.b64
import re, sys
s = open('/tmp/vast_artifacts.raw', errors='replace').read()
m = re.search(r'__ARTIFACTS_B64_BEGIN__\s*([A-Za-z0-9+/=]+)\s*__ARTIFACTS_B64_END__', s, re.S)
sys.stdout.write(m.group(1) if m else '')
PY
    if [ -s /tmp/vast_artifacts.b64 ] && \
       base64 -d < /tmp/vast_artifacts.b64 > /tmp/vast_artifacts.tar.gz 2>/dev/null && \
       tar xzf /tmp/vast_artifacts.tar.gz -C "$REPO_DIR/outputs/gpu-pilot" 2>/dev/null; then
        echo "artifacts restored to outputs/gpu-pilot"
    else
        echo "WARNING: no artifact payload found in the container log" >&2
        echo "         log captured at /tmp/vast_run_out.txt; use --keep to inspect" >&2
    fi
fi

echo
echo "=== done (rc=$RUN_RC) ==="
ls -l "$REPO_DIR/outputs/gpu-pilot" 2>/dev/null | head -20
