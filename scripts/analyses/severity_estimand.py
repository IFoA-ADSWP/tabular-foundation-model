#!/usr/bin/env python3
"""What the severity ladder's captures say under a second estimand, and where the dispersion is.

    python scripts/analyses/severity_estimand.py

Post-hoc and exploratory: this reads the two committed severity captures from the epoch ladder
(#672) and reports things the ladder's registered table does not — the same slots scored
unweighted as well as weighted, the spread of the predictions each arm makes, the error by truth
quintile, and, on Spanish, the single-claim and multi-claim strata separately. It sets no bar,
computes no verdict and cannot promote anything: `FINETUNING_STATISTICAL_ANALYSIS_PLAN.md` lists
pooled-policy and per-seed-spread readings as exploratory with no decision role.

The ladder's own contrast table remains the authority for the registered numbers. This script
prints `30 - raw`, `10 - raw` and `3 - raw` and they reproduce the published roundings. The
`10 -> 30` step is deliberately not printed: the ladder note produced that one from a different
relative-difference convention and the two do not agree (French -5.09% there, -4.81% here), so
reprinting it would offer a second number for a contrast that is not this note's subject.

Method: for each arm and seed, the metric is averaged over that seed's five folds; a contrast is
the per-seed relative difference `(M_arm - M_raw) / M_raw`, so the interval is a paired t over 20
seeds (19 df, t = 2.093). A negative percentage is a lower metric, which is better on RMSE.

Only committed captures are read. `--results` points at a checkout of `results/`; the default is
this repository's own tree, so the command is reproducible from a fresh clone.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from src.metrics import rmse, weighted_rmse  # noqa: E402  (repo root set immediately above)

# name, run id, dataset, and whether the registered metric is the weighted one.
FRENCH = ("severity_french", "20261121T153848Z", "freMTPL2sev", False)
SPANISH = ("severity_spanish", "20261121T232424Z", "spanish_motor_severity", True)
ARMS = ("A_raw", "B_ft3", "B_ft10", "B_ft30")
CONTRASTS = (("B_ft30", "A_raw"), ("B_ft10", "A_raw"), ("B_ft3", "A_raw"))
STRATUM = CONTRASTS[0]
T975_DF19 = 2.093024054408263
QUANTILES = 5


def load(run_dir: Path, target: str) -> dict[tuple[str, int, int], dict]:
    """Every slot's truth, prediction and weight, keyed by `(arm, seed, fold)`."""
    slots: dict[tuple[str, int, int], dict] = {}
    for meta in sorted((run_dir / target).glob("*/seed*_fold*/meta.json")):
        slot_dir = meta.parent
        arm = slot_dir.parent.name
        seed, fold = slot_dir.name.split("_")
        slots[(arm, int(seed.removeprefix("seed")), int(fold.removeprefix("fold")))] = {
            "y_true": np.load(slot_dir / "ground_truth.npy").ravel(),
            "y_pred": np.load(slot_dir / "predictions.npy").ravel(),
            "weight": np.load(slot_dir / "weights.npy").ravel(),
        }
    if not slots:
        raise SystemExit(f"{run_dir / target}: no captured slots")
    return slots


def score(slot: dict, weighted: bool) -> float:
    if weighted:
        return weighted_rmse(slot["y_true"], slot["y_pred"], slot["weight"])
    return rmse(slot["y_true"], slot["y_pred"])


def by_seed(slots: dict, weighted: bool) -> dict[str, np.ndarray]:
    """Each arm's metric per seed: the slot values averaged over that seed's folds."""
    seeds = sorted({key[1] for key in slots})
    folds = sorted({key[2] for key in slots})
    return {
        arm: np.array([np.mean([score(slots[(arm, seed, fold)], weighted) for fold in folds]) for seed in seeds])
        for arm in ARMS
    }


def contrast(per_seed: dict[str, np.ndarray], high: str, low: str) -> tuple[float, float, float, int]:
    """Mean relative difference, its 95% interval bounds, and how many seeds improve on `low`."""
    relative = (per_seed[high] - per_seed[low]) / per_seed[low]
    mean = float(relative.mean())
    half = T975_DF19 * float(relative.std(ddof=1)) / np.sqrt(len(relative))
    better = int((per_seed[high] < per_seed[low]).sum())
    return mean, mean - half, mean + half, better


def per_fold_relative(slots: dict, high: str, low: str, weighted: bool) -> list[float]:
    """The contrast inside each fold: the per-seed relative differences, averaged over seeds."""
    seeds = sorted({key[1] for key in slots})
    folds = sorted({key[2] for key in slots})
    return [
        float(np.mean([
            (score(slots[(high, seed, fold)], weighted) - score(slots[(low, seed, fold)], weighted))
            / score(slots[(low, seed, fold)], weighted)
            for seed in seeds
        ]))
        for fold in folds
    ]


def _stratum_sums(slot: dict, keep_rows) -> tuple[float, float]:
    """Weighted squared error and weight total for the rows a stratum keeps, in one slot."""
    keep = keep_rows(slot["weight"])
    squared = (slot["y_true"][keep] - slot["y_pred"][keep]) ** 2
    return float(np.sum(squared * slot["weight"][keep])), float(slot["weight"][keep].sum())


def stratum_rmse(slots: dict, arm: str, keep_rows) -> float:
    """One arm's weighted RMSE inside a stratum, pooled over every slot."""
    squared = 0.0
    weight_sum = 0.0
    for key in sorted(slots):
        if key[0] != arm:
            continue
        cell_squared, cell_weight = _stratum_sums(slots[key], keep_rows)
        squared += cell_squared
        weight_sum += cell_weight
    return float(np.sqrt(squared / weight_sum))


def stratum_by_seed(slots: dict, keep_rows) -> np.ndarray:
    """The per-seed relative difference inside a weight stratum, fold means averaged."""
    seeds = sorted({key[1] for key in slots})
    folds = sorted({key[2] for key in slots})
    high, low = STRATUM
    per_seed = []
    for seed in seeds:
        values = []
        for fold in folds:
            cells = {}
            for arm in (high, low):
                squared, weight = _stratum_sums(slots[(arm, seed, fold)], keep_rows)
                cells[arm] = np.sqrt(squared / weight)
            values.append((cells[high] - cells[low]) / cells[low])
        per_seed.append(float(np.mean(values)))
    return np.array(per_seed)


def report(name: str, run_dir: Path, target: str, registered_weighted: bool) -> None:
    slots = load(run_dir, target)
    seeds = sorted({key[1] for key in slots})
    folds = sorted({key[2] for key in slots})
    print(f"\n{'=' * 78}\n{name} — {run_dir.name} ({len(slots)} slots, seeds {min(seeds)}-{max(seeds)}, folds {folds})")

    per_seed = {}
    for weighted in (False, True):
        label = "weighted" if weighted else "unweighted"
        per_seed[weighted] = by_seed(slots, weighted)
        print(f"\n  arm means, {label} metric")
        for arm in ARMS:
            print(f"    {arm:7s} {per_seed[weighted][arm].mean():.5f}")
        for high, low in CONTRASTS:
            mean, lo, hi, better = contrast(per_seed[weighted], high, low)
            print(f"    {high} - {low}: {mean * 100:+.2f}% [{lo * 100:+.2f}%, {hi * 100:+.2f}%]"
                  f"  seeds better {better}/{len(seeds)}")

    print("\n  per-fold 30 - raw, registered metric")
    for fold, value in enumerate(per_fold_relative(slots, *STRATUM, registered_weighted)):
        print(f"    fold {folds[fold]}: {value * 100:+.2f}%")

    print("\n  prediction spread (std, mean over slots) and correlation with raw's predictions")
    for arm in ARMS:
        std = np.mean([slots[(arm, seed, fold)]["y_pred"].std() for seed in seeds for fold in folds])
        corr = np.mean([np.corrcoef(slots[(arm, seed, fold)]["y_pred"], slots[("A_raw", seed, fold)]["y_pred"])[0, 1]
                        for seed in seeds for fold in folds])
        print(f"    {arm:7s} std={std:.4f}  corr(raw)={corr:.5f}")

    print("\n  RMSE by truth quintile (pooled over slots)")
    pooled = np.concatenate([slots[("A_raw", seed, fold)]["y_true"] for seed in seeds for fold in folds])
    edges = np.quantile(pooled, np.linspace(0.0, 1.0, QUANTILES + 1))
    for arm in ARMS:
        cells = []
        for index in range(QUANTILES):
            squared = []
            for seed in seeds:
                for fold in folds:
                    slot = slots[(arm, seed, fold)]
                    upper = slot["y_true"] <= edges[index + 1] if index == QUANTILES - 1 else slot["y_true"] < edges[index + 1]
                    keep = (slot["y_true"] >= edges[index]) & upper
                    squared.append((slot["y_true"][keep] - slot["y_pred"][keep]) ** 2)
            cells.append(np.sqrt(np.mean(np.concatenate(squared))))
        print(f"    {arm:7s} " + "  ".join(f"Q{index + 1} {value:.4f}" for index, value in enumerate(cells)))
    print("    truth edges:", np.round(edges, 3))

    if registered_weighted:
        print("\n  Spanish strata: single-claim (weight 1) versus multi-claim (weight > 1)")
        high, low = STRATUM
        for label, keep_rows in (("weight = 1", lambda w: w == 1), ("weight > 1", lambda w: w > 1)):
            relative = stratum_by_seed(slots, keep_rows)
            print(f"    {label}: raw {stratum_rmse(slots, low, keep_rows):.5f}, "
                  f"ft30 {stratum_rmse(slots, high, keep_rows):.5f};"
                  f" 30 - raw {relative.mean() * 100:+.2f}%  seeds better {int((relative < 0).sum())}/{len(relative)}")
        for arm in (low, high):
            total = 0.0
            multi = 0.0
            for key in sorted(slots):
                if key[0] != arm:
                    continue
                squared = (slots[key]["y_true"] - slots[key]["y_pred"]) ** 2 * slots[key]["weight"]
                total += float(squared.sum())
                multi += float(squared[slots[key]["weight"] > 1].sum())
            print(f"    weight > 1 rows carry {100 * multi / total:.1f}% of {arm} weighted squared error")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--results", type=Path, default=_REPO / "results",
                        help="a checkout of results/ holding the captures (default: this repo)")
    for name, default_id, _target, _weighted in (FRENCH, SPANISH):
        parser.add_argument(f"--{name.replace('_', '-')}", default=default_id,
                            help=f"run id for {name} (default: {default_id})")
    args = parser.parse_args()

    for name, _default, target, weighted in (FRENCH, SPANISH):
        run_id = getattr(args, name.replace("-", "_"))
        run_dir = args.results / run_id
        if not run_dir.is_dir():
            raise SystemExit(f"{run_dir}: no such capture")
        report(name, run_dir, target, weighted)


if __name__ == "__main__":
    main()
