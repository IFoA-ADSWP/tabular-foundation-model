"""Rescore: recompute metrics from a run's arrays, and compare them to its record (#361).

One command, no refitting: `rescore --run <dir>` recomputes the five metrics a pilot run records
and reports, per arm × seed × metric, whether each recomputation agrees with the record. The
identity decisions are #356's (name plus a version, defined in `docs/analyses/METRIC_REGISTRY.md`)
and the interface is #357's (long-format CSV, fail closed).

**Integrity** comes from `capture_reader.read_run`: every slot is verified against the manifest
and the record before a number is computed, and a disagreement refuses naming both hashes. The
predictions export (#387) reads through the same function, so the two tools cannot disagree about
what "verified" means.
"""

from __future__ import annotations

import csv
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from capture_reader import read_run
from provenance import csv_cell
from metrics import (
    brier,
    expected_calibration_error,
    gini,
    log_loss,
    mae,
    medae,
    poisson_deviance,
    pr_auc,
    rmse,
    rmsle,
    roc_auc,
    weighted_rmse,
)
from run_capture import CaptureRefused

TOOL_VERSION = "2"  # 2: the fold column (#538)
DEFAULT_METRICSET = "recorded-five"
REGRESSION_METRICSET = "regression"
DEFAULT_OUT_DIR = Path(__file__).resolve().parents[1] / "docs" / "analyses" / "data"

FIELDS = (
    "metric",
    "metric_version",
    "value",
    "seed",
    "fold",
    "arm",
    "capture_sha",
    "tool_version",
    "source",
    "recorded_value",
    "agrees",
)

# Measured on the anchor: recomputing from the committed float32 arrays differs from the record
# by at most 3.4e-08 (B_ft10, seed 44). A tighter tolerance would refuse an honest run.
AGREES_REL_TOL = 1e-6
AGREES_ABS_TOL = 1e-9


class RescoreRefused(Exception):
    """A rescore that cannot make an honest claim. The message names what is missing."""


@dataclass(frozen=True)
class Metric:
    """One registry row: a name, the definition's version, and the record key it compares to."""

    name: str
    version: str
    record_key: str
    compute: Callable[..., float]
    weighted: bool = False


RECORDED_FIVE = (
    Metric("auc", "1", "roc_auc", roc_auc),
    Metric("pr_auc", "1", "pr_auc", pr_auc),
    Metric("brier", "1", "brier", brier),
    Metric("log_loss", "1", "log_loss", log_loss),
    Metric("ece", "1", "ece", expected_calibration_error),
)

# The regression set (#538). `record_key` is the record field a run at that definition writes;
# the verdict metric is resolved by name in `_recorded_value`, because a slot has one target.
REGRESSION_SIX = (
    Metric("rmse", "1", "rmse", rmse),
    Metric("mae", "1", "mae", mae),
    Metric("medae", "1", "medae", medae),
    Metric("rmsle", "1", "rmsle", rmsle),
    Metric("poisson_deviance", "1", "poisson_deviance", poisson_deviance),
    Metric("gini", "1", "gini", gini),
    # The grouped severity verdict metric (#555). It needs the slot's `weights.npy`, so
    # `rescore` refuses to compute it when the capture carries none.
    Metric("weighted_rmse", "1", "weighted_rmse", weighted_rmse, weighted=True),
)

METRICS = {metric.name: metric for metric in (*RECORDED_FIVE, *REGRESSION_SIX)}


def _recorded_value(metric: Metric, record: dict) -> float | None:
    """The value the record holds for this metric, or None when it holds none.

    A regression slot records its verdict metric by *name* (`verdict_metric`) and its value in
    `verdict_metric_value`; reading that value under another metric's name would report RMSE as
    a deviance, so the name must match. `rmse` is also written directly.
    """
    if record.get("verdict_metric") == metric.name:
        value = record.get("verdict_metric_value")
        return None if value is None else float(value)
    value = record.get(metric.record_key)
    return None if value is None else float(value)


@dataclass(frozen=True)
class MetricSet:
    """The metrics a run of the tool covers, and the name their file and rows carry."""

    name: str
    metrics: tuple[Metric, ...]


DEFAULT_METRIC_SET = MetricSet(DEFAULT_METRICSET, RECORDED_FIVE)
REGRESSION_METRIC_SET = MetricSet(REGRESSION_METRICSET, REGRESSION_SIX)
METRIC_SETS = {
    DEFAULT_METRICSET: DEFAULT_METRIC_SET,
    REGRESSION_METRICSET: REGRESSION_METRIC_SET,
}


def select_metrics(specs: list[str] | None) -> MetricSet:
    """The requested metrics, named so the file says what its rows contain."""
    if not specs:
        return DEFAULT_METRIC_SET

    chosen: list[Metric] = []
    for spec in specs:
        name, _, version = spec.partition("@")
        metric = METRICS.get(name)
        if metric is None:
            known = ", ".join(sorted(METRICS))
            raise RescoreRefused(f"unknown metric {name!r}; known metrics: {known}")
        if version and version != metric.version:
            raise RescoreRefused(
                f"metric {name!r} has no version {version!r}; known versions: {metric.version}"
            )
        if metric not in chosen:
            chosen.append(metric)

    chosen.sort(key=lambda metric: metric.name)
    return MetricSet(
        "+".join(f"{metric.name}-{metric.version}" for metric in chosen),
        tuple(chosen),
    )


def _fold_order(fold: int | None) -> int:
    """Sort a foldless slot before fold 0, so the CSV order is total."""
    return -1 if fold is None else int(fold)


def rescore(
    run_dir: Path,
    *,
    metric_set: MetricSet = DEFAULT_METRIC_SET,
    out_dir: Path | None = None,
) -> Path:
    """Recompute `metrics` over every arm × seed slot and write the long-format CSV."""
    run_dir = Path(run_dir)
    run = read_run(run_dir)

    rows: list[dict] = []
    for slot in run.slots:
        for metric in metric_set.metrics:
            if metric.weighted:
                if slot.weights is None:
                    # A weightless capture cannot produce this metric; skipping it keeps an old
                    # frequency run rescorable. A v4 severity capture always carries the weights,
                    # and the reader refuses one that does not.
                    continue
                value = metric.compute(slot.truth, slot.predictions, slot.weights)
            else:
                value = metric.compute(slot.truth, slot.predictions)
            recorded = _recorded_value(metric, slot.record)
            agrees = (
                None
                if recorded is None
                else math.isclose(
                    value, recorded, rel_tol=AGREES_REL_TOL, abs_tol=AGREES_ABS_TOL
                )
            )
            rows.append(
                {
                    "metric": metric.name,
                    "metric_version": metric.version,
                    "value": value,
                    "seed": slot.seed,
                    "fold": slot.fold,
                    "arm": slot.arm,
                    "capture_sha": slot.capture_sha,
                    "tool_version": TOOL_VERSION,
                    "source": slot.source,
                    "recorded_value": recorded,
                    "agrees": agrees,
                }
            )

    rows.sort(key=lambda row: (row["arm"], row["seed"], _fold_order(row["fold"]), row["metric"]))

    out_dir = Path(out_dir) if out_dir is not None else DEFAULT_OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{run.run_id}-rescore-{metric_set.name}.csv"
    with target.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: csv_cell(row[field]) for field in FIELDS})
    return target


def main(argv=None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Recompute metrics from a run's arrays and compare them to its record.",
    )
    parser.add_argument("--run", required=True, type=Path, help="a run directory, e.g. results/<run_id>")
    parser.add_argument(
        "--metric",
        action="append",
        metavar="NAME[@VERSION]",
        help="a metric to compute; repeatable. Default: the recorded five, compared to the record",
    )
    parser.add_argument(
        "--metric-set",
        choices=sorted(METRIC_SETS),
        default=None,
        help="a named set to compute (default: recorded-five); --metric overrides it",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="where the CSV goes (default: docs/analyses/data/)",
    )
    args = parser.parse_args(argv)

    if args.metric_set is not None and args.metric:
        parser.error("--metric-set and --metric are alternatives; --metric names its own set")

    try:
        metric_set = (
            METRIC_SETS[args.metric_set]
            if args.metric_set is not None
            else select_metrics(args.metric)
        )
        target = rescore(args.run, metric_set=metric_set, out_dir=args.out_dir)
    except (RescoreRefused, CaptureRefused) as exc:
        print(f"rescore: {exc}", file=sys.stderr)
        return 1
    print(f"rescore: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
