"""#211: one diagnostic record writer, one field definition, one record shape.

The seam is the record on disk -- `record.json` and `record.csv` under
`<root>/<diagnostic>/<run_id>/` -- because that is the surface a reviewer also reads. Two
diagnostics writing through the one writer must produce byte-identical keys, and neither may
append a row under a header an older schema wrote: both failures are on record in
`outputs/gpu-pilot/README.md`, and this ticket exists to make them impossible rather than
unlikely.

Run:  python -m pytest tests/test_diagnostics_records.py -v
"""

from __future__ import annotations

import dataclasses
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import provenance  # noqa: E402
from provenance import (  # noqa: E402
    DIAGNOSTIC_RECORD_FIELDS,
    DIAGNOSTIC_RECORD_SCHEMA_VERSION,
    DiagnosticRecord,
    read_diagnostic_record,
    write_diagnostic_record,
)

D1_SCRIPT = REPO_ROOT / "scripts" / "diagnostics" / "d1_profiling.py"
RUN_PILOT = REPO_ROOT / "scripts" / "run_pilot.py"


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def d1():
    return _load(D1_SCRIPT, "d1_profiling")


def record(diagnostic="d1_profiling", run_id="20261029T120000Z", **overrides):
    """One record, built the way a diagnostic builds it: values, never key names."""
    values = {
        "diagnostic": diagnostic,
        "run_id": run_id,
        "dataset_name": "coil2000",
        "dataset_sha256": "a" * 64,
        "model_version": None,
        "measurements": {"n_rows": 10, "positive_rate": 0.5},
    }
    values.update(overrides)
    return DiagnosticRecord(**values)


# --------------------------------------------------------------------------
# One definition of the fields
# --------------------------------------------------------------------------
def test_field_set_is_the_dataclass_and_nothing_else():
    """The header and the JSON keys both come from here, so neither can gain a field alone."""
    assert DIAGNOSTIC_RECORD_FIELDS == tuple(f.name for f in dataclasses.fields(DiagnosticRecord))
    assert DIAGNOSTIC_RECORD_FIELDS[0] == "schema_version"


def test_a_diagnostic_cannot_invent_a_field():
    """An unknown key is a TypeError at construction, not a column at write time."""
    with pytest.raises(TypeError):
        record(metric="log_loss")
    with pytest.raises(TypeError):
        DiagnosticRecord(diagnostic="d1_profiling", run_id="r", model_version=None)


# --------------------------------------------------------------------------
# Records land where #211 says they land
# --------------------------------------------------------------------------
def test_record_lands_under_diagnostic_and_run_id(tmp_path):
    written = write_diagnostic_record(record(), root=tmp_path)

    assert written == tmp_path / "d1_profiling" / "20261029T120000Z"
    on_disk = json.loads((written / "record.json").read_text(encoding="utf-8"))
    assert list(on_disk) == list(DIAGNOSTIC_RECORD_FIELDS)
    assert on_disk["schema_version"] == DIAGNOSTIC_RECORD_SCHEMA_VERSION
    assert on_disk["created_utc"], "the writer stamps the timestamp, not the diagnostic"

    header = (written / "record.csv").read_text(encoding="utf-8").splitlines()[0]
    assert header == ",".join(DIAGNOSTIC_RECORD_FIELDS)


# --------------------------------------------------------------------------
# The acceptance criterion: two diagnostics, byte-identical keys
# --------------------------------------------------------------------------
def test_two_diagnostics_writing_the_same_field_produce_byte_identical_keys(tmp_path):
    one = write_diagnostic_record(record("d1_profiling"), root=tmp_path)
    two = write_diagnostic_record(record("d2_feature_importance"), root=tmp_path)

    csv_headers = [(d / "record.csv").read_bytes().splitlines()[0] for d in (one, two)]
    assert csv_headers[0] == csv_headers[1], "the CSV header is not shared between diagnostics"

    first, second = (json.loads((d / "record.json").read_text(encoding="utf-8")) for d in (one, two))
    assert list(first) == list(second) == list(DIAGNOSTIC_RECORD_FIELDS)
    assert sorted(first["measurements"]) == sorted(second["measurements"])
    # Only the diagnostic's own name differs; every shared field is spelled the same way.
    assert {k for k in first if first[k] != second[k]} == {"diagnostic"}


# --------------------------------------------------------------------------
# The two failures outputs/gpu-pilot/README.md records
# --------------------------------------------------------------------------
def test_existing_record_is_rewritten_never_appended_to(tmp_path):
    """The DictWriter incident: an old header must not survive a second write."""
    write_diagnostic_record(record(), root=tmp_path)

    with pytest.raises(FileExistsError):
        write_diagnostic_record(record(), root=tmp_path)

    written = write_diagnostic_record(
        record(measurements={"n_rows": 11}), root=tmp_path, overwrite=True
    )
    lines = (written / "record.csv").read_text(encoding="utf-8").splitlines()
    assert lines[0] == ",".join(DIAGNOSTIC_RECORD_FIELDS)
    assert len(lines) == 2, "one header and one row: rewritten in full, not appended"
    assert json.loads((written / "record.json").read_text(encoding="utf-8"))["measurements"] == {
        "n_rows": 11
    }


def test_a_record_cannot_be_written_outside_its_tree(tmp_path):
    """The split-record incident: the path is derived, so it cannot point somewhere else."""
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
# D1 -- the first consumer
# --------------------------------------------------------------------------
def test_d1_profiles_a_frame(d1):
    frame = pd.DataFrame(
        {
            "target": [0, 1, 0, 1, 0, 1],
            "amount": [1.0, 2.0, None, 4.0, 5.0, 6.0],
            "kind": ["a", "b", "a", "b", "c", "c"],
        }
    )
    profile = d1.profile_frame(frame, "target")

    assert profile["n_rows"] == 6
    assert profile["n_features"] == 2
    assert profile["n_numeric_features"] == 1
    assert profile["n_categorical_features"] == 1
    assert profile["n_cols_with_missing"] == 1
    assert profile["missing_rate"] == pytest.approx(0.055556, abs=1e-6)  # 1 of 18 cells
    assert profile["target"] == {
        "kind": "binary",
        "positive_rate": 0.5,
        "n_positive": 3,
        "entropy_bits": 1.0,
    }


def test_d1_emits_through_the_shared_writer(tmp_path, d1):
    csv_path = tmp_path / "synthetic.csv"
    pd.DataFrame(
        {"y": [0, 1, 0, 1], "x": [0.1, 0.2, 0.3, 0.4], "c": ["a", "b", "a", "b"]}
    ).to_csv(csv_path, index=False)

    out = tmp_path / "records"
    assert d1.main(["--csv", str(csv_path), "--target", "y", "--out", str(out)]) == 0

    written = out / "d1_profiling" / next(p.name for p in (out / "d1_profiling").iterdir())
    on_disk = json.loads((written / "record.json").read_text(encoding="utf-8"))
    assert list(on_disk) == list(DIAGNOSTIC_RECORD_FIELDS)
    assert on_disk["dataset_name"] == "synthetic"
    assert on_disk["model_version"] is None, "D1 runs no model, and says so"
    assert on_disk["measurements"]["n_rows"] == 4


# --------------------------------------------------------------------------
# The move: run_pilot uses the shared implementation, it does not restate it
# --------------------------------------------------------------------------
def test_run_pilot_imports_the_moved_helpers():
    rp = _load(RUN_PILOT, "run_pilot")

    assert rp.assert_matched_context is provenance.assert_matched_context
    assert rp.inference_context_rows is provenance.inference_context_rows
    assert rp.FT_ARMS is provenance.FT_ARMS
    assert rp.BASELINE_TABPFN_ARM is provenance.BASELINE_TABPFN_ARM
