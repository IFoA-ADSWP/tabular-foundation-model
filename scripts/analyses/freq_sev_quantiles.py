#!/usr/bin/env python3
"""What the captured quantiles say — coverage and pinball, per arm and target (#555).

    python scripts/analyses/freq_sev_quantiles.py \\
        --frequency-french 20261112T164543Z --frequency-spanish 20261112T184155Z \\
        --severity-french 20261112T210029Z --severity-spanish 20261112T220641Z

The fair test's verdict uses point metrics only. This reads the nine quantiles each slot also
carries, so the distributional question is answered from evidence already on disk.

Two readings, and the reason both are printed:

- **Coverage** — the share of truths at or below each quantile. It is the intuitive check and it is
  unreliable on count targets: the French frequency capture carries negative lower quantiles, so no
  observation falls below them and coverage reads 0% at low levels whatever the model knows.
- **Pinball (quantile) loss** — the proper scoring rule for a quantile forecast. It survives
  negative quantiles and is the number to trust when the two disagree.

Slots are paired by `(fold, seed)` between the arms, and the difference is tested with a paired t
over 15 slots (5 folds x 3 seeds, 14 df).
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[2]
RESULTS = _REPO / "results"
LEVELS = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)
CONTROL, TREATMENT = "A_raw", "B_ft30"
T975_DF15 = 2.145


def slots(run_dir: Path, arm: str) -> list[Path]:
    return sorted(run_dir.glob(f"*/{arm}/seed*_fold*"))


def coverage(slot: Path) -> np.ndarray:
    quantiles = np.load(slot / "quantiles.npy")
    truth = np.load(slot / "ground_truth.npy")
    return np.array([float(np.mean(truth <= quantiles[i])) for i in range(len(LEVELS))])


def pinball(slot: Path) -> float:
    quantiles = np.load(slot / "quantiles.npy")
    truth = np.load(slot / "ground_truth.npy")
    losses = [
        np.mean(np.maximum(level * (truth - quantiles[i]), (level - 1) * (truth - quantiles[i])))
        for i, level in enumerate(LEVELS)
    ]
    return float(np.mean(losses))


def paired(before: np.ndarray, after: np.ndarray) -> tuple[float, float]:
    diff = after - before
    mean = float(diff.mean())
    sd = float(diff.std(ddof=1))
    return mean, mean / (sd / math.sqrt(len(diff))) if sd else float("inf")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for name in ("frequency-french", "frequency-spanish", "severity-french", "severity-spanish"):
        parser.add_argument(f"--{name}", required=True, help="run id under results/")
    args = parser.parse_args(argv)

    ids = {
        "frequency_french": args.frequency_french,
        "frequency_spanish": args.frequency_spanish,
        "severity_french": args.severity_french,
        "severity_spanish": args.severity_spanish,
    }
    header = f"{'target':<18}{'arm':<8}" + "".join(f"{level:>7.1f}" for level in LEVELS)
    print(header)
    for target, run_id in ids.items():
        run_dir = RESULTS / run_id
        cover = {arm: np.array([coverage(s) for s in slots(run_dir, arm)]) for arm in (CONTROL, TREATMENT)}
        for arm in (CONTROL, TREATMENT):
            print(f"{target:<18}{arm:<8}" + "".join(f"{v:>7.2f}" for v in cover[arm].mean(axis=0)))
        _, t = paired(cover[CONTROL][:, 0], cover[TREATMENT][:, 0])
        print(f"{'':<18}{'B-A t(low)':<8}{t:>7.1f}")
    print()
    print(f"{'target':<18}{'pinball A':>10}{'pinball B':>10}{'B-A':>9}{'t':>7}  reading")
    for target, run_id in ids.items():
        run_dir = RESULTS / run_id
        before = np.array([pinball(s) for s in slots(run_dir, CONTROL)])
        after = np.array([pinball(s) for s in slots(run_dir, TREATMENT)])
        mean, t = paired(before, after)
        reading = "worse" if t > T975_DF15 else ("better" if t < -T975_DF15 else "no change")
        print(
            f"{target:<18}{before.mean():>10.4f}{after.mean():>10.4f}{mean:>+9.4f}{t:>7.1f}  {reading}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
