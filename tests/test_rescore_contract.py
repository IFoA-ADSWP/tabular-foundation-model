"""Rescore reproduces what a run recorded, and refuses what it cannot verify.

Seam under test: the long-format CSV on disk, written by
`scripts/analyses/rescore.py --run <dir>`, and the refusals it exits with. The expected
recorded value is read from the run's own record, never recomputed here.
"""

from __future__ import annotations

import csv
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
ANCHOR = REPO / "results" / "20261031T021845Z"
SCRIPT = REPO / "scripts" / "analyses" / "rescore.py"

# Metric name -> the key its value holds in an arm's record.
RECORDED = {
    "auc": "roc_auc",
    "pr_auc": "pr_auc",
    "brier": "brier",
    "log_loss": "log_loss",
    "ece": "ece",
}


def _copy_anchor(tmp_path: Path, *, manifest: bool = False) -> Path:
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


def _record(run: Path, arm: str, seed: str) -> dict:
    return json.loads(
        (run / "uslapseagent" / arm / f"seed{seed}_foldNone" / "meta.json").read_text()
    )


def _rows(path: Path) -> list[dict]:
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def test_rescore_reproduces_the_recorded_five(tmp_path):
    run = _copy_anchor(tmp_path)
    out = tmp_path / "out"

    result = _cli("--run", str(run), "--out-dir", str(out))
    assert result.returncode == 0, result.stderr

    rows = _rows(out / f"{run.name}-rescore-recorded-five.csv")
    assert len(rows) == 4 * 2 * 5
    assert {row["metric"] for row in rows} == set(RECORDED)
    for row in rows:
        recorded = _record(run, row["arm"], row["seed"])
        expected = recorded[RECORDED[row["metric"]]]
        assert row["recorded_value"] == repr(expected)
        assert row["agrees"] == "true"
        assert math.isclose(
            float(row["value"]), expected, rel_tol=1e-6, abs_tol=1e-9
        ), (row, expected)
        # The row is traceable to the bytes, not just to a run id.
        assert row["capture_sha"] == recorded["predictions_sha256"]
        assert row["source"] == "record"
        assert row["metric_version"] == "1"


def test_rescore_with_a_manifest_verifies_against_both_hashes(tmp_path):
    run = _copy_anchor(tmp_path, manifest=True)
    out = tmp_path / "out"
    manifest = json.loads((run / "capture.json").read_text())
    by_slot = {(c["arm"], c["seed"]): c for c in manifest["captures"]}

    result = _cli("--run", str(run), "--out-dir", str(out))
    assert result.returncode == 0, result.stderr

    rows = _rows(out / f"{run.name}-rescore-recorded-five.csv")
    assert len(rows) == 40
    for row in rows:
        assert row["source"] == "capture.json"
        assert row["capture_sha"] == by_slot[(row["arm"], int(row["seed"]))]["predictions_sha256"]
        assert row["agrees"] == "true"


def test_a_mutated_array_refuses_and_names_both_hashes(tmp_path):
    run = _copy_anchor(tmp_path)
    slot = run / "uslapseagent" / "A_raw" / "seed43_foldNone"
    record = _record(run, "A_raw", "43")
    predictions = np.load(slot / "predictions.npy")
    np.save(slot / "predictions.npy", predictions + np.float32(1e-6))

    result = _cli("--run", str(run), "--out-dir", str(tmp_path / "out"))

    assert result.returncode == 1
    assert "hash mismatch" in result.stderr
    assert record["predictions_sha256"] in result.stderr
    assert "predictions.npy" in result.stderr


def test_a_mutated_array_refuses_against_the_manifest_too(tmp_path):
    run = _copy_anchor(tmp_path, manifest=True)
    slot = run / "uslapseagent" / "A_raw" / "seed43_foldNone"
    manifest = json.loads((run / "capture.json").read_text())
    entry = next(
        c for c in manifest["captures"] if (c["arm"], c["seed"]) == ("A_raw", 43)
    )
    predictions = np.load(slot / "predictions.npy")
    np.save(slot / "predictions.npy", predictions + np.float32(1e-6))

    result = _cli("--run", str(run), "--out-dir", str(tmp_path / "out"))

    assert result.returncode == 1
    assert entry["predictions_sha256"] in result.stderr
    assert "hash mismatch" in result.stderr


def test_an_unknown_metric_name_refuses_and_lists_the_known_ones(tmp_path):
    run = _copy_anchor(tmp_path)

    result = _cli("--run", str(run), "--metric", "f1", "--out-dir", str(tmp_path / "out"))

    assert result.returncode == 1
    assert "unknown metric 'f1'" in result.stderr
    assert "auc" in result.stderr


def test_an_unknown_metric_version_refuses_and_names_the_known_version(tmp_path):
    run = _copy_anchor(tmp_path)

    result = _cli("--run", str(run), "--metric", "auc@2", "--out-dir", str(tmp_path / "out"))

    assert result.returncode == 1
    assert "no version '2'" in result.stderr
    assert "known versions: 1" in result.stderr


def test_an_explicit_metric_set_names_its_own_file(tmp_path):
    run = _copy_anchor(tmp_path)
    out = tmp_path / "out"

    result = _cli("--run", str(run), "--metric", "ece@1", "--out-dir", str(out))

    assert result.returncode == 0, result.stderr
    rows = _rows(out / f"{run.name}-rescore-ece-1.csv")
    assert {row["metric"] for row in rows} == {"ece"}
    assert {(row["arm"], row["seed"]) for row in rows} == {
        (arm, str(seed))
        for arm in ("A_raw", "B_ft3", "B_ft10", "B_ft30")
        for seed in (43, 44)
    }


def test_rerunning_produces_identical_bytes(tmp_path):
    run = _copy_anchor(tmp_path)
    out = tmp_path / "out"

    assert _cli("--run", str(run), "--out-dir", str(out)).returncode == 0
    first = (out / f"{run.name}-rescore-recorded-five.csv").read_bytes()
    assert _cli("--run", str(run), "--out-dir", str(out)).returncode == 0

    assert (out / f"{run.name}-rescore-recorded-five.csv").read_bytes() == first
