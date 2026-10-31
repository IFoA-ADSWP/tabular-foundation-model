"""The run capture manifest: what a run retained, and what it did not (#362).

One `capture.json` per run directory, `schema_version: 1`, an entry per arm × seed carrying the
row count and the hashes of the two arrays — or null hashes and a reason when an array was not
retained. The shape was decided in #355; this module only writes it.

**The hashes cover the array's contiguous bytes, not the `.npy` file's bytes.** The record
already spells `predictions_sha256` that way (`_sha256_array` in `scripts/run_pilot.py`), and the
rescore tool (#361) refuses when the manifest and the record disagree, so a file-bytes hash would
make every manifest disagree with every record.

Nothing the record already holds is duplicated here: `record` is a relative pointer to the arm's
`meta.json`, which stays the home of dataset, split and provenance.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

CAPTURE_SCHEMA_VERSION = 1

_RUN_ID = re.compile(r"^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z$")
_SLOT = re.compile(r"^seed(\d+)_fold(\w+)$")

PREDICTIONS = "predictions.npy"
TRUTH = "ground_truth.npy"
RECORD = "meta.json"


class CaptureRefused(Exception):
    """A run that cannot be described honestly. The message names what is missing."""


@dataclass(frozen=True)
class Slot:
    """One arm × seed directory, and the files a manifest entry points at."""

    arm: str
    seed: int
    directory: Path
    record: Path

    @property
    def predictions(self) -> Path:
        return self.directory / PREDICTIONS

    @property
    def truth(self) -> Path:
        return self.directory / TRUTH

    @property
    def relative_record(self) -> str:
        """The record path as a manifest entry spells it: relative to the dataset directory."""
        return f"{self.arm}/{self.directory.name}/{RECORD}"


def sha256_array(values) -> str:
    """sha256 of an array's contiguous bytes — the record's convention, not the file's."""
    return hashlib.sha256(np.ascontiguousarray(values).tobytes()).hexdigest()


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
    """The dataset name and every arm × seed slot under `<run>/<dataset>/<arm>/seed<S>_fold<F>`.

    Refuses rather than guessing: a run with no slots, more than one dataset, an unrecognised
    slot name, a folded slot (the decided shape has no `fold` field), or a slot whose record is
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
            seed, fold = int(match.group(1)), match.group(2)
            if fold != "None":
                raise CaptureRefused(
                    f"{slot_dir} is fold {fold}; the capture shape is per arm × seed and carries "
                    "no fold field, so two folds would collide"
                )
            record = slot_dir / RECORD
            if not record.is_file():
                raise CaptureRefused(
                    f"{slot_dir} has no {RECORD}; a capture entry points at its record and a "
                    "pointer to nothing is not a manifest"
                )
            slots.append(Slot(arm=arm_dir.name, seed=seed, directory=slot_dir, record=record))

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


def _entry(slot: Slot) -> dict:
    predictions = np.load(slot.predictions) if slot.predictions.is_file() else None
    truth = np.load(slot.truth) if slot.truth.is_file() else None

    missing = [
        name
        for name, array in ((PREDICTIONS, predictions), (TRUTH, truth))
        if array is None
    ]
    reason = None
    if missing:
        reason = " and ".join(f"{name} not retained" for name in missing)

    return {
        "arm": slot.arm,
        "seed": slot.seed,
        "rows": _rows(slot, predictions, truth),
        "predictions_sha256": None if predictions is None else sha256_array(predictions),
        "truth_sha256": None if truth is None else sha256_array(truth),
        "record": slot.relative_record,
        "reason": reason,
    }


def build_capture(run_dir: Path) -> dict:
    """The manifest as data. Deterministic: the same directory yields the same dict."""
    run_dir = Path(run_dir)
    dataset, slots = discover_slots(run_dir)
    return {
        "schema_version": CAPTURE_SCHEMA_VERSION,
        "run_id": run_dir.resolve().name,
        "dataset": dataset,
        "created_utc": created_utc_from_run_id(run_dir.resolve().name),
        "captures": [_entry(slot) for slot in slots],
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
