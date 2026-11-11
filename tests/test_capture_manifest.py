"""The capture generator writes one manifest per run, and says what was not retained.

Seam under test: `capture.json` on disk, produced by
`scripts/analyses/make_capture.py --run <dir>`. The expectations are computed here from the
arrays the test loads, never from the generator's own helper.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
ANCHOR = REPO / "results" / "20261031T021845Z"
SCRIPT = REPO / "scripts" / "analyses" / "make_capture.py"


def _copy_anchor(tmp_path: Path) -> Path:
    """A writable copy of the committed anchor: tests must not write into `results/`."""
    run = tmp_path / ANCHOR.name
    shutil.copytree(ANCHOR / "uslapseagent", run / "uslapseagent")
    return run


def _cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=REPO,
    )


def _array_sha256(path: Path) -> str:
    return hashlib.sha256(np.load(path).tobytes()).hexdigest()


def test_the_anchor_manifest_covers_every_arm_and_seed(tmp_path):
    run = _copy_anchor(tmp_path)

    result = _cli("--run", str(run))
    assert result.returncode == 0, result.stderr

    manifest = json.loads((run / "capture.json").read_text())
    assert manifest["schema_version"] == 1
    assert manifest["run_id"] == ANCHOR.name
    assert manifest["dataset"] == "uslapseagent"

    captures = {(c["arm"], c["seed"]): c for c in manifest["captures"]}
    assert set(captures) == {
        (arm, seed)
        for arm in ("A_raw", "B_ft3", "B_ft10", "B_ft30")
        for seed in (43, 44)
    }
    for (arm, seed), entry in captures.items():
        slot = run / "uslapseagent" / arm / f"seed{seed}_foldNone"
        record = json.loads((slot / "meta.json").read_text())
        assert entry["rows"] == 1000
        assert entry["record"] == f"{arm}/{slot.name}/meta.json"
        assert entry["predictions_sha256"] == _array_sha256(slot / "predictions.npy")
        assert entry["truth_sha256"] == _array_sha256(slot / "ground_truth.npy")
        # The downstream contract: rescore refuses when this disagrees with the record.
        assert entry["predictions_sha256"] == record["predictions_sha256"]
        assert entry["reason"] is None


def test_a_slot_that_lost_an_array_says_so_instead_of_disappearing(tmp_path):
    run = _copy_anchor(tmp_path)
    slot = run / "uslapseagent" / "B_ft30" / "seed44_foldNone"
    (slot / "predictions.npy").unlink()

    result = _cli("--run", str(run))
    assert result.returncode == 0, result.stderr

    captures = json.loads((run / "capture.json").read_text())["captures"]
    entry = next(c for c in captures if (c["arm"], c["seed"]) == ("B_ft30", 44))
    assert entry["predictions_sha256"] is None
    assert entry["truth_sha256"] == _array_sha256(slot / "ground_truth.npy")
    assert entry["reason"] == "predictions.npy not retained"
    # The row count survives the array it came from.
    assert entry["rows"] == 1000
    # ...and the other seven slots are untouched by the gap.
    assert len(captures) == 8
    assert all(c["reason"] is None for c in captures if c is not entry)


def test_two_runs_over_the_same_directory_produce_identical_bytes(tmp_path):
    run = _copy_anchor(tmp_path)

    assert _cli("--run", str(run)).returncode == 0
    first = (run / "capture.json").read_bytes()
    assert _cli("--run", str(run)).returncode == 0

    assert (run / "capture.json").read_bytes() == first


def test_a_run_with_no_arm_records_refuses(tmp_path):
    run = tmp_path / "20261031T000000Z"
    run.mkdir()

    result = _cli("--run", str(run))

    assert result.returncode == 1
    assert "nothing to capture" in result.stderr


def test_the_committed_anchor_manifest_matches_its_arrays():
    """The committed manifest is evidence, so the suite keeps it honest.

    Read-only, and worked out from the arrays and the records rather than by calling the
    generator: a generator bug must not be able to reproduce itself here.
    """
    manifest = json.loads((ANCHOR / "capture.json").read_text())
    assert manifest["schema_version"] == 1
    assert manifest["run_id"] == ANCHOR.name
    assert manifest["dataset"] == "uslapseagent"

    captures = {(c["arm"], c["seed"]): c for c in manifest["captures"]}
    assert len(captures) == 8
    for (arm, seed), entry in captures.items():
        slot = ANCHOR / "uslapseagent" / arm / f"seed{seed}_foldNone"
        record = json.loads((slot / "meta.json").read_text())
        assert entry["record"] == f"{arm}/{slot.name}/meta.json"
        assert entry["predictions_sha256"] == _array_sha256(slot / "predictions.npy")
        assert entry["truth_sha256"] == _array_sha256(slot / "ground_truth.npy")
        assert entry["predictions_sha256"] == record["predictions_sha256"]
        assert entry["reason"] is None


def test_nothing_is_written_outside_the_run_directory(tmp_path):
    run = _copy_anchor(tmp_path)
    before = {p for p in tmp_path.rglob("*")}

    assert _cli("--run", str(run)).returncode == 0

    assert {p for p in tmp_path.rglob("*")} - before == {run / "capture.json"}


def _folded_run(tmp_path: Path) -> Path:
    """A run with two folds, which the v1 shape refuses and v2 must carry."""
    run = tmp_path / "20261109T000000Z"
    for fold in (0, 1):
        slot = run / "freMTPL2freq" / "A_raw" / f"seed0_fold{fold}"
        slot.mkdir(parents=True)
        np.save(slot / "predictions.npy", np.array([0.1, 0.2, 0.3]))
        np.save(slot / "ground_truth.npy", np.array([0.0, 0.0, 1.0]))
        (slot / "meta.json").write_text(
            json.dumps({"arm": "A_raw", "seed": 0, "fold": fold, "test_rows": 3})
        )
    return run


def test_a_folded_run_writes_schema_two_with_a_fold_per_entry(tmp_path):
    run = _folded_run(tmp_path)

    result = _cli("--run", str(run))
    assert result.returncode == 0, result.stderr

    manifest = json.loads((run / "capture.json").read_text())
    assert manifest["schema_version"] == 2
    assert [(c["fold"], c["seed"]) for c in manifest["captures"]] == [(0, 0), (1, 0)]
    assert all("fold" in c for c in manifest["captures"])


def test_a_non_integer_fold_label_refuses(tmp_path):
    run = tmp_path / "20261109T000000Z"
    slot = run / "freMTPL2freq" / "A_raw" / "seed0_foldA"
    slot.mkdir(parents=True)
    (slot / "meta.json").write_text("{}")

    result = _cli("--run", str(run))

    assert result.returncode == 1
    assert "fold" in result.stderr



# ---------------------------------------------------------------------------
# v3: row identity, exposure and quantiles (#538).
# ---------------------------------------------------------------------------
def _v3_run(
    tmp_path: Path,
    *,
    dataset: str = "freMTPL2freq",
    folds: tuple[int, ...] = (0, 1),
    arms: tuple[str, ...] = ("B_ft30",),
    write_index: bool = True,
    write_quantiles: bool = True,
    write_exposure: bool = True,
    index_offset: int = 0,
) -> Path:
    run = tmp_path / "20261109T000000Z"
    for arm in arms:
        for fold in folds:
            slot = run / dataset / arm / f"seed0_fold{fold}"
            slot.mkdir(parents=True)
            predictions = np.array([0.1, 0.2, 0.3])
            np.save(slot / "predictions.npy", predictions)
            np.save(slot / "ground_truth.npy", np.array([0.0, 0.0, 1.0]))
            if write_index:
                np.save(
                    slot / "test_index.npy",
                    np.array([10, 11, 12], dtype=np.int64) + index_offset,
                )
            if write_quantiles:
                np.save(slot / "quantiles.npy", np.tile(predictions, (9, 1)))
            if write_exposure:
                np.save(slot / "exposure.npy", np.ones(3))
            (slot / "meta.json").write_text(
                json.dumps({"arm": arm, "seed": 0, "fold": fold, "test_rows": 3})
            )
    return run


def test_a_run_declaring_the_arrays_writes_schema_three_with_every_hash(tmp_path):
    run = _v3_run(tmp_path)

    result = _cli("--run", str(run))
    assert result.returncode == 0, result.stderr

    manifest = json.loads((run / "capture.json").read_text())
    assert manifest["schema_version"] == 3
    for entry in manifest["captures"]:
        assert entry["test_index_sha256"]
        assert entry["quantiles_sha256"]
        assert entry["exposure_sha256"]
        assert entry["fold"] in (0, 1)


def test_a_partial_v3_run_is_refused_rather_than_demoted_to_v2(tmp_path):
    run = _v3_run(tmp_path, write_quantiles=False)

    result = _cli("--run", str(run))

    assert result.returncode == 1
    assert "partial v3" in result.stderr
    assert not (run / "capture.json").exists()


def test_a_foldless_run_may_not_declare_the_arrays(tmp_path):
    run = _v3_run(tmp_path, folds=(0,))
    slot = run / "freMTPL2freq" / "B_ft30" / "seed0_fold0"
    foldless = run / "freMTPL2freq" / "B_ft30" / "seed0_foldNone"
    slot.rename(foldless)
    (foldless / "meta.json").write_text(
        json.dumps({"arm": "B_ft30", "seed": 0, "fold": None, "test_rows": 3})
    )

    result = _cli("--run", str(run))

    assert result.returncode == 1
    assert "requires folds" in result.stderr


def test_exposure_is_required_for_fremtpl2freq_and_refused_elsewhere(tmp_path):
    missing = _v3_run(tmp_path / "missing", write_exposure=False)
    refused_missing = _cli("--run", str(missing))
    assert refused_missing.returncode == 1
    assert "exposure is required" in refused_missing.stderr

    foreign = _v3_run(
        tmp_path / "foreign", dataset="spanish_motor_severity", write_exposure=True
    )
    refused_foreign = _cli("--run", str(foreign))
    assert refused_foreign.returncode == 1
    assert "exposure is defined for freMTPL2freq" in refused_foreign.stderr


def test_two_slots_of_one_fold_must_carry_the_same_index(tmp_path):
    run = _v3_run(tmp_path, arms=("A_raw", "B_ft30"))
    other = run / "freMTPL2freq" / "B_ft30" / "seed0_fold0" / "test_index.npy"
    np.save(other, np.array([40, 41, 42], dtype=np.int64))

    result = _cli("--run", str(run))

    assert result.returncode == 1
    assert "different" in result.stderr
    assert "test_index.npy" in result.stderr
