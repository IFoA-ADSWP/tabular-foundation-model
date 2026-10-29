#!/usr/bin/env python3
"""D1 -- dataset profiling: the structural properties of one table, as one record.

Usage:
    python scripts/diagnostics/d1_profiling.py --csv data/raw/coil2000.csv --target CARAVAN
    python scripts/diagnostics/d1_profiling.py --csv data/raw/coil2000.csv \\
        --target CARAVAN --name coil2000
    python scripts/diagnostics/d1_profiling.py ... --out /tmp/records --run-id 20261029T120000Z

D1's *content* belongs to `docs/current/FINETUNING_DIAGNOSTICS_DESIGN.md` (#208): class balance,
feature type mix, missingness, target shape, correlation and the feature:row ratio. What this
script is for in #211 is narrower -- it is the first consumer of the shared writer, so D2-D5
inherit one record shape instead of inventing five.

Every run writes one record through `src/provenance.write_diagnostic_record`, landing under
`outputs/diagnostics/d1_profiling/<run_id>/` as `record.json` (source of truth) and
`record.csv` (the one-row view of it). The diagnostic supplies measurements and nothing else:
the schema version, timestamp and code revision are stamped by the writer.

A record is refused rather than overwritten -- two D1 runs are two runs, and a silent
overwrite is how a record stops describing what happened.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from math import log2
from pathlib import Path

import numpy as np
import pandas as pd

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "src"))

from provenance import (  # noqa: E402
    DIAGNOSTICS_ROOT,
    DiagnosticRecord,
    sha256_file,
    write_diagnostic_record,
)

DIAGNOSTIC = "d1_profiling"
# A categorical column at or above this many distinct values is flagged: one-hot encoding it
# can produce more columns than the dataset has rows, which changes what TabPFN sees.
HIGH_CARDINALITY = 50


def _target_profile(values):
    """Class balance for a binary target; shape for anything else."""
    values = values.dropna()
    if values.nunique() <= 2:
        p = float(values.astype(float).mean()) if len(values) else 0.0
        entropy = 0.0 if p in (0.0, 1.0) else -(p * log2(p) + (1 - p) * log2(1 - p))
        return {
            "kind": "binary",
            "positive_rate": round(p, 6),
            "n_positive": int((values.astype(float) == 1).sum()),
            "entropy_bits": round(entropy, 6),
        }
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return {"kind": "categorical", "n_distinct": int(values.nunique())}
    return {
        "kind": "numeric",
        "n_distinct": int(values.nunique()),
        "zero_inflation_rate": round(float((numeric == 0).mean()), 6),
        "skew": round(float(numeric.skew()), 6) if len(numeric) > 2 else None,
    }


def profile_frame(df, target):
    """D1's measurements for one frame. Counts and ratios only -- no judgement, no model.

    Pure: the frame is handed in, so the profiling rule can be tested on a synthetic table
    without a repository, and a real run has nothing to read except the CSV it was given.
    """
    if target not in df.columns:
        raise SystemExit(f"target column {target!r} is not in the frame: {list(df.columns)}")

    features = df.drop(columns=[target])
    numeric = features.select_dtypes(include="number")
    categorical = features.select_dtypes(exclude="number")

    missing = df.isna().mean()
    one_hot_width = int(numeric.shape[1] + sum(features[c].nunique(dropna=True) for c in categorical))

    max_corr = None
    if numeric.shape[1] >= 2:
        corr = numeric.corr().abs().to_numpy()
        np.fill_diagonal(corr, np.nan)
        if not np.isnan(corr).all():
            max_corr = round(float(np.nanmax(corr)), 6)

    return {
        "n_rows": int(len(df)),
        "n_cols": int(df.shape[1]),
        "n_features": int(features.shape[1]),
        "n_numeric_features": int(numeric.shape[1]),
        "n_categorical_features": int(categorical.shape[1]),
        "n_features_after_one_hot": one_hot_width,
        "feature_row_ratio": round(one_hot_width / max(len(df), 1), 6),
        "missing_rate": round(float(missing.mean()), 6) if len(missing) else 0.0,
        "n_cols_with_missing": int((missing > 0).sum()),
        "max_col_missing_rate": round(float(missing.max()), 6) if len(missing) else 0.0,
        "n_high_cardinality_features": int(
            sum(features[c].nunique(dropna=True) >= HIGH_CARDINALITY for c in categorical)
        ),
        "max_abs_feature_correlation": max_corr,
        "target": _target_profile(df[target]),
    }


def _run_id():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def main(argv=None):
    parser = argparse.ArgumentParser(description="D1 -- profile one dataset into one record.")
    parser.add_argument("--csv", type=Path, required=True, help="the table to profile")
    parser.add_argument("--target", required=True, help="target column in the table")
    parser.add_argument("--name", default=None, help="dataset name recorded (default: file stem)")
    parser.add_argument("--run-id", default=None, help="record directory name (default: UTC now)")
    parser.add_argument(
        "--out",
        type=Path,
        default=DIAGNOSTICS_ROOT,
        help=f"records root (default: {DIAGNOSTICS_ROOT})",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace an existing record for this run id instead of refusing",
    )
    args = parser.parse_args(argv)

    if not args.csv.exists():
        raise SystemExit(f"no such file: {args.csv}")

    df = pd.read_csv(args.csv)
    measurements = profile_frame(df, args.target)

    record = DiagnosticRecord(
        diagnostic=DIAGNOSTIC,
        run_id=args.run_id or _run_id(),
        dataset_name=args.name or args.csv.stem,
        dataset_sha256=sha256_file(args.csv),
        # D1 runs no model: profiling is an analysis of the data. Stating that is the honest
        # record, per docs/MODEL_VERSIONS.md -- a version inferred here would be a guess.
        model_version=None,
        measurements=measurements,
    )
    written = write_diagnostic_record(record, root=args.out, overwrite=args.overwrite)

    print(f"{DIAGNOSTIC} {record.dataset_name}: {written}")
    for key, value in measurements.items():
        print(f"  {key:32} {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
