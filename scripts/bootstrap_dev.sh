#!/usr/bin/env bash
# Build the local environment from requirements.lock, and prove it matches (#530).
#
#   ./scripts/bootstrap_dev.sh              # create or refresh .venv
#   VENV=/tmp/env ./scripts/bootstrap_dev.sh   # a named environment instead
#   ./scripts/bootstrap_dev.sh --recreate   # delete and rebuild
#
# The canonical test command in AGENTS.md is `pytest tests/ -q`. That command means nothing until an
# interpreter exists whose packages match the lock, so this is the thing to run first. The script
# asserts the pins rather than printing them: a venv that is merely importable can still be the
# wrong environment, which is the failure this exists to prevent.
#
# Why the lock and not requirements.txt: the ranges in requirements.txt admit a drift *within* them
# (scipy 1.10 vs 1.17, for example), so two machines can both satisfy the file and disagree on the
# result. The lock fixes one set of bytes.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PYTHON="${PYTHON:-python3.12}"
VENV="${VENV:-$REPO_ROOT/.venv}"
RECREATE=0
for arg in "$@"; do
  case "$arg" in
    --recreate) RECREATE=1 ;;
    *)
      echo "error: unknown argument: $arg" >&2
      echo "usage: $(basename "$0") [--recreate]   (PYTHON=, VENV= override the defaults)" >&2
      exit 2
      ;;
  esac
done

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "error: $PYTHON not found. This repository is tested on Python 3.12, and the lock's" >&2
  echo "       numpy<2 pin has no wheel for 3.13. Set PYTHON= to another 3.12 binary." >&2
  exit 1
fi

if [ "$RECREATE" -eq 1 ] && [ -d "$VENV" ]; then
  # The path is caller-controlled, so refuse anything that is not a virtualenv and anything whose
  # removal would take more than the venv with it.
  if [ ! -f "$VENV/pyvenv.cfg" ]; then
    echo "error: refusing to remove $VENV: it is not a virtualenv (no pyvenv.cfg)" >&2
    exit 1
  fi
  case "$VENV" in
    "" | "/" | "$HOME")
      echo "error: refusing to remove $VENV" >&2
      exit 1
      ;;
  esac
  echo "== removing $VENV"
  rm -rf "$VENV"
fi

if [ ! -d "$VENV" ]; then
  echo "== creating $VENV with $("$PYTHON" --version 2>&1)"
  "$PYTHON" -m venv "$VENV"
fi

echo "== installing requirements.lock (downloads torch and the TabPFN wheel once)"
"$VENV/bin/python" -m pip install --quiet --upgrade pip
"$VENV/bin/python" -m pip install --quiet -r requirements.lock
"$VENV/bin/python" -m pip install --quiet pytest

echo "== asserting the interpreter and the pins"
"$VENV/bin/python" - "$REPO_ROOT/requirements.lock" <<'PY'
import re
import sys
from importlib.metadata import PackageNotFoundError, version

if sys.version_info[:2] != (3, 12):
    raise SystemExit(
        f"error: {sys.version.split()[0]} in the venv; this repository is tested on 3.12 "
        "(the lock's numpy<2 has no 3.13 wheel). Recreate with PYTHON=python3.12."
    )

pins: dict[str, str] = {}
with open(sys.argv[1], encoding="utf-8") as handle:
    for line in handle:
        match = re.match(r"^([A-Za-z0-9_.-]+)==([^\s;]+)\s*$", line)
        if match:
            pins[match.group(1).lower().replace("_", "-")] = match.group(2)

required = ("tabpfn", "numpy", "pandas", "scipy", "scikit-learn")
problems = []
for name in required:
    want = pins.get(name)
    try:
        got = version(name)
    except PackageNotFoundError:
        got = None
    if want is None:
        problems.append(f"{name}: not pinned in requirements.lock")
    elif got != want:
        problems.append(f"{name}: lock {want}, installed {got}")

if problems:
    print("error: the environment does not match requirements.lock", file=sys.stderr)
    for problem in problems:
        print(f"  {problem}", file=sys.stderr)
    raise SystemExit(1)

print("   python " + sys.version.split()[0])
print("   " + ", ".join(f"{name} {pins[name]}" for name in required))
PY

cat <<EOF

Environment ready at $VENV.

  $VENV/bin/pytest tests/ -q                            # the full gate
  $VENV/bin/pytest tests/test_positive_control.py -q    # one suite, seconds
  $VENV/bin/ruff check scripts/ src/ tests/
  ./scripts/check.sh                                    # the same checks CI runs
EOF
