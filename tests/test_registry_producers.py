"""Registry adoption by the remaining producers and analysis scripts (#235).

The proof is metadata equivalence: every migrated script must select the same datasets,
with the same file/target/drop/metric/transform, as the private lists it used to keep.
No model is fitted here.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from src.experiment_spec import (
    CLASSIFICATION,
    REGRESSION,
    dataset_entry,
    datasets_by_mode,
    load_registry,
    mode_methods,
)

ROOT = Path(__file__).resolve().parents[1]
CLASSIFICATION_ORDER = [
    "bemtl97", "coil2000", "uslapseagent", "norauto", "ausprivauto0405", "bemtl16",
]
REGRESSION_ORDER = [
    "ausautoBI8999", "ausprivauto0405_vehvalue", "bemtl97_amount",
    "freMTPL2freq", "spanish_motor_freq", "spanish_motor_severity",
]
CLASSIFICATION_METHODS = [
    "cat", "lgbm", "xgb", "lr", "logisticglm", "tweedieglm", "poissonglm", "rf", "tabpfn",
]
REGRESSION_METHODS = ["ols", "poissonglm", "tweedieglm", "rf", "cat", "lgbm", "xgb", "tabpfn"]
EVAL = ROOT / "scripts/eval/insurance_benchmark_v1"
TOML = EVAL / "experiments.toml"

# The values the scripts kept privately before #235. This is the pin: if a registry edit
# changes a target, a drop or a metric, a committed result is no longer the same result.
EXPECTED = {
    "bemtl97": ("bemtl97.csv", "claim", ("nclaims", "amount"), "log_loss", None),
    "coil2000": ("coil2000.csv", "CARAVAN", (), "log_loss", None),
    "uslapseagent": ("uslapseagent.csv", "surrender", (), "log_loss", None),
    "norauto": ("norauto.csv", "NbClaim", (), "log_loss", None),
    "ausprivauto0405": ("ausprivauto0405.csv", "ClaimOcc", (), "log_loss", None),
    "bemtl16": ("bemtl16.csv", "number_of_liability_claims", (), "log_loss", None),
    "ausautoBI8999": ("ausautoBI8999.csv", "AggClaim", (), "rmse", None),
    "ausprivauto0405_vehvalue": ("ausprivauto0405.csv", "VehValue", (), "rmse", None),
    "bemtl97_amount": ("bemtl97.csv", "amount", ("claim",), "rmse", None),
    "freMTPL2freq": ("freMTPL2freq.csv", "ClaimNb", ("IDpol",),
                     "poisson_deviance", "log_exposure"),
    "spanish_motor_freq": ("spanish_motor_freq.csv", "N_claims_year", (),
                           "poisson_deviance", None),
    "spanish_motor_severity": ("spanish_motor_severity.csv", "Cost_claims_year", (),
                               "rmse", None),
}


def _load(path: Path, name: str):
    sys.path.insert(0, str(path.parent))
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def test_the_registry_holds_the_metadata_the_scripts_used():
    registry = load_registry(TOML)

    assert set(registry.datasets) == set(EXPECTED)
    for name, (file, target, drop, metric, transform) in EXPECTED.items():
        dataset = registry.datasets[name]
        assert dataset.file == file, name
        assert dataset.target == target, name
        assert dataset.drop == drop, name
        assert dataset.metric == metric, name
        assert dataset.transform == transform, name


def test_datasets_by_mode_is_ordered_and_dataset_entry_carries_the_values():
    registry = load_registry(TOML)
    classification = datasets_by_mode(registry, CLASSIFICATION)
    regression = datasets_by_mode(registry, REGRESSION)

    assert [d.name for d in classification] == CLASSIFICATION_ORDER
    assert [d.name for d in regression] == REGRESSION_ORDER
    entry = dataset_entry(registry.datasets["freMTPL2freq"])
    assert entry == {
        "name": "freMTPL2freq", "file": "freMTPL2freq.csv", "target": "ClaimNb",
        "drop": ["IDpol"], "metric": "poisson_deviance", "transform": "log_exposure",
    }


def test_every_dataset_has_one_experiment_and_one_method_list_per_mode():
    registry = load_registry(TOML)

    assert set(registry.experiments) == set(registry.datasets)
    for name, experiment in registry.experiments.items():
        assert experiment.dataset == name
        assert (experiment.n_folds, experiment.seed) == (5, 42)
    assert [m.name for m in mode_methods(registry, CLASSIFICATION)] == CLASSIFICATION_METHODS
    assert [m.name for m in mode_methods(registry, REGRESSION)] == REGRESSION_METHODS


def test_the_producers_select_the_registry_dataset_sets():
    registry = load_registry(TOML)

    tuned = _load(EVAL / "run_tuned_baselines.py", "producer_tuned_235")
    tabfm = _load(EVAL / "run_tabfm.py", "producer_tabfm_235")
    sweep = _load(ROOT / "scripts/benchmarks/run_home_turf_size_sweep.py",
                  "producer_sweep_235")

    assert [d["name"] for d in tuned.classification_datasets()] == CLASSIFICATION_ORDER
    assert [d["name"] for d in tabfm.classification_datasets()] == CLASSIFICATION_ORDER
    sweep_names = [d["name"] for d in sweep.sweep_datasets()]
    assert sweep_names == ["coil2000", "uslapseagent", "bemtl97"]
    for entry in sweep.sweep_datasets():
        declared = registry.datasets[entry["name"]]
        assert (entry["file"], entry["target"], entry["drop"]) == (
            declared.file, declared.target, list(declared.drop)
        )


def test_the_analysis_and_rescore_scripts_read_the_registry():
    pr_auc = _load(EVAL / "analyze_pr_auc.py", "analyze_pr_auc_235")
    tuned = _load(EVAL / "analyze_tuned_baselines.py", "analyze_tuned_235")
    plot = _load(EVAL / "plot_money_chart.py", "plot_money_235")
    rescore = _load(EVAL / "rescore_altmetrics.py", "rescore_235")
    reframe = _load(EVAL / "run_reframe_frequency.py", "reframe_235")

    assert pr_auc.DATASETS == CLASSIFICATION_ORDER
    assert tuned.DATASETS == CLASSIFICATION_ORDER
    assert pr_auc.METHODS == CLASSIFICATION_METHODS
    assert tuned.CANON_METHODS == CLASSIFICATION_METHODS
    assert reframe.BINARY_METHODS == CLASSIFICATION_METHODS
    # the plotted set is the committed chart's set; the files come from the registry
    assert plot.DATASETS == {name: file for name, (file, *_rest) in EXPECTED.items()}
    assert set(rescore.REG_ALT_CONFIG) == set(REGRESSION_ORDER)
    assert rescore.METHODS == REGRESSION_METHODS
