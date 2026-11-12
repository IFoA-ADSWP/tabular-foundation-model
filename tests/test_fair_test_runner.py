"""The fair-test runner writes the pre-registered matrix and a readable capture (#555).

Seam under test: the run directory on disk and the manifest `read_run` accepts. The model is
stubbed — these tests are about the loop, the grouped folds, the shared test rows and the record,
not about TabPFN.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from capture_reader import read_run
from fair_test_runner import ARMS, RunConfig, run, slot_matrix
from freq_sev_data import TARGETS

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


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
        "frequency_french": {"A_raw", "B_ft30", "B_ft10", "B_ft3"},
        "frequency_spanish": {"A_raw", "B_ft30", "B_ft10", "B_ft3"},
        "severity_french": {"A_raw", "B_ft30", "B_ft10", "B_ft3"},
        "severity_spanish": {"A_raw", "B_ft30", "B_ft10", "B_ft3"},
    }
    assert len(slots) == 4 * 4 * 5 * 3  # targets x arms x folds x model seeds


def test_a_run_writes_one_capture_per_target_the_reader_accepts(tmp_path):
    runs = _run(tmp_path)

    assert set(runs) == {spec.name for spec in TARGETS}
    for name, run_dir in runs.items():
        manifest = json.loads((run_dir / "capture.json").read_text())
        expected = 4 if name.startswith("severity") else 3
        assert manifest["schema_version"] == expected, name
        verified = read_run(run_dir)
        assert len(verified.slots) == 4  # four Arms x one fold x one seed


def test_every_slot_of_a_fold_shares_the_test_index(tmp_path):
    for run_dir in _run(tmp_path).values():
        verified = read_run(run_dir)
        by_fold = {}
        for slot in verified.slots:
            by_fold.setdefault(slot.fold, []).append(slot.test_index)
        for arrays in by_fold.values():
            assert all(np.array_equal(arrays[0], other) for other in arrays[1:])


def test_french_severity_is_stored_on_the_log_scale(tmp_path):
    """The metric is RMSE of log(amount); the slot's truth is the log, not the amount."""
    run_dir = _run(tmp_path)["severity_french"]
    slot = run_dir / "freMTPL2sev" / "B_ft30" / "seed0_fold0"
    index = np.load(slot / "test_index.npy")
    truth = np.load(slot / "ground_truth.npy")
    amounts = pd.read_csv(RAW / "freMTPL2sev.csv")["ClaimAmount"].to_numpy()

    assert truth == pytest.approx(np.log(amounts[index]))
    record = json.loads((slot / "meta.json").read_text())
    assert record["task"] == "severity"
    assert record["unit"] == "claim"
    assert record["reported_scale"] == "log"
    assert record["verdict_metric"] == "rmse"


def test_a_severity_slot_carries_the_weight_and_the_cluster(tmp_path):
    run_dir = _run(tmp_path)["severity_spanish"]
    slot = run_dir / "spanish_motor_severity" / "A_raw" / "seed0_fold0"
    index = np.load(slot / "test_index.npy")
    weights = np.load(slot / "weights.npy")
    cluster = np.load(slot / "cluster_id.npy")
    frequency = pd.read_csv(RAW / "spanish_motor_freq.csv")
    counts = frequency.loc[frequency["N_claims_year"] > 0, "N_claims_year"].to_numpy()
    record = json.loads((slot / "meta.json").read_text())

    assert weights == pytest.approx(counts[index])
    assert cluster.dtype == np.int64
    assert record["weighted"] is True
    assert record["unit"] == "claiming_policy"
    assert record["verdict_metric"] == "weighted_rmse"


def test_a_frequency_slot_carries_no_weight_or_cluster(tmp_path):
    run_dir = _run(tmp_path)["frequency_french"]
    slot = run_dir / "freMTPL2freq" / "A_raw" / "seed0_fold0"

    assert not (slot / "weights.npy").exists()
    assert not (slot / "cluster_id.npy").exists()
    assert (slot / "exposure.npy").exists(), "French frequency retains its exposure"


def test_the_french_severity_dataset_block_names_both_files(tmp_path):
    run_dir = _run(tmp_path)["severity_french"]
    record = json.loads(
        (run_dir / "freMTPL2sev" / "A_raw" / "seed0_fold0" / "meta.json").read_text()
    )
    dataset = record["provenance"]["dataset"]

    assert dataset["name"] == "freMTPL2sev"
    assert [entry["name"] for entry in dataset["files"]] == ["freMTPL2sev.csv", "freMTPL2freq.csv"]
    assert dataset["join_key"] == "IDpol"
    assert len(dataset["sha256"]) == 64


def test_non_finite_predictions_refuse(tmp_path):
    with pytest.raises(RuntimeError, match="non-finite"):
        _run(tmp_path, backend=NaNBackend())


def test_the_arm_ladder_is_the_pre_registered_one():
    assert {name: arm.epochs for name, arm in ARMS.items()} == {
        "A_raw": 0,
        "B_ft30": 30,
        "B_ft10": 10,
        "B_ft3": 3,
    }


def test_the_smoke_caps_are_the_epochs_and_rows_that_ran(tmp_path):
    run_dir = _run(tmp_path)["frequency_french"]
    record = json.loads(
        (run_dir / "freMTPL2freq" / "B_ft30" / "seed0_fold0" / "meta.json").read_text()
    )

    assert record["epochs"] == 1  # epochs_cap
    assert record["train_rows"] == 64  # train_rows_cap


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
        [
            "--smoke",
            "--targets",
            "frequency_french",
            "--out-root",
            str(tmp_path),
            "--run-id",
            "20261111T000000Z",
        ]
    )

    assert code == 0
    run_dirs = sorted(path.name for path in tmp_path.iterdir() if path.is_dir())
    assert run_dirs == ["20261111T000000Z"], "only the selected target may be written"
    record = json.loads(
        (tmp_path / "20261111T000000Z" / "freMTPL2freq" / "B_ft30" / "seed0_fold0" / "meta.json")
        .read_text()
    )
    assert record["epochs"] == 2  # the smoke cap, not the Arm's 30
    assert record["train_rows"] == 128


def test_the_gate_summary_is_the_paired_fold_level_mde(tmp_path):
    """The gate measures mean_f SD_fold(r), with r averaged over seeds inside a fold."""
    from fair_test_runner import gate_summary

    run_dir = tmp_path / "20261112T000000Z"
    raw = {
        0: (100.0, 102.0),
        1: (101.0, 103.0),
        2: (99.0, 100.0),
        3: (100.5, 101.5),
        4: (99.5, 98.5),
    }
    fine = {
        0: (98.0, 100.0),
        1: (99.5, 101.0),
        2: (98.0, 99.0),
        3: (99.0, 100.0),
        4: (97.5, 97.0),
    }
    for arm, values in (("A_raw", raw), ("B_ft30", fine)):
        for fold, seed_values in values.items():
            for seed, value in enumerate(seed_values):
                slot = run_dir / "freMTPL2freq" / arm / f"seed{seed}_fold{fold}"
                slot.mkdir(parents=True)
                (slot / "meta.json").write_text(
                    json.dumps(
                        {"fold": fold, "seed": seed, "verdict_metric_value": value}
                    )
                )

    row = gate_summary({"frequency_french": run_dir})["frequency_french"]
    per_fold = [
        float(np.mean([(raw[fold][seed] - fine[fold][seed]) / raw[fold][seed] for seed in (0, 1)]))
        for fold in raw
    ]

    assert row["folds"] == 5
    assert row["seeds_per_fold"] == 2
    assert row["mean_improvement"] == pytest.approx(float(np.mean(per_fold)))
    assert row["sd_r"] == pytest.approx(float(np.std(per_fold, ddof=1)))
    assert row["mde"] == pytest.approx(2.8016 * float(np.std(per_fold, ddof=1)) / np.sqrt(5))


def test_a_gate_without_the_treatment_arm_refuses(tmp_path):
    """A paired MDE needs both Arms; one alone is the gate this replaced."""
    from fair_test_runner import gate_summary

    run_dir = tmp_path / "20261112T000000Z"
    for fold in range(5):
        slot = run_dir / "freMTPL2freq" / "A_raw" / f"seed0_fold{fold}"
        slot.mkdir(parents=True)
        (slot / "meta.json").write_text(
            json.dumps({"fold": fold, "seed": 0, "verdict_metric_value": 100.0})
        )

    with pytest.raises(ValueError, match="no fold with both"):
        gate_summary({"frequency_french": run_dir})


def _cli(monkeypatch):
    import importlib.util
    import sys

    script = Path(__file__).resolve().parents[1] / "scripts" / "run_fair_test.py"
    spec = importlib.util.spec_from_file_location("run_fair_test_cli_arms", script)
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_fair_test_cli_arms"] = module
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "TabPFNBackend", lambda **kwargs: StubBackend())
    return module


def test_the_cli_runs_only_the_arms_it_was_given(tmp_path, monkeypatch):
    """The fair test is authorised for the primary pair (#564); the ladder is not run by default."""
    module = _cli(monkeypatch)

    code = module.main(
        [
            "--smoke",
            "--targets",
            "frequency_french",
            "--arms",
            "A_raw,B_ft30",
            "--out-root",
            str(tmp_path),
            "--run-id",
            "20261112T000000Z",
        ]
    )

    assert code == 0
    arms = sorted(
        path.name for path in (tmp_path / "20261112T000000Z" / "freMTPL2freq").iterdir()
    )
    assert arms == ["A_raw", "B_ft30"]


def test_the_cli_refuses_an_unknown_arm(tmp_path, monkeypatch):
    module = _cli(monkeypatch)

    with pytest.raises(SystemExit) as refused:
        module.main(["--smoke", "--arms", "A_raw,B_ft99", "--out-root", str(tmp_path)])

    assert refused.value.code == 2


def test_the_run_id_offset_keeps_the_runners_id_scheme(tmp_path, monkeypatch):
    """One process per target needs distinct ids; the offset is seconds, as `_run_ids` does."""
    module = _cli(monkeypatch)

    code = module.main(
        [
            "--smoke",
            "--targets",
            "frequency_french",
            "--arms",
            "A_raw",
            "--out-root",
            str(tmp_path),
            "--run-id",
            "20261112T000000Z",
            "--run-id-offset",
            "3",
        ]
    )

    assert code == 0
    assert [path.name for path in tmp_path.iterdir() if path.is_dir()] == ["20261112T000003Z"]
