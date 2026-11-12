"""The run capture manifest: what a run retained, and what it did not (#362).

One `capture.json` per run directory, an entry per arm × seed × fold carrying the row count and
the hashes of the two arrays — or null hashes and a reason when an array was not retained. The
shape was decided in #355; this module only writes it.

Two schema versions exist. `schema_version: 1` is the original arm × seed shape and stays
byte-identical, so the committed anchor still matches. `schema_version: 2` is written when any
slot carries a real fold: every entry gains a `fold` key, which is an integer or null.

**The hashes cover the array's contiguous bytes, not the `.npy` file's bytes.** The record
already spells `predictions_sha256` that way (`provenance.sha256_array`), and the
rescore tool (#361) refuses when the manifest and the record disagree, so a file-bytes hash would
make every manifest disagree with every record.

Nothing the record already holds is duplicated here: `record` is a relative pointer to the arm's
`meta.json`, which stays the home of dataset, split and provenance.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from provenance import sha256_array

CAPTURE_SCHEMA_VERSION = 1
CAPTURE_SCHEMA_VERSION_FOLDED = 2
CAPTURE_SCHEMA_VERSION_ARRAYS = 3
CAPTURE_SCHEMA_VERSION_WEIGHTS = 4

_RUN_ID = re.compile(r"^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z$")
_SLOT = re.compile(r"^seed(\d+)_fold(\w+)$")

PREDICTIONS = "predictions.npy"
TRUTH = "ground_truth.npy"
TEST_INDEX = "test_index.npy"
EXPOSURE = "exposure.npy"
QUANTILES = "quantiles.npy"
WEIGHTS = "weights.npy"
CLUSTER = "cluster_id.npy"
RECORD = "meta.json"

# The v3 arrays (#538). Nine deciles, ascending; exposure applies to one dataset only.
QUANTILE_LEVELS = 9
EXPOSURE_DATASET = "freMTPL2freq"


class CaptureRefused(Exception):
    """A run that cannot be described honestly. The message names what is missing."""


@dataclass(frozen=True)
class Slot:
    """One arm × seed × fold directory, and the files a manifest entry points at."""

    arm: str
    seed: int
    fold: int | None
    directory: Path
    record: Path

    @property
    def predictions(self) -> Path:
        return self.directory / PREDICTIONS

    @property
    def truth(self) -> Path:
        return self.directory / TRUTH

    @property
    def test_index(self) -> Path:
        return self.directory / TEST_INDEX

    @property
    def exposure(self) -> Path:
        return self.directory / EXPOSURE

    @property
    def quantiles(self) -> Path:
        return self.directory / QUANTILES

    @property
    def weights(self) -> Path:
        return self.directory / WEIGHTS

    @property
    def cluster(self) -> Path:
        return self.directory / CLUSTER

    @property
    def relative_record(self) -> str:
        """The record path as a manifest entry spells it: relative to the dataset directory."""
        return f"{self.arm}/{self.directory.name}/{RECORD}"


def created_utc_from_run_id(run_id: str) -> str:
    """The run's own UTC start, spelled as the manifest's `created_utc`.

    The run id is a UTC timestamp. Using it instead of the generator's clock is what makes two
    runs over the same directory produce identical bytes.
    """
    match = _RUN_ID.match(run_id)
    if not match:
        raise CaptureRefused(
            f"run directory name {run_id!r} is not a run id (YYYYMMDDTHHMMSSZ); "
            "the manifest's created_utc is taken from it"
        )
    year, month, day, hour, minute, second = match.groups()
    return f"{year}-{month}-{day}T{hour}:{minute}:{second}Z"


def discover_slots(run_dir: Path) -> tuple[str, list[Slot]]:
    """The dataset name and every arm × seed × fold slot under
    `<run>/<dataset>/<arm>/seed<S>_fold<F>`.

    Refuses rather than guessing: a run with no slots, more than one dataset, an unrecognised
    slot name, a fold label that is neither `None` nor an integer, or a slot whose record is
    missing.
    """
    run_dir = Path(run_dir)
    if not run_dir.is_dir():
        raise CaptureRefused(f"no run directory at {run_dir}")

    datasets = sorted(path for path in run_dir.iterdir() if path.is_dir())
    if not datasets:
        raise CaptureRefused(f"{run_dir} holds no dataset directory; there is nothing to capture")
    if len(datasets) > 1:
        names = ", ".join(path.name for path in datasets)
        raise CaptureRefused(
            f"{run_dir} holds more than one dataset ({names}); one manifest carries one dataset"
        )

    dataset_dir = datasets[0]
    slots: list[Slot] = []
    for arm_dir in sorted(path for path in dataset_dir.iterdir() if path.is_dir()):
        for slot_dir in sorted(path for path in arm_dir.iterdir() if path.is_dir()):
            match = _SLOT.match(slot_dir.name)
            if not match:
                raise CaptureRefused(
                    f"{slot_dir} is not an arm × seed slot (seed<S>_fold<F>); "
                    "the capture shape has no place for it"
                )
            seed, fold_label = int(match.group(1)), match.group(2)
            if fold_label == "None":
                fold: int | None = None
            elif fold_label.isdigit():
                fold = int(fold_label)
            else:
                raise CaptureRefused(
                    f"{slot_dir} has fold label {fold_label!r}; a folded capture needs an integer "
                    "fold (or 'None' for the original arm × seed shape)"
                )
            record = slot_dir / RECORD
            if not record.is_file():
                raise CaptureRefused(
                    f"{slot_dir} has no {RECORD}; a capture entry points at its record and a "
                    "pointer to nothing is not a manifest"
                )
            slots.append(
                Slot(arm=arm_dir.name, seed=seed, fold=fold, directory=slot_dir, record=record)
            )

    if not slots:
        raise CaptureRefused(f"{dataset_dir} holds no arm records; there is nothing to capture")
    return dataset_dir.name, slots


def _rows(slot: Slot, predictions, truth) -> int | None:
    """The test-row count, taken from whichever evidence the slot still has."""
    if predictions is not None:
        return int(len(predictions))
    if truth is not None:
        return int(len(truth))
    return json.loads(slot.record.read_text(encoding="utf-8")).get("test_rows")


def _load(path: Path) -> "np.ndarray | None":
    return np.load(path) if path.is_file() else None


def _check_test_index(array: np.ndarray, rows: int, slot: Slot) -> None:
    if array.ndim != 1 or array.shape[0] != rows:
        raise CaptureRefused(
            f"{slot.test_index} has shape {array.shape}; v3 requires one row of source positions "
            f"per test row ({rows},)"
        )
    if array.dtype != np.int64:
        raise CaptureRefused(
            f"{slot.test_index} has dtype {array.dtype}; v3 requires int64, as the amendment states"
        )


def _check_vector(array: np.ndarray, rows: int, path: Path) -> None:
    if array.ndim != 1 or array.shape[0] != rows:
        raise CaptureRefused(
            f"{path} has shape {array.shape}; v3 requires one value per test row ({rows},)"
        )
    if array.dtype != np.float64:
        raise CaptureRefused(f"{path} has dtype {array.dtype}; v3 requires float64")


def _check_quantiles(array: np.ndarray, rows: int, slot: Slot) -> None:
    if array.shape != (QUANTILE_LEVELS, rows):
        raise CaptureRefused(
            f"{slot.quantiles} has shape {array.shape}; v3 requires "
            f"({QUANTILE_LEVELS} levels, {rows} rows)"
        )
    if array.dtype != np.float64:
        raise CaptureRefused(f"{slot.quantiles} has dtype {array.dtype}; v3 requires float64")


def _v3_arrays(slot: Slot, dataset: str, rows: int) -> dict:
    """The v3 arrays of one slot, validated, or a refusal naming what is missing."""
    index = _load(slot.test_index)
    quantiles = _load(slot.quantiles)
    if index is None or quantiles is None:
        missing = [
            name
            for name, array in ((TEST_INDEX, index), (QUANTILES, quantiles))
            if array is None
        ]
        raise CaptureRefused(
            f"{slot.directory} declares schema v3 but lacks {', '.join(missing)}; "
            "a partial v3 run is refused rather than recorded"
        )
    _check_test_index(index, rows, slot)
    _check_quantiles(quantiles, rows, slot)

    arrays = {
        "test_index_sha256": sha256_array(index),
        "quantiles_sha256": sha256_array(quantiles),
    }
    exposure = _load(slot.exposure)
    if dataset == EXPOSURE_DATASET:
        if exposure is None:
            raise CaptureRefused(
                f"{slot.directory} is {EXPOSURE_DATASET} and declares schema v3, but has no "
                f"{EXPOSURE}; exposure is required for this dataset"
            )
        _check_vector(exposure, rows, slot.exposure)
        arrays["exposure_sha256"] = sha256_array(exposure)
    elif exposure is not None:
        raise CaptureRefused(
            f"{slot.directory} carries {EXPOSURE} for dataset {dataset!r}; exposure is defined "
            f"for {EXPOSURE_DATASET} only"
        )
    return arrays


def _v4_arrays(slot: Slot, dataset: str, rows: int) -> dict:
    """The v3 arrays plus the two a grouped severity target needs (#555).

    The weight and the cluster id are what make a claim-level or policy-grouped severity target
    honest: without the weight a 5-claim policy counts as one observation, and without the cluster
    the interval treats its claims as independent. A frequency slot carrying them is refused, so
    the arrays cannot become decoration.
    """
    arrays = _v3_arrays(slot, dataset, rows)
    task = json.loads(slot.record.read_text(encoding="utf-8")).get("task")
    weights = _load(slot.weights)
    cluster = _load(slot.cluster)

    if task == "severity":
        missing = [
            name
            for name, array in ((WEIGHTS, weights), (CLUSTER, cluster))
            if array is None
        ]
        if missing:
            raise CaptureRefused(
                f"{slot.directory} is a severity slot and declares schema v4, but lacks "
                f"{', '.join(missing)}; both are required for a grouped severity target"
            )
        _check_vector(weights, rows, slot.weights)
        if cluster.ndim != 1 or cluster.shape[0] != rows:
            raise CaptureRefused(
                f"{slot.cluster} has shape {cluster.shape}; v4 requires one cluster id per row "
                f"({rows},)"
            )
        if cluster.dtype != np.int64:
            raise CaptureRefused(f"{slot.cluster} has dtype {cluster.dtype}; v4 requires int64")
        arrays["weights_sha256"] = sha256_array(weights)
        arrays["cluster_sha256"] = sha256_array(cluster)
    elif weights is not None or cluster is not None:
        raise CaptureRefused(
            f"{slot.directory} carries {WEIGHTS} or {CLUSTER} for task {task!r}; the arrays are "
            "defined for severity only"
        )
    return arrays


def _entry(slot: Slot, version: int, dataset: str) -> dict:
    predictions = _load(slot.predictions)
    truth = _load(slot.truth)

    missing = [
        name
        for name, array in ((PREDICTIONS, predictions), (TRUTH, truth))
        if array is None
    ]
    reason = None
    if missing:
        reason = " and ".join(f"{name} not retained" for name in missing)

    entry = {"arm": slot.arm, "seed": slot.seed}
    if version >= CAPTURE_SCHEMA_VERSION_FOLDED:
        # v1 must stay byte-identical; v2 puts the fold after the seed.
        entry["fold"] = slot.fold
    rows = _rows(slot, predictions, truth)
    entry.update(
        {
            "rows": rows,
            "predictions_sha256": None if predictions is None else sha256_array(predictions),
            "truth_sha256": None if truth is None else sha256_array(truth),
            "record": slot.relative_record,
            "reason": reason,
        }
    )
    if version == CAPTURE_SCHEMA_VERSION_WEIGHTS:
        entry.update(_v4_arrays(slot, dataset, rows))
    elif version == CAPTURE_SCHEMA_VERSION_ARRAYS:
        entry.update(_v3_arrays(slot, dataset, rows))
    return entry


def _capture_version(dataset: str, slots: list[Slot]) -> int:
    """v3 when a slot declares the arrays, v2 when folded without them, v1 when foldless.

    A declaration is one slot carrying `test_index.npy`. From it every slot must carry the
    arrays, so a run with one missing array is refused rather than demoted to v2 and left
    unhashed (#538).
    """
    folded = any(slot.fold is not None for slot in slots)
    declared_v4 = any(slot.weights.is_file() or slot.cluster.is_file() for slot in slots)
    declared = any(slot.test_index.is_file() for slot in slots)
    if declared_v4:
        if not folded:
            raise CaptureRefused(
                "a foldless run carries the v4 weight/cluster arrays, but a v1 manifest has no "
                "fold to carry them; v4 requires folds"
            )
        if not declared:
            raise CaptureRefused(
                "a slot carries the v4 weight/cluster arrays without test_index/quantiles; "
                "v4 is v3 plus those arrays, never a replacement for them"
            )
        return CAPTURE_SCHEMA_VERSION_WEIGHTS
    if not declared:
        return CAPTURE_SCHEMA_VERSION_FOLDED if folded else CAPTURE_SCHEMA_VERSION
    if not folded:
        raise CaptureRefused(
            "a foldless run declares the v3 arrays, but a v1 manifest has no fold or array "
            "hashes to carry them; v3 requires folds"
        )
    return CAPTURE_SCHEMA_VERSION_ARRAYS


def _check_shared_indices(slots: list[Slot]) -> None:
    """Every slot of one fold carries the fold's test index, or the capture is refused."""
    by_fold: dict[int, list[Slot]] = {}
    for slot in slots:
        if slot.fold is not None and slot.test_index.is_file():
            by_fold.setdefault(slot.fold, []).append(slot)
    for fold, group in by_fold.items():
        first = np.load(group[0].test_index)
        for slot in group[1:]:
            if not np.array_equal(first, np.load(slot.test_index)):
                raise CaptureRefused(
                    f"fold {fold}: {group[0].directory} and {slot.directory} carry different "
                    f"{TEST_INDEX}; the index belongs to the fold, not the slot"
                )


def build_capture(run_dir: Path) -> dict:
    """The manifest as data. Deterministic: the same directory yields the same dict."""
    run_dir = Path(run_dir)
    dataset, slots = discover_slots(run_dir)
    version = _capture_version(dataset, slots)
    if version >= CAPTURE_SCHEMA_VERSION_ARRAYS:
        _check_shared_indices(slots)
    return {
        "schema_version": version,
        "run_id": run_dir.resolve().name,
        "dataset": dataset,
        "created_utc": created_utc_from_run_id(run_dir.resolve().name),
        "captures": [_entry(slot, version, dataset) for slot in slots],
    }


def render_capture(payload: dict) -> str:
    """The manifest as bytes-text. Fixed field order, one trailing newline, no clock."""
    return json.dumps(payload, indent=2) + "\n"


def write_capture(run_dir: Path) -> Path:
    """Write `capture.json` at the run root — the only file this tool writes."""
    run_dir = Path(run_dir)
    target = run_dir / "capture.json"
    target.write_text(render_capture(build_capture(run_dir)), encoding="utf-8")
    return target


def main(argv=None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Write a run's capture manifest from the arrays it retained.",
    )
    parser.add_argument("--run", required=True, type=Path, help="a run directory, e.g. results/<run_id>")
    args = parser.parse_args(argv)

    try:
        target = write_capture(args.run)
    except CaptureRefused as exc:
        print(f"make_capture: {exc}", file=sys.stderr)
        return 1
    print(f"capture: {target}")
    return 0
