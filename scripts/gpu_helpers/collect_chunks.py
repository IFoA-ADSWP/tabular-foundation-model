#!/usr/bin/env python3
"""Merge the chunked artifact payloads out of successive container-log polls (#564).

WHY THIS EXISTS

The log is the only transport this account has: `--transport ssh` needs an SSH key the
team context refuses to register, and the window a single poll can read is
`--tail 20000` lines x 440 characters, about 6.6 MB. A fair-test capture is ~30 MB per
target, so `emit_artifacts.sh` prints it as sequence-numbered chunks, paced so that each
one outlives several polls, and this script stitches the polls back together.

THE SHAPE IT RELIES ON

    __ARTIFACTS_INFO__ bytes=<n> sha256=<hex> lines=<n> files=<n> payload=<run id> chunks=<n>
    __ARTIFACTS_BEGIN__
    __ART_CHUNK__ seq=<i>/<n> payload=<run id> lines=<k>
    __ART__<440-char base64 line>
    ...
    __ART_CHUNK_END__
    __ARTIFACTS_END__

A chunk is sealed only on `__ART_CHUNK_END__`, so a poll that lands mid-chunk leaves it
unsealed rather than half-assembled. Chunks already on disk are never rewritten, so
repeated polls -- which re-read overlapping windows -- cannot duplicate one. `seq` is
the identity; the whole-payload sha256 on the INFO line remains the integrity check.

    collect_chunks.py merge    --window LOG --state DIR
    collect_chunks.py assemble --state DIR --out RAW

`merge` ingests one polled window and reports progress. `assemble` writes a raw log the
existing verifier can read, and REFUSES -- naming each missing seq -- when a payload is
incomplete, rather than letting a short read look like a clean transfer.

Exit codes: 0 complete · 1 incomplete (missing chunks named) · 2 usage error.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

INFO = "__ARTIFACTS_INFO__"
BEGIN = "__ARTIFACTS_BEGIN__"
END = "__ARTIFACTS_END__"
CHUNK = "__ART_CHUNK__"
CHUNK_END = "__ART_CHUNK_END__"
LINE_TAG = "__ART__"

CHUNK_RE = re.compile(r"^__ART_CHUNK__ seq=(\d+)/(\d+)(?:\s+payload=(\S+))?(?:\s+lines=(\d+))?\s*$")
INFO_RE = re.compile(r"^__ARTIFACTS_INFO__ (.+)$")


def _info_fields(line: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    match = INFO_RE.match(line)
    if not match:
        return fields
    for token in match.group(1).split():
        if "=" in token:
            key, value = token.split("=", 1)
            fields[key] = value
    return fields


def _payload_dir(state: Path, payload: str) -> Path:
    path = state / payload
    path.mkdir(parents=True, exist_ok=True)
    return path


def declared_chunks(directory: Path) -> int | None:
    """How many chunks a payload declared, or None when its INFO line was never seen.

    None is not zero: an unknown count cannot be reported as complete, and treating it as 0
    would let a payload whose declaration scrolled away assemble as an empty success.
    """
    meta = directory / "meta.json"
    if not meta.is_file():
        return None
    try:
        record = json.loads(meta.read_text())
    except (json.JSONDecodeError, ValueError):
        return None
    declared = record.get("chunks")
    if declared is None:
        return None
    try:
        return int(declared)
    except (TypeError, ValueError):
        return None


def merge_window(window: Path, state: Path) -> dict[str, dict[str, int]]:
    """Ingest one polled window. Returns payload -> {chunks, expected}."""
    if not window.is_file():
        return {}
    text = window.read_text(errors="replace").splitlines()

    current_payload: str | None = None
    buffering: list[str] | None = None
    seq: int | None = None
    # How many payload lines the box declared for the chunk being read. Completion is checked
    # against this COUNT, not against `__ART_CHUNK_END__` (#566): the log reflows lines at the
    # window's edge, so an end marker can arrive glued to a truncated line, and a chunk is
    # whole exactly when it has as many lines as its marker promised.
    want: int | None = None
    sealed: dict[str, int] = {}

    def seal() -> None:
        nonlocal buffering, seq, want, current_payload
        if buffering is None or seq is None or current_payload is None:
            buffering, seq, want = None, None, None
            return
        if want is not None and len(buffering) < want:
            # Short: a truncated tail, not a whole chunk. Drop it and let the repeat pass win.
            buffering, seq, want = None, None, None
            return
        directory = _payload_dir(state, current_payload)
        target = directory / f"{seq:03d}.txt"
        if not target.exists():
            kept = buffering if want is None else buffering[:want]
            target.write_text("".join(line + "\n" for line in kept))
        sealed[current_payload] = max(sealed.get(current_payload, 0), seq)
        buffering, seq, want = None, None, None

    def start_chunk(line: str) -> None:
        nonlocal seq, want, buffering, current_payload
        match = CHUNK_RE.match(line)
        if not match:
            seq, want, buffering = None, None, None
            return
        seq = int(match.group(1))
        if match.group(3):
            current_payload = match.group(3)
        want = int(match.group(4)) if match.group(4) else None
        buffering = []

    for line in text:
        if line.startswith(INFO):
            fields = _info_fields(line)
            payload = fields.get("payload", "default")
            count = fields.get("chunks")
            # No `chunks=` means a single block (the pilot and benchmark framing); a count
            # that is not a number is recorded as null, which `declared_chunks` reads as
            # unknown rather than as a complete payload of zero chunks.
            declared = int(count) if count is not None and count.isdigit() else (None if count is not None else 1)
            meta_path = state / payload / "meta.json"
            # The first INFO wins: it declares the payload the box produced, and a later
            # poll cannot know better than the box did.
            if not meta_path.exists():
                meta_path.parent.mkdir(parents=True, exist_ok=True)
                meta_path.write_text(
                    json.dumps({"info": line, "payload": payload, "chunks": declared}, indent=2)
                    + "\n"
                )
            current_payload = payload
            continue
        if line.startswith(CHUNK):
            seal()
            start_chunk(line)
            continue
        if line.startswith(CHUNK_END):
            seal()
            continue
        if line.startswith(END):
            seal()
            continue
        if CHUNK in line:
            # A marker can arrive glued to the tail of a payload line: the log reflows at the
            # window's edge. Base64 cannot contain '_', so a marker token inside a line is
            # never data.
            prefix, _, rest = line.partition(CHUNK)
            if buffering is not None and prefix.startswith(LINE_TAG):
                buffering.append(prefix)
            else:
                buffering = None
            seal()
            start_chunk(CHUNK + rest)
            continue
        if CHUNK_END in line:
            # End marker glued to a truncated payload line: short of `want`, so refused above.
            buffering, seq, want = None, None, None
            continue
        if buffering is not None and line.startswith(LINE_TAG):
            buffering.append(line)

    # A window can end exactly at a chunk boundary, with no following marker to trigger the seal.
    seal()

    report: dict[str, dict[str, int]] = {}
    for payload in sorted(p.name for p in state.iterdir() if p.is_dir()):
        directory = state / payload
        have = len([p for p in directory.glob("[0-9][0-9][0-9].txt")])
        declared = declared_chunks(directory)
        report[payload] = {"chunks": have, "expected": declared if declared is not None else 0}
    return report


def missing_chunks(state: Path) -> dict[str, list[int] | None]:
    """Per payload, the sequence numbers the box declared and the log never carried.

    `None` means the payload's declaration never survived a poll: its chunks cannot be
    reported complete, and `assemble` refuses rather than writing a short archive.
    """
    gaps: dict[str, list[int] | None] = {}
    for directory in sorted(p for p in state.iterdir() if p.is_dir()):
        declared = declared_chunks(directory)
        if declared is None:
            gaps[directory.name] = None
            continue
        have = {int(p.stem) for p in directory.glob("[0-9][0-9][0-9].txt")}
        gaps[directory.name] = [seq for seq in range(1, declared + 1) if seq not in have]
    return gaps


def assemble(state: Path, out: Path) -> tuple[int, str]:
    """Write the reassembled raw log, or refuse and name the missing chunks."""
    gaps = missing_chunks(state)
    if not gaps:
        return 1, "INCOMPLETE no payload was collected"

    undeclared = sorted(payload for payload, seqs in gaps.items() if seqs is None)
    if undeclared:
        return 1, (
            "INCOMPLETE no declaration arrived for "
            + ", ".join(undeclared)
            + " (its INFO line never landed in a polled window)"
        )
    broken = {payload: seqs for payload, seqs in gaps.items() if seqs}
    if broken:
        detail = "; ".join(
            f"{payload}: missing seq {','.join(str(s) for s in seqs or [])}"
            for payload, seqs in sorted(broken.items())
        )
        return 1, f"INCOMPLETE {detail}"

    lines: list[str] = []
    for payload in sorted(gaps):
        directory = state / payload
        meta = json.loads((directory / "meta.json").read_text())
        lines.append(meta["info"])
        lines.append(BEGIN)
        for chunk in sorted(directory.glob("[0-9][0-9][0-9].txt")):
            lines.append(chunk.read_text().rstrip("\n"))
        lines.append(END)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    total = sum(len(list((state / p).glob("[0-9][0-9][0-9].txt"))) for p in gaps)
    return 0, f"ASSEMBLED payloads={len(gaps)} chunks={total} -> {out}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("merge", "assemble"))
    parser.add_argument("--window", type=Path, help="one polled log window (merge)")
    parser.add_argument("--state", type=Path, required=True, help="chunk accumulator directory")
    parser.add_argument("--out", type=Path, help="raw log to write (assemble)")
    args = parser.parse_args(argv)

    if args.command == "merge":
        if args.window is None:
            parser.error("merge needs --window")
        args.state.mkdir(parents=True, exist_ok=True)
        report = merge_window(args.window, args.state)
        if report:
            summary = " ".join(
                f"{payload}={row['chunks']}/{row['expected'] or '?'}"
                for payload, row in report.items()
            )
            print(f"CHUNKS {summary}")
        return 0

    if args.out is None:
        parser.error("assemble needs --out")
    if not args.state.is_dir():
        print("INCOMPLETE no chunks were collected")
        return 1
    rc, report = assemble(args.state, args.out)
    print(report)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
