#!/usr/bin/env python3
"""Paired v3-vs-v3.5 analysis for one regression dataset (issue #216; master report §22).
The regression counterpart of analyze_version_retest.py: it reads the per-fold
predictions written by `run_frontier_benchmark.py --regression --save-predictions` and
fits no hosted model — no API calls.

Inputs (predictions/):
    <ds>__seed42__v3_default.npz      v3, same-day run
    <ds>__seed42__v3.5_default.npz    v3.5

Sections:
  1. Integrity: identical test folds and y_true across the two runs, and every
     non-TabPFN method's predictions bit-identical between them.
  2. Per-method fold means of the dataset's primary metric (metric_fn: RMSE or Poisson
     deviance) and MAE, plus a null model that predicts the training-fold mean. The folds
     partition the data, so each training fold's y is the other folds' y_true.
  3. Paired t over the 5 folds (df=4, two-sided): v3.5 against v3, every harness method
     and the null model; v3 against the same references.

Regression splits are KFold(5, shuffle=True, random_state=42) regardless of --seed, so
there is one seed. Scoring is float64 from the stored float32 arrays.

Output: version_retest_<ds>.csv (long format, same columns as analyze_version_retest.py).

Usage:
    python scripts/eval/insurance_benchmark_v1/analyze_regression_retest.py bemtl97_amount
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_frontier_benchmark as fb  # noqa: E402

N_FOLDS = 5
SEED = 42


def load_store(ds_name: str, version: str) -> dict[str, np.ndarray]:
    with np.load(fb.PREDICTIONS_DIR / f"{ds_name}__seed{SEED}__{version}.npz") as d:
        return {k: d[k] for k in d.files}


def fold_frame(store: dict, preds: list[np.ndarray], metric) -> pd.DataFrame:
    rows = []
    for k in range(N_FOLDS):
        y = store[f"y_true__fold{k}"].astype(np.float64)
        p = preds[k].astype(np.float64)
        rows.append({"primary": metric(y, p), "mae": float(np.mean(np.abs(y - p)))})
    return pd.DataFrame(rows)


def paired_rows(x: pd.DataFrame, ref: pd.DataFrame, **tags) -> list[dict]:
    """One row per metric for delta = x - ref (both metrics: lower is better)."""
    out = []
    for mt in ("primary", "mae"):
        d = x[mt].to_numpy() - ref[mt].to_numpy()
        out.append({**tags, "metric": mt, "a_mean": x[mt].mean(), "b_mean": ref[mt].mean(),
                    "delta": d.mean(), "p_paired": stats.ttest_rel(x[mt], ref[mt]).pvalue,
                    "a_better_folds": int((d < 0).sum()), "n_folds": len(d)})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("dataset")
    args = ap.parse_args()
    ds = next(d for d in fb.REG_DATASETS if d["name"] == args.dataset)
    metric = fb.metric_fn(ds)
    metric_name = ds.get("metric", "rmse")

    v3s, v35s = load_store(ds["name"], "v3_default"), load_store(ds["name"], "v3.5_default")
    methods = sorted({k.split("__")[0] for k in v3s} - {"y_true", "test_idx"})

    # ---- 1. integrity ----
    for k in range(N_FOLDS):
        for key in (f"test_idx__fold{k}", f"y_true__fold{k}"):
            assert np.array_equal(v3s[key], v35s[key]), f"{key} differs between the two runs"
    worst = max(np.abs(v3s[f"{m}__fold{k}"].astype(np.float64) - v35s[f"{m}__fold{k}"]).max()
                for m in methods if m != "tabpfn" for k in range(N_FOLDS))
    print(f"=== {ds['name']}: integrity\n  test folds + y_true identical: yes; "
          f"max |baseline prediction diff| across runs = {worst:.3g} ({len(methods) - 1} methods)")

    # ---- 2. per-method fold scores, plus the null model ----
    ys = [v3s[f"y_true__fold{k}"].astype(np.float64) for k in range(N_FOLDS)]
    null_preds = [np.full(len(ys[k]), np.concatenate([ys[j] for j in range(N_FOLDS) if j != k]).mean())
                  for k in range(N_FOLDS)]
    frames = {m: fold_frame(v3s, [v3s[f"{m}__fold{k}"] for k in range(N_FOLDS)], metric)
              for m in methods if m != "tabpfn"}
    frames["null (train mean)"] = fold_frame(v3s, null_preds, metric)
    v3 = fold_frame(v3s, [v3s[f"tabpfn__fold{k}"] for k in range(N_FOLDS)], metric)
    v35 = fold_frame(v35s, [v35s[f"tabpfn__fold{k}"] for k in range(N_FOLDS)], metric)
    se = lambda s: s.std(ddof=1) / np.sqrt(len(s))  # noqa: E731
    print(f"\n=== {ds['name']}: fold means ({metric_name} on the stored scale; MAE) — lower is better")
    table = {"tabpfn v3.5": v35, "tabpfn v3": v3, **frames}
    for name, f in sorted(table.items(), key=lambda kv: kv[1]["primary"].mean()):
        print(f"  {name:18} {metric_name} {f['primary'].mean():.5f} ± {se(f['primary']):.5f}   "
              f"MAE {f['mae'].mean():.5f}")

    # ---- 3. paired tests ----
    rows: list[dict] = []
    for label, x, refs in (("v3.5", v35, {"v3": v3, **frames}), ("v3", v3, frames)):
        print(f"\n=== {ds['name']}: {label} − reference, paired t df=4 (folds where {label} is better)")
        for name, ref in refs.items():
            rs = paired_rows(x, ref, seed=SEED, a=label, b=name)
            rows.extend(rs)
            print(f"  {name:18}" + "".join(
                f"   {r['metric']} {r['delta']:+.5f} p={r['p_paired']:.4f} {r['a_better_folds']}/5" for r in rs))

    out = HERE / f"version_retest_{ds['name']}.csv"
    pd.DataFrame(rows).replace({"metric": {"primary": metric_name}}).to_csv(
        out, index=False, float_format="%.6g")
    print(f"\nwrote {out.relative_to(fb.REPO)}")


if __name__ == "__main__":
    main()
