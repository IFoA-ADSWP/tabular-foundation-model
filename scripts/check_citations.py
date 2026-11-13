#!/usr/bin/env python3
"""The citation check: a run cited in `docs/` must have a capture (#364).

A **citation** is a bare run id (`YYYYMMDDTHHMMSSZ`) in any file under `docs/`. A cited run must
have `results/<id>/capture.json` whose entries cover every method × arm × seed × fold present in
the run with non-null hashes. A `schema_version: 2` capture also requires each record to name
`versions.tabpfn`, `versions.python` and `weights.path` or `weights.sha256`. A `schema_version: 4`
capture additionally owes `weights_sha256` and `cluster_sha256` on every severity entry (#555), and
is refused if a frequency entry carries them. A `schema_version: 5` capture adds the method axis
(#597): every entry and record names its `method`, `quantiles` is required exactly when the record
declares `quantile_levels`, and a non-TabPFN method owes an interpreter and a library version
instead of TabPFN's checkpoint. A version this gate does not know is refused, not guessed. Ids
predating the rule live in `docs/analyses/legacy_citations.txt`; that file is append-only and may
not gain an id from after the rule date.

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
    """One method × (arm) × seed × fold record a capture must cover."""

    method: Optional[str]
    arm: Optional[str]
    seed: int
    fold: Optional[int]
    record: Path


def expected_entries(run_dir: Path) -> list[Expected]:
    """The method × arm × seed × fold records the run's own records declare.

    `fold` is null in the original arm × seed runs and an integer in a folded run. Every field is
    read from the record, never inferred from the directory name: a baseline's directory is named
    after its method and its `arm` is null (#597).
    """
    expected: list[Expected] = []
    for meta in run_dir.glob("**/seed*_fold*/meta.json"):
        record = json.loads(meta.read_text())
        method = record.get("method")
        arm = record["arm"] if "arm" in record else meta.parent.parent.name
        seed = record.get("seed")
        if seed is None:
            continue
        fold = record.get("fold")
        expected.append(
            Expected(
                method=method,
                arm=arm,
                seed=int(seed),
                fold=None if fold is None else int(fold),
                record=meta,
            )
        )
    return expected


def _declares_quantiles(record: dict) -> bool:
    """The v5 rule: a record owes quantiles exactly when it declares `quantile_levels`.

    This is a second copy of `run_capture.declares_quantiles` on purpose. The paid path imports
    this module through `scripts/gpu_helpers/verify_artifacts.py` with only `scripts/` on
    `sys.path` — it has no `src/` beside it — so a module-level import from `src` turns a
    legitimate capture into "not beside the verifier" (measured 2026-11-13). `tests/
    test_check_citations.py` pins the two copies to each other, so they cannot drift.
    """
    return record.get("quantile_levels") is not None


def _where(exp: "Expected") -> str:
    """The slot as an operator can find it, without inventing an Arm a baseline does not have."""
    label = " ".join(part for part in (exp.method, exp.arm) if part)
    return f"{label} seed {exp.seed} fold {exp.fold}"


def _environment_problems(run_id: str, exp: Expected, entry: dict, version: int) -> list[str]:
    """The record fields that make the environment checkable (#506, #597).

    A capture entry points at a `meta.json`; that record must name the package that ran it, the
    interpreter, and (for TabPFN) the weights. The field names are the existing provenance
    block's — `versions.tabpfn`, `versions.python`, `weights.path`/`weights.sha256` — so the gate
    does not invent a second spelling.

    A baseline is a different predictor, so it owes no `versions.tabpfn` and no weights: v5 asks
    it for the interpreter and at least one library version other than `python`, and asks TabPFN
    for exactly what v2–v4 asked.
    """
    try:
        record = json.loads(exp.record.read_text())
    except json.JSONDecodeError as exc:
        return [f"{run_id}: {exp.record} is not valid JSON ({exc})"]

    versions = record.get("versions") or {}
    weights = record.get("weights") or {}
    where = _where(exp)
    problems: list[str] = []
    if not versions.get("python"):
        problems.append(f"{run_id}: {where} record has no versions.python")
    if version >= 5 and not exp.method:
        # The record is where a method is recorded, never inferred from a default.
        problems.append(f"{run_id}: {where} v5 record has no method")

    tabpfn_slot = version < 5 or exp.method == "tabpfn"
    if tabpfn_slot:
        if not versions.get("tabpfn"):
            problems.append(f"{run_id}: {where} record has no versions.tabpfn")
        if not (weights.get("path") or weights.get("sha256")):
            problems.append(f"{run_id}: {where} record has no weights.path or weights.sha256")
    elif not [key for key in versions if key != "python"]:
        problems.append(
            f"{run_id}: {where} record names no library version for method {exp.method!r}"
        )
    return problems


def _array_problems(
    run_id: str, exp: "Expected", entry: dict, dataset: str | None, version: int
) -> list[str]:
    """A v3+ entry hashes every array its dataset owes (#538, #597).

    `test_index` is required everywhere, and `exposure` only for freMTPL2freq, so an honest
    severity run is not refused for lacking a column its dataset does not have. `quantiles` is
    required on v3/v4; on v5 it is required exactly when the record declares
    `quantile_levels`, and refused when it does not — the same rule the writer applies.
    """
    where = _where(exp)
    required = ["test_index_sha256"]
    declared_quantiles = True
    if version >= 5:
        try:
            record = json.loads(exp.record.read_text())
        except json.JSONDecodeError as exc:
            return [f"{run_id}: {exp.record} is not valid JSON ({exc})"]
        declared_quantiles = _declares_quantiles(record)
    if declared_quantiles:
        required.append("quantiles_sha256")
    if dataset == "freMTPL2freq":
        required.append("exposure_sha256")
    problems = [
        f"{run_id}: {where} v{version} entry has no {key}"
        for key in required
        if not entry.get(key)
    ]
    if not declared_quantiles and entry.get("quantiles_sha256"):
        problems.append(
            f"{run_id}: {where} v{version} entry carries quantiles_sha256 but its record "
            "declares no quantile_levels"
        )
    if dataset != "freMTPL2freq" and entry.get("exposure_sha256"):
        problems.append(
            f"{run_id}: {where} v{version} entry carries exposure_sha256 for dataset {dataset!r}"
        )
    return problems


def _record_problems(
    run_id: str, exp: "Expected", entry: dict, version: int
) -> list[str]:
    """The record keys that make the retained arrays interpretable (#538, #597).

    `quantile_levels` is the one field without which nine rows of quantiles cannot be read (and on
    v5 the null declaration is itself the statement that the method has no distribution), and
    `verdict_metric` is what stops a rescorer reading RMSE as a deviance.
    """
    try:
        record = json.loads(exp.record.read_text())
    except json.JSONDecodeError as exc:
        return [f"{run_id}: {exp.record} is not valid JSON ({exc})"]

    where = _where(exp)
    required = ("verdict_metric", "verdict_metric_value", "rmse")
    problems = [
        f"{run_id}: {where} v{version} record has no {key}"
        for key in required
        if record.get(key) is None
    ]
    if "quantile_levels" not in record or (
        version < 5 and record.get("quantile_levels") is None
    ):
        problems.append(f"{run_id}: {where} v{version} record has no quantile_levels")
    return problems


def _weight_problems(
    run_id: str, exp: "Expected", entry: dict, version: int
) -> list[str]:
    """v4+ carries the two arrays a grouped severity target needs (#555, #564).

    The writer refuses a frequency slot that declares them, so the same rule runs here: a
    weight without a cluster (or the pair on a frequency target) is not a richer capture, it
    is a capture whose reader cannot tell which rows were weighted.
    """
    try:
        record = json.loads(exp.record.read_text())
    except json.JSONDecodeError as exc:
        return [f"{run_id}: {exp.record} is not valid JSON ({exc})"]

    where = _where(exp)
    keys = ("weights_sha256", "cluster_sha256")
    if record.get("task") == "severity":
        return [
            f"{run_id}: {where} v{version} severity entry has no {key}"
            for key in keys
            if not entry.get(key)
        ]
    return [
        f"{run_id}: {where} v{version} frequency entry carries {key}"
        for key in keys
        if entry.get(key)
    ]


def check_run_dir(run_dir: Path, run_id: str) -> list[str]:
    """Every reason this run directory is not capturable. Empty means fine."""
    run_dir = Path(run_dir)
    manifest_path = run_dir / "capture.json"
    if not manifest_path.is_file():
        where = "no run directory" if not run_dir.is_dir() else "no capture.json"
        return [f"{run_id}: cited but {where} under results/"]

    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as exc:
        return [f"{run_id}: capture.json is not valid JSON ({exc})"]

    version = manifest.get("schema_version")
    if version not in (1, 2, 3, 4, 5):
        return [
            f"{run_id}: capture.json schema_version {version!r} "
            "is not 1, 2, 3, 4 or 5"
        ]

    entries = {
        (e.get("method"), e.get("arm"), e.get("seed"), e.get("fold")): e
        for e in manifest.get("captures", [])
    }
    expected = expected_entries(run_dir)
    problems: list[str] = []
    for exp in sorted(
        expected,
        key=lambda e: (e.method or "", e.arm or "", e.seed, -1 if e.fold is None else e.fold),
    ):
        entry = entries.get((exp.method, exp.arm, exp.seed, exp.fold))
        if entry is None:
            problems.append(
                f"{run_id}: capture.json has no entry for "
                f"{_where(exp)}"
            )
            continue
        if not entry.get("predictions_sha256") or not entry.get("truth_sha256"):
            reason = entry.get("reason") or "no reason recorded"
            problems.append(
                f"{run_id}: {_where(exp)} "
                f"was not retained ({reason})"
            )
        if version in (3, 4, 5):
            problems.extend(
                _array_problems(run_id, exp, entry, manifest.get("dataset"), version)
            )
            problems.extend(_record_problems(run_id, exp, entry, version))
        if version in (4, 5):
            problems.extend(_weight_problems(run_id, exp, entry, version))
        if version in (2, 3, 4, 5):
            # v3 is a superset of v2, v4 of v3 and v5 of v4: the environment fields are still
            # required, with the method axis deciding which ones.
            problems.extend(_environment_problems(run_id, exp, entry, version))
    if not expected:
        problems.append(
            f"{run_id}: no slot records found, so the capture cannot be checked"
        )
    return problems


def check_run(root: Path, run_id: str) -> list[str]:
    """The `results/<id>/` form of `check_run_dir`, for the repository-wide check."""
    return check_run_dir(root / "results" / run_id, run_id)


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
