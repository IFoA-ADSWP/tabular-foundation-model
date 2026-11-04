"""The verdict tool (#398): deltas, null band, resolution, reading.

Fixtures are small run directories built in a temporary directory — the same seam
`test_capture_manifest.py` and `test_rescore_contract.py` use — so the tests assert what a reader can
observe: the numbers, the refusal, and the same output twice.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import verdict  # noqa: E402
from capture_reader import read_run  # noqa: E402
from metrics import roc_auc  # noqa: E402
from provenance import sha256_array  # noqa: E402
from run_capture import CaptureRefused  # noqa: E402

N = 400
RUN_ID = "20261104T120000Z"


def _slot(run: Path, arm: str, seed: int, truth, predictions) -> None:
    directory = run / "lapse" / arm / f"seed{seed}_foldNone"
    directory.mkdir(parents=True)
    np.save(directory / "predictions.npy", predictions)
    np.save(directory / "ground_truth.npy", truth)
    (directory / "meta.json").write_text(
        json.dumps(
            {
                "arm": arm,
                "seed": seed,
                "test_rows": len(truth),
                "predictions_sha256": sha256_array(predictions),
            }
        )
    )


def _run(tmp_path: Path, seeds=(43, 44), tuned: bool = True, signal: float = 0.2,
         baseline: bool = True) -> Path:
    """A run where the tuned arm separates the classes by `signal` more than the baseline."""
    run = tmp_path / RUN_ID
    for seed in seeds:
        rng = np.random.default_rng(1000 + seed)
        truth = np.array([0, 1] * (N // 2))
        mix = rng.random(N)
        base = np.clip(0.5 * truth + 0.5 * mix, 0, 1)
        if baseline:
            _slot(run, "A_raw", seed, truth, base)
        if tuned:
            if signal == 0.0:
                shifted = np.clip(base + rng.normal(0, 0.02, N), 0, 1)
            else:
                shifted = np.clip(signal * truth + (1.0 - signal) * mix, 0, 1)
            _slot(run, "B_ft3", seed, truth, shifted)
    return run


def _forced(mean: float, sd: float, brier: float = 0.0) -> verdict.Arm:
    """An Arm with a chosen mean and spread, built from real Delta objects."""
    n = 40
    values = [mean] * (n - 2) + [mean - 2.5 * sd, mean + 2.5 * sd]
    return verdict.Arm(
        name="B_ft3",
        deltas=tuple(
            verdict.Delta("B_ft3", 40 + i, 0.9, value, brier) for i, value in enumerate(values)
        ),
    )


def test_deltas_are_measured_against_the_in_run_baseline(tmp_path):
    run = read_run(_run(tmp_path, signal=0.4))
    (arm,) = verdict.arms(run)
    assert arm.name == "B_ft3"
    assert len(arm.deltas) == 2
    for delta in arm.deltas:
        tuned = run.slots[[(s.arm, s.seed) for s in run.slots].index(("B_ft3", delta.seed))]
        base = run.slots[[(s.arm, s.seed) for s in run.slots].index(("A_raw", delta.seed))]
        assert delta.auc == pytest.approx(roc_auc(tuned.truth, tuned.predictions))
        assert delta.delta_auc == pytest.approx(
            roc_auc(tuned.truth, tuned.predictions) - roc_auc(base.truth, base.predictions)
        )


def test_a_known_null_run_with_a_tight_interval_claims_equivalence(tmp_path):
    """Noise-only scores, and an interval inside the bounds: the honest claim is "no effect this big"."""
    run = read_run(_run(tmp_path, signal=0.0))
    (arm,) = verdict.arms(run)
    null = verdict.null_band(run, arm, reps=120)
    assert null["sd"] > 0
    assert all(band > 0 for band in null["band95"].values())
    # The instrument check is a separate concern and needs more replicates than this fixture runs.
    assert verdict.reading(arm, 0.002) == "equivalence"


def test_the_tool_reproduces_the_committed_null_band_on_the_anchor():
    run = read_run(REPO_ROOT / "results" / "20261031T021845Z")
    assert verdict.mean_band(run, reps=300) == pytest.approx(0.010, abs=0.003)


def test_a_seed_set_that_reuses_the_probe_is_refused(tmp_path):
    run = _run(tmp_path)
    other = _run(tmp_path / "other")
    with pytest.raises(CaptureRefused, match="must be disjoint"):
        verdict.check_seeds(read_run(run), exclude_run=other)


def test_a_run_short_of_the_declared_seed_count_is_refused(tmp_path):
    run = _run(tmp_path)
    with pytest.raises(CaptureRefused, match="declares"):
        verdict.check_seeds(read_run(run), declared=10)


def test_the_csv_is_byte_identical_across_runs(tmp_path):
    run = read_run(_run(tmp_path))
    first = verdict.render_csv(verdict.rows(run, 0.002, reps=120))
    second = verdict.render_csv(verdict.rows(run, 0.002, reps=120))
    assert first == second
    assert first.splitlines()[0].startswith("arm,seed,metric,value")
    assert "verdict/1" in first and "delta_auc/1" in first


def test_the_seed_count_formula_reproduces_the_sizing_document():
    # 0.00535 is the measured per-seed null SD; the sizing analysis gives 57 seeds for delta 0.002.
    design = verdict.resolution(0.00535, 0.002)
    assert design["seeds_needed"] == 57
    assert design["power"] >= 0.80


def test_power_falls_below_the_bar_when_the_seed_count_is_short():
    assert verdict.resolution(0.00535, 0.002, seeds=13)["power"] < 0.80


def test_reading_passes_only_when_the_effect_clears_the_target_and_the_brier_guard():
    assert verdict.reading(_forced(0.004, 0.0005), 0.002) == "pass"
    assert verdict.reading(_forced(0.004, 0.0005, brier=0.002), 0.002) == "unresolved"
    assert verdict.reading(_forced(0.0005, 0.0005), 0.002) == "equivalence"
    assert verdict.reading(_forced(0.0015, 0.03), 0.002) == "unresolved"


def test_a_run_with_no_tuned_arm_is_refused(tmp_path):
    run = _run(tmp_path, tuned=False)
    with pytest.raises(CaptureRefused, match="only A_raw"):
        verdict.arms(read_run(run))


def test_zero_between_seed_variance_never_passes():
    """Identical deltas make a zero-width interval; a pass from it is manufactured, not measured."""
    same = verdict.Arm(
        name="B_ft3", deltas=tuple(verdict.Delta("B_ft3", 40 + i, 0.9, 0.004, 0.0) for i in range(3))
    )
    assert same.sd == 0
    assert verdict.reading(same, 0.002) == "unresolved"


def test_zero_variance_never_claims_equivalence():
    flat = verdict.Arm(
        name="B_ft3", deltas=tuple(verdict.Delta("B_ft3", 40 + i, 0.9, 0.0, 0.0) for i in range(3))
    )
    assert verdict.reading(flat, 0.002) == "unresolved"


def test_a_rule_outside_the_instrument_band_is_void():
    arm = _forced(0.004, 0.0005)
    assert verdict.reading(arm, 0.002, false_positive_rate=0.20) == "void"
    assert verdict.reading(arm, 0.002, false_positive_rate=0.05) == "pass"


def test_a_run_without_the_baseline_arm_is_refused(tmp_path):
    run = _run(tmp_path, baseline=False)
    with pytest.raises(CaptureRefused, match="no A_raw"):
        verdict.arms(read_run(run))


def test_a_single_seed_is_refused(tmp_path):
    run = read_run(_run(tmp_path, seeds=(43,)))
    with pytest.raises(CaptureRefused, match="between-seed variance"):
        verdict.arms(run)


def test_a_non_positive_target_effect_is_refused():
    with pytest.raises(CaptureRefused, match="must be positive"):
        verdict.resolution(0.005, 0.0)


def test_too_few_permutations_are_refused(tmp_path):
    run = read_run(_run(tmp_path))
    (arm,) = verdict.arms(run)
    with pytest.raises(CaptureRefused, match="at least"):
        verdict.null_band(run, arm, reps=10)


def test_the_report_is_deterministic(tmp_path):
    run = read_run(_run(tmp_path, signal=0.2))
    assert verdict.report(run, 0.002, reps=120) == verdict.report(run, 0.002, reps=120)


def test_the_cli_exits_zero_on_a_run_and_two_on_a_bad_target(tmp_path):
    run = _run(tmp_path)
    assert verdict.main(["--run", str(run), "--reps", "120"]) == 0
    assert verdict.main(["--run", str(run), "--delta", "0"]) == 2
