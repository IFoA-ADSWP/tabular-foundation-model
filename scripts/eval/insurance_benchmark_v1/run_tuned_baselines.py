"""Tuned / feature-engineered classical baselines on the canonical frontier folds.

"Finality" test: does a properly-tuned classical baseline beat zero-tune hosted
TabPFN on the canonical protocol? Uses the EXACT same folds as the §14.12
robustness run (StratifiedKFold(5, shuffle=True, random_state=42)) so per-fold
paired tests against the stored tabpfn rows in frontier_pr_auc_results.csv are
valid.

Folds, data loading and metric helpers are imported from run_frontier_benchmark.py
(UNMODIFIED). New methods per dataset per fold (all fit on the same 5 splits):

  lr         plain LogisticRegression(C=1, random_state=0, max_iter=500) — FOLD
             IDENTITY check: per-fold log_loss must match the stored `lr` rows.
  lr_tuned   StandardScaler + LogisticRegression, C in {0.01, 0.1, 1, 10} by
             3-fold inner CV AUC on the training fold, refit on full fold.
  glm_eng    PolynomialFeatures(2, interaction_only) + StandardScaler + LR, same
             C grid / inner CV. Interactions capped: if > 100k features, keep raw
             + interactions of top-30 features by |corr| with the target.
  lgbm_tuned lr in {0.05, 0.1} x num_leaves in {31, 127}, early stopping
             (max 1000 rounds, patience 10) on a 10% stratified slice of the
             training fold, refit on the full fold with the best config.
  cat_tuned  lr in {0.05, 0.1} x depth in {6, 10}, same early-stopping protocol.
             If a dataset's cat tuning exceeds 10 min/fold, fall back to the
             single config (lr=0.1, depth=6) for the remaining folds.
  rf_tuned   n_estimators=300, max_features in {sqrt, 0.5} x min_samples_leaf in
             {1, 10}.

All tuning selects by ROC AUC (the metric under contest) — documented choice.
Per-fold time caps (10 min) are soft: remaining grid entries are skipped and the
best config seen so far is used; every cap hit is logged.

Per-fold scores: log_loss, auc, brier, pr_auc, lift10 (lift10 identical to
run_frontier_benchmark.top_decile_lift) + fit_s/infer_s + chosen config.

Output: frontier_tuned_baseline_results.csv (append mode).
Usage:  python scripts/eval/insurance_benchmark_v1/run_tuned_baselines.py [ds ...]
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.preprocessing import StandardScaler, PolynomialFeatures
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier

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
FOLD_CAP_S = 600  # soft per-fold tuning cap (10 min)
GBDT_GRID = [(0.05, 31), (0.05, 127), (0.1, 31), (0.1, 127)]  # (lr, num_leaves) for lgbm
CAT_GRID = [(0.05, 6), (0.05, 10), (0.1, 6), (0.1, 10)]  # (lr, depth) for catboost (max depth 16)
C_GRID = [0.01, 0.1, 1.0, 10.0]
MAX_POLY_FEATURES = 100_000


def say(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def tune_lr_cv(Xtr: np.ndarray, ytr: np.ndarray, cap_s: float) -> tuple[float, bool]:
    """Best C by 3-fold CV AUC (StandardScaler inside the CV)."""
    best_c, best_score, capped = C_GRID[0], -np.inf, False
    t0 = time.time()
    for c in C_GRID:
        if time.time() - t0 > cap_s:
            capped = True
            break
        pipe = make_pipeline(StandardScaler(),
                             LogisticRegression(C=c, random_state=0, max_iter=500))
        s = cross_val_score(pipe, Xtr, ytr, cv=3, scoring="roc_auc", n_jobs=-1).mean()
        if s > best_score:
            best_c, best_score = c, s
    return best_c, capped


def poly_features(Xtr: np.ndarray, Xte: np.ndarray, ytr: np.ndarray):
    """Interaction features with the feature-count cap: if > MAX_POLY_FEATURES,
    keep raw + interactions of top-30 features by |corr| with the target."""
    poly = PolynomialFeatures(degree=2, interaction_only=True, include_bias=False)
    if poly.fit_transform(Xtr).shape[1] <= MAX_POLY_FEATURES:
        Xtr_p = poly.fit_transform(Xtr)
        Xte_p = poly.transform(Xte)
        return Xtr_p, Xte_p, f"poly2_full({Xtr_p.shape[1]})"
    # cap branch (no canonical dataset hits this — 85 features -> 3.6K interactions)
    corr = np.abs(np.array([np.corrcoef(Xtr[:, j], ytr)[0, 1] for j in range(Xtr.shape[1])]))
    top = np.argsort(-corr)[:30]
    keep = np.concatenate([np.arange(Xtr.shape[1]), top])
    keep = np.unique(keep)
    Xtr_sel, Xte_sel = Xtr[:, keep], Xte[:, keep]
    Xtr_p = poly.fit_transform(Xtr_sel)
    Xte_p = poly.transform(Xte_sel)
    return Xtr_p, Xte_p, f"poly2_top30({Xtr_p.shape[1]})"


def tune_lgbm(Xtr, ytr, Xva, yva, cap_s: float):
    """Best (lr, num_leaves) by early-stopped AUC on the 10% slice."""
    from lightgbm import LGBMClassifier, early_stopping

    best, best_score, capped = None, -np.inf, False
    t0 = time.time()
    for lr_, nl in GBDT_GRID:
        if time.time() - t0 > cap_s:
            capped = True
            break
        m = LGBMClassifier(n_estimators=1000, learning_rate=lr_, num_leaves=nl,
                           random_state=0, device_type="cpu", verbose=-1)
        m.fit(Xtr, ytr, eval_set=[(Xva, yva)], eval_metric="auc",
              callbacks=[early_stopping(10, verbose=False)])
        s = m.best_score_["valid_0"]["auc"]
        if s > best_score:
            best = (lr_, nl, m.best_iteration_)
    return best, capped


def tune_cat(Xtr, ytr, Xva, yva, cap_s: float):
    """Best (lr, depth) by early-stopped AUC on the 10% slice."""
    from catboost import CatBoostClassifier

    best, best_score, capped = None, -np.inf, False
    t0 = time.time()
    for lr_, depth in CAT_GRID:
        if time.time() - t0 > cap_s:
            capped = True
            break
        m = CatBoostClassifier(iterations=1000, learning_rate=lr_, depth=depth,
                               random_state=0, verbose=0, eval_metric="AUC",
                               early_stopping_rounds=10)
        m.fit(Xtr, ytr, eval_set=(Xva, yva))
        s = m.get_best_score()["validation"]["AUC"]
        if s > best_score:
            best = (lr_, depth, m.get_best_iteration() or 1000)
    return best, capped


def run_dataset(ds: dict, out_rows: list[dict]) -> None:
    from sklearn.metrics import (average_precision_score, brier_score_loss,
                                 roc_auc_score)

    X, y = load_Xy(ds)
    metric = metric_fn(ds)
    skf = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    folds = list(skf.split(X, y))
    say(f"dataset={ds['name']} shape={X.shape} pos_rate={y.mean():.4f}")

    cat_capped = False  # dataset-level fallback after a 10-min/fold cap hit

    for fold, (tr, te) in enumerate(folds):
        Xtr, Xte, ytr, yte = X[tr], X[te], y[tr], y[te]
        Xva, yva = train_test_split(Xtr, ytr, test_size=0.10, stratify=ytr, random_state=0)[::2]

        def record(method: str, pp: np.ndarray, fit_s: float, infer_s: float, config: str) -> None:
            p1 = pp[:, 1]
            out_rows.append({
                "dataset": ds["name"], "method": method, "fold": fold,
                "log_loss": metric(yte, pp),
                "auc": roc_auc_score(yte, p1),
                "brier": brier_score_loss(yte, p1),
                "pr_auc": average_precision_score(yte, p1),
                "lift10": top_decile_lift(yte, p1),
                "fit_s": round(fit_s, 1), "infer_s": round(infer_s, 1), "config": config,
            })

        # -- lr (fold-identity reference, untuned) --
        t1 = time.time()
        m = LogisticRegression(C=1.0, random_state=0, max_iter=500)
        m.fit(Xtr, ytr)
        fit_s = time.time() - t1
        t1 = time.time()
        pp = m.predict_proba(Xte)
        record("lr", pp, fit_s, time.time() - t1, "C=1")

        # -- lr_tuned --
        t1 = time.time()
        c, capped = tune_lr_cv(Xtr, ytr, FOLD_CAP_S)
        pipe = make_pipeline(StandardScaler(),
                             LogisticRegression(C=c, random_state=0, max_iter=500))
        pipe.fit(Xtr, ytr)
        fit_s = time.time() - t1
        t1 = time.time()
        pp = pipe.predict_proba(Xte)
        record("lr_tuned", pp, fit_s, time.time() - t1, f"C={c}" + (" [cap-hit]" if capped else ""))

        # -- glm_eng --
        t1 = time.time()
        Xtr_p, Xte_p, poly_note = poly_features(Xtr, Xte, ytr)
        c2, capped2 = tune_lr_cv(Xtr_p, ytr, FOLD_CAP_S)
        pipe2 = make_pipeline(StandardScaler(),
                              LogisticRegression(C=c2, random_state=0, max_iter=500))
        pipe2.fit(Xtr_p, ytr)
        fit_s = time.time() - t1
        t1 = time.time()
        pp = pipe2.predict_proba(Xte_p)
        record("glm_eng", pp, fit_s, time.time() - t1,
               f"poly={poly_note},C={c2}" + (" [cap-hit]" if capped2 else ""))

        # -- lgbm_tuned --
        t1 = time.time()
        best, capped3 = tune_lgbm(Xtr, ytr, Xva, yva, FOLD_CAP_S)
        if best is None:
            best = (0.1, 127, 100)
        from lightgbm import LGBMClassifier
        m = LGBMClassifier(n_estimators=best[2], learning_rate=best[0], num_leaves=best[1],
                           random_state=0, device_type="cpu", verbose=-1)
        m.fit(Xtr, ytr)
        fit_s = time.time() - t1
        t1 = time.time()
        pp = m.predict_proba(Xte)
        record("lgbm_tuned", pp, fit_s, time.time() - t1,
               f"lr={best[0]},leaves={best[1]},iters={best[2]}" + (" [cap-hit]" if capped3 else ""))

        # -- cat_tuned (dataset-level fallback after a cap hit) --
        t1 = time.time()
        if cat_capped:
            best4 = (0.1, 6, 1000)
            from catboost import CatBoostClassifier
            m = CatBoostClassifier(iterations=best4[2], learning_rate=best4[0], depth=best4[1],
                                   random_state=0, verbose=0)
            m.fit(Xtr, ytr)
            fit_s = time.time() - t1
            t1 = time.time()
            pp = m.predict_proba(Xte)
            record("cat_tuned", pp, fit_s, time.time() - t1, f"lr={best4[0]},depth={best4[1]},iters={best4[2]} [dataset cap]")
        else:
            best4, capped4 = tune_cat(Xtr, ytr, Xva, yva, FOLD_CAP_S)
            if best4 is None:
                best4 = (0.1, 6, 1000)
            from catboost import CatBoostClassifier
            m = CatBoostClassifier(iterations=best4[2], learning_rate=best4[0], depth=best4[1],
                                   random_state=0, verbose=0)
            m.fit(Xtr, ytr)
            fit_s = time.time() - t1
            t1 = time.time()
            pp = m.predict_proba(Xte)
            record("cat_tuned", pp, fit_s, time.time() - t1,
                   f"lr={best4[0]},depth={best4[1]},iters={best4[2]}" + (" [cap-hit]" if capped4 else ""))
            if capped4 or fit_s > FOLD_CAP_S:
                cat_capped = True
                say(f"  cat cap hit on {ds['name']} fold {fold} -> single-config fallback for remaining folds")

        # -- rf_tuned --
        t1 = time.time()
        best5, capped5 = None, False
        for mf, msl in [( "sqrt", 1), ("sqrt", 10), (0.5, 1), (0.5, 10)]:
            if time.time() - t1 > FOLD_CAP_S:
                capped5 = True
                break
            m = RandomForestClassifier(n_estimators=300, max_features=mf, min_samples_leaf=msl,
                                       random_state=0, n_jobs=-1)
            m.fit(Xtr, ytr)
            pp_tmp = m.predict_proba(Xva)
            s = roc_auc_score(yva, pp_tmp[:, 1])
            if best5 is None or s > best5[0]:
                best5 = (s, mf, msl)
        if best5 is None:
            best5 = (0.0, "sqrt", 1)
        m = RandomForestClassifier(n_estimators=300, max_features=best5[1], min_samples_leaf=best5[2],
                                   random_state=0, n_jobs=-1)
        m.fit(Xtr, ytr)
        fit_s = time.time() - t1
        t1 = time.time()
        pp = m.predict_proba(Xte)
        record("rf_tuned", pp, fit_s, time.time() - t1,
               f"mf={best5[1]},msl={best5[2]}" + (" [cap-hit]" if capped5 else ""))

        say(f"  fold {fold} done: lr_tuned C={c}{'+' if not capped else ' cap'} | glm_eng C={c2}{'+' if not capped2 else ' cap'} | "
            f"lgbm lr={best[0]},l={best[1]} | cat lr={best4[0]},d={best4[1]} | rf mf={best5[1]},msl={best5[2]}")

    say(f"{ds['name']} done ({len(folds)} folds)")


def main() -> None:
    t0 = time.time()
    wanted = {a.lower() for a in sys.argv[1:]} if len(sys.argv) > 1 else None
    for ds in DATASETS:
        if wanted is not None and ds["name"].lower() not in wanted:
            continue
        print(f"\n{'=' * 70}\nDATASET {ds['name']}\n{'=' * 70}", flush=True)
        out_rows: list[dict] = []
        run_dataset(ds, out_rows)
        df = pd.DataFrame(out_rows)
        df.to_csv(OUT_CSV, mode="a", header=not OUT_CSV.exists(), index=False)
        say(f"appended {len(df)} rows -> {OUT_CSV.name}")
    print(f"\nALL DATASETS DONE in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
