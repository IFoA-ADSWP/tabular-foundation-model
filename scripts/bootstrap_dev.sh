#!/usr/bin/env bash
# Build the local environment the repository actually pins (#530).
#
# The canonical test command in AGENTS.md is `pytest tests/ -q`. That command means nothing until
# an interpreter exists whose packages match requirements.lock, so this is the thing to run first:
#
#   ./scripts/bootstrap_dev.sh
#   .venv/bin/pytest tests/ -q
#
# Idempotent: an existing .venv is refreshed, not recreated. Pass --recreate to throw it away.
#
# Why the lock and not requirements.txt: requirements.txt states ranges (`pandas>=2,<3`), so a
# fresh resolve can drift onto a major version the code does not support. A session that did that
# produced eight failures that were the environment, not the change.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PYTHON="${PYTHON:-python3.12}"
VENV="${VENV:-$REPO_ROOT/.venv}"
RECREATE=0
[ "${1:-}" = "--recreate" ] && RECREATE=1

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "error: $PYTHON not found. The lock needs Python 3.12 (tabpfn 8.5.0 needs >= 3.10;" >&2
  echo "       v3 and the dataclass syntax in this repo need >= 3.10 and are tested on 3.12)." >&2
  exit 1
fi

if [ "$RECREATE" -eq 1 ] && [ -d "$VENV" ]; then
  echo "== removing $VENV"
  rm -rf "$VENV"
fi

if [ ! -d "$VENV" ]; then
  echo "== creating $VENV with $("$PYTHON" --version 2>&1)"
  "$PYTHON" -m venv "$VENV"
fi

echo "== installing requirements.lock (this downloads torch and the TabPFN wheel once)"
"$VENV/bin/python" -m pip install --quiet --upgrade pip
"$VENV/bin/python" -m pip install --quiet -r requirements.lock
"$VENV/bin/python" -m pip install --quiet pytest

echo "== checking the pins and the imports the repository depends on"
"$VENV/bin/python" - <<'PY'
import importlib

import numpy
import pandas
import scipy
import sklearn

import tabpfn

print(
    f"   python {__import__('sys').version.split()[0]}  "
    f"tabpfn {tabpfn.__version__}  numpy {numpy.__version__}  "
    f"pandas {pandas.__version__}  scipy {scipy.__version__}  "
    f"sklearn {sklearn.__version__}"
)
for name in ("matplotlib", "lightgbm", "catboost"):
    try:
        importlib.import_module(name)
    except ModuleNotFoundError:
        print(f"   note: {name} is not installed (some benchmark and diagnostic scripts need it)")
PY

cat <<EOF

Environment ready.

  .venv/bin/pytest tests/ -q          # the full gate (~9 minutes on this machine)
  .venv/bin/pytest tests/test_positive_control.py -q   # a targeted suite, seconds
  .venv/bin/ruff check scripts/ src/ tests/
  ./scripts/check.sh                  # all eight checks, as CI runs them
EOF
