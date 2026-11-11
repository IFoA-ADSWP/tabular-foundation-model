"""The pilot's recorded metrics, defined once (#361).

These lived inside `scripts/run_pilot.py`. They moved here so the run and the rescore tool share
one definition of `ece`, `log_loss` and the rest instead of the registry naming two
implementations; `run_pilot` re-exports these names, so every call site and every test that
reached them through the runner keeps working.

`docs/analyses/METRIC_REGISTRY.md` states the version of each definition. Any edit here that could
move a value bumps the version there, and old numbers keep their old identity.
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    log_loss as _sklearn_log_loss,
    roc_auc_score,
)

def roc_auc(y_true, y_prob) -> float:
    return float(roc_auc_score(y_true, y_prob))


def pr_auc(y_true, y_prob) -> float:
    return float(average_precision_score(y_true, y_prob))


def brier(y_true, y_prob) -> float:
    return float(brier_score_loss(y_true, y_prob))


def log_loss(y_true, y_prob) -> float:
    return float(_sklearn_log_loss(y_true, np.clip(y_prob, 1e-15, 1 - 1e-15)))


def expected_calibration_error(y_true, y_prob, n_bins=10) -> float:
    """Expected calibration error, equal-width bins."""
    y_true = np.asarray(y_true, dtype=float)
    y_prob = np.asarray(y_prob, dtype=float)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    idx = np.clip(np.digitize(y_prob, edges[1:-1], right=True), 0, n_bins - 1)
    ece = 0.0
    n = len(y_true)
    for b in range(n_bins):
        m = idx == b
        if not m.any():
            continue
        ece += (m.sum() / n) * abs(y_true[m].mean() - y_prob[m].mean())
    return float(ece)


def compute_metrics(y_true, y_prob) -> dict:
    return {
        "roc_auc": roc_auc(y_true, y_prob),
        "brier": brier(y_true, y_prob),
        "pr_auc": pr_auc(y_true, y_prob),
        "log_loss": log_loss(y_true, y_prob),
        "ece": expected_calibration_error(y_true, y_prob),
    }


# ---------------------------------------------------------------------------
# Regression metrics (#538). Defined here so a rescored number and the run's own
# record cannot disagree about what "rmse" means.
# ---------------------------------------------------------------------------
def rmse(y_true, y_pred) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def mae(y_true, y_pred) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return float(np.mean(np.abs(y_true - y_pred)))


def medae(y_true, y_pred) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return float(np.median(np.abs(y_true - y_pred)))


def rmsle(y_true, y_pred) -> float:
    """RMSLE with predictions clipped below at 0; rows with a negative truth are excluded."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    keep = y_true >= 0
    return float(
        np.sqrt(np.mean((np.log1p(y_true[keep]) - np.log1p(np.clip(y_pred[keep], 0, None))) ** 2))
    )


def poisson_deviance(y_true, y_pred) -> float:
    """Deviance of counts: 2*sum[y*log(y/p) - (y-p)], with p clipped at 1e-12.

    The y = 0 row contributes 2p (the limit), which is most rows on a claim-count target.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.clip(np.asarray(y_pred, dtype=float), 1e-12, None)
    positive = y_true > 0
    terms = np.where(positive, y_true * np.log(np.where(positive, y_true, 1.0) / y_pred), 0.0)
    return float(2.0 * np.sum(terms - (y_true - y_pred)))


def gini(y_true, y_pred) -> float:
    """The normalised Gini, 2*C - 1, where C is the concordance of predictions with truth.

    Pairs tied on truth are excluded; a pair tied on prediction scores one half. A constant
    prediction scores 0. A constant truth has no comparable pairs, so the value is undefined.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    order = np.argsort(y_true, kind="mergesort")
    y_sorted = y_true[order]
    p_sorted = y_pred[order]

    coordinates = np.unique(p_sorted)
    # Fenwick tree over prediction ranks, counting rows already seen (lower truth).
    rank_of = {value: index + 1 for index, value in enumerate(coordinates)}
    tree = np.zeros(len(coordinates) + 1, dtype=np.int64)

    def add(index: int) -> None:
        while index <= len(coordinates):
            tree[index] += 1
            index += index & -index

    def prefix(index: int) -> int:
        total = 0
        while index > 0:
            total += int(tree[index])
            index -= index & -index
        return total

    concordant = 0.0
    comparable = 0
    seen = 0
    start = 0
    while start < len(y_sorted):
        end = start
        while end + 1 < len(y_sorted) and y_sorted[end + 1] == y_sorted[start]:
            end += 1
        for position in range(start, end + 1):
            rank = rank_of[p_sorted[position]]
            less = prefix(rank - 1)
            equal = prefix(rank) - less
            concordant += less + 0.5 * equal
            comparable += seen
        for position in range(start, end + 1):
            add(rank_of[p_sorted[position]])
            seen += 1
        start = end + 1

    if comparable == 0:
        return float("nan")
    return float(2.0 * (concordant / comparable) - 1.0)
