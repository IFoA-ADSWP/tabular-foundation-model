#!/usr/bin/env python3
"""Fail when the Pilot 2 documents disagree about the figures that matter.

WHY THIS EXISTS. The cost figures in these documents were recomputed several times as the model
was corrected, and each revision had to be carried into every place that quoted a number. On one
occasion a stale total (an execution-plan figure that counted two pooled arms where three run)
survived in two documents AND in the pull request title, while the corrected figure sat in a
third. No test looked at the documents, so nothing failed: the inconsistency was found by a human
sweeping for it.

A cost model that is recomputed must have a check that the recomputation reached every copy. That
is all this is.

TWO HARD RULES, and one report:

  A. A SUPERSEDED figure may not appear except on a line that marks it as superseded ("earlier",
     "superseded", "previous", "correction", ...). This is the rule that catches the defect above.
  B. Each CANONICAL figure must appear in at least one of the documents. This catches the opposite
     mistake -- adding a new document that quotes a figure nobody updated.
  C. (reported, not fatal) variant spellings of the same quantity, e.g. $367 next to $368.

USAGE
    python scripts/check_doc_figures.py [--docs-dir docs/reports] [--quiet]

Exit codes: 0 clean, 1 findings.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# --- the figures of record ---------------------------------------------------------------
# Keyed by the quantity, so a reader can see what each number MEANS rather than just its value.
CANONICAL: dict[str, list[str]] = {
    "steps 0-4, the recommended path": ["$4.70"],
    "the design as written, 15 repeats": ["$31"],
    "everything at full data scale": ["$368"],
    "available credit": ["$9.60"],
    "one successful four-dataset comparison": ["5p"],
    "the 7p ladder probe": ["7c"],
    "a designed interaction probe": ["$1.11"],
}

# Figures that were published at some point and have since been corrected. Any occurrence must
# be marked as historical on the same line.
SUPERSEDED: list[str] = [
    "$4.15",   # execution plan, before the pooled-arm count and the step-4 double-count were fixed
    "$15.05",  # the very first envelope, before measurement
    "$82.93",  # ditto, at full scale
    "$1.49",   # the first "lean" figure, before the two-experiment breakdown
    "$2.82",   # step 4 over four targets, when it is three
    "$4.08",   # transfer at 15 repeats, counted two pooled arms and 10 epochs
    "8-70c",   # step 3 before the same correction
    "58c",     # steps 0-4 at three epochs, before the correction
]

MARKERS: tuple[str, ...] = (
    "earlier", "supersed", "previous", "revision", "correction", "corrected", "historical",
    "no longer", "before the", "was ", "used to",
)

# Accepted alternative spellings of a canonical quantity: reported so the reader knows the
# documents round differently, but not treated as a defect.
VARIANTS: dict[str, str] = {"$367": "$368"}

_SKIP_SUFFIXES = (".md~", ".bak")


def docs_in(docs_dir: Path, pattern: str = "*.md") -> list[Path]:
    files = [p for p in sorted(docs_dir.glob(pattern)) if not p.name.endswith(_SKIP_SUFFIXES)]
    return [p for p in files if p.is_file()]


def find_superseded(files: list[Path]) -> list[str]:
    """Rule A: a superseded figure outside a line that marks it as historical."""
    findings = []
    for path in files:
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            lowered = line.lower()
            for pattern in SUPERSEDED:
                if pattern in line and not any(m in lowered for m in MARKERS):
                    findings.append(
                        f"{path}:{lineno}: superseded figure {pattern} with no historical marker "
                        f"on the line -- {line.strip()[:88]}"
                    )
    return findings


def find_missing_canonical(files: list[Path], docs_dir: Path) -> list[str]:
    """Rule B: a canonical figure that no document states at all."""
    text = "\n".join(p.read_text(encoding="utf-8") for p in files)
    findings = []
    for quantity, spellings in CANONICAL.items():
        if not any(s in text for s in spellings):
            findings.append(
                f"{docs_dir}: no document states the canonical figure for '{quantity}' "
                f"(looked for {', '.join(spellings)})"
            )
    return findings


def find_variants(files: list[Path]) -> list[str]:
    """Rule C: variant spellings, reported but not fatal."""
    notes = []
    for path in files:
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            for variant, canonical in VARIANTS.items():
                if variant in line and canonical not in line:
                    notes.append(
                        f"{path}:{lineno}: {variant} where the canonical spelling is {canonical} "
                        f"(rounding, not an error)"
                    )
    return notes


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "check doc figures").splitlines()[0])
    ap.add_argument("--docs-dir", default="docs/reports", type=Path)
    ap.add_argument("--pattern", default="PILOT_2_*.md")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    if not args.docs_dir.is_dir():
        print(f"ERROR: no such directory: {args.docs_dir}", file=sys.stderr)
        return 2
    files = docs_in(args.docs_dir, args.pattern)
    if not files:
        print(f"ERROR: no documents matched {args.pattern} in {args.docs_dir}", file=sys.stderr)
        return 2

    hard = find_superseded(files) + find_missing_canonical(files, args.docs_dir)
    soft = find_variants(files)

    if not args.quiet:
        print(f"checked {len(files)} document(s) in {args.docs_dir}")
        for note in soft:
            print(f"  note: {note}")
        for finding in hard:
            print(f"  FINDING: {finding}")

    if hard:
        print(f"\n{len(hard)} figure(s) disagree across the documents.")
        return 1
    if not args.quiet:
        print("all canonical figures are consistent; no superseded figure appears unmarked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
