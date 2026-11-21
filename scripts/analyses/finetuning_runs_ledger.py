#!/usr/bin/env python3
"""The cross-task runs ledger, generated from the committed evidence (#668).

    python scripts/analyses/finetuning_runs_ledger.py
    python scripts/analyses/finetuning_runs_ledger.py --out-csv /tmp/ledger.csv --out-doc /tmp/ledger.md

One row per run × arm × seed (classification) or run × arm × seed × fold (regression), written
twice: as a CSV under `docs/analyses/data/` and as the tables of
`docs/experiments/pilot2-phase2/FINETUNING_RUNS_LEDGER.md`. The Markdown is rendered from the CSV it
has just written, so the two forms cannot disagree. One table is the exception — it audits the
rejected pilot form against the chosen one — and the document says so beside it.

**The sources, and why they are read through a registry.**

Each campaign is one entry in `CAMPAIGNS`: its problem type, dataset → task mapping, arm labels,
era, record path shape and loader. The identity key and the two metric blocks are declared once for
the whole ledger rather than per campaign. Selection is by campaign membership and dataset, never by
"has an `ft` arm": the fair test, the actuarial baselines and the pilot all carry `A_raw` / `B_ft30`,
and a label-based selector would merge three campaigns into one.

- `pilot2-phase2` — the 23 Runs the campaign's own `## Runs` block names, one `capture.json` each.
- `outputs/finetune/pilot/pilot_metrics.parquet` — the 2,000-row R1 pilot's 16 aggregate rows only.
  It is an aggregate, not a Run: no epochs are recorded (`max_finetune_steps` is a different
  parameter and the comparator rows carry it too), and no provenance. Twelve of its cells are also
  recorded under `outputs/gpu-pilot/<dataset>/<arm>/`, with no provenance block either; the
  document lists the four cells where the two forms disagree and states that the aggregate is the
  chosen form.
- `outputs/gpu-pilot/runs/` — launch records with no `capture.json`; Rows with status `no-capture`.
- One curated `no-capture` cell: the `spanish_motor_lapse` breadth replication, whose per-seed
  records were never committed. It is listed so the cell is not silently missing, with blank metrics
  *and blank epoch/row fields*, because inventing them would be worse than the absence.
- `fair-test-freq-sev` — the four fair-test regression Runs, `20261112T*`.
- `actuarial-baseline-full` / `-matched` — the two registered baseline budgets, `20261113T2230*` and
  `20261114T0030*`. They are separate entries because one Spanish severity cell is the same fit
  under both run ids, so a shared campaign id would repeat the identity key.

The classification sources are never joined on `run_id` to the regression ones: the aggregate's ids
are synthetic (`<dataset>_<arm>_seed<N>`) and Run ids are directory names.

**The traps, one line each.**

- Classification epochs are the record's `effective_config.kwargs.epochs`; regression epochs are the
  record's top-level `epochs`. `config.epochs` and every Run manifest read `3` for every
  classification arm; the 30-epoch arm reads 3 there and 30 in the record that trained it.
- The identity key includes `train_rows` and `fold`: `uslapseagent` seed 42 exists at 2,000 rows and
  at 10,000, and a five-fold regression cell is five measurements, not one.
- Regression records name `task`, `fold`, `n_folds`, `rmse`, `verdict_metric` and
  `verdict_metric_value`. Severity's metric is read, never assumed: French severity records `rmse`
  (weight exactly 1), Spanish severity records `weighted_rmse`.
- Baseline records carry `arm: null` and name the method in `method`; the arm is the directory name
  and the two are asserted equal. `M_intercept` is a third comparator Method, not a programme Arm.
- `model_version` is printed as recorded — `auto` on classification rows, absent on regression rows.
  Never `v3`: `auto` names no version.
- A blank metric means "not applicable", never zero. The only legitimate zero is `epochs = 0` on a
  regression raw control, which is a recorded epoch count.
- `eligible_rows` is **curated from the pre-registrations' own dataset tables**, never derived from
  a capture: a capture covers the arms that ran, not the prepared dataset. `share_of_eligible` is
  computed per row as `train_rows / eligible_rows`, because one dataset carries a 10,000-row arm and
  a 542,410-row full-pool arm, and a per-dataset share would be wrong for one of them. A dataset
  with no curated size fails the renderer rather than printing a blank.
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
# The legacy per-arm records of the same 2,000-row pilot, one level above `runs/`. They are not read
# into the ledger (the aggregate is the chosen form) but they are audited against it, so the choice is
# visible rather than implicit.
GPU_PILOT_RECORDS = _REPO / "outputs" / "gpu-pilot"

CSV_PATH = _REPO / "docs" / "analyses" / "data" / "finetuning_runs_ledger.csv"
DOC_PATH = _REPO / "docs" / "experiments" / "pilot2-phase2" / "FINETUNING_RUNS_LEDGER.md"

COLUMNS = (
    "run_id",
    "experiment_family",
    "problem_type",
    "task",
    "era",
    "dataset",
    "arm",
    "arm_kind",
    "epochs",
    "seed",
    "fold",
    "train_rows",
    "eligible_rows",
    "share_of_eligible",
    "roc_auc",
    "brier",
    "pr_auc",
    "rmse",
    "verdict_metric",
    "verdict_metric_value",
    "status",
    "superseded_by_or_decision",
    "superseded_reason",
    "note",
    "source",
    "model_version",
    "checkpoint",
    "weights_sha256",
)

# The two metric blocks. They are disjoint per row: a classification row's regression block is blank
# and a regression row's classification block is blank, because "not applicable" is not zero.
CLASSIFICATION_METRICS = ("roc_auc", "brier", "pr_auc")
REGRESSION_METRICS = ("rmse", "verdict_metric", "verdict_metric_value")
# The summary's numeric columns per block. `verdict_metric` is a name, handled separately.
SUMMARY_METRICS = {
    "classification": ("roc_auc", "brier", "pr_auc"),
    "regression": ("rmse", "verdict_metric_value"),
}
REGRESSION_VERDICT_METRICS = {"poisson_deviance", "rmse", "weighted_rmse"}

# The identity key, declared once and read by `LedgerRow.cell`. `fold` is always in it: a
# classification row writes a blank fold and a regression row a fold number, so one key serves both
# blocks and a five-fold regression cell cannot collapse into one row.
IDENTITY_KEY = ("experiment_family", "dataset", "arm", "seed", "fold", "train_rows")

# `arm_kind` is derived, never recorded. A baseline is a Method in this repo's glossary, so the three
# comparator labels are not Arms of one kind. `M_intercept` is the intercept-only anchor the
# actuarial-baseline result registers beside the GLM and CatBoost.
COMPARATORS = {"E_glm", "F_catboost", "M_intercept"}
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
    "M_intercept": 7,
}

# The campaign's classification Runs block, read from the campaign index: `## Runs`, then the first
# fenced list.
RUNS_BLOCK = re.compile(r"^## Runs\s*\n.*?```\n(.*?)```", re.S | re.M)
RUN_ID = re.compile(r"^20\d{6}T\d{6}Z$")


@dataclass(frozen=True)
class Campaign:
    """One source of rows, and the rules that make its rows comparable.

    The identity key is not per campaign: it is `IDENTITY_KEY`, with `fold` in it for every row.
    A classification row writes a blank `fold` and a regression row its fold number, so one key
    covers both blocks.
    """

    campaign_id: str
    problem_type: str
    tasks: dict[str, str]
    datasets: frozenset[str]
    arm_labels: tuple[str, ...]
    era: str
    record_path: str
    what: str
    loader: str
    run_ids: tuple[str, ...] = ()
    run_index: Path | None = None

    def run_list(self, readme: Path | None = None) -> list[str]:
        """The Run ids this campaign reads: its index, else the ids the registry lists.

        `readme` overrides the registry's index so a caller can point at a fixture tree; the
        pipeline itself passes none and reads the index the registry names.
        """
        index = readme if readme is not None else self.run_index
        if index is not None:
            return campaign_runs(index)
        if not self.run_ids:
            raise EvidenceError(f"{self.campaign_id}: the registry names no Runs and no index")
        return list(self.run_ids)


CLASSIFICATION_DATASETS = frozenset(
    {"coil2000", "eudirectlapse", "spanish_motor_lapse", "uslapseagent"}
)
REGRESSION_DATASETS = frozenset(
    {"freMTPL2freq", "spanish_motor_freq", "freMTPL2sev", "spanish_motor_severity"}
)
REGRESSION_TASKS = {
    "freMTPL2freq": "frequency",
    "spanish_motor_freq": "frequency",
    "freMTPL2sev": "severity",
    "spanish_motor_severity": "severity",
}

# The registry. One entry per source, selected by campaign membership and dataset — never by arm
# label. The order here is the order the document prints.
CAMPAIGNS: tuple[Campaign, ...] = (
    Campaign(
        campaign_id="pilot2-phase2",
        problem_type="classification",
        tasks={"uslapseagent": "lapse", "eudirectlapse": "lapse"},
        datasets=frozenset({"uslapseagent", "eudirectlapse"}),
        arm_labels=("A_raw", "B_ft3", "B_ft10", "B_ft30"),
        era="auto",
        record_path="`results/<run>/<dataset>/<arm>/seed<N>_foldNone/meta.json`",
        what=(
            "the Run directories this campaign's own `Runs` block names, each with a `capture.json`"
        ),
        loader="capture",
        run_index=CAMPAIGN_README,
    ),
    Campaign(
        campaign_id="r1-pilot",
        problem_type="classification",
        tasks={dataset: "lapse" for dataset in sorted(CLASSIFICATION_DATASETS)},
        datasets=CLASSIFICATION_DATASETS,
        arm_labels=("A_raw", "B_in_domain", "E_glm", "F_catboost"),
        era="auto",
        record_path="`outputs/finetune/pilot/pilot_metrics.parquet`",
        what="the 2,000-row R1 pilot aggregate, one seed (42), no Capture",
        loader="aggregate",
    ),
    Campaign(
        campaign_id="gpu-pilot",
        problem_type="classification",
        tasks={"uslapseagent": "lapse"},
        datasets=frozenset({"uslapseagent"}),
        arm_labels=("A_raw", "B_ft3", "B_ft10", "B_ft30"),
        era="auto",
        record_path="`outputs/gpu-pilot/runs/<run>/<dataset>/<arm>/meta.json`",
        what="committed launch records with no `capture.json`",
        loader="launch",
    ),
    Campaign(
        campaign_id="pilot2-breadth-spanish",
        problem_type="classification",
        tasks={"spanish_motor_lapse": "lapse"},
        datasets=frozenset({"spanish_motor_lapse"}),
        arm_labels=("A_raw", "B_ft30"),
        era="auto",
        record_path="`docs/experiments/pilot2-phase2/finetuning_breadth_spanish_result.md`",
        what="one curated cell whose per-seed records were never committed",
        loader="curated",
    ),
    Campaign(
        campaign_id="fair-test-freq-sev",
        problem_type="regression",
        tasks=REGRESSION_TASKS,
        datasets=REGRESSION_DATASETS,
        arm_labels=("A_raw", "B_ft30"),
        era="v3_default",
        record_path="`results/<run>/<dataset>/<arm>/seed<N>_fold<K>/meta.json`",
        what=(
            "the four registered fair-test targets, policy-grouped folds; the #572 row-scaling runs "
            "`20261113T003320Z` and `20261113T095502Z` belong to the same campaign and are reported "
            "by the fair-test result, not this ledger"
        ),
        loader="regression",
        run_ids=(
            "20261112T164543Z",
            "20261112T184155Z",
            "20261112T210029Z",
            "20261112T220641Z",
        ),
    ),
    Campaign(
        campaign_id="actuarial-baseline-full",
        problem_type="regression",
        tasks=REGRESSION_TASKS,
        datasets=REGRESSION_DATASETS,
        arm_labels=("E_glm", "F_catboost", "M_intercept"),
        era="v3_default",
        record_path="`results/<run>/<dataset>/<arm>/seed<N>_fold<K>/meta.json`",
        what="the registered primary baseline arm, trained on the whole fold pool",
        loader="regression",
        run_ids=(
            "20261113T223000Z",
            "20261113T223001Z",
            "20261113T223002Z",
            "20261113T223003Z",
        ),
    ),
    Campaign(
        campaign_id="actuarial-baseline-matched",
        problem_type="regression",
        tasks=REGRESSION_TASKS,
        datasets=REGRESSION_DATASETS,
        arm_labels=("E_glm", "F_catboost", "M_intercept"),
        era="v3_default",
        record_path="`results/<run>/<dataset>/<arm>/seed<N>_fold<K>/meta.json`",
        what=(
            "the registered 10,000-row baseline sensitivity arm; on `spanish_motor_severity` the two "
            "arms are the same fit, captured under both run ids"
        ),
        loader="regression",
        run_ids=(
            "20261114T003000Z",
            "20261114T003001Z",
            "20261114T003002Z",
            "20261114T003003Z",
        ),
    ),
)

CAMPAIGN_BY_ID = {campaign.campaign_id: campaign for campaign in CAMPAIGNS}
PROBLEM_ORDER = {"classification": 0, "regression": 1}
CAMPAIGN_ORDER = {campaign.campaign_id: index for index, campaign in enumerate(CAMPAIGNS)}

# What each dataset is, for the table the CSV alone cannot answer. The dataset, task and problem type
# beside it are read from the CSV; this prose is curated from the campaigns' own target tables and
# names the unit and target, so a regression row's RMSE is not read as an AUC.
DATASET_NOTES = {
    "coil2000": "CoIL 2000: caravan-policy purchase (5.97% positive, NL)",
    "uslapseagent": "US lapse agent: policy surrender (37.9% positive)",
    "eudirectlapse": "EU direct motor: policy lapse (12.81% positive) — the known TabPFN exception",
    "spanish_motor_lapse": "Spanish motor: policy lapse",
    "freMTPL2freq": "French motor third-party liability: claims per policy (`ClaimNb`, unit policy)",
    "spanish_motor_freq": "Spanish motor: claims per policy year (`N_claims_year`, unit policy)",
    "freMTPL2sev": (
        "French motor third-party liability: claim amount per claim (`ClaimAmount`, on the log "
        "scale; unweighted RMSE, weight exactly 1)"
    ),
    "spanish_motor_severity": (
        "Spanish motor: cost per claim, weighted by the claim count "
        "(`Cost_claims_year / N_claims_year`, log scale)"
    ),
}


@dataclass(frozen=True)
class DatasetSize:
    """A dataset's prepared size, the unit it is counted in, and where the figure was sourced.

    `detail` carries the second unit where a dataset has one (French severity's policies, Spanish
    severity's claim-equivalents), so the document can show both without a second map.
    """

    eligible_rows: int
    unit: str
    source: str
    detail: str = ""


# The prepared size of each dataset, curated from the pre-registrations' own dataset tables — **not**
# derived from a capture (a capture covers the arms that ran, not the dataset that existed) and not
# from a count of the committed records. `unit` is the unit the ledger's `train_rows` is counted in:
# a claim count beside a policy-row numerator would make the share meaningless, so the French severity
# entry is 26,444 claims (not the 24,944 policies carrying them) and the Spanish severity entry is
# 5,950 claiming policies (not the 11,167 claim-equivalents the weighted fit counts).
DATASET_SIZES = {
    "coil2000": DatasetSize(
        9822,
        "policy",
        "docs/experiments/pilot2-phase2/FINETUNING_EXPERIMENT_REFERENCE.md",
    ),
    "uslapseagent": DatasetSize(
        29317,
        "policy",
        "docs/experiments/pilot2-phase2/FINETUNING_EXPERIMENT_REFERENCE.md",
    ),
    "eudirectlapse": DatasetSize(
        23060,
        "policy",
        "docs/experiments/pilot2-phase2/FINETUNING_EXPERIMENT_REFERENCE.md",
    ),
    "spanish_motor_lapse": DatasetSize(
        53502,
        "policy",
        "docs/experiments/frontier-benchmark/regime_characterization.md",
    ),
    "freMTPL2freq": DatasetSize(
        678013,
        "policy",
        "docs/experiments/fair-test-freq-sev/REGRESSOR_FINETUNING_PREREGISTRATION_FREQ_SEV_2026-11.md",
    ),
    "spanish_motor_freq": DatasetSize(
        53502,
        "policy",
        "docs/experiments/fair-test-freq-sev/REGRESSOR_FINETUNING_PREREGISTRATION_FREQ_SEV_2026-11.md",
    ),
    "freMTPL2sev": DatasetSize(
        26444,
        "claim",
        "docs/experiments/fair-test-freq-sev/REGRESSOR_FINETUNING_PREREGISTRATION_FREQ_SEV_2026-11.md",
        "the 26,444 claims sit on 24,944 policies",
    ),
    "spanish_motor_severity": DatasetSize(
        5950,
        "claiming policy",
        "docs/experiments/fair-test-freq-sev/REGRESSOR_FINETUNING_PREREGISTRATION_FREQ_SEV_2026-11.md",
        "11,167 claim-equivalents carry the claim weight",
    ),
}

# The share is a fraction of eligible rows, printed to four decimal places so two runs on the same
# tree write the same bytes.
SHARE_PLACES = 4


def dataset_size(dataset: str) -> DatasetSize:
    """The curated size of a dataset, or a refusal.

    A dataset with no entry would otherwise render an empty `eligible_rows` and an empty share, which
    reads as "the dataset has no size" rather than "nobody sourced one". Adding a campaign to the
    registry without a sourced size must fail here instead.
    """
    size = DATASET_SIZES.get(dataset)
    if size is None:
        raise EvidenceError(
            f"{dataset!r} has no curated DATASET_SIZES entry: add its prepared row count, unit and "
            "source pointer rather than letting the ledger render blank"
        )
    return size


def share_of_eligible(row: LedgerRow) -> str:
    """`train_rows / eligible_rows`, or blank when the row records no training budget.

    Computed per row, never stored: the same dataset has a 10,000-row arm and a full-pool baseline.
    A blank numerator gives a blank share — the Spanish `no-capture` rows — while `eligible_rows`
    stays populated, because the dataset's size does not depend on whether a capture exists.
    """
    if row.train_rows is None:
        return ""
    return f"{row.train_rows / dataset_size(row.dataset).eligible_rows:.{SHARE_PLACES}f}"


# Curated withdrawals. Mechanical replacement detection returns zero on this evidence (the Runs are
# seed-disjoint by construction; three duplicate launches were discarded before commit and their ids
# are not in the tree), so supersession is a list with a decision beside it. D22 withdraws D21's
# *reasoning*, not its stop, so the row names both: D21 is the stop, D22 the amendment. The label is
# built from those two fields so the column cannot be filled with one and forget the other.
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


def withdrawal_label(item: dict) -> str:
    """The decision that withdrew a row, and its amendment when it has one."""
    label = item["decision"]
    if item.get("amendment"):
        label += f" (amended by {item['amendment']})"
    return label


# One curated `no-capture` cell. The breadth replication ran 16 fresh seeds on `spanish_motor_lapse`
# at 10,000 rows; its records are runtime evidence on the launch machine and were never committed, so
# no per-seed row can be built without inventing one. The cell is listed with blank metrics, and with
# its epoch and row fields blank too: they would be read off the arm label and the prose, not off a
# record. The breadth result owns those numbers, and the note says so.
BREADTH_SEEDS = "341-356"
BREADTH_CELL = {
    "experiment_family": "pilot2-breadth-spanish",
    "dataset": "spanish_motor_lapse",
    "arms": ("A_raw", "B_ft30"),
    "source": "docs/experiments/pilot2-phase2/finetuning_breadth_spanish_result.md",
    "note": (
        f"breadth replication, seeds {BREADTH_SEEDS}: curated pointer, no capture and no committed "
        "per-seed record — the breadth result owns the 10,000-row, 30-epoch description, so the epoch "
        "and row fields are blank and the numbers are cited via finetuning_breadth_spanish_result.md, "
        "not a Capture"
    ),
}


class EvidenceError(SystemExit):
    """The evidence disagrees with itself; the ledger refuses rather than smoothing it over."""


@dataclass(frozen=True)
class LedgerRow:
    """One measurement. The three labels every row must state carry no default on purpose.

    `problem_type`, `task` and `era` defaulting to the classification line's values would let a
    regression row that forgot one be mislabelled rather than refused, so they are required.
    """

    run_id: str
    experiment_family: str
    problem_type: str
    task: str
    era: str
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
    fold: int | None = None
    rmse: float | None = None
    verdict_metric: str = ""
    verdict_metric_value: float | None = None
    superseded_by_or_decision: str = ""
    superseded_reason: str = ""
    note: str = ""
    source: str = ""
    model_version: str = ""
    checkpoint: str = ""
    weights_sha256: str = ""

    @property
    def cell(self) -> tuple:
        """The identity of one measurement, read from `IDENTITY_KEY`.

        `train_rows` and `fold` are in the key on purpose: the first keeps two budgets apart, the
        second keeps a five-fold regression cell from collapsing into one row.
        """
        return tuple(getattr(self, field) for field in IDENTITY_KEY)


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
    """The epochs the record says actually ran, for a classification record.

    `effective_config.kwargs.epochs` is the only honest source. The sibling `config.epochs` is the
    job's *source* config and reads 3 on every record; the Run manifest reads 3 as well. Reading
    either would label a 30-epoch arm as 3 epochs.
    """
    kwargs = (record.get("effective_config") or {}).get("kwargs") or {}
    epochs = kwargs.get("epochs")
    return None if epochs is None else int(epochs)


def regression_epochs(record: dict, arm: str) -> int | None:
    """The epochs a regression record says ran, from its top-level `epochs`.

    A regression record has no `effective_config` block: the count is top-level. The raw control
    records `0` — a real epoch count, not a blank — and a comparator Method records none. Both the
    `0` and the `None` are asserted rather than read off the arm label.
    """
    if "epochs" not in record:
        raise EvidenceError(
            f"{record.get('run_id')}: no top-level `epochs` — the regression record must record one"
        )
    epochs = record["epochs"]
    if arm == "A_raw":
        if epochs is None or int(epochs) != 0:
            raise EvidenceError(f"{arm}: the raw control records {epochs} epoch(s), not 0")
        return 0
    if FT_LABEL.match(arm):
        if epochs is None:
            raise EvidenceError(f"{arm}: records no epoch count")
        assert_epoch_agrees(arm, int(epochs))
        return int(epochs)
    if epochs is not None:
        raise EvidenceError(f"{arm}: a comparator records {epochs} epoch(s); none apply")
    return None


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
    """No identity key may repeat, across every campaign and both problem types.

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
    missing = [metric for metric in CLASSIFICATION_METRICS if record.get(metric) is None]
    if missing:
        raise EvidenceError(
            f"{record.get('run_id')}: no {', '.join(missing)} — the ledger does not invent one"
        )
    return {metric: float(record[metric]) for metric in CLASSIFICATION_METRICS}


def _regression_metrics(record: dict) -> dict:
    """The regression block, read from the record — the verdict metric's name included.

    Severity's metric differs by portfolio: French severity records `rmse` because its weight is
    exactly 1, Spanish severity records `weighted_rmse`. Reading a fixed name would mislabel one of
    them, so the name is taken from the field and only checked against the known set.
    """
    missing = [
        field for field in ("rmse", "verdict_metric", "verdict_metric_value")
        if record.get(field) is None
    ]
    if missing:
        raise EvidenceError(
            f"{record.get('run_id')}: no {', '.join(missing)} — the ledger does not invent one"
        )
    metric = str(record["verdict_metric"])
    if metric not in REGRESSION_VERDICT_METRICS:
        raise EvidenceError(f"{record.get('run_id')}: unknown verdict metric {metric!r}")
    return {
        "rmse": float(record["rmse"]),
        "verdict_metric": metric,
        "verdict_metric_value": float(record["verdict_metric_value"]),
    }


def _record_fields(record: dict, arm: str, campaign: Campaign) -> dict:
    """What an arm × (seed, fold) record contributes, with every trap handled once.

    The epoch assertion lives here so a new reader of `meta.json` cannot skip it. `train_rows` is cast
    because it is declared an int and sorts as one: a record that stored it as a string would otherwise
    sort beside the numbers and print unrounded. The weights sha is taken from the provenance block
    where there is one and from the record's own `weights` block otherwise — the launch records have no
    provenance block and still name the bytes they ran, and the regression records name the checkpoint
    only through `weights.path`.
    """
    if campaign.problem_type == "regression":
        epochs = regression_epochs(record, arm)
        metrics = _regression_metrics(record)
        weights = record.get("weights") or {}
        return {
            "epochs": epochs,
            "fold": None if record.get("fold") is None else int(record["fold"]),
            "train_rows": None if record.get("train_rows") is None else int(record["train_rows"]),
            "roc_auc": None,
            "brier": None,
            "pr_auc": None,
            "rmse": metrics["rmse"],
            "verdict_metric": metrics["verdict_metric"],
            "verdict_metric_value": metrics["verdict_metric_value"],
            "model_version": "",
            "checkpoint": Path(weights["path"]).name if weights.get("path") else "",
            "weights_sha256": weights.get("sha256", ""),
        }

    epochs = epochs_from_record(record)
    assert_epoch_agrees(arm, epochs)
    metrics = _cell_metrics(record)
    model = (record.get("provenance") or {}).get("model") or {}
    checkpoints = record.get("checkpoints") or []
    return {
        "epochs": epochs,
        "fold": None,
        "train_rows": None if record.get("train_rows") is None else int(record["train_rows"]),
        "roc_auc": metrics["roc_auc"],
        "brier": metrics["brier"],
        "pr_auc": metrics["pr_auc"],
        "rmse": None,
        "verdict_metric": "",
        "verdict_metric_value": None,
        "model_version": model.get("version", ""),
        "checkpoint": checkpoints[0] if checkpoints else "",
        "weights_sha256": model.get("weights_sha256")
        or (record.get("weights") or {}).get("sha256", ""),
    }


def _capture_entries(campaign: Campaign, results: Path, readme: Path | None):
    """Every record a campaign's Runs commit, read through their `capture.json`.

    Yields `(run_id, dataset, task, record_path, entry, record)`. Three ways a tree can disagree
    with itself are refused here, so no capture-reading loader can skip one: a Run the registry
    names with no Capture, a capture entry with no record, and a record present in the tree that
    the Capture does not cover. Both readers below consume this fully, so the stray check runs.
    """
    for run_id in campaign.run_list(readme):
        run_dir = results / run_id
        capture_path = run_dir / "capture.json"
        if not capture_path.is_file():
            raise EvidenceError(
                f"{run_id} is named by the {campaign.campaign_id} registry but has no capture.json"
            )
        capture = json.loads(capture_path.read_text())
        dataset = capture.get("dataset")
        if not dataset:
            raise EvidenceError(f"{run_id}: capture.json names no dataset")
        task = _task_for(campaign, run_id, dataset)

        covered: set[Path] = set()
        for entry in capture.get("captures", []):
            record_path = run_dir / dataset / entry["record"]
            if not record_path.is_file():
                raise EvidenceError(f"{run_id}: capture entry {entry['record']} has no record")
            covered.add(record_path.resolve())
            yield run_id, dataset, task, record_path, entry, json.loads(record_path.read_text())

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


def capture_rows(
    results: Path = RESULTS,
    readme: Path | None = None,
    campaign: Campaign | None = None,
) -> list[LedgerRow]:
    """One row per captured arm × seed record, for the Runs the campaign names.

    The Run id is the directory's, never the record's: a record's own `run_id` is
    `<dataset>_<arm>_seed<N>`. The record itself lives at
    `results/<run>/<dataset>/<arm>/<seed>_foldNone/`, because `capture.json`'s `record` omits the
    dataset level. `readme` overrides the campaign's own index, for a fixture tree.
    """
    campaign = campaign or CAMPAIGN_BY_ID["pilot2-phase2"]
    rows: list[LedgerRow] = []
    for run_id, dataset, task, record_path, entry, record in _capture_entries(
        campaign, results, readme
    ):
        arm = record.get("arm") or entry.get("arm")
        if arm is None:
            raise EvidenceError(f"{run_id}: {entry['record']} names no arm")
        _assert_arm_known(campaign, run_id, arm)
        if record.get("dataset") and record["dataset"] != dataset:
            raise EvidenceError(
                f"{run_id}: {entry['record']} is {record['dataset']}, the capture is {dataset}"
            )
        if record.get("status") != "success":
            raise EvidenceError(
                f"{run_id}: {entry['record']} is {record.get('status')!r}, not a success"
            )

        seed = record.get("seed", entry.get("seed"))
        fields = _record_fields(record, arm, campaign)
        rows.append(
            LedgerRow(
                run_id=run_id,
                experiment_family=campaign.campaign_id,
                problem_type=campaign.problem_type,
                task=task,
                era=campaign.era,
                dataset=dataset,
                arm=arm,
                arm_kind=arm_kind(arm),
                seed=None if seed is None else int(seed),
                status="current",
                source=_relative(record_path),
                note="" if fields["model_version"] == "auto" else "model version not recorded",
                **fields,
            )
        )
    return rows


def regression_rows(campaign: Campaign, results: Path = RESULTS) -> list[LedgerRow]:
    """One row per captured arm × seed × fold record, for a regression campaign's Runs.

    The record names `task`, `fold`, `n_folds`, `train_rows`, `rmse` and the verdict metric; the
    registry states the task the dataset serves and is asserted against it. The arm is the record's
    `arm` where it has one and its `method` otherwise — the baseline records carry `arm: null` — and
    the directory must agree with whichever field named it.
    """
    rows: list[LedgerRow] = []
    for run_id, dataset, task, record_path, entry, record in _capture_entries(
        campaign, results, None
    ):
        arm = (
            record.get("arm")
            or entry.get("arm")
            or record.get("method")
            or entry.get("method")
        )
        if arm is None:
            raise EvidenceError(f"{run_id}: {entry['record']} names no arm and no method")
        _assert_arm_known(campaign, run_id, arm)
        path_arm = record_path.parent.parent.name
        if path_arm != arm:
            raise EvidenceError(
                f"{_relative(record_path)}: the path names {path_arm!r}, the record {arm!r}"
            )
        if record.get("task") != task:
            raise EvidenceError(
                f"{_relative(record_path)}: the record's task is {record.get('task')!r}, the "
                f"registry says {task!r} for {dataset}"
            )
        if record.get("status") not in (None, "success"):
            raise EvidenceError(
                f"{_relative(record_path)}: status {record.get('status')!r}, not a success"
            )
        if record.get("n_folds") != 5:
            raise EvidenceError(
                f"{_relative(record_path)}: n_folds is {record.get('n_folds')!r}, not 5"
            )
        fold = record.get("fold", entry.get("fold"))
        if fold is None:
            raise EvidenceError(
                f"{_relative(record_path)}: a regression record with no fold; the identity key "
                "needs one"
            )

        seed = record.get("seed", entry.get("seed"))
        if seed is None:
            raise EvidenceError(f"{_relative(record_path)}: no seed")
        fields = _record_fields(record, arm, campaign)
        if fields["fold"] != int(fold):
            raise EvidenceError(
                f"{_relative(record_path)}: the fold disagrees with the capture entry"
            )
        rows.append(
            LedgerRow(
                run_id=run_id,
                experiment_family=campaign.campaign_id,
                problem_type=campaign.problem_type,
                task=task,
                era=campaign.era,
                dataset=dataset,
                arm=arm,
                arm_kind=arm_kind(arm),
                seed=int(seed),
                status="current",
                source=_relative(record_path),
                **fields,
            )
        )
    return rows


def _task_for(campaign: Campaign, run_id: str, dataset: str) -> str:
    if dataset not in campaign.datasets:
        raise EvidenceError(
            f"{run_id}: capture names {dataset!r}, which the {campaign.campaign_id} registry "
            "does not list"
        )
    return campaign.tasks[dataset]


def _assert_arm_known(campaign: Campaign, run_id: str, arm: str) -> None:
    if arm not in campaign.arm_labels:
        raise EvidenceError(
            f"{run_id}: arm {arm!r} is not in the {campaign.campaign_id} registry's labels "
            f"{campaign.arm_labels}"
        )


def pilot_rows(
    aggregate: Path = PILOT_AGGREGATE, campaign: Campaign | None = None
) -> list[LedgerRow]:
    """The 2,000-row R1 pilot's 16 aggregate rows, and nothing else from that file.

    Epochs stay blank: the file records `max_finetune_steps`, which is a different parameter and is
    carried by the comparator rows as well, so it cannot be read as an arm-level epoch count. There
    is no provenance block, so the model version and the weights sha stay blank rather than being
    borrowed from the captures.

    Twelve of these cells are also committed as per-arm records under `outputs/gpu-pilot/`. The
    aggregate is the chosen form — it is the only form covering all sixteen cells, so one pilot is not
    read from two files — and `pilot_cell_overlaps` reports every cell where the two disagree.
    """
    import pandas as pd

    campaign = campaign or CAMPAIGN_BY_ID["r1-pilot"]
    if not aggregate.is_file():
        raise EvidenceError(f"missing pilot aggregate: {_relative(aggregate)}")
    frame = pd.read_parquet(aggregate)

    rows: list[LedgerRow] = []
    for record in frame.to_dict("records"):
        arm = record["arm"]
        kind = arm_kind(arm)
        _assert_arm_known(campaign, _relative(aggregate), arm)
        task = _task_for(campaign, _relative(aggregate), record["dataset"])
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
                experiment_family=campaign.campaign_id,
                problem_type=campaign.problem_type,
                task=task,
                era=campaign.era,
                dataset=record["dataset"],
                arm=arm,
                arm_kind=kind,
                epochs=None,
                seed=int(record["seed"]),
                fold=None,
                train_rows=int(record["train_rows"]),
                roc_auc=float(record["roc_auc"]),
                brier=float(record["brier"]),
                pr_auc=float(record["pr_auc"]),
                status="superseded" if withdrawn else "current",
                superseded_by_or_decision=withdrawal_label(withdrawn) if withdrawn else "",
                superseded_reason=withdrawn["reason"] if withdrawn else "",
                note="2,000-row pilot aggregate: epochs not recorded, no provenance block",
                source=_relative(aggregate),
                checkpoint=checkpoint,
                model_version="",
            )
        )
    return rows


def launch_rows(
    runs: Path = GPU_PILOT_RUNS, campaign: Campaign | None = None
) -> list[LedgerRow]:
    """Records committed under `outputs/gpu-pilot/runs/<run>/<dataset>/<arm>/` — no Capture.

    These carry real metrics and a real checkpoint, but no `capture.json`: they cannot be cited as a
    Capture. They are Rows with status `no-capture`, and their pointer is the record file.

    A record with no arm fails the loader rather than being skipped: the document claims nothing was
    dropped, and a silent `continue` would make that claim false while still printing a total. A
    missing `runs/` directory is different — it is an absent source, and the family simply has no rows.
    """
    campaign = campaign or CAMPAIGN_BY_ID["gpu-pilot"]
    rows: list[LedgerRow] = []
    if not runs.is_dir():
        return rows
    for run_dir in sorted(path for path in runs.iterdir() if path.is_dir()):
        for record_path in sorted(run_dir.glob("*/*/meta.json")):
            record = json.loads(record_path.read_text())
            arm = record.get("arm")
            if arm is None:
                raise EvidenceError(f"{_relative(record_path)}: launch record names no arm")
            _assert_arm_known(campaign, run_dir.name, arm)
            task = _task_for(campaign, run_dir.name, record["dataset"])
            fields = _record_fields(record, arm, campaign)
            rows.append(
                LedgerRow(
                    run_id=run_dir.name,
                    experiment_family=campaign.campaign_id,
                    problem_type=campaign.problem_type,
                    task=task,
                    era=campaign.era,
                    dataset=record["dataset"],
                    arm=arm,
                    arm_kind=arm_kind(arm),
                    seed=int(record["seed"]),
                    status="no-capture",
                    note=(
                        "launch record with no capture.json — cite by description "
                        f"({_relative(record_path)}), not a Capture"
                    ),
                    source=_relative(record_path),
                    **fields,
                )
            )
    return rows


def breadth_rows(
    cell: dict = BREADTH_CELL, campaign: Campaign | None = None
) -> list[LedgerRow]:
    """The one curated `no-capture` cell, with blank metrics and no invented seed rows.

    `epochs` and `train_rows` are blank on purpose. The arm label says `B_ft30` and the breadth result
    says 10,000 training rows, but neither is a per-seed record: this row is a pointer to the result
    that owns those numbers, not a measurement, and a label-derived epoch presented as a recorded one
    is the trap this ledger exists to avoid.
    """
    campaign = campaign or CAMPAIGN_BY_ID["pilot2-breadth-spanish"]
    task = _task_for(campaign, cell["dataset"], cell["dataset"])
    return [
        LedgerRow(
            run_id="",
            experiment_family=campaign.campaign_id,
            problem_type=campaign.problem_type,
            task=task,
            era=campaign.era,
            dataset=cell["dataset"],
            arm=arm,
            arm_kind=arm_kind(arm),
            epochs=None,
            seed=None,
            fold=None,
            train_rows=None,
            roc_auc=None,
            brier=None,
            pr_auc=None,
            status="no-capture",
            note=cell["note"],
            source=cell["source"],
        )
        for arm in cell["arms"]
    ]


def pilot_cell_overlaps(
    aggregate: Path = PILOT_AGGREGATE, records: Path = GPU_PILOT_RECORDS
) -> list[dict]:
    """Every 2,000-row pilot cell recorded twice: aggregate rows beside the per-arm records.

    Twelve of the aggregate's sixteen cells also exist as `outputs/gpu-pilot/<dataset>/<arm>/meta.json`.
    Both forms are experiment output and neither carries a `provenance` block (the records are older
    schema: `versions` and a weights block, but no `provenance`), so `DOCUMENT_AUTHORITY.md`'s "a number
    resolves to the capture" chooses neither — and there is no Capture for these cells at all. The
    ledger takes the aggregate and the document prints every cell where the two disagree, with both
    values, so the choice is visible rather than implicit. `disagrees` compares at the six decimal
    places the ledger prints.
    """
    import pandas as pd

    if not aggregate.is_file():
        raise EvidenceError(f"missing pilot aggregate: {_relative(aggregate)}")
    frame = pd.read_parquet(aggregate)
    indexed = {
        (
            record["dataset"],
            record["arm"],
            int(record["seed"]),
            int(record["train_rows"]),
        ): record
        for record in frame.to_dict("records")
    }

    overlaps: list[dict] = []
    for record_path in sorted(records.glob("*/*/meta.json")):
        record = json.loads(record_path.read_text())
        if record.get("train_rows") is None or record.get("seed") is None:
            continue
        key = (
            record["dataset"],
            record["arm"],
            int(record["seed"]),
            int(record["train_rows"]),
        )
        aggregate_row = indexed.get(key)
        if aggregate_row is None:
            continue
        metrics = {
            metric: (float(aggregate_row[metric]), float(record[metric]))
            for metric in CLASSIFICATION_METRICS
            if record.get(metric) is not None
        }
        overlaps.append(
            {
                "dataset": key[0],
                "arm": key[1],
                "seed": key[2],
                "train_rows": key[3],
                "metrics": metrics,
                "disagrees": [
                    metric
                    for metric in CLASSIFICATION_METRICS
                    if metric in metrics
                    and round(metrics[metric][0], 6) != round(metrics[metric][1], 6)
                ],
                "device": (
                    f"{aggregate_row.get('device_name') or '—'} → "
                    f"{record.get('device_name') or '—'}"
                ),
                "record_source": _relative(record_path),
                "record_has_provenance": bool(record.get("provenance")),
            }
        )
    return overlaps


@dataclass(frozen=True)
class Sources:
    """Where every loader reads from, injected whole so one seam can point at a fixture tree."""

    results: Path = RESULTS
    readme: Path | None = None
    aggregate: Path = PILOT_AGGREGATE
    launches: Path = GPU_PILOT_RUNS


# Loader dispatch, by name. Each campaign's `loader` is a key here, and the registry is checked
# against the map at import, so a typo stops the generator before it reads a tree rather than after.
LOADERS = {
    "capture": lambda campaign, sources: capture_rows(
        sources.results, sources.readme, campaign
    ),
    "aggregate": lambda campaign, sources: pilot_rows(sources.aggregate, campaign),
    "launch": lambda campaign, sources: launch_rows(sources.launches, campaign),
    "curated": lambda campaign, sources: breadth_rows(campaign=campaign),
    "regression": lambda campaign, sources: regression_rows(campaign, sources.results),
}

_UNKNOWN_LOADERS = sorted({campaign.loader for campaign in CAMPAIGNS} - set(LOADERS))
if _UNKNOWN_LOADERS:
    raise RuntimeError(
        f"the campaign registry names loader(s) the map does not define: {_UNKNOWN_LOADERS}"
    )


def load_rows(
    results: Path = RESULTS,
    readme: Path | None = None,
    aggregate: Path = PILOT_AGGREGATE,
    launches: Path = GPU_PILOT_RUNS,
) -> list[LedgerRow]:
    """Every row, asserted, and in a total order so the same tree yields the same bytes."""
    sources = Sources(results, readme, aggregate, launches)
    rows: list[LedgerRow] = []
    for campaign in CAMPAIGNS:
        rows += LOADERS[campaign.loader](campaign, sources)
    assert_seed_disjoint(rows)
    return sorted(rows, key=_sort_key)


def _sort_key(row: LedgerRow):
    return (
        PROBLEM_ORDER.get(row.problem_type, 99),
        CAMPAIGN_ORDER.get(row.experiment_family, 99),
        row.dataset,
        ARM_ORDER.get(row.arm, 99),
        row.train_rows if row.train_rows is not None else -1,
        row.seed if row.seed is not None else -1,
        row.fold if row.fold is not None else -1,
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
        "problem_type": row.problem_type,
        "task": row.task,
        "era": row.era,
        "dataset": row.dataset,
        "arm": row.arm,
        "arm_kind": row.arm_kind,
        "epochs": _integer(row.epochs),
        "seed": _integer(row.seed),
        "fold": _integer(row.fold),
        "train_rows": _integer(row.train_rows),
        "eligible_rows": _integer(dataset_size(row.dataset).eligible_rows),
        "share_of_eligible": share_of_eligible(row),
        "roc_auc": _number(row.roc_auc, 6),
        "brier": _number(row.brier, 6),
        "pr_auc": _number(row.pr_auc, 6),
        "rmse": _number(row.rmse, 6),
        "verdict_metric": row.verdict_metric,
        "verdict_metric_value": _number(row.verdict_metric_value, 6),
        "status": row.status,
        "superseded_by_or_decision": row.superseded_by_or_decision,
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
    """`n`, mean and min–max per problem type × campaign × dataset × arm × training rows.

    Descriptive only: no interval, because an interval would be an inference and the ledger owns no
    verdict. Superseded and `no-capture` rows are excluded — a withdrawn row is not evidence a mean
    should carry, and a launch with no Capture would enter a mean over captured runs.

    The campaign is in the summary key because it is in the identity key: the two baseline budgets
    capture one Spanish severity fit under two run ids, and merging them would enter the same
    measurement twice in one `n`. Grouping by training rows splits a full-pool baseline by a row or
    two between folds; that is the recorded per-fold budget, not a design arm.

    Each block carries only its own metrics. A classification entry has no `rmse` key and a
    regression entry has no `roc_auc` key, so an absent metric cannot be read as a zero.
    """
    groups: dict[tuple, list[dict[str, str]]] = {}
    for row in csv_rows:
        if row["status"] != "current":
            continue
        group = (
            row["problem_type"],
            row["experiment_family"],
            row["dataset"],
            row["arm"],
            row["train_rows"],
        )
        groups.setdefault(group, []).append(row)

    summary = []
    for (problem_type, family, dataset, arm, train_rows), members in sorted(
        groups.items(),
        key=lambda item: (
            PROBLEM_ORDER.get(item[0][0], 99),
            CAMPAIGN_ORDER.get(item[0][1], 99),
            item[0][2],
            ARM_ORDER.get(item[0][3], 99),
            int(item[0][4]),
        ),
    ):
        entry = {
            "problem_type": problem_type,
            "family": family,
            "task": members[0]["task"],
            "dataset": dataset,
            "arm": arm,
            "train_rows": train_rows,
            "n": len(members),
        }
        for metric in SUMMARY_METRICS[problem_type]:
            values = [float(member[metric]) for member in members if member[metric] != ""]
            entry[metric] = {
                "mean": sum(values) / len(values) if values else None,
                "min": min(values) if values else None,
                "max": max(values) if values else None,
            }
        if problem_type == "regression":
            names = {member["verdict_metric"] for member in members if member["verdict_metric"]}
            if len(names) != 1:
                raise EvidenceError(
                    f"{dataset} / {arm}: {len(names)} verdict metrics in one cell: {sorted(names)}"
                )
            entry["verdict_metric"] = names.pop()
        summary.append(entry)
    return summary


def _table(headers: list[str], body: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    lines.extend("| " + " | ".join(cells) + " |" for cells in body)
    return lines


def _pin_sentence(problem_type: str, checkpoint: str, sha: str, members: list[dict]) -> str:
    """One problem type's pin, in the words its own rows support."""
    short = f"{sha[:8]}...{sha[-6:]}"
    versions = sorted({row["model_version"] for row in members if row["model_version"]})
    eras = sorted({row["era"] for row in members if row["era"]})
    era = " or ".join(f"`{value}`" for value in eras) if eras else "blank"
    if not versions:
        return (
            f"- {problem_type.capitalize()} rows record no `model_version`; their weights block "
            f"names the checkpoint `{checkpoint}` and weights sha256 `{short}`, so `era` reads "
            f"{era}."
        )
    recorded = ", ".join(f"`{value}`" for value in versions)
    qualifier = " — a value that names no version — " if set(versions) == {"auto"} else " "
    sentence = (
        f"- {problem_type.capitalize()} rows that record a version name `model_version` "
        f"{recorded}{qualifier}beside the checkpoint `{checkpoint}` and weights sha256 "
        f"`{short}`; `era` reads {era}."
    )
    without = [row for row in members if not row["model_version"]]
    if without:
        families = ", ".join(
            f"`{family}`" for family in sorted({row["experiment_family"] for row in without})
        )
        sentence += (
            f" The other {len(without)} of the {len(members)} {problem_type} rows record none "
            f"({families})."
        )
    return sentence


def _pin_lines(csv_rows: list[dict[str, str]]) -> list[str]:
    """The model pins, per problem type, as the rows state them.

    Every claim here is read from the CSV: the checkpoint and sha from the two columns, and the
    version and era from the same rows, so a campaign whose era changes cannot leave this prose
    lying while the byte comparison still passes. A classification record says `auto` — a value that
    names no version; a regression record names no `model_version` at all and its weights block names
    the regressor checkpoint, which is where the era comes from.
    """
    lines = [
        "**The model is named by its record, and the version is never inferred.** No row here is",
        "described as v3.5: a version is printed only where a record names one, and `auto` is never",
        "re-described as a version. No table subtracts one era or one model family from another.",
        "",
    ]
    for problem_type in ("classification", "regression"):
        members = [row for row in csv_rows if row["problem_type"] == problem_type]
        pairs = {
            (row["checkpoint"], row["weights_sha256"])
            for row in members
            if row["checkpoint"] or row["weights_sha256"]
        }
        if not pairs:
            continue
        if len(pairs) != 1:
            raise EvidenceError(
                f"the {problem_type} rows name more than one checkpoint or weights sha: "
                f"{sorted(pairs)}"
            )
        checkpoint, sha = next(iter(pairs))
        lines.append(_pin_sentence(problem_type, checkpoint, sha, members))
    return lines


def render_document(csv_rows: list[dict[str, str]], overlaps: list[dict] | None = None) -> str:
    """The campaign document, rendered from the CSV — and its one audit table from the sources.

    `overlaps` is the only content that does not come from the CSV: it compares the rejected form of the
    2,000-row pilot with the one the ledger reads, and the document says so where it prints it. The
    dataset descriptions are curated prose; the dataset, task, problem type and campaign columns
    beside them are read from the CSV.
    """
    if overlaps is None:
        overlaps = pilot_cell_overlaps()
    summary = summarise(csv_rows)
    families = sorted(
        {row["experiment_family"] for row in csv_rows},
        key=lambda family: CAMPAIGN_ORDER.get(family, 99),
    )
    statuses = sorted({row["status"] for row in csv_rows})
    superseded = [row for row in csv_rows if row["status"] == "superseded"]
    no_capture = [row for row in csv_rows if row["status"] == "no-capture"]
    differing_overlaps = [overlap for overlap in overlaps if overlap["disagrees"]]
    pilot_count = sum(1 for row in csv_rows if row["experiment_family"] == "r1-pilot")
    by_family = {
        family: [row for row in csv_rows if row["experiment_family"] == family]
        for family in families
    }
    family_counts = "; ".join(f"`{family}` {len(by_family[family])}" for family in families)
    status_list = ", ".join(f"`{status}`" for status in statuses)
    problem_counts = ", ".join(
        f"{sum(row['problem_type'] == problem_type for row in csv_rows)} {problem_type}"
        for problem_type in ("classification", "regression")
    )

    lines = [
        "# Runs ledger — every committed fine-tuning and fair-test run, classification and regression",
        "",
        "> **Status:** current — generated ledger, 2026-11-20. **Generated, not written:** rebuild it",
        "> with `python scripts/analyses/finetuning_runs_ledger.py`; a hand edit is overwritten and a",
        "> number typed here is a number with no evidence behind it.",
        "",
        "**Question.** What did the programme run, and what did it score — for lapse classification and",
        "for frequency/severity regression? One row per run × arm × seed (classification) or",
        "run × arm × seed × fold (regression), and a descriptive summary per task underneath. This is a",
        "reference, not a new verdict: it re-runs nothing, adds no interval, and changes no claim.",
        "",
        "**Provenance.** Built for the map's ledger tickets (#663 → #665 → #668). The classification",
        "fields and traps are the research note's (#664); the regression records add `task`, `fold`,",
        "`n_folds` and a verdict metric. Every row states its problem type, task and era, so a",
        "classification AUC and a regression RMSE cannot be read as the same kind of number.",
        "",
        "**Machine form.** [`finetuning_runs_ledger.csv`](../../analyses/data/finetuning_runs_ledger.csv)",
        "carries the same rows, one line each, with the full source pointer. The tables below are",
        "rendered from it, so they cannot disagree with it.",
        "",
        f"**Rows.** {len(csv_rows)} ({problem_counts}) across {len(families)} experiment families: "
        f"{family_counts}. Statuses present: {status_list}.",
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
        campaign = CAMPAIGN_BY_ID[family]
        source_rows.append(
            [
                f"`{family}`",
                campaign.problem_type,
                str(len(members)),
                counts,
                campaign.record_path,
            ]
        )
    lines += _table(["family", "problem type", "rows", "statuses", "read from"], source_rows)
    lines += [
        "",
        "Each family is read from the place the table names, and selected by **campaign membership and",
        "dataset**, never by \"has an `ft` arm\": the fair test, the baselines and the pilot all carry",
        "the same `A_raw` / `B_ft30` labels. In short:",
        "",
    ]
    for family in families:
        lines.append(f"- `{family}` — {CAMPAIGN_BY_ID[family].what}.")
    lines += [
        "",
        "## What each dataset is, and which task it serves",
        "",
        "The gap a reader hit: a row's dataset did not say whether it was a lapse classifier or a",
        "frequency/severity regressor, or what the data was. The dataset, task and problem type are",
        "read from the CSV; the description is curated from the campaigns' own target tables.",
        "",
    ]

    dataset_rows = []
    for dataset in sorted({row["dataset"] for row in csv_rows}):
        members = [row for row in csv_rows if row["dataset"] == dataset]
        campaigns = ", ".join(
            f"`{family}`" for family in families
            if any(row["experiment_family"] == family for row in members)
        )
        size = dataset_size(dataset)
        unit = size.unit if not size.detail else f"{size.unit} — {size.detail}"
        dataset_rows.append(
            [
                dataset,
                members[0]["task"],
                members[0]["problem_type"],
                f"{int(members[0]['eligible_rows']):,}",
                unit,
                DATASET_NOTES.get(dataset, "—"),
                campaigns,
            ]
        )
    lines += _table(
        [
            "dataset",
            "task",
            "problem type",
            "eligible rows",
            "unit",
            "what it is",
            "campaigns",
        ],
        dataset_rows,
    )
    lines += [
        "",
        "**The eligible-row count is curated from the pre-registrations' own dataset tables**, not",
        "derived from the captures: a capture covers the arms that ran, not the prepared dataset that",
        "existed. Each count's source is the dataset table in",
        "`FINETUNING_EXPERIMENT_REFERENCE.md` (the lapse datasets), `regime_characterization.md`",
        "(Spanish motor) or",
        "`REGRESSOR_FINETUNING_PREREGISTRATION_FREQ_SEV_2026-11.md` (frequency and severity), and the",
        "unit is the one the ledger's `train_rows` is counted in. The share is **per row**, not per",
        "dataset: `train_rows / eligible_rows`, because `freMTPL2freq` carries a 10,000-row TabPFN line",
        "and a 542,410-row full-pool baseline, and one share for the dataset would be wrong for one of",
        "them.",
        "",
        "## The ledger",
        "",
        "One row per run × arm × seed, or per run × arm × seed × fold where the evidence has folds.",
        "`epochs` is blank where no epoch applies (the comparator Methods) and where the source records",
        "no arm-level epoch count (the 2,000-row pilot) or no record at all (the curated Spanish cell);",
        "`epochs = 0` on a regression raw control is a recorded count, not a blank. `train_rows` and",
        "`fold` are part of the key: `uslapseagent` seed 42 exists at 2,000 and at 10,000 rows, and a",
        "five-fold regression cell is five measurements. `eligible_rows` is the dataset's curated",
        "prepared size in the row's own unit, and `share_of_eligible` is `train_rows / eligible_rows`,",
        "computed per row. A blank `train_rows` gives a blank share — the curated Spanish `no-capture`",
        "cell — while its `eligible_rows` still states the dataset's size, which does not depend on",
        "whether a capture exists.",
        "",
    ]

    body = []
    for row in csv_rows:
        body.append(
            [
                f"`{row['run_id']}`" if row["run_id"] else "—",
                row["experiment_family"],
                row["problem_type"],
                row["task"],
                row["era"],
                row["dataset"],
                f"`{row['arm']}`",
                row["arm_kind"],
                row["epochs"] or "—",
                row["seed"] or "—",
                row["fold"] or "—",
                f"{int(row['train_rows']):,}" if row["train_rows"] else "—",
                f"{int(row['eligible_rows']):,}" if row["eligible_rows"] else "—",
                row["share_of_eligible"] or "—",
                row["roc_auc"] or "—",
                row["brier"] or "—",
                row["pr_auc"] or "—",
                row["rmse"] or "—",
                row["verdict_metric"] or "—",
                row["verdict_metric_value"] or "—",
                row["status"],
            ]
        )
    lines += _table(
        [
            "run id",
            "family",
            "type",
            "task",
            "era",
            "dataset",
            "arm",
            "arm kind",
            "epochs",
            "seed",
            "fold",
            "train rows",
            "eligible rows",
            "share of eligible",
            "ROC AUC",
            "Brier",
            "PR-AUC",
            "RMSE",
            "verdict metric",
            "verdict value",
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
        ["run id", "dataset", "arm", "seed", "fold", "train rows", "status", "withdrawn by", "why"],
        [
            [
                f"`{row['run_id']}`" if row["run_id"] else "—",
                row["dataset"],
                f"`{row['arm']}`",
                row["seed"] or "—",
                row["fold"] or "—",
                row["train_rows"] or "—",
                row["status"],
                row["superseded_by_or_decision"] or "—",
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
    ]
    if overlaps:
        disagreeing_arms = ", ".join(
            f"`{arm}`" for arm in sorted({overlap["arm"] for overlap in differing_overlaps})
        )
        unrecorded_cells = pilot_count - len(overlaps)
        lines += [
            "## The 2,000-row pilot, recorded twice",
            "",
            f"{len(overlaps)} of the aggregate's {pilot_count} cells are also committed as per-arm "
            "records under",
            "`outputs/gpu-pilot/<dataset>/<arm>/meta.json`.",
            f"{len(overlaps) - len(differing_overlaps)} of them agree to six decimal places and "
            f"{len(differing_overlaps)} do not:",
            "",
        ]
        overlap_body = []
        for overlap in differing_overlaps:
            for metric in overlap["disagrees"]:
                aggregate_value, record_value = overlap["metrics"][metric]
                overlap_body.append(
                    [
                        overlap["dataset"],
                        f"`{overlap['arm']}`",
                        metric,
                        f"{aggregate_value:.6f}",
                        f"{record_value:.6f}",
                        overlap["device"],
                    ]
                )
        if overlap_body:
            lines += _table(
                ["dataset", "arm", "metric", "aggregate", "record", "device (aggregate → record)"],
                overlap_body,
            )
        lines += [
            "",
            "**Both forms are experiment output, and neither carries a `provenance` block.** The records",
            "are an older schema: `versions` and a weights block, which name libraries and bytes, not a",
            "capture. So `DOCUMENT_AUTHORITY.md`'s \"a number resolves to the capture\" chooses neither,",
            "and there is no Capture for these cells at all. **This ledger reads the aggregate for every",
            f"cell.** It is the only form that covers all {pilot_count} — the {unrecorded_cells} cells",
            "with no per-arm record exist nowhere else — and splitting one pilot's metrics across two",
            "files would leave no rule for which file wins. Every differing cell above is on arm",
            f"{disagreeing_arms}, and the device column shows why: the aggregate holds a GPU re-run",
            "where the record may hold the CPU run. The R1 results report states that device variance",
            "itself (§4b) and warns that the aggregate mixes provenance; the ledger quotes the",
            "aggregate's device for every cell rather than switching sources cell by cell.",
            "",
            "This table is the one part of this document not rendered from the CSV: it compares the",
            "chosen form with the rejected one, so it reads both.",
            "",
        ]
    lines += [
        "## Summary — dataset × arm × training rows",
        "",
        "`n`, mean and min–max across seeds (and folds, where the evidence has them, and instances,",
        "where a dataset has more than one Run). **Descriptive only: no interval and no verdict**, so",
        "the ledger cannot contradict an analysis that owns one. Current rows only — a withdrawn row",
        "would put a stopped cell inside a mean, and a `no-capture` row would put a launch with no",
        "Capture inside a mean over captured Runs. A line with `n = 1` prints the value and `single",
        "run`: an absent range is not a zero-width one. The 2,000-row and 10,000-row cells are separate",
        "lines for the same reason `train_rows` is part of the key.",
        "",
        "### Classification — ROC AUC, Brier and PR-AUC",
        "",
    ]

    classification_body = []
    for entry in summary:
        if entry["problem_type"] != "classification":
            continue
        classification_body.append(
            [
                f"`{entry['family']}`",
                entry["problem_type"],
                entry["task"],
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
            "family",
            "type",
            "task",
            "dataset",
            "arm",
            "train rows",
            "n",
            "ROC AUC mean (min–max)",
            "Brier mean (min–max)",
            "PR-AUC mean (min–max)",
        ],
        classification_body,
    )
    lines += [
        "",
        "### Regression — RMSE and the record's verdict metric",
        "",
        "The verdict metric is named per line because it is the record's, not a global choice: French",
        "severity records unweighted RMSE, Spanish severity the claim-weighted RMSE.",
        "",
    ]

    regression_body = []
    for entry in summary:
        if entry["problem_type"] != "regression":
            continue
        regression_body.append(
            [
                f"`{entry['family']}`",
                entry["problem_type"],
                entry["task"],
                entry["dataset"],
                f"`{entry['arm']}`",
                f"{int(entry['train_rows']):,}",
                str(entry["n"]),
                _range(entry["rmse"], 4, entry["n"]),
                f"`{entry['verdict_metric']}`",
                _range(entry["verdict_metric_value"], 4, entry["n"]),
            ]
        )
    lines += _table(
        [
            "family",
            "type",
            "task",
            "dataset",
            "arm",
            "train rows",
            "n",
            "RMSE mean (min–max)",
            "verdict metric",
            "verdict metric mean (min–max)",
        ],
        regression_body,
    )
    lines += [
        "",
        "The campaign is in this key because it is in the ledger's identity key: the two baseline",
        "budgets capture one Spanish severity fit under two run ids, and merging them would count the",
        "same fit twice. Grouping by training rows splits a full-pool baseline across the fold pool's",
        "one-row differences; that is the recorded per-fold budget, not a design arm.",
        "",
    ]
    lines += [
        "",
        "## How to read a row",
        "",
        "**`arm_kind` is derived, never recorded.** `A_raw` is the raw control (`raw`); `B_ft3`,",
        "`B_ft10`, `B_ft30` and the pilot's `B_in_domain` are fine-tuned (`fine-tuned`); `E_glm`,",
        "`F_catboost` and `M_intercept` are comparator Methods (`comparator`), not Arms of the",
        "programme. The baseline records carry `arm: null` and name the method in `method`; the",
        "generator takes the label from the record and asserts it against the directory name.",
        "",
        "**Epochs come from the record that trained, not from the config that launched.** For a",
        "classification record the source is `effective_config.kwargs.epochs`; `config.epochs` — and",
        "every Run manifest — reads `3` on every arm, including the 30-epoch one. A regression record",
        "names its count at the top level instead, where the raw control records `0` and a comparator",
        "records none. The generator asserts the recorded count equals the number in the `B_ftN` label",
        "and fails on a disagreement rather than smoothing it. The 2,000-row pilot records no",
        "arm-level epoch count at all (`max_finetune_steps` is a different parameter, carried by the",
        "comparator rows too), so its `epochs` column is blank, not `3`. The curated Spanish cell is",
        "blank for a stronger reason: there is no record to read one from.",
        "",
        "**Two metric blocks, and a blank is \"not applicable\".** A classification row records ROC",
        "AUC, Brier and PR-AUC; a regression row records RMSE and its verdict metric with the value.",
        "The other block is blank on that row, and a blank is never rendered as `0`: the evidence",
        "records no such number, and inventing one would make two tasks look comparable when they are",
        "not. `log_loss` and `ece` are recorded on the classification captures and are deliberately",
        "outside this ledger (the map's out-of-scope list, #663), not missing from it.",
        "",
        "**A superseded row names what withdrew it.** `superseded_by_or_decision` holds the replacing",
        "run id when a replacement was detected, or the decision that withdrew the row when one was",
        "curated; `superseded_reason` holds the prose. On this evidence replacement detection returns",
        "zero rows, so the four `coil2000` rows read `D21 (amended by D22)` and the column is not empty",
        "on any row whose status is `superseded`.",
        "",
        *_pin_lines(csv_rows),
        "",
        "**`source` is the pointer to the bytes.** For a capture row it is the per-`meta.json` record,",
        "because `capture.json` holds hashes and the record holds the numbers; the Run id is in the",
        "`run_id` column, taken from the directory. A per-seed record's own `run_id`",
        "(`<dataset>_<arm>_seed<N>`) is **not** the Run id and is not used as one.",
        "",
        "**A `no-capture` row cannot be cited as a Capture.** The Spanish breadth cell's per-seed records",
        "were never committed, so its rows carry blank metrics, no seed and blank `epochs` /",
        "`train_rows` — one row per arm, because a per-seed row would be an invention — and a pointer to",
        "[`finetuning_breadth_spanish_result.md`](finetuning_breadth_spanish_result.md). The breadth",
        "result owns the design's 10,000-row, 30-epoch description; this row is a pointer to it, and a",
        "label-derived epoch in an `epochs` column would be presented as a recorded one. Cite the",
        "result, not a Capture. The `gpu-pilot` rows do carry metrics, from committed launch records",
        "that are not Captures; they are cited by description, the way `REPORT_REGISTRY.md` already",
        "handles them.",
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
        # An absent range must not read as a zero-width one.
        return f"{values['mean']:.{places}f} — single run"
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
        f"{sum(row.problem_type == 'classification' for row in rows)} classification, "
        f"{sum(row.problem_type == 'regression' for row in rows)} regression — "
        f"{sum(row.status == 'current' for row in rows)} current, "
        f"{sum(row.status == 'superseded' for row in rows)} superseded, "
        f"{sum(row.status == 'no-capture' for row in rows)} no-capture"
    )
    print(f"wrote {_relative(args.out_csv)}")
    print(f"wrote {_relative(args.out_doc)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
