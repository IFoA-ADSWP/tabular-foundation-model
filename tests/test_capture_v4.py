"""Capture v4: the weight and cluster id that grouped severity needs (#555).

A v4 capture is v3 plus two arrays. The point of this file is that neither can become decoration:
a severity slot without them is refused, a frequency slot that carries them is refused, and a
changed weight fails the hash check.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from capture_reader import read_run
from run_capture import CaptureRefused, build_capture, render_capture


def _slot(
    run: Path,
    *,
    fold: int,
    dataset: str = "spanish_motor_severity",
    task: str = "severity",
    weights: bool = True,
    cluster: bool = True,
    cluster_dtype=np.int64,
) -> Path:
    slot = run / dataset / "A_raw" / f"seed0_fold{fold}"
    slot.mkdir(parents=True)
    predictions = np.array([0.1, 0.2, 0.3])
    np.save(slot / "predictions.npy", predictions)
    np.save(slot / "ground_truth.npy", np.array([0.0, 0.5, 1.0]))
    np.save(slot / "test_index.npy", np.array([10, 11, 12], dtype=np.int64))
    np.save(slot / "quantiles.npy", np.tile(predictions, (9, 1)))
    if weights:
        np.save(slot / "weights.npy", np.array([1.0, 2.0, 4.0]))
    if cluster is not None:
        np.save(slot / "cluster_id.npy", np.array([0, 0, 1], dtype=cluster_dtype))
    (slot / "meta.json").write_text(
        json.dumps(
            {
                "arm": "A_raw",
                "seed": 0,
                "fold": fold,
                "task": task,
                "test_rows": 3,
                "predictions_sha256": __import__("provenance").sha256_array(predictions),
                "verdict_metric": "rmse",
                "verdict_metric_value": 1.0,
                "quantile_levels": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
            }
        )
    )
    return slot


def _run(tmp_path: Path, **kwargs) -> Path:
    run = tmp_path / "20261112T000000Z"
    for fold in (0, 1):
        _slot(run, fold=fold, **kwargs)
    (run / "capture.json").write_text(render_capture(build_capture(run)))
    return run


def test_a_v4_capture_reads_the_weight_and_the_cluster(tmp_path):
    run = _run(tmp_path)

    assert json.loads((run / "capture.json").read_text())["schema_version"] == 4
    verified = read_run(run)

    slot = verified.slots[0]
    assert slot.weights == pytest.approx([1.0, 2.0, 4.0])
    assert slot.cluster.tolist() == [0, 0, 1]


def test_a_severity_slot_without_weights_is_refused(tmp_path):
    run = tmp_path / "20261112T000000Z"
    _slot(run, fold=0, weights=False)

    with pytest.raises(CaptureRefused, match="weights.npy"):
        build_capture(run)


def test_a_frequency_slot_carrying_weights_is_refused(tmp_path):
    """The arrays are for grouped severity; a frequency slot carrying them is a control that lies."""
    run = tmp_path / "20261112T000000Z"
    _slot(run, fold=0, dataset="spanish_motor_freq", task="frequency")

    with pytest.raises(CaptureRefused, match="severity only"):
        build_capture(run)


def test_a_changed_weight_fails_the_hash(tmp_path):
    run = _run(tmp_path)
    slot = run / "spanish_motor_severity" / "A_raw" / "seed0_fold0"
    np.save(slot / "weights.npy", np.array([9.0, 9.0, 9.0]))

    with pytest.raises(CaptureRefused, match="hash mismatch"):
        read_run(run)


def test_a_float_cluster_id_is_refused(tmp_path):
    run = tmp_path / "20261112T000000Z"
    _slot(run, fold=0, cluster_dtype=np.float64)

    with pytest.raises(CaptureRefused, match="int64"):
        build_capture(run)
