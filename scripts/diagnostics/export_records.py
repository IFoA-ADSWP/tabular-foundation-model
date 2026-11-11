#!/usr/bin/env python3
"""Export diagnostic records as committed tables (#407).

    python scripts/diagnostics/export_records.py --run outputs/diagnostics/d2_importance/

One table per diagnostic under `docs/analyses/data/`, one row per measured unit: a dataset x
family x feature for D2, a dataset for D1. Every row is checked against
`data/raw/MANIFEST.sha256` before anything is written, so the table cannot rest on bytes the run
did not read. `docs/analyses/data/README.md` names each column.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "src"))

from diagnostics_export import main  # noqa: E402  (importable after the src path insert above)

if __name__ == "__main__":
    raise SystemExit(main())
