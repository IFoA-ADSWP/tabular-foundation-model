"""`scripts/diagnostics/d5_eudirectlapse.py`: the reproduction, the ladder, and the falsifier.

The parts that must hold without a TabPFN fit are tested directly -- the §14.10 reproduction, the
collinearity reading, the ladder's shape, and the transform-fitted-on-train rule. The regime
comparison needs a model, so it is exercised through its pure pieces rather than by fitting.

Run:  python -m pytest tests/test_d5_eudirectlapse.py -v
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from provenance import DIAGNOSTIC_RECORD_FIELDS  # noqa: E402

SCRIPT = REPO_ROOT / "scripts" / "diagnostics" / "d5_eudirectlapse.py"


@pytest.fixture(scope="module")
def d5():
    spec = importlib.util.spec_from_file_location("d5_eudirectlapse", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["d5_eudirectlapse"] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# The wrongness check
# ---------------------------------------------------------------------------
def test_reproduction_reproduces_the_committed_baselines(d5):
    observed = d5.committed_baselines()
    block = d5.reproduction(observed)
    assert block["passed"], block
    # The three methods §14.10 names must all be present, mapped from the leaderboard's own labels.
    assert set(block["observed"]) == {"Linear", "GBM", "TabPFN"}
    assert block["observed"]["Linear"] > block["observed"]["GBM"] > block["observed"]["TabPFN"]


def test_reproduction_fails_on_a_shifted_baseline(d5):
    """A control that cannot fail is decoration: move Linear by 0.01 and it must go red."""
    observed = d5.committed_baselines()
    shifted = {label: dict(value) for label, value in observed.items()}
    shifted["Linear"]["mean_auc"] = round(shifted["Linear"]["mean_auc"] + 0.01, 6)
    block = d5.reproduction(shifted)
    assert not block["passed"]
    assert block["delta"]["Linear"] == pytest.approx(0.01, abs=1e-4)


def test_reproduction_names_a_missing_method(d5):
    observed = d5.committed_baselines()
    del observed["GBM"]
    with pytest.raises(SystemExit):
        d5.reproduction(observed)


def test_baselines_are_mean_of_one_minus_error(d5):
    observed = d5.committed_baselines()
    for label, block in observed.items():
        assert block["n_folds"] == 5, label
        assert block["mean_auc"] == pytest.approx(float(np.mean(block["per_fold"])), abs=1e-6)


# ---------------------------------------------------------------------------
# The collinear premium block
# ---------------------------------------------------------------------------
def test_premium_block_is_reported_collinear(d5):
    """The reading that D2's "different features" understates the overlap must be measured."""
    frame = d5.load_dataset()
    block = d5.premium_collinearity(frame)
    assert block["columns"] == list(d5.PREMIUM_COLUMNS)
    assert block["max_abs_correlation"] > 0.9
    assert set(block["strongest_pair"]) <= set(d5.PREMIUM_COLUMNS)
    assert block["matrix"]["prem_final"]["prem_pure"] == pytest.approx(0.9905, abs=1e-3)


# ---------------------------------------------------------------------------
# The ladder
# ---------------------------------------------------------------------------
def test_ladder_rungs_are_the_requested_ks_plus_all(d5):
    rng = np.random.default_rng(0)
    X = rng.normal(size=(400, 6)).astype(np.float32)
    y = (X[:, 0] * 2 + X[:, 1] - 1.5 > 0).astype(np.int64)
    names = [f"f{i}" for i in range(6)]
    ladder = d5.additivity_ladder(X, y, names, n_folds=3, ks=(1, 2))
    assert [int(k) for k in ladder["auc_by_k"]] == [1, 2, 6]
    assert ladder["n_rows"] == 400
    assert ladder["n_folds"] == 3


def test_ladder_recovers_a_known_additive_signal(d5):
    """Two additive features carry a linear task; the rung at k=2 should already rank well."""
    rng = np.random.default_rng(7)
    X = rng.normal(size=(1200, 8)).astype(np.float32)
    y = (X[:, 0] + X[:, 1] > 0).astype(np.int64)
    names = [f"f{i}" for i in range(8)]
    ladder = d5.additivity_ladder(X, y, names, n_folds=3, ks=(2,))
    assert ladder["auc_by_k"]["2"]["mean_auc"] > 0.85
    assert set(ladder["feature_order"][:2]) == {"f0", "f1"}


# ---------------------------------------------------------------------------
# The regimes
# ---------------------------------------------------------------------------
def _toy_frame(n=300, seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "lapse": rng.integers(0, 2, n),
            "prem_final": rng.normal(300, 50, n),
            "prem_pure": rng.normal(300, 50, n),
            "polholder_age": rng.integers(18, 80, n),
            "vehicl_region": rng.choice(["Reg1", "Reg2", "Reg3"], n),
        }
    )


def test_benchmark_regime_is_the_identity(d5):
    frame = _toy_frame()
    train, test = frame.iloc[:200], frame.iloc[200:]
    out_train, out_test, detail = d5.regime_frame(train, test, "benchmark")
    pd.testing.assert_frame_equal(out_train, train)
    pd.testing.assert_frame_equal(out_test, test)
    assert detail["regime"] == "benchmark"


def test_glm_top5_keeps_the_target_and_a_subset(d5):
    frame = _toy_frame()
    train, test = frame.iloc[:200], frame.iloc[200:]
    out_train, out_test, detail = d5.regime_frame(train, test, "glm_top5")
    assert "lapse" in out_train.columns
    assert len(detail["features"]) == min(d5.TOP_K, len(frame.columns) - 1)
    assert set(detail["features"]) < set(train.columns)
    assert not (set(detail["features"]) & set(detail["dropped"]))


def test_engineered_regime_replaces_the_premium_block(d5):
    frame = _toy_frame()
    train, test = frame.iloc[:200], frame.iloc[200:]
    out_train, out_test, detail = d5.regime_frame(train, test, "engineered")
    assert "premium_pc1" in out_train.columns and "premium_pc1" in out_test.columns
    assert "glm_logit" in out_train.columns and "glm_logit" in out_test.columns
    for column in d5.PREMIUM_COLUMNS[:2]:
        assert column not in out_train.columns
    assert len(out_train) == len(train) and len(out_test) == len(test)
    assert detail["transforms"]["glm_logit"].endswith("fitted on train only")


def test_engineered_logit_is_fitted_on_train_alone(d5):
    """Changing the test rows must not move the train-side log-odds by a single value.

    This is the leakage guard: the log-odds column is a model output, and if it were computed over
    the whole table the test rows would be inside the feature that is meant to help TabPFN.
    """
    frame = _toy_frame(n=400, seed=3)
    train, test = frame.iloc[:300], frame.iloc[300:]
    original_train, _, _ = d5.regime_frame(train, test, "engineered")

    scrambled = test.copy()
    scrambled["lapse"] = 1 - scrambled["lapse"]
    scrambled["polholder_age"] = scrambled["polholder_age"] + 7
    replayed_train, _, _ = d5.regime_frame(train, scrambled, "engineered")

    np.testing.assert_allclose(
        original_train["glm_logit"].to_numpy(), replayed_train["glm_logit"].to_numpy(),
    )


def test_unknown_regime_raises(d5):
    frame = _toy_frame()
    with pytest.raises(ValueError):
        d5.regime_frame(frame.iloc[:200], frame.iloc[200:], "nonsense")


# ---------------------------------------------------------------------------
# The verdict rule
# ---------------------------------------------------------------------------
def _regime_block(deltas):
    deltas = [float(d) for d in deltas]
    spread = np.std(deltas, ddof=1) / np.sqrt(len(deltas)) if len(deltas) > 1 else 0.0
    return {
        "per_seed": [{"delta_linear_minus_tabpfn": d} for d in deltas],
        "mean_delta": round(float(np.mean(deltas)), 6),
        "se_delta": round(float(spread), 6),
        "seeds_linear_ahead": sum(1 for d in deltas if d > 0),
        "n_seeds": len(deltas),
    }


def test_verdict_reads_a_closed_gap_as_the_linear_form(d5):
    """The measured shape, using this run's own per-seed deltas.

    The engineered residuals are not tidy: one seed reverses, one is +0.011, and the mean sits
    inside the interval. That spread is the evidence, so the fixture carries it rather than a
    cleaner series that would make the rule look more decisive than the data is.
    """
    regimes = {
        "benchmark": _regime_block([0.050781, 0.030103, 0.027881, 0.013403, 0.005913]),
        "engineered": _regime_block([0.003118, -0.006379, 0.006917, 0.000681, 0.011074]),
    }
    block = d5.verdict(regimes)
    assert block["conclusion"] == "glm is the right model for this dataset"
    assert block["feature_coverage"].startswith("the lever is the linear form")
    assert block["gap_closed_fraction"] > 0.8
    low, high = block["engineered_interval"]
    assert low < 0 < high
    assert block["seeds_linear_ahead"] == 4


def test_verdict_refutes_coverage_when_most_of_the_gap_survives(d5):
    block = d5.verdict(
        {
            "benchmark": _regime_block([0.020, 0.030, 0.010, 0.040, 0.020]),
            "engineered": _regime_block([0.020, 0.026, 0.022, 0.030, 0.024]),
        }
    )
    assert block["conclusion"] == "feature coverage refuted"
    assert block["feature_coverage"] == "refuted"


def test_verdict_supports_coverage_when_tabpfn_overtakes(d5):
    block = d5.verdict(
        {
            "benchmark": _regime_block([0.020, 0.030, 0.010, 0.040, 0.020]),
            "engineered": _regime_block([-0.010, -0.012, -0.008, -0.014, -0.011]),
        }
    )
    assert block["conclusion"] == "tabpfn needs these features"
    assert block["feature_coverage"] == "supported"


def test_verdict_names_a_small_residual_that_still_excludes_zero(d5):
    block = d5.verdict(
        {
            "benchmark": _regime_block([0.020, 0.030, 0.010, 0.040, 0.020]),
            "engineered": _regime_block([0.002, 0.003, 0.002, 0.003, 0.002]),
        }
    )
    assert block["conclusion"].startswith("the linear form closes most of the gap")


def test_verdict_says_not_tested_without_the_engineered_regime(d5):
    assert d5.verdict({"benchmark": _regime_block([0.02])})["conclusion"] == "not tested"


# ---------------------------------------------------------------------------
# The record
# ---------------------------------------------------------------------------
def test_measure_marks_d4_as_not_tested(d5):
    """The ticket consumes D4; the record must say it does not exist, not leave it implied."""
    block = d5.not_tested_block()
    assert "preprocessing_regime" in block
    assert "#305" in block["preprocessing_regime"]
    assert "equivalence" in block["fine_tuning"]


def test_skip_regimes_records_no_verdict(d5, monkeypatch):
    """`--skip-regimes` must not leave a verdict behind that nothing measured."""
    monkeypatch.setattr(d5, "additivity_ladder", lambda *a, **k: {"stubbed": True})
    measurements = d5.measure(d5.load_dataset(), skip_regimes=True, regimes=())
    assert measurements["regimes"] is None
    assert "verdict" not in measurements
    assert measurements["ladder"] == {"stubbed": True}


def test_record_fields_are_the_contract(d5):
    record = d5.DiagnosticRecord(
        diagnostic=d5.DIAGNOSTIC,
        run_id="test",
        model_version=None,
        seed=42,
        dataset_name=d5.DATASET,
        dataset_sha256=None,
        matched_context={},
    )
    assert set(DIAGNOSTIC_RECORD_FIELDS) == set(record.__dataclass_fields__)


# ---------------------------------------------------------------------------
# The power-run flag (#306 §9)
# ---------------------------------------------------------------------------
def test_seed_range_expands_inclusively(d5):
    assert d5._regime_seeds("42-46", None) == (42, 43, 44, 45, 46)
    assert d5._regime_seeds("331-332", None) == (331, 332)


def test_default_stays_five_seeds_when_no_range_is_given(d5):
    assert d5._regime_seeds(None, None) == d5.REGIME_SEEDS


def test_explicit_seed_list_is_parsed(d5):
    assert d5._regime_seeds(None, "42, 44 ,46") == (42, 44, 46)


def test_both_seed_forms_at_once_is_refused(d5):
    with pytest.raises(SystemExit):
        d5._regime_seeds("42-46", "42,43")


def test_a_malformed_or_inverted_range_is_refused(d5):
    for bad in ("42", "46-42", "a-b"):
        with pytest.raises(SystemExit):
            d5._regime_seeds(bad, None)


def test_a_repeated_seed_is_refused(d5):
    with pytest.raises(SystemExit):
        d5._regime_seeds(None, "42,42")


def test_main_forwards_the_seed_range_to_measure(d5, monkeypatch, tmp_path):
    """A flag that is parsed and not forwarded is worse than a flag that does not exist.

    This is the exact defect the first power run hit: `--seed-range` was accepted, `_regime_seeds`
    expanded it, and `measure` was called without `seeds` -- so the run reported five seeds under a
    sixty-six-seed request. It looked like a result, which is the failure mode.
    """
    captured = {}

    def fake_measure(frame, *, skip_regimes=False, regimes=(), model_path=None, seeds=()):
        captured["seeds"] = seeds
        captured["regimes"] = regimes
        return {
            "reproduction": {"passed": True, "delta": {"Linear": 0.0}},
            "premium_collinearity": {"max_abs_correlation": 0.99},
            "ladder": {"auc_by_k": {"1": {"mean_auc": 0.5}}},
            "regimes": None,
            "tabpfn": None,
            "not_tested": {},
        }

    monkeypatch.setattr(d5, "measure", fake_measure)
    monkeypatch.setattr(d5, "write_diagnostic_record", lambda record, root=None: tmp_path)

    d5.main(["--run-id", "t", "--seed-range", "42-44", "--regime", "benchmark"])

    assert captured["seeds"] == (42, 43, 44)
    assert captured["regimes"] == ("benchmark",)


def test_verdict_says_so_when_the_benchmark_gap_is_not_established(d5):
    """The sixty-six-seed result: a gap whose interval covers zero has nothing to explain.

    Five seeds put this at +0.0205 and sixty-six put it at +0.0054 with an interval covering zero.
    Saying "the linear form closes the gap" would then describe a gap that is not established.
    """
    # A gap of +0.005 with a spread wide enough that its interval covers zero -- which is what
    # sixty-six seeds produced. A fixture with no spread would pass this branch for the wrong reason.
    wide = [0.05, -0.04] * 33
    block = d5.verdict({
        "benchmark": _regime_block(wide),
        "engineered": _regime_block([-0.006, 0.004] * 33),
    })
    assert block["conclusion"] == "no gap is established at this row cap"
    assert block["benchmark_gap_favours_linear"] is False


def test_verdict_reports_a_reversal_as_parity_not_a_win(d5):
    """An engineered interval that covers zero with a negative point estimate is parity."""
    # The benchmark gap is established here (tight, positive), so this reaches the parity branch
    # rather than the "no gap" one; the engineered interval then covers zero with a negative mean.
    block = d5.verdict({
        "benchmark": _regime_block([0.020, 0.022] * 20),
        "engineered": _regime_block([-0.006, 0.004] * 20),
    })
    assert block["conclusion"].startswith("the engineered gap reverses")
    assert "parity" in block["reason"]


def test_a_multi_seed_run_does_not_stamp_a_single_split_seed(d5, monkeypatch, tmp_path):
    """ADR 0003: `seed` is the run's SPLIT seed, so a 66-seed run records the absence, not `42`.

    A record claiming seed=42 for a run that covered 42-107 is a field the artifact cannot back --
    the same class of error as a dropped parameter, one layer up.
    """
    captured = {}

    def fake_measure(frame, *, skip_regimes=False, regimes=(), model_path=None, seeds=()):
        return {
            "reproduction": {"passed": True, "delta": {"Linear": 0.0}},
            "premium_collinearity": {"max_abs_correlation": 0.99},
            "ladder": {"auc_by_k": {"1": {"mean_auc": 0.5}}},
            "seeds": list(seeds),
            "regimes": None,
            "tabpfn": None,
            "not_tested": {},
        }

    def capture(record, root=None):
        captured["record"] = record
        return tmp_path

    monkeypatch.setattr(d5, "measure", fake_measure)
    monkeypatch.setattr(d5, "write_diagnostic_record", capture)

    d5.main(["--run-id", "many", "--seed-range", "42-44", "--regime", "benchmark"])
    assert captured["record"].seed is None
    assert captured["record"].measurements["seeds"] == [42, 43, 44]

    d5.main(["--run-id", "one", "--regime-seeds", "42", "--regime", "benchmark"])
    assert captured["record"].seed == 42
    assert captured["record"].measurements["seeds"] == [42]
