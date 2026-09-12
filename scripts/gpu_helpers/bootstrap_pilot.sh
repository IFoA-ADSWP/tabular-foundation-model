#!/bin/bash
# Bootstrap the fine-tuning pilot on a plain GPU VM (Vast.ai, Lambda, EC2...).
#
# Usage:
#   export TABPFN_TOKEN="pk_..."
#   ssh -p <PORT> root@<IP> "TABPFN_TOKEN=$TABPFN_TOKEN bash -s" < scripts/gpu_helpers/bootstrap_pilot.sh
#
# or, already on the box:
#   TABPFN_TOKEN=pk_... bash bootstrap_pilot.sh
#
# Unlike the Colab launcher this does NOT detach: over SSH you keep the
# terminal, so blocking is correct and simpler. The per-arm subprocess
# isolation is kept -- on the 12 GB CPU runtime a fine-tuning OOM SIGKILLed
# the interpreter and took the whole batch with it.
#
# Deliberately does NOT use requirements.txt: it pins numpy>=1.24,<2, which
# has no cp313 wheels, so pip compiles numpy from source (~20 min).

set -uo pipefail

: "${TABPFN_TOKEN:?Set TABPFN_TOKEN before running}"

BRANCH="${BRANCH:-finetune-v2}"
REPO="https://github.com/IFoA-ADSWP/tabular-foundation-model.git"
WORKDIR="${WORKDIR:-/workspace/tfm}"
ARMS="${ARMS:-A_raw,B_in_domain,E_glm,F_catboost}"

TABPFN_PIN="tabpfn==8.5.0"

echo "============================================================"
echo "BOOTSTRAP — branch=$BRANCH arms=$ARMS workdir=$WORKDIR"
echo "============================================================"

# ---- 1. Verify the GPU BEFORE spending time or money ----
echo "--- GPU check ---"
if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi --query-gpu=name,memory.total,driver_version \
               --format=csv,noheader || true
else
    echo "FATAL: nvidia-smi not found — this is not a GPU box." >&2
    exit 2
fi

# ---- 2. Clone ----
mkdir -p "$(dirname "$WORKDIR")"
if [ -d "$WORKDIR/.git" ]; then
    echo "--- existing clone, fetching ---"
    git -C "$WORKDIR" fetch origin "$BRANCH"
    git -C "$WORKDIR" checkout "$BRANCH"
    git -C "$WORKDIR" reset --hard "origin/$BRANCH"
else
    echo "--- cloning ---"
    git clone --branch "$BRANCH" "$REPO" "$WORKDIR" || exit 2
fi
cd "$WORKDIR" || exit 2

# ---- 3. Dependencies ----
# torch is NOT listed: the PyTorch image ships a CUDA build and reinstalling
# risks swapping it for a CPU wheel.
echo "--- installing deps ($TABPFN_PIN) ---"
python3 -m pip install -q --upgrade "$TABPFN_PIN" scikit-learn pandas \
    pyarrow catboost || exit 2

echo "--- verifying torch sees the GPU ---"
if ! python3 -c "
import sys, torch
if not torch.cuda.is_available():
    sys.exit('FATAL: torch.cuda.is_available() is False — refusing to run on CPU.')
print('torch', torch.__version__, '| cuda', torch.version.cuda,
      '|', torch.cuda.get_device_name(0))
"; then
    echo "FATAL: CUDA unavailable to torch. Stopping before doing CPU work on a paid GPU." >&2
    exit 2
fi

# ---- 4. Run each arm in its own process ----
for arm in ${ARMS//,/ }; do
    echo
    echo "########## ARM $arm ##########"
    python3 scripts/run_pilot.py --arms "$arm"
    rc=$?
    if [ "$rc" -ne 0 ]; then
        # 137 => 128+9 SIGKILL, i.e. the OOM killer. Reported, not fatal.
        echo "########## ARM $arm EXITED rc=$rc (137 = OOM SIGKILL) ##########"
    fi
done

# ---- 5. Aggregate ----
echo
echo "########## AGGREGATE ##########"
python3 scripts/run_pilot.py --aggregate

echo
echo "########## ARTIFACTS ##########"
ls -lR outputs/finetune/pilot 2>/dev/null | head -40
echo "BOOTSTRAP FINISHED"
