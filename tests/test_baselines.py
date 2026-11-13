"""The actuarial baselines (#597): the registered encodings and the offset identity.

Two things are pinned numerically rather than asserted in prose:

1. **Rate + weight is the offset model.** scikit-learn 1.6.1 has no `offset` argument, so the
   registered frequency GLM is fitted on `ClaimNb/Exposure` with weight `Exposure`. That is only
   the offset model if the maximisers coincide, so the test fits the offset likelihood with an
   independent optimiser and compares coefficients.
2. **The two methods need opposite categorical handling.** A GLM gets the case study's GLM1
   encoding with one reference level dropped per factor; CatBoost gets the raw strings.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from baselines import (
    CatBoostBackend,
    GlmBackend,
    InterceptBackend,
    cat_features,
    catboost_frame,
    french_glm_design,
    spanish_glm_design,
)
from fair_test_runner import FitRequest
from freq_sev_data import TARGETS


def french_frame(rows: int = 6) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Area": list("ABCDEF")[:rows],
            "VehPower": np.arange(4, 4 + rows),
            "VehAge": np.arange(rows),
            "DrivAge": [18, 25, 30, 40, 45, 80][:rows],
            "BonusMalus": [50, 60, 200, 70, 80, 90][:rows],
            "VehBrand": ["B1", "B2", "B1", "B3", "B2", "B1"][:rows],
            "VehGas": ["Diesel", "Regular", "Diesel", "Regular", "Diesel", "Regular"][:rows],
            "Density": [1.0, 10.0, 100.0, 1000.0, 10_000.0, 100.0][:rows],
            "Region": ["R24", "R11", "R24", "R21", "R11", "R24"][:rows],
            "Exposure": np.full(rows, 0.5),
            "ClaimNb": np.arange(rows) % 2,
        }
    )


def request_for(
    *,
    target_name: str = "frequency_french",
    frame: pd.DataFrame | None = None,
    X: np.ndarray | None = None,
    y: np.ndarray | None = None,
    exposure: np.ndarray | None = None,
    weights: np.ndarray | None = None,
    seed: int = 0,
) -> FitRequest:
    spec = next(target for target in TARGETS if target.name == target_name)
    frame = french_frame() if frame is None else frame
    rows = len(frame)
    index = np.arange(rows, dtype=np.int64)
    X = np.zeros((rows, 1)) if X is None else X
    y = np.zeros(rows) if y is None else y
    weights = np.ones(rows) if weights is None else weights
    return FitRequest(
        target=spec,
        X_train=X,
        X_test=X,
        y_train=y,
        frame=frame,
        train_index=index,
        test_index=index,
        weights_train=weights,
        weights_test=weights,
        exposure_train=exposure,
        exposure_test=exposure,
        seed=seed,
        epochs=None,
    )


# ---------------------------------------------------------------------------
# The GLM1 encoding
# ---------------------------------------------------------------------------
def test_the_glm_design_drops_the_registered_reference_levels():
    design = french_glm_design(french_frame())

    for dropped in ("VehBrand_B1", "Region_R24", "VehGas_Diesel", "VehPower_4",
                    "VehAge_[1,10]", "DrivAge_[41,51)"):
        assert dropped not in design.columns, f"{dropped} should be the dropped reference level"
    assert {"VehBrand_B2", "Region_R11", "VehGas_Regular"} <= set(design.columns)


def test_the_glm_design_keeps_area_continuous_and_caps_bonus_malus():
    frame = french_frame()
    design = french_glm_design(frame)

    assert design["Area"].tolist() == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    assert design["BonusMalus"].tolist() == [50.0, 60.0, 150.0, 70.0, 80.0, 90.0]
    assert design["log_Density"].tolist() == pytest.approx(np.log(frame["Density"]))


def test_the_glm_design_bins_driver_age_at_the_case_study_edges():
    frame = french_frame()
    frame["DrivAge"] = [18, 20, 21, 25, 26, 40]
    design = french_glm_design(frame)

    # The reference class carries no dummy, so a 41-year-old is all zeros in the DrivAge block.
    reference = french_frame()
    reference["DrivAge"] = [41] * len(reference)
    assert not any(column.startswith("DrivAge_") for column in french_glm_design(reference).columns)

    age_columns = [column for column in design.columns if column.startswith("DrivAge_")]
    assert age_columns == [
        "DrivAge_[18,21)",
        "DrivAge_[21,26)",
        "DrivAge_[26,31)",
        "DrivAge_[31,41)",
    ]
    assert design.loc[0, "DrivAge_[18,21)"] == 1.0
    assert design.loc[1, "DrivAge_[18,21)"] == 1.0
    assert design.loc[2, "DrivAge_[21,26)"] == 1.0
    assert design.loc[5, "DrivAge_[31,41)"] == 1.0


def test_the_glm_design_merges_vehicle_power_above_nine():
    frame = french_frame()
    frame["VehPower"] = [4, 5, 6, 7, 8, 15]
    design = french_glm_design(frame)

    power_columns = [column for column in design.columns if column.startswith("VehPower_")]
    assert power_columns == [f"VehPower_{value}" for value in (5, 6, 7, 8, 9)]
    assert not any(column.startswith("VehPower_10") for column in design.columns)
    assert design.loc[5, "VehPower_9"] == 1.0  # 15 is merged into the top class


def test_the_spanish_glm_design_one_hots_the_fuel_type_only():
    frame = pd.DataFrame({"driver_age": [30.0, 40.0], "Type_fuel": ["P", "R"],
                          "Area": [1, 2], "N_claims_year": [0, 1]})
    design = spanish_glm_design(frame)

    assert "Type_fuel_P" not in design.columns  # first sorted level is the reference
    assert "Type_fuel_R" in design.columns
    assert design["Area"].tolist() == [1.0, 2.0]


# ---------------------------------------------------------------------------
# Rate + weight is the offset model
# ---------------------------------------------------------------------------
def _synthetic_frequency(rows: int = 500, seed: int = 0):
    rng = np.random.default_rng(seed)
    X = np.column_stack([np.ones(rows), rng.normal(size=(rows, 2))])
    beta = np.array([-1.0, 0.3, -0.2])
    exposure = rng.uniform(0.05, 1.0, size=rows)
    rate = np.exp(X @ beta)
    counts = rng.poisson(rate * exposure)
    return X, beta, exposure, counts


def _offset_mle(X, counts, exposure):
    """The Poisson MLE with `offset=log(Exposure)`, by Newton–Raphson.

    An independent implementation on purpose: comparing `PoissonRegressor` against the same
    library's IRLS would prove only that a function equals itself.
    """
    beta = np.zeros(X.shape[1])
    for _ in range(100):
        mu = np.exp(X @ beta + np.log(exposure))
        gradient = X.T @ (mu - counts)
        hessian = X.T @ (X * mu[:, None])
        step = np.linalg.solve(hessian, gradient)
        beta = beta - step
        if np.max(np.abs(step)) < 1e-13:
            break
    else:  # pragma: no cover - a convergent Poisson fit reaches the tolerance in ~10 steps
        raise AssertionError("the offset Newton fit did not converge")
    return beta


def test_the_rate_weight_fit_is_the_offset_fit():
    from sklearn.linear_model import PoissonRegressor

    X, _, exposure, counts = _synthetic_frequency()
    model = PoissonRegressor(alpha=0.0, max_iter=500, tol=1e-10)
    # X[:, 0] is the intercept column the offset fit needs; scikit-learn adds its own.
    model.fit(X[:, 1:], counts / exposure, sample_weight=exposure)

    offset = _offset_mle(X, counts, exposure)
    fitted = np.concatenate([[model.intercept_], model.coef_])

    assert fitted == pytest.approx(offset, abs=1e-8), (fitted, offset)


def test_the_weighted_deviance_on_the_rate_equals_the_count_deviance():
    """With `mu = E*m`, `d(y, mu) = E*d(r, m)` exactly — not up to a constant.

    `metrics.poisson_deviance` is the registered, unweighted total; the rate form is what a
    weighted Poisson fit minimises. The two must agree on the same fitted rate.
    """
    import metrics

    _, _, exposure, counts = _synthetic_frequency()
    rate = counts / exposure
    rate_pred = np.clip(0.9 * rate + 0.05, 1e-12, None)  # any positive rate; not the fit

    positive = rate > 0
    terms = np.where(positive, rate * np.log(np.where(positive, rate, 1.0) / rate_pred), 0.0)
    weighted = float(2 * np.sum(exposure * (terms - (rate - rate_pred))))
    count_deviance = metrics.poisson_deviance(counts, exposure * rate_pred)

    assert weighted == pytest.approx(count_deviance, rel=1e-12)


# ---------------------------------------------------------------------------
# The backends behind the seam
# ---------------------------------------------------------------------------
def _french_frequency_request(rows: int = 200, seed: int = 0) -> FitRequest:
    rng = np.random.default_rng(seed)
    frame = french_frame(rows=6).iloc[np.arange(rows) % 6].reset_index(drop=True)
    exposure = rng.uniform(0.1, 1.0, size=rows)
    rate = 0.1 + 0.05 * rng.integers(0, 3, size=rows)
    counts = rng.poisson(rate * exposure)
    frame["Exposure"] = exposure
    frame["ClaimNb"] = counts
    return request_for(
        frame=frame,
        y=counts.astype(float),
        exposure=exposure,
        weights=np.ones(rows),
    )


def test_the_glm_predicts_a_count_not_a_rate():
    request = _french_frequency_request()
    predictions, quantiles = GlmBackend().fit_predict(request)

    assert quantiles is None, "a GLM has no predictive distribution to retain"
    assert predictions.shape == (len(request.test_index),)
    # A count is exposure-scaled, so the mean cannot be the ~0.2 rate the response was fitted on.
    assert predictions.mean() > 0.1 * request.exposure_test.mean()


def test_the_glm_survives_an_unscaled_design():
    """Measured 2026-11-13: `lbfgs` overflowed on the Spanish columns and returned the intercept.

    The Spanish score is a red flag rather than a crash: a constant prediction is a valid array and
    scores exactly the anchor's deviance, so nothing in the capture refuses it. The solver and the
    design's scale are engineering, and this pins that the fit is not the anchor.
    """
    frame = pd.DataFrame(
        {
            "Premium": [1_000_000.0, 2_000_000.0, 3_000_000.0, 4_000_000.0, 5_000_000.0, 6_000_000.0],
            "Value_vehicle": [1e7, 2.1e7, 2.9e7, 4.2e7, 5.1e7, 6.3e7],
            "Area": [0, 1, 0, 1, 0, 1],
            "Type_fuel": ["P", "P", "R", "R", "P", "R"],
        }
    )
    y = np.array([0.0, 1.0, 0.0, 1.0, 0.0, 1.0])
    request = request_for(target_name="frequency_spanish", frame=frame, y=y)

    predictions, quantiles = GlmBackend().fit_predict(request)

    assert quantiles is None
    assert np.all(np.isfinite(predictions))
    assert np.std(predictions) > 1e-9, "the fit collapsed to the intercept"


def test_catboost_reads_raw_categoricals_and_declines_quantiles():
    request = _french_frequency_request(rows=60)
    frame = catboost_frame(request.frame, drop=("Exposure",))
    assert frame["Region"].dtype == object
    assert cat_features(frame) == ["Area", "VehBrand", "VehGas", "Region"]
    assert "Exposure" not in frame.columns, "exposure is the offset, not also a feature"

    predictions, quantiles = CatBoostBackend().fit_predict(request)
    assert quantiles is None
    assert np.all(np.isfinite(predictions)) and np.all(predictions > 0)


def test_the_intercept_anchor_is_the_exposure_weighted_mean_rate():
    request = _french_frequency_request(rows=30)
    predictions, quantiles = InterceptBackend().fit_predict(request)

    expected_rate = np.average(
        request.y_train / request.exposure_train, weights=request.exposure_train
    )
    assert quantiles is None
    assert predictions == pytest.approx(expected_rate * request.exposure_test)
