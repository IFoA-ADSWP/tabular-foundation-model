"""The row bootstrap reads the captures in the order it claims, and is reproducible (#752)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/analyses/severity_row_bootstrap.py"


def _module():
    spec = importlib.util.spec_from_file_location("bootstrap_for_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _make_tree(root: Path, seeds: int = 3, folds: int = 2, rows: int = 50) -> None:
    rng = np.random.default_rng(0)
    base = root / "run1" / "target"
    for arm in ("A_raw", "B_ft3", "B_ft10", "B_ft30"):
        for seed in range(seeds):
            for fold in range(folds):
                d = base / arm / f"seed{seed}_fold{fold}"
                d.mkdir(parents=True)
                truth = rng.normal(size=rows)
                shift = 0.0 if arm == "A_raw" else 0.05
                np.save(d / "ground_truth.npy", truth)
                np.save(d / "predictions.npy", truth + shift + rng.normal(scale=0.1, size=rows))
                np.save(d / "weights.npy", np.ones(rows))
                np.save(d / "test_index.npy", np.arange(fold * rows, (fold + 1) * rows))


def test_rows_are_the_folds_concatenated_and_seeds_stay_apart(tmp_path):
    cal = _module()
    _make_tree(tmp_path, seeds=3, folds=2, rows=50)
    per_seed, truth, weights = cal.load("run1", "target", results=tmp_path)
    assert truth.size == 100                      # folds concatenated
    assert per_seed["A_raw"].shape == (3, 100)    # seeds x rows
    assert weights.size == 100


def test_the_same_seed_gives_the_same_interval(tmp_path):
    cal = _module()
    _make_tree(tmp_path, seeds=3, folds=2, rows=50)
    per_seed, truth, weights = cal.load("run1", "target", results=tmp_path)
    a = cal.bootstrap(per_seed, truth, weights, False, 40, np.random.default_rng(7))
    b = cal.bootstrap(per_seed, truth, weights, False, 40, np.random.default_rng(7))
    assert a == b


def test_the_interval_brackets_the_point(tmp_path):
    cal = _module()
    _make_tree(tmp_path, seeds=4, folds=2, rows=200)
    per_seed, truth, weights = cal.load("run1", "target", results=tmp_path)
    res = cal.bootstrap(per_seed, truth, weights, False, 200, np.random.default_rng(1))
    r = res["B_ft30-A_raw"]
    assert r["low"] <= r["point"] <= r["high"]
