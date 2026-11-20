#!/usr/bin/env python3
"""The fine-tuning runs ledger, generated from the committed evidence (#665).

    python scripts/analyses/finetuning_runs_ledger.py
    python scripts/analyses/finetuning_runs_ledger.py --out-csv /tmp/ledger.csv --out-doc /tmp/ledger.md

One row per run × arm × seed, written twice: as a CSV under `docs/analyses/data/` and as the
tables of `docs/experiments/pilot2-phase2/FINETUNING_RUNS_LEDGER.md`. The Markdown is rendered
from the CSV it has just written, so the two forms cannot disagree.

**The sources, and why they are read separately.**

- `results/<run>/` for the 23 Runs the `pilot2-phase2` campaign's own `## Runs` block names. The
  scope is read from that block rather than from a glob: six fair-test Run directories carry the
  same `A_raw` / `B_ft30` labels, and unrelated captures carry a null arm and a null dataset.
- `outputs/finetune/pilot/pilot_metrics.parquet` for the 2,000-row R1 pilot's 16 rows only. It is an
  aggregate, not a Run: no epochs are recorded (`max_finetune_steps` is a different parameter and the
  comparator rows carry it too), and no provenance.
- `outputs/gpu-pilot/runs/` for launch records with no `capture.json` — these are Rows with status
  `no-capture`, not Captures.
- One curated `no-capture` cell: the `spanish_motor_lapse` breadth replication, whose per-seed
  records were never committed. It is listed so the cell is not silently missing, with blank metrics,
  because inventing them would be worse than the absence.

The two sources are never joined on `run_id`: the aggregate's ids are synthetic
(`<dataset>_<arm>_seed<N>`) and Run ids are directory names.

**The traps, one line each.**

- Epochs are the record's `effective_config.kwargs.epochs`. `config.epochs` and every Run manifest
  read `3` for every arm; the 30-epoch arm reads 3 there and 30 in the record that trained it.
- The cell key includes `train_rows`: `uslapseagent` seed 42 exists at 2,000 rows and at 10,000.
- Replacement detection cannot work on this evidence, so it is an assertion (the Runs are
  seed-disjoint by construction) and the withdrawals are curated from the decision log.
- `model_version` is printed as recorded — `auto` — beside the checkpoint and the weights sha.
  Never `v3`: `auto` names no version.
- A per-seed record's own `run_id` is `<dataset>_<arm>_seed<N>`, not the Run id; the Run id is the
  directory.

Exit codes: 0 wrote both files · 1 the evidence disagrees with itself.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

_ANALYSES = Path(__file__).resolve().parent
_REPO = _ANALYSES.parents[1]

RESULTS = _REPO / "results"
CAMPAIGN_README = _REPO / "docs" / "experiments" / "pilot2-phase2" / "README.md"
PILOT_AGGREGATE = _REPO / "outputs" / "finetune" / "pilot" / "pilot_metrics.parquet"
GPU_PILOT_RUNS = _REPO / "outputs" / "gpu-pilot" / "runs"

CSV_PATH = _REPO / "docs" / "analyses" / "data" / "finetuning_runs_ledger.csv"
DOC_PATH = _REPO / "docs" / "experiments" / "pilot2-phase2" / "FINETUNING_RUNS_LEDGER.md"

COLUMNS = (
    "run_id",
    "experiment_family",
    "dataset",
    "arm",
    "arm_kind",
    "epochs",
    "seed",
    "train_rows",
    "roc_auc",
    "brier",
    "pr_auc",
    "status",
    "superseded_by",
    "superseded_reason",
    "note",
    "source",
    "model_version",
    "checkpoint",
    "weights_sha256",
)

# The three metrics the evidence records everywhere. `log_loss` and `ece` are recorded on every
# capture record and are deliberately out of the ledger, not missing from it.
METRICS = ("roc_auc", "brier", "pr_auc")

# `arm_kind` is derived, never recorded. A baseline is a Method in this repo's glossary, so the two
# comparator labels are not a fourth and fifth Arm of one kind.
COMPARATORS = {"E_glm", "F_catboost"}
FINE_TUNED_LABELS = {"B_in_domain"}

FT_LABEL = re.compile(r"^B_ft(\d+)$")

# Arm order for the table: the raw control, the epoch ladder, the pilot's own fine-tuned label, then
# the comparator Methods.
ARM_ORDER = {
    "A_raw": 0,
    "B_ft3": 1,
    "B_ft10": 2,
    "B_ft30": 3,
    "B_in_domain": 4,
    "E_glm": 5,
    "F_catboost": 6,
}

# The campaign's Runs block, read from the campaign index: `## Runs`, then the first fenced list.
RUNS_BLOCK = re.compile(r"^## Runs\s*\n.*?```\n(.*?)```", re.S | re.M)
RUN_ID = re.compile(r"^20\d{6}T\d{6}Z$")

# Curated withdrawals. Mechanical replacement detection returns zero on this evidence (the Runs are
# seed-disjoint by construction; three duplicate launches were discarded before commit and their ids
# are not in the tree), so supersession is a list with a decision beside it. D22 withdraws D21's
# *reasoning*, not its stop, so the row cites both: D21 is the stop, D22 the amendment.
WITHDRAWALS = (
    {
        "dataset": "coil2000",
        "train_rows": 2000,
        "decision": "D21",
        "amendment": "D22",
        "reason": (
            "coil2000 stopped on resolution — median half-width 0.0149 at the largest usable split "
            "against a 0.006 floor; D22 withdraws D21's seed-cost inference and leaves the stop "
            "resting on the P1 gate alone"
        ),
    },
)

# One curated `no-capture` cell. The breadth replication ran 16 fresh seeds (341-356) on
# `spanish_motor_lapse` at 10,000 rows; its records are runtime evidence on the launch machine and
# were never committed, so no per-seed row can be built without inventing one. The cell is listed
# with blank metrics and the document a reader should cite instead.
BREADTH_CELL = {
    "experiment_family": "pilot2-breadth-spanish",
    "dataset": "spanish_motor_lapse",
    "train_rows": 10000,
    "seed_range": "341-356",
    "arms": (("A_raw", None), ("B_ft30", 30)),
    "source": "docs/experiments/pilot2-phase2/finetuning_breadth_spanish_result.md",
    "note": (
        "breadth replication, seeds 341-356: no capture and no committed per-seed record — cite "
        "via finetuning_breadth_spanish_result.md, not a Capture"
    ),
}


# Where each family is read from, for the document's sources table. The per-row `source` column
# carries the exact file; this says what the family *is*.
SOURCE_ROOTS = {
    "pilot2-phase2": "`results/<run>/<dataset>/<arm>/seed<N>_foldNone/meta.json`, one directory per Run",
    "r1-pilot": "`outputs/finetune/pilot/pilot_metrics.parquet`",
    "gpu-pilot": "`outputs/gpu-pilot/runs/<run>/<dataset>/<arm>/meta.json`",
    "pilot2-breadth-spanish": "`docs/experiments/pilot2-phase2/finetuning_breadth_spanish_result.md`",
}


class EvidenceError(SystemExit):
    """The evidence disagrees with itself; the ledger refuses rather than smoothing it over."""


@dataclass(frozen=True)
class LedgerRow:
    run_id: str
    experiment_family: str
    dataset: str
    arm: str
    arm_kind: str
    epochs: int | None
    seed: int | None
    train_rows: int | None
    roc_auc: float | None
    brier: float | None
    pr_auc: float | None
    status: str
    superseded_by: str = ""
    superseded_reason: str = ""
    note: str = ""
    source: str = ""
    model_version: str = ""
    checkpoint: str = ""
    weights_sha256: str = ""

    @property
    def cell(self) -> tuple:
        """The identity of one measurement. `train_rows` is in the key on purpose."""
        return (self.dataset, self.arm, self.seed, self.train_rows)


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(_REPO).as_posix()
    except ValueError:
        return path.as_posix()


def arm_kind(arm: str) -> str:
    """The kind of an arm label. Derived, and the derivation is declared in the document."""
    if arm == "A_raw":
        return "raw"
    if arm in COMPARATORS:
        return "comparator"
    if arm in FINE_TUNED_LABELS or FT_LABEL.match(arm):
        return "fine-tuned"
    raise EvidenceError(f"unknown arm label {arm!r}: no arm_kind can be derived from it")


def epochs_from_record(record: dict) -> int | None:
    """The epochs the record says actually ran.

    `effective_config.kwargs.epochs` is the only honest source. The sibling `config.epochs` is the
    job's *source* config and reads 3 on every record; the Run manifest reads 3 as well. Reading
    either would label a 30-epoch arm as 3 epochs.
    """
    kwargs = (record.get("effective_config") or {}).get("kwargs") or {}
    epochs = kwargs.get("epochs")
    return None if epochs is None else int(epochs)


def assert_epoch_agrees(arm: str, epochs: int | None) -> None:
    """A `B_ftN` label and its record must name the same epoch count.

    A disagreement fails the ledger rather than being smoothed: the label is what a reader quotes
    and the record is what trained. An arm without an `ftN` label that nevertheless records an
    epoch count is refused too — there is no label to check it against.
    """
    match = FT_LABEL.match(arm)
    if match:
        expected = int(match.group(1))
        if epochs != expected:
            raise EvidenceError(
                f"{arm}: the record trained {epochs} epoch(s), the label names {expected}"
            )
        return
    if epochs is not None:
        raise EvidenceError(
            f"{arm}: records {epochs} epoch(s) but carries no ftN label to check it against"
        )


def assert_seed_disjoint(rows) -> None:
    """No cell may repeat: the committed evidence is seed-disjoint by construction.

    Every row is checked, whatever its status. A repeat is either evidence the generator has read the
    same record twice, or a replacement that mechanical detection would have to mark. Both are
    failures here: on this evidence the correct answer is zero repeats, and a silently accepted
    duplicate would mark real evidence superseded.
    """
    seen: dict[tuple, LedgerRow] = {}
    for row in rows:
        previous = seen.get(row.cell)
        if previous is not None:
            raise EvidenceError(
                "the ledger's key repeats: "
                f"{row.cell} appears in {previous.run_id} and {row.run_id}"
            )
        seen[row.cell] = row


def campaign_runs(readme: Path) -> list[str]:
    """The Run ids the campaign's own index declares, in its order."""
    if not readme.is_file():
        raise EvidenceError(f"missing campaign index: {_relative(readme)}")
    match = RUNS_BLOCK.search(readme.read_text())
    if match is None:
        raise EvidenceError(f"{_relative(readme)}: no '## Runs' block to scope the ledger by")
    runs = [line.strip() for line in match.group(1).splitlines() if line.strip()]
    odd = [run for run in runs if not RUN_ID.match(run)]
    if odd:
        raise EvidenceError(f"{_relative(readme)}: not run ids in the Runs block: {odd}")
    if not runs:
        raise EvidenceError(f"{_relative(readme)}: the Runs block is empty")
    return runs


def _cell_metrics(record: dict) -> dict[str, float]:
    missing = [metric for metric in METRICS if record.get(metric) is None]
    if missing:
        raise EvidenceError(
            f"{record.get('run_id')}: no {', '.join(missing)} — the ledger does not invent one"
        )
    return {metric: float(record[metric]) for metric in METRICS}


def capture_rows(results: Path = RESULTS, readme: Path = CAMPAIGN_README) -> list[LedgerRow]:
    """One row per captured arm × seed record, for the Runs the campaign names.

    The Run id is the directory's, never the record's: a record's own `run_id` is
    `<dataset>_<arm>_seed<N>`. The record itself lives at
    `results/<run>/<dataset>/<arm>/<seed>_foldNone/`, because `capture.json`'s `record` omits the
    dataset level.
    """
    rows: list[LedgerRow] = []
    for run_id in campaign_runs(readme):
        run_dir = results / run_id
        capture_path = run_dir / "capture.json"
        if not capture_path.is_file():
            raise EvidenceError(
                f"{run_id} is named by the campaign index but has no capture.json under results/"
            )
        capture = json.loads(capture_path.read_text())
        dataset = capture.get("dataset")
        if not dataset:
            raise EvidenceError(f"{run_id}: capture.json names no dataset")

        covered: set[Path] = set()
        for entry in capture.get("captures", []):
            record_path = run_dir / dataset / entry["record"]
            if not record_path.is_file():
                raise EvidenceError(f"{run_id}: capture entry {entry['record']} has no record")
            covered.add(record_path.resolve())
            record = json.loads(record_path.read_text())

            arm = record.get("arm") or entry.get("arm")
            if arm is None:
                raise EvidenceError(f"{run_id}: {entry['record']} names no arm")
            if record.get("dataset") and record["dataset"] != dataset:
                raise EvidenceError(
                    f"{run_id}: {entry['record']} is {record['dataset']}, the capture is {dataset}"
                )
            if record.get("status") != "success":
                raise EvidenceError(
                    f"{run_id}: {entry['record']} is {record.get('status')!r}, not a success"
                )

            epochs = epochs_from_record(record)
            assert_epoch_agrees(arm, epochs)
            seed = record.get("seed", entry.get("seed"))
            metrics = _cell_metrics(record)
            provenance = record.get("provenance") or {}
            model = provenance.get("model") or {}
            checkpoints = record.get("checkpoints") or []

            rows.append(
                LedgerRow(
                    run_id=run_id,
                    experiment_family="pilot2-phase2",
                    dataset=dataset,
                    arm=arm,
                    arm_kind=arm_kind(arm),
                    epochs=epochs,
                    seed=None if seed is None else int(seed),
                    train_rows=record.get("train_rows"),
                    roc_auc=metrics["roc_auc"],
                    brier=metrics["brier"],
                    pr_auc=metrics["pr_auc"],
                    status="current",
                    source=_relative(record_path),
                    model_version=model.get("version", ""),
                    checkpoint=checkpoints[0] if checkpoints else "",
                    weights_sha256=model.get("weights_sha256", ""),
                    note="" if model.get("version") == "auto" else "model version not recorded",
                )
            )

        stray = sorted(
            path.resolve()
            for path in run_dir.glob("*/*/seed*_fold*/meta.json")
            if path.resolve() not in covered
        )
        if stray:
            raise EvidenceError(
                f"{run_id}: {len(stray)} record(s) are not covered by capture.json, e.g. "
                f"{_relative(stray[0])}"
            )
    return rows


def pilot_rows(aggregate: Path = PILOT_AGGREGATE) -> list[LedgerRow]:
    """The 2,000-row R1 pilot's 16 aggregate rows, and nothing else from that file.

    Epochs stay blank: the file records `max_finetune_steps`, which is a different parameter and is
    carried by the comparator rows as well, so it cannot be read as an arm-level epoch count. There
    is no provenance block, so the model version and the weights sha stay blank rather than being
    borrowed from the captures.
    """
    import pandas as pd

    if not aggregate.is_file():
        raise EvidenceError(f"missing pilot aggregate: {_relative(aggregate)}")
    frame = pd.read_parquet(aggregate)

    rows: list[LedgerRow] = []
    for record in frame.to_dict("records"):
        arm = record["arm"]
        kind = arm_kind(arm)
        withdrawn = next(
            (
                item
                for item in WITHDRAWALS
                if item["dataset"] == record["dataset"]
                and int(item["train_rows"]) == int(record["train_rows"])
            ),
            None,
        )
        checkpoints = record.get("checkpoints")
        checkpoint = checkpoints[0] if isinstance(checkpoints, (list, tuple)) and checkpoints else ""
        rows.append(
            LedgerRow(
                run_id=record["run_id"],
                experiment_family="r1-pilot",
                dataset=record["dataset"],
                arm=arm,
                arm_kind=kind,
                epochs=None,
                seed=int(record["seed"]),
                train_rows=int(record["train_rows"]),
                roc_auc=float(record["roc_auc"]),
                brier=float(record["brier"]),
                pr_auc=float(record["pr_auc"]),
                status="superseded" if withdrawn else "current",
                superseded_reason=(
                    f"{withdrawn['decision']} (amended by {withdrawn['amendment']}): "
                    f"{withdrawn['reason']}"
                    if withdrawn
                    else ""
                ),
                note="2,000-row pilot aggregate: epochs not recorded, no provenance block",
                source=_relative(aggregate),
                checkpoint=checkpoint,
                model_version="",
            )
        )
    return rows


def launch_rows(runs: Path = GPU_PILOT_RUNS) -> list[LedgerRow]:
    """Records committed under `outputs/gpu-pilot/runs/<run>/<dataset>/<arm>/` — no Capture.

    These carry real metrics and a real checkpoint, but no `capture.json`: they cannot be cited as a
    Capture. They are Rows with status `no-capture`, and their pointer is the record file.
    """
    rows: list[LedgerRow] = []
    if not runs.is_dir():
        return rows
    for run_dir in sorted(path for path in runs.iterdir() if path.is_dir()):
        for record_path in sorted(run_dir.glob("*/*/meta.json")):
            record = json.loads(record_path.read_text())
            arm = record.get("arm")
            if arm is None:
                continue
            epochs = epochs_from_record(record)
            assert_epoch_agrees(arm, epochs)
            checkpoints = record.get("checkpoints") or []
            weights = record.get("weights") or {}
            rows.append(
                LedgerRow(
                    run_id=run_dir.name,
                    experiment_family="gpu-pilot",
                    dataset=record["dataset"],
                    arm=arm,
                    arm_kind=arm_kind(arm),
                    epochs=epochs,
                    seed=int(record["seed"]),
                    train_rows=record.get("train_rows"),
                    roc_auc=float(record["roc_auc"]),
                    brier=float(record["brier"]),
                    pr_auc=float(record["pr_auc"]),
                    status="no-capture",
                    note=(
                        "launch record with no capture.json — cite by description "
                        f"({_relative(record_path)}), not a Capture"
                    ),
                    source=_relative(record_path),
                    checkpoint=checkpoints[0] if checkpoints else "",
                    weights_sha256=weights.get("sha256", ""),
                    model_version=((record.get("provenance") or {}).get("model") or {}).get(
                        "version", ""
                    ),
                )
            )
    return rows


def breadth_rows(cell: dict = BREADTH_CELL) -> list[LedgerRow]:
    """The one curated `no-capture` cell, with blank metrics and no invented seed rows."""
    return [
        LedgerRow(
            run_id="",
            experiment_family=cell["experiment_family"],
            dataset=cell["dataset"],
            arm=arm,
            arm_kind=arm_kind(arm),
            epochs=epochs,
            seed=None,
            train_rows=cell["train_rows"],
            roc_auc=None,
            brier=None,
            pr_auc=None,
            status="no-capture",
            note=cell["note"],
            source=cell["source"],
        )
        for arm, epochs in cell["arms"]
    ]


def load_rows(
    results: Path = RESULTS,
    readme: Path = CAMPAIGN_README,
    aggregate: Path = PILOT_AGGREGATE,
    launches: Path = GPU_PILOT_RUNS,
) -> list[LedgerRow]:
    """Every row, asserted, and in a total order so the same tree yields the same bytes."""
    rows = (
        capture_rows(results, readme)
        + pilot_rows(aggregate)
        + launch_rows(launches)
        + breadth_rows()
    )
    assert_seed_disjoint(rows)
    return sorted(rows, key=_sort_key)


# Family order for the table: the campaign's captured Runs first, then the earlier pilot and the
# launch records, then the curated cell whose evidence was never committed.
FAMILY_ORDER = {
    "pilot2-phase2": 0,
    "r1-pilot": 1,
    "gpu-pilot": 2,
    "pilot2-breadth-spanish": 3,
}


def _sort_key(row: LedgerRow):
    return (
        FAMILY_ORDER.get(row.experiment_family, 99),
        row.dataset,
        ARM_ORDER.get(row.arm, 99),
        row.train_rows if row.train_rows is not None else -1,
        row.seed if row.seed is not None else -1,
        row.run_id,
        row.source,
    )


def _number(value: float | None, places: int) -> str:
    return "" if value is None else f"{value:.{places}f}"


def _integer(value: int | None) -> str:
    return "" if value is None else str(value)


def csv_row(row: LedgerRow) -> dict[str, str]:
    return {
        "run_id": row.run_id,
        "experiment_family": row.experiment_family,
        "dataset": row.dataset,
        "arm": row.arm,
        "arm_kind": row.arm_kind,
        "epochs": _integer(row.epochs),
        "seed": _integer(row.seed),
        "train_rows": _integer(row.train_rows),
        "roc_auc": _number(row.roc_auc, 6),
        "brier": _number(row.brier, 6),
        "pr_auc": _number(row.pr_auc, 6),
        "status": row.status,
        "superseded_by": row.superseded_by,
        "superseded_reason": row.superseded_reason,
        "note": row.note,
        "source": row.source,
        "model_version": row.model_version,
        "checkpoint": row.checkpoint,
        "weights_sha256": row.weights_sha256,
    }


def write_csv(rows: list[LedgerRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(csv_row(row))


def read_csv(path: Path) -> list[dict[str, str]]:
    """The CSV as the document's only source, so the two forms cannot disagree."""
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def summarise(csv_rows: list[dict[str, str]]) -> list[dict]:
    """`n`, mean and min–max per dataset × arm × training rows, over current rows only.

    Descriptive only: no interval, because an interval would be an inference and the ledger owns no
    verdict. Superseded and `no-capture` rows are excluded — a withdrawn row is not evidence a mean
    should carry, and a launch with no Capture would enter a mean over captured runs.
    """
    groups: dict[tuple, list[dict[str, str]]] = {}
    for row in csv_rows:
        if row["status"] != "current":
            continue
        group = (row["dataset"], row["arm"], row["train_rows"])
        groups.setdefault(group, []).append(row)

    summary = []
    for (dataset, arm, train_rows), members in sorted(
        groups.items(),
        key=lambda item: (item[0][0], ARM_ORDER.get(item[0][1], 99), int(item[0][2])),
    ):
        entry = {
            "dataset": dataset,
            "arm": arm,
            "train_rows": train_rows,
            "n": len(members),
        }
        for metric in METRICS:
            values = [float(member[metric]) for member in members if member[metric]]
            entry[metric] = {
                "mean": sum(values) / len(values) if values else None,
                "min": min(values) if values else None,
                "max": max(values) if values else None,
            }
        summary.append(entry)
    return summary


def _table(headers: list[str], body: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    lines.extend("| " + " | ".join(cells) + " |" for cells in body)
    return lines


def _pin_line(csv_rows: list[dict[str, str]]) -> str:
    """The model pin, as the records state it — `auto`, a checkpoint and a weights sha."""
    versions = sorted({row["model_version"] for row in csv_rows if row["model_version"]})
    checkpoints = sorted({row["checkpoint"] for row in csv_rows if row["checkpoint"]})
    shas = sorted({row["weights_sha256"] for row in csv_rows if row["weights_sha256"]})
    if len(checkpoints) != 1 or len(shas) != 1:
        raise EvidenceError(
            "the evidence names more than one checkpoint or weights sha: "
            f"{checkpoints} / {shas}"
        )
    sha = f"{shas[0][:8]}...{shas[0][-6:]}"
    recorded = "`, `".join(versions) or "not recorded"
    return [
        f"**The model version is printed as recorded.** `model_version` reads `{recorded}` wherever a "
        "record names one —",
        "a recorded value that names no version, so this ledger never prints `v3`. The checkpoint is",
        f"`{checkpoints[0]}` and the weights sha256 `{sha}` on every row that records one.",
    ]


def render_document(csv_rows: list[dict[str, str]]) -> str:
    """The campaign document, rendered from the CSV and nothing else."""
    summary = summarise(csv_rows)
    families = sorted(
        {row["experiment_family"] for row in csv_rows},
        key=lambda family: FAMILY_ORDER.get(family, 99),
    )
    statuses = sorted({row["status"] for row in csv_rows})
    superseded = [row for row in csv_rows if row["status"] == "superseded"]
    no_capture = [row for row in csv_rows if row["status"] == "no-capture"]
    by_family = {
        family: [row for row in csv_rows if row["experiment_family"] == family]
        for family in families
    }
    family_counts = "; ".join(f"`{family}` {len(by_family[family])}" for family in families)
    status_list = ", ".join(f"`{status}`" for status in statuses)

    lines = [
        "# Fine-tuning runs ledger — every committed in-domain fine-tuning run",
        "",
        "> **Status:** current — generated ledger, 2026-11-20. **Generated, not written:** rebuild it with",
        "> `python scripts/analyses/finetuning_runs_ledger.py`; a hand edit is overwritten and a number",
        "> typed here is a number with no evidence behind it.",
        "",
        "**Question.** What did the fine-tuning programme run, and what did it score? One row per run ×",
        "arm × seed, and a descriptive summary per dataset × arm underneath. This is a reference, not a",
        "new verdict: it re-runs nothing, adds no interval, and changes no claim.",
        "",
        "**Provenance.** Built for the map's ledger ticket (#663 → #665). The fields and the traps are",
        "the research note's (#664): the epoch count that lies, the seed-disjoint evidence that makes",
        "mechanical supersession impossible, the row budget that has to be in the key, and the model",
        "version recorded as `auto`.",
        "",
        "**Machine form.** [`finetuning_runs_ledger.csv`](../../analyses/data/finetuning_runs_ledger.csv)",
        "carries the same rows, one line each, with the full source pointer. The tables below are",
        "rendered from it, so they cannot disagree with it.",
        "",
        f"**Rows.** {len(csv_rows)} across {len(families)} experiment families: "
        f"{family_counts}. "
        f"Statuses present: {status_list}.",
        "",
        "## Sources, and what each one is",
        "",
    ]

    source_rows = []
    for family in families:
        members = by_family[family]
        counts = ", ".join(
            f"{status} {sum(row['status'] == status for row in members)}"
            for status in sorted({row["status"] for row in members})
        )
        source_rows.append(
            [
                f"`{family}`",
                str(len(members)),
                counts,
                SOURCE_ROOTS.get(family, "—"),
            ]
        )
    lines += _table(["family", "rows", "statuses", "read from"], source_rows)
    run_count = len({row["run_id"] for row in by_family.get("pilot2-phase2", [])})
    lines += [
        "",
        "The families are read from four places, and they are read **separately**:",
        "",
        f"- `pilot2-phase2` — the {run_count} Run directories this campaign's own `Runs` block names, each",
        "  with a `capture.json`. Selected by campaign membership, never by \"has an `ft` arm\": six",
        "  fair-test Run directories carry the same `A_raw` / `B_ft30` labels and belong to another",
        "  campaign.",
        "- `r1-pilot` — `outputs/finetune/pilot/pilot_metrics.parquet`, an aggregate of the 2,000-row",
        "  pilot. It is not a Run and has no Capture, so its ids are synthetic and are never joined to",
        "  a Run id.",
        "- `gpu-pilot` — committed launch records under `outputs/gpu-pilot/runs/`, which have no",
        "  `capture.json` and so cannot be cited as a Capture.",
        "- `pilot2-breadth-spanish` — one curated cell whose per-seed records were never committed. It is",
        "  listed so the absence is visible, with blank metrics rather than invented ones.",
        "",
        "## The ledger",
        "",
        "One row per run × arm × seed. `epochs` is blank where no epoch applies (the raw control, and",
        "the comparator Methods) and where the source records no arm-level epoch count (the 2,000-row",
        "pilot). `train_rows` is part of the key: `uslapseagent` seed 42 exists at 2,000 and at 10,000",
        "rows, and they are two measurements, not a duplicate.",
        "",
    ]

    body = []
    for row in csv_rows:
        body.append(
            [
                f"`{row['run_id']}`" if row["run_id"] else "—",
                row["experiment_family"],
                row["dataset"],
                f"`{row['arm']}`",
                row["arm_kind"],
                row["epochs"] or "—",
                row["seed"] or "—",
                row["train_rows"] or "—",
                row["roc_auc"] or "—",
                row["brier"] or "—",
                row["pr_auc"] or "—",
                row["status"],
            ]
        )
    lines += _table(
        [
            "run id",
            "family",
            "dataset",
            "arm",
            "arm kind",
            "epochs",
            "seed",
            "train rows",
            "ROC AUC",
            "Brier",
            "PR-AUC",
            "status",
        ],
        body,
    )
    lines += [
        "",
        "## The rows that are not plainly current",
        "",
        f"{len(superseded)} withdrawn and {len(no_capture)} without a Capture. Nothing was dropped: a",
        "row that is not evidence a claim may rest on is still a record of what ran.",
        "",
    ]

    flagged = superseded + no_capture
    lines += _table(
        ["run id", "dataset", "arm", "seed", "train rows", "status", "why"],
        [
            [
                f"`{row['run_id']}`" if row["run_id"] else "—",
                row["dataset"],
                f"`{row['arm']}`",
                row["seed"] or "—",
                row["train_rows"] or "—",
                row["status"],
                (row["superseded_reason"] or row["note"]),
            ]
            for row in flagged
        ],
    )
    lines += [
        "",
        "The withdrawal is a **curated** list, not a diff of captures. The committed evidence is",
        "seed-disjoint by construction — three duplicate launches were discarded before commit and",
        "their run ids are not in the tree — so mechanical replacement detection returns zero rows and",
        "the generator asserts that instead of reporting an empty result as a finding. The four",
        "`coil2000` pilot rows are withdrawn by **D21**, whose stop stands, and **D22** amends it: it",
        "withdraws D21's seed-cost inference, not the stop, which rests on the P1 resolution gate.",
        "Every `coil2000` row here is withdrawn and the dataset is closed, so the summary below carries",
        "no `coil2000` line at all — an absent line is the honest form of a closed dataset.",
        "",
        "D11 (\"stop the fine-tuning line\") is **not** applied to these rows: it is historical, and D14,",
        "D15 and D16 reopened and published the line it stopped. A ledger that marked every `B_ft*` row",
        "withdrawn under D11 would contradict the campaign's own outcome.",
        "",
        "## Summary — dataset × arm × training rows",
        "",
        "`n`, mean and min–max across seeds (and instances, where a dataset has more than one Run).",
        "**Descriptive only: no interval and no verdict**, so the ledger cannot contradict an analysis",
        "that owns one. Current rows only — a withdrawn row would put a stopped cell inside a mean, and",
        "a `no-capture` row would put a launch with no Capture inside a mean over captured Runs. The",
        "2,000-row and 10,000-row cells are separate lines for the same reason `train_rows` is part of",
        "the key.",
        "",
    ]

    summary_body = []
    for entry in summary:
        summary_body.append(
            [
                entry["dataset"],
                f"`{entry['arm']}`",
                f"{int(entry['train_rows']):,}",
                str(entry["n"]),
                _range(entry["roc_auc"], 4, entry["n"]),
                _range(entry["brier"], 4, entry["n"]),
                _range(entry["pr_auc"], 4, entry["n"]),
            ]
        )
    lines += _table(
        [
            "dataset",
            "arm",
            "train rows",
            "n",
            "ROC AUC mean (min–max)",
            "Brier mean (min–max)",
            "PR-AUC mean (min–max)",
        ],
        summary_body,
    )
    lines += [
        "",
        "## How to read a row",
        "",
        "**`arm_kind` is derived, never recorded.** `A_raw` is the raw control (`raw`); `B_ft3`,",
        "`B_ft10`, `B_ft30` and the pilot's `B_in_domain` are fine-tuned (`fine-tuned`); `E_glm` and",
        "`F_catboost` are comparator Methods (`comparator`), not a fourth and fifth Arm of one kind.",
        "",
        "**Epochs come from the record that trained, not from the config that launched.** The source is",
        "each record's `effective_config.kwargs.epochs`. `config.epochs` — and every Run manifest —",
        "reads `3` on every arm, including the 30-epoch one, so a generator reading either would call a",
        "30-epoch arm a 3-epoch arm. The generator asserts the recorded count equals the number in the",
        "`B_ftN` label and fails on a disagreement rather than smoothing it. The 2,000-row pilot records",
        "no arm-level epoch count at all (`max_finetune_steps` is a different parameter, carried by the",
        "comparator rows too), so its `epochs` column is blank, not `3`.",
        "",
        *_pin_line(csv_rows),
        "",
        "**Three metrics, and no more.** ROC AUC, Brier and PR-AUC are recorded on every capture record;",
        "`log_loss` and `ece` are recorded too and are deliberately outside this ledger (the map's",
        "out-of-scope list, #663), not missing from it. A blank is \"the source did not record it\": no",
        "cell here is backfilled from prose.",
        "",
        "**`source` is the pointer to the bytes.** For a capture row it is the per-seed `meta.json`,",
        "because `capture.json` holds hashes and the record holds the numbers; the Run id is in the",
        "`run_id` column, taken from the directory. A per-seed record's own `run_id`",
        "(`<dataset>_<arm>_seed<N>`) is **not** the Run id and is not used as one.",
        "",
        "**A `no-capture` row cannot be cited as a Capture.** The Spanish breadth cell's per-seed records",
        "were never committed, so its rows carry blank metrics and no seed at all — one row per arm,",
        "because a per-seed row would be an invention — and a pointer to",
        "[`finetuning_breadth_spanish_result.md`](finetuning_breadth_spanish_result.md) — cite the result,",
        "not a Capture. The `gpu-pilot` rows do carry metrics, from committed launch records that are",
        "not Captures; they are cited by description, the way `REPORT_REGISTRY.md` already handles them.",
        "",
        "## Regenerating",
        "",
        "```",
        "python scripts/analyses/finetuning_runs_ledger.py",
        "```",
        "",
        "Two runs on the same tree write byte-identical files: rows are sorted on a total key and every",
        "float is formatted to fixed precision (six decimal places per row, four in the summary, which is",
        "computed from the CSV and therefore inherits that rounding). The generator writes both files or",
        "neither — a disagreement in the evidence exits before either is written.",
        "",
    ]
    return "\n".join(lines) + "\n"


def _range(values: dict, places: int, n: int) -> str:
    if values["mean"] is None:
        return "—"
    if n == 1:
        return f"{values['mean']:.{places}f}"
    return f"{values['mean']:.{places}f} ({values['min']:.{places}f}–{values['max']:.{places}f})"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-csv", type=Path, default=CSV_PATH, metavar="PATH")
    parser.add_argument("--out-doc", type=Path, default=DOC_PATH, metavar="PATH")
    args = parser.parse_args(argv)

    rows = load_rows()

    # Both files are written from one buffer each and moved into place last, so a disagreement in
    # the evidence cannot leave a new CSV beside a stale document.
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    csv_tmp = args.out_csv.with_name(args.out_csv.name + ".tmp")
    doc_tmp = args.out_doc.with_name(args.out_doc.name + ".tmp")
    write_csv(rows, csv_tmp)
    document = render_document(read_csv(csv_tmp))
    args.out_doc.parent.mkdir(parents=True, exist_ok=True)
    doc_tmp.write_text(document, encoding="utf-8")
    os.replace(csv_tmp, args.out_csv)
    os.replace(doc_tmp, args.out_doc)

    print(
        f"{len(rows)} rows: "
        f"{sum(row.status == 'current' for row in rows)} current, "
        f"{sum(row.status == 'superseded' for row in rows)} superseded, "
        f"{sum(row.status == 'no-capture' for row in rows)} no-capture"
    )
    print(f"wrote {_relative(args.out_csv)}")
    print(f"wrote {_relative(args.out_doc)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
