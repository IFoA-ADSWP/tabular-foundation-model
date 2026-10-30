"""`scripts/diagnostics/d1_profiling.py`: the first consumer of the shared record writer.

Two seams: the profiling rule (`profile_frame`, pure and testable on a synthetic frame) and the
record the script leaves on disk. The CLI is checked for the property #211 asks of it -- that no
flag can name a location outside `outputs/diagnostics/`.

Run:  python -m pytest tests/test_d1_profiling.py -v
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
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


# --- #302: the rest of the design's table, asserted through the record ------------


@pytest.fixture
def mixed_csv(tmp_path):
    """Two numeric features (one correlated), one categorical, one with missing values."""
    path = tmp_path / "mixed.csv"
    n = 40
    x = [float(i) for i in range(n)]
    # Near-duplicate, not exact: an exactly collinear pair makes the correlation matrix
    # singular, and the point of the test is a computable VIF that is large.
    noise = np.random.default_rng(7).normal(0.0, 1.5, n)
    pd.DataFrame(
        {
            "target": [i % 2 for i in range(n)],
            "x": x,
            "x_copy": [v + float(d) for v, d in zip(x, noise)],
            # Not proportional to x: an exact linear relation would make the matrix singular
            # and the test would be asserting the guard rather than a computed VIF.
            "amount": [None if i < 10 else float((i * 7) % 23) for i in range(n)],
            "kind": ["a", "b", "c", "d"][:1] * n,
        }
    ).to_csv(path, index=False)
    return path


def _record_for(d1, tmp_path, csv, target, name="synthetic"):
    root = tmp_path / "diagnostics"
    rc = d1.main(["--csv", str(csv), "--target", target, "--name", name, "--run-id", "R1"], root=root)
    assert rc == 0
    record = json.loads((root / "d1_profiling" / "R1" / "record.json").read_text())
    return record


def test_record_reports_missingness_per_column_and_marks_pattern_untested(d1, tmp_path, mixed_csv):
    m = _record_for(d1, tmp_path, mixed_csv, "target")["measurements"]

    assert m["missing_by_column"] == {"amount": 0.25}
    assert m["n_cols_with_missing"] == 1
    # The design asks for MCAR/MAR/MNAR. Deciding it needs a test the profile cannot run,
    # so the record says so rather than guessing a label.
    assert m["missing_pattern"] == "untested"


def test_record_reports_target_quantiles_for_a_numeric_target(d1, tmp_path):
    csv = tmp_path / "numeric_target.csv"
    pd.DataFrame({"t": [float(i) for i in range(20)], "f": [float(i) for i in range(20)]}).to_csv(
        csv, index=False
    )
    m = _record_for(d1, tmp_path, csv, "t")["measurements"]

    q = m["target"]["quantiles"]
    assert q["p50"] == pytest.approx(9.5)
    assert q["p05"] < q["p50"] < q["p95"]


def test_record_reports_numeric_to_categorical_ratio(d1, tmp_path, mixed_csv):
    m = _record_for(d1, tmp_path, mixed_csv, "target")["measurements"]
    assert m["numeric_to_categorical_ratio"] == pytest.approx(3.0)


def test_record_reports_vif_only_when_it_can_be_computed(d1, tmp_path, mixed_csv):
    """Two near-duplicate numeric features: VIF is computable and high. One feature: it is not."""
    m = _record_for(d1, tmp_path, mixed_csv, "target")["measurements"]
    assert m["max_vif"] is not None and m["max_vif"] > 5

    single = tmp_path / "single.csv"
    pd.DataFrame({"t": [0, 1, 0, 1], "only": [1.0, 2.0, 3.0, 4.0]}).to_csv(single, index=False)
    m2 = _record_for(d1, tmp_path / "two", single, "t")["measurements"]
    assert m2["max_vif"] is None
    assert m2["vif_reason"]


def test_anchors_write_one_record_each_from_the_registry(d1, tmp_path):
    a = tmp_path / "a.csv"
    b = tmp_path / "b.csv"
    pd.DataFrame({"t": [0, 1] * 10, "f": range(20)}).to_csv(a, index=False)
    pd.DataFrame({"y": [0, 1] * 10, "g": range(20)}).to_csv(b, index=False)

    root = tmp_path / "diagnostics"
    registry = {"alpha": {"file": str(a), "target": "t"}, "beta": {"file": str(b), "target": "y"}}
    rc = d1.main(["--all-anchors", "--run-id", "R2"], root=root, datasets=registry)
    assert rc == 0

    # A batch is several runs, not one run holding a list: one record per directory, which is
    # the shared writer's invariant (#211) and is not weakened for convenience.
    runs = sorted(p.name for p in (root / "d1_profiling").iterdir())
    assert runs == ["R2-alpha", "R2-beta"]
    for name, spec in registry.items():
        record = json.loads((root / "d1_profiling" / f"R2-{name}" / "record.json").read_text())
        assert record["dataset_name"] == name
        assert record["dataset_sha256"] == sha256_file(Path(spec["file"]))


def test_two_runs_with_the_same_inputs_produce_the_same_measurements(d1, tmp_path, mixed_csv):
    first = _record_for(d1, tmp_path / "one", mixed_csv, "target")["measurements"]
    second = _record_for(d1, tmp_path / "two", mixed_csv, "target")["measurements"]
    assert first == second
