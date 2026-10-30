"""`scripts/diagnostics/d3_reframe.py`: the §14.14 positive control, and the paid boundary.

Two things are asserted, both through the record the script leaves on disk:

1. The control reproduces §14.14 from committed evidence -- TabPFN at AUC rank #1 on both tasks.
2. The control can **fail**: a fixture where another method wins must produce `reproduced: false`
   and a non-zero exit. A check that cannot fail is decoration.

The paid path is asserted too: reframing a new dataset must refuse before writing anything, and say
why, because the design's "analysis $0" line does not hold for datasets the runner would fit.

Run:  python -m pytest tests/test_d3_reframe.py -v
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from provenance import DIAGNOSTIC_RECORD_FIELDS, sha256_file  # noqa: E402

SCRIPT = REPO_ROOT / "scripts" / "diagnostics" / "d3_reframe.py"


@pytest.fixture(scope="module")
def d3():
    spec = importlib.util.spec_from_file_location("d3_reframe", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["d3_reframe"] = mod
    spec.loader.exec_module(mod)
    return mod


def _record(root, name):
    return json.loads((root / "d3_reframe" / name / "record.json").read_text())


HEADER = "dataset,task,method,fold,seed,log_loss,auc,brier,pr_auc,lift10,fit_s,infer_s\n"


def _write_evidence(path, dataset, tabpfn_aucs, rival_aucs):
    lines = [HEADER]
    for fold, (tp, rv) in enumerate(zip(tabpfn_aucs, rival_aucs)):
        for task in ("binary", "ordinal"):
            lines.append(f"{dataset},{task},tabpfn,{fold},42,0.3,{tp},0.09,0.2,2.4,1.0,0.01\n")
            lines.append(f"{dataset},{task},cat,{fold},42,0.3,{rv},0.09,0.2,2.4,1.0,0.01\n")
    path.write_text("".join(lines))
    return path


def test_control_reproduces_section_14_14_from_committed_evidence(tmp_path, d3):
    root = tmp_path / "records"
    assert d3.main(["--control", "--run-id", "R1"], root=root) == 0

    binary = _record(root, "R1-spanish_motor_freq-binary")
    ordinal = _record(root, "R1-spanish_motor_freq-ordinal")

    # The ordinal task has one seed in the committed evidence, the binary task two. Asserting the
    # actual sets keeps the record honest about what it read rather than what we assumed.
    for record, task, seeds in ((binary, "binary", [7, 42]), (ordinal, "ordinal", [42])):
        assert list(record) == list(DIAGNOSTIC_RECORD_FIELDS)
        assert record["dataset_sha256"] == sha256_file(d3.EVIDENCE)
        m = record["measurements"]
        assert m["task"] == task
        assert m["tabpfn_rank"] == 1
        assert m["control"] == {"expected_tabpfn_rank": 1, "reproduced": True}
        assert m["n_methods"] >= 6 and m["n_folds"] == 5 and m["seeds"] == seeds


def test_the_control_can_fail(tmp_path, d3):
    """A rival that beats TabPFN must produce reproduced: false and a non-zero exit."""
    evidence = _write_evidence(tmp_path / "flipped.csv", "spanish_motor_freq",
                               tabpfn_aucs=[0.60] * 5, rival_aucs=[0.70] * 5)
    root = tmp_path / "records"

    with pytest.raises(SystemExit, match="CONTROL FAILED"):
        d3.main(["--control", "--run-id", "R2"], root=root, evidence=evidence)

    m = _record(root, "R2-spanish_motor_freq-binary")["measurements"]
    assert m["tabpfn_rank"] == 2
    assert m["control"]["reproduced"] is False


def test_reframing_a_new_dataset_refuses_before_writing(tmp_path, d3):
    root = tmp_path / "records"
    with pytest.raises(SystemExit, match="REFUSING"):
        d3.main(["--dataset", "freMTPL2freq"], root=root)
    assert not (root / "d3_reframe").exists(), "the refusal must not leave a record behind"


def test_the_refusal_names_the_measured_cost(d3):
    with pytest.raises(SystemExit) as excinfo:
        d3.main(["--dataset", "norauto"], root=Path("/nonexistent"))
    assert "0.0368" in str(excinfo.value), "a refusal without a number is a shrug"
