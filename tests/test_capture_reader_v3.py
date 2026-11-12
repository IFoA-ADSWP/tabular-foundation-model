"""The capture reader accepts every schema and refuses a tampered v3 array (#538).

Seam under test: `capture_reader.read_run`, the function rescore and the export both use. A v3
array is only evidence if a changed byte refuses, so the tamper cases are the point of the file.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from capture_reader import read_run
from run_capture import CaptureRefused, build_capture, render_capture


def _slot(run: Path, *, fold: int, dataset: str = "freMTPL2freq", arrays: bool = True) -> Path:
    slot = run / dataset / "B_ft30" / f"seed0_fold{fold}"
    slot.mkdir(parents=True)
    predictions = np.array([0.1, 0.2, 0.3])
    np.save(slot / "predictions.npy", predictions)
    np.save(slot / "ground_truth.npy", np.array([0.0, 0.0, 1.0]))
    if arrays:
        np.save(slot / "test_index.npy", np.array([10, 11, 12], dtype=np.int64))
        np.save(slot / "quantiles.npy", np.tile(predictions, (9, 1)))
        if dataset == "freMTPL2freq":
            np.save(slot / "exposure.npy", np.ones(3))
    (slot / "meta.json").write_text(
        json.dumps(
            {
                "arm": "B_ft30",
                "seed": 0,
                "fold": fold,
                "test_rows": 3,
                "predictions_sha256": __import__("provenance").sha256_array(predictions),
                "verdict_metric": "poisson_deviance",
                "verdict_metric_value": 1.0,
                "rmse": 0.5,
                "quantile_levels": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
            }
        )
    )
    return slot


def _run(tmp_path: Path, *, arrays: bool = True, folds: tuple[int, ...] = (0, 1)) -> Path:
    run = tmp_path / "20261110T000000Z"
    for fold in folds:
        _slot(run, fold=fold, arrays=arrays)
    (run / "capture.json").write_text(render_capture(build_capture(run)))
    return run


def test_a_v2_folded_capture_is_readable_with_its_fold(tmp_path):
    """The folded v2 capture shipped in #501 was unreadable; this pins the fix."""
    run = _run(tmp_path, arrays=False)

    assert json.loads((run / "capture.json").read_text())["schema_version"] == 2
    verified = read_run(run)

    assert [slot.fold for slot in verified.slots] == [0, 1]


def test_a_v3_capture_reads_the_arrays_and_the_fold(tmp_path):
    run = _run(tmp_path)
    verified = read_run(run)

    slot = verified.slots[0]
    assert slot.fold == 0
    assert slot.test_index.tolist() == [10, 11, 12]
    assert slot.quantiles.shape == (9, 3)
    assert slot.exposure.tolist() == [1.0, 1.0, 1.0]


@pytest.mark.parametrize("array_name", ["test_index.npy", "quantiles.npy", "exposure.npy"])
def test_a_tampered_v3_array_refuses(tmp_path, array_name):
    run = _run(tmp_path)
    path = run / "freMTPL2freq" / "B_ft30" / "seed0_fold0" / array_name
    array = np.load(path)
    np.save(path, array + (1 if array.dtype == np.int64 else 0.5))

    with pytest.raises(CaptureRefused, match="hash mismatch"):
        read_run(run)


def test_a_v3_entry_missing_a_hash_refuses(tmp_path):
    run = _run(tmp_path)
    manifest_path = run / "capture.json"
    manifest = json.loads(manifest_path.read_text())
    del manifest["captures"][0]["quantiles_sha256"]
    manifest_path.write_text(json.dumps(manifest))

    with pytest.raises(CaptureRefused, match="quantiles_sha256"):
        read_run(run)


def test_a_v3_fremtpl2freq_slot_without_exposure_refuses(tmp_path):
    run = _run(tmp_path)
    (run / "freMTPL2freq" / "B_ft30" / "seed0_fold0" / "exposure.npy").unlink()

    with pytest.raises(CaptureRefused, match="exposure.npy"):
        read_run(run)


def test_an_unknown_schema_version_refuses(tmp_path):
    run = _run(tmp_path)
    manifest = json.loads((run / "capture.json").read_text())
    manifest["schema_version"] = 4
    (run / "capture.json").write_text(json.dumps(manifest))

    with pytest.raises(CaptureRefused, match="unknown capture schema_version"):
        read_run(run)
