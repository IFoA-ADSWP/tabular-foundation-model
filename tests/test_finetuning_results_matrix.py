"""The paper matrix is generated, and this fails when it leaves its owners (#739)."""
from __future__ import annotations

import csv
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/analyses/finetuning_results_matrix.py"
DOC = REPO / "docs/shared/FINETUNING_RESULTS_MATRIX.md"
CSV = REPO / "docs/analyses/data/finetuning_results_matrix.csv"
LEDGER = REPO / "docs/analyses/data/finetuning_runs_ledger.csv"
LEDGER_DOC = REPO / "docs/experiments/pilot2-phase2/FINETUNING_RUNS_LEDGER.md"
PHASE2 = REPO / "docs/experiments/pilot2-phase2/FINETUNING_PHASE2_OUTCOME.md"
SPANISH = REPO / "docs/experiments/pilot2-phase2/finetuning_breadth_spanish_result.md"
LADDER = REPO / "docs/experiments/pilot2-phase2/EPOCH_LADDER_RESULT.md"
FAIR = REPO / "docs/experiments/fair-test-freq-sev/freq_sev_fair_test_result.md"

MINUS = str.maketrans({"\u2212": "-", "\u2013": "-", "\u2014": "-"})


def _load():
    spec = importlib.util.spec_from_file_location("finetuning_results_matrix", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def matrix():
    return _load()


@pytest.fixture(scope="module")
def all_rows(matrix):
    return matrix.rows()


def _ledger() -> list[dict[str, str]]:
    with LEDGER.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _owner_text(row) -> str:
    if row.source.startswith("Phase 2"):
        return PHASE2.read_text(encoding="utf-8").translate(MINUS)
    if row.source.startswith(("Fair test", "#572")):
        return FAIR.read_text(encoding="utf-8").translate(MINUS)
    if row.source.startswith("Ladder"):
        return LADDER.read_text(encoding="utf-8").translate(MINUS)
    raise AssertionError(f"no owner mapping for source {row.source!r}")


def _numbers(text: str) -> list[str]:
    return re.findall(r"\d+\.\d+", text)


def _owner_row(row) -> str:
    """The owner's table row for this dataset, so a transposed cell cannot pass by membership."""
    needle = f"`{row.dataset.strip('`')}`"
    matches = [
        line
        for line in _owner_text(row).splitlines()
        if line.lstrip().startswith("|") and needle in line
    ]
    assert len(matches) == 1, f"{row.dataset}: {len(matches)} owner rows in {row.source}"
    return matches[0]


def test_committed_files_match_the_generator():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_fair_test_cells_reproduce_the_analysis(matrix, all_rows):
    """A typed percentage would pass the drift check but not this one."""
    summary = matrix.fair_test.build_summary(
        matrix.FAIR_IDS,
        row_scale_french=matrix.ROW_SCALE_SEVERITY,
        row_scale_frequency=matrix.ROW_SCALE_FREQUENCY,
    )
    by_dataset = {
        row.dataset.strip("`"): row for row in all_rows if row.block == "targets"
    }

    expected = {
        "freMTPL2freq": summary["targets"]["frequency_french"],
        "spanish_motor_freq": summary["targets"]["frequency_spanish"],
        "freMTPL2sev": summary["targets"]["severity_french"],
        "spanish_motor_severity": summary["targets"]["severity_spanish"],
    }
    for dataset, target in expected.items():
        row = by_dataset[dataset]
        assert float(row.estimate.rstrip("%")) == pytest.approx(target["mean"] * 100, abs=0.005)
        assert float(row.ci_low.rstrip("%")) == pytest.approx(target["ci"][0] * 100, abs=0.005)
        assert float(row.ci_high.rstrip("%")) == pytest.approx(target["ci"][1] * 100, abs=0.005)
        assert row.decision == target["decision"]

    row_scale = {row.dataset.strip("`"): row for row in all_rows if row.block == "row-scale"}
    for dataset, key in (("freMTPL2sev", "row_scale"), ("freMTPL2freq", "row_scale_frequency")):
        arm = summary[key]
        assert row_scale[dataset].estimate == f"{arm['mean']:+.2%}"


def test_every_quoted_number_appears_in_its_owner_row(all_rows):
    quoted = [row for row in all_rows if row.source.startswith(("Phase 2", "Ladder"))]
    assert len(quoted) == 6, "the six quoted cells are the lapse and ladder rows"
    for row in quoted:
        owner_row = _owner_row(row)
        for token in _numbers(f"{row.estimate} {row.ci_low} {row.ci_high}"):
            assert token in owner_row, f"{row.dataset}: {token} is not in its owner row"
        assert row.decision.split(" — ")[0] in owner_row, (
            f"{row.dataset}: decision {row.decision!r} is not in its owner row"
        )


LAPSE_FAMILIES = {"pilot2-phase2", "gpu-pilot", "r1-pilot", "pilot2-breadth-spanish"}


def _ledger_entries(ledger: list[dict[str, str]], row) -> list[dict[str, str]]:
    dataset = row.dataset.strip("`")
    families = LAPSE_FAMILIES if row.task == "Lapse" else {"fair-test-freq-sev"}
    return [
        entry
        for entry in ledger
        if entry["dataset"] == dataset and entry["experiment_family"] in families
    ]


def test_design_axes_agree_with_the_ledger(all_rows):
    ledger = _ledger()
    # The Spanish lapse verdict ran at 10,000 rows, but its launch records were never captured:
    # the ledger holds only the earlier pilot cells. Its axes are checked against its own analysis.
    ledger_gaps = {"spanish_motor_lapse"}
    for row in all_rows:
        if row.block != "targets":
            continue
        dataset = row.dataset.strip("`")
        entries = _ledger_entries(ledger, row)
        assert entries, f"{dataset} is not in the runs ledger"

        eligible = int(re.search(r"[\d,]+", row.eligible_rows).group().replace(",", ""))
        assert {int(entry["eligible_rows"]) for entry in entries if entry["eligible_rows"]} == {
            eligible
        }, f"{dataset}: eligible rows disagree with the ledger"

        budget = int(re.search(r"[\d,]+", row.train_rows).group().replace(",", ""))
        ledger_budgets = {int(entry["train_rows"]) for entry in entries if entry["train_rows"]}
        if dataset not in ledger_gaps:
            assert budget == max(ledger_budgets), (
                f"{dataset}: the verdict budget {budget} is not the ledger's largest "
                f"({sorted(ledger_budgets)})"
            )

        match = re.search(r"[(](\d+)[-–](\d+)[)]", row.seeds)
        if match and dataset not in ledger_gaps:
            low, high = (int(value) for value in match.groups())
            ledger_seeds = {int(entry["seed"]) for entry in entries if entry["seed"]}
            assert low in ledger_seeds and high in ledger_seeds, (
                f"{dataset}: verdict seeds {low}-{high} not within ledger seeds"
            )


def test_the_matrix_states_the_registered_arms(all_rows):
    for row in all_rows:
        expected = (
            {0.0, 30.0}
            if row.block in ("targets", "row-scale")
            else {0.0, 3.0, 10.0, 30.0}
        )
        assert {float(part) for part in row.epochs.split(",")} == expected, row.dataset


def test_spanish_lapse_row_matches_its_owner(all_rows):
    row = next(entry for entry in all_rows if entry.dataset == "`spanish_motor_lapse`")
    owner = SPANISH.read_text(encoding="utf-8")
    assert "341–356" in owner
    assert "16 fresh seeds" in owner
    assert "10,000 train / 10,000 test" in owner
    assert "30-epoch" in owner
    assert row.seeds == "16 (341–356)"
    assert row.train_rows == "10,000 / 10,000"


def test_the_ladder_is_outside_the_ledger(all_rows):
    ladder_ids = {"20261121T153848Z", "20261121T232424Z"}
    assert {row.block for row in all_rows} == {"targets", "ladder", "row-scale"}
    assert not ladder_ids & {entry["run_id"] for entry in _ledger()}
    ledger_doc = LEDGER_DOC.read_text(encoding="utf-8")
    assert "Not exhaustive" in ledger_doc
    assert "the #572 row-scaling runs" in ledger_doc
    assert "the two severity ladder captures" in ledger_doc
    assert ladder_ids <= {run_id for run_id in re.findall(r"20\d{6}T\d{6}Z", ledger_doc)}


def test_coil2000_is_not_a_lapse_target(matrix, all_rows):
    datasets = {row.dataset for row in all_rows}
    assert "`coil2000`" not in datasets
    assert "coil2000` — stopped, not run" in PHASE2.read_text(encoding="utf-8")


def test_the_csv_carries_the_same_rows(all_rows):
    with CSV.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == len(all_rows)
    assert {row["block"] for row in rows} == {"targets", "ladder", "row-scale"}
    assert all(row["model_version"] == "v3_default" for row in rows)
