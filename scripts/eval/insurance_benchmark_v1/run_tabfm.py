"""TabFM foundation-model baseline on the canonical frontier folds (Part B).

TabFM (Google, v1.0.0, JAX, weights from HuggingFace google/tabfm-1.0.0-jax,
non-commercial license). Same StratifiedKFold(5, shuffle=True, random_state=42)
folds as the canonical protocol, so per-fold paired tests vs the stored tabpfn
rows in frontier_pr_auc_results.csv are valid.

Only the 3 smallest datasets are attempted (coil2000 9.8K, uslapseagent 29K,
bemtl16 59K) with a hard 60-min wall-clock cap per dataset. TabFM's ICL
attention is O(n^2) in context rows; if a fold with the full training set
fails/OOMs (or is impractically slow), we retry with max_num_rows=6000
(subsampled context per ensemble member — the package's documented mode) and
log it. If that also fails, the dataset is stopped and logged.

Per-fold metrics identical to the canonical protocol (log_loss, auc, brier,
pr_auc, lift10) + fit_s/infer_s. Rows appended to
frontier_tuned_baseline_results.csv as method="tabfm".

Usage: python scripts/eval/insurance_benchmark_v1/run_tabfm.py [ds ...]
(default: coil2000 uslapseagent bemtl16)
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

HERE = Path(__file__).resolve().parent
OUT_CSV = HERE / "frontier_tuned_baseline_results.csv"

from run_frontier_benchmark import (  # noqa: E402  (UNMODIFIED module)
    DATASETS,
    load_Xy,
    metric_fn,
    top_decile_lift,
)

N_FOLDS = 5
SEED = 42
DATASET_CAP_S = 60 * 60  # 60-min hard cap per dataset
N_ESTIMATORS = 8  # CPU-feasible ensemble (paper default is 32; logged in config)
ROW_CAP_FALLBACK = 6000  # max_num_rows per ensemble member on OOM/slow path
ALLOWED = {"coil2000", "uslapseagent", "bemtl16"}


def say(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def run_dataset(ds: dict, model) -> None:
    from tabfm.src.classifier_and_regressor import TabFMClassifier

    X, y = load_Xy(ds)
    metric = metric_fn(ds)
    skf = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    folds = list(skf.split(X, y))
    say(f"dataset={ds['name']} shape={X.shape} pos_rate={y.mean():.4f} (60-min cap)")

    # Memory-safe protocol on this 8 GB machine: the full-context fit (all train
    # rows in the ICL window) OOM-killed the process on coil2000 (silent hard kill,
    # not catchable), so we run max_num_rows=6000 from the start and log it. A
    # further OOM reduces the ensemble to 4 members.
    row_cap: int | None = ROW_CAP_FALLBACK
    n_est = N_ESTIMATORS
    t_start = time.time()
    for fold, (tr, te) in enumerate(folds):
        if time.time() - t_start > DATASET_CAP_S:
            say(f"  DATASET CAP (60 min) HIT on fold {fold} — stopping {ds['name']}")
            return
        Xtr_df = pd.DataFrame(X[tr])
        Xte_df = pd.DataFrame(X[te])
        ytr = y[tr]
        clf = TabFMClassifier(model=model, n_estimators=n_est, random_state=0,
                              verbose=False, use_amp=False, max_num_rows=row_cap)
        t1 = time.time()
        try:
            clf.fit(Xtr_df, ytr)
        except Exception as e:
            if n_est > 4:
                say(f"  fold {fold} fit failed ({type(e).__name__}: {str(e)[:120]}) "
                    f"-> retrying with n_estimators=4")
                n_est = 4
                clf = TabFMClassifier(model=model, n_estimators=n_est, random_state=0,
                                      verbose=False, use_amp=False, max_num_rows=row_cap)
                try:
                    clf.fit(Xtr_df, ytr)
                except Exception as e2:
                    say(f"  fold {fold} fit ALSO failed with n_estimators=4 "
                        f"({type(e2).__name__}: {str(e2)[:120]}) — stopping {ds['name']}")
                    return
            else:
                say(f"  fold {fold} fit failed with n_estimators={n_est} "
                    f"({type(e).__name__}: {str(e)[:120]}) — stopping {ds['name']}")
                return
        fit_s = time.time() - t1
        t1 = time.time()
        pp = clf.predict_proba(Xte_df)
        infer_s = time.time() - t1
        p1 = pp[:, 1]
        config = f"n_est={n_est},max_rows={row_cap or 'full'}"
        row = {
            "dataset": ds["name"], "method": "tabfm", "fold": fold,
            "log_loss": metric(y[te], pp),
            "auc": roc_auc_score(y[te], p1),
            "brier": brier_score_loss(y[te], p1),
            "pr_auc": average_precision_score(y[te], p1),
            "lift10": top_decile_lift(y[te], p1),
            "fit_s": round(fit_s, 1), "infer_s": round(infer_s, 1), "config": config,
        }
        pd.DataFrame([row]).to_csv(OUT_CSV, mode="a", header=not OUT_CSV.exists(), index=False)
        say(f"  tabfm f{fold} ll={row['log_loss']:.4f} auc={row['auc']:.4f} "
            f"pr_auc={row['pr_auc']:.4f} lift10={row['lift10']:.3f} (fit {fit_s:.0f}s, "
            f"infer {infer_s:.0f}s) [{config}]")
    say(f"{ds['name']} done in {time.time() - t_start:.0f}s")


def main() -> None:
    from tabfm.src.jax.tabfm_v1_0_0 import load

    t0 = time.time()
    wanted = {a.lower() for a in sys.argv[1:]} if len(sys.argv) > 1 else None
    say("loading TabFM v1.0.0 classification weights (HuggingFace, ~20 min restore on CPU)...")
    model = load(model_type="classification")  # bfloat16 defaults (memory-light)
    say(f"model loaded in {time.time() - t0:.0f}s")
    for ds in DATASETS:
        name = ds["name"]
        if name not in ALLOWED:
            continue
        if wanted is not None and name not in wanted:
            continue
        print(f"\n{'=' * 70}\nDATASET {name}\n{'=' * 70}", flush=True)
        try:
            run_dataset(ds, model)
        except Exception as e:
            say(f"  {name} ABORTED: {type(e).__name__}: {str(e)[:200]}")
    print(f"\nTABFM DONE in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
