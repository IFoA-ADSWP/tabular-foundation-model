#!/usr/bin/env python3
"""Write a run's capture manifest — one `capture.json` per run directory (#362).

Offline over an existing run, no paid path involved:

    python scripts/analyses/make_capture.py --run results/20261031T021845Z

Reads `<run>/<dataset>/<arm>/seed<S>_fold<F>/`, hashes `predictions.npy` and
`ground_truth.npy` as the record does, and writes `capture.json` at the run root. An arm whose
array was not retained still gets an entry: null hashes and a reason naming the file. A run that
cannot be described honestly — no slots, two datasets, a folded slot, a slot with no record —
exits non-zero and names what is wrong.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "src"))

from run_capture import main  # noqa: E402  (importable after the src path insert above)

if __name__ == "__main__":
    raise SystemExit(main())
