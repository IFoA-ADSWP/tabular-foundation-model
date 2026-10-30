"""`scripts/diagnostics/d3_reframe.py`: the §14.14 positive control, and the paid boundary.

The control is asserted against the **documented** figures, not against a re-derivation: rank #1,
the mean AUC per task and seed, and a paired p below 0.05. A control that only checked ordering
would pass with every number wrong.

Run:  python -m pytest tests/test_d3_reframe.py -v
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from provenance import DIAGNOSTIC_RECORD_FIELDS  # noqa: E402

SCRIPT = REPO_ROOT / "scripts" / "diagnostics" / "d3_reframe.py"

HEADER = (
    "dataset,task,metric,seed,baseline,tabpfn_mean,tabpfn_se,base_mean,base_se,"
    "delta,t_paired,p_paired,tabpfn_rank,n_folds\n"
)


@pytest.fixture(scope="module")
def d3():
    spec = importlib.util.spec_from_file_location("d3_reframe", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["d3_reframe"] = mod
    spec.loader.exec_module(mod)
    return mod


def _record(root, name):
    return json.loads((root / "d3_reframe" / name / "record.json").read_text())


def _summary(path, dataset, rows):
    lines = [HEADER]
    for task, seed, mean, p, rank in rows:
        base = mean - 0.008
        lines.append(
            f"{dataset},{task},auc,{seed},cat,{mean},0.004,{base},0.003,0.008,5.0,{p},{rank},5\n"
        )
    path.write_text("".join(lines))
    return path


def test_control_reproduces_section_14_14_from_committed_evidence(tmp_path, d3):
    root = tmp_path / "records"
    assert d3.main(["--control", "--run-id", "R1"], root=root) == 0

    binary = _record(root, "R1-spanish_motor_freq-binary")
    ordinal = _record(root, "R1-spanish_motor_freq-ordinal")

    for record, task, seeds in ((binary, "binary", [7, 42]), (ordinal, "ordinal", [42])):
        assert list(record) == list(DIAGNOSTIC_RECORD_FIELDS)
        # Independent of the code under test: hash the bytes here.
        assert record["dataset_sha256"] == hashlib.sha256(d3.EVIDENCE.read_bytes()).hexdigest()
        assert record["model_version"] == "v3_default"
        m = record["measurements"]
        assert m["task"] == task and m["dataset"] == "spanish_motor_freq"
        assert m["seeds"] == seeds
        assert m["control"]["reproduced"] is True
        for check in m["checks"]:
            assert check["recorded_rank"] == 1
            assert check["mean_ok"] is True
            assert check["significant"] is True


def test_a_wrong_mean_fails_even_when_the_rank_is_right(tmp_path, d3):
    """The control reads the numbers, not only the ordering: a rank-1 result with a wrong mean fails."""
    evidence = _summary(
        tmp_path / "wrong_mean.csv",
        "spanish_motor_freq",
        [("binary", 42, 0.7500, 0.001, 1), ("binary", 7, 0.7165, 0.002, 1),
         ("ordinal", 42, 0.7167, 0.001, 1)],
    )
    with pytest.raises(SystemExit, match="CONTROL FAILED"):
        d3.main(["--control", "--run-id", "R2"], root=tmp_path / "records", evidence=evidence)
    assert not (tmp_path / "records" / "d3_reframe").exists()


def test_a_rank_two_result_fails(tmp_path, d3):
    evidence = _summary(
        tmp_path / "rank2.csv",
        "spanish_motor_freq",
        [("binary", 42, 0.7170, 0.001, 2), ("binary", 7, 0.7165, 0.002, 1),
         ("ordinal", 42, 0.7167, 0.001, 1)],
    )
    with pytest.raises(SystemExit, match="CONTROL FAILED"):
        d3.main(["--control", "--run-id", "R3"], root=tmp_path / "records", evidence=evidence)


def test_reframing_a_new_dataset_refuses_before_writing(tmp_path, d3):
    with pytest.raises(SystemExit, match="REFUSING"):
        d3.main(["--dataset", "freMTPL2freq"], root=tmp_path / "records")
    assert not (tmp_path / "records" / "d3_reframe").exists()


def test_an_empty_dataset_name_cannot_bypass_the_refusal(d3):
    """`is not None`, not truthiness: `--dataset ""` was accepted and ignored before."""
    with pytest.raises(SystemExit, match="REFUSING"):
        d3.main(["--dataset", ""], root=Path("/nonexistent"))


def test_the_refusal_names_the_measured_cost(d3):
    with pytest.raises(SystemExit) as excinfo:
        d3.main(["--dataset", "norauto"], root=Path("/nonexistent"))
    assert "0.0368" in str(excinfo.value), "a refusal without a number is a shrug"
