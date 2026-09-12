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
GPU_ALLOW="$DEFAULT_ALLOW"
DISK=60
ARMS="A_raw,B_in_domain,E_glm,F_catboost"
IMAGE=""
TRANSPORT="execute"
KEEP=0
ASSUME_YES=0

while [ $# -gt 0 ]; do
    case "$1" in
        --offer-id)  OFFER_ID="$2"; shift 2 ;;
        --query)     QUERY="$2"; shift 2 ;;
        --pick)      PICK="$2"; shift 2 ;;
        --max-dph)   MAX_DPH="$2"; shift 2 ;;
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

: "${TABPFN_TOKEN:?Export TABPFN_TOKEN before running}"

INSTANCE_ID=""
cleanup() {
    if [ -n "$INSTANCE_ID" ]; then
        if [ "$KEEP" -eq 1 ]; then
            echo; echo "--- --keep: NOT destroying $INSTANCE_ID ---"
            echo "    destroy manually: vastai destroy instance $INSTANCE_ID"
        else
            echo; echo "--- destroying instance $INSTANCE_ID ---"
            vastai destroy instance "$INSTANCE_ID" || \
                echo "WARNING: destroy failed -- check 'vastai show instances'" >&2
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

# ---- 2. Select an offer (restricted to usable architectures) ----
echo "=== 2/7 selecting offer (pick=$PICK ceiling=\$$MAX_DPH/hr) ==="

if [ -z "$OFFER_ID" ]; then
    vastai search offers "$QUERY" -o dph --raw 2>/dev/null > /tmp/vast_candidates.json
    read -r OFFER_ID GPU_NAME DPH CUDA DLPERF CPU_RAM GPU_RAM DISK_SP REL < <(
        python3 - "$PICK" "$MAX_DPH" "$GPU_ALLOW" <<'PY'
import json, sys
pick, max_dph, allow = sys.argv[1], float(sys.argv[2]), set(a.strip() for a in sys.argv[3].split(','))
try:
    d = json.load(open('/tmp/vast_candidates.json'))
except Exception:
    print(""); raise SystemExit
o = d if isinstance(d, list) else d.get('offers', [])
bad = {'Tesla V100','Tesla P40','Tesla P100','Tesla T4','Q RTX 8000','Q RTX 6000','RTX 2080 Ti'}
o = [x for x in o
     if x.get('gpu_name') in allow
     and x.get('gpu_name') not in bad
     and (x.get('dph_total') or 9e9) <= max_dph
     and (x.get('cuda_max_good') or 0) >= 12.0]
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
    if python3 -c "import sys; sys.exit(0 if float('${CUDA:-12.4}') >= 12.8 else 1)"; then
        IMAGE="pytorch/pytorch:2.7.0-cuda12.8-cudnn9-runtime"
    elif python3 -c "import sys; sys.exit(0 if float('${CUDA:-12.4}') >= 12.4 else 1)"; then
        IMAGE="pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime"
    else
        IMAGE="pytorch/pytorch:2.4.0-cuda12.1-cudnn9-runtime"
    fi
fi
echo "=== 3/7 image: $IMAGE ==="

# ---- 4. SSH key (best-effort; not required on the execute transport) ----
echo "=== 4/7 ssh key (best effort) ==="
SSH_KEY_OUT="$(vastai create ssh-key "$(cat "$HOME/.ssh/id_ed25519.pub" 2>/dev/null || echo '')" 2>&1)"
if printf '%s' "$SSH_KEY_OUT" | grep -q "Failed with error"; then
    # Silence would be wrong: this is why we default to `execute`.
    echo "note: ssh key NOT registered -- $(printf '%s' "$SSH_KEY_OUT" | grep -o 'Failed with error.*' | head -1)"
    echo "      (expected in a team context; using the execute transport)"
    if [ "$TRANSPORT" = "ssh" ]; then
        echo "FATAL: --transport ssh requested but no key is registered." >&2
        exit 2
    fi
else
    echo "ssh key registered"
fi

# ---- 5. Create ----
echo "=== 5/7 creating instance (disk=${DISK}GB arms=$ARMS transport=$TRANSPORT) ==="
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
try: print(json.loads(m.group(0)).get('new_contract','') if m else '')
except Exception: print('')
")"
[ -z "$INSTANCE_ID" ] && { echo "FATAL: no instance id in the create response." >&2; exit 2; }
echo "instance id: $INSTANCE_ID"

# ---- 6. Wait for running ----
echo "=== 6/7 waiting for the instance ==="
HOST=""; PORT=""
for i in $(seq 1 60); do
    INFO="$(vastai show instance "$INSTANCE_ID" --raw 2>/dev/null)"
    read -r STATUS HOST PORT < <(printf '%s' "$INFO" | python3 -c "
import json,sys
try: d=json.load(sys.stdin)
except Exception: print('unknown'); raise SystemExit
print(d.get('actual_status','unknown'), d.get('ssh_host','') or '', d.get('ssh_port','') or '')
")
    echo "  [$i] status=$STATUS"
    [ "$STATUS" = "running" ] && break
    sleep 10
done
[ "$STATUS" = "running" ] || { echo "FATAL: instance never reached 'running'." >&2; exit 2; }

# ---- 7. Run the pilot ----
echo "=== 7/7 running pilot ==="
RUN_RC=0

if [ "$TRANSPORT" = "execute" ]; then
    # Ship the bootstrap base64-encoded, so no quoting can corrupt it.
    B64="$(base64 < "$REPO_DIR/scripts/gpu_helpers/bootstrap_pilot.sh" | tr -d '\n')"
    CMD="echo '$B64' | base64 -d > /tmp/boot.sh && TABPFN_TOKEN='$TABPFN_TOKEN' ARMS='$ARMS' bash /tmp/boot.sh"
    echo "running via: vastai execute $INSTANCE_ID"
    # Long jobs: poll the container log rather than hold one request open.
    vastai execute "$INSTANCE_ID" "$CMD" >/tmp/vast_run_out.txt 2>&1 &
    EXEC_PID=$!
    while kill -0 "$EXEC_PID" 2>/dev/null; do
        sleep 30
        echo "  --- log tail ---"
        vastai logs "$INSTANCE_ID" --tail 12 2>/dev/null | tail -12
    done
    wait "$EXEC_PID"; RUN_RC=$?
    echo "--- execute output ---"
    tail -60 /tmp/vast_run_out.txt
else
    SSH_OPTS=(-o StrictHostKeyChecking=accept-new -o ConnectTimeout=20 -o ServerAliveInterval=30)
    ssh -p "$PORT" "${SSH_OPTS[@]}" "root@$HOST" \
        "TABPFN_TOKEN='$TABPFN_TOKEN' ARMS='$ARMS' bash -s" \
        < "$REPO_DIR/scripts/gpu_helpers/bootstrap_pilot.sh"
    RUN_RC=$?
fi

# ---- pull artifacts ----
echo "=== pulling artifacts ==="
mkdir -p "$REPO_DIR/outputs/gpu-pilot"
if [ "$TRANSPORT" = "execute" ]; then
    vastai execute "$INSTANCE_ID" \
        "cd /workspace/tfm/outputs/finetune/pilot 2>/dev/null && tar czf - . | base64 -w0" \
        > /tmp/vast_artifacts.b64 2>/dev/null
    if grep -qE '^[A-Za-z0-9+/=]+$' /tmp/vast_artifacts.b64 2>/dev/null; then
        base64 -d /tmp/vast_artifacts.b64 > /tmp/vast_artifacts.tar.gz 2>/dev/null && \
            tar xzf /tmp/vast_artifacts.tar.gz -C "$REPO_DIR/outputs/gpu-pilot" && \
            echo "artifacts restored to outputs/gpu-pilot" || \
            echo "WARNING: artifact decode failed -- re-run with --keep"
    else
        echo "WARNING: could not retrieve artifacts via execute; re-run with --keep to fetch manually"
    fi
else
    scp -P "$PORT" -o StrictHostKeyChecking=accept-new -r \
        "root@$HOST:/workspace/tfm/outputs/finetune/pilot/*" \
        "$REPO_DIR/outputs/gpu-pilot/" || \
        echo "WARNING: scp failed -- re-run with --keep" >&2
fi

echo
echo "=== done (rc=$RUN_RC) ==="
ls -l "$REPO_DIR/outputs/gpu-pilot" 2>/dev/null | head -20
