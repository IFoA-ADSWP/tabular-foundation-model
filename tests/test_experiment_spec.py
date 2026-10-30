"""Registry loader tests (issue #230).

`load_registry` is the seam: a path in, frozen dataclasses out. Everything here goes
through that boundary, so the tests survive any reshaping of the parsing internals.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.experiment_spec import Registry, RegistryError, load_registry

MINIMAL = """
schema_version = 1

[datasets.toy]
file = "toy.csv"
target = "y"
drop = []
metric = "log_loss"

[methods.classification.lr]
n_params = "glm"

[experiments.toy]
dataset = "toy"
methods = ["lr"]
n_folds = 5
seed = 42
model_version = "v3_default"
"""


def write(tmp_path, text: str, name: str = "experiments.toml"):
    path = tmp_path / name
    path.write_text(text)
    return path


def broken(tmp_path, old: str, new: str):
    """MINIMAL with one substring replaced — the smallest edit that makes it not a registry."""
    assert old in MINIMAL, f"fixture has no {old!r} to replace"
    return write(tmp_path, MINIMAL.replace(old, new, 1))


# ---- schema and shape -------------------------------------------------------

def test_a_valid_registry_loads_into_frozen_dataclasses(tmp_path):
    registry = load_registry(write(tmp_path, MINIMAL))

    assert isinstance(registry, Registry)
    assert registry.schema_version == 1

    dataset = registry.datasets["toy"]
    assert (dataset.name, dataset.file, dataset.target) == ("toy", "toy.csv", "y")
    assert dataset.drop == ()

    experiment = registry.experiment("toy")
    assert experiment.methods == ("lr",)
    assert (experiment.n_folds, experiment.seed) == (5, 42)
    assert experiment.model_version == "v3_default"
    # the metric is a property of the dataset (GLOSSARY.md), not declared twice
    assert experiment.metric == "log_loss"

    with pytest.raises(Exception):
        experiment.seed = 7  # frozen: an experiment cannot be edited after load


@pytest.mark.parametrize(
    "old, new, names",
    [
        # an unrecognised schema version is refused, not guessed at
        ("schema_version = 1", "schema_version = 2", "2"),
        ("schema_version = 1\n", "", "schema_version"),
        # unknown keys are refused at every level
        ("schema_version = 1", "schema_version = 1\nsurprise = true", "surprise"),
        ('metric = "log_loss"', 'metric = "log_loss"\nmetrik = "rmse"', "metrik"),
        ('methods = ["lr"]', 'methods = ["lr"]\ntolerance = 0.1', "tolerance"),
        # the metric is the dataset's, so an experiment cannot restate it
        ('methods = ["lr"]', 'methods = ["lr"]\nmetric = "rmse"', "metric"),
    ],
)
def test_malformed_shape_is_refused_and_names_the_offender(tmp_path, old, new, names):
    with pytest.raises(RegistryError, match=names):
        load_registry(broken(tmp_path, old, new))


@pytest.mark.parametrize("field", ['file = "toy.csv"', 'target = "y"', 'metric = "log_loss"'])
def test_a_dataset_missing_a_required_field_is_refused(tmp_path, field):
    path = broken(tmp_path, field + "\n", "")
    with pytest.raises(RegistryError, match=r"datasets\.toy.*missing"):
        load_registry(path)


@pytest.mark.parametrize(
    "field", ["n_folds = 5", "seed = 42", 'model_version = "v3_default"', 'methods = ["lr"]']
)
def test_an_experiment_missing_a_required_field_is_refused(tmp_path, field):
    path = broken(tmp_path, field + "\n", "")
    with pytest.raises(RegistryError, match=r"experiments\.toy.*missing"):
        load_registry(path)


@pytest.mark.parametrize(
    "old, new, names",
    [
        ('seed = 42', 'seed = "42"', "seed"),
        ("n_folds = 5", "n_folds = 1", "n_folds"),
        ("n_folds = 5", "n_folds = true", "n_folds"),
        ("seed = 42", "seed = -1", "seed"),
        ('model_version = "v3_default"', 'model_version = ""', "model_version"),
        ('metric = "log_loss"', 'metric = "auc"', "auc"),
        ('n_params = "glm"', 'n_params = "magic"', "magic"),
    ],
)
def test_an_entry_with_a_bad_value_is_refused_and_names_it(tmp_path, old, new, names):
    with pytest.raises(RegistryError, match=names):
        load_registry(broken(tmp_path, old, new))


# ---- references -------------------------------------------------------------

def test_a_reference_to_a_dataset_that_does_not_exist_is_refused(tmp_path):
    path = broken(tmp_path, 'dataset = "toy"', 'dataset = "coil2000"')
    with pytest.raises(RegistryError, match=r"experiments\.toy.*unknown dataset 'coil2000'"):
        load_registry(path)


def test_a_reference_to_a_method_that_does_not_exist_is_refused(tmp_path):
    path = broken(tmp_path, 'methods = ["lr"]', 'methods = ["lr", "tabpfn"]')
    with pytest.raises(
        RegistryError, match=r"experiments\.toy.*unknown classification method 'tabpfn'"
    ):
        load_registry(path)


def test_a_method_from_the_other_mode_is_not_silently_substituted(tmp_path):
    # poissonglm exists, but as a regression method. An experiment with a log_loss
    # dataset must not pick it up: the mode decides the namespace.
    text = MINIMAL.replace(
        '[methods.classification.lr]', "[methods.regression.lr]"
    )
    with pytest.raises(RegistryError, match=r"unknown classification method 'lr'"):
        load_registry(write(tmp_path, text))


def test_a_duplicate_id_is_refused_and_names_the_entry(tmp_path):
    path = write(tmp_path, MINIMAL + "\n[experiments.toy]\ndataset = \"toy\"\n")
    with pytest.raises(RegistryError, match="toy"):
        load_registry(path)


@pytest.mark.parametrize("section", ["datasets", "methods", "experiments"])
def test_a_section_of_the_wrong_type_is_refused_not_crashed_on(tmp_path, section):
    # A section that is not a table declares nothing; refusing it beats an AttributeError.
    text = f"schema_version = 1\n{section} = 3\n"
    with pytest.raises(RegistryError, match=section):
        load_registry(write(tmp_path, text))


def test_a_boolean_is_not_a_schema_version(tmp_path):
    # `true == 1` in Python; a registry that says `schema_version = true` has not
    # declared version 1, and must not be read as if it had.
    with pytest.raises(RegistryError, match="schema_version"):
        load_registry(broken(tmp_path, "schema_version = 1", "schema_version = true"))


def test_looking_up_an_unregistered_experiment_names_it_and_lists_the_known_ones(tmp_path):
    registry = load_registry(write(tmp_path, MINIMAL))
    with pytest.raises(RegistryError, match=r"unknown experiment 'nope'.*toy"):
        registry.experiment("nope")


def test_the_experiments_methods_resolve_in_its_own_mode_in_declared_order(tmp_path):
    text = MINIMAL.replace(
        'methods = ["lr"]', 'methods = ["rf", "lr"]'
    ).replace(
        '[methods.classification.lr]',
        '[methods.classification.rf]\nn_params = "trees"\n\n[methods.classification.lr]',
    )
    registry = load_registry(write(tmp_path, text))
    experiment = registry.experiment("toy")

    assert [m.name for m in registry.methods_of(experiment)] == ["rf", "lr"]
    assert registry.methods_of(experiment)[0].n_params == "trees"
    assert registry.dataset_of(experiment).name == "toy"


# ---- the committed file vs the code it was generated from --------------------
#
# DATASETS is deprecated for the classification frontier (#231 reads the registry) but
# run_tuned_baselines still imports it until #235; REG_DATASETS serves regression until
# #232/#235. This test keeps the committed file and those remaining code lists from
# drifting apart.

REGISTRY = (
    Path(__file__).resolve().parents[1]
    / "scripts/eval/insurance_benchmark_v1/experiments.toml"
)

# The regression loop's order is the literal in run_dataset_regression; classification is
# taken from the runner's own method constants inside the test.
REGRESSION_ORDER = ("ols", "poissonglm", "tweedieglm", "rf", "cat", "lgbm", "xgb", "tabpfn")

# The D2 counting rule per method (spec §5): everything unlisted is counted from the
# fitted trees.
N_PARAMS_BY_METHOD = {
    "classification": {"lr": "glm", "logisticglm": "glm", "tweedieglm": "glm",
                       "poissonglm": "glm", "tabpfn": "tabpfn"},
    "regression": {"ols": "glm", "poissonglm": "glm", "tweedieglm": "glm",
                   "tabpfn": "tabpfn"},
}


def _runner():
    import importlib.util

    script = REGISTRY.parent / "run_frontier_benchmark.py"
    spec = importlib.util.spec_from_file_location("runner_for_registry_test", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_committed_registry_covers_the_remaining_code_dataset_lists():
    runner = _runner()
    registry = load_registry(REGISTRY)

    expected = {d["name"]: d for d in runner.DATASETS + runner.REG_DATASETS}
    assert set(registry.datasets) == set(expected)

    for name, declared in expected.items():
        dataset = registry.datasets[name]
        assert dataset.file == declared["file"], name
        assert dataset.target == declared["target"], name
        assert dataset.drop == tuple(declared["drop"]), name
        assert dataset.metric == declared.get("metric", "log_loss"), name
        assert dataset.transform == declared.get("transform"), name

    # every dataset has exactly one experiment, at the runner's fold count and seed
    assert set(registry.experiments) == set(expected)
    for name, experiment in registry.experiments.items():
        assert experiment.dataset == name
        assert experiment.n_folds == runner.N_FOLDS
        assert experiment.seed == runner.SEED

    # the runner compares the same method list for every dataset in a mode, so the
    # registry must too — checking only one experiment per mode would let the other ten
    # drift silently
    for mode in ("classification", "regression"):
        lists = {experiment.methods for experiment in registry.experiments.values()
                 if experiment.mode == mode}
        assert len(lists) == 1, f"{mode} experiments disagree about which methods: {lists}"


def test_the_committed_registry_declares_every_method_in_runner_order():
    runner = _runner()
    registry = load_registry(REGISTRY)

    classification = registry.experiment("coil2000")
    compared = [m.name for m in registry.methods_of(classification)]
    # Every method the runner compares is declared — derived from its own constants, so
    # drift in REUSED_METHODS or FAST_METHODS fails here rather than passing silently.
    assert set(compared) == set(runner.CLASSIFICATION_METHODS)
    assert compared[-1] == "tabpfn"  # the hosted method is always deferred to last

    regression = registry.experiment("freMTPL2freq")
    assert tuple(m.name for m in registry.methods_of(regression)) == REGRESSION_ORDER

    for mode, experiment in (("classification", classification), ("regression", regression)):
        for method in registry.methods_of(experiment):
            expected = N_PARAMS_BY_METHOD[mode].get(method.name, "trees")
            assert method.n_params == expected, (mode, method.name)

    # the model version is a literal, pinned per experiment, never inferred
    from src.model_version import BASELINE_MODEL_PATH

    assert {e.model_version for e in registry.experiments.values()} == {BASELINE_MODEL_PATH}





# ---- shared fold constructor (#231) -----------------------------------------

def test_make_folds_is_reproducible_for_the_same_kind_count_and_seed():
    import numpy as np

    from src.experiment_spec import make_folds

    X = np.zeros((120, 3))
    y = np.array([0, 1] * 60)
    first = list(make_folds("stratified", 5, 42).split(X, y))
    second = list(make_folds("stratified", 5, 42).split(X, y))

    assert len(first) == len(second) == 5
    for (tr_a, te_a), (tr_b, te_b) in zip(first, second):
        assert np.array_equal(tr_a, tr_b)
        assert np.array_equal(te_a, te_b)


def test_make_folds_changes_the_split_when_the_seed_changes():
    import numpy as np

    from src.experiment_spec import make_folds

    X = np.zeros((120, 3))
    y = np.array([0, 1] * 60)
    first = list(make_folds("stratified", 5, 42).split(X, y))
    second = list(make_folds("stratified", 5, 7).split(X, y))

    assert any(not np.array_equal(a[1], b[1]) for a, b in zip(first, second))


def test_make_folds_refuses_an_unknown_kind_and_names_it():
    from src.experiment_spec import RegistryError, make_folds

    with pytest.raises(RegistryError, match=r"unknown fold kind 'nope'"):
        make_folds("nope", 5, 42)
