#!/usr/bin/env python3
"""Reassemble and VERIFY the artifact payload returned through the container log.

WHY THIS EXISTS (docs/reports/PILOT_2_PREREQUISITES.md PR-2)

R1 returned metrics and metadata but no per-arm predictions, so its headline numbers
could be read but never recomputed or paired-tested. Predictions are the evidence;
metrics alone are a claim.

The transfer channel is the container log, which caps every LINE at exactly 500
characters -- so the payload is folded into tagged lines well under that and must be
reassembled in order. That cap once truncated a single-line payload silently: it
decoded to a partial gzip that tar rejected, while every log message said the
transfer had succeeded.

So this does three things, in order, and refuses to report success unless all pass:

  1. SIZE. The box declares its payload (`__ARTIFACTS_INFO__ bytes= lines= files=
     sha256=`). A short read is reported as such -- "captured 812 of 3808 lines" --
     instead of failing later as a cryptic tar error.
  2. INTEGRITY. The reassembled archive's sha256 must match the declared value.
  3. VERIFIABILITY. Every arm's `predictions.npy` is hashed and compared against the
     `predictions_sha256` its own `meta.json` recorded at production time. This is the
     check that makes a returned metric recomputable by a third party.

  4. IDENTITY (`--expect-seeds`). The seeds in the restored tree's `meta.json` files are
     compared against the seeds the launch was given, per `(dataset, arm)`. (3) proves a
     batch is internally consistent; only this proves it is the batch that was asked for.
     On 2026-11-05 two launches asked for 225-236 and 237-248, both wrote 141-152, and both
     reported `verified=24 mismatched=0` (#429).

  5. MEASUREMENT (`--expect-measurement`). A benchmark run returns one `benchmark_fit`
     record and no predictions, so (3) cannot run and must not read as a failed check.
     The equivalent claim is the record itself: exactly one, and carrying the fields the
     acceptance criterion names (`wall_seconds`, `rows`, `epochs`, `device`,
     `tabpfn_version`, `frame`, `seed`), with a positive wall time (#528).

Note the subtlety in (3): `meta.json` records the hash of the ARRAY's bytes
(`array.tobytes()`), not of the `.npy` container, so hashing the file directly would
always mismatch. `npy_data_sha256` parses the `.npy` header and hashes only the data
payload -- pure stdlib, so no numpy is needed on the receiving side.

Exit codes:
    0  payload restored and every declared prediction verified
    3  no usable payload (absent, or declared empty)
    4  payload incomplete (short read, checksum mismatch, or unpack failure)
    5  payload restored but prediction verification FAILED
    6  the restored tree's seeds are not the seeds the launch requested
    7  the payload is not one complete benchmark measurement
    2  usage error
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import re
import sys
import tarfile

INFO_RE = re.compile(r"__ARTIFACTS_INFO__ (.+)")
PAYLOAD_RE = re.compile(r"__ARTIFACTS_BEGIN__(.*?)__ARTIFACTS_END__", re.S)
LINE_TAG = "__ART__"

EXIT_OK = 0
EXIT_NO_PAYLOAD = 3
EXIT_INCOMPLETE = 4
EXIT_UNVERIFIED = 5
EXIT_SEED_MISMATCH = 6
EXIT_MEASUREMENT = 7

MEASUREMENT_KIND = "benchmark_fit"
# The fields the probe's acceptance criterion names (#528). A record missing one of these is a
# claim the fair test cannot be sized from, so it is refused rather than reported as measured.
MEASUREMENT_FIELDS = (
    "wall_seconds",
    "rows",
    "epochs",
    "device",
    "tabpfn_version",
    "frame",
    "seed",
)


def parse_info(raw: str) -> dict:
    """Parse the box's self-declared payload size/checksum line."""
    info: dict = {}
    m = INFO_RE.search(raw)
    if m:
        for kv in m.group(1).split():
            if "=" in kv:
                k, v = kv.split("=", 1)
                info[k] = v
    return info


def payload_lines(raw: str) -> list[str] | None:
    """Return the tagged payload lines in order, or None if no markers were found."""
    m = PAYLOAD_RE.search(raw)
    if not m:
        return None
    return [ln[len(LINE_TAG):].strip() for ln in m.group(1).splitlines() if ln.startswith(LINE_TAG)]


def npy_data_sha256(path: str) -> str | None:
    """sha256 of a .npy file's DATA PAYLOAD, i.e. array.tobytes() for a contiguous array."""
    with open(path, "rb") as f:
        if f.read(6) != b"\x93NUMPY":
            return None
        major = f.read(1)
        f.read(1)  # minor
        hlen = int.from_bytes(f.read(2 if major == b"\x01" else 4), "little")
        f.read(hlen)  # header dict, including padding
        return hashlib.sha256(f.read()).hexdigest()


def restore(raw: str, dest: str) -> tuple[int, str]:
    """Check, decode, verify and unpack the payload. Returns (exit_code, report)."""
    info = parse_info(raw)
    lines = payload_lines(raw)

    if lines is None:
        return EXIT_NO_PAYLOAD, "no artifact markers found in the container log"

    declared = int(info.get("lines", -1))
    if declared == 0:
        return EXIT_NO_PAYLOAD, "payload declared empty (0 bytes) -- the box produced no outputs"

    if declared > 0 and len(lines) != declared:
        return (
            EXIT_INCOMPLETE,
            f"payload is short: captured {len(lines)} of {declared} lines "
            "(raise the runner's --tail, or the run died mid-emit)",
        )

    try:
        blob = base64.b64decode("".join(lines))
    except Exception as e:
        return EXIT_INCOMPLETE, f"base64 decode failed: {type(e).__name__}: {e}"

    if info.get("sha256") not in (None, "-"):
        got = hashlib.sha256(blob).hexdigest()
        if got != info["sha256"]:
            return (
                EXIT_INCOMPLETE,
                f"archive sha256 mismatch: declared {info['sha256'][:16]} got {got[:16]}",
            )

    os.makedirs(dest, exist_ok=True)
    try:
        with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tf:
            # Be explicit about extraction filtering: Python 3.14 will apply it by
            # default, and `filter="data"` refuses absolute paths, device files and
            # links that escape the destination -- worth having on deliberately, since
            # this archive comes from a machine we do not control. Only available from
            # 3.12, and the box may be on 3.11, so fall back rather than fail.
            if sys.version_info >= (3, 12):
                tf.extractall(dest, filter="data")
            else:
                tf.extractall(dest)
    except Exception as e:
        return EXIT_INCOMPLETE, f"archive could not be unpacked: {type(e).__name__}: {e}"

    return EXIT_OK, (
        f"restored to {dest} ({len(lines)} lines, {info.get('files', '?')} files, "
        f"{info.get('bytes', '?')} bytes)"
    )


def verify_predictions(dest: str) -> tuple[int, int, int, list[str]]:
    """Compare each arm's predictions against the hash its meta.json recorded.

    Returns (verified, mismatched, missing, detail_lines).
    """
    verified = mismatched = missing = 0
    details: list[str] = []
    for root, _dirs, files in os.walk(dest):
        if "meta.json" not in files:
            continue
        try:
            with open(os.path.join(root, "meta.json")) as f:
                meta = json.load(f)
        except Exception:
            continue
        claim = meta.get("predictions_sha256")
        if not claim:
            continue  # older schema: nothing claimed, nothing to check
        rid = meta.get("run_id", os.path.relpath(root, dest))
        path = os.path.join(root, "predictions.npy")
        if not os.path.exists(path):
            details.append(f"  MISSING  {rid}")
            missing += 1
            continue
        got = npy_data_sha256(path)
        if got == claim:
            verified += 1
        else:
            details.append(f"  MISMATCH {rid}: claimed {claim[:16]} got {str(got)[:16]}")
            mismatched += 1
    return verified, mismatched, missing, details


def verify_measurement(dest: str) -> tuple[int, str]:
    """Check a benchmark payload: exactly one complete `benchmark_fit` record.

    A measurement has no predictions, so `verify_predictions` would find nothing to check and
    report `verified=0` -- which the launcher treats as a refusal. The equivalent claim here is
    the record's own shape: the fields the acceptance criterion names, and a wall time that is a
    positive number. Anything else is a payload that cannot size the fair test.

    Exactly one, not at least one: the probe measures one point, and two records in one payload
    means either a mixed launch or a duplicated emit. Both are worth stopping on.
    """
    records: list[tuple[str, dict]] = []
    for root, _dirs, files in os.walk(dest):
        for name in files:
            if not name.endswith(".json"):
                continue
            path = os.path.join(root, name)
            try:
                with open(path) as f:
                    payload = json.load(f)
            except Exception:
                continue
            if isinstance(payload, dict) and payload.get("kind") == MEASUREMENT_KIND:
                records.append((path, payload))

    if len(records) != 1:
        return EXIT_MEASUREMENT, (
            f"expected exactly one {MEASUREMENT_KIND} record, found {len(records)}"
        )

    path, payload = records[0]
    label = os.path.basename(path)
    block = payload.get("measurement")
    if not isinstance(block, dict):
        return EXIT_MEASUREMENT, f"{label} has no measurement block"

    missing = [field for field in MEASUREMENT_FIELDS if block.get(field) in (None, "")]
    if missing:
        return EXIT_MEASUREMENT, f"{label} is missing {', '.join(missing)}"

    try:
        wall = float(block["wall_seconds"])
    except (TypeError, ValueError):
        return EXIT_MEASUREMENT, f"{label} wall_seconds is not a number"
    if wall <= 0:
        return EXIT_MEASUREMENT, f"{label} wall_seconds={wall:g} is not a positive time"

    return EXIT_OK, (
        f"measurement {label}: wall_seconds={wall:g} rows={block['rows']} epochs={block['epochs']} "
        f"device={block['device']} tabpfn={block['tabpfn_version']} frame={block['frame']}"
    )


def parse_seeds(spec: str) -> list[int]:
    """Turn `225,226,227` or `225-236` (or a mix) into an ordered list of ints.

    A reversed range is an error rather than an empty list: `236-225` silently expanding
    to nothing would report every written seed as unexpected and hide the real mistake.
    """
    seeds: list[int] = []
    for item in spec.replace(" ", ",").split(","):
        if not item:
            continue
        if "-" in item:
            lo, _, hi = item.partition("-")
            start, end = int(lo), int(hi)
            if end < start:
                raise ValueError(f"reversed range {item!r}")
            seeds.extend(range(start, end + 1))
        else:
            seeds.append(int(item))
    if not seeds:
        raise ValueError("no seeds in the list")
    return seeds


def seed_ranges(seeds) -> str:
    """`[141,142,...,152]` -> `141-152`, so a mismatch names ranges, not 12 numbers."""
    ordered = sorted(set(seeds))
    if not ordered:
        return "(none)"
    runs: list[list[int]] = [[ordered[0]]]
    for seed in ordered[1:]:
        if seed == runs[-1][-1] + 1:
            runs[-1].append(seed)
        else:
            runs.append([seed])
    return ",".join(
        f"{run[0]}-{run[-1]}" if len(run) > 1 else str(run[0]) for run in runs
    )


def written_seeds(dest: str) -> dict[tuple[str, str], set[int]]:
    """The seeds each `(dataset, arm)` in the restored tree actually wrote.

    Grouped per arm rather than pooled: a batch whose `B_in_domain` died at seed 142 of
    141-143 has the right *union* and the wrong evidence, and the issue's "partial run is
    refused" has to hold one level below the batch too. A multi-fold run writes one meta
    per fold for the same seed, so each group is a set.
    """
    groups: dict[tuple[str, str], set[int]] = {}
    for root, _dirs, files in os.walk(dest):
        if "meta.json" not in files:
            continue
        try:
            with open(os.path.join(root, "meta.json")) as f:
                meta = json.load(f)
        except Exception:
            continue
        try:
            seed = int(meta.get("seed"))
        except (TypeError, ValueError):
            continue  # absent or non-numeric: the group simply does not record it
        key = (str(meta.get("dataset") or "?"), str(meta.get("arm") or "?"))
        groups.setdefault(key, set()).add(seed)
    return groups


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify the container-log artifact payload")
    ap.add_argument("--raw", required=True, help="captured container log")
    ap.add_argument("--dest", required=True, help="where to unpack the payload")
    ap.add_argument(
        "--verify-only",
        action="store_true",
        help="skip unpacking; verify predictions already present in --dest",
    )
    ap.add_argument(
        "--expect-seeds",
        metavar="LIST",
        help=(
            "seeds the launch was given, as a comma list and/or ranges "
            "(e.g. 225,226,227 or 225-236); refusing when the tree holds another set"
        ),
    )
    ap.add_argument(
        "--expect-measurement",
        action="store_true",
        help=(
            "the payload is one benchmark_fit record, not predictions: check exactly one "
            "complete record and skip the prediction/seed checks (refuses both flags)"
        ),
    )
    args = ap.parse_args()

    if args.expect_measurement and args.expect_seeds is not None:
        print("FAIL --expect-measurement and --expect-seeds describe different payloads")
        return 2

    try:
        # An explicitly empty list is a mistake, not a request to skip the check --
        # `vast_run.sh` refuses `--seeds ""` for the same reason.
        expected = parse_seeds(args.expect_seeds) if args.expect_seeds is not None else None
    except ValueError as e:
        print(f"FAIL --expect-seeds is not a seed list: {e}")
        return 2

    if args.verify_only:
        rc, report = EXIT_OK, f"verifying existing payload in {args.dest}"
    else:
        if not os.path.exists(args.raw):
            print(f"FAIL missing captured log: {args.raw}")
            return EXIT_MEASUREMENT if args.expect_measurement else EXIT_NO_PAYLOAD
        with open(args.raw, errors="replace") as f:
            raw = f.read()
        rc, report = restore(raw, args.dest)

    print(f"{'OK' if rc == EXIT_OK else 'FAIL'} {report}")
    if rc != EXIT_OK:
        # A benchmark launch exists to return its measurement, so "the box produced no
        # outputs" is not a warning there -- it is the run having measured nothing.
        if args.expect_measurement and rc == EXIT_NO_PAYLOAD:
            return EXIT_MEASUREMENT
        return rc

    if args.expect_measurement:
        rc, report = verify_measurement(args.dest)
        print(f"{'OK' if rc == EXIT_OK else 'FAIL'} {report}")
        return rc

    verified, mismatched, missing, details = verify_predictions(args.dest)
    for line in details:
        print(line)
    print(f"VERIFY predictions verified={verified} mismatched={mismatched} missing={missing}")

    seed_mismatch = False
    if expected is not None:
        expected_set = set(expected)
        groups = written_seeds(args.dest)
        written = set().union(*groups.values()) if groups else set()
        print(f"SEEDS requested={seed_ranges(expected)} written={seed_ranges(written)}")
        absent = [seed for seed in expected if seed not in written]
        extra = sorted(written - expected_set)
        if absent or extra:
            seed_mismatch = True
            if absent:
                print(f"  MISSING seeds: {seed_ranges(absent)} (requested, never written)")
            if extra:
                print(f"  UNEXPECTED seeds: {seed_ranges(extra)} (written, never requested)")
        for (dataset, arm), seeds in sorted(groups.items()):
            if seeds != expected_set:
                seed_mismatch = True
                gap = seed_ranges(expected_set - seeds)
                print(
                    f"  INCOMPLETE {dataset}/{arm}: requested={seed_ranges(expected)} "
                    f"written={seed_ranges(seeds)} (missing {gap})"
                )
        if seed_mismatch:
            print("FAIL this batch did not write the seeds it was asked for")

    if verified == 0:
        print("FAIL no run declared a verifiable prediction hash -- nothing was checked")
        return EXIT_UNVERIFIED
    if mismatched or missing:
        print("FAIL the run's metrics are NOT recomputable from these files")
        return EXIT_UNVERIFIED
    if seed_mismatch:
        return EXIT_SEED_MISMATCH
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
