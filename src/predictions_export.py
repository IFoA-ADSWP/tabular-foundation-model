"""A run's predictions as one table a colleague can open (#387).

The capture is already committed and verifiable, but reading it means numpy, a directory layout,
and the knowledge that row *i* pairs with row *i* of `ground_truth.npy`. This writes the same
evidence as one long-format CSV — a row per prediction — so an actuarial colleague can open it in
a spreadsheet, R or pandas and compute their own metric without our code.

It verifies before it writes, through `capture_reader.read_run`: with a `capture.json` present
both hashes must agree, otherwise the export refuses naming both. A colleague cannot export
altered arrays, and a local mutation is a refusal rather than a quiet table.

`row` is the position in the test array, not the row in the source dataset. Segment and fairness
analysis need the test indices, which the capture does not carry (#387's out-of-scope section).
"""

from __future__ import annotations

import csv
from pathlib import Path

from capture_reader import read_run
from provenance import csv_cell
from run_capture import CaptureRefused

FIELDS = (
    "run_id",
    "dataset",
    "arm",
    "seed",
    "row",
    "y_true",
    "probability",
    "capture_sha",
    "source",
)

DEFAULT_OUT_DIR = Path(__file__).resolve().parents[1] / "docs" / "analyses" / "data"


def export_predictions(run_dir: Path, *, out_dir: Path | None = None) -> Path:
    """Write one row per prediction for every verified arm × seed slot."""
    run = read_run(Path(run_dir))

    out_dir = Path(out_dir) if out_dir is not None else DEFAULT_OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{run.run_id}-predictions.csv"

    with target.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        for slot in run.slots:
            for index in range(len(slot.predictions)):
                row = {
                    "run_id": run.run_id,
                    "dataset": run.dataset,
                    "arm": slot.arm,
                    "seed": slot.seed,
                    "row": index,
                    "y_true": int(slot.truth[index]),
                    "probability": float(slot.predictions[index]),
                    "capture_sha": slot.capture_sha,
                    "source": slot.source,
                }
                writer.writerow({field: csv_cell(row[field]) for field in FIELDS})
    return target


def main(argv=None) -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Export a run's predictions as one table a colleague can open.",
    )
    parser.add_argument("--run", required=True, type=Path, help="a run directory, e.g. results/<run_id>")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="where the CSV goes (default: docs/analyses/data/)",
    )
    args = parser.parse_args(argv)

    try:
        target = export_predictions(args.run, out_dir=args.out_dir)
    except CaptureRefused as exc:
        print(f"export_predictions: {exc}", file=sys.stderr)
        return 1
    print(f"export_predictions: {target}")
    return 0
