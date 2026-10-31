"""A run's predictions as one table a colleague can open, without our code (#387).

Seam under test: the CSV on disk. Every expectation is read from the arrays and the manifest,
never from the exporter's own helpers.
"""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
ANCHOR = REPO / "results" / "20261031T021845Z"
SCRIPT = REPO / "scripts" / "analyses" / "export_predictions.py"
COMMITTED = REPO / "docs" / "analyses" / "data" / f"{ANCHOR.name}-predictions.csv"

COLUMNS = [
    "run_id",
    "dataset",
    "arm",
    "seed",
    "row",
    "y_true",
    "probability",
    "capture_sha",
    "source",
]

ARMS = ("A_raw", "B_ft3", "B_ft10", "B_ft30")
SEEDS = (43, 44)


def _copy_anchor(tmp_path: Path, *, manifest: bool = True) -> Path:
    run = tmp_path / ANCHOR.name
    shutil.copytree(ANCHOR / "uslapseagent", run / "uslapseagent")
    if manifest:
        shutil.copy(ANCHOR / "capture.json", run / "capture.json")
    return run


def _cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=REPO,
    )


def _rows(path: Path) -> list[dict]:
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def _slot(run: Path, arm: str, seed: int) -> Path:
    return run / "uslapseagent" / arm / f"seed{seed}_foldNone"


def test_the_anchor_predictions_are_one_row_per_prediction(tmp_path):
    run = _copy_anchor(tmp_path)
    out = tmp_path / "out"
    manifest = json.loads((run / "capture.json").read_text())
    hashes = {(c["arm"], c["seed"]): c["predictions_sha256"] for c in manifest["captures"]}

    result = _cli("--run", str(run), "--out-dir", str(out))
    assert result.returncode == 0, result.stderr

    rows = _rows(out / f"{run.name}-predictions.csv")
    assert len(rows) == len(ARMS) * len(SEEDS) * 1000
    assert list(rows[0]) == COLUMNS

    for row in rows:
        arm, seed = row["arm"], int(row["seed"])
        slot = _slot(run, arm, seed)
        predictions = np.load(slot / "predictions.npy")
        truth = np.load(slot / "ground_truth.npy")
        i = int(row["row"])
        assert row["run_id"] == run.name
        assert row["dataset"] == "uslapseagent"
        assert float(row["probability"]) == float(predictions[i])
        assert int(row["y_true"]) == int(truth[i])
        assert row["capture_sha"] == hashes[(arm, seed)]
        assert row["source"] == "capture.json"


def test_a_mutated_array_refuses_before_a_table_is_written(tmp_path):
    run = _copy_anchor(tmp_path)
    slot = _slot(run, "A_raw", 43)
    truth = np.load(slot / "ground_truth.npy")
    np.save(slot / "ground_truth.npy", np.float32(1.0) - truth)
    out = tmp_path / "out"

    result = _cli("--run", str(run), "--out-dir", str(out))

    assert result.returncode == 1
    assert "ground_truth.npy" in result.stderr
    assert not (out / f"{run.name}-predictions.csv").exists()


def test_two_runs_of_the_command_produce_identical_bytes(tmp_path):
    run = _copy_anchor(tmp_path)
    out = tmp_path / "out"
    target = out / f"{run.name}-predictions.csv"

    assert _cli("--run", str(run), "--out-dir", str(out)).returncode == 0
    first = target.read_bytes()
    assert _cli("--run", str(run), "--out-dir", str(out)).returncode == 0

    assert target.read_bytes() == first


def test_the_committed_table_matches_the_arrays():
    """The committed CSV is the colleague-facing artifact; it must not drift from the arrays."""
    rows = _rows(COMMITTED)
    assert len(rows) == len(ARMS) * len(SEEDS) * 1000

    for row in rows:
        slot = _slot(ANCHOR, row["arm"], int(row["seed"]))
        i = int(row["row"])
        assert float(row["probability"]) == float(np.load(slot / "predictions.npy")[i])
        assert int(row["y_true"]) == int(np.load(slot / "ground_truth.npy")[i])
