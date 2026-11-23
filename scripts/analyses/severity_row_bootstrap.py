#!/usr/bin/env python3
"""The paired row bootstrap the analysis plan registered (#752).

    python scripts/analyses/severity_row_bootstrap.py --target severity_french
    python scripts/analyses/severity_row_bootstrap.py --target severity_spanish --reps 2000

The epoch ladder reported t-intervals over twenty seeds that share five fixed folds. Those contain no
split and no row component, and the statistical analysis plan registered a paired bootstrap over **rows**
instead. This computes that interval from the committed captures and prints it beside the reported one.

Method, fixed by the protocol in #752 and not chosen here:

- each fold's test rows are identical across the twenty seeds (the script asserts it);
- one row resample is drawn per replicate and applied to **every** seed, so the pairing is preserved;
- each seed's relative contrast ``(M_arm - M_raw) / M_raw`` is computed on the resampled rows, then
  averaged across seeds; the replicate's value is that average;
- the 2.5 and 97.5 percentiles of 2,000 replicates are the interval.

Metric: unweighted RMSE on log amount for the French target, weighted RMSE on log cost for the Spanish
(the weights are the committed ``weights.npy``).

**No verdict moves.** The ladder's frozen rule and its CONFIRMED/REFUTED/UNRESOLVED readings stay with
``EPOCH_LADDER_RESULT.md``; this asks only whether the interval the plan registered agrees with the one
reported.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[2]
RESULTS = _REPO / "results"
ARMS = ("A_raw", "B_ft3", "B_ft10", "B_ft30")

TARGETS = {
    "severity_french": {
        "run": "20261121T153848Z",
        "dataset": "freMTPL2sev",
        "weighted": False,
        "reported": (0.0061, 0.0212),   # EPOCH_LADDER_RESULT.md, B_ft30 - A_raw, relative
    },
    "severity_spanish": {
        "run": "20261121T232424Z",
        "dataset": "spanish_motor_severity",
        "weighted": True,
        "reported": (-0.0208, -0.0050),
    },
}


def load(run: str, dataset: str, results: Path = RESULTS) -> tuple[dict, np.ndarray, np.ndarray]:
    """Return {arm: (seeds, rows) predictions}, truth and weights for one target.

    Rows are each seed's fold test sets concatenated in fold order. Folds may be uneven — the French
    target is not divided equally — so the concatenation is per seed, never a reshape. Every seed must
    carry the same test indices within a fold, or the pairing the analysis assumes does not hold.
    """
    base = results / run / dataset
    slots = sorted(base.glob(f"{ARMS[0]}/seed*_fold*"))
    if not slots:
        raise SystemExit(f"{base}: no slots")
    folds = sorted({int(p.name.split("_fold")[1]) for p in slots})
    seeds = sorted({p.name.split("_")[0] for p in base.glob(f"{ARMS[0]}/seed*_fold{folds[0]}")})
    if not seeds:
        raise SystemExit(f"{base}: no seeds")

    truth, weights = [], []
    for fold in folds:
        reference = np.load(base / ARMS[0] / f"{seeds[0]}_fold{fold}" / "test_index.npy")
        for seed in seeds:
            on_disk = np.load(base / ARMS[0] / f"{seed}_fold{fold}" / "test_index.npy")
            if not np.array_equal(reference, on_disk):
                raise SystemExit(f"{base}: test indices differ at {seed}_fold{fold}")
        truth.append(np.load(base / ARMS[0] / f"{seeds[0]}_fold{fold}" / "ground_truth.npy"))
        w = base / ARMS[0] / f"{seeds[0]}_fold{fold}" / "weights.npy"
        weights.append(np.load(w) if w.exists() else np.ones_like(truth[-1]))

    per_seed = {}
    for arm in ARMS:
        per_seed[arm] = np.stack([
            np.concatenate([np.load(base / arm / f"{seed}_fold{fold}" / "predictions.npy")
                            for fold in folds])
            for seed in seeds
        ])
    return per_seed, np.concatenate(truth), np.concatenate(weights)


def rmse(pred: np.ndarray, truth: np.ndarray, weights: np.ndarray, weighted: bool) -> np.ndarray:
    err2 = (pred - truth) ** 2
    if not weighted:
        return np.sqrt(err2.mean(axis=1))
    return np.sqrt((err2 * weights).sum(axis=1) / weights.sum())


def contrasts(per_seed: dict[str, np.ndarray], truth: np.ndarray, weights: np.ndarray,
              weighted: bool) -> dict[str, np.ndarray]:
    """Per-seed relative contrast against A_raw, one value per seed."""
    raw = rmse(per_seed["A_raw"], truth, weights, weighted)
    out = {}
    for arm in ("B_ft30", "B_ft10"):
        out[f"{arm}-A_raw"] = (rmse(per_seed[arm], truth, weights, weighted) - raw) / raw
    return out


def bootstrap(per_seed: dict[str, np.ndarray], truth: np.ndarray, weights: np.ndarray,
              weighted: bool, reps: int, rng: np.random.Generator) -> dict[str, dict]:
    n = truth.size
    draws = {name: [] for name in ("B_ft30-A_raw", "B_ft10-A_raw")}
    for _ in range(reps):
        idx = rng.integers(0, n, n)
        c = contrasts({arm: p[:, idx] for arm, p in per_seed.items()}, truth[idx], weights[idx], weighted)
        for name, value in c.items():
            draws[name].append(float(np.mean(value)))
    point = contrasts(per_seed, truth, weights, weighted)
    out = {}
    for name, values in draws.items():
        values = np.asarray(values)
        out[name] = {
            "point": float(np.mean(point[name])),
            "low": float(np.percentile(values, 2.5)),
            "high": float(np.percentile(values, 97.5)),
        }
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", choices=sorted(TARGETS), default="severity_french")
    parser.add_argument("--reps", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    spec = TARGETS[args.target]
    per_seed, truth, weights = load(spec["run"], spec["dataset"])
    rng = np.random.default_rng(args.seed)
    res = bootstrap(per_seed, truth, weights, spec["weighted"], args.reps, rng)
    if args.json:
        print(json.dumps({"target": args.target, "rows": int(truth.size),
                          "seeds": int(per_seed["A_raw"].shape[0]), "reps": args.reps,
                          "intervals": res, "reported": spec["reported"]}, indent=1))
        return 0
    print(f"{args.target}: {truth.size} rows x {per_seed['A_raw'].shape[0]} seeds, {args.reps} replicates")
    print(f"{'contrast':<18}{'point':>9}{'row-bootstrap 95%':>26}   reported (t, 20 seeds)")
    for name, r in res.items():
        if name == "B_ft30-A_raw":
            rep = spec["reported"]
            shown = f"[{rep[0]*100:+.2f}, {rep[1]*100:+.2f}] %"
        else:
            shown = "—"
        print(f"{name:<18}{r['point']*100:+8.2f}%   [{r['low']*100:+.2f}, {r['high']*100:+.2f}] %   {shown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
