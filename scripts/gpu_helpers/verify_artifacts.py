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

Note the subtlety in (3): `meta.json` records the hash of the ARRAY's bytes
(`array.tobytes()`), not of the `.npy` container, so hashing the file directly would
always mismatch. `npy_data_sha256` parses the `.npy` header and hashes only the data
payload -- pure stdlib, so no numpy is needed on the receiving side.

Exit codes:
    0  payload restored and every declared prediction verified
    3  no usable payload (absent, or declared empty)
    4  payload incomplete (short read, checksum mismatch, or unpack failure)
    5  payload restored but prediction verification FAILED
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


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify the container-log artifact payload")
    ap.add_argument("--raw", required=True, help="captured container log")
    ap.add_argument("--dest", required=True, help="where to unpack the payload")
    ap.add_argument(
        "--verify-only",
        action="store_true",
        help="skip unpacking; verify predictions already present in --dest",
    )
    args = ap.parse_args()

    if args.verify_only:
        rc, report = EXIT_OK, f"verifying existing payload in {args.dest}"
    else:
        if not os.path.exists(args.raw):
            print(f"FAIL missing captured log: {args.raw}")
            return EXIT_NO_PAYLOAD
        with open(args.raw, errors="replace") as f:
            raw = f.read()
        rc, report = restore(raw, args.dest)

    print(f"{'OK' if rc == EXIT_OK else 'FAIL'} {report}")
    if rc != EXIT_OK:
        return rc

    verified, mismatched, missing, details = verify_predictions(args.dest)
    for line in details:
        print(line)
    print(f"VERIFY predictions verified={verified} mismatched={mismatched} missing={missing}")

    if verified == 0:
        print("FAIL no run declared a verifiable prediction hash -- nothing was checked")
        return EXIT_UNVERIFIED
    if mismatched or missing:
        print("FAIL the run's metrics are NOT recomputable from these files")
        return EXIT_UNVERIFIED
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
