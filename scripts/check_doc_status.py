#!/usr/bin/env python3
"""Assert that every report states what it is.

Half the documents in docs/reports/ never say whether they describe the design as built or a plan
that has since been overtaken, so a reader arriving at one cannot tell which. This turns that into a
fix-list rather than an invisible risk.

A report satisfies the check if one of its first WINDOW lines is a bolded status marker, e.g.
    > **Status:** current as of 2026-09-14
    > **Historical document.** Superseded by ...
Prose that merely contains the word "current" does not pass: the marker has to lead a line.

Usage:
  python3 scripts/check_doc_status.py                     # list unlabelled reports; exit 1 if any
  python3 scripts/check_doc_status.py --warn              # list them, always exit 0
  python3 scripts/check_doc_status.py --dir docs/reports
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

WINDOW = 15
MARKER = re.compile(
    r"^\s*(?:>\s*)?[*_]{0,2}(status|current|superseded|historical|proposed|draft|archived)\b",
    re.IGNORECASE,
)


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
    parser.add_argument("--dir", default="docs/reports")
    parser.add_argument("--warn", action="store_true", help="report but never fail")
    args = parser.parse_args(argv)

    root = pathlib.Path(args.dir)
    if not root.is_dir():
        print(f"  no such directory: {root}")
        return 2

    missing, total = unlabelled(root)
    for name in missing:
        print(f"  unlabelled: {name}")
    print(f"  {total - len(missing)}/{total} reports state their status (first {WINDOW} lines)")

    if missing and not args.warn:
        print("  FAIL: a report that does not say what it is cannot be trusted to be current")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
