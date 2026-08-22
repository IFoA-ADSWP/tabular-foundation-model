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
