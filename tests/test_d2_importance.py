"""`scripts/diagnostics/d2_importance.py`: what each family uses, and the check that it is real.

Three things are tested here, in the order a reader would distrust them:

* the **measurement** -- permutation importance finds a planted signal and leaves noise at zero,
  and the same seed produces the same matrix;
* the **readings** -- the design's three questions are answered by numbers in the record, not left
  to the reader's eye over two top-tens;
* the **wrongness check** -- a control that cannot fail is decoration, so both its pass and its
  fail are exercised, and a failing control still writes its record and exits non-zero.

Nothing here fits TabPFN: the model builders are injected (`main(..., families=...)`, the same seam
D1 uses for its dataset registry), so the suite stays offline and fast.

Run:  python -m pytest tests/test_d2_importance.py -v
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


from provenance import DIAGNOSTIC_RECORD_FIELDS, read_diagnostic_record  # noqa: E402

SCRIPT = REPO_ROOT / "scripts" / "diagnostics" / "d2_importance.py"


@pytest.fixture(scope="module")
def d2():
    spec = importlib.util.spec_from_file_location("d2_importance", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["d2_importance"] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Fakes: a fitted-model builder whose predictions are a known function of the rows
# ---------------------------------------------------------------------------
class SignedSumModel:
    """Scores rows by one column, so its permutation importance has a known answer."""

    def __init__(self, column=0, scale=6.0):
        self.column = column
        self.scale = scale

    def fit(self, X, y):  # noqa: ARG002 - sklearn-shaped, the values are irrelevant
        return self

    def predict_proba(self, X):
        # A steep logistic in one column: shuffling that column must cost real AUC, and the
        # others must cost none.
        logits = self.scale * X[:, self.column]
        probability = 1.0 / (1.0 + np.exp(-logits))
        return np.column_stack([1.0 - probability, probability])


def _signal_frame(rows=300, seed=0):
    rng = np.random.default_rng(seed)
    signal = rng.normal(size=rows)
    noise = rng.normal(size=rows)
    label = (signal + rng.normal(size=rows) * 0.3 > 0).astype(int)
    return pd.DataFrame({"signal": signal, "noise": noise, "target": label})


def signed_sum_builder(X, y):
    """A family builder whose model reads one column -- the shape `main(families=...)` needs."""
    return SignedSumModel(column=0).fit(X, y)


def _write_frame(frame, path):
    frame.to_csv(path, index=False)
    return path


# ---------------------------------------------------------------------------
# The working set
# ---------------------------------------------------------------------------
def test_the_split_applies_the_cap_before_splitting(d2):
    rng = np.random.default_rng(1)
    frame = pd.DataFrame(
        {"x": rng.normal(size=5000), "target": (rng.random(5000) < 0.2).astype(int)}
    )

    train, test, meta = d2.stratified_split(frame, "target", cap=2000, test_rows=500, seed=42)

    assert meta["rows_sampled"] == 2000
    assert meta["rows_available"] == 5000
    assert len(train) == 1500 and len(test) == 500
    # Stratified: the rare class survives the cap at roughly its population rate.
    assert meta["test_positive_rate"] == pytest.approx(0.2, abs=0.05)
    # The ticket's words, in the field a reader would check.
    assert meta["cap_rows"] == 2000
    assert "approximation" in meta["note"]
    assert "2000-row subsample" in meta["note"]


def test_the_split_is_reproducible_for_a_seed(d2):
    frame = _signal_frame(rows=800)
    first = d2.stratified_split(frame, "target", cap=500, test_rows=100, seed=7)
    second = d2.stratified_split(frame, "target", cap=500, test_rows=100, seed=7)
    third = d2.stratified_split(frame, "target", cap=500, test_rows=100, seed=8)

    assert first[0].index.tolist() == second[0].index.tolist()
    assert first[1].index.tolist() == second[1].index.tolist()
    assert first[0].index.tolist() != third[0].index.tolist()


def test_a_categorical_seen_only_in_the_test_rows_encodes_to_zero(d2):
    train = pd.DataFrame({"kind": ["a", "b", "a", "b"], "target": [0, 1, 0, 1]})
    test = pd.DataFrame({"kind": ["a", "z"], "target": [0, 1]})

    X_train, X_test, names, dropped = d2.encode_features(train, test, "target")

    assert names == ["kind"] and dropped == []
    assert X_test[1, 0] == 0.0  # "z" was never seen in training: missing, then 0.0
    assert X_test[0, 0] == X_train[0, 0]


def test_a_feature_constant_in_training_is_dropped_and_named(d2):
    train = pd.DataFrame({"useful": [0.0, 1.0, 2.0, 3.0], "flat": [1.0, 1.0, 1.0, 1.0], "target": [0, 1, 0, 1]})
    test = pd.DataFrame({"useful": [0.5, 1.5], "flat": [1.0, 2.0], "target": [0, 1]})

    _, _, names, dropped = d2.encode_features(train, test, "target")

    assert dropped == ["flat"]
    assert names == ["useful"]  # constant in training even though it varies in test


# ---------------------------------------------------------------------------
# Permutation importance
# ---------------------------------------------------------------------------
def test_importance_ranks_the_planted_signal_first_and_noise_near_zero(d2):
    rng = np.random.default_rng(3)
    signal = rng.normal(size=400)
    noise = rng.normal(size=400)
    y = (signal + rng.normal(size=400) * 0.2 > 0).astype(int)
    X = np.column_stack([signal, noise, rng.normal(size=400)])

    model = SignedSumModel(column=0).fit(X, y)
    baseline, importance = d2.permutation_importance(
        d2.positive_probability(model), X, y, n_repeats=3, seed=42
    )
    ranking = d2.rank_features(["signal", "noise", "other_noise"], importance)

    assert baseline > 0.9
    assert ranking[0]["feature"] == "signal"
    assert ranking[0]["importance"] > 0.3
    assert ranking[1]["importance"] < 0.05
    assert ranking[2]["importance"] < 0.05


def test_importance_is_reproducible_for_a_seed(d2):
    frame = _signal_frame(rows=400)
    X = frame[["signal", "noise"]].to_numpy()
    y = frame["target"].to_numpy()

    predict = d2.positive_probability(SignedSumModel(column=0).fit(X, y))
    first = d2.permutation_importance(predict, X, y, n_repeats=2, seed=11)[1]
    second = d2.permutation_importance(predict, X, y, n_repeats=2, seed=11)[1]
    third = d2.permutation_importance(predict, X, y, n_repeats=2, seed=12)[1]

    np.testing.assert_allclose(first, second)
    assert not np.allclose(first, third)


# ---------------------------------------------------------------------------
# The three readings
# ---------------------------------------------------------------------------
def _rankings(pairs):
    """`{family: [(feature, importance), ...]}` in the order given, as `rank_features` output."""
    return {
        family: [
            {"feature": feature, "importance": importance, "std": 0.0}
            for feature, importance in rows
        ]
        for family, rows in pairs.items()
    }


def test_readings_separate_a_rank_move_from_a_missing_feature(d2):
    """`shared` and `only_*` answer different questions and must not be conflated."""
    rankings = _rankings(
        {
            "glm": [("a", 0.5), ("b", 0.4), ("c", 0.3), ("d", 0.2)],
            "lgbm": [("b", 0.5), ("a", 0.4), ("d", 0.3), ("c", 0.2)],
            "tabpfn": [("e", 0.5), ("f", 0.4), ("g", 0.3), ("h", 0.2)],
        }
    )
    univariate = {name: 0.5 for name in "abcdefgh"}

    readings = d2.compare_readings(rankings, univariate, k=2)

    glm_lgbm = next(
        pair for pair in readings["same_features_ranked_differently"] if {pair["a"], pair["b"]} == {"glm", "lgbm"}
    )
    assert glm_lgbm["shared_top_k"] == 2
    # Ranks 1,2,3,4 against 2,1,4,3 -- correlated, moved, and not the same ordering.
    assert glm_lgbm["spearman_all_features"] == pytest.approx(0.6)
    assert glm_lgbm["largest_rank_moves"][0]["feature"] in {"a", "b"}

    glm_tabpfn = next(
        pair for pair in readings["different_features"] if {pair["a"], pair["b"]} == {"glm", "tabpfn"}
    )
    assert glm_tabpfn["only_a"] == ["a", "b"]
    assert glm_tabpfn["only_b"] == ["e", "f"]
    assert glm_tabpfn["jaccard_top_k"] == 0.0


def test_an_interaction_candidate_is_a_tree_top_feature_with_no_marginal_signal(d2):
    """The tree-only reading: high LGBM importance, no univariate signal, seen by no other family."""
    rankings = _rankings(
        {
            "glm": [("linear", 0.5), ("shared", 0.4), ("xor", 0.3)],
            "lgbm": [("xor", 0.5), ("linear", 0.4), ("shared", 0.3)],
        }
    )
    univariate = {"linear": 0.80, "shared": 0.70, "xor": 0.505}

    readings = d2.compare_readings(rankings, univariate, k=2)
    interaction = readings["interaction_only"]

    assert interaction["tree_only_features"] == ["xor"]
    assert interaction["candidates"] == ["xor"]
    # Present in the ranking, outside the top: the rank is recorded, not inferred.
    assert interaction["detail"][0]["ranks"] == {"glm": 3}
    assert interaction["compared_against"] == ["glm"]
    assert "0.02" in interaction["rule"]


def test_a_feature_tabpfn_also_ranks_first_is_not_tree_only(d2):
    """TabPFN is an interaction learner: a feature it uses is not "visible only to the tree model"."""
    rankings = _rankings(
        {
            "glm": [("linear", 0.5), ("shared", 0.4)],
            "lgbm": [("xor", 0.5), ("linear", 0.4)],
            "tabpfn": [("xor", 0.6), ("linear", 0.2)],
        }
    )
    univariate = {"linear": 0.80, "shared": 0.70, "xor": 0.505}

    interaction = d2.compare_readings(rankings, univariate, k=2)["interaction_only"]

    assert interaction["compared_against"] == ["tabpfn", "glm"]
    assert interaction["tree_only_features"] == []  # TabPFN ranks xor first, so it is not tree-only
    assert interaction["candidates"] == []


# ---------------------------------------------------------------------------
# The wrongness check
# ---------------------------------------------------------------------------
def test_the_control_passes_when_the_permuted_label_cannot_dominate(d2):
    real = _rankings({"glm": [("a", 0.40), ("b", 0.02)]})
    control = _rankings({"glm": [("b", 0.03), ("a", 0.01)]})

    block = d2.control_block(real, control, k=2)

    assert block["passed"] is True
    assert block["families"][0]["ratio_to_real_top"] == pytest.approx(0.075)


def test_the_control_fails_when_a_feature_dominates_a_permuted_label(d2):
    real = _rankings({"glm": [("a", 0.40), ("b", 0.02)]})
    control = _rankings({"glm": [("leak", 0.55), ("a", 0.01)]})

    block = d2.control_block(real, control, k=2)

    assert block["passed"] is False
    assert block["families"][0]["control_top_feature"] == "leak"


def test_the_control_threshold_is_the_real_top_not_the_kth(d2):
    """A k-th-place threshold would pass on noise; the top is what "dominate" means."""
    real = _rankings({"glm": [("a", 0.40), ("b", 0.02), ("c", -0.01)]})
    control = _rankings({"glm": [("b", 0.05), ("a", 0.01), ("c", 0.0)]})

    block = d2.control_block(real, control, k=3)

    assert block["passed"] is True  # 0.05 clears the k-th (-0.01) but not the top (0.40)


# ---------------------------------------------------------------------------
# The record
# ---------------------------------------------------------------------------
@pytest.fixture
def two_datasets(tmp_path):
    rng = np.random.default_rng(5)
    registry = {}
    for name in ("alpha", "beta"):
        rows = 400
        signal = rng.normal(size=rows)
        frame = pd.DataFrame(
            {
                "target": (signal + rng.normal(size=rows) * 0.3 > 0).astype(int),
                "signal": signal,
                "noise": rng.normal(size=rows),
                "kind": rng.integers(0, 3, rows),
            }
        )
        registry[name] = {"file": _write_frame(frame, tmp_path / f"{name}.csv"), "target": "target"}
    return registry


def _run(d2, tmp_path, registry, **kwargs):
    families = kwargs.pop("families", {"glm": signed_sum_builder, "lgbm": signed_sum_builder})
    return d2.main(
        ["--all-anchors", "--control-dataset", "alpha", "--run-id", "R1",
         "--subsample", "200", "--test-rows", "50", "--repeats", "2"],
        root=tmp_path / "records",
        datasets=registry,
        families=families,
        **kwargs,
    )


def test_one_record_per_dataset_carries_the_cap_and_the_readings(d2, tmp_path, two_datasets):
    assert _run(d2, tmp_path, two_datasets) == 0

    record = read_diagnostic_record(tmp_path / "records" / "d2_importance" / "R1-alpha")

    assert list(record) == list(DIAGNOSTIC_RECORD_FIELDS)
    assert record["dataset_name"] == "alpha"
    assert record["seed"] == 42
    # Injected families are a test seam: the record must not borrow a model label for a
    # TabPFN this process never loaded.
    assert record["model_version"] == "injected-families"
    assert record["matched_context"]["checked"] is False

    m = record["measurements"]
    assert m["subsample"]["cap_rows"] == 200
    assert m["subsample"]["rows_sampled"] == 200
    assert m["subsample"]["train_rows"] + m["subsample"]["test_rows"] == 200
    assert "approximation" in m["subsample"]["note"]
    assert set(m["families"]) == {"glm", "lgbm"}
    assert m["families"]["glm"]["top_k"][0] == "signal"
    assert set(m["readings"]) == {
        "same_features_ranked_differently",
        "different_features",
        "interaction_only",
    }
    # The cap is stated in one place; the readings are answerable from the record alone.
    assert m["readings"]["different_features"][0]["jaccard_top_k"] is not None
    assert m["importance"]["metric"] == "drop in ROC AUC"
    assert any("subsample" in line for line in m["limitations"])

    # One record per dataset, each named for it.
    written = sorted(path.name for path in (tmp_path / "records" / "d2_importance").iterdir())
    assert written == ["R1-alpha", "R1-beta"]


def test_the_control_runs_on_exactly_one_dataset(d2, tmp_path, two_datasets):
    assert _run(d2, tmp_path, two_datasets) == 0

    alpha = read_diagnostic_record(tmp_path / "records" / "d2_importance" / "R1-alpha")
    beta = read_diagnostic_record(tmp_path / "records" / "d2_importance" / "R1-beta")

    assert alpha["measurements"]["control"] is not None
    assert beta["measurements"]["control"] is None


def test_the_control_dataset_is_named_and_recorded(d2, tmp_path, two_datasets):
    assert d2.main(
        ["--dataset", "alpha", "--dataset", "beta", "--control-dataset", "beta", "--run-id", "R2",
         "--subsample", "200", "--test-rows", "50", "--repeats", "2"],
        root=tmp_path / "records",
        datasets=two_datasets,
        families={"glm": signed_sum_builder},
    ) == 0

    alpha = read_diagnostic_record(tmp_path / "records" / "d2_importance" / "R2-alpha")
    beta = read_diagnostic_record(tmp_path / "records" / "d2_importance" / "R2-beta")

    assert alpha["measurements"]["control"] is None
    control = beta["measurements"]["control"]
    assert control["passed"] is True
    assert control["permuted_test_auc"]["glm"] == pytest.approx(0.5, abs=0.15)


def test_a_control_dataset_outside_the_run_is_refused(d2, tmp_path, two_datasets):
    with pytest.raises(SystemExit, match="not among the datasets run"):
        d2.main(
            ["--dataset", "alpha", "--control-dataset", "beta"],
            root=tmp_path / "records",
            datasets=two_datasets,
            families={"glm": signed_sum_builder},
        )


def test_a_failing_control_still_writes_its_record_and_exits_non_zero(d2, tmp_path, two_datasets, monkeypatch):
    """The policy that differs from D3: the failure *is* the evidence, so it is not discarded."""
    monkeypatch.setattr(
        d2, "control_block", lambda *a, **k: {"passed": False, "rule": "forced", "families": [], "k": 2}
    )

    assert d2.main(
        ["--dataset", "alpha", "--control-dataset", "alpha", "--run-id", "R3",
         "--subsample", "200", "--test-rows", "50", "--repeats", "2"],
        root=tmp_path / "records",
        datasets=two_datasets,
        families={"glm": signed_sum_builder},
    ) == 1

    record = read_diagnostic_record(tmp_path / "records" / "d2_importance" / "R3-alpha")
    assert record["measurements"]["control"]["passed"] is False


def test_the_cli_cannot_name_a_location(tmp_path, two_datasets, d2):
    """#211: records land under outputs/diagnostics/, not wherever a flag points."""
    for flag in ("--out", "--root"):
        with pytest.raises(SystemExit):
            d2.main(["--dataset", "alpha", flag, str(tmp_path)], datasets=two_datasets)

    assert d2.DIAGNOSTICS_ROOT == REPO_ROOT / "outputs" / "diagnostics"


def test_batching_is_throughput_not_method(d2):
    """One prediction call for several permuted copies must give the unbatched answer.

    The batch size exists to make a CPU-only run finish; if it changed a number, the record's
    `predict_batch` field would be a methodological choice masquerading as a speed knob.
    """
    frame = _signal_frame(rows=300)
    X = frame[["signal", "noise"]].to_numpy()
    y = frame["target"].to_numpy()
    predict = d2.positive_probability(SignedSumModel(column=0).fit(X, y))

    one_at_a_time = d2.permutation_importance(predict, X, y, n_repeats=2, seed=5, batch=1)[1]
    batched = d2.permutation_importance(predict, X, y, n_repeats=2, seed=5, batch=4)[1]

    np.testing.assert_allclose(one_at_a_time, batched)


def test_the_recorded_tabpfn_version_is_the_one_the_package_resolves(d2, monkeypatch):
    """`auto` must not be reported as v2 when the package loads v2.5.

    The library normalises `"auto"` to `None` before resolving, and the two spellings answer
    differently. Recording the wrong one would put a version in the record that no checkpoint
    matched -- the failure `docs/MODEL_VERSIONS.md` exists to prevent.
    """
    pytest.importorskip("tabpfn")
    import model_version
    from tabpfn.settings import settings

    monkeypatch.delenv("TABPFN_MODEL_PATH", raising=False)
    monkeypatch.setattr(model_version, "explicit_model_path", lambda: None)

    info = d2.tabpfn_provenance(n_estimators=1)

    assert info["requested_model_path"] == "auto"
    assert info["resolved_version"] == settings.tabpfn.model_version.value
    if info["resolved_version"] == "v2.5":
        assert "v2.5" in info["checkpoint"]


class CoinFlipModel:
    """A fitted classifier that has learned nothing -- the shape `at_chance` exists to name."""

    def fit(self, X, y):  # noqa: ARG002 - sklearn-shaped
        return self

    def predict_proba(self, X):
        probability = np.full(len(X), 0.5)
        return np.column_stack([1.0 - probability, probability])


def test_a_family_with_no_signal_says_so_in_the_record(d2, tmp_path, two_datasets):
    """A ranking of noise is still a ranking; the record must not let it pass for a reading."""
    def build(X, y):
        return CoinFlipModel().fit(X, y)

    assert d2.main(
        ["--dataset", "alpha", "--no-control", "--run-id", "R4",
         "--subsample", "200", "--test-rows", "50", "--repeats", "2"],
        root=tmp_path / "records",
        datasets=two_datasets,
        families={"glm": build},
    ) == 0

    m = read_diagnostic_record(tmp_path / "records" / "d2_importance" / "R4-alpha")["measurements"]
    assert m["families"]["glm"]["no_better_than_chance"] is True
    assert any("at chance" in line and "glm" in line for line in m["limitations"])


def test_a_skipped_control_is_recorded_as_skipped(d2, tmp_path, two_datasets):
    """`--no-control` must not read like a dataset the control simply did not cover."""
    assert d2.main(
        ["--dataset", "alpha", "--no-control", "--run-id", "R5",
         "--subsample", "200", "--test-rows", "50", "--repeats", "2"],
        root=tmp_path / "records",
        datasets=two_datasets,
        families={"glm": signed_sum_builder},
    ) == 0

    m = read_diagnostic_record(tmp_path / "records" / "d2_importance" / "R5-alpha")["measurements"]
    assert m["control"] is None
    assert any("--no-control" in line and "wrongness check" in line for line in m["limitations"])
