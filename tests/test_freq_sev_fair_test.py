"""The fair test's verdict arithmetic (#555): pairing by seed, and the registered decision rule.

The bug this guards against is quiet: averaging each arm's sorted metric values instead of pairing
`s` with `s` compares seed 0's control with seed 1's treatment whenever the ordering differs, and
still returns a plausible-looking number. So the fixture below gives the seeds deliberately
crossed values, where sorting and pairing disagree.
"""

from __future__ import annotations

import importlib.util
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


def _slot(run: Path, *, arm: str, seed: int, fold: int, value: float) -> None:
    slot = run / "freMTPL2freq" / arm / f"seed{seed}_fold{fold}"
    slot.mkdir(parents=True)
    (slot / "meta.json").write_text(
        '{"arm": "%s", "seed": %d, "fold": %d, "verdict_metric_value": %r}' % (arm, seed, fold, value)
    )


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
