#!/usr/bin/env python3
"""Export a run's predictions as one table a colleague can open (#387).

    python scripts/analyses/export_predictions.py --run results/20261031T021845Z

One row per prediction: `run_id, dataset, arm, seed, row, y_true, probability, capture_sha,
source`. Long format, sorted by arm then seed then row, so a diff means the inputs changed.

The arrays are verified before anything is written, through the same reader `rescore` uses: with
a `capture.json` present both hashes must agree, otherwise the command refuses naming both. A
colleague can therefore analyse the table knowing which bytes it rests on.

`row` is the position in the test array, not the row in the source dataset — segment analysis
needs the test indices, which the capture does not yet carry.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "src"))

from predictions_export import main  # noqa: E402  (importable after the src path insert above)

if __name__ == "__main__":
    raise SystemExit(main())
