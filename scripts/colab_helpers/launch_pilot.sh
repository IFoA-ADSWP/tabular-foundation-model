#!/bin/bash
# Launch the fine-tuning pilot on a Colab VM as a DETACHED background job.
#
#   export TABPFN_TOKEN="pk_..."
#   bash scripts/colab_helpers/launch_pilot.sh
#
# Returns in seconds. Poll progress with:
#   cat scripts/colab_helpers/poll_pilot.py | colab exec
#
# Why this shape: `colab exec` forwards code to the VM and the CLI's kernel
# poll times out on long silent jobs (pip install, model runs). So we ship the
# work as a detached process and read its log file instead.
#
# The TabPFN licence token is interpolated into the bootstrap locally and
# uploaded for the duration of the run; it is never committed to the repo.

set -euo pipefail

export PATH="$HOME/.local/share/uv/tools/google-colab-cli/bin:$PATH"

: "${TABPFN_TOKEN:?Export TABPFN_TOKEN first: export TABPFN_TOKEN=pk_...}"

BRANCH="${BRANCH:-finetune-v2}"
REPO="https://github.com/IFoA-ADSWP/tabular-foundation-model.git"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# ---- 1. Bootstrap: runs ON THE VM, detached. Contains the token. ----
cat > "$TMP/_bootstrap.py" <<PYEOF
import os, shutil, subprocess, sys

os.environ["TABPFN_TOKEN"] = "${TABPFN_TOKEN}"

WORKDIR = "/content/tfm"
if os.path.exists(WORKDIR):
    shutil.rmtree(WORKDIR)
subprocess.run(["git", "clone", "--branch", "${BRANCH}", "${REPO}", WORKDIR], check=True)
os.chdir(WORKDIR)

# NB: not requirements.txt -- it pins numpy>=1.24,<2 which has no cp313
# wheels, so pip compiles numpy from source (~20 min stall).
subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                "tabpfn", "torch", "scikit-learn", "pandas", "pyarrow", "catboost"],
               check=True)

subprocess.run([sys.executable, "scripts/run_pilot.py"], check=False)
print("BOOTSTRAP FINISHED")
PYEOF

# ---- 2. Launcher: runs ON THE VM, returns immediately. No secret here. ----
cat > "$TMP/_launch.py" <<'PYEOF'
import os, subprocess, sys

env = dict(os.environ, PYTHONUNBUFFERED="1")
with open("/content/pilot.log", "w") as log:
    subprocess.Popen(
        [sys.executable, "-u", "/content/_bootstrap.py"],
        stdout=log, stderr=subprocess.STDOUT,
        start_new_session=True, env=env,
    )
print("LAUNCHED - setup + pilot running detached.")
print("Poll: cat scripts/colab_helpers/poll_pilot.py | colab exec")
PYEOF

# ---- 3. Ship and launch ----
colab upload "$TMP/_bootstrap.py" /content/_bootstrap.py
colab exec -f "$TMP/_launch.py" --timeout 120
