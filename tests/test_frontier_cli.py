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
    manifest_path = tmp_path / "toy__seed42.manifest.json"
    assert manifest_path.exists()

    import json
    manifest = json.loads(manifest_path.read_text())
    assert manifest["dataset"] == "toy"
    assert manifest["n_folds"] == n_folds
    assert manifest["methods"] == methods
    assert manifest["seed"] == 42
    assert manifest["schema_version"] == 1
    assert len(manifest["script_git_sha"]) in (7, 40, len("unknown"))

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


def test_verify_predictions_readback_catches_mismatch(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "PREDICTIONS_DIR", tmp_path)
    n_folds, methods = 1, ["lgbm"]
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
    assert pp_glm[:, 1].min() >= 1e-6
    assert pp_glm[:, 1].max() <= 1 - 1e-6
