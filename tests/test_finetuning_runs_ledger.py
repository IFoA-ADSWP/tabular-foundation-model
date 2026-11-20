"""The runs ledger (#665, extended #668): what the evidence records, and what must not be smoothed.

The traps are the tests. The ledger's whole value is that it reads the field that trained rather than
the field that launched, keeps two measurements that look like a duplicate apart, and refuses an
evidence tree the campaign index disagrees with — and each of those has a way of quietly returning a
plausible answer instead. The regression half adds two more: a fold is part of the identity, and a
blank metric is not a zero.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "analyses" / "finetuning_runs_ledger.py"
COMMITTED_CSV = REPO / "docs" / "analyses" / "data" / "finetuning_runs_ledger.csv"
COMMITTED_DOC = REPO / "docs" / "experiments" / "pilot2-phase2" / "FINETUNING_RUNS_LEDGER.md"


def _row(module, **overrides):
    values = {
        "run_id": "20261104T122235Z",
        "experiment_family": "pilot2-phase2",
        "problem_type": "classification",
        "task": "lapse",
        "era": "auto",
        "dataset": "uslapseagent",
        "arm": "A_raw",
        "arm_kind": "raw",
        "epochs": None,
        "seed": 45,
        "train_rows": 10000,
        "roc_auc": 0.95,
        "brier": 0.08,
        "pr_auc": 0.90,
        "status": "current",
    }
    values.update(overrides)
    return module.LedgerRow(**values)


def _capture(results: Path, run_id: str, dataset: str, slots) -> None:
    """A minimal committed Run: `capture.json` plus one record per (arm, seed)."""
    run = results / run_id
    entries = []
    for arm, seed, epochs in slots:
        record = run / dataset / arm / f"seed{seed}_foldNone" / "meta.json"
        record.parent.mkdir(parents=True)
        payload = {
            "schema_version": 4,
            "run_id": f"{dataset}_{arm}_seed{seed}",
            "dataset": dataset,
            "arm": arm,
            "seed": seed,
            "train_rows": 10000,
            "status": "success",
            "roc_auc": 0.5,
            "brier": 0.1,
            "pr_auc": 0.2,
            "config": {"epochs": 3},
            "effective_config": {"kwargs": {}},
            "checkpoints": ["tabpfn-v3-classifier-v3_default.ckpt"],
            "provenance": {"model": {"version": "auto", "weights_sha256": "abc"}},
        }
        if epochs is not None:
            payload["effective_config"]["kwargs"]["epochs"] = epochs
        record.write_text(json.dumps(payload))
        entries.append(
            {
                "arm": arm,
                "seed": seed,
                "rows": 1000,
                "record": f"{arm}/seed{seed}_foldNone/meta.json",
            }
        )
    run.mkdir(parents=True, exist_ok=True)
    (run / "capture.json").write_text(
        json.dumps({"schema_version": 1, "run_id": run_id, "dataset": dataset, "captures": entries})
    )


def _campaign(readme: Path, run_ids) -> None:
    readme.parent.mkdir(parents=True, exist_ok=True)
    lines = "\n".join(run_ids)
    readme.write_text(f"# Campaign\n\n## Runs\n\nCommitted under `results/`:\n\n```\n{lines}\n```\n")


def _launch_record(
    runs: Path,
    run_id: str,
    dataset: str,
    arm: str | None,
    *,
    seed: int = 42,
    epochs: int | None = None,
    train_rows: int = 10000,
) -> Path:
    """One committed launch record — real metrics, no capture.json, no provenance block."""
    path = runs / run_id / dataset / (arm or "unlabelled") / "meta.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": f"{dataset}_{arm}_seed{seed}",
        "dataset": dataset,
        "seed": seed,
        "train_rows": train_rows,
        "status": "success",
        "roc_auc": 0.9,
        "brier": 0.1,
        "pr_auc": 0.8,
        "effective_config": {"kwargs": {} if epochs is None else {"epochs": epochs}},
        "checkpoints": ["tabpfn-v3-classifier-v3_default.ckpt"],
        "weights": {"sha256": "abc123"},
        "provenance": None,
    }
    if arm is not None:
        payload["arm"] = arm
    path.write_text(json.dumps(payload))
    return path


def _pilot_cells() -> list[dict]:
    """The 2,000-row pilot's shape: four datasets × four arms, seed 42."""
    return [
        {
            "run_id": f"{dataset}_{arm}_seed42",
            "dataset": dataset,
            "arm": arm,
            "seed": 42,
            "train_rows": 2000,
            "roc_auc": 0.7,
            "brier": 0.1,
            "pr_auc": 0.5,
            "checkpoints": ["tabpfn-v3-classifier-v3_default.ckpt"],
        }
        for dataset in ("coil2000", "eudirectlapse", "spanish_motor_lapse", "uslapseagent")
        for arm in ("A_raw", "B_in_domain", "E_glm", "F_catboost")
    ]


def _pilot_aggregate(path: Path, rows: list[dict] | None = None) -> Path:
    import pandas as pd

    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows if rows is not None else _pilot_cells()).to_parquet(path)
    return path


def test_two_runs_write_byte_identical_files(tmp_path, load_script):
    module = load_script("finetuning_runs_ledger", SCRIPT)

    first_csv, first_doc = tmp_path / "a.csv", tmp_path / "a.md"
    second_csv, second_doc = tmp_path / "b.csv", tmp_path / "b.md"
    module.main(["--out-csv", str(first_csv), "--out-doc", str(first_doc)])
    module.main(["--out-csv", str(second_csv), "--out-doc", str(second_doc)])

    assert first_csv.read_bytes() == second_csv.read_bytes()
    assert first_doc.read_bytes() == second_doc.read_bytes()


def test_the_committed_artefacts_are_byte_identical_to_a_fresh_render(tmp_path, load_script):
    """A hand edit to the CSV or the rendered document would otherwise pass every check."""
    module = load_script("finetuning_runs_ledger", SCRIPT)
    out_csv, out_doc = tmp_path / "ledger.csv", tmp_path / "ledger.md"

    module.main(["--out-csv", str(out_csv), "--out-doc", str(out_doc)])

    assert out_csv.read_bytes() == COMMITTED_CSV.read_bytes(), (
        "docs/analyses/data/finetuning_runs_ledger.csv is not what the generator writes"
    )
    assert out_doc.read_bytes() == COMMITTED_DOC.read_bytes(), (
        "docs/experiments/pilot2-phase2/FINETUNING_RUNS_LEDGER.md is not what the generator writes"
    )


def test_the_markdown_ledger_is_rendered_from_the_csv(tmp_path, load_script):
    module = load_script("finetuning_runs_ledger", SCRIPT)
    out_csv, out_doc = tmp_path / "ledger.csv", tmp_path / "ledger.md"
    module.main(["--out-csv", str(out_csv), "--out-doc", str(out_doc)])

    rows = module.read_csv(out_csv)
    section = out_doc.read_text().split("## The ledger", 1)[1].split("## The rows that", 1)[0]
    table = [line for line in section.splitlines() if line.startswith("| ")]
    # The header and its separator, then one line per CSV row.
    assert len(table) - 2 == len(rows)


def test_epochs_come_from_the_effective_config_and_the_label_must_agree(load_script):
    module = load_script("finetuning_runs_ledger", SCRIPT)
    record = {
        "arm": "B_ft30",
        "config": {"epochs": 3},
        "effective_config": {"kwargs": {"epochs": 30}},
    }

    assert module.epochs_from_record(record) == 30
    module.assert_epoch_agrees("B_ft30", 30)

    with pytest.raises(module.EvidenceError):
        module.assert_epoch_agrees("B_ft30", 3)
    with pytest.raises(module.EvidenceError):
        module.assert_epoch_agrees("A_raw", 30)


def test_the_anchor_records_a_10_epoch_fit_whose_config_says_three(load_script):
    """The live case: the note's trap is in the committed evidence, not only in a fixture."""
    module = load_script("finetuning_runs_ledger", SCRIPT)
    rows = [
        row
        for row in module.load_rows()
        if row.run_id == "20261031T021845Z" and row.arm == "B_ft10"
    ]

    assert rows, "the anchor's B_ft10 arm is missing from the ledger"
    assert {row.epochs for row in rows} == {10}


def test_the_2000_and_10000_row_cells_for_seed_42_stay_two_rows(load_script):
    module = load_script("finetuning_runs_ledger", SCRIPT)
    rows = [
        row
        for row in module.load_rows()
        if (row.dataset, row.arm, row.seed) == ("uslapseagent", "A_raw", 42)
    ]

    assert sorted(row.train_rows for row in rows) == [2000, 10000]
    assert len({row.cell for row in rows}) == 2


def test_seed_disjointness_fires_on_a_fabricated_duplicate(load_script):
    module = load_script("finetuning_runs_ledger", SCRIPT)
    first = _row(module, run_id="20261104T122235Z")
    module.assert_seed_disjoint([first])

    duplicate = _row(module, run_id="20261104T123839Z")
    with pytest.raises(module.EvidenceError, match="repeats"):
        module.assert_seed_disjoint([first, duplicate])


def test_the_committed_evidence_is_seed_disjoint(load_script):
    """Mechanical replacement detection must return zero rows, and the ledger asserts it."""
    module = load_script("finetuning_runs_ledger", SCRIPT)
    captures = module.capture_rows()

    assert len(captures) == 580
    module.assert_seed_disjoint(captures)


def test_the_coil2000_pilot_rows_name_the_decision_that_withdrew_them(load_script):
    module = load_script("finetuning_runs_ledger", SCRIPT)
    rows = [row for row in module.load_rows() if row.dataset == "coil2000"]

    assert len(rows) == 4
    assert {row.status for row in rows} == {"superseded"}
    for row in rows:
        assert row.superseded_by_or_decision == "D21 (amended by D22)"
        assert row.superseded_reason


def test_no_superseded_row_leaves_the_withdrawing_decision_blank(load_script):
    module = load_script("finetuning_runs_ledger", SCRIPT)
    superseded = [row for row in module.load_rows() if row.status == "superseded"]

    assert superseded
    assert [row for row in superseded if not row.superseded_by_or_decision] == []


def test_the_spanish_breadth_rows_are_no_capture_and_invent_no_fields(load_script):
    module = load_script("finetuning_runs_ledger", SCRIPT)
    rows = [
        row
        for row in module.load_rows()
        if row.dataset == "spanish_motor_lapse" and row.status == "no-capture"
    ]

    assert {row.arm for row in rows} == {"A_raw", "B_ft30"}
    for row in rows:
        assert row.roc_auc is None and row.brier is None and row.pr_auc is None
        # A curated pointer, not a record: the breadth result owns the row count and epoch budget.
        assert row.epochs is None and row.train_rows is None
        assert "breadth result owns" in row.note
        assert "not a Capture" in row.note


def test_the_scope_guard_excludes_a_fair_test_shaped_capture(tmp_path, load_script):
    """Six fair-test Runs carry `A_raw`/`B_ft30` too; campaign membership is the selector."""
    module = load_script("finetuning_runs_ledger", SCRIPT)
    results = tmp_path / "results"
    readme = tmp_path / "README.md"

    _capture(results, "20261104T122235Z", "uslapseagent", [("A_raw", 45, None), ("B_ft30", 45, 30)])
    _capture(results, "20261112T164543Z", "freMTPL2freq", [("A_raw", 1, None), ("B_ft30", 1, 30)])
    _campaign(readme, ["20261104T122235Z"])

    rows = module.capture_rows(results, readme)

    assert {row.dataset for row in rows} == {"uslapseagent"}
    assert {row.experiment_family for row in rows} == {"pilot2-phase2"}


def test_a_campaign_run_without_a_capture_is_refused(tmp_path, load_script):
    module = load_script("finetuning_runs_ledger", SCRIPT)
    results = tmp_path / "results"
    readme = tmp_path / "README.md"
    results.mkdir()
    _campaign(readme, ["20261104T122235Z"])

    with pytest.raises(module.EvidenceError, match="no capture.json"):
        module.capture_rows(results, readme)


def test_the_summary_is_descriptive_only(load_script):
    module = load_script("finetuning_runs_ledger", SCRIPT)
    summary = module.summarise(
        [
            {
                "problem_type": "classification",
                "experiment_family": "pilot2-phase2",
                "task": "lapse",
                "dataset": "uslapseagent",
                "arm": "B_ft30",
                "train_rows": "10000",
                "status": "current",
                "roc_auc": "0.94",
                "brier": "0.08",
                "pr_auc": "0.89",
            },
            {
                "problem_type": "classification",
                "experiment_family": "pilot2-phase2",
                "task": "lapse",
                "dataset": "uslapseagent",
                "arm": "B_ft30",
                "train_rows": "10000",
                "status": "current",
                "roc_auc": "0.96",
                "brier": "0.06",
                "pr_auc": "0.91",
            },
        ]
    )

    assert len(summary) == 1
    entry = summary[0]
    assert entry["n"] == 2
    assert entry["roc_auc"] == {"mean": pytest.approx(0.95), "min": 0.94, "max": 0.96}
    assert set(entry) == {
        "problem_type",
        "family",
        "task",
        "dataset",
        "arm",
        "train_rows",
        "n",
        "roc_auc",
        "brier",
        "pr_auc",
    }


def test_a_single_run_prints_the_value_and_says_so(load_script):
    """`n = 1` must not render as a mean with an absent range that reads like a zero-width one."""
    module = load_script("finetuning_runs_ledger", SCRIPT)
    one = {"mean": 0.95, "min": 0.95, "max": 0.95}
    two = {"mean": 0.95, "min": 0.94, "max": 0.96}

    assert module._range(one, 4, 1) == "0.9500 — single run"
    assert module._range(two, 4, 2) == "0.9500 (0.9400–0.9600)"


def test_the_pilot_loader_reads_sixteen_cells_from_an_injected_aggregate(
    tmp_path, load_script
):
    module = load_script("finetuning_runs_ledger", SCRIPT)
    with pytest.raises(module.EvidenceError, match="missing pilot aggregate"):
        module.pilot_rows(tmp_path / "absent.parquet")

    aggregate = _pilot_aggregate(tmp_path / "pilot_metrics.parquet")
    rows = module.pilot_rows(aggregate)

    assert len(rows) == 16
    assert {row.experiment_family for row in rows} == {"r1-pilot"}
    assert {row.seed for row in rows} == {42}
    assert {row.train_rows for row in rows} == {2000}
    assert all(row.epochs is None for row in rows)


def test_the_launch_loader_reads_four_records_from_an_injected_tree(tmp_path, load_script):
    module = load_script("finetuning_runs_ledger", SCRIPT)
    runs = tmp_path / "runs"
    for arm, epochs in (("A_raw", None), ("B_ft3", 3), ("B_ft10", 10), ("B_ft30", 30)):
        _launch_record(runs, "20260914T010247Z", "uslapseagent", arm, epochs=epochs)

    rows = module.launch_rows(runs)

    assert len(rows) == 4
    assert {row.run_id for row in rows} == {"20260914T010247Z"}
    assert {row.status for row in rows} == {"no-capture"}
    assert {row.arm_kind for row in rows} == {"raw", "fine-tuned"}
    ft30 = next(row for row in rows if row.arm == "B_ft30")
    assert ft30.epochs == 30
    assert ft30.weights_sha256 == "abc123"
    assert ft30.model_version == ""


def test_the_launch_loader_treats_an_absent_tree_as_no_rows(tmp_path, load_script):
    module = load_script("finetuning_runs_ledger", SCRIPT)

    assert module.launch_rows(tmp_path / "absent") == []


def test_the_launch_loader_refuses_a_record_with_no_arm(tmp_path, load_script):
    """A `continue` here would make the document's "nothing was dropped" false by construction."""
    module = load_script("finetuning_runs_ledger", SCRIPT)
    runs = tmp_path / "runs"
    _launch_record(runs, "20260914T010247Z", "uslapseagent", "A_raw")
    _launch_record(runs, "20260914T010247Z", "uslapseagent", None)

    with pytest.raises(module.EvidenceError, match="names no arm"):
        module.launch_rows(runs)


def test_the_pilot_overlap_is_listed_and_the_aggregate_is_the_chosen_form(load_script):
    """Twelve cells are recorded twice; the ledger takes the aggregate and says why."""
    module = load_script("finetuning_runs_ledger", SCRIPT)
    overlaps = module.pilot_cell_overlaps()

    assert len(overlaps) == 12
    # Neither form carries a provenance block, so neither outranks the other by evidence.
    assert {overlap["record_has_provenance"] for overlap in overlaps} == {False}
    differing = {
        (overlap["dataset"], overlap["arm"]): overlap
        for overlap in overlaps
        if overlap["disagrees"]
    }
    assert set(differing) == {
        ("coil2000", "A_raw"),
        ("eudirectlapse", "A_raw"),
        ("spanish_motor_lapse", "A_raw"),
        ("uslapseagent", "A_raw"),
    }
    aggregate_value, record_value = differing[("spanish_motor_lapse", "A_raw")]["metrics"][
        "roc_auc"
    ]
    assert aggregate_value == pytest.approx(0.723295)
    assert record_value == pytest.approx(0.723028)

    rows = [
        row
        for row in module.load_rows()
        if row.experiment_family == "r1-pilot"
        and row.dataset == "spanish_motor_lapse"
        and row.arm == "A_raw"
    ]
    assert len(rows) == 1
    # The pin: the ledger carries the aggregate's value, not the record's.
    assert rows[0].roc_auc == pytest.approx(aggregate_value)
    assert rows[0].source.endswith("pilot_metrics.parquet")


# --- The cross-task half (#668) ---------------------------------------------------------------

def _regression_row(module, **overrides):
    """One regression row, with the classification block blank."""
    values = {
        "run_id": "20261112T164543Z",
        "experiment_family": "fair-test-freq-sev",
        "problem_type": "regression",
        "task": "frequency",
        "era": "v3_default",
        "dataset": "freMTPL2freq",
        "arm": "B_ft30",
        "arm_kind": "fine-tuned",
        "epochs": 30,
        "seed": 0,
        "fold": 0,
        "train_rows": 10000,
        "roc_auc": None,
        "brier": None,
        "pr_auc": None,
        "rmse": 0.24,
        "verdict_metric": "poisson_deviance",
        "verdict_metric_value": 3200.0,
        "status": "current",
    }
    values.update(overrides)
    return module.LedgerRow(**values)


FAIR_RUN = "20261112T164543Z"


def _regression_run(
    results: Path, run_id: str, slots, dataset: str = "freMTPL2freq"
) -> None:
    """A committed regression Run: `capture.json` plus one record per fold slot.

    Each slot is the record's own fields. `path_arm` puts the record in a directory that disagrees
    with its `arm`, and a field set to `None` — in the slot, in `record` or in `entry` — is absent
    from the record or the capture entry, so a fixture can omit what a refusal is about.
    """
    run = results / run_id
    entries = []
    for slot in slots:
        arm = slot["arm"]
        path_arm = slot.get("path_arm", arm)
        seed = slot.get("seed", 0)
        fold = slot.get("fold", 0)
        name = f"seed{seed}_fold{fold}"
        payload = {
            "schema_version": 5,
            "run_id": f"{dataset}_{path_arm}_seed{seed}",
            "dataset": dataset,
            "arm": arm,
            "seed": seed,
            "fold": fold,
            "n_folds": 5,
            "task": "frequency",
            "train_rows": 10000,
            "status": "success",
            "epochs": 30,
            "rmse": 0.24,
            "verdict_metric": "poisson_deviance",
            "verdict_metric_value": 3200.0,
            "weights": {
                "path": "checkpoints/tabpfn-v3-regressor-v3_default.ckpt",
                "sha256": "ab12cd34ef56",
            },
        }
        payload.update(slot.get("record", {}))
        payload = {key: value for key, value in payload.items() if value is not None}
        record = run / dataset / path_arm / name / "meta.json"
        record.parent.mkdir(parents=True, exist_ok=True)
        record.write_text(json.dumps(payload))
        entry = {
            "arm": path_arm,
            "seed": seed,
            "fold": fold,
            "record": f"{path_arm}/{name}/meta.json",
        }
        entry.update(slot.get("entry", {}))
        entries.append({key: value for key, value in entry.items() if value is not None})
    run.mkdir(parents=True, exist_ok=True)
    (run / "capture.json").write_text(
        json.dumps(
            {"schema_version": 1, "run_id": run_id, "dataset": dataset, "captures": entries}
        )
    )


def _regression_campaign(module, run_id: str = FAIR_RUN):
    """The fair-test registry entry, narrowed to one Run so a fixture needs one capture."""
    return dataclasses.replace(
        module.CAMPAIGN_BY_ID["fair-test-freq-sev"], run_ids=(run_id,)
    )


def test_regression_rows_carry_five_folds_per_seed_and_the_verdict_metric(load_script):
    """One row per run × arm × seed × fold: a five-fold cell is five measurements, not one."""
    module = load_script("finetuning_runs_ledger", SCRIPT)
    rows = [
        row
        for row in module.load_rows()
        if row.problem_type == "regression"
        and row.dataset == "freMTPL2freq"
        and row.arm == "B_ft30"
        and row.experiment_family == "fair-test-freq-sev"
    ]

    assert len(rows) == 15
    assert {row.seed for row in rows} == {0, 1, 2}
    assert {row.fold for row in rows} == {0, 1, 2, 3, 4}
    assert {row.verdict_metric for row in rows} == {"poisson_deviance"}
    assert all(row.rmse is not None and row.verdict_metric_value is not None for row in rows)
    assert len({row.cell for row in rows}) == 15
    assert {row.task for row in rows} == {"frequency"}


def test_the_severity_verdict_metric_is_read_not_assumed(load_script):
    """French severity records `rmse`; only Spanish severity carries the claim weight."""
    module = load_script("finetuning_runs_ledger", SCRIPT)
    rows = [row for row in module.load_rows() if row.problem_type == "regression"]

    assert {row.verdict_metric for row in rows if row.dataset == "freMTPL2sev"} == {"rmse"}
    assert {row.verdict_metric for row in rows if row.dataset == "spanish_motor_severity"} == {
        "weighted_rmse"
    }
    assert {row.task for row in rows if row.dataset == "freMTPL2sev"} == {"severity"}


def test_the_fold_key_keeps_a_fabricated_duplicate_apart(load_script):
    module = load_script("finetuning_runs_ledger", SCRIPT)
    first = _regression_row(module, fold=0)
    second_fold = _regression_row(module, fold=1)

    # Same run, arm, seed and budget — only the fold differs. Two rows, not a duplicate.
    module.assert_seed_disjoint([first, second_fold])
    assert len({first.cell, second_fold.cell}) == 2

    duplicate = _regression_row(module, fold=0)
    with pytest.raises(module.EvidenceError, match="repeats"):
        module.assert_seed_disjoint([first, duplicate])


def test_a_blank_metric_is_not_a_zero(load_script):
    """A regression row's classification block is blank, and vice versa — never 0."""
    module = load_script("finetuning_runs_ledger", SCRIPT)
    rows = module.load_rows()
    regression = next(row for row in rows if row.problem_type == "regression")
    classification = next(
        row
        for row in rows
        if row.problem_type == "classification" and row.roc_auc is not None
    )

    assert regression.roc_auc is None and regression.brier is None and regression.pr_auc is None
    assert classification.rmse is None
    assert classification.verdict_metric == "" and classification.verdict_metric_value is None

    regression_csv = module.csv_row(regression)
    classification_csv = module.csv_row(classification)
    assert regression_csv["roc_auc"] == regression_csv["brier"] == regression_csv["pr_auc"] == ""
    assert classification_csv["rmse"] == classification_csv["verdict_metric_value"] == ""
    assert classification_csv["verdict_metric"] == ""

    # The one legitimate zero is a recorded epoch count on a regression raw control.
    assert regression_csv["epochs"] == "0"


def test_classification_values_match_the_published_ledger(load_script):
    """A handful of values pinned from `fd3a58f`'s CSV: the extension must not move them."""
    module = load_script("finetuning_runs_ledger", SCRIPT)
    rows = [row for row in module.load_rows() if row.problem_type == "classification"]
    indexed = {
        (row.run_id, row.dataset, row.arm, row.seed): row
        for row in rows
        if row.run_id
    }

    anchor = indexed[("20261031T021845Z", "uslapseagent", "B_ft10", 43)]
    assert (anchor.roc_auc, anchor.brier, anchor.pr_auc) == pytest.approx(
        (0.951097, 0.080458, 0.900992)
    )
    assert (anchor.epochs, anchor.train_rows, anchor.arm_kind) == (10, 10000, "fine-tuned")

    coil = indexed[("coil2000_A_raw_seed42", "coil2000", "A_raw", 42)]
    assert (coil.roc_auc, coil.brier, coil.pr_auc) == pytest.approx(
        (0.767530, 0.050767, 0.187545), abs=1e-6
    )
    assert coil.status == "superseded"
    assert coil.superseded_by_or_decision == "D21 (amended by D22)"

    launch = indexed[("20260914T010247Z", "uslapseagent", "A_raw", 42)]
    assert (launch.roc_auc, launch.brier, launch.pr_auc) == pytest.approx(
        (0.945717, 0.083267, 0.885643), abs=1e-6
    )
    assert launch.status == "no-capture"

    spanish = indexed[("spanish_motor_lapse_A_raw_seed42", "spanish_motor_lapse", "A_raw", 42)]
    assert (spanish.roc_auc, spanish.brier, spanish.pr_auc) == pytest.approx(
        (0.723295, 0.197776, 0.570771), abs=1e-6
    )

    breadth = [
        row
        for row in rows
        if row.experiment_family == "pilot2-breadth-spanish" and row.arm == "A_raw"
    ]
    assert len(breadth) == 1
    assert breadth[0].run_id == "" and breadth[0].seed is None
    assert breadth[0].roc_auc is None and breadth[0].status == "no-capture"


def test_classification_rows_keep_their_problem_type_and_task(load_script):
    module = load_script("finetuning_runs_ledger", SCRIPT)
    rows = [row for row in module.load_rows() if row.problem_type == "classification"]

    assert {row.task for row in rows} == {"lapse"}
    assert {row.fold for row in rows} == {None}
    assert {row.era for row in rows} == {"auto"}


def test_the_baseline_methods_are_comparators(load_script):
    """The ticket names `E_glm` and `F_catboost`; the captures also carry `M_intercept`."""
    module = load_script("finetuning_runs_ledger", SCRIPT)
    rows = [
        row
        for row in module.load_rows()
        if row.problem_type == "regression" and row.experiment_family.startswith("actuarial")
    ]

    assert module.arm_kind("M_intercept") == "comparator"
    assert {row.arm for row in rows} == {"E_glm", "F_catboost", "M_intercept"}
    assert {row.arm_kind for row in rows} == {"comparator"}
    assert {row.verdict_metric for row in rows if row.dataset == "freMTPL2sev"} == {"rmse"}


def test_the_summary_reports_each_tasks_own_block(load_script):
    module = load_script("finetuning_runs_ledger", SCRIPT)
    rows = [module.csv_row(row) for row in module.load_rows()]
    summary = module.summarise(rows)

    classification = [entry for entry in summary if entry["problem_type"] == "classification"]
    regression = [entry for entry in summary if entry["problem_type"] == "regression"]
    assert classification and regression

    for entry in classification:
        assert entry["task"] == "lapse"
        assert "roc_auc" in entry and "brier" in entry and "pr_auc" in entry
        assert "rmse" not in entry and "verdict_metric" not in entry

    for entry in regression:
        assert entry["task"] in {"frequency", "severity"}
        assert "rmse" in entry and "verdict_metric_value" in entry
        assert entry["verdict_metric"] in {"poisson_deviance", "rmse", "weighted_rmse"}
        assert "roc_auc" not in entry and "brier" not in entry and "pr_auc" not in entry

    # The two baseline budgets are separate lines even where the fit is the same one.
    baselines = [
        entry
        for entry in regression
        if entry["dataset"] == "spanish_motor_severity"
        and entry["arm"] == "E_glm"
    ]
    assert {entry["family"] for entry in baselines} == {
        "actuarial-baseline-full",
        "actuarial-baseline-matched",
    }
    assert {entry["n"] for entry in baselines} == {15}


def test_the_row_scale_runs_stay_out_of_scope(load_script):
    """#572's row-scaling arms are the fair-test result's, not the ledger's (#668 scope)."""
    module = load_script("finetuning_runs_ledger", SCRIPT)
    run_ids = {row.run_id for row in module.load_rows()}

    assert "20261113T003320Z" not in run_ids
    assert "20261113T095502Z" not in run_ids
    assert {"20261112T164543Z", "20261112T210029Z"} <= run_ids


def test_regression_rows_carry_the_registered_era(load_script):
    module = load_script("finetuning_runs_ledger", SCRIPT)
    rows = [row for row in module.load_rows() if row.problem_type == "regression"]

    assert {row.era for row in rows} == {"v3_default"}
    assert {row.model_version for row in rows} == {""}
    assert {row.checkpoint for row in rows if row.arm == "B_ft30"} == {
        "tabpfn-v3-regressor-v3_default.ckpt"
    }


# --- The loader seams, at the interface a caller uses -----------------------------------------

def test_a_row_must_state_its_problem_type_task_and_era(load_script):
    """A defaulted label would mislabel a row that forgot one instead of refusing it."""
    module = load_script("finetuning_runs_ledger", SCRIPT)
    values = {
        "run_id": "20261112T164543Z",
        "experiment_family": "fair-test-freq-sev",
        "problem_type": "regression",
        "task": "frequency",
        "era": "v3_default",
        "dataset": "freMTPL2freq",
        "arm": "B_ft30",
        "arm_kind": "fine-tuned",
        "epochs": 30,
        "seed": 0,
        "train_rows": 10000,
        "roc_auc": None,
        "brier": None,
        "pr_auc": None,
        "status": "current",
    }
    module.LedgerRow(**values)

    for missing in ("problem_type", "task", "era"):
        with pytest.raises(TypeError):
            module.LedgerRow(
                **{key: value for key, value in values.items() if key != missing}
            )


def test_every_campaign_names_a_loader_in_the_dispatch_map(load_script):
    """The map is checked against the registry at import; this pins that it stays a map."""
    module = load_script("finetuning_runs_ledger", SCRIPT)

    assert {campaign.loader for campaign in module.CAMPAIGNS} <= set(module.LOADERS)


def _read_regression(module, tmp_path, slots, dataset: str = "freMTPL2freq"):
    results = tmp_path / "results"
    _regression_run(results, FAIR_RUN, slots, dataset=dataset)
    return module.regression_rows(_regression_campaign(module), results)


def test_the_regression_loader_reads_an_injected_fixture_tree(tmp_path, load_script):
    """The seam itself: a fixture tree, read through the campaign's own registry entry."""
    module = load_script("finetuning_runs_ledger", SCRIPT)

    rows = _read_regression(
        module,
        tmp_path,
        [{"arm": "B_ft30", "seed": 0, "fold": fold} for fold in range(5)],
    )

    assert len(rows) == 5
    assert {row.fold for row in rows} == {0, 1, 2, 3, 4}
    assert len({row.cell for row in rows}) == 5
    assert {row.problem_type for row in rows} == {"regression"}
    assert {row.task for row in rows} == {"frequency"}
    assert {row.verdict_metric for row in rows} == {"poisson_deviance"}
    assert {row.model_version for row in rows} == {""}
    assert {row.checkpoint for row in rows} == {"tabpfn-v3-regressor-v3_default.ckpt"}


def test_a_regression_run_without_a_capture_is_refused(tmp_path, load_script):
    module = load_script("finetuning_runs_ledger", SCRIPT)
    results = tmp_path / "results"
    results.mkdir()

    with pytest.raises(module.EvidenceError, match="no capture.json"):
        module.regression_rows(_regression_campaign(module), results)


def test_a_regression_record_must_sit_under_the_arm_it_names(tmp_path, load_script):
    """The directory names the arm; a record that disagrees is a different measurement."""
    module = load_script("finetuning_runs_ledger", SCRIPT)

    with pytest.raises(module.EvidenceError, match="the path names"):
        _read_regression(module, tmp_path, [{"arm": "A_raw", "path_arm": "B_ft30"}])


def test_a_regression_capture_must_name_a_registered_dataset(tmp_path, load_script):
    module = load_script("finetuning_runs_ledger", SCRIPT)

    with pytest.raises(module.EvidenceError, match="does not list"):
        _read_regression(module, tmp_path, [{"arm": "B_ft30"}], dataset="coil2000")


def test_a_regression_record_must_serve_the_registrys_task(tmp_path, load_script):
    """The registry maps the dataset to its task; the record is asserted against it."""
    module = load_script("finetuning_runs_ledger", SCRIPT)

    with pytest.raises(module.EvidenceError, match="the registry says"):
        _read_regression(
            module, tmp_path, [{"arm": "B_ft30", "record": {"task": "severity"}}]
        )


def test_a_regression_record_must_have_five_folds(tmp_path, load_script):
    module = load_script("finetuning_runs_ledger", SCRIPT)

    with pytest.raises(module.EvidenceError, match="not 5"):
        _read_regression(module, tmp_path, [{"arm": "B_ft30", "record": {"n_folds": 10}}])


def test_a_regression_record_with_no_fold_is_refused(tmp_path, load_script):
    """The fold is in the identity key; a row without one would collapse five measurements."""
    module = load_script("finetuning_runs_ledger", SCRIPT)

    with pytest.raises(module.EvidenceError, match="no fold"):
        _read_regression(module, tmp_path, [{"arm": "B_ft30", "fold": None}])


def test_a_regression_record_with_no_seed_is_refused(tmp_path, load_script):
    module = load_script("finetuning_runs_ledger", SCRIPT)

    with pytest.raises(module.EvidenceError, match="no seed"):
        _read_regression(
            module,
            tmp_path,
            [{"arm": "B_ft30", "seed": None, "entry": {"seed": None}}],
        )


def test_an_unknown_verdict_metric_is_refused(tmp_path, load_script):
    """The metric name is read, never assumed: an unrecognised one is not silently labelled."""
    module = load_script("finetuning_runs_ledger", SCRIPT)

    with pytest.raises(module.EvidenceError, match="unknown verdict metric"):
        _read_regression(
            module, tmp_path, [{"arm": "B_ft30", "record": {"verdict_metric": "mae"}}]
        )


# --- The pin prose follows the rows -----------------------------------------------------------

def _csv_record(module, **overrides):
    """One regression CSV row, as `read_csv` would hand it to the renderer."""
    values = dict.fromkeys(module.COLUMNS, "")
    values.update(
        {
            "experiment_family": "fair-test-freq-sev",
            "problem_type": "regression",
            "task": "frequency",
            "era": "fixture_era",
            "dataset": "freMTPL2freq",
            "arm": "B_ft30",
            "epochs": "30",
            "seed": "0",
            "fold": "0",
            "train_rows": "10000",
            "rmse": "0.240000",
            "verdict_metric": "poisson_deviance",
            "verdict_metric_value": "3200.000000",
            "status": "current",
            "checkpoint": "fixture-regressor.ckpt",
            "weights_sha256": "0123456789abcdef0123",
        }
    )
    values.update(overrides)
    return values


def test_the_pin_sentence_is_read_from_the_rows(load_script):
    """A changed campaign era must move the prose, not leave it lying behind a byte compare."""
    module = load_script("finetuning_runs_ledger", SCRIPT)

    unrecorded = "\n".join(module._pin_lines([_csv_record(module)]))
    assert "record no `model_version`" in unrecorded
    assert "`fixture_era`" in unrecorded

    recorded = "\n".join(
        module._pin_lines([_csv_record(module, model_version="fixture_version")])
    )
    assert "record no `model_version`" not in recorded
    assert "`fixture_version`" in recorded
    assert "`fixture_era`" in recorded


def test_the_pin_sentence_names_every_era_the_rows_record(load_script):
    module = load_script("finetuning_runs_ledger", SCRIPT)
    rows = [_csv_record(module), _csv_record(module, era="later_era")]

    assert "`fixture_era` or `later_era`" in "\n".join(module._pin_lines(rows))
