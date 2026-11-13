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
from run_capture import (
    CAPTURE_SCHEMA_VERSION,
    CAPTURE_SCHEMA_VERSION_ARRAYS,
    CAPTURE_SCHEMA_VERSION_FOLDED,
    CAPTURE_SCHEMA_VERSION_METHODS,
    CAPTURE_SCHEMA_VERSION_WEIGHTS,
    CLUSTER,
    EXPOSURE,
    EXPOSURE_DATASET,
    QUANTILES,
    TEST_INDEX,
    WEIGHTS,
    CaptureRefused,
    Slot,
    declares_quantiles,
    discover_slots,
)

CAPTURE_FILE = "capture.json"
READABLE_VERSIONS = (
    CAPTURE_SCHEMA_VERSION,
    CAPTURE_SCHEMA_VERSION_FOLDED,
    CAPTURE_SCHEMA_VERSION_ARRAYS,
    CAPTURE_SCHEMA_VERSION_WEIGHTS,
    CAPTURE_SCHEMA_VERSION_METHODS,
)


@dataclass(frozen=True)
class VerifiedSlot:
    """One arm × seed × fold's arrays, after whatever hash source exists has proved them."""

    arm: str | None
    seed: int
    fold: int | None
    predictions: np.ndarray
    truth: np.ndarray
    capture_sha: str
    source: str
    record: dict
    method: str | None = None
    test_index: np.ndarray | None = None
    exposure: np.ndarray | None = None
    quantiles: np.ndarray | None = None
    weights: np.ndarray | None = None
    cluster: np.ndarray | None = None


@dataclass(frozen=True)
class VerifiedRun:
    """A run whose every slot has been verified, with the identity the artifacts need."""

    run_id: str
    dataset: str
    slots: tuple[VerifiedSlot, ...]


def _slot_key(slot: Slot) -> tuple[str | None, str | None, int, int | None]:
    return (slot.method, slot.arm, slot.seed, slot.fold)


def read_manifest(
    run_dir: Path,
) -> tuple[dict[tuple[str | None, str | None, int, int | None], dict], int] | None:
    """The run's manifest entries by method × arm × seed × fold, and the schema version.

    None when no manifest exists. A version this reader does not know refuses rather than
    guessing; v1 through v5 are readable, and a v1–v4 entry keys on `method: None`.
    """
    path = Path(run_dir) / CAPTURE_FILE
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    version = payload.get("schema_version")
    if version not in READABLE_VERSIONS:
        raise CaptureRefused(
            f"{path}: unknown capture schema_version {version!r}; this tool reads "
            f"{', '.join(str(v) for v in READABLE_VERSIONS)}"
        )
    entries = {
        (entry.get("method"), entry.get("arm"), entry["seed"], entry.get("fold")): entry
        for entry in payload.get("captures", [])
    }
    return entries, version


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


def _verify_arrays(
    slot: Slot, entry: dict, version: int, dataset: str
) -> dict[str, np.ndarray | None]:
    """The v3/v4 arrays, each proved against the manifest hash that names it.

    A v3 entry must carry a hash for every array *its dataset* owes, so `dataset` is forwarded
    from `read_run` exactly as the writer forwards it; a missing hash would let an unverified
    array through, and a freMTPL2freq slot without exposure reads as a refusal, not as `None`.
    A v4 severity slot owes `weights` and `cluster_id` as well (#555).
    """
    if version < CAPTURE_SCHEMA_VERSION_ARRAYS:
        return {
            "test_index": None,
            "exposure": None,
            "quantiles": None,
            "weights": None,
            "cluster": None,
        }

    wanted = {TEST_INDEX: "test_index_sha256"}
    if version < CAPTURE_SCHEMA_VERSION_METHODS:
        wanted[QUANTILES] = "quantiles_sha256"
    else:
        record = json.loads(slot.record.read_text(encoding="utf-8"))
        if declares_quantiles(record):
            wanted[QUANTILES] = "quantiles_sha256"
        elif slot.quantiles.is_file():
            raise CaptureRefused(
                f"{slot.quantiles} is present but the record declares no quantile_levels; "
                "an unverified distribution is refused rather than ignored"
            )
    if dataset == EXPOSURE_DATASET:
        wanted[EXPOSURE] = "exposure_sha256"
    if version >= CAPTURE_SCHEMA_VERSION_WEIGHTS:
        task = json.loads(slot.record.read_text(encoding="utf-8")).get("task")
        # The manifest is the artifact under verification: if it carries the hashes, the arrays
        # are owed and checked even when the record's pointer forgot to say `task`.
        has_hashes = (
            entry.get("weights_sha256") is not None
            or entry.get("cluster_sha256") is not None
        )
        if task == "severity" or has_hashes:
            wanted[WEIGHTS] = "weights_sha256"
            wanted[CLUSTER] = "cluster_sha256"

    loaded: dict[str, np.ndarray | None] = {}
    for name, hash_key in wanted.items():
        path = slot.directory / name
        if not path.is_file():
            raise CaptureRefused(
                f"{path} is missing; the manifest declares schema v{version} for {dataset}"
            )
        array = np.load(path)
        expected = entry.get(hash_key)
        if expected is None:
            raise CaptureRefused(
                f"{CAPTURE_FILE} entry {slot.arm} seed {slot.seed} fold {slot.fold} carries no "
                f"{hash_key}; a v{version} entry must hash {name}"
            )
        computed = sha256_array(array)
        if computed != expected:
            raise CaptureRefused(
                f"hash mismatch for {path}: array is {computed}, {CAPTURE_FILE} says {expected}"
            )
        loaded[name.removesuffix(".npy")] = array
    return {
        "test_index": loaded.get("test_index"),
        "exposure": loaded.get("exposure"),
        "quantiles": loaded.get("quantiles"),
        "weights": loaded.get("weights"),
        "cluster": loaded.get("cluster_id"),
    }


def read_run(run_dir: Path) -> VerifiedRun:
    """Every arm × seed × fold slot of a run, verified; refuses a gap in the manifest."""
    run_dir = Path(run_dir)
    dataset, slots = discover_slots(run_dir)
    manifest = read_manifest(run_dir)

    version = CAPTURE_SCHEMA_VERSION
    entries: dict[tuple[str, int, int | None], dict] = {}
    if manifest is not None:
        entries, version = manifest
        uncaptured = [
            f"{slot.arm} seed {slot.seed} fold {slot.fold}"
            for slot in slots
            if _slot_key(slot) not in entries
        ]
        if uncaptured:
            raise CaptureRefused(
                f"{run_dir / CAPTURE_FILE} has no entry for {', '.join(uncaptured)}; "
                "a cited run's manifest covers every arm × seed × fold"
            )

    verified = []
    for slot in slots:
        record = read_record(slot)
        entry = None if manifest is None else entries[_slot_key(slot)]
        predictions, truth, capture_sha, source = _verify(slot, entry, record)
        extras = (
            {"test_index": None, "exposure": None, "quantiles": None}
            if entry is None
            else _verify_arrays(slot, entry, version, dataset)
        )
        verified.append(
            VerifiedSlot(
                arm=slot.arm,
                method=slot.method,
                seed=slot.seed,
                fold=slot.fold,
                predictions=predictions,
                truth=truth,
                capture_sha=capture_sha,
                source=source,
                record=record,
                **extras,
            )
        )
    return VerifiedRun(
        run_id=run_dir.resolve().name,
        dataset=dataset,
        slots=tuple(verified),
    )
