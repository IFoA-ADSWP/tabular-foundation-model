"""Frontier registry adoption tests (issue #231).

The seam under test is the planner, not a model fit: which methods, folds and metric a
loaded experiment hands to the runner. The reproduction proof is the coil2000 run recorded
in `docs/plans/frontier-registry-adoption.md`; these tests keep the wiring honest without
fitting a dataset.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from src.experiment_spec import CLASSIFICATION, RegistryError, load_registry

ROOT = Path(__file__).resolve().parents[1]
TOML = ROOT / "scripts/eval/insurance_benchmark_v1/experiments.toml"


def _load_runner():
    script = ROOT / "scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py"
    spec = importlib.util.spec_from_file_location("runner_for_231_test", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mod = _load_runner()


def test_every_classification_method_in_the_file_has_a_code_constructor():
    registry = load_registry(TOML)
    compared = set()
    for experiment in registry.experiments.values():
        if experiment.mode != CLASSIFICATION:
            continue
        for method in registry.methods_of(experiment):
            compared.add(method.name)
            assert method.name in mod.CLASSIFICATION_METHODS, (
                f"{method.name} is declared in experiments.toml but the code registry "
                f"does not build it"
            )
            # the file owns the counting rule; the code table must agree
            assert mod.CLASSIFICATION_METHODS[method.name].n_params == method.n_params

    assert compared == set(mod.CLASSIFICATION_METHODS)


def test_the_experiment_method_list_decides_the_plan_without_a_code_edit():
    full = mod.planned_classification_methods(None)
    subset = mod.planned_classification_methods(("tabpfn", "lr"))

    assert subset == ["lr", "tabpfn"]  # hosted method deferred to last
    assert set(full) - set(subset)  # narrowing the file narrows the comparison


def test_an_unknown_method_is_refused_and_named():
    with pytest.raises(RegistryError, match="'nope'"):
        mod.planned_classification_methods(("lr", "nope"))


def test_experiment_selection_refuses_a_method_the_code_cannot_build(monkeypatch):
    monkeypatch.delitem(mod.CLASSIFICATION_METHODS, "lr")

    with pytest.raises(RegistryError, match="'lr'"):
        mod.experiment_selection("coil2000")


def test_an_unknown_metric_is_refused_and_named():
    with pytest.raises(ValueError, match="'nope'"):
        mod.metric_fn({"metric": "nope"})


def test_an_absent_metric_still_defaults_for_ad_hoc_data():
    # --data has no experiment, so no metric is declared; that path keeps log loss.
    metric = mod.metric_fn({})
    value = metric(np.array([0, 1, 0, 1]), np.array([0.2, 0.8, 0.3, 0.7]))
    assert np.isfinite(value)


def test_default_classification_datasets_come_from_the_registry():
    args = mod.make_parser().parse_args([])
    datasets, wanted = mod.select_datasets(args)

    registry = load_registry(TOML)
    expected = [experiment.dataset for experiment in registry.experiments.values()
                if experiment.mode == CLASSIFICATION]
    assert wanted is None
    assert [ds["name"] for ds in datasets] == expected
