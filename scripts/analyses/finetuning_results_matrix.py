#!/usr/bin/env python3
"""Generate the paper-facing in-domain fine-tuning results matrix (#739).

    python scripts/analyses/finetuning_results_matrix.py --write   # refresh the block and CSV
    python scripts/analyses/finetuning_results_matrix.py --check   # fail on drift
    python scripts/analyses/finetuning_results_matrix.py --print   # print the generated block

The matrix restates the three result owners; it is not a fourth analysis. Fair-test cells are
recomputed through `freq_sev_fair_test.build_summary()`, which is the same function the verdict
document calls. The lapse cells quote `FINETUNING_PHASE2_OUTCOME.md` and the ladder cells quote
`EPOCH_LADDER_RESULT.md`; a test checks every quoted number against its owner and every design axis
against the runs ledger.

The ledger is deliberately not the only source: it has one row per seed/fold and no verdict, and the
epoch ladder is outside it by scope. The matrix closes that gap without re-running anything.
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
from dataclasses import dataclass
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import freq_sev_fair_test as fair_test  # noqa: E402

DOC_PATH = _REPO / "docs/shared/FINETUNING_RESULTS_MATRIX.md"
CSV_PATH = _REPO / "docs/analyses/data/finetuning_results_matrix.csv"
LEDGER_PATH = _REPO / "docs/analyses/data/finetuning_runs_ledger.csv"
PHASE2_PATH = _REPO / "docs/experiments/pilot2-phase2/FINETUNING_PHASE2_OUTCOME.md"
LADDER_PATH = _REPO / "docs/experiments/pilot2-phase2/EPOCH_LADDER_RESULT.md"
FAIR_PATH = _REPO / "docs/experiments/fair-test-freq-sev/freq_sev_fair_test_result.md"

BEGIN = "<!-- BEGIN GENERATED: finetuning-results-matrix -->"
END = "<!-- END GENERATED: finetuning-results-matrix -->"

FAIR_IDS = {
    "frequency_french": "20261112T164543Z",
    "frequency_spanish": "20261112T184155Z",
    "severity_french": "20261112T210029Z",
    "severity_spanish": "20261112T220641Z",
}
ROW_SCALE_SEVERITY = "20261113T003320Z"
ROW_SCALE_FREQUENCY = "20261113T095502Z"
MODEL_VERSION = "v3_default"


@dataclass(frozen=True)
class Row:
    """One line of the matrix. `block` is `targets`, `ladder` or `row-scale`."""

    block: str
    task: str
    target: str
    dataset: str
    unit: str
    eligible_rows: str
    train_rows: str
    holdout: str
    splits: str
    seeds: str
    seed_count: int
    arms: str
    epochs: str
    metric: str
    estimate: str
    ci_low: str
    ci_high: str
    decision: str
    note: str
    source: str
    model_version: str = MODEL_VERSION

    @property
    def estimate_ci(self) -> str:
        return f"{self.estimate} [{self.ci_low}, {self.ci_high}]"

    @property
    def decision_text(self) -> str:
        return f"{self.decision} — {self.note}" if self.note else self.decision


def _pct(value: float) -> str:
    return f"{value:+.2%}"


def _ci(value: float) -> str:
    """A CI bound without the redundant plus, so the interval reads as an interval."""
    return _pct(value).lstrip("+")


def _thousands(value: int) -> str:
    return f"{value:,}"


def _budget_text(values: list[int]) -> str:
    """A row budget, as a range when the folds differ."""
    low, high = min(values), max(values)
    return _thousands(low) if low == high else f"{_thousands(low)}–{_thousands(high)}"


def _lapse_rows() -> list[Row]:
    """The three lapse targets. The delta is ROC AUC; the Phase 2 table is the owner."""
    return [
        Row(
            block="targets",
            task="Lapse",
            target="`surrender` (binary)",
            dataset="`uslapseagent`",
            unit="policy",
            eligible_rows="29,317",
            train_rows="10,000 / 1,000",
            holdout="1,000 test rows",
            splits="one stratified holdout per seed",
            seeds="28 (55–82)",
            seed_count=28,
            arms="raw, 30 epochs",
            epochs="0, 30",
            metric="ROC AUC (Brier veto)",
            estimate="+0.0035",
            ci_low="0.00272",
            ci_high="0.00428",
            decision="gain",
            note="the whole interval above δ = 0.002",
            source="Phase 2 §3; `results/20261104T123839Z/`",
        ),
        Row(
            block="targets",
            task="Lapse",
            target="`lapse` (binary)",
            dataset="`eudirectlapse`",
            unit="policy",
            eligible_rows="23,060",
            train_rows="10,000 / 1,000",
            holdout="1,000 test rows",
            splits="one stratified holdout per seed",
            seeds="238 (93–330)",
            seed_count=238,
            arms="raw, 30 epochs",
            epochs="0, 30",
            metric="ROC AUC (Brier veto)",
            estimate="+0.0007",
            ci_low="-0.0003",
            ci_high="0.0018",
            decision="equivalence",
            note="bounded inside ±δ",
            source="Phase 2 §3; twenty `results/` runs",
        ),
        Row(
            block="targets",
            task="Lapse",
            target="`LapseB` (binary)",
            dataset="`spanish_motor_lapse`",
            unit="policy",
            eligible_rows="53,502",
            train_rows="10,000 / 10,000",
            holdout="10,000 test rows",
            splits="one stratified holdout per seed",
            seeds="16 (341–356)",
            seed_count=16,
            arms="raw, 30 epochs",
            epochs="0, 30",
            metric="ROC AUC (Brier veto)",
            estimate="+0.0003",
            ci_low="-0.0002",
            ci_high="0.0008",
            decision="equivalence",
            note="bounded inside ±δ; quoted, no committed capture",
            source="Phase 2 §3; `outputs/gpu-pilot/` launch record",
        ),
    ]


def _fair_rows(summary: dict) -> list[Row]:
    """The four registered fair-test targets, recomputed from their captures."""
    rows: list[Row] = []

    frequency_french = summary["targets"]["frequency_french"]
    row_scale_frequency = summary["row_scale_frequency"]
    rows.append(
        Row(
            block="targets",
            task="Frequency",
            target="`ClaimNb` (count)",
            dataset="`freMTPL2freq`",
            unit="policy-year",
            eligible_rows="678,013",
            train_rows="10,000 / fold holdout",
            holdout="the fold's held-out policies",
            splits="5 policy-grouped folds",
            seeds="3 per fold (0–2)",
            seed_count=3,
            arms="raw, 30 epochs",
            epochs="0, 30",
            metric="Poisson deviance",
            estimate=_pct(frequency_french["mean"]),
            ci_low=_ci(frequency_french["ci"][0]),
            ci_high=_ci(frequency_french["ci"][1]),
            decision=frequency_french["decision"],
            note=(
                f"{_pct(row_scale_frequency['mean'])} at "
                f"{_budget_text(row_scale_frequency['train_rows'])} rows (4×)"
            ),
            source=(
                "Fair test; `20261112T164543Z`; row scaling `20261113T095502Z`"
            ),
        )
    )

    frequency_spanish = summary["targets"]["frequency_spanish"]
    rows.append(
        Row(
            block="targets",
            task="Frequency",
            target="`N_claims_year` (count)",
            dataset="`spanish_motor_freq`",
            unit="policy-year",
            eligible_rows="53,502",
            train_rows="10,000 / fold holdout",
            holdout="the fold's held-out policies",
            splits="5 policy-grouped folds",
            seeds="3 per fold (0–2)",
            seed_count=3,
            arms="raw, 30 epochs",
            epochs="0, 30",
            metric="Poisson deviance",
            estimate=_pct(frequency_spanish["mean"]),
            ci_low=_ci(frequency_spanish["ci"][0]),
            ci_high=_ci(frequency_spanish["ci"][1]),
            decision=frequency_spanish["decision"],
            note="MDE 4.69% is above the 4% floor, so the target is underpowered",
            source="Fair test; `20261112T184155Z`",
        )
    )

    severity_french = summary["targets"]["severity_french"]
    row_scale_severity = summary["row_scale"]
    rows.append(
        Row(
            block="targets",
            task="Severity",
            target="`ClaimAmount` (log, per claim)",
            dataset="`freMTPL2sev`",
            unit="claim",
            eligible_rows="26,444 claims",
            train_rows="10,000 / fold holdout",
            holdout="the fold's held-out claims",
            splits="5 policy-grouped folds",
            seeds="3 per fold (0–2)",
            seed_count=3,
            arms="raw, 30 epochs",
            epochs="0, 30",
            metric="per-claim RMSE (log)",
            estimate=_pct(severity_french["mean"]),
            ci_low=_ci(severity_french["ci"][0]),
            ci_high=_ci(severity_french["ci"][1]),
            decision=severity_french["decision"],
            note=(
                f"{_pct(row_scale_severity['mean'])} at "
                f"{_budget_text(row_scale_severity['train_rows'])} rows (2.1×)"
            ),
            source=(
                "Fair test; `20261112T210029Z`; row scaling `20261113T003320Z`"
            ),
        )
    )

    severity_spanish = summary["targets"]["severity_spanish"]
    rows.append(
        Row(
            block="targets",
            task="Severity",
            target="`Cost/N` (log, per claiming policy)",
            dataset="`spanish_motor_severity`",
            unit="claiming policy, claim-weighted",
            eligible_rows="5,950 claiming policies (11,167 claim-eq.)",
            train_rows="4,760 / fold holdout",
            holdout="the fold's held-out policies",
            splits="5 policy-grouped folds",
            seeds="3 per fold (0–2)",
            seed_count=3,
            arms="raw, 30 epochs",
            epochs="0, 30",
            metric="claim-weighted RMSE (log)",
            estimate=_pct(severity_spanish["mean"]),
            ci_low=_ci(severity_spanish["ci"][0]),
            ci_high=_ci(severity_spanish["ci"][1]),
            decision=severity_spanish["decision"],
            note="below the 2% floor and covers it",
            source="Fair test; `20261112T220641Z`",
        )
    )
    return rows


def _row_scale_rows(summary: dict) -> list[Row]:
    """The #572 robustness arms, reported beside the registered rows, never inside them."""
    severity = summary["row_scale"]
    frequency = summary["row_scale_frequency"]
    return [
        Row(
            block="row-scale",
            task="Severity",
            target="`ClaimAmount` (log, per claim)",
            dataset="`freMTPL2sev`",
            unit="claim",
            eligible_rows="26,444 claims",
            train_rows=f"{_budget_text(severity['train_rows'])} (the whole claim pool)",
            holdout="the fold's held-out claims",
            splits="5 policy-grouped folds",
            seeds="3 per fold (0–2)",
            seed_count=3,
            arms="raw, 30 epochs",
            epochs="0, 30",
            metric="per-claim RMSE (log)",
            estimate=_pct(severity["mean"]),
            ci_low=_ci(severity["ci"][0]),
            ci_high=_ci(severity["ci"][1]),
            decision=severity["decision"],
            note="#572; 2.1× the registered cap, the most this dataset allows",
            source="#572; `20261113T003320Z`",
        ),
        Row(
            block="row-scale",
            task="Frequency",
            target="`ClaimNb` (count)",
            dataset="`freMTPL2freq`",
            unit="policy-year",
            eligible_rows="678,013",
            train_rows=f"{_budget_text(frequency['train_rows'])} (4× the registered cap)",
            holdout="the fold's held-out policies",
            splits="5 policy-grouped folds",
            seeds="3 per fold (0–2)",
            seed_count=3,
            arms="raw, 30 epochs",
            epochs="0, 30",
            metric="Poisson deviance",
            estimate=_pct(frequency["mean"]),
            ci_low=_ci(frequency["ci"][0]),
            ci_high=_ci(frequency["ci"][1]),
            decision=frequency["decision"],
            note="#572",
            source="#572; `20261113T095502Z`",
        ),
    ]


def _ladder_rows() -> list[Row]:
    """The 20-seed epoch ladder. Numbers are owned by EPOCH_LADDER_RESULT.md."""
    return [
        Row(
            block="ladder",
            task="Severity",
            target="`ClaimAmount` (log, per claim)",
            dataset="`severity_french`",
            unit="claim",
            eligible_rows="26,444 claims",
            train_rows="10,000 / fold holdout",
            holdout="the fold's held-out claims",
            splits="5 policy-grouped folds",
            seeds="20 (1001–1020)",
            seed_count=20,
            arms="raw, 3, 10, 30 epochs",
            epochs="0, 3, 10, 30",
            metric="per-claim RMSE (log)",
            estimate="+1.37%",
            ci_low="0.61%",
            ci_high="2.12%",
            decision="REFUTED",
            note="worse than raw at every rung; 30 − raw",
            source="Ladder; `results/20261121T153848Z/`",
        ),
        Row(
            block="ladder",
            task="Severity",
            target="`Cost/N` (log, per claiming policy)",
            dataset="`severity_spanish`",
            unit="claiming policy, claim-weighted",
            eligible_rows="5,950 claiming policies (11,167 claim-eq.)",
            train_rows="4,760 / fold holdout",
            holdout="the fold's held-out policies",
            splits="5 policy-grouped folds",
            seeds="20 (1001–1020)",
            seed_count=20,
            arms="raw, 3, 10, 30 epochs",
            epochs="0, 3, 10, 30",
            metric="claim-weighted RMSE (log)",
            estimate="-1.29%",
            ci_low="-2.08%",
            ci_high="-0.50%",
            decision="CONFIRMED",
            note="better at 30; shape non-monotone (10 worse than 3)",
            source="Ladder; `results/20261121T232424Z/`",
        ),
        Row(
            block="ladder",
            task="Lapse",
            target="`lapse` (binary)",
            dataset="`eudirectlapse`",
            unit="policy",
            eligible_rows="23,060",
            train_rows="10,000 / 1,000",
            holdout="1,000 test rows",
            splits="one stratified holdout per seed",
            seeds="20 (1001–1020)",
            seed_count=20,
            arms="raw, 3, 10, 30 epochs",
            epochs="0, 3, 10, 30",
            metric="ROC AUC",
            estimate="+0.00205",
            ci_low="-0.0047",
            ci_high="0.0089",
            decision="UNRESOLVED",
            note="the interval covers zero; observed half-width ~0.0068",
            source="Ladder; four `outputs/gpu-pilot/runs/20261121T*` launches",
        ),
    ]


def rows() -> list[Row]:
    summary = fair_test.build_summary(
        FAIR_IDS,
        row_scale_french=ROW_SCALE_SEVERITY,
        row_scale_frequency=ROW_SCALE_FREQUENCY,
    )
    return _lapse_rows() + _fair_rows(summary) + _row_scale_rows(summary) + _ladder_rows()


def _table(headers: list[str], body: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(cells) + " |" for cells in body)
    return "\n".join(lines)


def _target_table(items: list[Row]) -> str:
    return _table(
        [
            "Task",
            "Target (unit)",
            "Dataset",
            "Eligible",
            "Train / holdout",
            "Splits",
            "Seeds",
            "Arms (epochs)",
            "Metric",
            "Estimate [95% CI]",
            "Decision",
        ],
        [
            [
                row.task,
                row.target,
                row.dataset,
                row.eligible_rows,
                row.train_rows,
                row.splits,
                row.seeds,
                row.arms,
                row.metric,
                row.estimate_ci,
                row.decision_text,
            ]
            for row in items
        ],
    )


def block() -> str:
    """The generated block that sits inside the document."""
    everything = rows()
    targets = [row for row in everything if row.block == "targets"]
    row_scale = [row for row in everything if row.block == "row-scale"]
    ladder = [row for row in everything if row.block == "ladder"]
    return "\n".join(
        [
            BEGIN,
            "",
            "### Table 1 — registered in-domain fine-tuning targets",
            "",
            _target_table(targets),
            "",
            "### Table 2 — epoch ladder (exploratory, no decision role)",
            "",
            _target_table(ladder),
            "",
            "### Table 3 — row-scaling robustness arms (#572)",
            "",
            _target_table(row_scale),
            "",
            END,
        ]
    )


CSV_COLUMNS = [
    "block",
    "task",
    "target",
    "dataset",
    "unit",
    "eligible_rows",
    "train_rows",
    "holdout",
    "splits",
    "seeds",
    "seed_count",
    "arms",
    "epochs",
    "metric",
    "estimate",
    "ci_low",
    "ci_high",
    "decision",
    "note",
    "source",
    "model_version",
]


def render_csv() -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in rows():
        writer.writerow({column: getattr(row, column) for column in CSV_COLUMNS})
    return buffer.getvalue()


def _replace_block(text: str, generated: str) -> str:
    start = text.index(BEGIN)
    end = text.index(END) + len(END)
    return text[:start] + generated + text[end:]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="refresh the document block and CSV")
    parser.add_argument("--check", action="store_true", help="fail when either file has drifted")
    parser.add_argument("--print", dest="show", action="store_true", help="print the block")
    args = parser.parse_args(argv)

    generated = block()
    if args.show:
        print(generated)
        return 0

    if args.write:
        text = DOC_PATH.read_text(encoding="utf-8")
        DOC_PATH.write_text(_replace_block(text, generated), encoding="utf-8")
        CSV_PATH.write_text(render_csv(), encoding="utf-8")
        print(f"wrote {DOC_PATH.relative_to(_REPO)} and {CSV_PATH.relative_to(_REPO)}")
        return 0

    if args.check:
        text = DOC_PATH.read_text(encoding="utf-8")
        if BEGIN not in text or END not in text:
            print(f"{DOC_PATH}: no generated-table markers", file=sys.stderr)
            return 1
        embedded = text[text.index(BEGIN): text.index(END) + len(END)]
        if embedded.strip() != generated.strip():
            print(f"{DOC_PATH}: the matrix has drifted from its generator", file=sys.stderr)
            return 1
        if CSV_PATH.read_text(encoding="utf-8") != render_csv():
            print(f"{CSV_PATH}: the CSV has drifted from its generator", file=sys.stderr)
            return 1
        print("matrix and CSV match the generator")
        return 0

    print(generated)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
