"""Rescore: recompute metrics from a run's arrays, and compare them to its record (#361).

One command, no refitting: `rescore --run <dir>` recomputes the five metrics a pilot run records
and reports, per arm × seed × metric, whether each recomputation agrees with the record. The
identity decisions are #356's (name plus a version, defined in `docs/analyses/METRIC_REGISTRY.md`)
and the interface is #357's (long-format CSV, fail closed).

**Integrity has two sources.** With a `capture.json` (#362) present, the manifest's
`predictions_sha256` must agree with the record's and with the array on disk; a disagreement
refuses, naming both hashes, and an entry with null hashes refuses with its own reason. Without a
manifest the record's `predictions_sha256` verifies the predictions array. The truth array has no
independent hash without a manifest — stated here rather than implied by silence.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

from metrics import brier, expected_calibration_error, log_loss, pr_auc, roc_auc
from run_capture import (
    CAPTURE_SCHEMA_VERSION,
    CaptureRefused,
    discover_slots,
    sha256_array,
)

TOOL_VERSION = "1"
CAPTURE_FILE = "capture.json"
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

    @property
    def identity(self) -> str:
        return f"{self.name}/{self.version}"


RECORDED_FIVE = (
    Metric("auc", "1", "roc_auc", roc_auc),
    Metric("pr_auc", "1", "pr_auc", pr_auc),
    Metric("brier", "1", "brier", brier),
    Metric("log_loss", "1", "log_loss", log_loss),
    Metric("ece", "1", "ece", expected_calibration_error),
)
METRICS = {metric.name: metric for metric in RECORDED_FIVE}


def select_metrics(specs: list[str] | None) -> tuple[tuple[Metric, ...], str]:
    """The requested metrics and the metric-set name their rows are written under."""
    if not specs:
        return RECORDED_FIVE, DEFAULT_METRICSET

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
    metricset = "+".join(f"{metric.name}-{metric.version}" for metric in chosen)
    return tuple(chosen), metricset


def read_manifest(run_dir: Path) -> dict[tuple[str, int], dict] | None:
    """The run's capture entries by arm × seed, or None when no manifest exists."""
    path = Path(run_dir) / CAPTURE_FILE
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    version = payload.get("schema_version")
    if version != CAPTURE_SCHEMA_VERSION:
        raise RescoreRefused(
            f"{path}: unknown capture schema_version {version!r}; this tool reads "
            f"{CAPTURE_SCHEMA_VERSION}"
        )
    return {(entry["arm"], entry["seed"]): entry for entry in payload.get("captures", [])}


def _read_record(slot) -> dict:
    if not slot.record.is_file():
        raise RescoreRefused(f"{slot.record} is missing; there is no record to compare against")
    return json.loads(slot.record.read_text(encoding="utf-8"))


def _verify(slot, entry: dict | None, record: dict) -> tuple[np.ndarray, np.ndarray, str, str]:
    """Load the arrays, prove them against whichever hash source exists, and name it."""
    for path in (slot.predictions, slot.truth):
        if not path.is_file():
            raise RescoreRefused(f"{path} is missing; there is nothing to rescore")

    predictions = np.load(slot.predictions)
    truth = np.load(slot.truth)
    computed = sha256_array(predictions)

    if entry is None:
        recorded_sha = record.get("predictions_sha256")
        if recorded_sha is None:
            raise RescoreRefused(
                f"{slot.record} carries no predictions_sha256 and no {CAPTURE_FILE} exists; "
                "the predictions cannot be verified"
            )
        if computed != recorded_sha:
            raise RescoreRefused(
                f"hash mismatch for {slot.predictions}: array is {computed}, record says "
                f"{recorded_sha}"
            )
        return predictions, truth, computed, "record"

    manifest_sha = entry.get("predictions_sha256")
    if manifest_sha is None:
        raise RescoreRefused(
            f"{CAPTURE_FILE} entry {slot.arm} seed {slot.seed} was not retained: "
            f"{entry.get('reason') or 'no reason stated'}"
        )
    if manifest_sha != computed:
        raise RescoreRefused(
            f"hash mismatch for {slot.predictions}: array is {computed}, {CAPTURE_FILE} says "
            f"{manifest_sha}"
        )
    recorded_sha = record.get("predictions_sha256")
    if recorded_sha is not None and recorded_sha != manifest_sha:
        raise RescoreRefused(
            f"hash mismatch for {slot.arm} seed {slot.seed}: {CAPTURE_FILE} says {manifest_sha}, "
            f"{slot.record} says {recorded_sha}"
        )
    return predictions, truth, manifest_sha, CAPTURE_FILE


def _cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return repr(value)
    return str(value)


def rescore(
    run_dir: Path,
    *,
    metrics: tuple[Metric, ...] = RECORDED_FIVE,
    out_dir: Path | None = None,
) -> Path:
    """Recompute `metrics` over every arm × seed slot and write the long-format CSV."""
    run_dir = Path(run_dir)
    _, slots = discover_slots(run_dir)
    manifest = read_manifest(run_dir)
    if manifest is not None:
        uncaptured = [
            f"{slot.arm} seed {slot.seed}"
            for slot in slots
            if (slot.arm, slot.seed) not in manifest
        ]
        if uncaptured:
            raise RescoreRefused(
                f"{run_dir / CAPTURE_FILE} has no entry for {', '.join(uncaptured)}; "
                "a cited run's manifest covers every arm × seed"
            )

    rows: list[dict] = []
    for slot in slots:
        record = _read_record(slot)
        predictions, truth, capture_sha, source = _verify(
            slot, None if manifest is None else manifest[(slot.arm, slot.seed)], record
        )
        for metric in metrics:
            value = metric.compute(truth, predictions)
            recorded = record.get(metric.record_key)
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
                    "capture_sha": capture_sha,
                    "tool_version": TOOL_VERSION,
                    "source": source,
                    "recorded_value": None if recorded is None else float(recorded),
                    "agrees": agrees,
                }
            )

    rows.sort(key=lambda row: (row["arm"], row["seed"], row["metric"]))

    out_dir = Path(out_dir) if out_dir is not None else DEFAULT_OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = run_dir.resolve().name
    metricset = DEFAULT_METRICSET if metrics == RECORDED_FIVE else "+".join(
        f"{metric.name}-{metric.version}" for metric in metrics
    )
    target = out_dir / f"{run_id}-rescore-{metricset}.csv"
    with target.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _cell(row[field]) for field in FIELDS})
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
        metrics, _ = select_metrics(args.metric)
        target = rescore(args.run, metrics=metrics, out_dir=args.out_dir)
    except (RescoreRefused, CaptureRefused) as exc:
        print(f"rescore: {exc}", file=sys.stderr)
        return 1
    print(f"rescore: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
