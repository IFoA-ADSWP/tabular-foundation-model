"""The fair-test runner writes the pre-registered matrix and a readable v3 capture (#539).

Seam under test: the run directory on disk and the manifest `read_run` accepts. The model is
stubbed — these tests are about the loop, the shared test rows and the record, not about TabPFN.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from capture_reader import read_run
from fair_test_runner import ARMS, RunConfig, run, slot_matrix
from regression_data import load_frame


class StubBackend:
    name = "stub"

    def provenance(self) -> dict:
        return {
            "versions": {"tabpfn": "stub", "python": "3.12"},
            "weights": {"path": "/cache/stub.ckpt", "sha256": "a" * 64},
        }

    def fit_predict(self, X_train, y_train, X_test, *, seed, epochs):
        del seed, epochs
        prediction = np.full(len(X_test), float(np.mean(y_train)))
        return prediction, np.tile(prediction, (9, 1))


class LargePredictionBackend(StubBackend):
    """Returns 5.0 whatever it is given, so a back-transform is unmistakable (expm1(5) = 147.4)."""

    def fit_predict(self, X_train, y_train, X_test, *, seed, epochs):
        del X_train, y_train, seed, epochs
        prediction = np.full(len(X_test), 5.0)
        return prediction, np.tile(prediction, (9, 1))


class NaNBackend(StubBackend):
    def fit_predict(self, X_train, y_train, X_test, *, seed, epochs):
        prediction, quantiles = super().fit_predict(
            X_train, y_train, X_test, seed=seed, epochs=epochs
        )
        prediction[0] = np.nan
        return prediction, quantiles


SMALL = dict(folds=1, seeds=(0,), test_rows=32)


def _run(tmp_path: Path, backend=None) -> dict[str, Path]:
    config = RunConfig(**SMALL)
    return run(
        config,
        backend or StubBackend(),
        tmp_path,
        run_id="20261111T000000Z",
        train_rows_cap=64,
        epochs_cap=1,
    )


def test_the_slot_matrix_is_the_pre_registered_design():
    slots = slot_matrix(RunConfig())

    per_target = {}
    for slot in slots:
        per_target.setdefault(slot.target.name, set()).add(slot.arm.name)
    assert per_target == {
        "claimnb": {"A_raw", "B_ft30", "B_ft10", "B_ft3", "X_log1p", "S_50k"},
        "severity": {"A_raw", "B_ft30", "B_ft10", "B_ft3", "S_50k"},
        "vehvalue": {"A_raw", "B_ft30", "B_ft10", "B_ft3", "S_50k"},
        "exposure": {"D_exposure"},
    }
    # 17 target-arm pairs x 5 folds x 3 model seeds.
    assert len(slots) == 17 * 5 * 3


def test_a_run_writes_a_v3_capture_the_reader_accepts(tmp_path):
    runs = _run(tmp_path)

    # One capture carries one dataset, so the fair test is one run per target.
    assert set(runs) == {"claimnb", "severity", "vehvalue", "exposure"}
    slots = 0
    for run_dir in runs.values():
        manifest = json.loads((run_dir / "capture.json").read_text())
        assert manifest["schema_version"] == 3
        verified = read_run(run_dir)
        slots += len(verified.slots)
        assert {slot.fold for slot in verified.slots} == {0}
    assert slots == 17  # 17 target-arm pairs x 1 fold x 1 seed


def test_every_slot_of_a_fold_shares_the_test_index(tmp_path):
    runs = _run(tmp_path)

    for run_dir in runs.values():
        verified = read_run(run_dir)
        by_fold = {}
        for slot in verified.slots:
            by_fold.setdefault(slot.fold, []).append(slot.test_index)
        for arrays in by_fold.values():
            assert all(np.array_equal(arrays[0], other) for other in arrays[1:])


def test_the_record_carries_the_four_v3_keys_and_provenance(tmp_path):
    run_dir = _run(tmp_path)["claimnb"]
    record = json.loads(
        (run_dir / "freMTPL2freq" / "B_ft30" / "seed0_fold0" / "meta.json").read_text()
    )

    for key in ("verdict_metric", "verdict_metric_value", "rmse", "quantile_levels"):
        assert record.get(key) is not None, key
    assert record["verdict_metric"] == "poisson_deviance"
    assert record["versions"]["tabpfn"] == "stub"
    assert record["weights"]["sha256"] == "a" * 64


def test_x_log1p_reports_counts_not_logs(tmp_path):
    """X_log1p fits on log1p and reports on the count scale, so it is comparable with A_raw."""
    config = RunConfig(folds=1, seeds=(0,), test_rows=256)
    run_dir = run(
        config,
        StubBackend(),
        tmp_path,
        run_id="20261111T000000Z",
        train_rows_cap=128,
        epochs_cap=1,
    )["claimnb"]
    _, raw_truth = load_frame(
        "freMTPL2freq", "ClaimNb", ("IDpol",), log_features=("Exposure",)
    )
    slot = run_dir / "freMTPL2freq" / "X_log1p" / "seed0_fold0"
    index = np.load(slot / "test_index.npy")
    stored = np.load(slot / "ground_truth.npy")
    record = json.loads((slot / "meta.json").read_text())

    # 256 rows guarantee some positives, so a log-scale truth would differ.
    assert stored.max() > 0
    assert stored == pytest.approx(raw_truth[index])
    assert record["reported_scale"] == "count"
    assert record["verdict_metric"] == "poisson_deviance"


def test_x_log1p_back_transforms_predictions_but_not_quantiles(tmp_path):
    config = RunConfig(folds=1, seeds=(0,), test_rows=16)
    run_dir = run(
        config,
        LargePredictionBackend(),
        tmp_path,
        run_id="20261111T000000Z",
        train_rows_cap=128,
        epochs_cap=1,
    )["claimnb"]
    slot = run_dir / "freMTPL2freq" / "X_log1p" / "seed0_fold0"
    record = json.loads((slot / "meta.json").read_text())

    # The fit predicted 5.0 on the log scale: counts are expm1(5), quantiles stay at 5.0.
    assert np.load(slot / "predictions.npy") == pytest.approx(np.expm1(5.0))
    assert np.load(slot / "quantiles.npy") == pytest.approx(np.full((9, 16), 5.0))
    assert record["quantile_scale"] == "log1p"


def test_non_finite_predictions_refuse(tmp_path):
    with pytest.raises(RuntimeError, match="non-finite"):
        _run(tmp_path, backend=NaNBackend())


def test_the_smoke_caps_are_the_epochs_and_rows_that_ran(tmp_path):
    run_dir = _run(tmp_path)["claimnb"]
    record = json.loads(
        (run_dir / "freMTPL2freq" / "B_ft30" / "seed0_fold0" / "meta.json").read_text()
    )

    assert record["epochs"] == 1  # epochs_cap
    assert record["train_rows"] == 64  # train_rows_cap


def test_the_arm_ladder_is_the_pre_registered_one():
    assert {name: arm.epochs for name, arm in ARMS.items()} == {
        "A_raw": 0,
        "B_ft30": 30,
        "B_ft10": 10,
        "B_ft3": 3,
        "X_log1p": 30,
        "S_50k": 30,
        "D_exposure": 0,
    }
    assert ARMS["S_50k"].train_rows == 50_000
    assert ARMS["X_log1p"].transform == "log1p"


def test_the_record_carries_the_split_and_the_dataset_fingerprint(tmp_path):
    run_dir = _run(tmp_path)["claimnb"]
    record = json.loads(
        (run_dir / "freMTPL2freq" / "A_raw" / "seed0_fold0" / "meta.json").read_text()
    )

    split = record["provenance"]["split"]
    assert split["n_folds"] == 1
    assert split["seed"] == 42
    assert split.get("sha256") is None  # the manifest carries the test-index hash
    assert split["rule"] == "holdout-80-20"
    dataset = record["provenance"]["dataset"]
    assert dataset["name"] == "freMTPL2freq"
    assert len(dataset["sha256"]) == 64
    assert record["fold_seed"] == 42
    assert record["log_features"] == ["Exposure"]


def test_the_cli_forwards_smoke_and_targets(tmp_path, monkeypatch):
    import importlib.util
    import sys

    script = Path(__file__).resolve().parents[1] / "scripts" / "run_fair_test.py"
    spec = importlib.util.spec_from_file_location("run_fair_test_cli", script)
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_fair_test_cli"] = module
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "TabPFNBackend", lambda **kwargs: StubBackend())

    code = module.main(
        ["--smoke", "--targets", "claimnb", "--out-root", str(tmp_path), "--run-id", "20261111T000000Z"]
    )

    assert code == 0
    run_dirs = sorted(path.name for path in tmp_path.iterdir() if path.is_dir())
    assert run_dirs == ["20261111T000000Z"], "only the selected target may be written"
    record = json.loads(
        (tmp_path / "20261111T000000Z" / "freMTPL2freq" / "B_ft30" / "seed0_fold0" / "meta.json").read_text()
    )
    assert record["epochs"] == 2  # the smoke cap, not the Arm's 30
    assert record["train_rows"] == 128
