#!/bin/bash
# End-to-end pilot run on Vast.ai: pick offer -> create -> bootstrap -> pull -> destroy.
#
#   bash scripts/gpu_helpers/vast_run.sh [options]
#
# Options:
#   --offer-id N     use a specific offer (skips selection)
#   --query 'Q'      offer search query        (default: DEFAULT_QUERY below)
#   --pick HOW       value | cheapest | fastest   (default: value = dlperf/$)
#   --max-dph N      hard price ceiling in $/hr   (default 0.60)
#   --disk N         local disk GB                (default 60)
#   --arms LIST      arms to run                  (default all four)
#   --image NAME     override the docker image
#   --keep           do NOT destroy on exit
#   --yes            skip the confirmation prompt
#
# Why a query and not an offer ID: the marketplace turns over fast -- an offer
# recommended 30 minutes earlier was already gone. Selecting at run time is the
# only way this script stays usable.
#
# The image is chosen to match the host's max CUDA. A CUDA 12.4 image will not
# run on a driver that only supports 12.1.
#
# Cost safety: a trap destroys the instance on ANY exit (success, failure,
# Ctrl-C) unless --keep. A forgotten running instance bills indefinitely.

set -uo pipefail

export PATH="$HOME/.local/share/uv/tools/vastai/bin:$PATH"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

DEFAULT_QUERY='num_gpus=1 gpu_ram>=23 cpu_ram>=32 disk_space>=50 reliability>=0.98 inet_down>200'

OFFER_ID=""
QUERY="$DEFAULT_QUERY"
PICK="value"
MAX_DPH="0.60"
DISK=60
ARMS="A_raw,B_in_domain,E_glm,F_catboost"
IMAGE=""
KEEP=0
ASSUME_YES=0

while [ $# -gt 0 ]; do
    case "$1" in
        --offer-id) OFFER_ID="$2"; shift 2 ;;
        --query)    QUERY="$2"; shift 2 ;;
        --pick)     PICK="$2"; shift 2 ;;
        --max-dph)  MAX_DPH="$2"; shift 2 ;;
        --disk)     DISK="$2"; shift 2 ;;
        --arms)     ARMS="$2"; shift 2 ;;
        --image)    IMAGE="$2"; shift 2 ;;
        --keep)     KEEP=1; shift ;;
        --yes)      ASSUME_YES=1; shift ;;
        -h|--help)  sed -n '2,30p' "$0"; exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done

: "${TABPFN_TOKEN:?Export TABPFN_TOKEN before running}"

INSTANCE_ID=""
cleanup() {
    if [ -n "$INSTANCE_ID" ]; then
        if [ "$KEEP" -eq 1 ]; then
            echo
            echo "--- --keep: NOT destroying $INSTANCE_ID ---"
            echo "    destroy manually: vastai destroy instance $INSTANCE_ID"
        else
            echo
            echo "--- destroying instance $INSTANCE_ID ---"
            vastai destroy instance "$INSTANCE_ID" || \
                echo "WARNING: destroy failed -- check 'vastai show instances'" >&2
        fi
    fi
}
trap cleanup EXIT

# ---- 1. Auth ----
echo "=== 1/7 auth ==="
if ! vastai show user >/dev/null 2>&1; then
    echo "No 2FA session; launching vast_login.sh"
    bash "$REPO_DIR/scripts/gpu_helpers/vast_login.sh" || exit 2
fi
echo "session OK"

# ---- 2. Select an offer ----
echo "=== 2/7 selecting offer (pick=$PICK ceiling=\$$MAX_DPH/hr) ==="

if [ -z "$OFFER_ID" ]; then
    : > /tmp/vast_candidates.json
    vastai search offers "$QUERY" -o dph --raw 2>/dev/null > /tmp/vast_candidates.json

    read -r OFFER_ID GPU_NAME DPH CUDA DLPERF CPU_RAM GPU_RAM DISK_SP REL < <(python3 - "$PICK" "$MAX_DPH" <<'PY'
import json, sys
pick, max_dph = sys.argv[1], float(sys.argv[2])
try:
    d = json.load(open('/tmp/vast_candidates.json'))
except Exception:
    print(""); raise SystemExit
o = d if isinstance(d, list) else d.get('offers', [])
o = [x for x in o if (x.get('dph_total') or 9e9) <= max_dph]
if not o:
    print(""); raise SystemExit
if pick == 'cheapest':
    o.sort(key=lambda x: x.get('dph_total') or 9e9)
elif pick == 'fastest':
    o.sort(key=lambda x: -(x.get('dlperf') or 0))
else:
    o.sort(key=lambda x: -((x.get('dlperf') or 0) / (x.get('dph_total') or 1)))
x = o[0]
print(x.get('id'), x.get('gpu_name','?').replace(' ', '_'), f"{x.get('dph_total',0):.4f}",
      x.get('cuda_max_good') or 0, f"{x.get('dlperf') or 0:.1f}",
      int((x.get('cpu_ram') or 0)/1000), f"{(x.get('gpu_ram') or 0)/1000:.1f}",
      int(x.get('disk_space') or 0), f"{x.get('reliability',0):.4f}")
PY
)
    if [ -z "$OFFER_ID" ]; then
        echo "FATAL: no offer matched within \$$MAX_DPH/hr. Widen with --query / --max-dph." >&2
        exit 2
    fi
    echo "selected: id=$OFFER_ID gpu=$GPU_NAME \$$DPH/hr dlperf=$DLPERF cuda<=$CUDA ram=${CPU_RAM}GB vram=${GPU_RAM}GB disk=${DISK_SP}GB rel=$REL"
else
    echo "using caller-supplied offer id $OFFER_ID"
fi

# ---- 3. Image matching the host CUDA ----
if [ -z "$IMAGE" ]; then
    CUDA_NUM="${CUDA:-12.1}"
    if python3 -c "import sys; sys.exit(0 if float('$CUDA_NUM') >= 12.4 else 1)"; then
        IMAGE="pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime"
    else
        IMAGE="pytorch/pytorch:2.4.0-cuda12.1-cudnn9-runtime"
    fi
fi
echo "=== 3/7 image: $IMAGE ==="

# ---- 4. SSH key ----
echo "=== 4/7 ssh key ==="
if ! vastai show ssh-keys 2>/dev/null | grep -qE "ssh-ed25519|ssh-rsa"; then
    [ -f "$HOME/.ssh/id_ed25519.pub" ] || ssh-keygen -t ed25519 -f "$HOME/.ssh/id_ed25519" -N ""
    vastai create ssh-key "$(cat "$HOME/.ssh/id_ed25519.pub")" || exit 2
    echo "registered $HOME/.ssh/id_ed25519.pub"
else
    echo "ssh key already on the account"
fi

# ---- 5. Create ----
echo "=== 5/7 creating instance (disk=${DISK}GB arms=$ARMS) ==="
if [ "$ASSUME_YES" -eq 0 ]; then
    printf 'Proceed? [y/N] '
    read -r REPLY
    case "$REPLY" in [yY]*) ;; *) echo "aborted"; exit 0 ;; esac
fi

CREATE_OUT="$(vastai create instance "$OFFER_ID" \
    --image "$IMAGE" --disk "$DISK" --ssh --direct \
    --label "tabpfn-pilot" --raw 2>&1)"
echo "$CREATE_OUT"
INSTANCE_ID="$(printf '%s' "$CREATE_OUT" | python3 -c "
import json,sys,re
m=re.search(r'\{.*\}', sys.stdin.read(), re.S)
try:
    print(json.loads(m.group(0)).get('new_contract','') if m else '')
except Exception:
    print('')
")"

if [ -z "$INSTANCE_ID" ]; then
    echo "FATAL: no instance id in the create response." >&2
    exit 2
fi
echo "instance id: $INSTANCE_ID"

# ---- 6. Wait for running ----
echo "=== 6/7 waiting for the instance ==="
HOST=""; PORT=""
for i in $(seq 1 60); do
    INFO="$(vastai show instance "$INSTANCE_ID" --raw 2>/dev/null)"
    read -r STATUS HOST PORT < <(printf '%s' "$INFO" | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
except Exception:
    print('unknown'); raise SystemExit
print(d.get('actual_status','unknown'), d.get('ssh_host','') or '', d.get('ssh_port','') or '')
")
    echo "  [$i] status=$STATUS host=${HOST:-...} port=${PORT:-...}"
    [ "$STATUS" = "running" ] && [ -n "$HOST" ] && [ -n "$PORT" ] && break
    sleep 10
done

if [ -z "$HOST" ] || [ -z "$PORT" ]; then
    echo "FATAL: never got a usable ssh endpoint." >&2
    exit 2
fi

# ---- 7. Run ----
echo "=== 7/7 running pilot on $HOST:$PORT ==="
SSH_OPTS=(-o StrictHostKeyChecking=accept-new -o ConnectTimeout=20 -o ServerAliveInterval=30)
ssh -p "$PORT" "${SSH_OPTS[@]}" "root@$HOST" \
    "TABPFN_TOKEN='$TABPFN_TOKEN' ARMS='$ARMS' bash -s" \
    < "$REPO_DIR/scripts/gpu_helpers/bootstrap_pilot.sh"
RUN_RC=$?
echo "bootstrap exit code: $RUN_RC"

echo "=== pulling artifacts ==="
mkdir -p "$REPO_DIR/outputs/gpu-pilot"
scp -P "$PORT" "${SSH_OPTS[@]}" -r \
    "root@$HOST:/workspace/tfm/outputs/finetune/pilot/*" \
    "$REPO_DIR/outputs/gpu-pilot/" || \
    echo "WARNING: scp failed -- re-run with --keep to inspect the instance" >&2

echo
echo "=== done (rc=$RUN_RC) ==="
ls -l "$REPO_DIR/outputs/gpu-pilot" 2>/dev/null | head -20
