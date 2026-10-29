"""The record contract: a pilot arm record's `provenance` block, and the verdict it earns.

The seam is the record on disk, because that is the surface a reviewer reads a number
against. Nothing here reaches into a writer's internals or restates a private key list;
the assertions are on the JSON the pilot wrote and on the verdict the shared reader
computes from it.

What this covers, one acceptance criterion each (issue #241):

* a mock pilot run writes an arm record declaring schema 3, with all four provenance
  sections and a non-null model version;
* that record reads `comparable` with no missing keys;
* a record with its model version removed reads `partial`, naming exactly that key;
* a record with no block reads `unusable`, not an exception;
* a record declaring a higher schema version raises;
* the fingerprint helper takes a frame plus target and drop columns, with no dataset
  registry in play;
* `analyse_pilot.py` reads a schema-3 record unchanged;
* every committed record is classified, none rewritten.

Run:  python -m pytest tests/test_record_contract.py -v
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from provenance import (  # noqa: E402
    ARM_RECORD_SCHEMA_VERSION,
    DataSource,
    dataset_fingerprint,
    read_record,
    verdict,
)

PILOT_RECORD = REPO_ROOT / "outputs" / "gpu-pilot"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def rp():
    return _load("run_pilot", REPO_ROOT / "scripts" / "run_pilot.py")


@pytest.fixture(scope="module")
def ap():
    return _load("analyse_pilot", REPO_ROOT / "scripts" / "analyse_pilot.py")


# --------------------------------------------------------------------------
# A mock pilot run, through the runner's own write path
# --------------------------------------------------------------------------
def _toy_csv(tmp_path: Path) -> Path:
    rng = np.random.default_rng(3)
    rows = ["y,a,b"]
    for _ in range(60):
        y = int(rng.random() > 0.5)
        rows.append(f"{y},{rng.random():.6f},{int(rng.integers(0, 3))}")
    path = tmp_path / "toy.csv"
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path


def _source() -> DataSource:
    return DataSource(
        url="https://example.invalid/data/raw/toy.csv",
        repo="IFoA-ADSWP/tabular-foundation-model",
        ref="main",
        ref_is_pinned=False,
    )


def _metrics() -> dict:
    return {"log_loss": 0.5, "roc_auc": 0.7, "ece": 0.01, "brier": 0.1, "pr_auc": 0.2}


@pytest.fixture
def mock_arm_run(rp, tmp_path):
    """One mock arm run: a frame, its fingerprint, a real split, and the writer.

    The model fit is stubbed to a probability array. Everything downstream of it -- the
    split, the fingerprint, the record -- is the runner's own code, so the record under
    test is the record a paid run would leave.
    """
    import pandas as pd

    csv = _toy_csv(tmp_path)
    frame = pd.read_csv(csv)
    fingerprint = dataset_fingerprint(
        "toy",
        frame=frame,
        target="y",
        drop=(),
        path=csv,
        repo_root=tmp_path,
        source=_source(),
    )
    X = frame[["a", "b"]].to_numpy(dtype=float)
    y = frame["y"].to_numpy().astype(int)
    *_, split_fp = rp.make_split(
        X, y, seed=42, train_size=None, test_size=None, fold=None, n_folds=None
    )
    probs = np.linspace(0.01, 0.99, split_fp["n_test"])
    truth = y[: split_fp["n_test"]]
    rp.save_results(
        "toy",
        "B_ft3",
        _metrics(),
        probs,
        truth,
        0.12,
        dict(rp.DEFAULT_CONFIG),
        tmp_path / "pilot",
        seed=42,
        fold=None,
        n_folds=None,
        split_fp=split_fp,
        dataset_fp=fingerprint,
        arm_fp=rp.effective_config("B_ft3", dict(rp.DEFAULT_CONFIG)),
        context_rows=None,
        context_note="n/a",
    )
    return tmp_path / "pilot" / "toy" / "B_ft3" / "meta.json"


def _record(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# The writer: schema 3, four sections, a model version
# --------------------------------------------------------------------------
def test_a_pilot_arm_record_declares_schema_three(mock_arm_run):
    record = _record(mock_arm_run)

    assert record["schema_version"] == ARM_RECORD_SCHEMA_VERSION == 3
    assert set(record["provenance"]) == {"dataset", "split", "model", "code"}


def test_the_block_names_its_dataset_split_model_and_code(mock_arm_run):
    record = _record(mock_arm_run)
    block = record["provenance"]

    assert block["dataset"]["name"] == "toy"
    assert block["dataset"]["target"] == "y"
    assert block["dataset"]["sha256"] == hashlib.sha256(
        (mock_arm_run.parents[3] / "toy.csv").read_bytes()
    ).hexdigest()
    assert (block["dataset"]["n_rows"], block["dataset"]["n_cols"]) == (60, 3)

    assert block["split"]["seed"] == 42
    # The fold construction is a RULE, not a sentence: a reader can compare two records'
    # rules and see a fold change as a rule change rather than as a metric change.
    assert block["split"]["rule"] == {
        "constructor": "train_test_split",
        "params": {"random_state": 42, "stratify": "y", "test_size": 18, "train_size": None},
    }
    assert block["split"]["sha256"] == record["split_fingerprint"]["train_index_sha256"]

    assert block["model"]["version"], "no pilot record has ever carried a model version"
    assert block["model"]["client_version"]

    assert len(block["code"]["git_sha"]) == 40
    assert isinstance(block["code"]["dirty"], bool)
    assert block["code"]["runtime"]["python"]


def test_the_block_is_the_same_object_the_legacy_keys_hold(mock_arm_run):
    """One fingerprint, not two that could disagree -- the transition must not drift."""
    record = _record(mock_arm_run)

    assert record["provenance"]["dataset"] == record["dataset_fingerprint"]
    assert record["provenance"]["split"]["sha256"] == (
        record["split_fingerprint"]["train_index_sha256"]
    )


# --------------------------------------------------------------------------
# The reader: verdicts, and what they name
# --------------------------------------------------------------------------
def _complete(**over) -> dict:
    record = {
        "schema_version": ARM_RECORD_SCHEMA_VERSION,
        "provenance": {
            "dataset": {
                "name": "coil2000",
                "file": "coil2000.csv",
                "target": "CARAVAN",
                "drop": [],
                "sha256": "a" * 64,
                "n_rows": 5822,
                "n_cols": 86,
            },
            "split": {
                "n_folds": 5,
                "seed": 42,
                "sha256": "b" * 64,
                "rule": {"constructor": "StratifiedKFold", "params": {"n_splits": 5}},
            },
            "model": {
                "version": "v3_default",
                "weights_sha256": "c" * 64,
                "client_version": "2.6.0",
            },
            "code": {
                "git_sha": "d" * 40,
                "dirty": False,
                "runtime": {"python": "3.12.0"},
                "image": None,
            },
        },
    }
    record.update(over)
    return record


def test_a_complete_record_reads_comparable(mock_arm_run):
    result = verdict(mock_arm_run)

    assert result.status == "comparable"
    assert result.missing == ()
    assert result.schema_version == ARM_RECORD_SCHEMA_VERSION


def test_the_written_record_without_its_model_version_is_partial(mock_arm_run, tmp_path):
    """The acceptance criterion, on the artifact rather than on a hand-built dict."""
    record = _record(mock_arm_run)
    record["provenance"]["model"]["version"] = None
    stripped = tmp_path / "stripped" / "meta.json"
    stripped.parent.mkdir()
    stripped.write_text(json.dumps(record), encoding="utf-8")

    result = verdict(stripped)

    assert result.status == "partial"
    assert result.missing == ("provenance.model.version",)


@pytest.mark.parametrize(
    ("drop_key", "missing_key"),
    [
        (("model", "version"), "provenance.model.version"),
        (("code", "git_sha"), "provenance.code.git_sha"),
        (("split", "sha256"), "provenance.split.sha256"),
    ],
)
def test_one_missing_identity_item_is_partial_and_named(drop_key, missing_key):
    """The verdict says WHAT is missing, so 'non-comparable' is actionable."""
    record = _complete()
    record["provenance"][drop_key[0]][drop_key[1]] = None

    result = verdict(record)

    assert result.status == "partial"
    assert result.missing == (missing_key,)


def test_a_dataset_without_a_content_hash_is_partial_and_named():
    record = _complete()
    record["provenance"]["dataset"]["sha256"] = None

    result = verdict(record)

    assert result.status == "partial"
    assert result.missing == ("provenance.dataset[coil2000].sha256",)


def test_a_run_level_record_names_the_dataset_that_is_missing_its_hash():
    """A run manifest covers N datasets; the verdict must point at the one at fault."""
    record = _complete()
    second = dict(record["provenance"]["dataset"], name="uslapseagent", sha256=None)
    record["provenance"]["dataset"] = [record["provenance"]["dataset"], second]

    result = verdict(record)

    assert result.status == "partial"
    assert result.missing == ("provenance.dataset[uslapseagent].sha256",)


def test_a_complete_run_level_record_reads_comparable():
    record = _complete()
    second = dict(record["provenance"]["dataset"], name="uslapseagent")
    record["provenance"]["dataset"] = [record["provenance"]["dataset"], second]

    assert verdict(record).status == "comparable"


@pytest.mark.parametrize(
    ("section", "key", "missing_key"),
    [
        ("split", "seed", "provenance.split.seed"),
        ("split", "verify", "provenance.split.n_folds"),
    ],
)
def test_record_without_a_split_identity_is_unusable(section, key, missing_key):
    record = _complete()
    if key == "verify":
        # No fold count and no construction: the record does not say what the split was.
        record["provenance"][section]["n_folds"] = None
        record["provenance"][section]["rule"] = None
    else:
        record["provenance"][section][key] = None

    result = verdict(record)

    assert result.status == "unusable"
    assert result.missing == (missing_key,)


def test_record_whose_dataset_cannot_be_identified_is_unusable():
    record = _complete()
    record["provenance"]["dataset"]["name"] = None

    result = verdict(record)

    assert result.status == "unusable"
    assert result.missing == ("provenance.dataset[0].name",)


def test_record_with_no_dataset_at_all_is_unusable():
    record = _complete()
    record["provenance"]["dataset"] = []

    result = verdict(record)

    assert result.status == "unusable"
    assert result.missing == ("provenance.dataset",)


def test_record_with_no_provenance_block_is_unusable_not_an_exception():
    record = {"schema_version": 2, "run_id": "coil2000_A_raw_seed42", "roc_auc": 0.7}

    result = verdict(record)

    assert result.status == "unusable"
    assert result.missing == ("provenance",)


# --------------------------------------------------------------------------
# Version dispatch: fail closed, and never upgrade a legacy record
# --------------------------------------------------------------------------
@pytest.mark.parametrize("declared", [4, 99, 0, "3"])
def test_a_schema_version_this_reader_does_not_know_raises(declared):
    record = _complete(schema_version=declared)

    with pytest.raises(ValueError, match="schema_version"):
        verdict(record)


def test_reading_a_file_with_an_unknown_schema_version_raises(tmp_path):
    path = tmp_path / "meta.json"
    path.write_text(json.dumps(_complete(schema_version=99)), encoding="utf-8")

    with pytest.raises(ValueError, match="schema_version"):
        read_record(path)


def test_a_committed_v2_record_reads_unusable_and_is_not_rewritten():
    """Read, never upgraded.

    A v2 pilot record carries fingerprints at the top level but no `provenance` block, so the
    block contract cannot read it -- and it is not the reader's job to reinterpret an old file
    into the new shape. It gets a stated verdict, and its bytes stay the evidence.
    """
    path = PILOT_RECORD / "uslapseagent" / "A_raw" / "meta.json"
    if not path.exists():
        pytest.skip("the committed v2 pilot record is not present in this checkout")
    before = path.read_bytes()

    result = verdict(path)

    assert result.status == "unusable"
    assert result.missing == ("provenance",)
    assert result.schema_version == 2
    assert path.read_bytes() == before


def test_no_committed_record_is_left_unclassified():
    """Legacy records get a verdict -- including the unversioned ones -- never a raise."""
    records = sorted(PILOT_RECORD.glob("**/meta.json"))
    records += sorted((REPO_ROOT / "results").glob("*/manifest.json"))
    if not records:
        pytest.skip("no committed records in this checkout")

    statuses = {path: verdict(path).status for path in records}
    assert set(statuses.values()) <= {"comparable", "partial", "unusable"}


# --------------------------------------------------------------------------
# The fingerprint helper a second runner can call
# --------------------------------------------------------------------------
def test_fingerprint_takes_a_frame_a_target_and_drop_columns(tmp_path):
    import pandas as pd

    path = tmp_path / "toy.csv"
    path.write_text("y,a,leaky\n0,1,9\n1,2,9\n0,3,9\n", encoding="utf-8")

    fp = dataset_fingerprint(
        "toy",
        frame=pd.read_csv(path),
        target="y",
        drop=("leaky",),
        path=path,
        repo_root=tmp_path,
        source=_source(),
    )

    assert fp["drop"] == ["leaky"]
    assert fp["target"] == "y"
    assert fp["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert (fp["n_rows"], fp["n_cols"]) == (3, 3)


def test_fingerprint_of_a_frame_with_no_file_says_it_cannot_hash(tmp_path):
    """No bytes on disk means no content hash -- the absence is stated, not faked."""
    import pandas as pd

    fp = dataset_fingerprint(
        "in_memory",
        frame=pd.DataFrame({"y": [0, 1], "a": [1.0, 2.0]}),
        target="y",
        path=None,
        repo_root=tmp_path,
        source=_source(),
    )

    assert fp["sha256"] is None
    assert fp["n_rows"] == 2


def test_the_pilot_adapter_states_a_missing_table(rp, tmp_path, monkeypatch):
    """The pilot's binding keeps the one state the shared helper no longer has: no file."""
    monkeypatch.setitem(rp.DATASETS, "toy", {"file": "toy.csv", "target": "y"})
    monkeypatch.setattr(rp, "DATA_DIR", tmp_path)

    assert rp.dataset_fingerprint("toy") == {
        "name": "toy",
        "path": str(tmp_path / "toy.csv"),
        "exists": False,
    }


# --------------------------------------------------------------------------
# Consumers: the analysis script keeps reading the records
# --------------------------------------------------------------------------
def test_analyse_pilot_reads_a_schema_three_record(ap, mock_arm_run):
    found = ap.discover(mock_arm_run.parents[1].parent)

    assert list(found) == ["toy"]
    assert list(found["toy"]) == ["B_ft3"]
    record = found["toy"]["B_ft3"][(42, None)]
    assert record["status"] == "success"
    assert record["epochs"] == 3
    assert record["probs"].shape == record["y_true"].shape
