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

# ---- 0. Always emit the completion marker, on EVERY exit path ----
# The runner polls the log for this exact string. Without it an aborted
# bootstrap is indistinguishable from a slow one, so the runner waits out its
# whole ceiling while the instance bills -- which is precisely how a 60-minute
# leak happened. A trap makes that structurally impossible.
_BOOTSTRAP_DONE=0
finish() {
    [ "$_BOOTSTRAP_DONE" -eq 1 ] && return 0
    _BOOTSTRAP_DONE=1
    echo
    echo "BOOTSTRAP FINISHED"
}
trap finish EXIT

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

# ---- 3b. Prove the TabPFN licence BEFORE running any arm ----
# A token being PRESENT is not the same as a token WORKING. With an un-accepted
# licence every arm dies in about a second, with a message that reads like a model
# problem ("requires a one-time license acceptance ... no interactive terminal"),
# so the batch burns GPU minutes to learn nothing. Force the gated weight download
# here, once, where the outcome is unambiguous. On failure, stop -- the arms would
# fail identically.
#
# NOTE: `python3 -c` and not a heredoc. The header still documents piping this
# script to `bash -s`, and a heredoc would swallow the rest of the script from stdin.
echo "--- TabPFN auth preflight (forces the gated weight download) ---"
python3 -c '
import os, sys
tok = os.environ.get("TABPFN_TOKEN") or ""
if not tok:
    sys.exit("no TABPFN_TOKEN in the environment at all")
print("  token present: %d chars, prefix %s..." % (len(tok), tok[:10]))
import numpy as np
from tabpfn import TabPFNClassifier
rng = np.random.default_rng(0)
X = rng.random((24, 4))
y = (X[:, 0] > 0.5).astype(int)
TabPFNClassifier(n_estimators=1, device="cpu", random_state=0).fit(X, y)
print("  TABPFN_AUTH_OK - weights downloaded and a fit completed")
'
PREFLIGHT_RC=$?
if [ "$PREFLIGHT_RC" -ne 0 ]; then
    echo "########## PREFLIGHT FAILED (rc=$PREFLIGHT_RC) ##########" >&2
    echo "FATAL: the token/licence cannot download weights; refusing to run arms" >&2
    echo "       that would fail identically. Accept the licence at" >&2
    echo "       https://ux.priorlabs.ai (Licenses tab), then re-run." >&2
    exit 3
fi
echo "########## PREFLIGHT OK ##########"

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

# ---- 6. Emit results through the LOG STREAM ----
# This is the only return channel that always works:
#   * `vastai execute` is NOT a shell -- it runs only ls/rm/du, so it can neither
#     run a script nor read a file (a 400 "Invalid command given" otherwise).
#   * SSH needs a registered key, and a TEAM-context account refuses to create one.
#   * `vastai copy` wants --identity, i.e. a key again.
# So the container log is it. Keep the payload to the small essentials (metrics
# plus each run's meta.json) -- tens of KB, not the full 252 KB output tree.
cd outputs/finetune/pilot 2>/dev/null || { echo "__ARTIFACTS_B64_BEGIN__"; echo "__ARTIFACTS_B64_END__"; exit 0; }
PAYLOAD="pilot_metrics.parquet"
for f in */meta.json; do [ -f "$f" ] && PAYLOAD="$PAYLOAD $f"; done
# Predictions are useful but sizeable; include only if modest.
if [ -f pilot_predictions.parquet ] && [ "$(wc -c < pilot_predictions.parquet)" -lt 300000 ]; then
    PAYLOAD="$PAYLOAD pilot_predictions.parquet"
fi
echo
echo "__ARTIFACTS_B64_BEGIN__"
tar czf - $PAYLOAD 2>/dev/null | base64 -w0 2>/dev/null
echo
echo "__ARTIFACTS_B64_END__"
finish
