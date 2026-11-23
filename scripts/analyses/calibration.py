#!/usr/bin/env python3
"""Probability calibration from the committed prediction captures (#745).

    python scripts/analyses/calibration.py
    python scripts/analyses/calibration.py --targets coil2000 norauto --json

Reads `scripts/eval/insurance_benchmark_v1/predictions/<target>__seed<seed>__<version>.npz`, pools the
five folds, and reports per target: rows, base rate, mean predicted probability, the **calibration
slope and intercept** from a logistic recalibration of `y` on `logit(p)`, the Brier score, and
predicted against observed by decile.

Why a slope: Brier mixes calibration with refinement, so a Brier match cannot show the probabilities
mean what they say. The slope can. A slope of 1 with intercept 0 is perfect; below 1 the probabilities
are too extreme, above 1 too flat.

The bar this answers was registered before the run (issue #745, 2026-11-23): slope in [0.90, 1.10] on
every classification target. Deciles are reported as diagnostics and carry no bar.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[2]
PREDICTIONS = _REPO / "scripts/eval/insurance_benchmark_v1/predictions"

# The six classification targets of the frontier suite, and the seed/release the paper reports.
CLASSIFICATION = ("coil2000", "uslapseagent", "bemtl16", "ausprivauto0405", "bemtl97", "norauto")
SEED = 42
VERSION = "v3.5_default"
BAR = (0.90, 1.10)
EPS = 1e-6
DECILES = 10


def load(target: str, predictions: Path = PREDICTIONS, seed: int = SEED,
         version: str = VERSION) -> tuple[np.ndarray, np.ndarray]:
    """Pool every fold of one target's capture into (predicted probability, outcome)."""
    path = predictions / f"{target}__seed{seed}__{version}.npz"
    if not path.exists():
        raise SystemExit(f"{path}: no committed capture")
    data = np.load(path)
    folds = sorted(
        int(key.split("__fold")[1]) for key in data.files if key.startswith("y_true__fold")
    )
    if not folds:
        raise SystemExit(f"{path}: no folds")
    p = np.concatenate([data[f"tabpfn__fold{i}"] for i in folds]).astype(float)
    y = np.concatenate([data[f"y_true__fold{i}"] for i in folds]).astype(float)
    return np.clip(p, EPS, 1.0 - EPS), y


def slope_intercept(p: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Logistic recalibration: fit y ~ logit(p). Slope 1, intercept 0 is perfect."""
    from sklearn.linear_model import LogisticRegression

    logit = np.log(p / (1.0 - p)).reshape(-1, 1)
    # A large C means effectively unpenalised, so the slope is the plain logistic estimate.
    fit = LogisticRegression(C=1e6, max_iter=1000).fit(logit, y)
    return float(fit.coef_[0, 0]), float(fit.intercept_[0])


def brier(p: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((p - y) ** 2))


def deciles(p: np.ndarray, y: np.ndarray, bins: int = DECILES) -> list[dict]:
    """Mean predicted against observed rate, by quantile bin of the prediction."""
    edges = np.quantile(p, np.linspace(0.0, 1.0, bins + 1))
    edges[0], edges[-1] = -np.inf, np.inf
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        keep = (p > lo) & (p <= hi)
        if not keep.any():
            continue
        rows.append({
            "predicted": float(p[keep].mean()),
            "observed": float(y[keep].mean()),
            "n": int(keep.sum()),
        })
    return rows


def measure(targets: tuple[str, ...] = CLASSIFICATION, predictions: Path = PREDICTIONS,
            seed: int = SEED, version: str = VERSION) -> list[dict]:
    out = []
    for target in targets:
        p, y = load(target, predictions, seed, version)
        slope, intercept = slope_intercept(p, y)
        out.append({
            "target": target,
            "rows": int(y.size),
            "base_rate": float(y.mean()),
            "mean_predicted": float(p.mean()),
            "slope": slope,
            "intercept": intercept,
            "brier": brier(p, y),
            "within_bar": BAR[0] <= slope <= BAR[1],
            "deciles": deciles(p, y),
        })
    return out


def render(results: list[dict]) -> str:
    head = (
        f"| target | rows | base rate | mean predicted | slope | intercept | Brier | bar "
        f"[{BAR[0]:.2f}, {BAR[1]:.2f}] |\n"
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |"
    )
    lines = [head]
    for r in results:
        lines.append(
            f"| {r['target']} | {r['rows']:,} | {r['base_rate']:.4f} | {r['mean_predicted']:.4f} | "
            f"{r['slope']:.3f} | {r['intercept']:+.3f} | {r['brier']:.5f} | "
            f"{'met' if r['within_bar'] else 'MISSED'} |"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--targets", nargs="+", default=list(CLASSIFICATION))
    parser.add_argument("--predictions", type=Path, default=PREDICTIONS)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--version", default=VERSION)
    parser.add_argument("--json", action="store_true", help="machine form instead of the table")
    args = parser.parse_args(argv)

    results = measure(tuple(args.targets), args.predictions, args.seed, args.version)
    if args.json:
        print(json.dumps(results, indent=1))
    else:
        print(render(results))
        print(f"\nBar: slope in [{BAR[0]:.2f}, {BAR[1]:.2f}] on every target (issue #745).")
        missed = [r["target"] for r in results if not r["within_bar"]]
        print("Verdict: " + ("CONFIRMED" if not missed else f"REFUTED — {', '.join(missed)}"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
