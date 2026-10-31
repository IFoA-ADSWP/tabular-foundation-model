#!/usr/bin/env python3
"""Recompute a run's metrics from its arrays, and compare them to what it recorded (#361).

    python scripts/analyses/rescore.py --run results/20261031T021845Z
    python scripts/analyses/rescore.py --run results/<run_id> --metric auc/1 --metric ece/1

With no `--metric`, the five a pilot run records are recomputed and each is compared to the
record: `agrees` is the point of that mode, a consistency check on the run's own record before
anyone cites a number. Output is one long-format CSV per metric set under `docs/analyses/data/`,
one row per arm × seed × metric, carrying the metric version, the capture hash and the tool
version so a row is self-describing.

Fails closed, naming what is missing, on: no record or arrays, a hash mismatch (naming both
hashes), an unknown metric name, an unknown version, or a capture entry whose array was not
retained.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "src"))

from rescore import main  # noqa: E402  (importable after the src path insert above)

if __name__ == "__main__":
    raise SystemExit(main())
