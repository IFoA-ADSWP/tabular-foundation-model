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
TRANSPORT="execute"
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

: "${TABPFN_TOKEN:?Export TABPFN_TOKEN before running}"

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
echo "=== 2/7 selecting offer (pick=$PICK ceiling=\$$MAX_DPH/hr min-vram=${MIN_VRAM}GB) ==="

if [ -z "$OFFER_ID" ]; then
    vastai search offers "$QUERY" -o dph --raw 2>/dev/null > /tmp/vast_candidates.json
    read -r OFFER_ID GPU_NAME DPH CUDA DLPERF CPU_RAM GPU_RAM DISK_SP REL < <(
        python3 - "$PICK" "$MAX_DPH" "$GPU_ALLOW" "$MIN_VRAM" <<'PY'
import json, sys
pick, max_dph = sys.argv[1], float(sys.argv[2])
allow = set(a.strip() for a in sys.argv[3].split(','))
min_vram = float(sys.argv[4])
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
     and (x.get('cuda_max_good') or 0) >= 12.0
     and (x.get('gpu_ram') or 0) / 1000.0 >= min_vram]
if not o:
    print(""); raise SystemExit
if pick == 'cheapest':
    o.sort(key=lambda x: (x.get('dph_total') or 9e9, -(x.get('reliability') or 0)))
elif pick == 'fastest':
    o.sort(key=lambda x: (-(x.get('dlperf') or 0), -(x.get('reliability') or 0)))
else:
    # Value first, reliability as tiebreak: two offers at the same dlperf/$
    # should not be separated by API return order, or a 0.978 host can be
    # picked over a 0.998 one at the same price.
    o.sort(key=lambda x: (-((x.get('dlperf') or 0) / (x.get('dph_total') or 1)),
                          -(x.get('reliability') or 0)))
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
    # Every tier must carry torch >= 2.5: tabpfn 8.5.0 requires torch>=2.5, so
    # a 2.4.0 image would let pip upgrade torch to a CUDA 12.4 wheel on a host
    # that only supports 12.2 -- a mid-run CUDA failure on a paid instance.
    # Verified tag matrix: 2.5.1 -> {cuda12.1, cuda12.4}, 2.6.0 -> cuda12.6,
    # 2.7.0 -> cuda12.8.
    IMAGE="$(python3 - "${CUDA:-12.4}" <<'PY'
import sys
c = float(sys.argv[1])
if   c >= 12.8: print("pytorch/pytorch:2.7.0-cuda12.8-cudnn9-runtime")
elif c >= 12.6: print("pytorch/pytorch:2.6.0-cuda12.6-cudnn9-runtime")
elif c >= 12.4: print("pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime")
else:           print("pytorch/pytorch:2.5.1-cuda12.1-cudnn9-runtime")
PY
)"
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
T_CREATE="$(date -u +%s)"
echo "instance id: $INSTANCE_ID  (billing starts now)"

# ---- 6. Wait for running ----
echo "=== 6/7 waiting for the instance ==="
HOST=""; PORT=""
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

BOOTSTRAP_RC="$RUN_RC"
T_END="$(date -u +%s)"

# ---- pull artifacts ----
echo "=== pulling artifacts ==="
mkdir -p "$REPO_DIR/outputs/gpu-pilot"
if [ "$TRANSPORT" = "execute" ]; then
    # Markers so CLI decoration around the payload cannot corrupt the stream.
    vastai execute "$INSTANCE_ID" \
        "cd /workspace/tfm/outputs/finetune/pilot 2>/dev/null && echo __VAST_B64_BEGIN__ && tar czf - . | base64 -w0 && echo __VAST_B64_END__" \
        > /tmp/vast_artifacts.raw 2>/dev/null
    python3 - <<'PY' > /tmp/vast_artifacts.b64
import re, sys
s = open('/tmp/vast_artifacts.raw', errors='replace').read()
m = re.search(r'__VAST_B64_BEGIN__\s*(\S+?)\s*__VAST_B64_END__', s, re.S)
sys.stdout.write(m.group(1) if m else '')
PY
    if [ -s /tmp/vast_artifacts.b64 ] && \
       base64 -d < /tmp/vast_artifacts.b64 > /tmp/vast_artifacts.tar.gz 2>/dev/null && \
       tar xzf /tmp/vast_artifacts.tar.gz -C "$REPO_DIR/outputs/gpu-pilot" 2>/dev/null; then
        echo "artifacts restored to outputs/gpu-pilot"
    else
        echo "WARNING: artifact retrieval via execute failed -- re-run with --keep" >&2
        echo "         (raw CLI output left at /tmp/vast_artifacts.raw)" >&2
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
