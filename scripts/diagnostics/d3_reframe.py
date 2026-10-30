#!/usr/bin/env python3
"""D3 -- target reframing: the control, and the boundary of what is free.

The diagnostics design asks whether reframing a frequency target as classification moves TabPFN's
rank. §14.14 already answered that for `spanish_motor_freq` (binary and ordinal, AUC rank #1), so
that result is this diagnostic's **positive control**: if the reading cannot reproduce a known
result, a "flip" on a new dataset means nothing.

Two modes, and the second exists to refuse rather than to run:

- `--control` reads the committed reframe evidence and writes one record per task. It costs nothing
  and proves the reading works.
- `--dataset NAME` **refuses**. Reframing an untouched dataset means fitting every method on it, and
  the reframe runner uses the hosted TabPFN client, so the "analysis only, $0" line in the design
  does not hold for new datasets. The refusal prints the reason and the estimate instead of spending.

Records go through the shared writer into one directory per task, named `<run id>-<dataset>-<task>`.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "src"))

from model_version import resolve_model_path  # noqa: E402  (same-dir module, after the path insert)
from provenance import (  # noqa: E402  (same-dir module, after the path insert)
    DIAGNOSTICS_ROOT,
    DiagnosticRecord,
    matched_context_evidence,
    sha256_file,
    write_diagnostic_record,
)

DIAGNOSTIC = "d3_reframe"
EVIDENCE = _REPO / "scripts" / "eval" / "insurance_benchmark_v1" / "reframe_frequency_results.csv"
# §14.14: reframing moved TabPFN to AUC rank #1 on both tasks. That is the claim being reproduced.
EXPECTED_TABPFN_RANK = 1
# Measured cost of one four-arm run at 10,000 rows. A reframe fits nine methods over five folds,
# so this is the floor, not the estimate.
MEASURED_RUN_USD = 0.0368


def read_ranks(rows, dataset, task, metric="auc"):
    """Per-method mean of `metric` over folds and seeds, ranked high to low.

    Means before ranks: one fold is one noisy estimate, and a rank computed inside a fold cannot
    be compared with a rank computed across methods.
    """
    by_method = defaultdict(list)
    for row in rows:
        if row["dataset"] == dataset and row["task"] == task:
            by_method[row["method"]].append(float(row[metric]))
    if not by_method:
        raise SystemExit(f"no rows for dataset={dataset!r} task={task!r} in the evidence")
    means = {method: mean(values) for method, values in by_method.items()}
    ranked = sorted(means.items(), key=lambda item: -item[1])
    return ranked, means


def control_measurements(rows, dataset, task):
    ranked, means = read_ranks(rows, dataset, task)
    rank = next(i for i, (method, _) in enumerate(ranked, 1) if method == "tabpfn")
    seeds = sorted(
        {int(row["seed"]) for row in rows if row["dataset"] == dataset and row["task"] == task}
    )
    folds = sorted({row["fold"] for row in rows if row["dataset"] == dataset and row["task"] == task})
    leader, leader_mean = ranked[0]
    return {
        "task": task,
        "metric": "auc",
        "n_methods": len(ranked),
        "n_folds": len(folds),
        "seeds": seeds,
        "tabpfn_mean": round(means["tabpfn"], 6),
        "tabpfn_rank": rank,
        "leader": leader,
        "leader_mean": round(leader_mean, 6),
        "control": {
            "expected_tabpfn_rank": EXPECTED_TABPFN_RANK,
            "reproduced": rank == EXPECTED_TABPFN_RANK,
        },
    }


def _run_id():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _refuse_paid(dataset):
    return (
        f"REFUSING: reframing {dataset!r} means fitting every method on it, and the reframe runner "
        f"uses the hosted TabPFN client -- the design's 'analysis only, $0' does not hold for a "
        f"new dataset. Measured floor for one comparable run is ${MEASURED_RUN_USD:.4f}, and a "
        f"reframe is nine methods over five folds. The ticket says to stop rather than spend; do "
        f"that, and get an estimate agreed first."
    )


def main(argv=None, *, root=None, evidence=None):
    parser = argparse.ArgumentParser(description="D3 -- reframe control, and the paid boundary.")
    parser.add_argument("--control", action="store_true", help="reproduce §14.14 from committed evidence")
    parser.add_argument("--dataset", metavar="NAME", help="refuse: reframing a new dataset spends money")
    parser.add_argument("--run-id", default=None, help="record directory prefix (default: UTC now)")
    args = parser.parse_args(argv)

    if args.dataset and not args.control:
        raise SystemExit(_refuse_paid(args.dataset))
    if not args.control:
        parser.error("give --control")

    source = Path(evidence or EVIDENCE)
    if not source.exists():
        raise SystemExit(f"no evidence at {source}")
    with source.open(newline="") as handle:
        rows = list(csv.DictReader(handle))

    dataset = "spanish_motor_freq"
    base = args.run_id or _run_id()
    verdicts = []
    for task in ("binary", "ordinal"):
        measurements = control_measurements(rows, dataset, task)
        verdicts.append(measurements["control"]["reproduced"])
        record = DiagnosticRecord(
            diagnostic=DIAGNOSTIC,
            run_id=f"{base}-{dataset}-{task}",
            dataset_name=f"{dataset}-{task}",
            dataset_sha256=sha256_file(source),
            # Reframing reads committed results here; the version is the one those results were
            # produced under, resolved from the environment rather than inferred from a filename.
            model_version=resolve_model_path(),
            seed=None,
            matched_context=matched_context_evidence(),
            measurements=measurements,
        )
        written = write_diagnostic_record(record, root=root or DIAGNOSTICS_ROOT)
        print(f"{DIAGNOSTIC} {record.dataset_name}: tabpfn rank {measurements['tabpfn_rank']} -> {written}")

    if not all(verdicts):
        raise SystemExit(
            "CONTROL FAILED: the reading did not reproduce §14.14, so no flip on a new dataset "
            "would be interpretable."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
