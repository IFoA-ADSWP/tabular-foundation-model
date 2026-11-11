"""The anchor datasets, loaded from the pilot runner rather than re-declared.

D1 and D2 both explain "the four anchor datasets", and both must name the same four with the same
files and targets. `scripts/run_pilot.py` already owns that list; a copy in each diagnostic would be
a second source of truth that starts correct and drifts.

The loader is deliberately dynamic: importing `run_pilot` normally would execute the runner's own
module-level state, and its `DATASETS` entry gets `DATA_DIR` resolved there. Loading the file by
path keeps the diagnostic free of the runner's imports while still reading the runner's declaration.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PILOT_SCRIPT = REPO_ROOT / "scripts" / "run_pilot.py"


def load_anchor_datasets(script=PILOT_SCRIPT):
    """`name -> {"file": Path, "target": str}` exactly as the pilot declares it.

    A diagnostic that resolves its datasets through this cannot describe a file the anchor will
    never run, which is the failure the shared function exists to prevent.
    """
    if not Path(script).exists():
        raise SystemExit(f"cannot load the anchor datasets from {script}: no such file")
    spec = importlib.util.spec_from_file_location("_pilot_registry", script)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise SystemExit(f"cannot load the anchor datasets from {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["_pilot_registry"] = module
    spec.loader.exec_module(module)
    return {
        name: {"file": module.DATA_DIR / entry["file"], "target": entry["target"]}
        for name, entry in module.DATASETS.items()
    }
