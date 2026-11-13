"""Capture v5: the method axis, and quantiles only where a method has them (#597).

The point of the version is that a GLM has no honest predictive distribution. A manifest that
demanded nine quantile rows would force the runner to emit the mean nine times and call it a
distribution, so v5 makes the array optional — and makes the record's declaration, not the file's
presence, the thing that decides whether it is owed.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from capture_reader import read_run
from provenance import sha256_array
from run_capture import CaptureRefused, build_capture, render_capture


def _slot(
    run: Path,
    *,
    fold: int,
    method: str = "E_glm",
    arm: str | None = None,
    quantiles: bool = False,
    declare_quantiles: bool | None = None,
) -> Path:
    """One v5 slot. The directory is named after the method for a baseline, as the runner writes it."""
    label = arm or method
    slot = run / "freMTPL2freq" / label / f"seed0_fold{fold}"
    slot.mkdir(parents=True)
    predictions = np.array([0.4, 0.5, 0.6])
    np.save(slot / "predictions.npy", predictions)
    np.save(slot / "ground_truth.npy", np.array([0.0, 1.0, 0.0]))
    np.save(slot / "test_index.npy", np.array([10, 11, 12], dtype=np.int64))
    np.save(slot / "exposure.npy", np.array([0.5, 1.0, 0.25]))
    if quantiles:
        np.save(slot / "quantiles.npy", np.tile(predictions, (9, 1)))
    levels = (
        [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9] if quantiles else None
    )
    if declare_quantiles is not None:
        levels = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9] if declare_quantiles else None
    (slot / "meta.json").write_text(
        json.dumps(
            {
                "method": method,
                "arm": arm,
                "seed": 0,
                "fold": fold,
                "task": "frequency",
                "test_rows": 3,
                "predictions_sha256": sha256_array(predictions),
                "verdict_metric": "poisson_deviance",
                "verdict_metric_value": 1.0,
                "rmse": 0.5,
                "quantile_levels": levels,
                "versions": {"numpy": np.__version__, "python": "3.12"},
            }
        )
    )
    return slot


def _run(tmp_path: Path, *, quantify: bool = False, **kwargs) -> Path:
    run = tmp_path / "20261113T000000Z"
    for fold in (0, 1):
        _slot(run, fold=fold, **kwargs)
    (run / "capture.json").write_text(render_capture(build_capture(run)))
    return run


def test_a_baseline_capture_reads_without_quantiles(tmp_path):
    run = _run(tmp_path)

    manifest = json.loads((run / "capture.json").read_text())
    assert manifest["schema_version"] == 5
    assert manifest["captures"][0]["method"] == "E_glm"
    assert manifest["captures"][0]["arm"] is None
    assert "quantiles_sha256" not in manifest["captures"][0]

    verified = read_run(run)
    assert {slot.method for slot in verified.slots} == {"E_glm"}
    assert all(slot.quantiles is None for slot in verified.slots)
    assert all(slot.arm is None for slot in verified.slots)


def test_a_tabpfn_capture_keeps_its_quantiles_and_its_arm(tmp_path):
    run = _run(tmp_path, method="tabpfn", arm="A_raw", quantiles=True)
    record = json.loads(
        (run / "freMTPL2freq" / "A_raw" / "seed0_fold0" / "meta.json").read_text()
    )
    record["versions"] = {"tabpfn": "8.5.0", "python": "3.12"}
    record["weights"] = {"path": "/cache/checkpoint.ckpt", "sha256": "c" * 64}
    (run / "freMTPL2freq" / "A_raw" / "seed0_fold0" / "meta.json").write_text(json.dumps(record))
    (run / "capture.json").write_text(render_capture(build_capture(run)))

    verified = read_run(run)
    assert verified.slots[0].method == "tabpfn"
    assert verified.slots[0].arm == "A_raw"
    assert verified.slots[0].quantiles is not None


def test_quantiles_declared_but_missing_are_refused(tmp_path):
    run = tmp_path / "20261113T000000Z"
    _slot(run, fold=0, method="tabpfn", arm="A_raw", quantiles=False, declare_quantiles=True)

    with pytest.raises(CaptureRefused, match="quantiles.npy"):
        build_capture(run)


def test_quantiles_present_but_undeclared_are_refused(tmp_path):
    """A mean repeated nine times must not pass as a distribution."""
    run = tmp_path / "20261113T000000Z"
    _slot(run, fold=0, quantiles=True, declare_quantiles=False)

    with pytest.raises(CaptureRefused, match="declares no quantile_levels"):
        build_capture(run)


def test_a_run_that_mixes_a_method_record_with_a_legacy_one_is_refused(tmp_path):
    run = tmp_path / "20261113T000000Z"
    _slot(run, fold=0)
    legacy = _slot(run, fold=1, method="tabpfn", arm="A_raw", quantiles=True)
    record = json.loads((legacy / "meta.json").read_text())
    del record["method"]
    (legacy / "meta.json").write_text(json.dumps(record))

    with pytest.raises(CaptureRefused, match="method axis is recorded for the whole run"):
        build_capture(run)


def test_a_method_run_without_folds_is_refused(tmp_path):
    run = tmp_path / "20261113T000000Z"
    slot = run / "freMTPL2freq" / "E_glm" / "seed0_foldNone"
    _slot(run, fold=0)
    (run / "freMTPL2freq" / "E_glm" / "seed0_fold0").rename(slot)

    with pytest.raises(CaptureRefused, match="foldless"):
        build_capture(run)


def test_the_reader_refuses_an_unhashed_quantiles_array(tmp_path):
    """A file the manifest never names is not evidence; it is an unverified claim."""
    run = _run(tmp_path)
    np.save(
        run / "freMTPL2freq" / "E_glm" / "seed0_fold0" / "quantiles.npy",
        np.zeros((9, 3)),
    )

    with pytest.raises(CaptureRefused, match="unverified distribution"):
        read_run(run)
