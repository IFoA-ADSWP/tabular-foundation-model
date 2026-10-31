"""Read a run's capture, verified before anything uses it (#361, #387).

One reader for the rescore tool and the predictions export, so both refuse on the same evidence
and neither can drift from the other.

**Integrity has two sources.** With a `capture.json` present both of the entry's hashes are
checked: `predictions_sha256` against the record's and the array on disk, and `truth_sha256`
against the array on disk. A disagreement refuses, naming both hashes, and a null hash refuses
with the entry's reason. Without a manifest the record's `predictions_sha256` verifies the
predictions array, and there is no truth hash to check — stated here rather than implied by
silence (#384).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from provenance import sha256_array
from run_capture import CAPTURE_SCHEMA_VERSION, CaptureRefused, Slot, discover_slots

CAPTURE_FILE = "capture.json"


@dataclass(frozen=True)
class VerifiedSlot:
    """One arm × seed's arrays, after whatever hash source exists has proved them."""

    arm: str
    seed: int
    predictions: np.ndarray
    truth: np.ndarray
    capture_sha: str
    source: str
    record: dict


@dataclass(frozen=True)
class VerifiedRun:
    """A run whose every slot has been verified, with the identity the artifacts need."""

    run_id: str
    dataset: str
    slots: tuple[VerifiedSlot, ...]


def read_manifest(run_dir: Path) -> dict[tuple[str, int], dict] | None:
    """The run's capture entries by arm × seed, or None when no manifest exists."""
    path = Path(run_dir) / CAPTURE_FILE
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    version = payload.get("schema_version")
    if version != CAPTURE_SCHEMA_VERSION:
        raise CaptureRefused(
            f"{path}: unknown capture schema_version {version!r}; this tool reads "
            f"{CAPTURE_SCHEMA_VERSION}"
        )
    return {(entry["arm"], entry["seed"]): entry for entry in payload.get("captures", [])}


def read_record(slot: Slot) -> dict:
    if not slot.record.is_file():
        raise CaptureRefused(f"{slot.record} is missing; there is no record to compare against")
    return json.loads(slot.record.read_text(encoding="utf-8"))


def _verify(slot: Slot, entry: dict | None, record: dict) -> tuple[np.ndarray, np.ndarray, str, str]:
    """Load the arrays, prove them against whichever hash source exists, and name it."""
    for path in (slot.predictions, slot.truth):
        if not path.is_file():
            raise CaptureRefused(f"{path} is missing; there is nothing to rescore")

    predictions = np.load(slot.predictions)
    truth = np.load(slot.truth)
    if len(predictions) != len(truth):
        raise CaptureRefused(
            f"{slot.predictions} has {len(predictions)} rows and {slot.truth} has {len(truth)}"
        )
    computed = sha256_array(predictions)

    if entry is None:
        recorded_sha = record.get("predictions_sha256")
        if recorded_sha is None:
            raise CaptureRefused(
                f"{slot.record} carries no predictions_sha256 and no {CAPTURE_FILE} exists; "
                "the predictions cannot be verified"
            )
        if computed != recorded_sha:
            raise CaptureRefused(
                f"hash mismatch for {slot.predictions}: array is {computed}, record says "
                f"{recorded_sha}"
            )
        return predictions, truth, computed, "record"

    manifest_sha = entry.get("predictions_sha256")
    if manifest_sha is None:
        raise CaptureRefused(
            f"{CAPTURE_FILE} entry {slot.arm} seed {slot.seed} was not retained: "
            f"{entry.get('reason') or 'no reason stated'}"
        )
    if manifest_sha != computed:
        raise CaptureRefused(
            f"hash mismatch for {slot.predictions}: array is {computed}, {CAPTURE_FILE} says "
            f"{manifest_sha}"
        )
    recorded_sha = record.get("predictions_sha256")
    if recorded_sha is not None and recorded_sha != manifest_sha:
        raise CaptureRefused(
            f"hash mismatch for {slot.arm} seed {slot.seed}: {CAPTURE_FILE} says {manifest_sha}, "
            f"{slot.record} says {recorded_sha}"
        )

    # The labels decide every value, so the manifest's truth hash is checked with the same rule.
    # Without a manifest there is no truth hash to check against, and this docstring says so.
    computed_truth = sha256_array(truth)
    manifest_truth = entry.get("truth_sha256")
    if manifest_truth is None:
        raise CaptureRefused(
            f"{CAPTURE_FILE} entry {slot.arm} seed {slot.seed} did not retain {slot.truth.name}: "
            f"{entry.get('reason') or 'no reason stated'}"
        )
    if manifest_truth != computed_truth:
        raise CaptureRefused(
            f"hash mismatch for {slot.truth}: array is {computed_truth}, {CAPTURE_FILE} says "
            f"{manifest_truth}"
        )
    return predictions, truth, manifest_sha, CAPTURE_FILE


def read_run(run_dir: Path) -> VerifiedRun:
    """Every arm × seed slot of a run, verified; refuses a gap in the manifest."""
    run_dir = Path(run_dir)
    dataset, slots = discover_slots(run_dir)
    manifest = read_manifest(run_dir)
    if manifest is not None:
        uncaptured = [
            f"{slot.arm} seed {slot.seed}"
            for slot in slots
            if (slot.arm, slot.seed) not in manifest
        ]
        if uncaptured:
            raise CaptureRefused(
                f"{run_dir / CAPTURE_FILE} has no entry for {', '.join(uncaptured)}; "
                "a cited run's manifest covers every arm × seed"
            )

    verified = []
    for slot in slots:
        record = read_record(slot)
        entry = None if manifest is None else manifest[(slot.arm, slot.seed)]
        predictions, truth, capture_sha, source = _verify(slot, entry, record)
        verified.append(
            VerifiedSlot(
                arm=slot.arm,
                seed=slot.seed,
                predictions=predictions,
                truth=truth,
                capture_sha=capture_sha,
                source=source,
                record=record,
            )
        )
    return VerifiedRun(run_id=run_dir.resolve().name, dataset=dataset, slots=tuple(verified))
