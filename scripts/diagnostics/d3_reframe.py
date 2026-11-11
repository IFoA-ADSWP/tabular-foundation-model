#!/usr/bin/env python3
"""D3 -- target reframing: the control, and the boundary of what is free.

The design asks whether reframing a frequency target moves TabPFN's rank. §14.14 answered that for
`spanish_motor_freq` -- binary and ordinal, AUC rank #1, paired-significant at both seeds -- so that
result is this diagnostic's **positive control**: if the reading cannot reproduce a known result, a
flip on a new dataset would mean nothing.

What "reproduce" means here, precisely: the control reads the committed **summary** (§14.14's own
record), and checks it against the figures the report states -- rank #1, the documented mean AUC per
task and seed, and a paired p below 0.05. A control that only checked ordering would still pass with
every number wrong.

Two modes, and the second refuses rather than runs:

- `--control` reads the committed summary and writes one record per task. No spend, no model fits.
- `--dataset NAME` **refuses**. Reframing an untouched dataset means fitting nine methods through
  the hosted TabPFN client; the design's "analysis only, $0" holds only for the dataset whose
  result is already committed.
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "src"))

from provenance import (  # noqa: E402  (importable after the src path insert above)
    DIAGNOSTICS_ROOT,
    DiagnosticRecord,
    matched_context_evidence,
    sha256_file,
    write_diagnostic_record,
)

DIAGNOSTIC = "d3_reframe"
EVIDENCE = _REPO / "scripts" / "eval" / "insurance_benchmark_v1" / "reframe_frequency_summary.csv"
DATASET = "spanish_motor_freq"

# What §14.14 states, as independent expected values. Deliberately literals from the report: a
# control that recomputes them the way the code does can never disagree with the code.
DOCUMENTED_MEAN_AUC = {
    ("binary", 42): 0.7170,
    ("binary", 7): 0.7165,
    ("ordinal", 42): 0.7167,
}
AUC_TOLERANCE = 0.0005
MAX_P = 0.05
MEASURED_RUN_USD = 0.0368


def control_rows(rows, dataset, task):
    """One §14.14 row per seed: AUC only, deduplicated across baseline comparisons.

    The summary file carries a row per (task, seed, baseline) *and* per metric. Reading it without
    both filters silently takes a Poisson-deviance row as if it were AUC -- which is how a control
    can pass on nonsense.
    """
    selected = [
        r
        for r in rows
        if r["dataset"] == dataset and r["task"] == task and r["metric"] == "auc"
    ]
    if not selected:
        raise SystemExit(f"no AUC summary rows for dataset={dataset!r} task={task!r}")
    by_seed = {}
    for row in selected:
        seed = int(row["seed"])
        entry = by_seed.setdefault(seed, {"means": set(), "ranks": set(), "p": []})
        entry["means"].add(round(float(row["tabpfn_mean"]), 6))
        entry["ranks"].add(int(row["tabpfn_rank"]))
        entry["p"].append(float(row["p_paired"]))
    return [
        {
            "seed": seed,
            "tabpfn_mean": next(iter(entry["means"])),
            "tabpfn_rank": next(iter(entry["ranks"])),
            "p_paired": min(entry["p"]),
            "means_disagree": len(entry["means"]) > 1,
            "ranks_disagree": len(entry["ranks"]) > 1,
        }
        for seed, entry in sorted(by_seed.items())
    ]


def control_measurements(rows, dataset, task):
    """Check the recorded claim against the documented one, and record both."""
    checks = []
    for row in control_rows(rows, dataset, task):
        seed = int(row["seed"])
        recorded = float(row["tabpfn_mean"])
        documented = DOCUMENTED_MEAN_AUC.get((task, seed))
        checks.append(
            {
                "seed": seed,
                "recorded_mean_auc": round(recorded, 6),
                "documented_mean_auc": documented,
                "recorded_rank": int(row["tabpfn_rank"]),
                "p_paired": round(float(row["p_paired"]), 6),
                "rank_ok": row["tabpfn_rank"] == 1 and not row["ranks_disagree"],
                "mean_consistent": not row["means_disagree"],
                "mean_ok": documented is not None and abs(recorded - documented) <= AUC_TOLERANCE,
                "significant": float(row["p_paired"]) < MAX_P,
            }
        )
    per_seed_ok = all(
        c["rank_ok"] and c["mean_ok"] and c["significant"] and c["mean_consistent"] for c in checks
    )
    return {
        "task": task,
        "metric": "auc",
        "dataset": dataset,
        "seeds": [c["seed"] for c in checks],
        "checks": checks,
        "control": {"reproduced": per_seed_ok, "tolerance": AUC_TOLERANCE, "max_p": MAX_P},
    }


def _refuse_paid(dataset):
    return (
        f"REFUSING: reframing {dataset!r} means fitting every method on it, and the reframe runner "
        f"uses the hosted TabPFN client -- the design's 'analysis only, $0' does not hold for a new "
        f"dataset. Measured floor for one comparable run is ${MEASURED_RUN_USD:.4f}, and a reframe "
        f"is nine methods over five folds. The ticket says to stop rather than spend."
    )


def main(argv=None, *, root=None, evidence=None):
    parser = argparse.ArgumentParser(description="D3 -- reframe control, and the paid boundary.")
    parser.add_argument("--control", action="store_true", help="reproduce §14.14 from committed evidence")
    parser.add_argument("--dataset", metavar="NAME", help="refuse: reframing a new dataset spends money")
    parser.add_argument("--run-id", default=None, help="record directory prefix (default: UTC now)")
    args = parser.parse_args(argv)

    if args.dataset is not None:
        # `is not None`, not truthiness: `--dataset ""` must not slip through the guard.
        raise SystemExit(_refuse_paid(args.dataset))
    if not args.control:
        parser.error("give --control")

    source = Path(evidence or EVIDENCE)
    if not source.exists():
        raise SystemExit(f"no evidence at {source}")
    with source.open(newline="") as handle:
        rows = list(csv.DictReader(handle))

    # Both tasks before either write: a failure must not leave half a control set behind.
    measurements_by_task = {task: control_measurements(rows, DATASET, task) for task in ("binary", "ordinal")}
    if not all(m["control"]["reproduced"] for m in measurements_by_task.values()):
        raise SystemExit(
            "CONTROL FAILED: the committed evidence does not match §14.14 -- rank, mean AUC or "
            "significance. Nothing was written; a flip elsewhere would not be interpretable."
        )

    base = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for task, measurements in measurements_by_task.items():
        record = DiagnosticRecord(
            diagnostic=DIAGNOSTIC,
            run_id=f"{base}-{DATASET}-{task}",
            # This record reads the summary artifact; it never loads a dataset.
            dataset_name=source.name,
            dataset_sha256=sha256_file(source),
            # §14.14's numbers were produced under v3_default. Stamping the resolver's current label
            # would mix version eras in a claim, which AGENTS.md forbids.
            model_version="v3_default",
            seed=None,
            matched_context=matched_context_evidence(),
            measurements=measurements,
        )
        written = write_diagnostic_record(record, root=root or DIAGNOSTICS_ROOT)
        print(f"{DIAGNOSTIC} {DATASET}/{task}: reproduced -> {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
