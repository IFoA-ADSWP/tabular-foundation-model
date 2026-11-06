#!/usr/bin/env python3
"""D5 -- why the linear model beats TabPFN on `eudirectlapse`, as one record.

Usage:
    python scripts/diagnostics/d5_eudirectlapse.py --run-id 20261106T0900Z
    python scripts/diagnostics/d5_eudirectlapse.py --run-id ... --skip-regimes   # baselines + ladder

The design (§D5) consumes D1's profile, D2's feature comparison and D4's preprocessing result. D4
does not exist: #305 is open and blocked on D10's measured-estimate rule. This diagnostic therefore
says the preprocessing regime was **not tested** rather than assuming it, and tests the one rival
explanation it can test on its own -- feature coverage -- directly.

**Two rival explanations, and the experiment that separates them.**

* *feature coverage* -- TabPFN lacks something the GLM has (a column, a transform, an interaction).
  The lever would be feature engineering, and fine-tuning would be irrelevant.
* *additive structure* -- the target is close to additive in a few features on a weak signal, so a
  low-variance linear fit is the better inductive bias. Nothing is missing; the extra flexibility
  costs more than it buys.

Both families see the same folds and the same rows in three regimes; only the feature set changes.
The `engineered` regime hands TabPFN the linear model's own fitted log-odds plus a single
principal component of the collinear premium block. **If TabPFN still trails the linear model when
it has the linear model's functional form as a column, feature coverage is refuted on this dataset**
and additive structure is what remains.

**The version trap, stated where a reader will meet it.** The committed claim is v3_default through
the hosted client. The local package is 6.4.1, which enumerates `V2` and `V2_5` only -- there is no
V3 checkpoint here, so a local run cannot reproduce or adjudicate a v3 number. The regime comparison
is therefore a **within-experiment paired comparison** (same version, folds and rows; one feature set
changed), which is internally valid, and the record names the version it ran on. Nothing here quotes
a v2.5 delta beside a v3 delta as one table.

**The wrongness check.** The committed §14.10 baselines are re-derived from
`scripts/eval/lapse_benchmark_v1/results_per_split.csv` and the script exits non-zero if they do not
come back. An explanation of a gap that has misread the baseline explains the wrong gap.

**The second check this dataset invites.** D2 reads "TabPFN and GLM use different features" from a
top-10 Jaccard of 0.54 -- but the four premium columns are ~0.99 correlated, so a disagreement
between `prem_pure` and `prem_final` is not a disagreement about information. The record carries the
correlation matrix, so the reader can discount that reading.
"""

from __future__ import annotations

import argparse
import os
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "src"))

from provenance import (  # noqa: E402  (importable after the src path insert above)
    DIAGNOSTICS_ROOT,
    DiagnosticRecord,
    matched_context_evidence,
    sha256_file,
    write_diagnostic_record,
)

DIAGNOSTIC = "d5_eudirectlapse"
DATASET = "eudirectlapse"
TARGET = "lapse"
DATA_FILE = _REPO / "data" / "raw" / "eudirectlapse.csv"
LAPSE_EVIDENCE = _REPO / "scripts" / "eval" / "lapse_benchmark_v1" / "results_per_split.csv"

# §14.10, as committed in `docs/analyses/tabpfn_vs_gbdt_baselines_finetuning.md`. The reproduction
# step asserts these come back from the per-fold rows; a drift of more than half the thinnest
# recorded standard error (0.0037 for Linear) is a different baseline, not rounding.
EXPECTED_BASELINES = {
    "Linear": 0.6260,
    "GBM": 0.6138,
    "TabPFN": 0.6101,
}
REPRODUCTION_TOLERANCE = 0.0019

# The leaderboard's method names against the names §14.10 uses. Mapped rather than guessed: the
# report says "Linear", the evidence says "[Lapse] LR (default)", and a rename on either side should
# break this comparison loudly instead of silently matching nothing.
METHOD_LABELS = {
    "[Lapse] LR (default)": "Linear",
    "[Lapse] GBM (default)": "GBM",
    "[Lapse] TabPFNClient (default)": "TabPFN",
}

# The benchmark's `lr` is unscaled category codes with `max_iter=500`. Two problems follow on this
# table, and they are worth stating rather than working around. Unscaled, `lbfgs` is badly
# conditioned -- premium columns run to ~2,900 while policy ages sit near 50 -- and raising the
# iteration budget to converge it took over twenty minutes on five folds, which is not a price a
# $0 diagnostic should pay. Standardising first makes the same estimator converge in hundreds of
# iterations. Standardisation is applied to the linear model only: TabPFN does not need it, and
# giving the baseline its best behaviour is the fair side to err on.
LR_MAX_ITER = 1000
LR_C = 1.0

# D2's cap and split, kept identical so the two diagnostics describe the same working set.
SUBSAMPLE_CAP = 2000
TEST_ROWS = 500
N_FOLDS = 5
CV_SEED = 42
REGIME_SEEDS = (42, 43, 44, 45, 46)

# Throughput choices inherited from D2, whose plan carries the measurements behind them.
TABPFN_ESTIMATORS = 1
TABPFN_FIT_MODE = "fit_preprocessors"
PREDICT_BATCH = 10

# The collinear block. Named rather than discovered: the design's E1 hypothesis is about *which*
# features a family uses, and these four are the ones D2's top-tens disagree about.
PREMIUM_COLUMNS = ("prem_final", "prem_last", "prem_market", "prem_pure")
LADDER_KS = (1, 2, 3, 5, 10)
REGIMES = ("benchmark", "glm_top5", "engineered")
TOP_K = 5


# ---------------------------------------------------------------------------
# The dataset
# ---------------------------------------------------------------------------
def load_dataset(path: Path = DATA_FILE) -> pd.DataFrame:
    """The raw table, with the target intact and nothing dropped.

    No leak-drop is applied because none is owed: every column is a property of the policy or the
    offer at renewal, and the target is whether the holder lapsed. A `drop` list invented here
    would be a preprocessing regime, which is #305's question, not this one's.
    """
    frame = pd.read_csv(path)
    if TARGET not in frame.columns:
        raise SystemExit(f"{path} has no {TARGET!r} column")
    return frame


def coded(frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """The benchmark's `load_Xy` encoding: per-column category codes, missing to 0."""
    target = frame[TARGET].to_numpy(dtype=np.int64)
    features = frame.drop(columns=[TARGET])
    for column in features.select_dtypes(include=["object", "category"]).columns:
        features[column] = features[column].astype("category").cat.codes.replace(-1, np.nan)
    features = features.fillna(0.0).astype(np.float32)
    return features.to_numpy(dtype=np.float32), target, list(features.columns)


# ---------------------------------------------------------------------------
# The wrongness check
# ---------------------------------------------------------------------------
def committed_baselines(path: Path = LAPSE_EVIDENCE) -> dict[str, dict]:
    """Per-fold AUC for the three methods on `eudirectlapse`, from the committed evidence.

    The lapse leaderboard records `metric_error` = 1 - AUC per fold; the mean is taken over folds
    rather than over the error column's mean, which is the same number here but states which
    operation produced it.
    """
    frame = pd.read_csv(path)
    rows = frame[
        frame["dataset"].astype(str).str.startswith(DATASET)
        & (frame["metric"] == "roc_auc")
        & (frame["problem_type"] == "binary")
    ]
    if rows.empty:
        raise SystemExit(f"no {DATASET} ROC AUC rows in {path}")
    out: dict[str, dict] = {}
    for method, group in rows.groupby("method"):
        label = METHOD_LABELS.get(str(method), str(method))
        aucs = [float(1.0 - value) for value in group["metric_error"]]
        out[label] = {
            "mean_auc": round(float(np.mean(aucs)), 6),
            "n_folds": len(aucs),
            "per_fold": [round(value, 6) for value in aucs],
        }
    return out


def reproduction(observed: dict[str, dict], expected: dict[str, float] | None = None) -> dict:
    """Compare the re-derived baselines with §14.10, and say what would count as a failure."""
    expected = EXPECTED_BASELINES if expected is None else expected
    missing = sorted(set(expected) - set(observed))
    if missing:
        raise SystemExit(f"the committed evidence has no rows for {missing}")
    deltas = {
        label: round(observed[label]["mean_auc"] - value, 6)
        for label, value in expected.items()
    }
    worst = max(deltas.values(), key=abs) if deltas else 0.0
    return {
        "passed": bool(abs(worst) <= REPRODUCTION_TOLERANCE),
        "expected": dict(expected),
        "observed": {label: observed[label]["mean_auc"] for label in expected},
        "delta": deltas,
        "tolerance": REPRODUCTION_TOLERANCE,
        "rule": "every baseline within half the thinnest recorded SE (0.0037) of its §14.10 value",
    }


# ---------------------------------------------------------------------------
# The collinear premium block
# ---------------------------------------------------------------------------
def premium_collinearity(frame: pd.DataFrame) -> dict:
    """Pairwise Pearson correlation of the premium columns, and the strongest off-diagonal pair."""
    present = [column for column in PREMIUM_COLUMNS if column in frame.columns]
    if len(present) < 2:
        return {"columns": present, "matrix": None, "max_abs_correlation": None}
    matrix = frame[present].corr().round(6)
    values = matrix.to_numpy()
    np.fill_diagonal(values, np.nan)
    flat = np.nanmax(np.abs(values))
    index = np.unravel_index(np.nanargmax(np.abs(values)), values.shape)
    return {
        "columns": present,
        "matrix": {
            column: {row: float(matrix.loc[row, column]) for row in present}
            for column in present
        },
        "max_abs_correlation": round(float(flat), 6),
        "strongest_pair": [present[index[0]], present[index[1]]],
        "reading": (
            "a top-ten disagreement between two of these columns is not a disagreement about "
            "information; D2's Jaccard on this dataset understates the overlap"
        ),
    }


# ---------------------------------------------------------------------------
# The additivity ladder -- free, and at full data
# ---------------------------------------------------------------------------
def _logit(X: np.ndarray, y: np.ndarray):
    """A standardised logistic regression, fitted on the rows it is given.

    The `StandardScaler` is inside the pipeline so it is fitted on training rows only: a scaler
    fitted on the whole table would carry test-set moments into the baseline the comparison rests on.
    """
    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(C=LR_C, random_state=0, max_iter=LR_MAX_ITER),
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model.fit(X, y)
    return model


def _auc(model, X: np.ndarray, y: np.ndarray) -> float:
    return float(roc_auc_score(y, model.predict_proba(X)[:, 1]))


def _rank_by_signal(X: np.ndarray, y: np.ndarray, names: list[str]) -> list[str]:
    """Feature order for the ladder: marginal AUC, most informative first.

    Computed on the fold's training rows, so the ordering is fitted rather than read off the test
    rows. A feature with no marginal signal scores 0.5 and sorts last.
    """
    scores = []
    for index, name in enumerate(names):
        column = X[:, index]
        value = 0.5 if np.all(column == column[0]) else _auc_free(column, y)
        scores.append((abs(value - 0.5), name))
    return [name for _, name in sorted(scores, reverse=True)]


def _auc_free(column: np.ndarray, y: np.ndarray) -> float:
    """Single-column AUC, with direction removed -- which end is positive is the model's problem."""
    value = float(roc_auc_score(y, column))
    return value if value >= 0.5 else 1.0 - value


def additivity_ladder(
    X: np.ndarray,
    y: np.ndarray,
    names: list[str],
    *,
    n_folds: int = N_FOLDS,
    seed: int = CV_SEED,
    ks: tuple[int, ...] = LADDER_KS,
) -> dict:
    """How few additive features reproduce the linear model's ranking, at full data.

    This measures the dataset, not the model, so it does not depend on which TabPFN version exists
    locally. The top rung uses every feature, and is the rung to compare against §14.10's Linear.
    """
    folds = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=seed)
    rungs: dict[str, list[float]] = {}
    order: list[str] = []
    for train_index, test_index in folds.split(X, y):
        ranked = _rank_by_signal(X[train_index], y[train_index], names)
        if not order:
            order = ranked
        for k in (*ks, len(names)):
            chosen = [names.index(name) for name in ranked[:k]]
            model = _logit(X[np.ix_(train_index, chosen)], y[train_index])
            rungs.setdefault(str(k), []).append(_auc(model, X[np.ix_(test_index, chosen)], y[test_index]))
    return {
        "n_rows": int(X.shape[0]),
        "n_folds": n_folds,
        "seed": seed,
        "feature_order": order,
        "estimator": f"StandardScaler + LogisticRegression(C={LR_C}, max_iter={LR_MAX_ITER})",
        "auc_by_k": {
            k: {
                "mean_auc": round(float(np.mean(values)), 6),
                "se_auc": round(float(np.std(values, ddof=1) / np.sqrt(len(values))), 6),
                "n_folds": len(values),
            }
            for k, values in sorted(rungs.items(), key=lambda item: int(item[0]))
        },
        "reading": (
            "the top rung is the linear baseline rebuilt on this tooling's own folds; the rung "
            "where AUC stops rising is how much of the signal is additive in a few features"
        ),
    }


# ---------------------------------------------------------------------------
# The three regimes
# ---------------------------------------------------------------------------
def _split(frame: pd.DataFrame, seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    train, test = train_test_split(
        frame, train_size=SUBSAMPLE_CAP - TEST_ROWS, test_size=TEST_ROWS,
        stratify=frame[TARGET], random_state=seed,
    )
    return train, test


def _glm_ranking(train: pd.DataFrame) -> list[str]:
    """Features the linear model leans on most, by standardised coefficient magnitude."""
    X, y, names = coded(train)
    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(C=LR_C, random_state=0, max_iter=LR_MAX_ITER),
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model.fit(X, y)
    coefs = np.abs(model.named_steps["logisticregression"].coef_[0])
    return [names[i] for i in np.argsort(coefs)[::-1]]


def regime_frame(train: pd.DataFrame, test: pd.DataFrame, regime: str) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Apply one feature regime to the train/test halves, fitting anything it needs on train rows.

    Every transform is fitted on `train` and applied to `test`. The log-odds column in particular
    is a model output: computing it once over the whole table would hand the test rows to the
    feature that is meant to help TabPFN, and the comparison would measure leakage.
    """
    detail: dict = {"regime": regime}
    if regime == "benchmark":
        return train, test, detail

    if regime == "glm_top5":
        keep = [*_glm_ranking(train)[:TOP_K], TARGET]
        detail["features"] = [column for column in keep if column != TARGET]
        detail["dropped"] = [c for c in train.columns if c not in keep]
        return train[keep], test[keep], detail

    if regime == "engineered":
        train_out, test_out = train.copy(), test.copy()
        premium = [column for column in PREMIUM_COLUMNS if column in train.columns]

        scaler = StandardScaler().fit(train_out[premium])
        pca = PCA(n_components=1, random_state=0).fit(scaler.transform(train_out[premium]))
        train_out["premium_pc1"] = pca.transform(scaler.transform(train_out[premium]))[:, 0]
        test_out["premium_pc1"] = pca.transform(scaler.transform(test_out[premium]))[:, 0]
        train_out = train_out.drop(columns=premium)
        test_out = test_out.drop(columns=premium)

        logistic = make_pipeline(
            StandardScaler(),
            LogisticRegression(C=LR_C, random_state=0, max_iter=LR_MAX_ITER),
        )
        X_train, y_train, _ = coded(train)
        X_test, _, _ = coded(test)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            logistic.fit(X_train, y_train)
        train_out["glm_logit"] = logistic.decision_function(X_train)
        test_out["glm_logit"] = logistic.decision_function(X_test)

        detail["features"] = [column for column in train_out.columns if column != TARGET]
        detail["transforms"] = {
            "premium": f"{premium} -> premium_pc1 (standardised PCA, fitted on train)",
            "glm_logit": "standardised logistic regression decision value, fitted on train only",
        }
        return train_out, test_out, detail

    raise ValueError(f"unknown regime {regime!r}")


def _tabpfn(model_path: str | None = None):
    from tabpfn import TabPFNClassifier

    kwargs = {"n_estimators": TABPFN_ESTIMATORS, "random_state": 0, "fit_mode": TABPFN_FIT_MODE}
    if model_path:
        kwargs["model_path"] = model_path
    return TabPFNClassifier(**kwargs)


def run_regimes(frame: pd.DataFrame, *, regimes: tuple[str, ...] = REGIMES,
                seeds: tuple[int, ...] = REGIME_SEEDS, model_path: str | None = None) -> dict:
    """TabPFN and the linear model on identical rows, one feature set changed at a time."""
    results: dict[str, dict] = {}
    for regime in regimes:
        per_seed = []
        for seed in seeds:
            train, test = _split(frame, seed)
            train_r, test_r, detail = regime_frame(train, test, regime)
            X_train, y_train, names = coded(train_r)
            X_test, y_test, _ = coded(test_r)
            model = _tabpfn(model_path)
            model.fit(X_train, y_train)
            tabpfn_auc = float(roc_auc_score(y_test, model.predict_proba(X_test)[:, 1]))
            linear = _logit(X_train, y_train)
            linear_auc = _auc(linear, X_test, y_test)
            per_seed.append(
                {
                    "seed": seed,
                    "n_train": int(X_train.shape[0]),
                    "n_features": len(names),
                    "tabpfn_auc": round(tabpfn_auc, 6),
                    "linear_auc": round(linear_auc, 6),
                    "delta_linear_minus_tabpfn": round(linear_auc - tabpfn_auc, 6),
                }
            )
        deltas = np.array([row["delta_linear_minus_tabpfn"] for row in per_seed])
        results[regime] = {
            "detail": detail,
            "per_seed": per_seed,
            "mean_tabpfn_auc": round(float(np.mean([r["tabpfn_auc"] for r in per_seed])), 6),
            "mean_linear_auc": round(float(np.mean([r["linear_auc"] for r in per_seed])), 6),
            "mean_delta": round(float(deltas.mean()), 6),
            "se_delta": round(float(deltas.std(ddof=1) / np.sqrt(len(deltas))), 6),
            "seeds_linear_ahead": int((deltas > 0).sum()),
            "n_seeds": len(per_seed),
        }
    return results


# Two-sided 95% critical values for a t distribution, by degrees of freedom. A table rather than a
# scipy import: the diagnostic already avoids a heavy dependency for one number, and the cell is
# readable, which the call to `scipy.stats.t.ppf` would not be at the point of use.
T95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228}


def verdict(regimes: dict) -> dict:
    """Turn the three measured deltas into the one statement the ticket asks for.

    The rule is three-way, not two-way, because the measured result is neither of the design's two
    outcomes: handing TabPFN the linear model's fitted log-odds closed 88% of the gap and left a
    residual that covers zero. A binary "closes / does not close" would have called that a
    refutation and thrown away the finding, so the fractions and the interval are reported and the
    reading is derived from them rather than selected from two sentences.

    `gap_closed` is measured against the benchmark regime in the same run, so it compares the
    intervention with the thing it is an intervention on, not with an external number.
    """
    engineered = regimes.get("engineered")
    if engineered is None:
        return {"conclusion": "not tested", "reason": "the engineered regime was skipped"}

    deltas = np.array([row["delta_linear_minus_tabpfn"] for row in engineered["per_seed"]], dtype=float)
    n = int(deltas.size)
    mean = float(deltas.mean())
    se = float(deltas.std(ddof=1) / np.sqrt(n)) if n > 1 else float("nan")
    margin = T95.get(n - 1, 1.96) * se
    low, high = mean - margin, mean + margin

    benchmark = regimes.get("benchmark")
    benchmark_delta = float(benchmark["mean_delta"]) if benchmark else None
    closed = None if not benchmark_delta else round(1.0 - mean / benchmark_delta, 4)

    # Does the benchmark gap itself survive at this row cap? If it does not, there is nothing for
    # the engineered regime to explain, and saying "the linear form closes it" would describe a
    # gap that is not established. The five-seed version of this experiment reported +0.0205 and
    # the sixty-six-seed version reports +0.0054 with an interval covering zero -- so the check is
    # not decorative.
    benchmark_interval = None
    benchmark_established = None
    if benchmark is not None:
        bench = np.array([r["delta_linear_minus_tabpfn"] for r in benchmark["per_seed"]], dtype=float)
        bn = int(bench.size)
        bse = float(bench.std(ddof=1) / np.sqrt(bn)) if bn > 1 else float("nan")
        bmargin = T95.get(bn - 1, 1.96) * bse
        benchmark_interval = [round(float(bench.mean() - bmargin), 6), round(float(bench.mean() + bmargin), 6)]
        benchmark_established = bool(benchmark_interval[0] > 0)

    reading = {
        "benchmark_delta": benchmark_delta,
        "engineered_delta": round(mean, 6),
        "engineered_interval": [round(low, 6), round(high, 6)],
        "gap_closed_fraction": closed,
        "benchmark_interval": benchmark_interval,
        "benchmark_gap_established": benchmark_established,
        "seeds_linear_ahead": int((deltas > 0).sum()),
        "n_seeds": n,
        "rule": "a 95% t interval over seeds; the point estimate and its interval decide the sentence",
    }

    if benchmark_established is False:
        return {
            **reading,
            "conclusion": "no gap is established at this row cap",
            "feature_coverage": "not testable here",
            "reason": (
                f"the benchmark gap is {benchmark_delta:+.4f} with interval {benchmark_interval}, "
                "which covers zero; there is no established gap for the engineered regime to "
                "explain, so the explanation belongs to the full-data comparison and not to this "
                "row cap"
            ),
        }
    if high < 0:
        return {
            **reading,
            "conclusion": "tabpfn needs these features",
            "feature_coverage": "supported",
            "reason": "given the linear form, TabPFN leads beyond the seed noise",
        }
    if low > 0 and benchmark_delta and mean > 0.5 * benchmark_delta:
        return {
            **reading,
            "conclusion": "feature coverage refuted",
            "feature_coverage": "refuted",
            "reason": (
                "the engineered regime leaves more than half the benchmark gap, so the deficit is "
                "not the inputs"
            ),
        }
    if low > 0:
        return {
            **reading,
            "conclusion": "the linear form closes most of the gap, and does not reverse it",
            "feature_coverage": "partly supported",
            "reason": (
                f"the residual {mean:+.4f} still excludes zero, but it is a small fraction of the "
                "benchmark gap and TabPFN does not overtake the linear method"
            ),
        }
    if mean < 0:
        return {
            **reading,
            "conclusion": "the engineered gap reverses, but not beyond noise",
            "feature_coverage": "supported at this resolution",
            "reason": (
                f"with the linear form supplied, TabPFN is ahead by {mean:+.4f} on "
                f"{int((deltas < 0).sum())} of {n} seeds; the interval covers zero, so this is "
                "parity rather than a win -- and it is the opposite sign to the benchmark regime"
            ),
        }
    return {
        **reading,
        "conclusion": "glm is the right model for this dataset",
        "feature_coverage": "the lever is the linear form, which the linear model already is",
        "reason": (
            "the engineered regime closes the gap to within the seed noise, and the feature that "
            "closes it is the linear model's own fitted log-odds -- a feature TabPFN cannot be "
            "given without first fitting the model it is being compared against, so it is the "
            "argument for the linear method rather than against it"
        ),
    }


def tabpfn_provenance(model_path: str | None = None) -> dict:
    """What the TabPFN arm loaded, named rather than assumed.

    The label is derived from the checkpoint that was actually loaded, not from the package
    version and not from what the caller asked for. That distinction is the whole point of
    ADR 0003: a v2.5 run and a v3 run differ in the model, and `auto` records intent rather
    than observation.
    """
    try:
        import tabpfn

        version = getattr(tabpfn, "__version__", None)
    except Exception as error:  # pragma: no cover - environment dependent
        return {"package_version": None, "error": str(error)}

    resolved = model_path or "auto"
    name = Path(resolved).name if model_path else ""
    if "v3_default" in name:
        label, source = "v3_default", "pinned"
    elif model_path:
        label, source = name or None, "pinned"
    else:
        # `auto` with no path: 6.x resolves to v2.5; nothing here can observe v3.
        label, source = ("v2_5" if str(version).startswith("6.") else None), "auto"

    sha = None
    if model_path and Path(model_path).is_file():
        sha = sha256_file(Path(model_path))

    return {
        "package_version": version,
        "requested": "auto" if model_path is None else model_path,
        "checkpoint": name or None,
        "checkpoint_sha256": sha,
        "resolved_version": label,
        "version_source": source,
        "note": (
            "the label is derived from the checkpoint that loaded; with no path the package's "
            "`auto` resolves v2.5 on 6.x and nothing here can observe v3"
        ),
    }


def _regime_seeds(seed_range: str | None, explicit: str | None) -> tuple[int, ...]:
    """Split seeds for the regime comparison: a range, a list, or the default five.

    The power run is the reason this exists. Five seeds cannot resolve an effect of 0.002; a design
    that needs sixty-six should say so on the command line rather than in a comment.
    """
    if seed_range and explicit:
        raise SystemExit("give --seed-range or --regime-seeds, not both")
    if explicit:
        seeds = tuple(int(part) for part in explicit.replace(" ", "").split(",") if part)
    elif seed_range:
        try:
            low, high = (int(part) for part in seed_range.split("-", 1))
        except ValueError:
            raise SystemExit(f"--seed-range must be A-B, got {seed_range!r}") from None
        if high < low:
            raise SystemExit(f"--seed-range is empty: {seed_range!r}")
        seeds = tuple(range(low, high + 1))
    else:
        return REGIME_SEEDS
    if len(set(seeds)) != len(seeds):
        raise SystemExit("--seed-range/--regime-seeds lists a seed twice")
    return seeds


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def not_tested_block() -> dict:
    """What this diagnostic did not test, and why -- recorded, not left to the reader.

    D5's design input list names D4; D4 does not exist. A record that omitted the gap would let a
    later reader assume preprocessing was ruled out rather than never examined.
    """
    return {
        "preprocessing_regime": (
            "D4 (#305) has not run: the ticket is blocked on D10's measured-estimate rule, so "
            "no preprocessing ablation exists to cite and none is claimed here"
        ),
        "fine_tuning": "excluded by #306; D18 already answered it as equivalence at delta 0.002",
    }


def measure(frame: pd.DataFrame, *, skip_regimes: bool = False,
            regimes: tuple[str, ...] = REGIMES, model_path: str | None = None,
            seeds: tuple[int, ...] = REGIME_SEEDS) -> dict:
    X, y, names = coded(frame)
    measurements: dict = {
        "reproduction": reproduction(committed_baselines()),
        "premium_collinearity": premium_collinearity(frame),
        "ladder": additivity_ladder(X, y, names),
        "regimes": (
            run_regimes(frame, regimes=regimes, seeds=seeds, model_path=model_path)
            if not skip_regimes else None
        ),
        "tabpfn": None if skip_regimes else tabpfn_provenance(model_path),
        "not_tested": not_tested_block(),
    }
    if not skip_regimes:
        measurements["verdict"] = verdict(measurements["regimes"])
    return measurements


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="D5 -- the eudirectlapse gap, as one record.")
    parser.add_argument("--run-id", required=True, help="names the record directory")
    parser.add_argument("--root", type=Path, default=None, help="record root (default: outputs/diagnostics)")
    parser.add_argument("--skip-regimes", action="store_true", help="baselines and ladder only ($0, seconds)")
    parser.add_argument(
        "--seed-range", default=None,
        help="inclusive A-B of split seeds (e.g. 42-107). The power run needs ~66 seeds to bound "
             "the engineered residual below delta 0.002; the default five cannot.",
    )
    parser.add_argument(
        "--regime-seeds", default=None,
        help="explicit comma-separated split seeds, instead of --seed-range",
    )
    parser.add_argument(
        "--model-path", default=None,
        help="checkpoint to load (default: $TABPFN_MODEL_PATH, else the package's `auto`). "
             "Pass the v3_default .ckpt to measure on the line the baselines were measured on.",
    )
    parser.add_argument(
        "--regime", action="append", dest="regimes", default=None,
        help=f"subset of {REGIMES}; repeat for several",
    )
    args = parser.parse_args(argv)

    regimes = tuple(args.regimes) if args.regimes else REGIMES
    seeds = _regime_seeds(args.seed_range, args.regime_seeds)
    unknown = sorted(set(regimes) - set(REGIMES))
    if unknown:
        raise SystemExit(f"unknown regime(s) {unknown}; choose from {REGIMES}")

    frame = load_dataset()
    model_path = args.model_path or os.environ.get("TABPFN_MODEL_PATH") or None
    measurements = measure(frame, skip_regimes=args.skip_regimes, regimes=regimes,
                           model_path=model_path, seeds=seeds)

    provenance_tabpfn = measurements["tabpfn"] or tabpfn_provenance(model_path)
    record = DiagnosticRecord(
        diagnostic=DIAGNOSTIC,
        run_id=args.run_id,
        # ADR 0003: the label is the RESOLVED checkpoint's, not the package's and not the
        # request. A diagnostic that runs no model still records the label this environment
        # resolves to, because its output is read against model runs.
        model_version=provenance_tabpfn.get("resolved_version"),
        seed=(seeds[0] if not args.skip_regimes else CV_SEED),
        dataset_name=DATASET,
        dataset_sha256=sha256_file(DATA_FILE),
        matched_context=matched_context_evidence(),
        measurements={**measurements, "tabpfn": provenance_tabpfn},
    )
    written = write_diagnostic_record(record, root=args.root or DIAGNOSTICS_ROOT)

    reproduction_block = measurements["reproduction"]
    print(f"{DIAGNOSTIC}: {written}")
    print(f"  reproduction: {'passed' if reproduction_block['passed'] else 'FAILED'} "
          f"(worst delta {max(reproduction_block['delta'].values(), key=abs):+.6f})")
    print(f"  premium max |r|: {measurements['premium_collinearity']['max_abs_correlation']}")
    ladder = measurements["ladder"]["auc_by_k"]
    print("  ladder: " + "  ".join(f"k={k}:{v['mean_auc']:.4f}" for k, v in ladder.items()))
    if measurements["regimes"]:
        for name, block in measurements["regimes"].items():
            print(f"  {name:11} linear={block['mean_linear_auc']:.4f} tabpfn={block['mean_tabpfn_auc']:.4f} "
                  f"delta={block['mean_delta']:+.4f} ± {block['se_delta']:.4f} "
                  f"({block['seeds_linear_ahead']}/{block['n_seeds']} seeds)")
        print(f"  verdict: {measurements['verdict']['conclusion']}")

    return 0 if reproduction_block["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
