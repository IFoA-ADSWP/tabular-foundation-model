"""The actuarial baseline's analysis (#597): the better-baseline rule and the comparability proof.

Two ways this can be quietly wrong, and both are tested here:

* **The seed pairing.** Averaging each run's sorted metric values compares seed 0 with seed 1
  whenever an ordering differs, and still returns a plausible number.
* **The comparison itself.** If a baseline slot scores rows the registered capture did not, the
  number is a comparison between different test sets. The tool refuses instead of reporting it.
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "analyses" / "actuarial_baseline.py"


def _module():
    spec = importlib.util.spec_from_file_location("actuarial_baseline", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["actuarial_baseline"] = module
    spec.loader.exec_module(module)
    return module


def _tabpfn_slot(run: Path, *, arm: str, seed: int, fold: int, value: float, index) -> None:
    slot = run / "freMTPL2freq" / arm / f"seed{seed}_fold{fold}"
    slot.mkdir(parents=True)
    np.save(slot / "test_index.npy", np.asarray(index, dtype=np.int64))
    (slot / "meta.json").write_text(
        json.dumps({"method": "tabpfn", "arm": arm, "seed": seed, "fold": fold,
                    "verdict_metric_value": value, "train_rows": 10000})
    )


def _baseline_slot(
    run: Path, *, method: str, seed: int, fold: int, value: float, index, rows: int = 500000
) -> None:
    slot = run / "freMTPL2freq" / method / f"seed{seed}_fold{fold}"
    slot.mkdir(parents=True)
    np.save(slot / "test_index.npy", np.asarray(index, dtype=np.int64))
    (slot / "meta.json").write_text(
        json.dumps({"method": method, "arm": None, "seed": seed, "fold": fold,
                    "verdict_metric_value": value, "train_rows": rows})
    )


def test_fold_ratios_pair_seeds_by_id_not_by_sorted_value():
    module = _module()
    tabpfn = {(0, 0): 10.0, (0, 1): 100.0}
    baseline = {(0, 0): 100.0, (0, 1): 9.0}

    ratios = module.fold_ratios(tabpfn, baseline)

    # (100-10)/100 = 0.9 and (9-100)/9 = -10.111..., mean -4.6056
    assert ratios[0] == pytest.approx((0.9 + (9.0 - 100.0) / 9.0) / 2)


def test_the_verdict_is_against_the_better_baseline(tmp_path):
    module = _module()
    tabpfn_run = tmp_path / "20261112T000001Z"
    baseline_run = tmp_path / "20261114T090001Z"
    index = np.arange(5, dtype=np.int64)
    for fold in range(5):
        _tabpfn_slot(tabpfn_run, arm="B_ft30", seed=0, fold=fold, value=80.0, index=index)
        _tabpfn_slot(tabpfn_run, arm="A_raw", seed=0, fold=fold, value=85.0, index=index)
        # E_glm is the weaker baseline (higher deviance); F_catboost is the one to beat.
        _baseline_slot(baseline_run, method="E_glm", seed=0, fold=fold, value=100.0, index=index)
        _baseline_slot(baseline_run, method="F_catboost", seed=0, fold=fold, value=90.0,
                       index=index)

    target = "frequency_french"
    tabpfn_runs = {name: tabpfn_run for name in module.TARGETS}
    baseline_runs = {name: baseline_run for name in module.TARGETS}
    # The other three targets reuse the same slots; only this one's row is asserted.
    summary = module.analyse(tabpfn_runs, baseline_runs)

    row = summary["targets"][target]
    assert row["better_baseline"] == "F_catboost"
    assert row["verdict"]["mean"] == pytest.approx((90.0 - 80.0) / 90.0)
    assert row["verdict"]["floor"] == 0.02
    assert row["verdict"]["decision"] == "Go"
    assert row["by_baseline"]["E_glm"]["mean_r"] == pytest.approx((100.0 - 80.0) / 100.0)
    assert row["train_rows"] == [500000]


def test_a_run_that_is_not_five_folds_is_refused(tmp_path):
    """The interval and the MDE constant are the registered 4-df ones; a 3-fold run is not it."""
    module = _module()

    with pytest.raises(SystemExit, match="paired t over five folds"):
        module.target_verdict({0: 0.1, 1: 0.1, 2: 0.1}, floor=0.02)


def test_the_comparability_proof_refuses_a_different_test_index(tmp_path):
    module = _module()
    tabpfn_run = tmp_path / "20261112T000001Z"
    baseline_run = tmp_path / "20261114T090001Z"
    _tabpfn_slot(tabpfn_run, arm="A_raw", seed=0, fold=0, value=1.0, index=[0, 1, 2])
    _baseline_slot(baseline_run, method="E_glm", seed=0, fold=0, value=1.0, index=[0, 1, 3])

    with pytest.raises(SystemExit, match="score rows other than the registered capture"):
        module.assert_comparability(tabpfn_run, baseline_run)


def test_a_baseline_capture_without_test_index_is_refused(tmp_path):
    module = _module()
    tabpfn_run = tmp_path / "20261112T000001Z"
    baseline_run = tmp_path / "20261114T090001Z"
    _tabpfn_slot(tabpfn_run, arm="A_raw", seed=0, fold=0, value=1.0, index=[0, 1, 2])
    slot = baseline_run / "freMTPL2freq" / "E_glm" / "seed0_fold0"
    slot.mkdir(parents=True)
    (slot / "meta.json").write_text(json.dumps({"method": "E_glm", "seed": 0, "fold": 0}))

    with pytest.raises(SystemExit, match="no test_index"):
        module.assert_comparability(tabpfn_run, baseline_run)


def test_the_task_mean_is_descriptive_and_carries_no_decision(tmp_path, monkeypatch, capsys):
    module = _module()
    monkeypatch.setattr(module, "RESULTS", tmp_path)

    argv = []
    for index, target in enumerate(module.TARGETS):
        flag = target.replace("_", "-")
        tabpfn_id = f"20261112T00000{index}Z"
        baseline_id = f"20261114T09000{index}Z"
        argv += [f"--tabpfn-{flag}", tabpfn_id, f"--baseline-{flag}", baseline_id]
        run_index = np.arange(3, dtype=np.int64)
        for fold in range(5):
            _tabpfn_slot(tmp_path / tabpfn_id, arm="B_ft30", seed=0, fold=fold, value=80.0,
                         index=run_index)
            _tabpfn_slot(tmp_path / tabpfn_id, arm="A_raw", seed=0, fold=fold, value=85.0,
                         index=run_index)
            _baseline_slot(tmp_path / baseline_id, method="E_glm", seed=0, fold=fold,
                           value=100.0, index=run_index)
            _baseline_slot(tmp_path / baseline_id, method="F_catboost", seed=0, fold=fold,
                           value=90.0, index=run_index)
            _baseline_slot(tmp_path / baseline_id, method="M_intercept", seed=0, fold=fold,
                           value=140.0, index=run_index)

    module.main(argv + ["--json"])
    summary = json.loads(capsys.readouterr().out)

    assert set(summary["targets"]) == set(module.TARGETS)
    assert summary["tasks"]["frequency"]["mean_r"] == pytest.approx(10/90)
    assert "note" in summary["tasks"]["frequency"]
    assert "decision" not in summary["tasks"]["frequency"]
    assert math.isclose(
        summary["targets"]["frequency_spanish"]["anchor"]["mean"], 60 / 140, rel_tol=1e-6
    )
