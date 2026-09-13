"""Tests for the Pilot 2 analysis primitives (`src/paired_analysis.py`).

The metric used here is the Mann-Whitney form of ROC AUC, hand-verifiable on tiny samples and
checked against scikit-learn where available -- so a passing suite means the bootstrap is
resampling rows correctly, not that a library agreed with itself.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from paired_analysis import (  # noqa: E402
    holm_adjust,
    inverse_variance_summary,
    paired_bootstrap_ci,
)


def auc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """ROC AUC via the Mann-Whitney U statistic (ties get 0.5)."""
    y_true = np.asarray(y_true)
    y_score = np.asarray(y_score, dtype=float)
    pos, neg = y_score[y_true == 1], y_score[y_true == 0]
    if pos.size == 0 or neg.size == 0:
        raise ValueError("AUC undefined: one class missing")
    cmp = pos[:, None] - neg[None, :]
    return float((np.sum(cmp > 0) + 0.5 * np.sum(cmp == 0)) / (pos.size * neg.size))


# --------------------------------------------------------------------------- the metric itself

def test_auc_metric_is_correct_on_hand_checkable_cases():
    y = np.array([0, 0, 1, 1])
    assert auc(y, np.array([1.0, 2.0, 3.0, 4.0])) == pytest.approx(1.0)
    assert auc(y, np.array([4.0, 3.0, 2.0, 1.0])) == pytest.approx(0.0)
    # negatives 1.0 and 2.0, positives 1.5 and 3.0 -> 3 of the 4 pairs concordant
    assert auc(y, np.array([1.0, 2.0, 1.5, 3.0])) == pytest.approx(0.75)


def test_auc_metric_agrees_with_sklearn():
    sklearn_metrics = pytest.importorskip("sklearn.metrics")
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, size=200)
    s = rng.normal(size=200) + y * 0.7
    assert auc(y, s) == pytest.approx(sklearn_metrics.roc_auc_score(y, s))


# --------------------------------------------------------------------------- paired bootstrap

def test_paired_bootstrap_null_gives_zero_estimate_and_interval_containing_zero():
    rng = np.random.default_rng(1)
    y = rng.integers(0, 2, size=400)
    s = rng.normal(size=400) + y * 0.5
    out = paired_bootstrap_ci(y, s, s.copy(), auc, n_resamples=400, seed=7)
    assert out["estimate"] == pytest.approx(0.0, abs=1e-12)
    assert out["ci_low"] <= 0.0 <= out["ci_high"]
    assert out["excludes_zero"] is False


def test_paired_bootstrap_detects_a_real_difference_and_gets_the_direction_right():
    rng = np.random.default_rng(2)
    y = rng.integers(0, 2, size=600)
    noise = rng.normal(size=600)
    weak = noise + y * 0.2
    strong = noise + y * 1.5
    out = paired_bootstrap_ci(y, weak, strong, auc, n_resamples=400, seed=7)
    assert out["estimate"] > 0
    assert out["excludes_zero"] is True
    assert out["ci_low"] > 0.0
    assert out["metric"]["b"] > out["metric"]["a"]


def test_paired_bootstrap_is_paired_not_two_independent_samples():
    """A paired interval must be TIGHTER than the unpaired widths for the same arms.

    Both arms are evaluated on the same 1,000 rows, so resampling rows cancels most of the
    sampling variance. If this ever fails, the module has started resampling arms separately.
    """
    rng = np.random.default_rng(3)
    y = rng.integers(0, 2, size=1_000)
    base = rng.normal(size=1_000) + y * 0.8
    better = base + y * 0.3  # a small, consistent improvement
    out = paired_bootstrap_ci(y, base, better, auc, n_resamples=500, seed=7)
    unpaired_half_width = 0.06  # R1's observed unpaired half-width on 1,000 rows
    assert (out["ci_high"] - out["ci_low"]) / 2 < unpaired_half_width


def test_degenerate_resamples_are_counted_not_hidden():
    y = np.array([0, 0, 0, 1])  # one positive: many resamples will contain none
    s = np.array([0.1, 0.2, 0.3, 0.9])
    out = paired_bootstrap_ci(y, s, s + 0.01, auc, n_resamples=200, seed=5)
    assert out["n_degenerate"] > 0
    assert out["n_resamples"] == 200


def test_single_class_sample_is_rejected_rather_than_bootstrapped():
    y = np.ones(50)
    s = np.linspace(0.0, 1.0, 50)
    with pytest.raises(ValueError, match="undefined on most resamples|one class"):
        paired_bootstrap_ci(y, s, s, auc, n_resamples=50, seed=1)


def test_seed_reproduces_the_interval_exactly():
    rng = np.random.default_rng(4)
    y = rng.integers(0, 2, size=300)
    a = rng.normal(size=300) + y * 0.4
    b = a + y * 0.2
    first = paired_bootstrap_ci(y, a, b, auc, n_resamples=300, seed=99)
    second = paired_bootstrap_ci(y, a, b, auc, n_resamples=300, seed=99)
    assert (first["ci_low"], first["ci_high"]) == (second["ci_low"], second["ci_high"])


def test_length_mismatch_is_rejected():
    y = np.array([0, 1, 0, 1])
    with pytest.raises(ValueError, match="same length"):
        paired_bootstrap_ci(y, np.array([0.1, 0.2, 0.3]), np.array([0.1, 0.2, 0.3, 0.4]), auc)


# --------------------------------------------------------------------------- aggregation (D4)

def test_inverse_variance_reproduces_the_hand_computed_pooled_estimate():
    # w1 = 1e6, w2 = 400  ->  (1e6*0.01 + 400*0.05) / (1e6 + 400)  =  10020 / 1000400
    out = inverse_variance_summary([0.01, 0.05], [1e-6, 2.5e-3])
    assert out["pooled"] == pytest.approx(10020 / 1000400, rel=1e-12)
    assert out["k"] == 2


def test_inverse_variance_lets_the_precise_estimate_dominate():
    precise = inverse_variance_summary([0.01, 0.50], [1e-6, 1e-2])
    plain_mean = (0.01 + 0.50) / 2
    assert abs(precise["pooled"] - 0.01) < abs(plain_mean - 0.01)
    assert precise["pooled"] == pytest.approx(0.01, abs=2e-3)


def test_inverse_variance_reports_heterogeneity_rather_than_hiding_it():
    consistent = inverse_variance_summary([0.010, 0.011, 0.009], [1e-6, 1e-6, 1e-6])
    inconsistent = inverse_variance_summary([0.010, 0.090, -0.040], [1e-6, 1e-6, 1e-6])
    assert inconsistent["i2"] > consistent["i2"]
    assert inconsistent["q"] > consistent["q"]


def test_inverse_variance_ci_excludes_zero_for_tight_consistent_estimates():
    out = inverse_variance_summary([0.02, 0.025], [1e-6, 1e-6])
    assert out["excludes_zero"] is True
    assert out["ci_low"] > 0.0


def test_inverse_variance_single_estimate_has_no_heterogeneity():
    out = inverse_variance_summary([0.03], [1e-5])
    assert out["k"] == 1
    assert out["i2"] == 0.0
    assert out["pooled"] == pytest.approx(0.03)


def test_inverse_variance_rejects_bad_input():
    with pytest.raises(ValueError, match="same shape"):
        inverse_variance_summary([0.1, 0.2], [1e-6])
    with pytest.raises(ValueError, match="positive"):
        inverse_variance_summary([0.1], [0.0])
    with pytest.raises(ValueError, match="no estimates"):
        inverse_variance_summary([], [])


# --------------------------------------------------------------------------- multiplicity

def test_holm_matches_the_worked_example():
    assert holm_adjust([0.01, 0.02, 0.04, 0.5]) == pytest.approx([0.04, 0.06, 0.08, 0.5])


def test_holm_preserves_the_callers_ordering():
    shuffled = [0.04, 0.5, 0.01, 0.02]
    adjusted = holm_adjust(shuffled)
    assert adjusted[2] == pytest.approx(0.04)  # the p=0.01 entry, smallest
    assert adjusted[0] == pytest.approx(0.08)
    assert adjusted[1] == pytest.approx(0.5)


def test_holm_never_decreases_and_never_exceeds_one():
    adjusted = holm_adjust([0.001, 0.2, 0.9])
    assert all(0.0 <= v <= 1.0 for v in adjusted)
    assert adjusted[0] <= adjusted[2]


def test_holm_on_a_single_pvalue_is_unchanged():
    assert holm_adjust([0.03]) == pytest.approx([0.03])
    assert holm_adjust([]) == []


def test_holm_rejects_out_of_range_values():
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        holm_adjust([0.5, 1.4])


def test_holm_is_stricter_than_no_correction_for_the_family_of_four():
    """The SAP's per-dataset family: four comparisons, so the smallest p-value is quadrupled."""
    p = [0.01, 0.30, 0.45, 0.60]
    adjusted = holm_adjust(p)
    assert adjusted[0] == pytest.approx(0.04)
    assert adjusted[0] > p[0]
