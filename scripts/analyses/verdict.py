#!/usr/bin/env python3
"""What a run can claim — per-seed deltas, the null band, and the design's resolution (#398).

    python scripts/analyses/verdict.py --run results/<run_id> --delta 0.002
    python scripts/analyses/verdict.py --run results/20261031T021845Z --reps 1000

Reads a verified **Capture** and prints three things for every tuned arm: its per-seed deltas against
the in-run `A_raw`, the permutation null's spread and false-positive rate, and the seed count the target
effect needs. The reading (pass / equivalence / unresolved) is computed from the interval and the Brier
veto, never asserted.

Fails closed, naming what is missing, on: no baseline arm, fewer than two seeds, a non-positive target
effect, or too few permutations to support a band.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "src"))

from verdict import main  # noqa: E402  (importable after the src path insert above)

if __name__ == "__main__":
    raise SystemExit(main())
