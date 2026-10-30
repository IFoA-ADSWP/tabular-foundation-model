"""The pilot takes its experiment from the registry (#238).

`resolve_invocation` is the seam: a parsed command line in, the values the run will use
out, or a refusal naming the experiment and the flag that contradicts it. Nothing here
fits a model, so a wrong refusal costs milliseconds rather than a paid minute.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_pilot.py"


def _load():
    spec = importlib.util.spec_from_file_location("run_pilot_for_cli_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mod = _load()


def resolve(*argv):
    return mod.resolve_invocation(mod.make_parser().parse_args(list(argv)))


# ---- without an id: exactly the pre-#238 behaviour ---------------------------

def test_without_an_experiment_the_module_defaults_are_unchanged():
    dataset, arms, seeds, train_size, test_size, folds, config, budgets, experiment_id, declared, version = resolve()

    assert dataset is None  # every dataset
    assert arms == list(mod.ARMS)
    assert seeds == [mod.DEFAULT_SEED]
    assert (train_size, test_size) == (mod.TRAIN_SIZE, mod.TEST_SIZE)
    assert folds is None
    assert config == mod.DEFAULT_CONFIG
    assert budgets is None  # no declaration, so the module's ladder table stands
    assert experiment_id is None and declared is None and version is None


def test_without_an_experiment_flags_still_override_the_defaults():
    _dataset, _arms, seeds, train_size, test_size, folds, config, _budgets, experiment_id, declared, _version = resolve(
        "--seeds", "42,43", "--rung", "P1b", "--folds", "5",
        "--epochs", "10", "--learning-rate", "1e-4", "--n-estimators", "4",
    )

    assert seeds == [42, 43]
    assert (train_size, test_size) == (5000, 2000)  # P1b
    assert folds == 5
    assert (config["epochs"], config["learning_rate"], config["n_estimators"]) == (10, 1e-4, 4)
    assert config["fit_mode"] == mod.DEFAULT_CONFIG["fit_mode"]


def test_without_an_experiment_an_unknown_arm_is_refused():
    with pytest.raises(mod.InvocationError, match="unknown arm"):
        resolve("--arms", "A_raw,nope")


# ---- with an id: the registry owns the values -------------------------------

def test_an_experiment_supplies_every_value_without_a_flag():
    dataset, arms, seeds, train_size, test_size, folds, config, budgets, experiment_id, declared, version = resolve(
        "--experiment", "coil2000_p1a")

    assert dataset == "coil2000"
    assert arms == ["A_raw", "B_in_domain", "E_glm", "F_catboost"]
    assert seeds == [42]
    assert (train_size, test_size) == (2000, 1000)
    assert folds is None
    assert config["epochs"] == 3
    assert config["context_samples"] == 64
    # the declaration owns the arm budgets; the module's ladder table is not consulted
    assert budgets == {"A_raw": 3, "B_in_domain": 3, "E_glm": 3, "F_catboost": 3}
    assert experiment_id == "coil2000_p1a"
    assert declared == config  # the run refuses a contradiction, so these agree today
    assert version == "v3_default"


def test_a_flag_that_repeats_the_declaration_is_accepted():
    _dataset, _arms, seeds, train_size, test_size, _folds, config, _budgets, experiment_id, declared, _version = resolve(
        "--experiment", "coil2000_p1a", "--seeds", "42", "--epochs", "3",
        "--train-size", "2000", "--test-size", "1000", "--rung", "P1a",
        "--dataset", "coil2000", "--arms", "A_raw,B_in_domain,E_glm,F_catboost",
    )

    assert seeds == [42]
    assert (train_size, test_size) == (2000, 1000)
    assert config["epochs"] == 3


@pytest.mark.parametrize("argv, flag", [
    (["--epochs", "10"], "--epochs"),
    (["--learning-rate", "1e-4"], "--learning-rate"),
    (["--n-estimators", "4"], "--n-estimators"),
    (["--seeds", "43"], "--seeds"),
    (["--folds", "5"], "--folds"),
    (["--train-size", "5000"], "--train-size"),
    (["--test-size", "2000"], "--test-size"),
    (["--rung", "P1b"], "--rung"),
    (["--dataset", "uslapseagent"], "--dataset"),
])
def test_a_contradicting_flag_is_refused_naming_the_id_and_the_flag(argv, flag):
    with pytest.raises(mod.InvocationError) as raised:
        resolve("--experiment", "coil2000_p1a", *argv)

    message = str(raised.value)
    assert "coil2000_p1a" in message
    assert flag in message


def test_arms_select_within_the_declaration():
    # The launcher runs one arm per process, so a subset is a selection, not a
    # contradiction; an arm the declaration does not name is refused.
    _dataset, arms, _seeds, _t, _te, _f, _c, _b, _id, _d, _v = resolve(
        "--experiment", "coil2000_p1a", "--arms", "E_glm")
    assert arms == ["E_glm"]

    with pytest.raises(mod.InvocationError) as raised:
        resolve("--experiment", "coil2000_p1a", "--arms", "B_ft30")
    assert "coil2000_p1a" in str(raised.value) and "--arms" in str(raised.value)


def test_an_unknown_experiment_id_names_it_and_lists_the_known_ones():
    from experiment_spec import RegistryError

    with pytest.raises(RegistryError) as raised:
        resolve("--experiment", "nope")

    assert "unknown pilot experiment 'nope'" in str(raised.value)
    assert "coil2000_p1a" in str(raised.value)


def test_the_declared_budgets_replace_the_module_ladder_table(monkeypatch):
    # With an experiment, the registry owns the ladder; without one, the table is the
    # fallback that keeps every pre-#238 invocation identical.
    monkeypatch.setattr(mod, "ARM_BUDGETS", {"B_ft10": 7})
    assert mod.arm_epochs("B_ft10", {"epochs": 3}) == 7

    monkeypatch.setattr(mod, "ARM_BUDGETS", None)
    assert mod.arm_epochs("B_ft10", {"epochs": 3}) == 10  # ARM_EPOCH_OVERRIDES
    assert mod.arm_epochs("A_raw", {"epochs": 3}) == 3


def test_resolved_config_applies_the_arms_own_budget(monkeypatch):
    # The pair is only a drift detector if `resolved` is what the arm runs. A ladder arm
    # under a 3-epoch base executes 30, and the record must say 30 (ADR 0004).
    base = {"epochs": 3, "learning_rate": 1e-5}
    monkeypatch.setattr(mod, "ARM_BUDGETS", {"B_ft30": 30})

    assert mod.resolved_config("B_ft30", base)["epochs"] == 30
    assert mod.resolved_config("A_raw", base)["epochs"] == 3
    assert base["epochs"] == 3  # the caller's config is not mutated
