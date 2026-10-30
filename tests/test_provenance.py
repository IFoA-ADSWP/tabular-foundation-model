"""`src/provenance.py`: the shared record writer, read back from disk.

The seams here are the ones a caller uses: `write_diagnostic_record` writing a record a reviewer
can read, `read_diagnostic_record` reading it back fail-closed, `dataset_fingerprint`
fingerprinting a table, and `matched_context_evidence` carrying the assertion's own numbers.

Nothing here recomputes the writer's field list or re-asserts a re-export: a test that recomputes
the code only proves the code agrees with itself.

Run:  python -m pytest tests/test_provenance.py -v
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from provenance import (  # noqa: E402  (importable after the src path insert above)
    DIAGNOSTIC_RECORD_FIELDS,
    DIAGNOSTIC_RECORD_SCHEMA_VERSION,
    DataSource,
    DiagnosticRecord,
    dataset_fingerprint,
    matched_context_evidence,
    read_diagnostic_record,
    write_diagnostic_record,
)


def record(diagnostic="d1_profiling", run_id="20261029T120000Z", **overrides):
    """One record, built the way a diagnostic builds it: values, never key names."""
    values = {
        "diagnostic": diagnostic,
        "run_id": run_id,
        "dataset_name": "coil2000",
        "dataset_sha256": "a" * 64,
        "model_version": "v3_default",
        "seed": None,
        "matched_context": matched_context_evidence(),
        "measurements": {"n_rows": 10, "positive_rate": 0.5},
    }
    values.update(overrides)
    return DiagnosticRecord(**values)


# --------------------------------------------------------------------------
# A record on disk
# --------------------------------------------------------------------------
def test_a_record_lands_under_its_diagnostic_and_run_id(tmp_path):
    written = write_diagnostic_record(record(), root=tmp_path)

    assert written == tmp_path / "d1_profiling" / "20261029T120000Z"
    on_disk = read_diagnostic_record(written)

    assert list(on_disk) == list(DIAGNOSTIC_RECORD_FIELDS)
    assert on_disk["schema_version"] == DIAGNOSTIC_RECORD_SCHEMA_VERSION
    assert on_disk["dataset_name"] == "coil2000"
    assert on_disk["measurements"] == {"n_rows": 10, "positive_rate": 0.5}
    assert on_disk["created_utc"], "the writer stamps the timestamp, not the diagnostic"
    assert on_disk["runtime"]["python"], "the writer stamps the stack that produced it"

    header = (written / "record.csv").read_text(encoding="utf-8").splitlines()[0]
    assert header == ",".join(DIAGNOSTIC_RECORD_FIELDS)


def test_two_diagnostics_write_the_same_keys(tmp_path):
    """The #211 criterion, with only D1 in the tree: one writer, one field order.

    Keys and header only -- comparing values across two writes would compare two runs' clocks,
    which is not the property this test is about.
    """
    one = write_diagnostic_record(record("d1_profiling"), root=tmp_path)
    two = write_diagnostic_record(record("d2_feature_importance"), root=tmp_path)

    headers = [(d / "record.csv").read_bytes().splitlines()[0] for d in (one, two)]
    assert headers[0] == headers[1]
    assert headers[0].decode("utf-8") == ",".join(DIAGNOSTIC_RECORD_FIELDS)

    key_orders = [list(json.loads((d / "record.json").read_text(encoding="utf-8"))) for d in (one, two)]
    assert key_orders[0] == key_orders[1]


# --------------------------------------------------------------------------
# The record cannot be replaced, and cannot leave its tree
# --------------------------------------------------------------------------
def test_an_existing_record_is_refused_and_left_untouched(tmp_path):
    """An old record must not end up claiming it was produced now."""
    written = write_diagnostic_record(record(), root=tmp_path)
    before = (written / "record.json").read_bytes(), (written / "record.csv").read_bytes()

    with pytest.raises(FileExistsError, match="REFUSING TO OVERWRITE"):
        write_diagnostic_record(record(measurements={"n_rows": 11}), root=tmp_path)

    after = (written / "record.json").read_bytes(), (written / "record.csv").read_bytes()
    assert after == before, "a refused write must not touch the record it refused"


def test_a_run_id_cannot_escape_the_record_tree(tmp_path):
    """The split-record failure: the path is derived, so it cannot point somewhere else."""
    with pytest.raises(ValueError):
        write_diagnostic_record(record(run_id="../../elsewhere"), root=tmp_path)
    with pytest.raises(ValueError):
        write_diagnostic_record(record(diagnostic="/tmp/elsewhere"), root=tmp_path)


def test_reader_refuses_a_schema_version_it_does_not_know(tmp_path):
    written = write_diagnostic_record(record(), root=tmp_path)
    (written / "record.json").write_text(
        json.dumps({**read_diagnostic_record(written), "schema_version": 99}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="schema_version"):
        read_diagnostic_record(written)


# --------------------------------------------------------------------------
# The dataset fingerprint the diagnostics share with the pilot
# --------------------------------------------------------------------------
def _source():
    return DataSource(
        url="https://example.invalid/data/raw/toy.csv",
        repo="IFoA-ADSWP/tabular-foundation-model",
        ref="deadbeef",
        ref_is_pinned=True,
    )


def test_fingerprint_of_a_known_table(tmp_path):
    import pandas as pd

    data_dir = tmp_path / "raw"
    data_dir.mkdir()
    path = data_dir / "toy.csv"
    path.write_text("y,a,leaky\n0,1,2\n1,3,4\n0,5,6\n", encoding="utf-8")

    fp = dataset_fingerprint(
        "toy",
        frame=pd.read_csv(path),
        target="y",
        drop=("leaky",),
        path=path,
        repo_root=tmp_path,
        source=_source(),
    )

    assert fp["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert (fp["n_rows"], fp["n_cols"], fp["file"]) == (3, 3, "toy.csv")
    assert (fp["target"], fp["drop"]) == ("y", ["leaky"])
    assert fp["positive_rate"] == pytest.approx(1 / 3, abs=1e-6)
    assert fp["source_url"].endswith("/data/raw/toy.csv")
    assert (fp["source_ref"], fp["source_ref_is_pinned"]) == ("deadbeef", True)


def test_fingerprint_of_a_frame_with_no_file_states_it_cannot_hash(tmp_path):
    """No bytes on disk means no content hash: the absence is stated, not invented."""
    import pandas as pd

    fp = dataset_fingerprint(
        "in_memory",
        frame=pd.DataFrame({"y": [0, 1], "a": [1.0, 2.0]}),
        target="y",
        path=None,
        repo_root=tmp_path,
        source=_source(),
    )
    assert fp["sha256"] is None and fp["file"] is None
    assert fp["n_rows"] == 2


def test_fingerprint_states_a_missing_table(tmp_path):
    """A table that is not on disk is STATE, not an error -- the original behaviour."""
    missing = dataset_fingerprint(
        "absent",
        target="y",
        path=tmp_path / "absent.csv",
        repo_root=tmp_path,
        source=_source(),
    )
    assert missing == {
        "name": "absent",
        "path": str(tmp_path / "absent.csv"),
        "exists": False,
    }


# --------------------------------------------------------------------------
# Matched-inference-context evidence
# --------------------------------------------------------------------------
def test_matched_context_evidence_carries_the_numbers_compared():
    evidence = matched_context_evidence(
        {
            "A_raw": (2000, "full training split"),
            "B_ft3": (2000, "refit on full X_"),
        }
    )
    assert evidence["checked"] is True
    assert evidence["baseline_arm"] == "A_raw"
    assert evidence["arms"]["B_ft3"] == {"rows": 2000, "mechanism": "refit on full X_"}


def test_matched_context_evidence_states_when_nothing_was_compared():
    """A diagnostic that runs no model must not imply a pass nobody earned."""
    assert matched_context_evidence()["checked"] is False


def test_matched_context_evidence_propagates_the_violation():
    with pytest.raises(AssertionError, match="MATCHED-CONTEXT VIOLATION"):
        matched_context_evidence({"A_raw": (2000, "full"), "B_ft3": (64, "subsampled")})
