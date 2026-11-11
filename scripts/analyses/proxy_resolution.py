#!/usr/bin/env python3
"""Measure the paired half-width a cell resolves at a chosen test size (#444).

The readiness study measured `spanish_motor_lapse` at 1,000 test rows and found a paired
half-width of 0.0154, too coarse for the 0.006 floor. This tool repeats that measurement at the
size a cell would actually run, on the committed CSV and before any spend.

The perturbation is the offline analogue of a fine-tuned rung: the same learner fitted on a 90%
subsample of the training rows, against the learner fitted on all of them, scored on the same
test rows. The half-width is the paired bootstrap interval of ΔAUC.

Usage:
    python scripts/analyses/proxy_resolution.py \
        --csv data/raw/spanish_motor_lapse.csv --target LapseB \
        --drop N_claims_year,Cost_claims_year \
        --train 10000 --test 10000 --seeds 42,43,44 --resamples 4000

Exit codes: 0 measured · 1 the input cannot be measured.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split


def _frame(path: Path, target: str, drop: tuple[str, ...]) -> tuple[np.ndarray, np.ndarray]:
    df = pd.read_csv(path)
    absent = [column for column in (target, *drop) if column not in df.columns]
    if absent:
        raise ValueError(f"{path}: column(s) {absent} are not in the table")
    y = df[target].to_numpy(dtype=int)
    X = (
        pd.get_dummies(df.drop(columns=[target, *drop]), drop_first=False)
        .fillna(0)
        .to_numpy(dtype=float)
    )
    return X, y


def half_width(
    X: np.ndarray,
    y: np.ndarray,
    *,
    train_rows: int,
    test_rows: int,
    seed: int,
    resamples: int,
) -> dict[str, float]:
    """The paired 95% half-width of ΔAUC at one split seed."""
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        train_size=train_rows,
        test_size=test_rows,
        random_state=seed,
        stratify=y,
    )
    rng_subsample = np.random.default_rng(seed)
    subsample = rng_subsample.choice(
        len(X_train), size=int(0.9 * len(X_train)), replace=False
    )

    full = HistGradientBoostingClassifier(random_state=seed).fit(X_train, y_train)
    perturbed = HistGradientBoostingClassifier(random_state=seed).fit(
        X_train[subsample], y_train[subsample]
    )
    p_full = full.predict_proba(X_test)[:, 1]
    p_perturbed = perturbed.predict_proba(X_test)[:, 1]

    rng_boot = np.random.default_rng(seed)
    draws = np.empty(resamples)
    n = len(y_test)
    for i in range(resamples):
        index = rng_boot.integers(0, n, n)
        truth = y_test[index]
        draws[i] = roc_auc_score(truth, p_perturbed[index]) - roc_auc_score(truth, p_full[index])
    low, high = np.percentile(draws, [2.5, 97.5])
    return {
        "delta_auc": float(draws.mean()),
        "low": float(low),
        "high": float(high),
        "half_width": float((high - low) / 2),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--target", required=True)
    parser.add_argument("--drop", default="", help="comma-separated leak columns")
    parser.add_argument("--train", type=int, default=10_000)
    parser.add_argument("--test", type=int, required=True)
    parser.add_argument("--seeds", default="42")
    parser.add_argument("--resamples", type=int, default=4_000)
    args = parser.parse_args(argv)

    drop = tuple(column.strip() for column in args.drop.split(",") if column.strip())
    seeds = [int(seed) for seed in args.seeds.split(",") if seed.strip()]
    if not seeds:
        print("proxy_resolution: --seeds named no seed", file=sys.stderr)
        return 1
    try:
        X, y = _frame(args.csv, args.target, drop)
    except (FileNotFoundError, ValueError) as exc:
        print(f"proxy_resolution: {exc}", file=sys.stderr)
        return 1
    if args.train + args.test > len(y):
        print(
            f"proxy_resolution: {len(y)} rows cannot supply {args.train} train + {args.test} test",
            file=sys.stderr,
        )
        return 1

    widths = []
    for seed in seeds:
        result = half_width(
            X, y, train_rows=args.train, test_rows=args.test, seed=seed, resamples=args.resamples
        )
        widths.append(result["half_width"])
        print(
            f"seed {seed}: delta {result['delta_auc']:+.4f} "
            f"CI [{result['low']:+.4f}, {result['high']:+.4f}] "
            f"half-width {result['half_width']:.4f}"
        )
    print(
        f"train {args.train} test {args.test} resamples {args.resamples}: "
        f"median half-width {float(np.median(widths)):.4f} max {max(widths):.4f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
