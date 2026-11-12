"""The lapse student record is a Record, and it cannot fabricate the teacher (#377).

#370's per-fold output went to `/tmp/opencode` and was lost, which is why the lapse numbers were
estimates. This suite pins the committed artifact so a regression in the writer is caught by the
gate rather than by the next reader of the memo:

* the committed record parses through `src/provenance.read_record` and earns `comparable`;
* its teacher rows are exactly the committed `results_per_split.csv` rows re-scored, so the
  reused teacher cannot drift to another model era unnoticed;
* teacher Brier is `null` with a reason, never a number, because no committed teacher
  probabilities exist;
* every pinned student has five folds on both Datasets.

No model is fitted here: the test reads committed files only.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.provenance import read_record, verdict

REPO = Path(__file__).resolve().parents[1]
RECORD = REPO / "results" / "20261031-lapse-students" / "record.json"
PER_FOLD = REPO / "results" / "20261031-lapse-students" / "per_fold.csv"
COMMITTED = REPO / "scripts" / "eval" / "lapse_benchmark_v1" / "results_per_split.csv"

DATASETS = ("eudirectlapse", "spanish_motor_lapse")
STUDENTS = ("catboost", "xgboost", "random_forest", "logistic_regression")
TEACHER_METHOD = "[Lapse] TabPFNClient (default)"


@pytest.fixture(scope="module")
def record() -> dict:
    return json.loads(RECORD.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def per_fold() -> pd.DataFrame:
    return pd.read_csv(PER_FOLD)


def test_record_is_a_comparable_capture(record):
    assert record["schema_version"] == 2
    assert verdict(read_record(RECORD, kind="capture"), kind="capture").status == "comparable"


def test_record_carries_a_version_pin_and_names_its_source(record):
    provenance = record["provenance"]
    assert provenance["model"]["version"] == "v3_default"
    # The label is attributed, not resolved from a client: none was imported.
    assert provenance["model"]["version_source"] == "documented-timeline"
    assert provenance["model"]["client_version"] is None
    assert record["teacher_reuse"]["teacher_refit"] is False
    assert record["teacher_reuse"]["source"].endswith("results_per_split.csv")


def test_teacher_rows_are_the_committed_rows_rescored(per_fold):
    committed = pd.read_csv(COMMITTED)
    teacher = per_fold[per_fold["method"] == "tabpfn"]
    assert len(teacher) == 5 * len(DATASETS)

    for dataset in DATASETS:
        dataset_id = committed.loc[
            committed["dataset"].str.startswith(dataset + "-"), "dataset"
        ].unique()
        assert len(dataset_id) == 1
        rows = committed[
            (committed["dataset"] == dataset_id[0]) & (committed["method"] == TEACHER_METHOD)
        ].sort_values("fold")
        got = teacher[teacher["dataset"] == dataset].sort_values("fold")
        assert got["fold"].tolist() == rows["fold"].tolist()
        # auc = 1 - metric_error, to the last bit of the committed float
        assert got["auc"].tolist() == pytest.approx(
            (1.0 - rows["metric_error"]).tolist(), abs=1e-12
        )


def test_teacher_mean_reproduces_the_published_v3_default_number(per_fold):
    """docs/MODEL_VERSIONS.md: 0.6101 (eudirectlapse) and 0.7553 (spanish_motor_lapse)."""
    expected = {"eudirectlapse": 0.6101, "spanish_motor_lapse": 0.7553}
    for dataset, published in expected.items():
        got = per_fold[(per_fold["dataset"] == dataset) & (per_fold["method"] == "tabpfn")]["auc"].mean()
        assert got == pytest.approx(published, abs=5e-5)


def test_no_teacher_brier_is_invented(record, per_fold):
    teacher = per_fold[per_fold["method"] == "tabpfn"]
    assert teacher["brier"].isna().all()
    # and the absence is explained, not merely blank
    assert record["teacher_reuse"]["teacher_brier"].startswith("not measurable")


def test_every_pinned_student_is_measured_per_fold(per_fold):
    for dataset in DATASETS:
        for student in STUDENTS:
            rows = per_fold[(per_fold["dataset"] == dataset) & (per_fold["method"] == student)]
            assert rows["fold"].tolist() == [0, 1, 2, 3, 4]
            assert rows["auc"].notna().all()
            assert rows["brier"].notna().all()
            # measured here, not reused
            assert rows["source"].str.startswith("measured:").all()
