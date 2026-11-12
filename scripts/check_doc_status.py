#!/usr/bin/env python3
"""Assert that every report states what it is.

Half the documents in the report tiers never say whether they describe the design as built or a plan
that has since been overtaken, so a reader arriving at one cannot tell which. This turns that into a
fix-list rather than an invisible risk.

The tiers are checked together because they are one collection: a report moved from current/ to
archive/ stays the same document and must not leave the check by being moved. `--dir` remains
available for checking a single directory.

A report satisfies the check if one of its first WINDOW lines is a bolded status marker, e.g.
    > **Status:** current as of 2026-09-14
    > **Historical document.** Superseded by ...
Prose that merely contains the word "current" does not pass: the marker has to lead a line.

The same script enforces the claim registry's shape. `docs/current/FINETUNING_FINDINGS.md` is a pointer,
not a store: a row that restates a number its owning document owns goes stale silently, which is how two
rows kept asserting what their owners had contradicted. Each row must be Claim | Status | Owner, and no
claim cell may contain a digit. Row references (F1, L3) and ISO dates are identifiers, not measurements, so
they are stripped first.

Usage:
  python3 scripts/check_doc_status.py                     # list unlabelled reports; exit 1 if any
  python3 scripts/check_doc_status.py --warn              # list them, always exit 0
  python3 scripts/check_doc_status.py --dir docs/archive  # check one directory (repeatable)
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

WINDOW = 15
# The three report tiers. docs/reports/ was dissolved into these in #200-#202, and this script
# kept pointing at the dead path -- so the rule silently stopped being enforced for six weeks
# (it exited 2, and nobody reads an exit code that says "no such directory").
DEFAULT_DIRS = ("docs/current", "docs/reference", "docs/archive")
MARKER = re.compile(
    r"^\s*(?:>\s*)?[*_]{0,2}(status|current|superseded|historical|proposed|draft|archived)\b",
    re.IGNORECASE,
)

# The registry is checked only when the whole collection is being checked; --dir stays a
# per-directory status check. A missing registry is a failure, never a skip: a check that passes
# because its subject moved is worse than no check at all.
CLAIM_REGISTRY = pathlib.Path("docs/current/FINETUNING_FINDINGS.md")
ROW_REF = re.compile(r"\b[FL]\d+\b")
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
ANY_DIGIT = re.compile(r"\d")


def registry_problems(path: pathlib.Path) -> list[str]:
    """Return one line per registry row that restates a number or is not three columns."""
    if not path.exists():
        return [f"missing claim registry: {path}"]
    problems: list[str] = []
    for lineno, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
        text = line.strip()
        if not text.startswith("|"):
            continue
        cells = [cell.strip() for cell in text.strip("|").split("|")]
        label_match = ROW_REF.search(cells[0]) if cells else None
        label = label_match.group(0) if label_match else "claim"
        if len(cells) != 3:
            problems.append(f"{path}:{lineno}: {label} — a registry row is Claim | Status | Owner")
            continue
        residue = ANY_DIGIT.search(ISO_DATE.sub("", ROW_REF.sub("", cells[0])))
        if residue:
            problems.append(
                f"{path}:{lineno}: {label} restates a number — move it to the owner and link"
            )
    return problems


def unlabelled(root: pathlib.Path) -> tuple[list[str], int]:
    """Return (names of reports with no status marker, total reports)."""
    missing, total = [], 0
    for path in sorted(root.glob("*.md")):
        total += 1
        head = path.read_text(errors="replace").splitlines()[:WINDOW]
        if not any(MARKER.match(line) for line in head):
            missing.append(path.name)
    return missing, total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dir",
        action="append",
        default=None,
        metavar="DIR",
        help="directory of reports to check; repeat for several "
        f"(default: {' '.join(DEFAULT_DIRS)})",
    )
    parser.add_argument("--warn", action="store_true", help="report but never fail")
    args = parser.parse_args(argv)

    missing: list[str] = []
    total = 0
    for name in args.dir or list(DEFAULT_DIRS):
        root = pathlib.Path(name)
        if not root.is_dir():
            print(f"  no such directory: {root}")
            return 2
        dir_missing, dir_total = unlabelled(root)
        prefix = name.rstrip("/")
        missing.extend(f"{prefix}/{report}" for report in dir_missing)
        total += dir_total

    for name in missing:
        print(f"  unlabelled: {name}")
    print(f"  {total - len(missing)}/{total} reports state their status (first {WINDOW} lines)")

    registry: list[str] = []
    if args.dir is None:
        registry = registry_problems(CLAIM_REGISTRY)
        if registry:
            for problem in registry:
                print(f"  {problem}")
        else:
            print("  claim registry: every claim names its owner and carries no number")

    if (missing or registry) and not args.warn:
        if missing:
            print("  FAIL: a report that does not say what it is cannot be trusted to be current")
        if registry:
            print("  FAIL: a registry row that restates a number goes stale without anyone noticing")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
