#!/usr/bin/env python3
"""The frequency/severity fair test's verdict, from its captures (#555, #564).

    python scripts/analyses/freq_sev_fair_test.py \\
        --frequency-french 20261112T164543Z \\
        --frequency-spanish 20261112T184155Z \\
        --severity-french 20261112T210029Z \\
        --severity-spanish 20261112T220641Z

Reproduces the registered statistic from the retained captures rather than from a launch summary:

    r_{t,f,s} = (M(A_raw) - M(B_ft30)) / M(A_raw)

averaged over the three seeds inside each fold to `r_{t,f}`; the target's interval is a paired t
over five folds (4 df); the task's interval is the registered **two-way bootstrap** that resamples
portfolios and folds (10,000 draws), and the task mean is the mean of the two portfolio means.

The decision rule is the one in the pre-registration, not a reading of the numbers:

    Go            CI excludes zero AND the point estimate is at or above the floor
    No-go         CI upper bound is below the floor — a meaningful gain is excluded
    Inconclusive  CI covers both zero and the floor, or a target is underpowered

Floors: frequency task 2% (pooled); Spanish frequency 4% per target and it does not decide the
task; severity task 2%. If the two portfolios of a task disagree in sign the task is heterogenous
and no task-level gain is claimed.

`--row-scale-french <run id>` adds the #572 row-scaling arm on `severity_french`. It is reported
beside the registered targets and **not** folded into the severity task: the registered verdict is
the 10,000-row pair, and the arm asks whether a larger budget changes it rather than replacing it.
Its summary entry carries the per-fold ratios and the training budgets the folds recorded, because
the verdict document quotes both.

Only `meta.json` is read: the verdict metric's value is recorded per slot at capture time, so the
verdict recomputes from the manifest's own numbers without loading the arrays.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import defaultdict
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
RESULTS = _REPO / "results"

CONTROL = "A_raw"
TREATMENT = "B_ft30"
FLOOR_FREQUENCY = 0.02
FLOOR_FREQUENCY_SPANISH = 0.04
FLOOR_SEVERITY = 0.02
T975_DF4 = 2.776


def fold_ratios(run_dir: Path) -> dict[int, float]:
    """`r_{t,f}` for every fold: the per-seed ratios, averaged inside the fold.

    Seeds are paired by their id. Averaging the two arms' sorted values instead would compare
    seed 0's control with seed 1's treatment whenever the ordering differed, which is a different
    statistic and quietly shifts the mean.
    """
    pairs: dict[tuple[int, int], dict[str, float]] = defaultdict(dict)
    for meta in run_dir.glob("*/*/seed*_fold*/meta.json"):
        record = json.loads(meta.read_text())
        arm = record.get("arm")
        if arm not in (CONTROL, TREATMENT):
            continue
        seed = record.get("seed")
        fold = record.get("fold")
        if seed is None or fold is None:
            continue
        pairs[(int(fold), int(seed))][arm] = float(record["verdict_metric_value"])

    by_fold: dict[int, list[float]] = defaultdict(list)
    for (fold, _seed), arms in sorted(pairs.items()):
        if CONTROL not in arms or TREATMENT not in arms:
            raise SystemExit(f"{run_dir}: fold {fold} seed {_seed} is missing an arm")
        by_fold[fold].append((arms[CONTROL] - arms[TREATMENT]) / arms[CONTROL])
    return {fold: _mean(values) for fold, values in sorted(by_fold.items())}


def _mean(values) -> float:
    values = list(values)
    return sum(values) / len(values)


def fold_train_rows(run_dir: Path) -> list[int]:
    """The distinct training-row budgets the captured folds recorded, ascending."""
    rows = set()
    for meta in run_dir.glob("*/*/seed*_fold*/meta.json"):
        record = json.loads(meta.read_text())
        if record.get("train_rows") is not None:
            rows.add(int(record["train_rows"]))
    return sorted(rows)


def target_interval(ratios: dict[int, float]) -> tuple[float, float, float]:
    """Mean `r`, its half-width and standard deviation across folds."""
    values = list(ratios.values())
    mean = _mean(values)
    sd = math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))
    return mean, T975_DF4 * sd / math.sqrt(len(values)), sd


def target_summary(values: dict[int, float], run_id: str, floor: float) -> dict:
    """One target's row: its interval, MDE, floor and the registered decision."""
    mean, half, sd = target_interval(values)
    return {
        "run_id": run_id,
        "mean": mean,
        "ci": [mean - half, mean + half],
        "sd_fold": sd,
        "mde": 2.8016 * sd / math.sqrt(len(values)),
        "floor": floor,
        "decision": decide(mean, mean - half, mean + half, floor),
    }


def task_interval(
    portfolios: list[dict[int, float]], reps: int = 10_000, seed: int = 42
) -> tuple[float, float, float]:
    """Mean of the portfolio means, and the registered two-way bootstrap interval."""
    mean = _mean(_mean(p.values()) for p in portfolios)
    folds = [sorted(p) for p in portfolios]
    rng = random.Random(seed)
    draws = []
    for _ in range(reps):
        picked = [rng.choice(portfolios) for _ in portfolios]
        means = []
        for portfolio, fold_ids in zip(picked, folds):
            sample = [rng.choice(fold_ids) for _ in fold_ids]
            means.append(_mean(portfolio[f] for f in sample))
        draws.append(_mean(means))
    draws.sort()
    return mean, draws[int(0.025 * reps)], draws[int(0.975 * reps)]


def decide(point: float, low: float, high: float, floor: float) -> str:
    if low <= 0 <= high:
        return "Inconclusive"
    if point >= floor and low > 0:
        return "Go"
    if high < floor:
        return "No-go"
    return "Inconclusive"


def _print_target(label: str, row: dict) -> None:
    """One table row: the label with `r`, its interval, MDE, floor and decision."""
    low, high = row["ci"]
    print(
        f"{label:<18}{row['mean']:>+8.2%}   [{low:>+6.2%}, {high:>+6.2%}]"
        f"{row['mde']:>7.2%}{row['floor']:>7.0%}  {row['decision']}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for name in ("frequency-french", "frequency-spanish", "severity-french", "severity-spanish"):
        parser.add_argument(f"--{name}", required=True, help="run id under results/")
    parser.add_argument("--reps", type=int, default=10_000)
    parser.add_argument("--json", action="store_true", help="print the summary as JSON")
    parser.add_argument(
        "--row-scale-french",
        default=None,
        metavar="RUN_ID",
        help="the #572 row-scaling arm on severity_french; reported separately, not in the task",
    )
    args = parser.parse_args(argv)

    ids = {
        "frequency_french": args.frequency_french,
        "frequency_spanish": args.frequency_spanish,
        "severity_french": args.severity_french,
        "severity_spanish": args.severity_spanish,
    }
    ratios = {target: fold_ratios(RESULTS / run_id) for target, run_id in ids.items()}

    floors = {
        "frequency_french": FLOOR_FREQUENCY,
        "frequency_spanish": FLOOR_FREQUENCY_SPANISH,
        "severity_french": FLOOR_SEVERITY,
        "severity_spanish": FLOOR_SEVERITY,
    }
    summary: dict = {"targets": {}, "tasks": {}}
    for target, values in ratios.items():
        summary["targets"][target] = target_summary(values, ids[target], floors[target])

    for task, members, floor in (
        ("frequency", ["frequency_french", "frequency_spanish"], FLOOR_FREQUENCY),
        ("severity", ["severity_french", "severity_spanish"], FLOOR_SEVERITY),
    ):
        portfolios = [ratios[m] for m in members]
        signs = {math.copysign(1, _mean(p.values())) for p in portfolios}
        mean, low, high = task_interval(portfolios, args.reps)
        heterogeneous = len(signs) > 1
        summary["tasks"][task] = {
            "members": members,
            "mean": mean,
            "ci": [low, high],
            "floor": floor,
            "heterogeneous": heterogeneous,
            "decision": "Heterogeneous" if heterogeneous else decide(mean, low, high, floor),
        }

    if args.row_scale_french:
        run_dir = RESULTS / args.row_scale_french
        values = fold_ratios(run_dir)
        summary["row_scale"] = {
            **target_summary(values, args.row_scale_french, FLOOR_SEVERITY),
            "target": "severity_french",
            "folds": {str(fold): value for fold, value in values.items()},
            "train_rows": fold_train_rows(run_dir),
        }

    if args.json:
        print(json.dumps(summary, indent=2))
        return 0

    print(f"{'target':<18}{'r':>9}{'95% CI':>20}{'MDE':>8}{'floor':>7}  decision")
    for target, row in summary["targets"].items():
        _print_target(target, row)
    print()
    for task, row in summary["tasks"].items():
        low, high = row["ci"]
        print(
            f"task {task:<13}{row['mean']:>+8.2%}   [{low:>+6.2%}, {high:>+6.2%}]"
            f"{'':>7}{row['floor']:>7.0%}  {row['decision']}"
        )
    if "row_scale" in summary:
        row = summary["row_scale"]
        rows = row["train_rows"]
        budget = f"{rows[0]}–{rows[-1]} rows" if rows else "train rows unrecorded"
        print()
        print(
            f"row-scaling arm (#572: not part of the registered verdict; {row['run_id']}, "
            f"{budget})"
        )
        _print_target(row["target"], row)
        print(
            "per fold: "
            + "  ".join(f"{fold}: {value:+.2%}" for fold, value in row["folds"].items())
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
