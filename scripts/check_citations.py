#!/usr/bin/env python3
"""The citation check: a run cited in `docs/` must have a capture (#364).

A **citation** is a bare run id (`YYYYMMDDTHHMMSSZ`) in any file under `docs/`. A cited run must
have `results/<id>/capture.json` whose entries cover every arm × seed present in the run with
non-null hashes. Ids predating the rule live in `docs/analyses/legacy_citations.txt`; that file is
append-only and may not gain an id from after the rule date.

Conversation is not citation: issue text and commit messages are not scanned, deliberately.

Usage:
    python scripts/check_citations.py [--root REPO]

Exit codes: 0 all citations resolvable (or exempt) · 1 at least one cannot be resolved.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# A run id, not a launch id: the lease label is `<run id>-<hex>`, so a trailing `-`
# means this is a launch and the capture lives under the run it names.
RUN_ID = re.compile(r"(?<![0-9A-Za-z])\d{8}T\d{6}Z(?![0-9A-Za-z-])")
RULE_DATE = "20261031T000000Z"
LEGACY = Path("docs/analyses/legacy_citations.txt")
SCANNED_SUFFIXES = {".md", ".csv", ".txt"}


def cited(root: Path) -> dict[str, set[tuple[str, int]]]:
    """Every run id mentioned under docs/, with the `(file, line)` that mention it.

    The line matters as much as the file: when the check refuses a citation the operator's next
    action is to open the document, and an id can appear several times in one note.
    """
    found: dict[str, set[tuple[str, int]]] = {}
    docs = root / "docs"
    if not docs.is_dir():
        return found
    for path in sorted(docs.rglob("*")):
        if not path.is_file() or path.suffix not in SCANNED_SUFFIXES:
            continue
        if path.name == LEGACY.name:
            continue  # the list itself names ids; it is not a citation
        text = path.read_text(errors="ignore")
        relative = str(path.relative_to(root))
        for match in RUN_ID.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            found.setdefault(match.group(), set()).add((relative, line))
    return found


def legacy_ids(root: Path) -> set[str]:
    path = root / LEGACY
    if not path.is_file():
        return set()
    ids = {
        line.strip()
        for line in path.read_text().splitlines()
        if RUN_ID.fullmatch(line.strip())
    }
    return ids


def expected_entries(run_dir: Path) -> set[tuple[str, int]]:
    """The arm × seed pairs the run's own records declare."""
    pairs: set[tuple[str, int]] = set()
    for meta in run_dir.glob("**/seed*_fold*/meta.json"):
        record = json.loads(meta.read_text())
        arm = record.get("arm") or meta.parent.parent.name
        seed = record.get("seed")
        if seed is not None:
            pairs.add((arm, int(seed)))
    return pairs


def check_run(root: Path, run_id: str) -> list[str]:
    """Every reason this cited run is not capturable. Empty means fine."""
    run_dir = root / "results" / run_id
    manifest_path = run_dir / "capture.json"
    if not manifest_path.is_file():
        where = "no run directory" if not run_dir.is_dir() else "no capture.json"
        return [f"{run_id}: cited but {where} under results/"]

    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as exc:
        return [f"{run_id}: capture.json is not valid JSON ({exc})"]

    if manifest.get("schema_version") != 1:
        return [
            f"{run_id}: capture.json schema_version {manifest.get('schema_version')!r} is not 1"
        ]

    entries = {(e.get("arm"), e.get("seed")): e for e in manifest.get("captures", [])}
    problems: list[str] = []
    for arm, seed in sorted(expected_entries(run_dir)):
        entry = entries.get((arm, seed))
        if entry is None:
            problems.append(
                f"{run_id}: capture.json has no entry for {arm} seed {seed}"
            )
        elif not entry.get("predictions_sha256") or not entry.get("truth_sha256"):
            reason = entry.get("reason") or "no reason recorded"
            problems.append(f"{run_id}: {arm} seed {seed} was not retained ({reason})")
    if not expected_entries(run_dir):
        problems.append(
            f"{run_id}: no arm records found, so the capture cannot be checked"
        )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root")
    args = parser.parse_args(argv)
    root = args.root.resolve()

    exempt = legacy_ids(root)
    stale = sorted(run_id for run_id in exempt if run_id >= RULE_DATE)
    if stale:
        print(
            "citation: legacy_citations.txt lists ids from after the rule date:",
            file=sys.stderr,
        )
        for run_id in stale:
            print(f"  {run_id}", file=sys.stderr)
        print("  Only pre-rule citations may be exempt.", file=sys.stderr)
        return 1

    mentions = cited(root)
    problems: list[str] = []
    checked = 0
    for run_id in sorted(mentions):
        if run_id in exempt:
            continue
        checked += 1
        reasons = check_run(root, run_id)
        if not reasons:
            continue
        # check_run reports *why* the run cannot be re-derived; the location is where it was
        # cited, which check_run has no reason to know. Kept separate so each stays testable.
        where = ", ".join(f"{path}:{line}" for path, line in sorted(mentions[run_id]))
        problems.extend(f"{reason}\n    — cited at {where}" for reason in reasons)

    exempt_count = len(set(mentions) & exempt)
    print(f"citations: {len(mentions)} cited, {exempt_count} exempt, {checked} checked")
    if problems:
        print("citation: cited runs that cannot be re-derived:", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        print(
            "  Retain a capture (scripts/analyses/make_capture.py), or cite an exempt run.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
