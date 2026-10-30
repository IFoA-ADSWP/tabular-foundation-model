#!/usr/bin/env python3
"""D1 -- dataset profiling: the structural properties of one table, as one record.

Usage:
    python scripts/diagnostics/d1_profiling.py --csv data/raw/coil2000.csv --target CARAVAN
    python scripts/diagnostics/d1_profiling.py --csv data/raw/coil2000.csv \\
        --target CARAVAN --name coil2000
    python scripts/diagnostics/d1_profiling.py ... --run-id 20261029T120000Z

D1's *content* belongs to `docs/current/FINETUNING_DIAGNOSTICS_DESIGN.md` (#208): class balance,
feature type mix, missingness, target shape, correlation and the feature:row ratio. What this
script is for in #211 is narrower -- it is the first consumer of the shared writer, so D2-D5
inherit one record shape instead of inventing five.

Every run writes one record through `src/provenance.write_diagnostic_record`, landing under
`outputs/diagnostics/d1_profiling/<run_id>-<dataset>/` as `record.json` (source of truth) and
`record.csv` (the one-row view of it). The dataset name is always in the run id, so the same
dataset's directory does not depend on how many others were profiled with it. The diagnostic supplies measurements and nothing else:
the schema version, timestamp, code revision and runtime are stamped by the writer.

Where the record goes is not a choice this script offers. There is no `--out`: #211 says records
land under `outputs/diagnostics/` and deliberately **not** in `scripts/eval/insurance_benchmark_v1/`,
which is the frontier tree with its own lineage, so the location is enforced rather than promised.

A record is refused rather than replaced -- two D1 runs are two runs, and an overwritten record
would carry the second run's timestamp while claiming the first run's profile.
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

from model_version import resolve_model_path  # noqa: E402  (same-dir module, after the path insert)
from provenance import (  # noqa: E402  (same-dir module, after the path insert)
    DIAGNOSTICS_ROOT,
    DiagnosticRecord,
    matched_context_evidence,
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
        # Quantiles rather than a histogram: the design asks for the shape, and quantiles are
        # comparable between datasets where bins are not.
        "quantiles": {
            label: round(float(numeric.quantile(q)), 6)
            for label, q in (("p05", 0.05), ("p25", 0.25), ("p50", 0.5), ("p75", 0.75), ("p95", 0.95))
        },
    }


VIF_MAX_FEATURES = 200


def _max_vif(numeric):
    """The largest variance inflation factor, or (None, reason) when it cannot be computed.

    Computed from the inverse correlation matrix (VIF_i = [R^-1]_ii) so no new dependency is
    added. Bounded on purpose: VIF is a property of the whole numeric block, and a hundred
    features would make the inverse expensive for a number nobody reads.
    """
    if numeric.shape[1] < 2:
        return None, "fewer than two numeric features"
    if numeric.shape[1] > VIF_MAX_FEATURES:
        return None, f"more than {VIF_MAX_FEATURES} numeric features"
    frame = numeric.dropna()
    if len(frame) <= numeric.shape[1] + 1:
        return None, "too few complete rows"
    corr = frame.corr().to_numpy()
    if np.isnan(corr).any():
        return None, "correlation matrix has missing values"
    try:
        inverse = np.linalg.inv(corr)
    except np.linalg.LinAlgError:
        return None, "correlation matrix is singular"
    diagonal = np.diag(inverse)
    if not np.isfinite(diagonal).all() or (diagonal <= 0).any():
        return None, "non-positive variance"
    return round(float(diagonal.max()), 6), None


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

    max_vif, vif_reason = _max_vif(numeric)

    return {
        # Per-column rates, not only the aggregate: a single 40% column and forty 1% columns
        # have the same mean and nothing else in common.
        "missing_by_column": {
            str(col): round(float(rate), 6) for col, rate in missing.items() if rate > 0
        },
        "n_rows": int(len(df)),
        "n_cols": int(df.shape[1]),
        "n_features": int(features.shape[1]),
        "n_numeric_features": int(numeric.shape[1]),
        "n_categorical_features": int(categorical.shape[1]),
        "numeric_to_categorical_ratio": (
            round(numeric.shape[1] / categorical.shape[1], 6) if categorical.shape[1] else None
        ),
        "max_vif": max_vif,
        "vif_reason": vif_reason,
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


def _anchor_registry():
    """The pilot's dataset registry, as name -> {"file", "target"}.

    One source of truth. D1 profiles the datasets the anchor will actually run, so the list
    comes from the runner rather than from a second copy here that can drift.
    """
    import importlib.util

    script = _REPO / "scripts" / "run_pilot.py"
    spec = importlib.util.spec_from_file_location("_pilot_registry", script)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise SystemExit(f"cannot load the pilot registry from {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["_pilot_registry"] = module
    spec.loader.exec_module(module)
    return {
        name: {"file": module.DATA_DIR / entry["file"], "target": entry["target"]}
        for name, entry in module.DATASETS.items()
    }


def _targets(args, datasets):
    """Resolve the invocation into [(name, path, target)] -- one record each."""
    if args.csv is not None:
        return [(args.name or args.csv.stem, args.csv, args.target)]

    registry = datasets if datasets is not None else _anchor_registry()
    if args.all_anchors:
        names = list(registry)
    else:
        names = args.dataset
    unknown = [n for n in names if n not in registry]
    if unknown:
        raise SystemExit(f"unknown dataset(s) {unknown}; the registry holds {sorted(registry)}")
    return [(n, Path(registry[n]["file"]), registry[n]["target"]) for n in names]


def main(argv=None, *, root=None, datasets=None):
    """Run D1 and write one record.

    ``root`` is a test seam, not a command-line option: the CLI cannot name a location, so no
    invocation of this script can put a diagnostic record outside `outputs/diagnostics/`.
    """
    parser = argparse.ArgumentParser(description="D1 -- profile one or more datasets, one record each.")
    parser.add_argument("--csv", type=Path, help="the table to profile (ad-hoc, single file)")
    parser.add_argument("--target", help="target column in --csv")
    parser.add_argument(
        "--dataset",
        action="append",
        default=[],
        metavar="NAME",
        help="profile a registered pilot dataset by name (repeatable)",
    )
    parser.add_argument(
        "--all-anchors",
        action="store_true",
        help="profile every dataset the pilot registry declares",
    )
    parser.add_argument("--name", default=None, help="dataset name recorded (default: file stem)")
    parser.add_argument("--run-id", default=None, help="record directory name (default: UTC now)")
    args = parser.parse_args(argv)

    if args.csv is None and not args.dataset and not args.all_anchors:
        parser.error("give --csv, or --dataset NAME, or --all-anchors")
    if args.csv is not None and args.target is None:
        parser.error("--csv needs --target")

    targets = _targets(args, datasets)
    base_run_id = args.run_id or _run_id()

    # Pre-flight everything before writing anything: a set of records that fails halfway is not
    # recoverable, because the writer refuses to replace the ones already written.
    names = [name for name, _, _ in targets]
    duplicates = sorted({n for n in names if names.count(n) > 1})
    if duplicates:
        raise SystemExit(f"duplicate dataset name(s) {duplicates}: one record per name, per run")
    missing_files = [str(f) for _, f, _ in targets if not f.exists()]
    if missing_files:
        raise SystemExit(f"no such file(s): {missing_files}")

    for index, (name, path, target) in enumerate(targets):
        # The dataset name is always in the run id, so the directory a dataset lands in does not
        # depend on how many datasets were profiled with it. D2-D5 copy this convention.
        record = _profile_one(
            path=path,
            target=target,
            name=name,
            run_id=f"{base_run_id}-{name}",
        )
        written = write_diagnostic_record(record, root=root or DIAGNOSTICS_ROOT)
        print(f"{DIAGNOSTIC} {record.dataset_name}: {written}")
        for key, value in record.measurements.items():
            print(f"  {key:32} {value}")
        if index + 1 < len(targets):
            print()
    return 0


def _profile_one(*, path, target, name, run_id):
    df = pd.read_csv(path)
    measurements = profile_frame(df, target)
    return DiagnosticRecord(
        diagnostic=DIAGNOSTIC,
        run_id=run_id,
        dataset_name=name,
        dataset_sha256=sha256_file(path),
        # D1 runs no model, so this is the version this environment RESOLVES to, not one it
        # used -- recorded because a diagnostic's output is read against model runs and #241's
        # `provenance` block carries the same field. `matched_context.checked` is False below,
        # which is where the absence of a model is stated.
        model_version=resolve_model_path(),
        # No split, so no seed: profiling reads the whole table.
        seed=None,
        matched_context=matched_context_evidence(),
        measurements=measurements,
    )


if __name__ == "__main__":
    raise SystemExit(main())
