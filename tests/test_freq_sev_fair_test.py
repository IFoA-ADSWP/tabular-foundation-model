"""The fair test's verdict arithmetic (#555): pairing by seed, and the registered decision rule.

The bug this guards against is quiet: averaging each arm's sorted metric values instead of pairing
`s` with `s` compares seed 0's control with seed 1's treatment whenever the ordering differs, and
still returns a plausible-looking number. So the fixture below gives the seeds deliberately
crossed values, where sorting and pairing disagree.
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "analyses" / "freq_sev_fair_test.py"


def _module():
    spec = importlib.util.spec_from_file_location("freq_sev_fair_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["freq_sev_fair_test"] = module
    spec.loader.exec_module(module)
    return module


def _slot(run: Path, *, arm: str, seed: int, fold: int, value: float, **extra) -> None:
    slot = run / "freMTPL2freq" / arm / f"seed{seed}_fold{fold}"
    slot.mkdir(parents=True)
    record = {"arm": arm, "seed": seed, "fold": fold, "verdict_metric_value": value, **extra}
    (slot / "meta.json").write_text(json.dumps(record))


def test_seeds_are_paired_by_id_not_by_sorted_value(tmp_path):
    """The arms' orderings differ here, so sorting the values mispairs the seeds.

    Correct: seed 0 is (10-100)/10 = -9.0 and seed 1 is (100-9)/100 = +0.91, mean -4.045.
    Sorting each arm's values first would pair 10 with 9 and 100 with 100, mean +0.05.
    """
    run = tmp_path / "20261112T000000Z"
    for seed, (control, treatment) in enumerate(((10.0, 100.0), (100.0, 9.0))):
        _slot(run, arm="A_raw", seed=seed, fold=0, value=control)
        _slot(run, arm="B_ft30", seed=seed, fold=0, value=treatment)

    ratios = _module().fold_ratios(run)

    assert math.isclose(ratios[0], -4.045, abs_tol=1e-9)


def test_the_decision_rule_is_the_registered_one():
    decide = _module().decide

    assert decide(0.07, 0.03, 0.11, floor=0.02) == "Go"            # clear of the floor
    assert decide(0.01, -0.01, 0.03, floor=0.02) == "Inconclusive"  # covers zero and the floor
    assert decide(-0.01, -0.02, -0.005, floor=0.02) == "No-go"      # a gain is excluded
    assert decide(0.03, 0.005, 0.06, floor=0.02) == "Go"            # excludes zero, above floor


def test_a_target_interval_is_the_paired_t_over_five_folds():
    ratios = {fold: 0.10 for fold in range(5)}

    mean, half, sd = _module().target_interval(ratios)

    assert mean == 0.10 and sd == 0.0 and half == 0.0


def test_the_task_mean_is_the_mean_of_portfolios():
    task_interval = _module().task_interval
    mean, low, high = task_interval([{0: 0.20, 1: 0.20}, {0: 0.0, 1: 0.0}], reps=200)

    assert math.isclose(mean, 0.10)
    assert low <= mean <= high


def test_the_row_scaling_arm_is_reported_and_not_folded_into_the_task(tmp_path, monkeypatch, capsys):
    """The #572 arm asks whether a bigger budget moves the verdict; it does not replace it.

    So a run passed through `--row-scale-french` must appear under `row_scale` and leave both
    `targets` and the severity task mean exactly where the registered pair put them. Folding it in
    would silently restate the published severity number.
    """
    module = _module()
    monkeypatch.setattr(module, "RESULTS", tmp_path)

    registered = {
        "frequency_french": ("20261112T000001Z", 0.90),
        "frequency_spanish": ("20261112T000002Z", 0.96),
        "severity_french": ("20261112T000003Z", 1.01),
        "severity_spanish": ("20261112T000004Z", 0.98),
    }
    for run_id, treatment in registered.values():
        for fold in range(2):
            for arm, value in (("A_raw", 1.0), ("B_ft30", treatment)):
                _slot(tmp_path / run_id, arm=arm, seed=0, fold=fold, value=value)

    row_scale_id = "20261113T000005Z"
    for fold in range(2):
        for arm, value in (("A_raw", 1.0), ("B_ft30", 1.02)):
            _slot(tmp_path / row_scale_id, arm=arm, seed=0, fold=fold, value=value, train_rows=21177)

    argv = ["--reps", "50", "--json", "--row-scale-french", row_scale_id]
    for target, (run_id, _treatment) in registered.items():
        argv += [f"--{target.replace('_', '-')}", run_id]

    module.main(argv)
    summary = json.loads(capsys.readouterr().out)

    assert set(summary["targets"]) == set(registered)
    assert math.isclose(summary["tasks"]["severity"]["mean"], 0.005)
    assert math.isclose(summary["row_scale"]["mean"], -0.02)
    assert summary["row_scale"]["decision"] == "No-go"
    assert summary["row_scale"]["train_rows"] == [21177]


def test_the_frequency_row_scaling_arm_is_reported_and_not_folded_into_the_task(
    tmp_path, monkeypatch, capsys
):
    """The frequency half of #572 is the mirror: +9.69% on 1.8% of the pool, retested at 40,000 rows.

    A run passed through `--row-scale-frequency` must appear under `row_scale_frequency` and leave
    the registered frequency task mean exactly where the 10,000-row pair put it. Folding it in would
    silently restate the published Go, in whichever direction the bigger budget moved the number.
    """
    module = _module()
    monkeypatch.setattr(module, "RESULTS", tmp_path)

    registered = {
        "frequency_french": ("20261112T000001Z", 0.90),
        "frequency_spanish": ("20261112T000002Z", 0.96),
        "severity_french": ("20261112T000003Z", 1.01),
        "severity_spanish": ("20261112T000004Z", 0.98),
    }
    for run_id, treatment in registered.values():
        for fold in range(2):
            for arm, value in (("A_raw", 1.0), ("B_ft30", treatment)):
                _slot(tmp_path / run_id, arm=arm, seed=0, fold=fold, value=value)

    # The arm reverses here (r = -8%) so a fold-in would be visible as a moved task mean.
    row_scale_id = "20261113T000006Z"
    for fold in range(2):
        for arm, value in (("A_raw", 1.0), ("B_ft30", 1.08)):
            _slot(tmp_path / row_scale_id, arm=arm, seed=0, fold=fold, value=value, train_rows=40000)

    argv = ["--reps", "50", "--json", "--row-scale-frequency", row_scale_id]
    for target, (run_id, _treatment) in registered.items():
        argv += [f"--{target.replace('_', '-')}", run_id]

    module.main(argv)
    summary = json.loads(capsys.readouterr().out)

    assert set(summary["targets"]) == set(registered)
    assert math.isclose(summary["tasks"]["frequency"]["mean"], 0.07)  # (0.10 + 0.04) / 2
    assert math.isclose(summary["row_scale_frequency"]["mean"], -0.08)
    assert summary["row_scale_frequency"]["target"] == "frequency_french"
    assert summary["row_scale_frequency"]["decision"] == "No-go"
    assert summary["row_scale_frequency"]["train_rows"] == [40000]
    assert "row_scale" not in summary


def test_both_row_scaling_arms_keep_their_own_entry(tmp_path, monkeypatch, capsys):
    """The two arms' summary keys are asymmetric (`row_scale` vs `row_scale_frequency`).

    A refactor that derived the key from the target name, or reused `row_scale` for both, would
    silently overwrite one arm with the other when a caller passes both — which the reproduce
    command in the verdict document does. So pass both and check each keeps its own run id.
    """
    module = _module()
    monkeypatch.setattr(module, "RESULTS", tmp_path)

    registered = {
        "frequency_french": ("20261112T000001Z", 0.90),
        "frequency_spanish": ("20261112T000002Z", 0.96),
        "severity_french": ("20261112T000003Z", 1.01),
        "severity_spanish": ("20261112T000004Z", 0.98),
    }
    for run_id, treatment in registered.values():
        for fold in range(2):
            for arm, value in (("A_raw", 1.0), ("B_ft30", treatment)):
                _slot(tmp_path / run_id, arm=arm, seed=0, fold=fold, value=value)

    severity_arm, frequency_arm = "20261113T000005Z", "20261113T000006Z"
    for run_id, treatment, rows in ((severity_arm, 0.98, 21177), (frequency_arm, 1.08, 40000)):
        for fold in range(2):
            for arm, value in (("A_raw", 1.0), ("B_ft30", treatment)):
                _slot(tmp_path / run_id, arm=arm, seed=0, fold=fold, value=value, train_rows=rows)

    argv = [
        "--reps", "50", "--json",
        "--row-scale-french", severity_arm,
        "--row-scale-frequency", frequency_arm,
    ]
    for target, (run_id, _treatment) in registered.items():
        argv += [f"--{target.replace('_', '-')}", run_id]

    module.main(argv)
    summary = json.loads(capsys.readouterr().out)

    assert summary["row_scale"]["run_id"] == severity_arm
    assert summary["row_scale"]["target"] == "severity_french"
    assert summary["row_scale"]["train_rows"] == [21177]
    assert summary["row_scale_frequency"]["run_id"] == frequency_arm
    assert summary["row_scale_frequency"]["target"] == "frequency_french"
    assert summary["row_scale_frequency"]["train_rows"] == [40000]
    assert summary["row_scale"]["mean"] != summary["row_scale_frequency"]["mean"]
