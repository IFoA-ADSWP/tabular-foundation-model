"""Insurance frontier benchmark — full v1 scope (3 independent frontiers).

Generalizes the validated pilot (run_frontier_pilot_bemtl97.py) to all three
home-turf sweep datasets per docs/analyses/insurance_frontier_benchmark_spec.md
(commit 037d215, branch feat/tabarena-benchmark), D5 Option A:

  bemtl97       target=claim,    drop=["nclaims","amount"]  (leak-fixed)
  coil2000      target=CARAVAN,  drop=[]
  uslapseagent  target=surrender, drop=[]
  norauto       target=NbClaim,  drop=[]                    (no sweep rows — fresh power)
  ausprivauto0405 target=ClaimOcc, drop=[]                  (no sweep rows — fresh power)
  bemtl16       target=number_of_liability_claims, drop=[]  (no sweep rows — fresh power)

Each dataset is an INDEPENDENT frontier (separate table + plot, no cross-dataset
Pareto comparison).

  D1 (Option B): re-run LogisticGLM/LR, TweedieGLM, PoissonGLM + RandomForest on the
                 home-turf sweep's splits (StratifiedKFold(5, shuffle=True, random_state=42)),
                 log loss, 5 folds. Tweedie/Poisson regressors on the binary target:
                 predicted mean treated as P(y=1), clipped to [1e-6, 1-1e-6].
  D2 (Option A): re-fit LightGBM/XGBoost/CatBoost at recorded defaults purely to count
                 parameters: n_estimators x average leaves per tree (fold-0 train only;
                 tree structure is seed-insensitive for counting). RF leaves counted from
                 the fitted fold-0 RF. GLM/LR params = post-encoding column count + 1
                 (harness uses cat.codes -> raw column count). TabPFN = constant
                 10,000,000 (settled non-decision, spec §5 — do not research).
  D3 (Option B): Pareto frontier under the beyond-SE rule — model A is dominated iff some B
                 with strictly fewer params has mean_B + SE_B < mean_A - SE_A.
                 Models within SE of each other both stay on the frontier.

TabPFN/CAT/LGBM/XGB log-loss values are REUSED from home_turf_sweep_results.csv
(identical splits — no re-running), filtered to dataset + full size
(n_rows == len(X), n_estimators.isna()): 5 fold rows per method. Datasets with NO
sweep rows (norauto) fall back to FRESH power on the same 5 folds: cat/lgbm/xgb fit
locally at sweep defaults; TabPFN runs last via the hosted API with a retry loop
(3 attempts, backoff 10s/60s/300s) so a hosted stall never blocks the fast results.

Regression mode (--regression flag): the same frontier machinery on continuous/count
targets, 4 independent frontiers, always FRESH power (the sweep CSV is
classification-only — regression never reuses it):

  ausautoBI8999         target=AggClaim (already log-scale),  drop=[], metric=rmse
  ausprivauto0405_vehvalue target=VehValue (raw),             drop=[], metric=rmse
  bemtl97_amount        target=amount (log1p),                drop=["claim"], metric=rmse
  freMTPL2freq          target=ClaimNb,                       drop=["IDpol"], metric=poisson_deviance

bemtl97_amount drops `claim` because claim == (amount > 0) at 100% — a deterministic
leak of the target (verified). freMTPL2freq drops IDpol (unique ids) and replaces the
Exposure column with log(Exposure): Exposure is the natural Poisson offset (verified:
no Exposure=0 rows), and log-offset is the standard GLM form. RMSE/poisson deviance
are computed on the target AS STORED — no re-transform of the log-scale targets.

Metrics dispatch through metric_fn(ds): log_loss (classification, default), rmse
(sklearn mean_squared_error, sqrt) or poisson_deviance (mean_poisson_deviance) for
regression. Regression y_pred is clipped to >= 1e-12 before deviance — OLS on count
targets can predict negatives and sklearn's deviance requires non-negative y_pred.
Regression folds are 5-fold KFold(shuffle=True, random_state=42) — NOT
StratifiedKFold (continuous target) — same seed as classification.

Regression methods (all at defaults): ols (LinearRegression), poissonglm
(PoissonRegressor(alpha=0, max_iter=500)), tweedieglm (TweedieRegressor(power=1.5)),
rf (RandomForestRegressor), cat/lgbm/xgb default regressors, tabpfn
(TabPFNRegressor(random_state=0) via the hosted API — run last, same 3-attempt
backoff retry loop as the classifier path). Param counting transfers verbatim from
classification: OLS/GLMs = post-encoding n_cols + 1; GBDT/RF = n_estimators x mean
leaves (the same leaf-counting helpers, applied to the fold-0 regressor fits);
TabPFN = 10,000,000 constant.

Usage:
    source /tmp/tabarena/.venv-ta/bin/activate
    python scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py          # all datasets
    python scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py coil2000 # subset, case-insensitive
    python scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py --regression
    python scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py --regression ausautoBI8999
    python scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py --data data/raw/some.csv --target TARGET [--drop a,b]
    python scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py --pr-auc                # PR-AUC/lift10 robustness: fresh-fit ALL methods, append per-fold rows to
                                                                                                 #   frontier_pr_auc_results.csv (dataset,seed,method,fold,log_loss,auc,brier,pr_auc,lift10),
                                                                                                 #   and extend the summary CSVs with mean_pr_auc/se_pr_auc/mean_lift10/se_lift10
    python scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py --seed 7 ausprivauto0405 # split-seed stability (default 42; seed != 42 writes
                                                                                                 #   frontier_results_<ds>_seed<N>.csv/.png so the canonical seed-42 files are not clobbered)

Outputs (same dir as this script), per dataset:
    frontier_results_<dataset>.csv   method | mean <metric> | SE | n_params | on-frontier
    frontier_plot_<dataset>.png      x = log10(n_params), y = mean <metric>, +/- SE bars,
                                     frontier red / dominated grey

Self-check: per-dataset assert-based sanity checks (5 fold rows per reused method —
skipped when the sweep has no rows for that dataset — no NaNs, unique methods, >=1
frontier point, no train/test overlap). Regression adds: all targets >= 0 and a
deviance clip-guard check.
"""
from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
import sys as _sys
_sys.path.insert(0, str(REPO))  # repo root
from src.api_key import load_api_key as _load_api_key  # noqa: E402
DATA_RAW = REPO / "data" / "raw"

# D5 Option A: the home-turf sweep datasets plus norauto. Load configs identical to
# scripts/benchmarks/run_home_turf_size_sweep.py (target + drops); norauto.csv was leak-fixed
# in d170afc (ClaimAmount dropped — do not re-derive) and has no sweep rows.
DATASETS = [
    dict(name="bemtl97", file="bemtl97.csv", target="claim", drop=["nclaims", "amount"]),
    dict(name="coil2000", file="coil2000.csv", target="CARAVAN", drop=[]),
    dict(name="uslapseagent", file="uslapseagent.csv", target="surrender", drop=[]),
    dict(name="norauto", file="norauto.csv", target="NbClaim", drop=[]),
    dict(name="ausprivauto0405", file="ausprivauto0405.csv", target="ClaimOcc", drop=[]),
    dict(name="bemtl16", file="bemtl16.csv", target="number_of_liability_claims", drop=[]),
]

# Regression-mode datasets (--regression flag) — always FRESH power, no sweep reuse.
# Targets are used AS STORED (AggClaim is already log-scale, amount is log1p — no
# re-transform; RMSE/deviance computed on the stored scale). bemtl97_amount drops
# `claim`: verified claim == (amount > 0) at 100% — a deterministic leak of the target.
# freMTPL2freq drops IDpol (unique ids) and replaces Exposure with log(Exposure)
# (natural Poisson offset; verified no Exposure=0 rows) via transform="log_exposure".
# spanish_motor_freq: last policy-year per ID (53,502 rows), target N_claims_year;
# NO log_exposure transform — per-row exposure is uniform ~1 year (verified in step
# 1), and leak columns (N_claims_history/R_Claims_history/Cost_claims_year) were
# dropped at prep time (scripts/infra/prepare_insurance_datasets.py).
REG_DATASETS = [
    dict(name="ausautoBI8999", file="ausautoBI8999.csv", target="AggClaim", drop=[], metric="rmse"),
    dict(name="ausprivauto0405_vehvalue", file="ausprivauto0405.csv", target="VehValue", drop=[], metric="rmse"),
    dict(name="bemtl97_amount", file="bemtl97.csv", target="amount", drop=["claim"], metric="rmse"),
    dict(name="freMTPL2freq", file="freMTPL2freq.csv", target="ClaimNb", drop=["IDpol"], metric="poisson_deviance", transform="log_exposure"),
    dict(name="spanish_motor_freq", file="spanish_motor_freq.csv", target="N_claims_year", drop=[], metric="poisson_deviance"),
    dict(name="spanish_motor_severity", file="spanish_motor_severity.csv", target="Cost_claims_year", drop=[], metric="rmse"),
]

METRIC_LABELS = {  # plot y-axis per metric (metric_fn dispatch)
    "log_loss": "mean log loss",
    "rmse": "mean RMSE",
    "poisson_deviance": "mean poisson deviance",
}
N_FOLDS = 5
SWEEP_CSV = HERE / "home_turf_sweep_results.csv"
PR_AUC_CSV = HERE / "frontier_pr_auc_results.csv"  # per-fold PR-AUC/lift10 rows (append mode, --pr-auc only)
REUSED_METHODS = ["cat", "lgbm", "xgb", "tabpfn"]  # log loss reused as-is from the sweep
FAST_METHODS = ["lr", "logisticglm", "tweedieglm", "poissonglm", "rf"]  # D1 Option B, new compute

# CLI flags, set by main() before the dataset loop:
#   PR_AUC_MODE: --pr-auc — forces EVERY method to fresh-fit (the sweep CSV has no
#                predictions, so PR AUC / top-decile lift need real fits) and appends
#                per-fold rows to PR_AUC_CSV.
#   SEED:        --seed N — StratifiedKFold(random_state=N), default 42 (unchanged).
PR_AUC_MODE = False
SEED = 42

# TabPFN parameter count — settled non-decision (spec §5): constant per dataset, orders of
# magnitude above the GBDTs, so its precise value never changes frontier membership.
# ponytail: fixed constant, exact hosted-model figure to be confirmed from PriorLabs/TabPFN
# docs later — do not research or block on it now.
TABPFN_N_PARAMS = 10_000_000

# One-hot style: the harness encodes with cat.codes, so post-encoding column count == raw
# column count; GLM params = that + 1 intercept (spec §5 counting-rule table).


def load_Xy(ds: dict, regression: bool = False) -> tuple[np.ndarray, np.ndarray]:
    """Identical to scripts/benchmarks/run_home_turf_size_sweep.py load_Xy — same split input.
    regression=True keeps y as float64 (continuous/count targets) instead of int64
    class labels. Regression datasets may set ds["transform"]="log_exposure"
    (freMTPL2freq): the Exposure column is replaced by log(Exposure) — Exposure is the
    natural Poisson offset (verified: no Exposure=0 rows), and log-offset is the
    standard GLM form."""
    path = ds["file"] if os.path.isabs(ds["file"]) else DATA_RAW / ds["file"]
    df = pd.read_csv(path)
    df = df.dropna(subset=[ds["target"]]).reset_index(drop=True)
    y = df[ds["target"]].to_numpy(dtype=np.float64 if regression else np.int64)
    X = df.drop(columns=[ds["target"]] + ds["drop"])
    if ds.get("transform") == "log_exposure":
        X["Exposure"] = np.log(X["Exposure"].to_numpy(dtype=float))
    for col in X.select_dtypes(include=["object", "category"]).columns:
        X[col] = X[col].astype("category").cat.codes.replace(-1, np.nan)
    X = X.fillna(0.0).astype(np.float32)
    return X.to_numpy(dtype=np.float32), y


def metric_fn(ds: dict):
    """Metric dispatch (metrics.py-style, inline): returns metric(y_true, y_pred) -> float.
    Classification (default): log_loss. Regression: rmse (sqrt of sklearn
    mean_squared_error) or poisson_deviance (sklearn mean_poisson_deviance). Regression
    y_pred is clipped to >= 1e-12 before deviance — OLS on count targets can predict
    negatives, and sklearn's deviance requires non-negative y_pred."""
    from sklearn.metrics import log_loss, mean_poisson_deviance, mean_squared_error

    if ds.get("metric") == "rmse":
        def rmse(y_true, y_pred):
            return float(np.sqrt(mean_squared_error(y_true, y_pred)))
        return rmse
    if ds.get("metric") == "poisson_deviance":
        def poisson_deviance(y_true, y_pred):
            y_pred = np.clip(y_pred, 1e-12, None)  # non-negative y_pred guard (OLS on counts)
            return float(mean_poisson_deviance(y_true, y_pred))
        return poisson_deviance

    def cross_entropy(y_true, y_pred):
        return float(log_loss(y_true, y_pred))

    return cross_entropy


def top_decile_lift(y_true: np.ndarray, p1: np.ndarray) -> float:
    """Lift in the top 10% of scores: (positives in top decile / n_top) / base rate.
    Ties broken by stable argsort order (fine per spec). NaN if base rate is 0."""
    n_top = max(1, int(round(len(y_true) * 0.10)))
    top = np.argsort(-p1, kind="stable")[:n_top]
    base = float(y_true.mean())
    if base <= 0:
        return float("nan")
    return float(y_true[top].sum()) / n_top / base


def fold_scores(metric, y_true: np.ndarray, pp: np.ndarray) -> dict:
    """All per-fold classification metrics from a 2-column probability matrix."""
    from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

    p1 = pp[:, 1]
    return {
        "log_loss": metric(y_true, pp),
        "auc": roc_auc_score(y_true, p1),
        "brier": brier_score_loss(y_true, p1),
        "pr_auc": average_precision_score(y_true, p1),
        "lift10": top_decile_lift(y_true, p1),
    }


def row_for(method: str, scores: list[dict]) -> dict:
    """Summary row (mean ± SE over folds) from a list of fold_scores dicts.
    PR-AUC/lift10 columns are added only in --pr-auc mode (backward compat:
    the 9-column summary format is unchanged otherwise)."""
    a = {k: np.array([s[k] for s in scores], dtype=float)
         for k in ("log_loss", "auc", "brier", "pr_auc", "lift10")}
    n = len(a["log_loss"])
    row = {
        "method": method,
        "mean": a["log_loss"].mean(),
        "se": a["log_loss"].std(ddof=1) / np.sqrt(n),
        "mean_auc": a["auc"].mean(),
        "se_auc": a["auc"].std(ddof=1) / np.sqrt(n),
        "mean_brier": a["brier"].mean(),
        "se_brier": a["brier"].std(ddof=1) / np.sqrt(n),
        "_fold_auc": a["auc"],
        "_fold_brier": a["brier"],
    }
    if PR_AUC_MODE:
        row["mean_pr_auc"] = a["pr_auc"].mean()
        row["se_pr_auc"] = a["pr_auc"].std(ddof=1) / np.sqrt(n)
        row["mean_lift10"] = a["lift10"].mean()
        row["se_lift10"] = a["lift10"].std(ddof=1) / np.sqrt(n)
        row["_fold_pr_auc"] = a["pr_auc"]
        row["_fold_lift10"] = a["lift10"]
    return row


# ---------------------------------------------------------------------------
# D1 models — hyperparameters match the v1 harness (run_tabarena_insurance_benchmark.py)
# ---------------------------------------------------------------------------
def make_lr():
    from sklearn.linear_model import LogisticRegression
    return LogisticRegression(random_state=0, max_iter=500)


def make_logisticglm():
    from sklearn.linear_model import LogisticRegression
    # v1 harness LogisticGlmModel: penalty=None, lbfgs, max_iter=500, random_state=0
    return LogisticRegression(penalty=None, solver="lbfgs", max_iter=500, random_state=0)


def make_tweedieglm():
    from sklearn.linear_model import TweedieRegressor
    # v1 harness TweedieGlmModel: power=1.5, alpha=0.0, max_iter=500
    return TweedieRegressor(power=1.5, alpha=0.0, max_iter=500)


def make_poissonglm():
    from sklearn.linear_model import PoissonRegressor
    # v1 harness PoissonGlmModel: alpha=0.0, max_iter=500
    return PoissonRegressor(alpha=0.0, max_iter=500)


def make_rf():
    from sklearn.ensemble import RandomForestClassifier
    return RandomForestClassifier(random_state=0)


# ---------------------------------------------------------------------------
# D2 models — refit at sweep defaults purely to count parameters (fold-0 train only;
# tree structure is seed-insensitive for counting, spec §5 D2)
# ---------------------------------------------------------------------------
def make_cat():
    from catboost import CatBoostClassifier
    return CatBoostClassifier(random_state=0, verbose=0)


def make_xgb():
    from xgboost import XGBClassifier
    return XGBClassifier(random_state=0)


def make_lgbm():
    from lightgbm import LGBMClassifier
    return LGBMClassifier(random_state=0, device_type="cpu", verbose=-1)


# ---------------------------------------------------------------------------
# Regression models (--regression mode only) — 8 methods, all at defaults
# ---------------------------------------------------------------------------
def make_ols():
    from sklearn.linear_model import LinearRegression
    return LinearRegression()


def make_poissonglm_reg():
    from sklearn.linear_model import PoissonRegressor
    # design: PoissonRegressor(alpha=0, max_iter=500) — defaults otherwise
    return PoissonRegressor(alpha=0, max_iter=500)


def make_tweedieglm_reg():
    from sklearn.linear_model import TweedieRegressor
    # design: TweedieRegressor(power=1.5) — alpha/max_iter at sklearn defaults
    return TweedieRegressor(power=1.5)


def make_rf_reg():
    from sklearn.ensemble import RandomForestRegressor
    return RandomForestRegressor(random_state=0)


def make_cat_reg():
    from catboost import CatBoostRegressor
    return CatBoostRegressor(random_state=0, verbose=0)


def make_xgb_reg():
    from xgboost import XGBRegressor
    return XGBRegressor(random_state=0)


def make_lgbm_reg():
    from lightgbm import LGBMRegressor
    return LGBMRegressor(random_state=0, device_type="cpu", verbose=-1)


# ---------------------------------------------------------------------------
# Parameter counting (spec §5 rule table)
# ---------------------------------------------------------------------------
def count_lgbm_leaves(model) -> int:
    """n_estimators x mean leaves per tree, from the fitted booster."""
    trees = model.booster_.dump_model()["tree_info"]
    leaves = [t["tree_structure"] for t in trees]
    counts = []

    def walk(node):
        if "leaf_index" in node:
            return 1
        return walk(node["left_child"]) + walk(node["right_child"])

    for t in leaves:
        counts.append(walk(t))
    return int(round(len(counts) * float(np.mean(counts))))


def count_xgb_leaves(model) -> int:
    """n_estimators x mean leaves per tree via trees_to_dataframe."""
    df = model.get_booster().trees_to_dataframe()
    per_tree = df[df["Feature"] == "Leaf"].groupby("Tree").size()
    return int(round(len(per_tree) * float(per_tree.mean())))


def count_cat_leaves(model) -> int:
    """n_estimators x mean leaves per tree via get_tree_leaf_counts (per-tree leaf counts)."""
    counts = model.get_tree_leaf_counts()  # (n_trees,) — leaf count per tree
    return int(round(len(counts) * float(counts.mean())))


def count_rf_leaves(model) -> int:
    """RandomForest counted under the same GBDT leaf rule: n_estimators x mean leaves."""
    leaves = [int(t.tree_.n_leaves) for t in model.estimators_]
    return int(round(len(leaves) * float(np.mean(leaves))))


# ---------------------------------------------------------------------------
# Frontier rule (spec D3: Option B)
# ---------------------------------------------------------------------------
def pareto_frontier(rows: list[dict]) -> list[str]:
    """Dominated iff some other method is strictly more parsimonious AND better on power
    beyond SE: mean_B + SE_B < mean_A - SE_A (lower log loss is better)."""
    frontier = []
    for a in rows:
        dominated = False
        for b in rows:
            if b is a:
                continue
            if b["n_params"] < a["n_params"] and b["mean"] + b["se"] < a["mean"] - a["se"]:
                dominated = True
                break
        if not dominated:
            frontier.append(a["method"])
    return frontier


# ---------------------------------------------------------------------------
# One dataset
# ---------------------------------------------------------------------------
def run_dataset(ds: dict, out_csv: Path, out_png: Path) -> pd.DataFrame:
    from sklearn.model_selection import StratifiedKFold

    def say(msg: str) -> None:
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

    X, y = load_Xy(ds)
    n_cols = X.shape[1]
    metric = metric_fn(ds)  # metric dispatch: log_loss for classification (default)
    say(f"dataset={ds['name']} shape={X.shape} pos_rate={y.mean():.4f} seed={SEED}")

    skf = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    folds = list(skf.split(X, y))

    # Per-fold PR-AUC/lift10 rows for the append-mode CSV (--pr-auc only).
    pr_fold_rows: list[dict] = []

    def record_fold(method: str, fold: int, s: dict) -> None:
        if PR_AUC_MODE:
            pr_fold_rows.append({"dataset": ds["name"], "seed": SEED, "method": method,
                                 "fold": fold, **s})

    # ---- 1. Power: reuse sweep CSV rows for <dataset>@full, default config only ----
    # Datasets with NO sweep rows (norauto) fall back to FRESH CPU fits on the same
    # 5 folds, same pattern as the D1 fast-method loop below. TabPFN is deferred to
    # step 4a so a hosted-API stall never blocks the fast CPU results.
    # --pr-auc forces fresh power for EVERYTHING: the sweep CSV has no per-fold
    # predictions, so PR AUC / top-decile lift cannot be computed from reused rows.
    sweep = pd.read_csv(SWEEP_CSV)
    sweep_full = sweep[(sweep.dataset == ds["name"]) & (sweep.n_rows == len(X)) & (sweep.n_estimators.isna())]
    fresh = sweep_full.empty or PR_AUC_MODE
    rows: list[dict] = []

    def reuse_or_fresh(m: str) -> dict:
        r = sweep_full[sweep_full.method == m].sort_values("fold")
        if (not PR_AUC_MODE) and len(r) == N_FOLDS:
            ll = r["log_loss"].to_numpy(dtype=float)
            auc = r["roc_auc"].to_numpy(dtype=float)
            brier = r["brier"].to_numpy(dtype=float)
            return {
                "method": m,
                "mean": ll.mean(),
                "se": ll.std(ddof=1) / np.sqrt(len(ll)),
                "mean_auc": auc.mean(),
                "se_auc": auc.std(ddof=1) / np.sqrt(len(auc)),
                "mean_brier": brier.mean(),
                "se_brier": brier.std(ddof=1) / np.sqrt(len(brier)),
                "_fold_auc": auc,
                "_fold_brier": brier,
            }
        assert fresh, f"sweep missing fold rows for {m}"
        maker = {"cat": make_cat, "lgbm": make_lgbm, "xgb": make_xgb}[m]
        scores = []
        t1 = time.time()
        for fold, (tr, te) in enumerate(folds):
            model = maker()
            model.fit(X[tr], y[tr])
            pp = model.predict_proba(X[te])
            s = fold_scores(metric, y[te], pp)
            scores.append(s)
            record_fold(m, fold, s)
            say(f"  {m} f{fold} ll={s['log_loss']:.4f} ({time.time() - t1:.0f}s)")
        return row_for(m, scores)

    for m in ("cat", "lgbm", "xgb"):
        rows.append(reuse_or_fresh(m))

    # ---- 2. D1: fit GLMs/LR/RF on the same 5 folds (new compute) ----
    d1_makers = {
        "lr": make_lr,
        "logisticglm": make_logisticglm,
        "tweedieglm": make_tweedieglm,
        "poissonglm": make_poissonglm,
        "rf": make_rf,
    }
    for m in FAST_METHODS:
        maker = d1_makers[m]
        scores = []
        t1 = time.time()
        for fold, (tr, te) in enumerate(folds):
            Xtr, Xte, ytr, yte = X[tr], X[te], y[tr], y[te]
            model = maker()
            model.fit(Xtr, ytr)
            if m in ("tweedieglm", "poissonglm"):
                # regressor on a binary target: predicted mean treated as P(y=1), clipped
                mu = np.clip(model.predict(Xte), 1e-6, 1 - 1e-6)
                pp = np.column_stack([1 - mu, mu])
            else:
                pp = model.predict_proba(Xte)
            s = fold_scores(metric, yte, pp)
            scores.append(s)
            record_fold(m, fold, s)
            say(f"  {m} f{fold} ll={s['log_loss']:.4f} ({time.time() - t1:.0f}s)")
        rows.append(row_for(m, scores))

    # ---- 3. D2: refit GBDTs + RF on fold-0 train purely to count leaves ----
    # (tree structure is seed-insensitive for counting, spec §5 D2 — one fold suffices)
    tr0, _ = folds[0]
    d2_counts: dict[str, int] = {}
    for m, maker in {"cat": make_cat, "xgb": make_xgb, "lgbm": make_lgbm}.items():
        t1 = time.time()
        model = maker()
        model.fit(X[tr0], y[tr0])
        counter = {"cat": count_cat_leaves, "xgb": count_xgb_leaves, "lgbm": count_lgbm_leaves}[m]
        d2_counts[m] = counter(model)
        say(f"  count {m}: {d2_counts[m]} params ({time.time() - t1:.0f}s)")
    t1 = time.time()
    rf = make_rf()
    rf.fit(X[tr0], y[tr0])
    d2_counts["rf"] = count_rf_leaves(rf)
    say(f"  count rf: {d2_counts['rf']} params ({time.time() - t1:.0f}s)")

    # ---- 4a. TabPFN power: reuse the sweep row when present; otherwise FRESH hosted
    # run — LAST, after every CPU method above has flushed, so a hosted stall never
    # blocks the fast results from the run log ----
    r = sweep_full[sweep_full.method == "tabpfn"].sort_values("fold")
    if (not PR_AUC_MODE) and len(r) == N_FOLDS:
        ll = r["log_loss"].to_numpy(dtype=float)
        auc = r["roc_auc"].to_numpy(dtype=float)
        brier = r["brier"].to_numpy(dtype=float)
        rows.append({
            "method": "tabpfn",
            "mean": ll.mean(),
            "se": ll.std(ddof=1) / np.sqrt(len(ll)),
            "mean_auc": auc.mean(),
            "se_auc": auc.std(ddof=1) / np.sqrt(len(auc)),
            "mean_brier": brier.mean(),
            "se_brier": brier.std(ddof=1) / np.sqrt(len(brier)),
            "_fold_auc": auc,
            "_fold_brier": brier,
        })
    else:
        assert fresh, "sweep missing fold rows for tabpfn"
        from tabpfn_client import TabPFNClassifier

        _load_api_key()  # env or .env candidates, same as the sweep
        scores = []
        t1 = time.time()
        for fold, (tr, te) in enumerate(folds):
            model = TabPFNClassifier(model_path="v3_default", random_state=0)  # default n_estimators=None
            # Hosted API is flaky (RemoteProtocolError/ConnectionError/httpx timeouts
            # seen in the sweep log): up to 3 attempts, backoff 10s/60s/300s.
            for attempt in range(1, 4):
                try:
                    model.fit(X[tr], y[tr])
                    break
                except Exception as e:
                    wait = [10, 60, 300][attempt - 1]
                    say(f"  tabpfn f{fold} fit attempt {attempt}/3 failed: {e!r}; retrying in {wait}s")
                    time.sleep(wait)
                    if attempt == 3:
                        raise
            pp = model.predict_proba(X[te])
            if pp.ndim == 1 or pp.shape[1] == 1:  # single-class fallback (sweep pattern)
                pp = np.column_stack([1 - pp, pp]) if pp.ndim == 1 else np.column_stack([1 - pp[:, 0], pp[:, 0]])
            s = fold_scores(metric, y[te], pp)
            scores.append(s)
            record_fold("tabpfn", fold, s)
            say(f"  tabpfn f{fold} ll={s['log_loss']:.4f} ({time.time() - t1:.0f}s)")
        rows.append(row_for("tabpfn", scores))

    # ---- 5. n_params for every method ----
    glm_n = n_cols + 1  # post-encoding column count + 1 intercept (harness uses cat.codes)
    for r in rows:
        m = r["method"]
        if m in ("lr", "logisticglm", "tweedieglm", "poissonglm"):
            r["n_params"] = glm_n
        elif m == "tabpfn":
            r["n_params"] = TABPFN_N_PARAMS
        else:
            r["n_params"] = d2_counts[m]
    for r in rows:
        assert isinstance(r["n_params"], int) and r["n_params"] > 0

    on_frontier = set(pareto_frontier(rows))
    for r in rows:
        r["on_frontier"] = "yes" if r["method"] in on_frontier else "no"
    cols = ["method", "mean", "se", "mean_auc", "se_auc", "mean_brier", "se_brier"]
    if PR_AUC_MODE:
        cols += ["mean_pr_auc", "se_pr_auc", "mean_lift10", "se_lift10"]
    cols += ["n_params", "on_frontier", "_fold_auc", "_fold_brier"]
    if PR_AUC_MODE:
        cols += ["_fold_pr_auc", "_fold_lift10"]
    table = pd.DataFrame(rows)[cols].sort_values("mean", ignore_index=True)

    # ---- 5b. Persist per-fold PR-AUC/lift10 rows (append mode, --pr-auc only) ----
    if PR_AUC_MODE:
        pd.DataFrame(pr_fold_rows).to_csv(
            PR_AUC_CSV, mode="a", header=not PR_AUC_CSV.exists(), index=False
        )
        say(f"  appended {len(pr_fold_rows)} per-fold rows -> {PR_AUC_CSV.name}")

    # ---- 6. Plot ----
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 5))
    for _, r in table.iterrows():
        color = "#d62728" if r["on_frontier"] == "yes" else "#7f7f7f"
        ax.errorbar(np.log10(r["n_params"]), r["mean"], yerr=r["se"], fmt="o",
                    color=color, capsize=4, markersize=7)
        ax.annotate(r["method"], (np.log10(r["n_params"]), r["mean"]),
                    textcoords="offset points", xytext=(7, 5), fontsize=8)
    ax.set_xlabel("log10(n_params)")
    ax.set_ylabel("mean log loss")
    ax.set_title(f"Insurance frontier — {ds['name']} (full, 5 folds, mean ± SE)")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
    plt.close(fig)

    # ---- 7. Self-check (repo assert convention) ----
    sanity_check(sweep_full, folds, table, on_frontier)
    table = table.drop(columns=[c for c in table.columns if c.startswith("_fold")])
    table.to_csv(out_csv, index=False)
    print(table.to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    return table


def sanity_check(sweep_full: pd.DataFrame, folds: list[tuple[np.ndarray, np.ndarray]], table: pd.DataFrame, on_frontier: set) -> None:
    """Assert-based sanity checks, per repo convention (run at end of main)."""
    # (a) when the sweep HAS rows for this dataset: exactly 5 non-NaN fold rows per
    # reused method (skipped for fresh datasets like norauto, which have none).
    if not sweep_full.empty:
        n = sweep_full[sweep_full.method == "lgbm"]["fold"].nunique()
        assert n == N_FOLDS, f"expected {N_FOLDS} sweep folds, got {n}"
        assert sweep_full["log_loss"].notna().all(), "sweep reused log-loss has NaNs"
        assert sweep_full["brier"].notna().all(), "sweep reused brier has NaNs"
        assert sweep_full["roc_auc"].notna().all(), "sweep reused roc_auc has NaNs"
    # split is a valid 5-fold partition of the full index set with no train/test
    # overlap within a fold (checked for fresh and reused runs alike)
    n_total = sum(len(te) for _, te in folds)
    assert len(np.unique(np.concatenate([te for _, te in folds]))) == n_total, "test folds overlap"
    for tr, te in folds:
        assert not np.isin(te, tr).any(), "train/test overlap within fold"
    # (b) exactly one n_params per method, no NaNs in emitted table
    assert table["n_params"].notna().all() and table["mean"].notna().all() and table["se"].notna().all(), "NaN in table"
    assert table["method"].nunique() == len(table), "duplicate methods in table"
    # (c) frontier rule returns at least one on-frontier model
    assert len(on_frontier) >= 1, "frontier is empty"
    # (d) AUC/Brier addendum (spec 2026-08): classification only — regression tables
    # have no AUC columns. mean_auc in [0.5, 1], brier >= 0, per-fold AUC > 0.4
    # (legit folds dip below 0.5 — sweep min 0.4196).
    if "mean_auc" in table.columns:
        assert table["mean_auc"].between(0.5, 1.0).all(), "mean_auc outside [0.5, 1]"
        assert (table["mean_brier"] >= 0).all(), "negative mean_brier"
        assert (table["_fold_auc"].explode() > 0.4).all(), "per-fold AUC <= 0.4"
        assert (table["_fold_brier"].explode() >= 0).all(), "negative per-fold brier"
    # (e) PR-AUC/lift10 addendum (--pr-auc robustness runs): pr_auc in [0, 1],
    # lift10 >= 0, no NaNs in the emitted means.
    if "mean_pr_auc" in table.columns:
        assert table["mean_pr_auc"].between(0.0, 1.0).all(), "mean_pr_auc outside [0, 1]"
        assert (table["mean_lift10"] >= 0).all(), "negative mean_lift10"
        assert table["mean_pr_auc"].notna().all() and table["mean_lift10"].notna().all(), "NaN in pr_auc/lift10"
        assert (table["_fold_pr_auc"].explode() >= 0).all(), "negative per-fold pr_auc"
        assert (table["_fold_lift10"].explode() >= 0).all(), "negative per-fold lift10"
    print(f"SELF-CHECK OK: folds={N_FOLDS}, methods={len(table)}, on-frontier={len(on_frontier)}")


def run_dataset_regression(ds: dict, out_csv: Path, out_png: Path) -> pd.DataFrame:
    """Regression-mode frontier (--regression). No sweep reuse — the sweep CSV is
    classification-only, so every regression dataset is FRESH power: all CPU methods
    first (same 5 folds), TabPFN last via the hosted API (same retry/backoff loop as
    the classifier path) so a hosted stall never blocks the fast results."""
    from sklearn.model_selection import KFold

    def say(msg: str) -> None:
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

    X, y = load_Xy(ds, regression=True)
    n_cols = X.shape[1]
    metric = metric_fn(ds)  # rmse or poisson_deviance, clipped as needed
    say(f"dataset={ds['name']} shape={X.shape} metric={ds['metric']} y=[{y.min():.4g}, {y.max():.4g}]")

    # KFold (NOT StratifiedKFold — continuous/count target), same seed as classification
    kf = KFold(n_splits=N_FOLDS, shuffle=True, random_state=42)
    folds = list(kf.split(X))

    # ---- 1. Fresh power: 7 CPU regressors on the same 5 folds, all at defaults ----
    makers = {
        "ols": make_ols,
        "poissonglm": make_poissonglm_reg,
        "tweedieglm": make_tweedieglm_reg,
        "rf": make_rf_reg,
        "cat": make_cat_reg,
        "lgbm": make_lgbm_reg,
        "xgb": make_xgb_reg,
    }
    rows: list[dict] = []
    fold0_models: dict[str, object] = {}  # fold-0 fits reused for leaf counting (D2 rule)
    for m in ("ols", "poissonglm", "tweedieglm", "rf", "cat", "lgbm", "xgb"):
        fold_vals = []
        t1 = time.time()
        for fold, (tr, te) in enumerate(folds):
            model = makers[m]()
            model.fit(X[tr], y[tr])
            if fold == 0:
                fold0_models[m] = model
            fold_vals.append(metric(y[te], model.predict(X[te])))
            say(f"  {m} f{fold} {ds['metric']}={fold_vals[-1]:.4f} ({time.time() - t1:.0f}s)")
        vals = np.array(fold_vals)
        rows.append({"method": m, "mean": vals.mean(), "se": vals.std(ddof=1) / np.sqrt(len(vals))})

    # ---- 2. TabPFN power: hosted API, LAST ----
    from tabpfn_client import TabPFNRegressor

    _load_api_key()  # env or .env candidates, same as the sweep
    fold_vals = []
    t1 = time.time()
    for fold, (tr, te) in enumerate(folds):
        model = TabPFNRegressor(model_path="v3_default", random_state=0)  # default n_estimators=None
        # Hosted API is flaky (RemoteProtocolError/ConnectionError/httpx timeouts seen
        # in the sweep log): up to 3 attempts, backoff 10s/60s/300s — same as classifier.
        for attempt in range(1, 4):
            try:
                model.fit(X[tr], y[tr])
                break
            except Exception as e:
                wait = [10, 60, 300][attempt - 1]
                say(f"  tabpfn f{fold} fit attempt {attempt}/3 failed: {e!r}; retrying in {wait}s")
                time.sleep(wait)
                if attempt == 3:
                    raise
        fold_vals.append(metric(y[te], model.predict(X[te])))
        say(f"  tabpfn f{fold} {ds['metric']}={fold_vals[-1]:.4f} ({time.time() - t1:.0f}s)")
    vals = np.array(fold_vals)
    rows.append({"method": "tabpfn", "mean": vals.mean(), "se": vals.std(ddof=1) / np.sqrt(len(vals))})

    # ---- 3. n_params: OLS/GLMs = post-encoding n_cols + 1; GBDT/RF = n_estimators x
    # mean leaves (same helpers as classification, applied to the fold-0 regressor
    # fits — they work on regressor objects); TabPFN = constant ----
    glm_n = n_cols + 1
    counters = {"rf": count_rf_leaves, "cat": count_cat_leaves, "lgbm": count_lgbm_leaves, "xgb": count_xgb_leaves}
    for r in rows:
        m = r["method"]
        if m in ("ols", "poissonglm", "tweedieglm"):
            r["n_params"] = glm_n
        elif m == "tabpfn":
            r["n_params"] = TABPFN_N_PARAMS
        else:
            r["n_params"] = counters[m](fold0_models[m])
    for r in rows:
        assert isinstance(r["n_params"], int) and r["n_params"] > 0

    on_frontier = set(pareto_frontier(rows))
    for r in rows:
        r["on_frontier"] = "yes" if r["method"] in on_frontier else "no"
    table = pd.DataFrame(rows)[["method", "mean", "se", "n_params", "on_frontier"]].sort_values(
        "mean", ignore_index=True
    )
    table.to_csv(out_csv, index=False)
    print(table.to_string(index=False, float_format=lambda v: f"{v:.4f}"))

    # ---- 4. Plot (same style as classification; y label follows the metric) ----
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ylabel = METRIC_LABELS[ds["metric"]]
    fig, ax = plt.subplots(figsize=(8, 5))
    for _, r in table.iterrows():
        color = "#d62728" if r["on_frontier"] == "yes" else "#7f7f7f"
        ax.errorbar(np.log10(r["n_params"]), r["mean"], yerr=r["se"], fmt="o",
                    color=color, capsize=4, markersize=7)
        ax.annotate(r["method"], (np.log10(r["n_params"]), r["mean"]),
                    textcoords="offset points", xytext=(7, 5), fontsize=8)
    ax.set_xlabel("log10(n_params)")
    ax.set_ylabel(ylabel)
    ax.set_title(f"Insurance frontier — {ds['name']} (full, 5 folds, mean ± SE)")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
    plt.close(fig)

    # ---- 5. Self-check ----
    sanity_check_regression(ds, folds, table, on_frontier, y, metric)
    return table


def sanity_check_regression(ds: dict, folds: list[tuple[np.ndarray, np.ndarray]], table: pd.DataFrame, on_frontier: set, y: np.ndarray, metric) -> None:
    """Regression-mode self-checks: the shared fold/table/frontier checks (sweep checks
    skipped — regression never reuses the classification sweep) plus target
    non-negativity and the deviance clip guard."""
    assert y.min() >= 0, "regression targets must be non-negative"
    if ds.get("metric") == "poisson_deviance":
        # OLS can predict negatives on count targets; the metric must clip y_pred to
        # >= 1e-12 before deviance (sklearn raises on negative y_pred). Verify the
        # guard end-to-end with a negative prediction.
        assert np.isfinite(metric(np.array([0.0, 2.0, 5.0]), np.array([-3.0, 1.0, 4.5]))), "deviance clip guard broken"
    sanity_check(pd.DataFrame(), folds, table, on_frontier)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def make_parser() -> argparse.ArgumentParser:
    """CLI: legacy positional dataset filters + --regression, plus generic
    --data/--target/--drop for arbitrary CSVs (issue #46)."""
    parser = argparse.ArgumentParser(
        prog="run_frontier_benchmark.py",
        description="Pareto frontier benchmark (power vs parsimony, D1-D5) on the v1 "
                    "insurance datasets, or on any single CSV supplied via --data.",
    )
    parser.add_argument(
        "filters", nargs="*", metavar="DATASET",
        help="case-insensitive dataset-name filter(s); empty = all registered datasets "
             "(ignored when --data is given)",
    )
    parser.add_argument("--regression", action="store_true",
                        help="regression mode: continuous/count targets, KFold splits")
    parser.add_argument("--pr-auc", action="store_true",
                        help="PR-AUC/lift10 robustness: fresh-fit ALL methods, append per-fold rows "
                             "to frontier_pr_auc_results.csv (ignored with --data)")
    parser.add_argument("--seed", type=int, default=42, metavar="N",
                        help="StratifiedKFold random_state (default 42; seed != 42 writes "
                             "frontier_results_<ds>_seed<N>.csv/.png so canonical seed-42 files are not clobbered)")
    parser.add_argument("--data", metavar="CSV",
                        help="run a single arbitrary dataset CSV (absolute path, or relative to repo root)")
    parser.add_argument("--target", metavar="COL",
                        help="target column name (required when --data is given)")
    parser.add_argument("--drop", metavar="COLS",
                        help="comma-separated leak columns to drop (with --data; default: none)")
    return parser


def select_datasets(args: argparse.Namespace) -> tuple[list[dict], set[str] | None]:
    """Dataset selection: registry (filtered case-insensitively) or a single synthetic
    --data entry. Returns (datasets, wanted_filter) — filter is None for --data."""
    datasets = REG_DATASETS if args.regression else DATASETS
    if args.data is not None:
        # relative --data paths are repo-root-relative; load_Xy treats non-absolute
        # paths as data/raw/-relative (registry behavior), so resolve here
        data = args.data if os.path.isabs(args.data) else str(REPO / args.data)
        ds = dict(name=Path(args.data).stem, file=data, target=args.target,
                  metric="rmse" if args.regression else "log_loss",
                  drop=[c.strip() for c in args.drop.split(",")] if args.drop else [])
        return [ds], None  # --data wins; filters ignored
    wanted = {f.lower() for f in args.filters} if args.filters else None
    return datasets, wanted


def main() -> None:
    global SEED, PR_AUC_MODE
    t0 = time.time()
    parser = make_parser()
    args = parser.parse_args()
    if args.data is not None and args.target is None:
        parser.error("--target is required when --data is given")
    SEED = args.seed
    PR_AUC_MODE = args.pr_auc and args.data is None  # --pr-auc is a registry-run mode
    datasets, wanted = select_datasets(args)
    runner = run_dataset_regression if args.regression else run_dataset
    for ds in datasets:
        name = ds["name"]
        if wanted is not None and name.lower() not in wanted:
            continue
        # Seed != 42 gets suffixed outputs so split-seed runs never clobber the
        # canonical seed-42 frontier_results_*.csv / plots.
        suffix = f"_seed{SEED}" if SEED != 42 else ""
        out_csv = HERE / f"frontier_results_{name}{suffix}.csv"
        out_png = HERE / f"frontier_plot_{name}{suffix}.png"
        print(f"\n{'=' * 70}\nDATASET {name}\n{'=' * 70}", flush=True)
        runner(ds, out_csv, out_png)
        print(f"[{time.strftime('%H:%M:%S')}] {name} done -> {out_csv}, {out_png}", flush=True)
    print(f"\nALL DATASETS DONE in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
