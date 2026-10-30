"""CLI entrypoint tests for scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py
(issue #46: generic --data/--target/--drop, plus legacy filter/--regression usage).

The module imports only numpy/pandas at top level (tabpfn_client is imported lazily
inside the runner functions), so a plain importlib load is offline-safe.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("run_frontier_benchmark_cli_test", _SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load_module()


def parse(argv):
    return mod.make_parser().parse_args(argv)


# ---- a. Parsing -------------------------------------------------------------

def test_parse_data_target():
    args = parse(["--data", "X", "--target", "Y"])
    assert args.filters == []
    assert args.data == "X"
    assert args.target == "Y"
    assert not args.regression


def test_parse_out_dir_default_and_flag():
    assert parse([]).out_dir is None
    assert parse(["--out-dir", "results/foo"]).out_dir == "results/foo"
    assert parse(["--out-dir", "legacy"]).out_dir == "legacy"


def test_write_manifest(tmp_path):
    import json
    import argparse
    mod.SEED = 7
    mod.PR_AUC_MODE = False
    mod.write_manifest(tmp_path, argparse.Namespace(out_dir=str(tmp_path)))
    d = json.loads((tmp_path / "manifest.json").read_text())
    assert d["seed"] == 7
    assert len(d["git_sha"]) == 40
    assert d["pr_auc_mode"] is False


def test_parse_data_without_target_errors(monkeypatch):
    # argparse cannot enforce the dependency itself; main() raises via parser.error
    monkeypatch.setattr(sys, "argv", ["prog", "--data", "X"])
    with pytest.raises(SystemExit):
        mod.main()


def test_parse_save_predictions_flag():
    assert parse([]).save_predictions is False
    assert parse(["--save-predictions"]).save_predictions is True


def test_parse_legacy_filter_regression():
    args = parse(["bemtl97", "--regression"])
    assert args.filters == ["bemtl97"]
    assert args.regression
    assert args.data is None


# ---- e. --experiment (#230) -------------------------------------------------

def test_parse_experiment_flag():
    assert parse([]).experiment is None
    assert parse(["--experiment", "coil2000"]).experiment == "coil2000"


def test_an_experiment_supplies_its_own_dataset_entry():
    datasets, experiment = mod.experiment_selection("coil2000")

    assert experiment.id == "coil2000"
    assert experiment.mode == "classification"
    assert len(datasets) == 1
    ds = datasets[0]
    assert ds["name"] == "coil2000"  # filenames and sweep joins stay keyed to the dataset
    assert ds["file"] == "coil2000.csv"
    assert ds["target"] == "CARAVAN"
    assert ds["drop"] == []
    assert ds["metric"] == "log_loss"


def test_a_regression_experiment_selects_regression_mode_and_its_transform():
    datasets, experiment = mod.experiment_selection("freMTPL2freq")

    assert experiment.mode == "regression"
    ds = datasets[0]
    assert ds["metric"] == "poisson_deviance"
    assert ds["transform"] == "log_exposure"


def test_an_unknown_experiment_names_itself():
    from src.experiment_spec import RegistryError

    with pytest.raises(RegistryError, match="'nope'"):
        mod.experiment_selection("nope")


def refuse_to_run(monkeypatch):
    """Fail loudly if a guard lets main() reach the dataset runner.

    Without this, a guard that stops firing would quietly fit a real dataset for minutes
    and leave a run directory in the repo — which is how the seed-7 run got loose once.
    """
    def boom(*args, **kwargs):
        raise AssertionError("a guard failed: main() reached the dataset runner")

    monkeypatch.setattr(mod, "run_dataset", boom)
    monkeypatch.setattr(mod, "run_dataset_regression", boom)


@pytest.mark.parametrize(
    "argv",
    [
        ["--experiment", "coil2000", "--data", "X", "--target", "Y"],
        ["coil2000", "--experiment", "coil2000"],
        ["--experiment", "coil2000", "--regression"],
    ],
)
def test_an_experiment_refuses_conflicting_selection(monkeypatch, tmp_path, argv):
    refuse_to_run(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["prog", *argv, "--out-dir", str(tmp_path)])
    with pytest.raises(SystemExit):
        mod.main()


def test_the_run_manifest_records_the_experiment_id(tmp_path):
    import argparse
    import json

    mod.SEED, mod.PR_AUC_MODE, mod.EXPERIMENT_ID = 42, False, "coil2000"
    mod.write_manifest(tmp_path, argparse.Namespace(out_dir=str(tmp_path)))
    assert json.loads((tmp_path / "manifest.json").read_text())["experiment_id"] == "coil2000"


def test_the_run_manifest_records_the_model_version_actually_used(tmp_path, monkeypatch):
    # The registry pins a literal; the manifest must say what the run really resolved,
    # or the pin is an unverifiable claim (ADR 0001).
    import argparse
    import json

    monkeypatch.setattr(mod, "_model_path", lambda: "v3.5_default")
    mod.SEED, mod.EXPERIMENT_ID = 42, "coil2000"
    mod.write_manifest(tmp_path, argparse.Namespace(out_dir=str(tmp_path)))
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["model_version"] == "v3.5_default"
    assert manifest["experiment_id"] == "coil2000"
    # and it does not claim more than it can: reused rows are unattested until #233
    assert "reused" in manifest["model_version_scope"] and "#233" in manifest["model_version_scope"]


# ---- declared vs resolved model version (#239) ------------------------------

def _run_manifest(tmp_path, monkeypatch, *, resolved, declared_versions, experiment_id):
    """Write a run manifest with the module globals a run would have set, and read it back."""
    import argparse
    import json

    monkeypatch.setattr(mod, "_model_path", lambda: resolved)
    monkeypatch.setattr(mod, "SEED", 42)
    monkeypatch.setattr(mod, "PR_AUC_MODE", False)
    monkeypatch.setattr(mod, "EXPERIMENT_ID", experiment_id)
    monkeypatch.setattr(mod, "RUN_DECLARED_VERSIONS", declared_versions)
    mod.write_manifest(tmp_path, argparse.Namespace(out_dir=str(tmp_path)))
    return json.loads((tmp_path / "manifest.json").read_text())


def test_the_run_manifest_records_both_versions_when_they_agree(tmp_path, monkeypatch):
    manifest = _run_manifest(tmp_path, monkeypatch, resolved="v3_default",
                             declared_versions=("v3_default",), experiment_id="coil2000")

    assert manifest["model_version_declared"] == "v3_default"
    assert manifest["model_version"] == "v3_default"
    assert manifest["model_version_mismatch"] is False


def test_the_run_manifest_flags_a_mismatch_and_names_both_values(tmp_path, monkeypatch):
    # The exact failure ADR 0001 exists to prevent: the box resolved a different model
    # than the experiment declared. The artifact says so instead of looking consistent.
    manifest = _run_manifest(tmp_path, monkeypatch, resolved="v3.5_default",
                             declared_versions=("v3_default",), experiment_id="coil2000")

    assert manifest["model_version_declared"] == "v3_default"
    assert manifest["model_version"] == "v3.5_default"
    assert manifest["model_version_mismatch"] is True


def test_an_ad_hoc_run_records_an_absent_declaration_not_a_pass(tmp_path, monkeypatch):
    # Absent is not false: no experiment declared a version, so nothing was verified.
    manifest = _run_manifest(tmp_path, monkeypatch, resolved="v3_default",
                             declared_versions=(), experiment_id=None)

    assert manifest["model_version_declared"] is None
    assert "model_version_mismatch" in manifest  # present, so absent ≠ predates-schema
    assert manifest["model_version_mismatch"] is None
    assert manifest["model_version_mismatch"] is not False


def test_a_run_covering_experiments_that_disagree_names_no_single_literal(tmp_path, monkeypatch):
    # No literal is true of the whole run, so none is invented; the flag still answers.
    manifest = _run_manifest(tmp_path, monkeypatch, resolved="v3_default",
                             declared_versions=("v3_default", "v3.5_default"),
                             experiment_id=None)

    assert manifest["model_version_declared"] is None
    assert manifest["model_version_mismatch"] is True


def test_a_sweep_run_records_the_declaration_its_experiments_share(monkeypatch, tmp_path):
    # The default classification run is a sweep of several experiments (#231). It has no
    # single experiment_id, but every declaration it covers is v3_default, so the run can
    # still say what it declared.
    import json

    refuse_to_run(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["prog", "--out-dir", str(tmp_path)])
    with pytest.raises(AssertionError, match="reached the dataset runner"):
        mod.main()

    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["experiment_id"] is None
    assert manifest["model_version_declared"] == "v3_default"
    assert manifest["model_version_mismatch"] is False


def test_a_sweep_run_flags_drift_instead_of_staying_silent(monkeypatch, tmp_path):
    # The most common run must be able to contradict itself; before this, only an
    # --experiment run recorded a declaration at all.
    import json

    monkeypatch.setattr(mod, "_model_path", lambda: "v3.5_default")
    refuse_to_run(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["prog", "--out-dir", str(tmp_path)])
    with pytest.raises(AssertionError, match="reached the dataset runner"):
        mod.main()

    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["model_version_declared"] == "v3_default"
    assert manifest["model_version"] == "v3.5_default"
    assert manifest["model_version_mismatch"] is True


def test_a_filtered_sweep_declares_only_what_it_covers(monkeypatch, tmp_path):
    # A filter that matches nothing runs nothing, so the run declares nothing. This is the
    # absent case at run level, and it must stay None rather than borrowing a registry value.
    import json

    monkeypatch.setattr(sys, "argv",
                        ["prog", "no-such-dataset", "--out-dir", str(tmp_path)])
    mod.main()  # nothing matches, so no runner is reached

    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["model_version_declared"] is None
    assert manifest["model_version_mismatch"] is None


def test_an_experiment_run_wires_its_declared_version_into_the_manifest(monkeypatch, tmp_path):
    # Proves main() sets the global from the registry, not just that write_manifest can
    # record one it is handed.
    import json

    refuse_to_run(monkeypatch)
    monkeypatch.setattr(sys, "argv",
                        ["prog", "--experiment", "coil2000", "--out-dir", str(tmp_path)])
    with pytest.raises(AssertionError, match="reached the dataset runner"):
        mod.main()

    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["experiment_id"] == "coil2000"
    assert manifest["model_version_declared"] == "v3_default"


def test_an_ad_hoc_run_through_main_declares_nothing(monkeypatch, tmp_path):
    import json

    refuse_to_run(monkeypatch)
    monkeypatch.setattr(sys, "argv",
                        ["prog", "--data", "X.csv", "--target", "y", "--out-dir", str(tmp_path)])
    with pytest.raises(AssertionError, match="reached the dataset runner"):
        mod.main()

    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["experiment_id"] is None
    assert manifest["model_version_declared"] is None
    assert manifest["model_version_mismatch"] is None


def test_an_experiment_refuses_a_seed_that_contradicts_its_declaration(monkeypatch, tmp_path):
    # coil2000 is declared at seed 42. Stamping that id on a seed-7 run would make the
    # artifact contradict the declaration it cites — the bug class this ticket exists for.
    refuse_to_run(monkeypatch)
    monkeypatch.setattr(sys, "argv",
                        ["prog", "--experiment", "coil2000", "--seed", "7",
                         "--out-dir", str(tmp_path)])
    with pytest.raises(SystemExit):
        mod.main()


def test_an_experiment_accepts_its_declared_seed(monkeypatch, tmp_path):
    # The guard must not refuse the seed the registry actually declares.
    refuse_to_run(monkeypatch)
    monkeypatch.setattr(sys, "argv",
                        ["prog", "--experiment", "coil2000", "--seed", "42",
                         "--out-dir", str(tmp_path)])
    with pytest.raises(AssertionError, match="reached the dataset runner"):
        mod.main()  # selection and seed both accepted; it stops at the runner stub


def test_an_experiment_passes_its_declared_fold_count_to_the_runner(monkeypatch, tmp_path):
    # #231 folds from the experiment, so a declared count is honoured rather than refused.
    import dataclasses

    datasets, experiment = mod.experiment_selection("coil2000")
    monkeypatch.setattr(mod, "experiment_selection",
                        lambda _id: (datasets, dataclasses.replace(experiment, n_folds=10)))
    seen = {}

    def capture(_ds, _out_csv, _out_png, experiment=None, seed=None, n_folds=None,
                row_size=None):
        seen["folds"] = n_folds
        raise AssertionError("stop after capture")

    monkeypatch.setattr(mod, "run_dataset", capture)
    monkeypatch.setattr(sys, "argv",
                        ["prog", "--experiment", "coil2000", "--out-dir", str(tmp_path)])
    with pytest.raises(AssertionError, match="stop after capture"):
        mod.main()
    assert seen["folds"] == 10


def test_the_all_datasets_path_keeps_the_cli_seed(monkeypatch, tmp_path):
    # `--seed 7` is the documented split-stability run. The dataset now supplies its
    # methods, but the sweep's own seed and filename must still come from the CLI.
    seen = {}

    def capture(_ds, _out_csv, _out_png, experiment=None, seed=None, n_folds=None,
                row_size=None):
        seen.update(seed=seed, folds=n_folds,
                    experiment=experiment.id if experiment else None)
        raise AssertionError("stop after capture")

    monkeypatch.setattr(mod, "run_dataset", capture)
    monkeypatch.setattr(sys, "argv",
                        ["prog", "coil2000", "--seed", "7", "--out-dir", str(tmp_path)])
    with pytest.raises(AssertionError, match="stop after capture"):
        mod.main()
    assert seen == {"seed": 7, "folds": 5, "experiment": "coil2000"}


def test_every_results_row_states_its_experiment_id():
    table = pd.DataFrame({"method": ["lr", "rf"], "mean": [0.2, 0.4]})
    stamped = mod.with_experiment_id(table, "coil2000")

    assert list(stamped.columns)[0] == "experiment_id"
    assert list(stamped["experiment_id"]) == ["coil2000", "coil2000"]
    # the existing columns keep their values and row order
    assert list(stamped["method"]) == ["lr", "rf"]
    assert list(stamped["mean"]) == [0.2, 0.4]
    # the input is not mutated
    assert "experiment_id" not in table.columns


def test_an_ad_hoc_run_stamps_an_empty_experiment_id():
    table = pd.DataFrame({"method": ["lr"], "mean": [0.2]})
    assert list(mod.with_experiment_id(table, None)["experiment_id"]) == [""]


def _experiment(model_version="v3_default"):
    """The declaration a capture belongs to. The capture reads this, not the run's global."""
    from src.experiment_spec import Experiment

    return Experiment(id="toy", dataset="toy", methods=("lgbm",), metric="log_loss",
                      n_folds=1, seed=42, model_version=model_version)


def test_the_capture_manifest_records_the_experiment_id(tmp_path, monkeypatch):
    import json

    monkeypatch.setattr(mod, "PREDICTIONS_DIR", tmp_path)
    n_folds, methods = 2, ["lgbm"]
    pred_store = _toy_pred_store(n_folds=n_folds, methods=methods)
    ds = dict(name="toy", file="toy.csv", target="y", drop=[])

    npz_path = mod.write_predictions_npz(ds, pred_store, methods, n_folds,
                                          problem_type="classification",
                                          metric_name="log_loss", seed=42,
                                          experiment=_experiment())
    manifest = json.loads(npz_path.with_suffix(".manifest.json").read_text())
    assert manifest["experiment_id"] == "toy"
    assert npz_path.name == "toy__seed42__v3_default.npz"  # capture discovery unchanged


def test_the_capture_manifest_carries_the_dataset_declaration_not_the_runs(tmp_path, monkeypatch):
    # A capture covers one experiment, so it records that experiment's literal even when the
    # run it belongs to is a sweep with no single experiment_id (#239).
    import json

    monkeypatch.setattr(mod, "PREDICTIONS_DIR", tmp_path)
    monkeypatch.setattr(mod, "_model_path", lambda: "v3.5_default")
    n_folds, methods = 2, ["lgbm"]
    ds = dict(name="toy", file="toy.csv", target="y", drop=[])

    npz_path = mod.write_predictions_npz(ds, _toy_pred_store(n_folds=n_folds, methods=methods),
                                          methods, n_folds, problem_type="classification",
                                          metric_name="log_loss", seed=42,
                                          experiment=_experiment())
    manifest = json.loads(npz_path.with_suffix(".manifest.json").read_text())

    assert manifest["model_version_declared"] == "v3_default"
    assert manifest["model_version"] == "v3.5_default"
    assert manifest["model_version_mismatch"] is True


def test_an_ad_hoc_capture_records_an_absent_declaration(tmp_path, monkeypatch):
    # No experiment, so the capture declares nothing. It must say so, not borrow the run's
    # value or claim agreement.
    import json

    monkeypatch.setattr(mod, "PREDICTIONS_DIR", tmp_path)
    n_folds, methods = 2, ["lgbm"]
    ds = dict(name="toy_adhoc", file="toy.csv", target="y", drop=[])

    npz_path = mod.write_predictions_npz(ds, _toy_pred_store(n_folds=n_folds, methods=methods),
                                          methods, n_folds, problem_type="classification",
                                          metric_name="log_loss", seed=42)
    manifest = json.loads(npz_path.with_suffix(".manifest.json").read_text())

    assert manifest["model_version_declared"] is None
    assert manifest["model_version_mismatch"] is None
    assert manifest["model_version_mismatch"] is not False


def test_parse_drop_splits():
    args = parse(["--data", "X", "--target", "Y", "--drop", "a,b"])
    datasets, wanted = mod.select_datasets(args)
    assert datasets[0]["drop"] == ["a", "b"]


# ---- b. Synthetic ds construction ------------------------------------------

def test_synthetic_ds():
    args = parse(["--data", "/abs/path/foo.csv", "--target", "T", "--drop", "a,b"])
    datasets, wanted = mod.select_datasets(args)
    assert wanted is None  # --data wins; filters ignored
    assert len(datasets) == 1
    ds = datasets[0]
    assert ds["name"] == "foo"  # csv stem without .csv
    assert ds["file"] == "/abs/path/foo.csv"  # absolute path kept as given
    assert ds["target"] == "T"
    assert ds["drop"] == ["a", "b"]


def test_synthetic_ds_default_drop_and_relative_path():
    args = parse(["--data", "data/raw/foo.csv", "--target", "T"])
    ds, _ = mod.select_datasets(args)
    assert ds[0]["drop"] == []
    assert ds[0]["name"] == "foo"
    assert ds[0]["file"] == str(mod.REPO / "data/raw/foo.csv")  # repo-root-relative


def test_synthetic_ds_metric_by_mode():
    # The plot step does METRIC_LABELS[ds["metric"]] — the synthetic entry must
    # carry a metric or --data crashes at the plot (regression mode especially).
    cls, _ = mod.select_datasets(parse(["--data", "X.csv", "--target", "Y"]))
    reg, _ = mod.select_datasets(parse(["--data", "X.csv", "--target", "Y", "--regression"]))
    assert cls[0]["metric"] == "log_loss"
    assert reg[0]["metric"] == "rmse"


# ---- c. load_Xy on a real registry CSV --------------------------------------

def test_load_xy_coil2000():
    reg = next(ds for ds in mod.DATASETS if ds["name"] == "coil2000")
    X, y = mod.load_Xy(reg)

    assert X.dtype == np.float32
    assert y.dtype == np.int64  # classification path
    assert len(X) == len(y)

    # X holds every column except target + drop, same rows (post dropna)
    df = pd.read_csv(mod.DATA_RAW / reg["file"]).dropna(subset=[reg["target"]]).reset_index(drop=True)
    assert X.shape[0] == len(df)
    assert X.shape[1] == len([c for c in df.columns if c not in [reg["target"]] + reg["drop"]])
    assert np.array_equal(y, df[reg["target"]].to_numpy(dtype=np.int64))


# ---- d. Prediction capture (--save-predictions, #122) ------------------------

def _toy_pred_store(n_folds=2, methods=("lgbm", "tweedieglm"), n_per_fold=5, seed=0):
    """Synthetic two-fold pred_store: known y_true/y_pred so read-back is checkable
    by hand, no real dataset or model fit involved."""
    rng = np.random.default_rng(seed)
    store: dict[str, np.ndarray] = {}
    for k in range(n_folds):
        y_true = rng.integers(0, 2, size=n_per_fold).astype(np.float32)
        store[f"y_true__fold{k}"] = y_true
        store[f"test_idx__fold{k}"] = np.arange(n_per_fold, dtype=np.int32)
        for m in methods:
            p1 = rng.uniform(0.05, 0.95, size=n_per_fold).astype(np.float32)
            store[f"{m}__fold{k}"] = p1
    return store


def test_the_regression_runner_receives_the_cli_seed(monkeypatch, tmp_path):
    seen = {}

    def capture(_ds, out_csv, _out_png, seed=None, n_folds=None, row_size=None):
        seen.update(seed=seed, folds=n_folds, filename=Path(out_csv).name)
        raise AssertionError("stop after capture")

    monkeypatch.setattr(mod, "run_dataset_regression", capture)
    monkeypatch.setattr(sys, "argv",
                        ["prog", "ausautoBI8999", "--regression", "--seed", "7",
                         "--out-dir", str(tmp_path)])
    with pytest.raises(AssertionError, match="stop after capture"):
        mod.main()
    assert seen == {"seed": 7, "folds": 5,
                    "filename": "frontier_results_ausautoBI8999_seed7.csv"}


def test_a_regression_experiment_passes_its_declared_seed(monkeypatch, tmp_path):
    import dataclasses

    datasets, experiment = mod.experiment_selection("freMTPL2freq")
    monkeypatch.setattr(mod, "experiment_selection",
                        lambda _id: (datasets, dataclasses.replace(experiment, seed=7)))
    seen = {}

    def capture(_ds, _out_csv, _out_png, seed=None, n_folds=None, experiment=None,
                row_size=None):
        seen.update(seed=seed, folds=n_folds)
        raise AssertionError("stop after capture")

    monkeypatch.setattr(mod, "run_dataset_regression", capture)
    monkeypatch.setattr(sys, "argv",
                        ["prog", "--experiment", "freMTPL2freq", "--seed", "7",
                         "--out-dir", str(tmp_path)])
    with pytest.raises(AssertionError, match="stop after capture"):
        mod.main()
    assert seen == {"seed": 7, "folds": 5}


def test_regression_capture_split_states_the_seed(tmp_path, monkeypatch):
    import json

    monkeypatch.setattr(mod, "PREDICTIONS_DIR", tmp_path)
    pred_store = _toy_pred_store(n_folds=2, methods=("lgbm",))
    ds = dict(name="toyreg", file="toy.csv", target="y", drop=[])

    npz_path = mod.write_predictions_npz(ds, pred_store, ["lgbm"], 2,
                                          problem_type="regression",
                                          metric_name="rmse", seed=7)
    manifest = json.loads(npz_path.with_suffix(".manifest.json").read_text())
    assert manifest["seed"] == 7
    assert manifest["split"] == "KFold(2, shuffle=True, random_state=7)"


def test_write_predictions_npz_and_readback(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "PREDICTIONS_DIR", tmp_path)
    mod.SAVE_PREDICTIONS = True
    n_folds, methods = 2, ["lgbm", "tweedieglm"]
    pred_store = _toy_pred_store(n_folds=n_folds, methods=methods)
    ds = dict(name="toy", file="toy.csv", target="y", drop=[])
    metric = mod.metric_fn({})  # default: log_loss

    npz_path = mod.write_predictions_npz(ds, pred_store, methods, n_folds,
                                          problem_type="classification",
                                          metric_name="log_loss", seed=42)
    assert npz_path.exists()
    manifest_path = npz_path.with_suffix(".manifest.json")
    assert manifest_path.exists()

    import json
    manifest = json.loads(manifest_path.read_text())
    assert manifest["dataset"] == "toy"
    assert manifest["n_folds"] == n_folds
    assert manifest["methods"] == methods
    assert manifest["seed"] == 42
    assert manifest["schema_version"] == 1
    assert len(manifest["script_git_sha"]) in (7, 40, len("unknown"))
    with np.load(npz_path) as saved:
        assert manifest["predictions_sha256"] == mod.predictions_data_sha256(saved)
    assert mod.verify_predictions_dir(tmp_path) == 0

    # rows["mean"] computed the exact same way read-back will recompute it, so this
    # must pass with plenty of margin (both paths reconstruct pp identically).
    rows = []
    for m in methods:
        vals = [metric(pred_store[f"y_true__fold{k}"],
                        mod._reconstruct_pp(m, pred_store[f"{m}__fold{k}"]))
                for k in range(n_folds)]
        rows.append({"method": m, "mean": float(np.mean(vals))})
    mod.verify_predictions_readback(npz_path, methods, metric, rows, n_folds,
                                     problem_type="classification")


def test_verify_predictions_dir_catches_tampered_npz(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "PREDICTIONS_DIR", tmp_path)
    n_folds, methods = 2, ["lgbm"]
    pred_store = _toy_pred_store(n_folds=n_folds, methods=methods)
    ds = dict(name="toy3", file="toy3.csv", target="y", drop=[])
    npz_path = mod.write_predictions_npz(ds, pred_store, methods, n_folds,
                                          problem_type="classification",
                                          metric_name="log_loss", seed=42)
    assert mod.verify_predictions_dir(tmp_path) == 0
    # one prediction nudged by a float32 ulp must break the hash
    pred_store["lgbm__fold0"][0] = np.nextafter(pred_store["lgbm__fold0"][0], np.float32(1))
    np.savez_compressed(npz_path, **pred_store)
    assert mod.verify_predictions_dir(tmp_path) == 1


def test_verify_predictions_readback_catches_mismatch(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "PREDICTIONS_DIR", tmp_path)
    n_folds, methods = 2, ["lgbm"]
    pred_store = _toy_pred_store(n_folds=n_folds, methods=methods)
    ds = dict(name="toy2", file="toy2.csv", target="y", drop=[])
    metric = mod.metric_fn({})
    npz_path = mod.write_predictions_npz(ds, pred_store, methods, n_folds,
                                          problem_type="classification",
                                          metric_name="log_loss", seed=42)
    bogus_rows = [{"method": "lgbm", "mean": 999.0}]
    with pytest.raises(AssertionError, match="read-back mismatch"):
        mod.verify_predictions_readback(npz_path, methods, metric, bogus_rows, n_folds,
                                         problem_type="classification")


def test_write_predictions_npz_rejects_length_mismatch(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "PREDICTIONS_DIR", tmp_path)
    pred_store = {
        "y_true__fold0": np.array([0.0, 1.0, 0.0], dtype=np.float32),
        "test_idx__fold0": np.array([0, 1, 2], dtype=np.int32),
        "lgbm__fold0": np.array([0.1, 0.9], dtype=np.float32),  # wrong length
    }
    ds = dict(name="bad", file="bad.csv", target="y", drop=[])
    with pytest.raises(AssertionError, match="length mismatch"):
        mod.write_predictions_npz(ds, pred_store, ["lgbm"], 1,
                                   problem_type="classification",
                                   metric_name="log_loss", seed=42)


def test_reconstruct_pp():
    p1 = np.array([0.2, 0.8], dtype=np.float32)
    pp_lgbm = mod._reconstruct_pp("lgbm", p1)
    assert np.allclose(pp_lgbm[:, 1], p1)
    assert np.allclose(pp_lgbm.sum(axis=1), 1.0)

    # tweedieglm/poissonglm re-clip to [1e-6, 1-1e-6] before reconstructing
    raw = np.array([-0.5, 1.5], dtype=np.float32)  # outside [0, 1], as a raw GLM mean can be
    pp_glm = mod._reconstruct_pp("tweedieglm", raw)
    # Compare the bounds in the ARRAY's dtype, not against float64 literals. The clip is applied in
    # float32, where float32(1e-6) rounds to 9.99999997e-07 -- BELOW the float64 literal 1e-6. The
    # old comparison therefore failed on a correct result, and had done so on every run. The
    # property under test is unchanged: the output stays inside the documented clip.
    assert pp_glm.dtype == np.float32
    assert pp_glm[:, 1].min() >= np.float32(1e-6)
    assert pp_glm[:, 1].max() <= np.float32(1 - 1e-6)


# ---- the row-size point (#264) ----------------------------------------------

def test_parse_size_defaults_to_full():
    assert parse([]).size == "full"
    assert parse(["--size", "1000"]).size == "1000"


def test_an_experiment_run_stamps_the_row_size_point(monkeypatch, tmp_path):
    import json

    refuse_to_run(monkeypatch)
    monkeypatch.setattr(sys, "argv",
                        ["prog", "--experiment", "coil2000", "--size", "1000",
                         "--out-dir", str(tmp_path)])
    with pytest.raises(AssertionError, match="reached the dataset runner"):
        mod.main()

    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["row_size"] == 1000


def test_an_undeclared_size_is_refused_by_name(monkeypatch, tmp_path):
    refuse_to_run(monkeypatch)
    monkeypatch.setattr(sys, "argv",
                        ["prog", "--experiment", "coil2000", "--size", "2000",
                         "--out-dir", str(tmp_path)])

    with pytest.raises(SystemExit):
        mod.main()


def test_size_cannot_be_combined_with_data(monkeypatch, tmp_path):
    refuse_to_run(monkeypatch)
    monkeypatch.setattr(sys, "argv",
                        ["prog", "--data", "X.csv", "--target", "y", "--size", "1000",
                         "--out-dir", str(tmp_path)])

    with pytest.raises(SystemExit):
        mod.main()


def test_the_regression_path_declares_no_row_sizes_yet(monkeypatch, tmp_path):
    refuse_to_run(monkeypatch)
    monkeypatch.setattr(sys, "argv",
                        ["prog", "--regression", "--size", "1000", "--out-dir", str(tmp_path)])

    with pytest.raises(SystemExit):
        mod.main()


def test_a_sweep_size_is_validated_against_every_dataset_it_covers(monkeypatch, tmp_path):
    # Only three sweep datasets declare 1000/5000; norauto and the rest are full-only, so
    # an unfiltered run cannot honour --size 1000 for the whole sweep.
    refuse_to_run(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["prog", "--size", "1000", "--out-dir", str(tmp_path)])

    with pytest.raises(SystemExit):
        mod.main()


def test_a_filtered_sweep_accepts_a_declared_size(monkeypatch, tmp_path):
    import json

    refuse_to_run(monkeypatch)
    monkeypatch.setattr(sys, "argv",
                        ["prog", "coil2000", "--size", "1000", "--out-dir", str(tmp_path)])
    with pytest.raises(AssertionError, match="reached the dataset runner"):
        mod.main()

    assert json.loads((tmp_path / "manifest.json").read_text())["row_size"] == 1000


def test_every_results_row_states_the_row_count():
    table = pd.DataFrame({"method": ["lr"], "mean": [0.2]})
    stamped = mod.with_row_count(table, 1000)

    assert list(stamped.columns)[0] == "n_rows"
    assert list(stamped["n_rows"]) == [1000]
    assert "n_rows" not in table.columns
