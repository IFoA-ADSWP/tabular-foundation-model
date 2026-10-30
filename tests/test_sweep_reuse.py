"""Sweep reuse provenance tests (issue #233).

The seam is the predicate plus the run manifest: a row is reusable only when the table
records the run's seed and resolved model version, and the manifest says which methods
reused a row and which were fitted. No model is fitted here.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py"
SWEEP = ROOT / "scripts/benchmarks/run_home_turf_size_sweep.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mod = _load(RUNNER, "runner_for_233_test")


def sweep_frame(**overrides) -> pd.DataFrame:
    rows = []
    for method in ("cat", "tabpfn"):
        for fold in range(5):
            row = {
                "dataset": "coil2000", "n_rows": 100, "method": method, "fold": fold,
                "n_estimators": None, "log_loss": 0.2, "brier": 0.05, "roc_auc": 0.7,
                "seed": 42, "model_version": "v3_default",
            }
            row.update(overrides)
            rows.append(row)
    return pd.DataFrame(rows)


def test_a_matching_row_is_reusable():
    rows = mod.reusable_sweep_rows(sweep_frame(), "coil2000", 100, 42, "v3_default")
    assert len(rows) == 10


def test_a_legacy_table_without_provenance_is_never_reused():
    legacy = sweep_frame().drop(columns=["seed", "model_version"])
    rows = mod.reusable_sweep_rows(legacy, "coil2000", 100, 42, "v3_default")
    assert rows.empty


def test_a_different_seed_is_never_reused():
    rows = mod.reusable_sweep_rows(sweep_frame(), "coil2000", 100, 7, "v3_default")
    assert rows.empty


def test_a_different_model_version_is_never_reused():
    rows = mod.reusable_sweep_rows(sweep_frame(), "coil2000", 100, 42, "v2.5")
    assert rows.empty


def test_a_different_row_count_or_non_default_estimator_is_not_reused():
    frame = pd.concat([
        sweep_frame(),
        sweep_frame(n_estimators=8),  # a non-default TabPFN config, never a frontier row
    ], ignore_index=True)
    rows = mod.reusable_sweep_rows(frame, "coil2000", 100, 42, "v3_default")
    assert len(rows) == 10
    assert rows["n_estimators"].isna().all()
    assert mod.reusable_sweep_rows(frame, "coil2000", 5000, 42, "v3_default").empty


def test_a_table_with_columns_but_unattributable_rows_returns_only_matches():
    frame = pd.concat(
        [sweep_frame(), sweep_frame(seed=float("nan"))], ignore_index=True
    )
    rows = mod.reusable_sweep_rows(frame, "coil2000", 100, 42, "v3_default")
    assert len(rows) == 10
    assert (rows["seed"] == 42).all()


def test_the_manifest_is_rewritten_with_the_power_source(tmp_path, monkeypatch):
    args = argparse.Namespace(out_dir=str(tmp_path))
    monkeypatch.setattr(mod, "POWER_SOURCES", {})
    mod.write_manifest(tmp_path, args)
    assert json.loads((tmp_path / "manifest.json").read_text())["power"] is None

    monkeypatch.setattr(mod, "POWER_SOURCES",
                        {"coil2000": {"reused": ["cat", "lgbm"], "fresh": ["lr", "tabpfn"]}})
    mod.write_manifest(tmp_path, args)
    assert json.loads((tmp_path / "manifest.json").read_text())["power"] == {
        "coil2000": {"reused": ["cat", "lgbm"], "fresh": ["lr", "tabpfn"]}
    }


def test_the_sweep_writer_stamps_seed_and_model_version_on_every_row():
    sweep = _load(SWEEP, "sweep_for_233_test")
    row = sweep.sweep_row("coil2000", 1000, "cat", 0, None, False)

    assert row["seed"] == sweep.SPLIT_SEED == 42
    assert row["model_version"] == sweep._model_path()
