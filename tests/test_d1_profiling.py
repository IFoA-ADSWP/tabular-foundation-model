"""`scripts/diagnostics/d1_profiling.py`: the first consumer of the shared record writer.

Two seams: the profiling rule (`profile_frame`, pure and testable on a synthetic frame) and the
record the script leaves on disk. The CLI is checked for the property #211 asks of it -- that no
flag can name a location outside `outputs/diagnostics/`.

Run:  python -m pytest tests/test_d1_profiling.py -v
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from model_version import resolve_model_path  # noqa: E402  (importable after the src path insert above)
from provenance import DIAGNOSTIC_RECORD_FIELDS, read_diagnostic_record, sha256_file  # noqa: E402  (importable after the src path insert above)

SCRIPT = REPO_ROOT / "scripts" / "diagnostics" / "d1_profiling.py"


@pytest.fixture(scope="module")
def d1():
    spec = importlib.util.spec_from_file_location("d1_profiling", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["d1_profiling"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def csv_path(tmp_path):
    path = tmp_path / "synthetic.csv"
    pd.DataFrame(
        {
            "target": [0, 1, 0, 1, 0, 1],
            "amount": [1.0, 2.0, None, 4.0, 5.0, 6.0],
            "kind": ["a", "b", "a", "b", "c", "c"],
        }
    ).to_csv(path, index=False)
    return path


def test_profile_frame_counts_structure(d1):
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


def test_d1_emits_one_record_through_the_shared_writer(tmp_path, csv_path, d1):
    out = tmp_path / "records"
    assert d1.main(
        ["--csv", str(csv_path), "--target", "target", "--run-id", "20261029T120000Z"],
        root=out,
    ) == 0

    written = out / "d1_profiling" / "20261029T120000Z"
    on_disk = read_diagnostic_record(written)

    assert list(on_disk) == list(DIAGNOSTIC_RECORD_FIELDS)
    assert on_disk["dataset_name"] == "synthetic"
    assert on_disk["dataset_sha256"] == sha256_file(csv_path)
    assert on_disk["measurements"]["n_rows"] == 6
    # D1 profiles a whole table: the resolved model label is recorded, the split seed is not.
    assert on_disk["model_version"] == resolve_model_path()
    assert on_disk["seed"] is None
    assert on_disk["matched_context"]["checked"] is False


def test_d1_refuses_to_replace_a_record(tmp_path, csv_path, d1):
    argv = ["--csv", str(csv_path), "--target", "target", "--run-id", "20261029T120000Z"]
    out = tmp_path / "records"
    d1.main(argv, root=out)
    before = (out / "d1_profiling" / "20261029T120000Z" / "record.json").read_bytes()

    with pytest.raises(FileExistsError, match="REFUSING TO OVERWRITE"):
        d1.main(argv, root=out)

    after = (out / "d1_profiling" / "20261029T120000Z" / "record.json").read_bytes()
    assert after == before


def test_the_cli_cannot_name_a_location(tmp_path, csv_path, d1):
    """#211: records land under outputs/diagnostics/, not wherever a flag points."""
    for flag in ("--out", "--root"):
        with pytest.raises(SystemExit):
            d1.main(["--csv", str(csv_path), "--target", "target", flag, str(tmp_path)])

    # With no flag to redirect it, the script's only target is the records tree.
    assert d1.DIAGNOSTICS_ROOT == REPO_ROOT / "outputs" / "diagnostics"
