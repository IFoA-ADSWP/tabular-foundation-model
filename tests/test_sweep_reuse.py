"""Sweep reuse provenance tests (issue #233).

The seam is the predicate plus the run manifest: a row is reusable only when the table
records the run's seed and resolved model version, and the manifest says which methods
reused a row and which were fitted. No model is fitted here.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd

from src.experiment_spec import Experiment

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


# ---------------------------------------------------------------------------
# Arm selection (#186's --tabpfn-default-only / --out-dir, no fitting)
# ---------------------------------------------------------------------------
def arms(methods: list[tuple[str, dict]]) -> list[tuple[str, object]]:
    return [(name, kw.get("n_estimators")) for name, kw in methods]


DEFAULT_ARMS = [
    ("tabpfn", None), ("tabpfn", 8), ("tabpfn", 1), ("cat", None), ("xgb", None),
    ("lgbm", None),
]
GBDT_ARMS = [("cat", None), ("xgb", None), ("lgbm", None)]


def test_the_default_cell_fits_every_arm():
    sweep = _load(SWEEP, "sweep_for_186_arms_test")

    assert arms(sweep.methods_for("coil2000", 1000)) == DEFAULT_ARMS
    # The n=8 probe arm is dropped only after the probe proves it identical.
    assert arms(sweep.methods_for("coil2000", 1000, n8_equals_default=True)) == [
        ("tabpfn", None), ("tabpfn", 1)] + GBDT_ARMS
    assert arms(sweep.methods_for("coil2000", 1000, n8_equals_default=False)) == DEFAULT_ARMS


def test_tabpfn_default_only_keeps_the_winner_table_arms():
    sweep = _load(SWEEP, "sweep_for_186_default_only_test")

    for size in (1000, 5000, None):
        assert arms(sweep.methods_for("coil2000", size, tabpfn_default_only=True)) == [
            ("tabpfn", None)] + GBDT_ARMS
    # §23.1's re-test: the default arm scored against the GBDTs, on the full bemtl97 cell too.
    assert arms(sweep.methods_for("bemtl97", None, tabpfn_default_only=True)) == [
        ("tabpfn", None)] + GBDT_ARMS


def test_the_full_bemtl97_trim_drops_the_extra_tabpfn_configs():
    sweep = _load(SWEEP, "sweep_for_trim_test")

    assert sweep.trimmed_for("bemtl97", None) is True
    assert arms(sweep.methods_for("bemtl97", None)) == [("tabpfn", None)] + GBDT_ARMS
    # Only the full cell is trimmed; the declared 1K/5K points fit every arm.
    assert sweep.trimmed_for("bemtl97", 5000) is False
    assert arms(sweep.methods_for("bemtl97", 5000)) == DEFAULT_ARMS
    assert sweep.trimmed_for("coil2000", None) is False


def test_the_new_cli_flags_reach_the_run_settings(monkeypatch):
    sweep = _load(SWEEP, "sweep_for_186_cli_test")

    monkeypatch.setattr(sys, "argv", ["prog"])
    default = sweep.parse_args()
    assert default.out_dir is None and default.tabpfn_default_only is False

    monkeypatch.setattr(sys, "argv", ["prog", "--out-dir", "results/run", "--tabpfn-default-only"])
    explicit = sweep.parse_args()
    assert explicit.out_dir == "results/run"
    assert explicit.tabpfn_default_only is True


def _experiment(model_version: str = "v3_default") -> Experiment:
    return Experiment(id="coil2000", dataset="coil2000", methods=("cat",),
                      metric="log_loss", n_folds=5, seed=42,
                      model_version=model_version)


def test_reuse_requires_the_declared_and_resolved_versions_to_agree():
    assert mod.reuse_version_for(_experiment(), "v3_default") == "v3_default"
    assert mod.reuse_version_for(_experiment(), "v2.5") is None


def test_an_ad_hoc_run_declares_nothing_and_reuses_nothing():
    assert mod.reuse_version_for(None, "v3_default") is None
