"""The fine-tuning runs ledger (#665): what the evidence records, and what must not be smoothed.

The traps are the tests. The ledger's whole value is that it reads the field that trained rather than
the field that launched, keeps two measurements that look like a duplicate apart, and refuses an
evidence tree the campaign index disagrees with — and each of those has a way of quietly returning a
plausible answer instead.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "analyses" / "finetuning_runs_ledger.py"


def _row(module, **overrides):
    values = {
        "run_id": "20261104T122235Z",
        "experiment_family": "pilot2-phase2",
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


def test_two_runs_write_byte_identical_files(tmp_path, load_script):
    module = load_script("finetuning_runs_ledger", SCRIPT)

    first_csv, first_doc = tmp_path / "a.csv", tmp_path / "a.md"
    second_csv, second_doc = tmp_path / "b.csv", tmp_path / "b.md"
    module.main(["--out-csv", str(first_csv), "--out-doc", str(first_doc)])
    module.main(["--out-csv", str(second_csv), "--out-doc", str(second_doc)])

    assert first_csv.read_bytes() == second_csv.read_bytes()
    assert first_doc.read_bytes() == second_doc.read_bytes()


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


def test_the_coil2000_pilot_rows_are_withdrawn_under_d21_and_d22(load_script):
    module = load_script("finetuning_runs_ledger", SCRIPT)
    rows = [row for row in module.load_rows() if row.dataset == "coil2000"]

    assert len(rows) == 4
    assert {row.status for row in rows} == {"superseded"}
    for row in rows:
        assert "D21" in row.superseded_reason
        assert "D22" in row.superseded_reason


def test_the_spanish_breadth_rows_are_no_capture_and_carry_no_metric(load_script):
    module = load_script("finetuning_runs_ledger", SCRIPT)
    rows = [
        row
        for row in module.load_rows()
        if row.dataset == "spanish_motor_lapse" and row.status == "no-capture"
    ]

    assert {row.arm for row in rows} == {"A_raw", "B_ft30"}
    for row in rows:
        assert row.roc_auc is None and row.brier is None and row.pr_auc is None
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
                "dataset": "uslapseagent",
                "arm": "B_ft30",
                "train_rows": "10000",
                "status": "current",
                "roc_auc": "0.94",
                "brier": "0.08",
                "pr_auc": "0.89",
            },
            {
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
    assert set(entry) == {"dataset", "arm", "train_rows", "n", "roc_auc", "brier", "pr_auc"}
