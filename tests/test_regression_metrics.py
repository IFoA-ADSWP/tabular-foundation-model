"""The regression metric definitions, against numbers written here by hand (#538).

`tests/test_rescore_regression.py` checks the plumbing; this file checks the arithmetic. It must
not import the implementation's expectations from the implementation, or a sign flip would pass.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from metrics import gini, mae, medae, poisson_deviance, rmse, rmsle


def test_rmse_and_mae_on_a_two_row_case():
    truth = np.array([0.0, 2.0])
    prediction = np.array([1.0, 1.0])

    assert rmse(truth, prediction) == pytest.approx(1.0)
    assert mae(truth, prediction) == pytest.approx(1.0)


def test_medae_ignores_the_single_large_error():
    assert medae(np.array([0.0, 2.0, 10.0]), np.array([1.0, 1.0, 1.0])) == pytest.approx(1.0)


def test_rmsle_of_a_doubling_is_log_two():
    assert rmsle(np.array([0.0]), np.array([1.0])) == pytest.approx(math.log(2.0))


def test_rmsle_clips_a_negative_prediction_to_zero():
    # log1p(-0.5) would be a nan; the contract clips the prediction at 0 instead.
    assert rmsle(np.array([0.0]), np.array([-0.5])) == pytest.approx(0.0)


def test_poisson_deviance_hand_computed():
    # 2*0.5 (the y=0 row) + 0 (y=p) + 2*(2*ln 2 - 1) (the y=2 row) = 1.772588722239781
    assert poisson_deviance(
        np.array([0.0, 1.0, 2.0]), np.array([0.5, 1.0, 1.0])
    ) == pytest.approx(1.772588722239781)


def test_poisson_deviance_of_a_perfect_positive_prediction_is_zero():
    truth = np.array([1.0, 2.0])

    assert poisson_deviance(truth, truth) == pytest.approx(0.0)


def test_a_zero_row_costs_the_clip_when_the_prediction_is_zero():
    # The contract clips ŷ at 1e-12, so a perfect zero still contributes 2e-12; stated here
    # rather than left for a reader to discover in a tiny non-zero deviance.
    assert poisson_deviance(np.array([0.0]), np.array([0.0])) == pytest.approx(
        2e-12, rel=1e-6
    )


def test_gini_is_one_for_a_perfect_ranking_and_minus_one_for_its_reverse():
    truth = np.array([1.0, 2.0, 3.0])

    assert gini(truth, np.array([1.0, 2.0, 3.0])) == pytest.approx(1.0)
    assert gini(truth, np.array([3.0, 2.0, 1.0])) == pytest.approx(-1.0)


def test_gini_of_a_constant_prediction_is_zero():
    assert gini(np.array([1.0, 2.0, 3.0]), np.array([1.0, 1.0, 1.0])) == pytest.approx(0.0)


def test_gini_excludes_pairs_tied_on_truth():
    # The two 1s are never compared with each other; both compare with the 2, and both are
    # concordant, so the concordance is 1 and the Gini is 1.
    assert gini(np.array([1.0, 1.0, 2.0]), np.array([1.0, 2.0, 3.0])) == pytest.approx(1.0)


def test_a_pair_tied_on_prediction_scores_one_half():
    # Pairs: (1,2) ties on prediction -> 0.5; (1,3) and (2,3) are concordant -> 1 each.
    # C = 2.5/3, so the Gini is 2*C - 1 = 0.6666666...
    assert gini(np.array([1.0, 2.0, 3.0]), np.array([1.0, 1.0, 3.0])) == pytest.approx(
        2.0 / 3.0
    )


def test_gini_is_undefined_for_constant_truth():
    assert math.isnan(gini(np.array([1.0, 1.0, 1.0]), np.array([1.0, 2.0, 3.0])))
