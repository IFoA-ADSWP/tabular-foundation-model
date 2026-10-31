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
from metrics import brier, expected_calibration_error, log_loss, pr_auc, roc_auc
from run_capture import CaptureRefused

TOOL_VERSION = "1"
DEFAULT_METRICSET = "recorded-five"
DEFAULT_OUT_DIR = Path(__file__).resolve().parents[1] / "docs" / "analyses" / "data"

FIELDS = (
    "metric",
    "metric_version",
    "value",
    "seed",
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
    compute: Callable[[object, object], float]


RECORDED_FIVE = (
    Metric("auc", "1", "roc_auc", roc_auc),
    Metric("pr_auc", "1", "pr_auc", pr_auc),
    Metric("brier", "1", "brier", brier),
    Metric("log_loss", "1", "log_loss", log_loss),
    Metric("ece", "1", "ece", expected_calibration_error),
)
METRICS = {metric.name: metric for metric in RECORDED_FIVE}


@dataclass(frozen=True)
class MetricSet:
    """The metrics a run of the tool covers, and the name their file and rows carry."""

    name: str
    metrics: tuple[Metric, ...]


DEFAULT_METRIC_SET = MetricSet(DEFAULT_METRICSET, RECORDED_FIVE)


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
            value = metric.compute(slot.truth, slot.predictions)
            recorded = slot.record.get(metric.record_key)
            agrees = (
                None
                if recorded is None
                else math.isclose(
                    value, float(recorded), rel_tol=AGREES_REL_TOL, abs_tol=AGREES_ABS_TOL
                )
            )
            rows.append(
                {
                    "metric": metric.name,
                    "metric_version": metric.version,
                    "value": value,
                    "seed": slot.seed,
                    "arm": slot.arm,
                    "capture_sha": slot.capture_sha,
                    "tool_version": TOOL_VERSION,
                    "source": slot.source,
                    "recorded_value": None if recorded is None else float(recorded),
                    "agrees": agrees,
                }
            )

    rows.sort(key=lambda row: (row["arm"], row["seed"], row["metric"]))

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
        "--out-dir",
        type=Path,
        default=None,
        help="where the CSV goes (default: docs/analyses/data/)",
    )
    args = parser.parse_args(argv)

    try:
        metric_set = select_metrics(args.metric)
        target = rescore(args.run, metric_set=metric_set, out_dir=args.out_dir)
    except (RescoreRefused, CaptureRefused) as exc:
        print(f"rescore: {exc}", file=sys.stderr)
        return 1
    print(f"rescore: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
