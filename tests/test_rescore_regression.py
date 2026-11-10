"""Rescore computes the regression set, and a folded capture is readable (#538).

Seam under test: the CSV on disk written by `scripts/analyses/rescore.py --metric-set
regression`, and the `fold` column that lets a five-fold run be rescor ed at all.
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

import metrics
from provenance import sha256_array
from run_capture import build_capture, render_capture

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "analyses" / "rescore.py"


def _run(tmp_path: Path, *, verdict_metric: str = "poisson_deviance") -> Path:
    run = tmp_path / "20261110T000000Z"
    truth = np.array([0.0, 1.0, 2.0, 0.0])
    predictions = np.array([0.2, 0.8, 1.5, 0.4])
    for fold in (0, 1):
        slot = run / "freMTPL2freq" / "B_ft30" / f"seed0_fold{fold}"
        slot.mkdir(parents=True)
        np.save(slot / "predictions.npy", predictions)
        np.save(slot / "ground_truth.npy", truth)
        np.save(slot / "test_index.npy", np.array([100, 101, 102, 103], dtype=np.int64))
        np.save(slot / "quantiles.npy", np.tile(predictions, (9, 1)))
        np.save(slot / "exposure.npy", np.ones(4))
        verdict_value = (
            metrics.poisson_deviance(truth, predictions)
            if verdict_metric == "poisson_deviance"
            else metrics.rmse(truth, predictions)
        )
        (slot / "meta.json").write_text(
            json.dumps(
                {
                    "arm": "B_ft30",
                    "seed": 0,
                    "fold": fold,
                    "test_rows": 4,
                    "predictions_sha256": sha256_array(predictions),
                    "verdict_metric": verdict_metric,
                    "verdict_metric_value": verdict_value,
                    "rmse": metrics.rmse(truth, predictions),
                    "quantile_levels": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
                }
            )
        )
    (run / "capture.json").write_text(render_capture(build_capture(run)))
    return run


def _cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, cwd=REPO
    )


def _rows(path: Path) -> list[dict]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def test_a_folded_capture_is_readable_and_the_rows_carry_the_fold(tmp_path):
    run = _run(tmp_path)
    out = tmp_path / "out"

    result = _cli("--run", str(run), "--metric-set", "regression", "--out-dir", str(out))
    assert result.returncode == 0, result.stderr

    rows = _rows(out / f"{run.name}-rescore-regression.csv")
    assert len(rows) == 2 * 6  # two folds x six metrics
    assert [row["fold"] for row in rows] == ["0", "0", "0", "0", "0", "0", "1", "1", "1", "1", "1", "1"]
    assert {row["metric"] for row in rows} == {
        "rmse",
        "mae",
        "medae",
        "rmsle",
        "poisson_deviance",
        "gini",
    }


def test_the_verdict_metric_agrees_and_the_others_have_no_recorded_value(tmp_path):
    run = _run(tmp_path)
    out = tmp_path / "out"

    assert _cli("--run", str(run), "--metric-set", "regression", "--out-dir", str(out)).returncode == 0
    rows = _rows(out / f"{run.name}-rescore-regression.csv")

    deviance = [row for row in rows if row["metric"] == "poisson_deviance"]
    assert all(row["agrees"] == "true" for row in deviance)
    assert all(row["recorded_value"] != "" for row in deviance)

    mae = [row for row in rows if row["metric"] == "mae"]
    assert all(row["recorded_value"] == "" for row in mae)
    assert all(row["agrees"] == "" for row in mae)


def test_a_rate_metric_is_not_read_from_the_verdict_value(tmp_path):
    """The name must match: a severity run records RMSE, not a deviance."""
    run = _run(tmp_path, verdict_metric="rmse")
    out = tmp_path / "out"

    assert _cli("--run", str(run), "--metric-set", "regression", "--out-dir", str(out)).returncode == 0
    rows = _rows(out / f"{run.name}-rescore-regression.csv")

    deviance = [row for row in rows if row["metric"] == "poisson_deviance"]
    assert all(row["recorded_value"] == "" for row in deviance)
    rmse = [row for row in rows if row["metric"] == "rmse"]
    assert all(row["agrees"] == "true" for row in rmse)
