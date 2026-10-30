"""Classification-reframe experiment for issue #67 (frequency -> binary/ordinal).

Hypothesis: TabPFN loses every count/frequency task in the v1 suite (Spanish
motor freq, freMTPL2freq, bemtl97_amount) but wins/ties every binary
classification task on ranking (AUC/PR-AUC). Reframing the count target as
binary claim/no-claim (or ordinal 0/1/2+) may move TabPFN onto its strongest
axis (probability ranking).

Dataset: spanish_motor_freq, declared in experiments.toml (#235) and loaded
EXACTLY through run_frontier_benchmark.load_Xy() (cat.codes encoding for
object/category columns, fillna(0), float32; leak columns dropped at prep
time).

Reframed targets:
  binary  y_bin = (N_claims_year > 0)          claim vs no-claim (11.1% pos)
  ordinal y_ord = min(N_claims_year, 2)        0 / 1 / 2+ claims
                 (88.9% / 6.3% / 4.8%)

Folds: StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED),
stratified on y_bin for the binary task and y_ord for the ordinal task.

Methods:
  binary (9):  tabpfn, cat, lgbm, xgb, lr, logisticglm, tweedieglm,
               poissonglm, rf — model configs IDENTICAL to
               run_frontier_benchmark.py (make_cat/make_lgbm/make_xgb/make_lr/
               make_logisticglm/make_tweedieglm/make_poissonglm/make_rf).
               tweedieglm/poissonglm are Poisson/Tweedie regressors used as
               probability rankers exactly as the canonical script does on
               binary targets: predicted mean treated as P(y=1), clipped to
               [1e-6, 1-1e-6].
  ordinal (6): tabpfn, cat, lgbm, xgb, lr, rf (multiclass-capable subset).
               DEVIATION (documented): poissonglm/tweedieglm are EXCLUDED from
               the ordinal task — sklearn GLM regressors are single-output
               (no multiclass probabilities) and P(>=1) via 1-exp(-mu) would
               not feed multiclass log loss/Brier; the comparison stays on
               native multiclass probability methods.

Metrics:
  binary:  log_loss, auc, brier, pr_auc, lift10 — metric_fn + fold_scores +
           top_decile_lift from run_frontier_benchmark.py UNCHANGED.
  ordinal: auc = roc_auc_score(y, probs, average='macro', multi_class='ovr'),
           log_loss = sklearn log_loss (multiclass), brier = MSE between
           one-hot y and probs, lift10 = top_decile_lift on P(>=1)
           (= sum of probs[:, 1:]). pr_auc left NaN (not in the ordinal
           protocol).

Seed stability (issue asks): binary task re-run at SEED=7 (all 9 methods).
Ordinal runs at SEED=42 only.

TabPFN: hosted API, TabPFNClassifier(model_path="v3_default",
random_state=0) — same retry loop as the canonical runner (3 attempts,
backoff 10s/60s/300s on fit) and the same single-class predict_proba
fallback. Runs LAST per task so a hosted stall never blocks the CPU rows.
API key via run_frontier_benchmark._load_api_key() (env or repo-root .env) —
no keys embedded in code.

Outputs (same dir):
  reframe_frequency_results.csv — per-fold rows:
    dataset, task [binary/ordinal], method, fold, seed, log_loss, auc,
    brier, pr_auc, lift10, fit_s, infer_s

Usage:
    python scripts/eval/insurance_benchmark_v1/run_reframe_frequency.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from run_frontier_benchmark import (  # noqa: E402 — same-dir import, UNMODIFIED helpers
    _load_api_key,
    fold_scores,
    make_cat,
    make_lgbm,
    make_lr,
    make_logisticglm,
    make_poissonglm,
    make_rf,
    make_tweedieglm,
    make_xgb,
    metric_fn,
    top_decile_lift,
)

HERE = Path(__file__).resolve().parent
OUT_CSV = HERE / "reframe_frequency_results.csv"

N_FOLDS = 5

_REPO = HERE.parent.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))
from src.experiment_spec import (  # noqa: E402
    CLASSIFICATION,
    dataset_entry,
    load_registry,
    mode_methods,
)

_REGISTRY = load_registry(HERE / "experiments.toml")
# The canonical 9, as every classification experiment declares them (#235).
BINARY_METHODS = [method.name for method in mode_methods(_REGISTRY, CLASSIFICATION)]


# The ordinal task is a multiclass subset; it is a study selection, not an experiment.
ORDINAL_METHODS = ["cat", "lgbm", "xgb", "lr", "rf", "tabpfn"]
CPU_MAKERS = {
    "cat": make_cat, "lgbm": make_lgbm, "xgb": make_xgb,
    "lr": make_lr, "logisticglm": make_logisticglm,
    "tweedieglm": make_tweedieglm, "poissonglm": make_poissonglm, "rf": make_rf,
}


def say(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def ordinal_scores(y_true: np.ndarray, probs: np.ndarray) -> dict:
    """Ordinal-task per-fold metrics: ovr-macro AUC, multiclass log loss,
    Brier = MSE(one-hot, probs), top-decile lift on P(>=1). pr_auc = NaN
    (not in the ordinal protocol)."""
    from sklearn.metrics import log_loss, roc_auc_score

    k = int(y_true.max()) + 1
    oh = np.eye(k)[y_true]
    p_ge1 = probs[:, 1:].sum(axis=1)
    return {
        "log_loss": float(log_loss(y_true, probs)),
        "auc": float(roc_auc_score(y_true, probs, average="macro", multi_class="ovr")),
        "brier": float(np.mean((oh - probs) ** 2)),
        "pr_auc": float("nan"),
        "lift10": top_decile_lift(y_true, p_ge1),
    }


def run_task(X: np.ndarray, y_task: np.ndarray, task: str, seed: int,
             methods: list[str], rows: list[dict]) -> None:
    from sklearn.model_selection import StratifiedKFold

    say(f"task={task} seed={seed} n={len(y_task)} "
        f"classes={np.unique(y_task, return_counts=True)[1].tolist()}")

    skf = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=seed)
    folds = list(skf.split(X, y_task))

    for m in [mm for mm in methods if mm != "tabpfn"]:
        t1 = time.time()
        for fold, (tr, te) in enumerate(folds):
            Xtr, Xte, ytr, yte = X[tr], X[te], y_task[tr], y_task[te]
            model = CPU_MAKERS[m]()
            tf = time.time()
            model.fit(Xtr, ytr)
            fit_s = time.time() - tf
            ti = time.time()
            if m in ("tweedieglm", "poissonglm"):
                # canonical binary-target handling: regressor mean as P(y=1), clipped
                mu = np.clip(model.predict(Xte), 1e-6, 1 - 1e-6)
                pp = np.column_stack([1 - mu, mu])
            else:
                pp = model.predict_proba(Xte)
            infer_s = time.time() - ti
            s = fold_scores(metric_fn({}), yte, pp) if task == "binary" \
                else ordinal_scores(yte, pp)
            rows.append({"dataset": "spanish_motor_freq", "task": task, "method": m,
                         "fold": fold, "seed": seed, **s, "fit_s": fit_s, "infer_s": infer_s})
            say(f"  {m} f{fold} ll={s['log_loss']:.4f} auc={s['auc']:.4f} "
                f"(fit {fit_s:.0f}s / inf {infer_s:.0f}s, cum {time.time()-t1:.0f}s)")

    # TabPFN LAST (hosted API — a stall must never block the CPU rows).
    from tabpfn_client import TabPFNClassifier

    _load_api_key()  # env or repo-root .env — same as canonical
    t1 = time.time()
    for fold, (tr, te) in enumerate(folds):
        model = TabPFNClassifier(model_path="v3_default", random_state=0)
        tf = time.time()
        for attempt in range(1, 4):  # canonical retry loop: 10s/60s/300s
            try:
                model.fit(X[tr], y_task[tr])
                break
            except Exception as e:
                wait = [10, 60, 300][attempt - 1]
                say(f"  tabpfn f{fold} fit attempt {attempt}/3 failed: {e!r}; retrying in {wait}s")
                time.sleep(wait)
                if attempt == 3:
                    raise
        fit_s = time.time() - tf
        ti = time.time()
        pp = model.predict_proba(X[te])
        if pp.ndim == 1 or pp.shape[1] == 1:  # single-class fallback (canonical pattern)
            pp = np.column_stack([1 - pp, pp]) if pp.ndim == 1 \
                else np.column_stack([1 - pp[:, 0], pp[:, 0]])
        infer_s = time.time() - ti
        if task == "ordinal":
            assert pp.shape[1] == 3, f"ordinal tabpfn proba shape {pp.shape}"
        s = fold_scores(metric_fn({}), y_task[te], pp) if task == "binary" \
            else ordinal_scores(y_task[te], pp)
        rows.append({"dataset": "spanish_motor_freq", "task": task, "method": "tabpfn",
                     "fold": fold, "seed": seed, **s, "fit_s": fit_s, "infer_s": infer_s})
        say(f"  tabpfn f{fold} ll={s['log_loss']:.4f} auc={s['auc']:.4f} "
            f"(fit {fit_s:.0f}s / inf {infer_s:.0f}s, cum {time.time()-t1:.0f}s)")


def main() -> None:
    t0 = time.time()
    ds = dataset_entry(_REGISTRY.datasets["spanish_motor_freq"])
    X, y_raw = load_xy(ds)
    say(f"loaded {ds['name']} X={X.shape} pos_rate={(y_raw > 0).mean():.4f}")

    rows: list[dict] = []

    # Binary task, seeds 42 + 7 (seed-7 = rank-stability re-run, all 9 methods).
    y_bin = (y_raw > 0).astype(np.int64)
    for seed in (42, 7):
        print(f"\n{'=' * 70}\nBINARY TASK seed={seed}\n{'=' * 70}", flush=True)
        run_task(X, y_bin, "binary", seed, BINARY_METHODS, rows)

    # Ordinal task, seed 42 only.
    y_ord = np.minimum(y_raw, 2).astype(np.int64)
    print(f"\n{'=' * 70}\nORDINAL TASK seed=42\n{'=' * 70}", flush=True)
    run_task(X, y_ord, "ordinal", 42, ORDINAL_METHODS, rows)

    out = pd.DataFrame(rows)
    assert len(out) == 5 * (9 * 2 + 6), f"expected 120 fold rows, got {len(out)}"
    # NaN allowed only for ordinal pr_auc (not in the ordinal protocol).
    assert out[out.task == "binary"].notna().all().all(), "NaN in binary rows"
    assert out[out.task == "ordinal"].drop(columns=["pr_auc"]).notna().all().all(), \
        "NaN in ordinal rows (pr_auc excepted)"
    assert out[out.task == "ordinal"]["pr_auc"].isna().all(), "ordinal pr_auc should be NaN"
    out.to_csv(OUT_CSV, index=False)
    say(f"wrote {OUT_CSV} ({len(out)} rows) in {time.time() - t0:.0f}s total")


def load_xy(ds: dict) -> tuple[np.ndarray, np.ndarray]:
    """Canonical leak-fixed load via run_frontier_benchmark.load_Xy, but with a
    reframe ds dict (no 'metric' key -> metric_fn stays classification).
    regression=True keeps y float (counts as stored)."""
    from run_frontier_benchmark import load_Xy

    reframe_ds = dict(ds)  # drop the poisson_deviance metric tag: this is classification now
    reframe_ds.pop("metric", None)
    return load_Xy(reframe_ds, regression=True)


if __name__ == "__main__":
    main()
