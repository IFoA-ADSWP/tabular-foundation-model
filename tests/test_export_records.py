"""`scripts/diagnostics/export_records.py`: a record becomes a table a reviewer can open (#407).

Seam under test: the CSV bytes on disk. Every expectation is read from the record JSON and the
raw manifest, never from the exporter's own helpers -- otherwise a wrong exporter and a matching
wrong test would agree with each other.

The committed table is the subject, not a copy of it: `docs/analyses/data/d2_importance.csv` must
equal a fresh export of the committed fixtures, byte for byte. That is what makes the table
reproducible from the tree rather than a claim about a git-ignored directory.

Run:  python -m pytest tests/test_export_records.py -v
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from anchor_datasets import load_anchor_datasets  # noqa: E402  (importable after the src path insert above)

SCRIPT = REPO_ROOT / "scripts" / "diagnostics" / "export_records.py"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "diagnostics" / "d2_importance"
COMMITTED = REPO_ROOT / "docs" / "analyses" / "data" / "d2_importance.csv"
D1_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "diagnostics" / "d1_profiling"
D1_COMMITTED = REPO_ROOT / "docs" / "analyses" / "data" / "d1_profiling.csv"
REPRO_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "diagnostics" / "d1_profiling-repro"
MANIFEST = REPO_ROOT / "data" / "raw" / "MANIFEST.sha256"

D2_COLUMNS = [
    "run_id",
    "dataset",
    "family",
    "rank",
    "feature",
    "importance",
    "std",
    "univariate_auc",
    "test_auc",
    "no_better_than_chance",
    "model_version_requested",
    "model_resolved_version",
    "dataset_sha256",
    "record_sha",
]

TOP_K = 10
INTERACTION_MARGINAL_AUC = 0.02


def _cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


def _export(run: Path, out_dir: Path, *extra: str) -> subprocess.CompletedProcess:
    return _cli("--run", str(run), "--out-dir", str(out_dir), *extra)


def _rows(path: Path) -> list[dict]:
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def _manifest(path: Path = MANIFEST) -> dict[str, str]:
    entries = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        sha, _, name = line.partition("  ")
        entries[name.strip().lstrip("./")] = sha
    return entries


def _record_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _record(run_id: str) -> dict:
    return json.loads((FIXTURES / run_id / "record.json").read_text())


@pytest.fixture(scope="module")
def d1():
    """The real D1 diagnostic, so the exporter's required keys are checked against its output."""
    spec = importlib.util.spec_from_file_location(
        "_d1_for_export", REPO_ROOT / "scripts" / "diagnostics" / "d1_profiling.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["_d1_for_export"] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# The committed table
# ---------------------------------------------------------------------------
def test_committed_d2_table_is_a_fresh_export_of_the_fixtures(tmp_path):
    out = tmp_path / "data"
    result = _export(FIXTURES, out)
    assert result.returncode == 0, result.stderr
    assert (out / "d2_importance.csv").read_bytes() == COMMITTED.read_bytes()


def test_export_is_idempotent_and_order_independent(tmp_path):
    forward = tmp_path / "forward"
    reverse = tmp_path / "reverse"
    assert _export(FIXTURES, forward).returncode == 0
    dirs = sorted(p for p in FIXTURES.iterdir() if p.is_dir())
    args = [str(p) for p in reversed(dirs)]
    result = _cli(*sum((["--run", p] for p in args), []), "--out-dir", str(reverse))
    assert result.returncode == 0, result.stderr
    assert (forward / "d2_importance.csv").read_bytes() == (reverse / "d2_importance.csv").read_bytes()


def test_table_header_and_every_row_is_anchored():
    rows = _rows(COMMITTED)
    assert list(rows[0]) == D2_COLUMNS
    manifest = _manifest()
    for row in rows:
        # The checkable anchor: the record's dataset hash is the manifest's entry for that CSV.
        assert row["dataset_sha256"] == manifest[f"{row['dataset']}.csv"], row["dataset"]
        # And the record itself, committed beside the test, is the file the row came from.
        assert row["record_sha"] == _record_sha(FIXTURES / row["run_id"] / "record.json")


def test_one_row_per_dataset_family_feature():
    rows = _rows(COMMITTED)
    record = _record("20261104T1725Z-coil2000")
    expected = sum(len(family["ranking"]) for family in record["measurements"]["families"].values())
    coil = [row for row in rows if row["dataset"] == "coil2000"]
    assert len(coil) == expected
    assert {row["dataset"] for row in rows} == {
        "coil2000",
        "eudirectlapse",
        "spanish_motor_lapse",
        "uslapseagent",
    }


# ---------------------------------------------------------------------------
# A reviewer reads the top ten and the three readings from the CSV alone
# ---------------------------------------------------------------------------
def _ranks(rows: list[dict], dataset: str) -> dict[str, dict[str, int]]:
    """family -> feature -> rank, read from the table and nothing else."""
    ranks: dict[str, dict[str, int]] = {}
    for row in rows:
        if row["dataset"] != dataset:
            continue
        ranks.setdefault(row["family"], {})[row["feature"]] = int(row["rank"])
    return ranks


def _top(ranks: dict[str, int], k: int = TOP_K) -> list[str]:
    return [feature for feature, rank in sorted(ranks.items(), key=lambda kv: kv[1]) if rank <= k]


def _univariate(rows: list[dict], dataset: str) -> dict[str, float]:
    return {
        row["feature"]: float(row["univariate_auc"])
        for row in rows
        if row["dataset"] == dataset and row["univariate_auc"]
    }


def test_top_ten_matches_the_record():
    rows = _rows(COMMITTED)
    for run_id in ("20261104T1725Z-coil2000", "20261104T1725Z-uslapseagent"):
        record = _record(run_id)
        ranks = _ranks(rows, record["dataset_name"])
        for family, block in record["measurements"]["families"].items():
            assert _top(ranks[family]) == block["top_k"][:TOP_K]


def test_three_readings_are_recomputable_from_the_table_alone():
    """Spearman, top-k Jaccard and the tree-only screen, from the CSV columns only."""
    for run_id in ("20261104T1725Z-coil2000", "20261104T1725Z-eudirectlapse"):
        record = _record(run_id)
        dataset = record["dataset_name"]
        rows = _rows(COMMITTED)
        ranks = _ranks(rows, dataset)
        univariate = _univariate(rows, dataset)

        same = {(row["a"], row["b"]): row for row in record["measurements"]["readings"]["same_features_ranked_differently"]}
        different = {(row["a"], row["b"]): row for row in record["measurements"]["readings"]["different_features"]}

        for (a, b), block in same.items():
            shared = sorted(set(ranks[a]) & set(ranks[b]))
            spearman = pd.Series([ranks[a][f] for f in shared]).corr(
                pd.Series([ranks[b][f] for f in shared]), method="pearson"
            )
            assert round(float(spearman), 6) == block["spearman_all_features"]

            top_a, top_b = set(_top(ranks[a])), set(_top(ranks[b]))
            union = top_a | top_b
            assert round(len(top_a & top_b) / len(union), 6) == different[(a, b)]["jaccard_top_k"]

        seen_by_others = set(_top(ranks["tabpfn"])) | set(_top(ranks["glm"]))
        candidates = [
            feature
            for feature in _top(ranks["lgbm"])
            if feature not in seen_by_others
            and abs(univariate[feature] - 0.5) < INTERACTION_MARGINAL_AUC
        ]
        assert candidates == record["measurements"]["readings"]["interaction_only"]["candidates"]


# ---------------------------------------------------------------------------
# Refusals
# ---------------------------------------------------------------------------
def _tampered_fixture(tmp_path: Path, run_id: str = "20261104T1725Z-uslapseagent") -> Path:
    root = tmp_path / "fixtures"
    run = root / run_id
    shutil.copytree(FIXTURES / run_id, run)
    record = json.loads((run / "record.json").read_text())
    record["dataset_sha256"] = "0" * 64
    (run / "record.json").write_text(json.dumps(record, indent=2) + "\n")
    return root


def test_a_record_whose_dataset_bytes_moved_is_refused(tmp_path):
    root = _tampered_fixture(tmp_path)
    out = tmp_path / "data"
    result = _export(root, out)
    assert result.returncode != 0
    assert "0" * 64 in result.stderr
    assert _manifest()["uslapseagent.csv"] in result.stderr
    assert not (out / "d2_importance.csv").exists()


def test_an_unsupported_diagnostic_is_refused_by_name(tmp_path):
    run = tmp_path / "d3_reframe" / "20261104T1725Z-uslapseagent"
    run.mkdir(parents=True)
    record = _record("20261104T1725Z-uslapseagent")
    record["diagnostic"] = "d3_reframe"
    (run / "record.json").write_text(json.dumps(record, indent=2) + "\n")
    result = _export(run, tmp_path / "data")
    assert result.returncode != 0
    assert "d3_reframe" in result.stderr
    assert "d2_importance" in result.stderr


def test_a_record_missing_a_measurement_is_refused_naming_the_key(tmp_path):
    run = tmp_path / "d2_importance" / "20261104T1725Z-uslapseagent"
    run.mkdir(parents=True)
    record = _record("20261104T1725Z-uslapseagent")
    del record["measurements"]["families"]
    (run / "record.json").write_text(json.dumps(record, indent=2) + "\n")
    result = _export(run, tmp_path / "data")
    assert result.returncode != 0
    assert "families" in result.stderr


def test_a_dataset_outside_the_manifest_is_refused(tmp_path):
    run = tmp_path / "d2_importance" / "20261104T1725Z-made_up"
    run.mkdir(parents=True)
    record = _record("20261104T1725Z-uslapseagent")
    record["run_id"] = "20261104T1725Z-made_up"
    record["dataset_name"] = "made_up_dataset"
    (run / "record.json").write_text(json.dumps(record, indent=2) + "\n")
    result = _export(run, tmp_path / "data")
    assert result.returncode != 0
    assert "made_up_dataset" in result.stderr


def test_two_records_for_one_run_and_dataset_are_refused(tmp_path):
    root = tmp_path / "fixtures"
    shutil.copytree(FIXTURES, root)
    duplicate = root / "copy-of-uslapseagent"
    shutil.copytree(FIXTURES / "20261104T1725Z-uslapseagent", duplicate)
    result = _export(root, tmp_path / "data")
    assert result.returncode != 0
    assert "uslapseagent" in result.stderr


def test_two_runs_of_one_dataset_are_refused(tmp_path):
    """A second run would put two `rank = 1` rows in one family, and a top ten would stop being one."""
    root = tmp_path / "fixtures"
    shutil.copytree(FIXTURES, root)
    second = root / "later-run-uslapseagent"
    shutil.copytree(FIXTURES / "20261104T1725Z-uslapseagent", second)
    record = json.loads((second / "record.json").read_text())
    record["run_id"] = "20261107T090000Z-uslapseagent"
    (second / "record.json").write_text(json.dumps(record, indent=2) + "\n")

    out = tmp_path / "data"
    result = _export(root, out)
    assert result.returncode != 0
    assert "20261104T1725Z-uslapseagent" in result.stderr
    assert "20261107T090000Z-uslapseagent" in result.stderr
    assert not (out / "d2_importance.csv").exists()


def test_every_row_names_the_model_it_was_measured_with():
    """Keyed by run_id: a single record's version stamped on every row would pass a global check."""
    rows = _rows(COMMITTED)
    by_run = {row["run_id"]: row for row in rows}
    assert set(by_run) == {f"20261104T1725Z-{name}" for name in (
        "coil2000",
        "eudirectlapse",
        "spanish_motor_lapse",
        "uslapseagent",
    )}
    for run_id, row in by_run.items():
        record = _record(run_id)
        # The record asked for `auto` and the library resolved a concrete era (#285).
        assert row["model_version_requested"] == record["model_version"] == "auto"
        assert row["model_resolved_version"] == record["measurements"]["tabpfn"]["resolved_version"]
        assert row["model_resolved_version"]


def test_a_record_with_no_provenance_block_is_refused(tmp_path):
    run = tmp_path / "d2_importance" / "20261104T1725Z-uslapseagent"
    run.mkdir(parents=True)
    record = _record("20261104T1725Z-uslapseagent")
    del record["measurements"]["tabpfn"]
    (run / "record.json").write_text(json.dumps(record, indent=2) + "\n")
    result = _export(run, tmp_path / "data")
    assert result.returncode != 0
    assert "tabpfn" in result.stderr


def test_no_better_than_chance_flags_the_families_whose_ranking_is_noise():
    """The column has to be usable: it must agree with the test AUC it summarises."""
    rows = _rows(COMMITTED)
    for row in rows:
        flagged = row["no_better_than_chance"] == "true"
        assert flagged == (float(row["test_auc"]) < 0.52), row["dataset"]


# ---------------------------------------------------------------------------
# D1: one row per dataset, the nested blocks kept machine-readable
# ---------------------------------------------------------------------------
def test_committed_d1_table_is_a_fresh_export_of_the_fixtures(tmp_path):
    out = tmp_path / "data"
    result = _export(D1_FIXTURES, out)
    assert result.returncode == 0, result.stderr
    assert (out / "d1_profiling.csv").read_bytes() == D1_COMMITTED.read_bytes()


def test_every_d1_row_is_anchored_and_one_per_dataset():
    rows = _rows(D1_COMMITTED)
    assert {row["dataset"] for row in rows} == {
        "coil2000",
        "eudirectlapse",
        "spanish_motor_lapse",
        "uslapseagent",
    }
    manifest = _manifest()
    for row in rows:
        assert row["dataset_sha256"] == manifest[f"{row['dataset']}.csv"]
        assert row["record_sha"] == _record_sha(D1_FIXTURES / row["run_id"] / "record.json")
        # The nested blocks are JSON a reader can parse, not a flattened string.
        assert json.loads(row["target"])["kind"] == "binary"
        assert json.loads(row["missing_by_column"]) == {}
        # The counts hold together, so a reader can trust the widths without the record.
        assert int(row["n_features"]) + 1 == int(row["n_cols"])
        assert int(row["n_numeric_features"]) + int(row["n_categorical_features"]) == int(
            row["n_features"]
        )


def test_d1_agrees_with_a_recomputation_from_the_raw_csv():
    """#302's wrongness check: the record must match the file it names, not only hash it."""
    rows = {row["dataset"]: row for row in _rows(D1_COMMITTED)}
    for dataset, row in rows.items():
        frame = pd.read_csv(REPO_ROOT / "data" / "raw" / f"{dataset}.csv")
        target = json.loads(row["target"])

        assert int(row["n_rows"]) == len(frame)
        assert int(row["n_cols"]) == frame.shape[1]
        assert int(row["n_cols_with_missing"]) == int(frame.isna().any().sum())
        assert float(row["missing_rate"]) == round(float(frame.isna().to_numpy().mean()), 6)
        # The target is named per dataset in the registry, so recompute against that column.
        column = load_anchor_datasets()[dataset]["target"]
        values = frame[column].dropna()
        assert int(target["n_positive"]) == int((values.astype(float) == 1).sum())
        assert float(target["positive_rate"]) == round(float(values.astype(float).mean()), 6)


def test_a_second_run_reproduces_every_measurement():
    """#302: "a second run with the same inputs produces the same values" — checked, not asserted."""
    first = json.loads((D1_FIXTURES / "20261107T112100Z-eudirectlapse" / "record.json").read_text())
    second = json.loads(
        (REPRO_FIXTURE / "20261106T-d5-cites-d1-eudirectlapse" / "record.json").read_text()
    )
    assert first["measurements"] == second["measurements"]
    assert first["dataset_sha256"] == second["dataset_sha256"]
    # Different files, so the hashes differ: `record_sha` names the record, not the measurement.
    assert _record_sha(D1_FIXTURES / "20261107T112100Z-eudirectlapse" / "record.json") != _record_sha(
        REPRO_FIXTURE / "20261106T-d5-cites-d1-eudirectlapse" / "record.json"
    )
    assert first["created_utc"] != second["created_utc"]


def _d1_record(d1, tmp_path: Path, name: str = "uslapseagent") -> tuple[Path, dict]:
    frame = pd.DataFrame(
        {
            "a": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "b": ["x", "y", "x", "y", "x", None],
            "target": [0, 1, 0, 1, 1, 0],
        }
    )
    measurements = d1.profile_frame(frame, "target")
    dataset_sha = hashlib.sha256(b"synthetic frame").hexdigest()
    record = {
        "schema_version": 1,
        "diagnostic": "d1_profiling",
        "run_id": f"20261107T000000Z-{name}",
        "git_sha": None,
        "git_dirty": False,
        "model_version": "auto",
        "seed": None,
        "dataset_name": name,
        "dataset_sha256": dataset_sha,
        "matched_context": {"checked": False, "baseline_arm": "A_raw", "arms": {}},
        "runtime": None,
        "measurements": measurements,
    }
    directory = tmp_path / "fixtures" / "d1_profiling" / record["run_id"]
    directory.mkdir(parents=True)
    (directory / "record.json").write_text(json.dumps(record, indent=2) + "\n")
    manifest = tmp_path / "MANIFEST.sha256"
    manifest.write_text(f"{dataset_sha}  ./{name}.csv\n")
    return tmp_path / "fixtures" / "d1_profiling", manifest


def test_d1_writes_one_row_per_dataset_and_keeps_the_nested_blocks(d1, tmp_path):
    root, manifest = _d1_record(d1, tmp_path)
    out = tmp_path / "data"
    result = _export(root, out, "--manifest", str(manifest))
    assert result.returncode == 0, result.stderr

    rows = _rows(out / "d1_profiling.csv")
    assert len(rows) == 1
    row = rows[0]
    assert row["dataset"] == "uslapseagent"
    assert int(row["n_rows"]) == 6
    assert float(row["missing_rate"]) > 0
    # The per-column rates and the target shape survive as JSON rather than being dropped.
    assert json.loads(row["missing_by_column"]) == d1.profile_frame(
        pd.DataFrame(
            {
                "a": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
                "b": ["x", "y", "x", "y", "x", None],
                "target": [0, 1, 0, 1, 1, 0],
            }
        ),
        "target",
    )["missing_by_column"]
    assert json.loads(row["target"])["kind"] == "binary"


def test_d1_refuses_a_record_that_predates_a_profile_column(d1, tmp_path):
    root, manifest = _d1_record(d1, tmp_path)
    record_path = next(root.glob("*/record.json"))
    record = json.loads(record_path.read_text())
    del record["measurements"]["max_vif"]
    record_path.write_text(json.dumps(record, indent=2) + "\n")
    result = _export(root, tmp_path / "data", "--manifest", str(manifest))
    assert result.returncode != 0
    assert "max_vif" in result.stderr
