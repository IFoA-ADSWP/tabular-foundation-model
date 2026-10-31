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
