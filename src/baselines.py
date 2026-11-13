"""The actuarial baselines: a GLM and a CatBoost, built the way a pricing team builds one (#597).

`E_glm` and `F_catboost` are **methods**, not Arms: an Arm varies how TabPFN is trained, a method
varies which predictor is compared (`GLOSSARY.md`). Both sit behind the runner's backend seam, so
the matrix is exercisable without TabPFN or a rented machine.

The configuration is not chosen here — it is registered in
`docs/experiments/fair-test-freq-sev/baseline_method_specification.md`, and the reasons live
there. Two implementation facts are load-bearing enough to repeat:

1. **The offset is realised as rate + weight.** scikit-learn 1.6.1 has no `offset` argument, and
   the weighted Poisson deviance on `y/E` with weight `E` is *equal* to the count deviance with
   `offset=log(E)`, not merely proportional — `tests/test_baselines.py` pins the identity against
   an independent offset fit rather than trusting this comment.
2. **The two methods need opposite categorical handling.** A GLM cannot read `.cat.codes` (an
   arbitrary linear order per region), and CatBoost must not be handed them either (it wants the
   raw strings in `cat_features`). `glm_design` and `catboost_frame` are the two stages.

Severity is a Gaussian model on `log(amount)` — the lognormal — because the registered metric is
RMSE on that scale. The Gamma family is deliberately absent: it estimates `E[Y]` on the amount
scale, which is a different functional from the `E[log Y]` the metric rewards (§3.3 of the
specification).
"""

from __future__ import annotations

import platform

import numpy as np
import pandas as pd

# The case study's GLM1 reference levels: the level dropped from each factor's dummies. With one
# level dropped per factor the design is full rank, so the unpenalised fit (`alpha=0`) is
# identifiable (§3.4 of the specification).
VEH_POWER_CAP = 9
BONUS_MALUS_CAP = 150
FRENCH_AREA = "ABCDEF"
VEH_AGE_LABELS = ("[0,1)", "[1,10]", "(10,inf)")
DRIV_AGE_LABELS = ("[18,21)", "[21,26)", "[26,31)", "[31,41)", "[41,51)", "[51,71)", "[71,inf)")
VEH_AGE_REFERENCE = "[1,10]"
DRIV_AGE_REFERENCE = "[41,51)"
VEH_BRAND_REFERENCE = "B1"
VEH_GAS_REFERENCE = "Diesel"
REGION_REFERENCE = "R24"

HYPERPARAMETERS_GLM = {"alpha": 0.0, "max_iter": 500, "tol": 1e-10}
HYPERPARAMETERS_CATBOOST = {
    "iterations": 1000,
    "depth": 6,
    "learning_rate": 0.03,
    "l2_leaf_reg": 3.0,
}


# ---------------------------------------------------------------------------
# Encodings
# ---------------------------------------------------------------------------
def _veh_age_bin(age: np.ndarray) -> np.ndarray:
    """`[0,1)`, `[1,10]`, `(10,inf)` — the case study's three vehicle-age classes."""
    return np.select([age < 1, age <= 10], [VEH_AGE_LABELS[0], VEH_AGE_LABELS[1]],
                     default=VEH_AGE_LABELS[2])


def _driv_age_bin(age: np.ndarray) -> np.ndarray:
    """The case study's seven driver-age classes, `[41,51)` as the reference."""
    edges = (21, 26, 31, 41, 51, 71)
    labels = DRIV_AGE_LABELS
    return np.select(
        [age < edges[0], age < edges[1], age < edges[2], age < edges[3], age < edges[4],
         age < edges[5]],
        list(labels[:6]),
        default=labels[6],
    )


def _dummies(frame: pd.DataFrame, columns: tuple[str, ...], reference: dict[str, str]) -> pd.DataFrame:
    """One-hot with an explicit reference level dropped per factor.

    `pd.get_dummies(drop_first=True)` drops the first *category*, so ordering each categorical with
    its registered reference first is what makes the drop land on the intended level.
    """
    staged = pd.DataFrame(index=frame.index)
    for column in columns:
        values = frame[column].astype(str)
        # The levels are strings once `astype(str)` has run, so the reference must be compared as
        # one too — otherwise an integer reference (VehPower 4) never drops its own level.
        ref = str(reference[column])
        categories = [ref] + sorted(set(values) - {ref})
        staged[column] = pd.Categorical(values, categories=categories)
    return pd.get_dummies(staged, columns=list(columns), drop_first=True, dtype=float)


def french_glm_design(frame: pd.DataFrame) -> pd.DataFrame:
    """The case study's GLM1 encoding: bins, merges, references, and `Area` continuous."""
    out = pd.DataFrame(index=frame.index)
    out["Area"] = frame["Area"].map(
        {letter: index + 1 for index, letter in enumerate(FRENCH_AREA)}
    ).astype(float)
    out["BonusMalus"] = np.minimum(frame["BonusMalus"].to_numpy(dtype=float), BONUS_MALUS_CAP)
    out["log_Density"] = np.log(frame["Density"].to_numpy(dtype=float))

    factors = pd.DataFrame(index=frame.index)
    factors["VehPower"] = np.minimum(frame["VehPower"].to_numpy(dtype=int), VEH_POWER_CAP)
    factors["VehAge"] = _veh_age_bin(frame["VehAge"].to_numpy(dtype=float))
    factors["DrivAge"] = _driv_age_bin(frame["DrivAge"].to_numpy(dtype=float))
    factors["VehBrand"] = frame["VehBrand"].astype(str)
    factors["VehGas"] = frame["VehGas"].astype(str)
    factors["Region"] = frame["Region"].astype(str)

    reference = {
        "VehPower": min(int(frame["VehPower"].min()), VEH_POWER_CAP),
        "VehAge": VEH_AGE_REFERENCE,
        "DrivAge": DRIV_AGE_REFERENCE,
        "VehBrand": VEH_BRAND_REFERENCE,
        "VehGas": VEH_GAS_REFERENCE,
        "Region": REGION_REFERENCE,
    }
    encoded = _dummies(
        factors,
        ("VehPower", "VehAge", "DrivAge", "VehBrand", "VehGas", "Region"),
        reference,
    )
    return pd.concat([out, encoded], axis=1)


def spanish_glm_design(frame: pd.DataFrame) -> pd.DataFrame:
    """The Spanish frame is numeric apart from `Type_fuel`; one-hot it, keep the rest as given."""
    categorical = tuple(
        column for column in frame.columns
        if not np.issubdtype(frame[column].dtype, np.number)
    )
    if not categorical:
        return frame.astype(float)
    reference = {column: sorted(frame[column].astype(str).unique())[0] for column in categorical}
    numeric = frame.drop(columns=list(categorical)).astype(float)
    return pd.concat([numeric, _dummies(frame, categorical, reference)], axis=1)


def glm_design(frame: pd.DataFrame, portfolio: str) -> pd.DataFrame:
    """The design matrix the registered specification names, for one portfolio."""
    if portfolio == "french":
        return french_glm_design(frame)
    return spanish_glm_design(frame)


def catboost_frame(frame: pd.DataFrame, *, drop: tuple[str, ...] = ()) -> pd.DataFrame:
    """The raw view CatBoost reads: nothing encoded, categoricals as strings.

    Built once on the whole frame before any split, as the case study insists — doing the
    pre-processing after the split is one of its named mistakes. `drop` removes a column whose
    role the model has taken another way; on frequency that is `Exposure`, which is the offset and
    must not also be a feature, or the elasticity is estimated instead of fixed at one.
    """
    out = frame.drop(columns=[column for column in drop if column in frame.columns]).copy()
    for column in out.columns:
        if not np.issubdtype(out[column].dtype, np.number):
            out[column] = out[column].astype(str)
    return out


def cat_features(frame: pd.DataFrame) -> list[str]:
    """The columns CatBoost converts to target statistics, in frame order."""
    return [
        column for column in frame.columns
        if not np.issubdtype(frame[column].dtype, np.number)
    ]


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------
def _frequency_response(request):
    """The response, weight and test-scale factor of a frequency fit.

    French policies carry an exposure, so the registered realisation is rate + weight and the
    prediction is a rate multiplied back by exposure. The Spanish view has no exposure column,
    so the count is the response and the weight is 1 (`baseline_method_specification.md` §1).
    """
    if request.exposure_train is None:
        return request.y_train, np.ones(len(request.y_train)), None
    return (
        request.y_train / request.exposure_train,
        request.exposure_train,
        request.exposure_test,
    )


class GlmBackend:
    """`E_glm`: Poisson-log on the rate, and a Gaussian identity on `log(amount)`."""

    method = "E_glm"

    def __init__(self) -> None:
        self._designs: dict[str, pd.DataFrame] = {}

    def provenance(self) -> dict:
        import sklearn  # noqa: PLC0415

        return {
            "versions": {
                "scikit-learn": sklearn.__version__,
                "python": platform.python_version(),
            }
        }

    def _design(self, request) -> pd.DataFrame:
        """The design is built once per target, on the whole frame before any split."""
        key = request.target.name
        if key not in self._designs:
            self._designs[key] = glm_design(request.frame, request.target.portfolio)
        return self._designs[key]

    def fit_predict(self, request):
        from sklearn.linear_model import PoissonRegressor, TweedieRegressor  # noqa: PLC0415

        design = self._design(request)
        X_train = design.iloc[request.train_index]
        X_test = design.iloc[request.test_index]

        if request.target.task == "frequency":
            y, weight, exposure_test = _frequency_response(request)
            model = PoissonRegressor(**HYPERPARAMETERS_GLM)
            model.fit(X_train, y, sample_weight=weight)
            predictions = model.predict(X_test)
            if exposure_test is not None:
                predictions = predictions * exposure_test
            return predictions, None

        # power=0 with an identity link is OLS on log(amount): the lognormal severity model the
        # registered RMSE rewards (§3.3). The claim weight is the design's, and is 1 in French.
        model = TweedieRegressor(power=0, link="identity", **HYPERPARAMETERS_GLM)
        model.fit(X_train, request.y_train, sample_weight=request.weights_train)
        return model.predict(X_test), None


class CatBoostBackend:
    """`F_catboost`: shipped defaults, raw categoricals, Poisson and RMSE objectives."""

    method = "F_catboost"

    def __init__(self) -> None:
        self._frames: dict[tuple[str, bool], pd.DataFrame] = {}

    def provenance(self) -> dict:
        import catboost  # noqa: PLC0415

        return {
            "versions": {
                "catboost": catboost.__version__,
                "python": platform.python_version(),
            }
        }

    def _frame(self, request) -> pd.DataFrame:
        offset = request.exposure_train is not None
        key = (request.target.name, offset)
        if key not in self._frames:
            self._frames[key] = catboost_frame(
                request.frame, drop=("Exposure",) if offset else ()
            )
        return self._frames[key]

    def fit_predict(self, request):
        from catboost import CatBoostRegressor  # noqa: PLC0415

        frame = self._frame(request)
        X_train = frame.iloc[request.train_index]
        X_test = frame.iloc[request.test_index]
        categories = cat_features(frame)

        if request.target.task == "frequency":
            y, weight, exposure_test = _frequency_response(request)
            loss = "Poisson"
        else:
            y, weight, exposure_test = request.y_train, request.weights_train, None
            loss = "RMSE"

        model = CatBoostRegressor(
            loss_function=loss,
            random_seed=request.seed,
            verbose=0,
            allow_writing_files=False,
            **HYPERPARAMETERS_CATBOOST,
        )
        model.fit(X_train, y, cat_features=categories, sample_weight=weight)
        # Poisson predicts on the mean scale (`Exponent`), so the French rate is multiplied back
        # to a count before the registered deviance is taken.
        predictions = model.predict(
            X_test, prediction_type="Exponent" if loss == "Poisson" else "RawFormulaVal"
        )
        if exposure_test is not None:
            predictions = predictions * exposure_test
        return np.asarray(predictions, dtype=float), None


class InterceptBackend:
    """The null anchor: one parameter per target, so a rank is never reported without it.

    It carries the same exposure treatment as the GLM — the intercept of a Poisson model with an
    offset is the exposure-weighted mean rate — so the anchor is a genuine one-parameter member of
    the same model space rather than a different metric.
    """

    method = "M_intercept"

    def provenance(self) -> dict:
        return {
            "versions": {"numpy": np.__version__, "python": platform.python_version()}
        }

    def fit_predict(self, request):
        if request.target.task == "frequency":
            y, weight, exposure_test = _frequency_response(request)
            rate = float(np.average(y, weights=weight))
            predictions = np.full(len(request.test_index), rate)
            if exposure_test is not None:
                predictions = predictions * exposure_test
            return predictions, None
        return np.full(len(request.test_index), float(np.mean(request.y_train))), None


BACKENDS = {
    "E_glm": GlmBackend,
    "F_catboost": CatBoostBackend,
    "M_intercept": InterceptBackend,
}
