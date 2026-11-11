#!/usr/bin/env python3
"""The citation check: a run cited in `docs/` must have a capture (#364).

A **citation** is a bare run id (`YYYYMMDDTHHMMSSZ`) in any file under `docs/`. A cited run must
have `results/<id>/capture.json` whose entries cover every arm × seed × fold present in the run
with non-null hashes. A `schema_version: 2` capture also requires each record to name
`versions.tabpfn`, `versions.python` and `weights.path` or `weights.sha256`. Ids predating the
rule live in `docs/analyses/legacy_citations.txt`; that file is append-only and may not gain an id
from after the rule date.

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
from typing import NamedTuple, Optional

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


class Expected(NamedTuple):
    """One arm × seed × fold record a capture must cover."""

    arm: str
    seed: int
    fold: Optional[int]
    record: Path


def expected_entries(run_dir: Path) -> list[Expected]:
    """The arm × seed × fold records the run's own records declare.

    `fold` is null in the original arm × seed runs and an integer in a folded run. The field is
    read from the record, never inferred from the directory name.
    """
    expected: list[Expected] = []
    for meta in run_dir.glob("**/seed*_fold*/meta.json"):
        record = json.loads(meta.read_text())
        arm = record.get("arm") or meta.parent.parent.name
        seed = record.get("seed")
        if seed is None:
            continue
        fold = record.get("fold")
        expected.append(
            Expected(
                arm=arm,
                seed=int(seed),
                fold=None if fold is None else int(fold),
                record=meta,
            )
        )
    return expected


def _environment_problems(run_id: str, exp: Expected, entry: dict) -> list[str]:
    """The v2 record fields that make the environment checkable (#506).

    A v2 capture entry points at a `meta.json`; that record must name the package that ran it,
    the interpreter, and the weights. The field names are the existing provenance block's —
    `versions.tabpfn`, `versions.python`, `weights.path`/`weights.sha256` — so the gate does not
    invent a second spelling.
    """
    try:
        record = json.loads(exp.record.read_text())
    except json.JSONDecodeError as exc:
        return [f"{run_id}: {exp.record} is not valid JSON ({exc})"]

    versions = record.get("versions") or {}
    weights = record.get("weights") or {}
    where = f"{exp.arm} seed {exp.seed} fold {exp.fold}"
    problems: list[str] = []
    if not versions.get("tabpfn"):
        problems.append(f"{run_id}: {where} record has no versions.tabpfn")
    if not versions.get("python"):
        problems.append(f"{run_id}: {where} record has no versions.python")
    if not (weights.get("path") or weights.get("sha256")):
        problems.append(f"{run_id}: {where} record has no weights.path or weights.sha256")
    return problems


def _array_problems(
    run_id: str, exp: "Expected", entry: dict, dataset: str | None
) -> list[str]:
    """A v3 entry hashes every array its dataset owes (#538).

    `test_index` and `quantiles` are required everywhere; `exposure` only for freMTPL2freq, so
    an honest severity run is not refused for lacking a column its dataset does not have.
    """
    where = f"{exp.arm} seed {exp.seed} fold {exp.fold}"
    required = ["test_index_sha256", "quantiles_sha256"]
    if dataset == "freMTPL2freq":
        required.append("exposure_sha256")
    problems = [
        f"{run_id}: {where} v3 entry has no {key}" for key in required if not entry.get(key)
    ]
    if dataset != "freMTPL2freq" and entry.get("exposure_sha256"):
        problems.append(
            f"{run_id}: {where} v3 entry carries exposure_sha256 for dataset {dataset!r}"
        )
    return problems


def _record_problems(run_id: str, exp: "Expected", entry: dict) -> list[str]:
    """The v3 record keys that make the retained arrays interpretable (#538).

    `quantile_levels` is the one field without which nine rows of quantiles cannot be read, and
    `verdict_metric` is what stops a rescorer reading RMSE as a deviance. The writer cannot check
    a record it does not write, so the gate does.
    """
    try:
        record = json.loads(exp.record.read_text())
    except json.JSONDecodeError as exc:
        return [f"{run_id}: {exp.record} is not valid JSON ({exc})"]

    where = f"{exp.arm} seed {exp.seed} fold {exp.fold}"
    required = ("verdict_metric", "verdict_metric_value", "rmse", "quantile_levels")
    return [f"{run_id}: {where} v3 record has no {key}" for key in required if record.get(key) is None]


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

    if manifest.get("schema_version") not in (1, 2, 3):
        return [
            f"{run_id}: capture.json schema_version {manifest.get('schema_version')!r} "
            "is not 1, 2 or 3"
        ]

    entries = {
        (e.get("arm"), e.get("seed"), e.get("fold")): e
        for e in manifest.get("captures", [])
    }
    expected = expected_entries(run_dir)
    problems: list[str] = []
    for exp in sorted(
        expected, key=lambda e: (e.arm, e.seed, -1 if e.fold is None else e.fold)
    ):
        entry = entries.get((exp.arm, exp.seed, exp.fold))
        if entry is None:
            problems.append(
                f"{run_id}: capture.json has no entry for "
                f"{exp.arm} seed {exp.seed} fold {exp.fold}"
            )
            continue
        if not entry.get("predictions_sha256") or not entry.get("truth_sha256"):
            reason = entry.get("reason") or "no reason recorded"
            problems.append(
                f"{run_id}: {exp.arm} seed {exp.seed} fold {exp.fold} "
                f"was not retained ({reason})"
            )
        if manifest.get("schema_version") == 3:
            problems.extend(
                _array_problems(run_id, exp, entry, manifest.get("dataset"))
            )
            problems.extend(_record_problems(run_id, exp, entry))
        if manifest.get("schema_version") in (2, 3):
            # v3 is a superset: the environment fields v2 required are still required.
            problems.extend(_environment_problems(run_id, exp, entry))
    if not expected:
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
