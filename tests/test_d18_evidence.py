"""D18's evidence is committed, seed-disjoint, and reproduces what the result document prints (#436).

Seam: the run directories under `results/`, the verdict tool's public reading, and the figures the
result document carries. The document names the runs; the test reads that list from the document
rather than keeping a second copy, so a cited run that is not present — or a figure that drifts from
the evidence — fails here. `read_run` verifies every array against its `capture.json` and its record,
so the test reads the committed evidence exactly as a reviewer would. It never calls the capture
generator.
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import verdict  # noqa: E402
from capture_reader import read_run  # noqa: E402

RESULT_DOC = REPO_ROOT / "docs" / "experiments" / "pilot2-phase2" / "finetuning_breadth_eudirectlapse_result.md"

_CITED = re.compile(r"results/(\d{8}T\d{6}Z)")
_MEAN = re.compile(r"Mean ΔAUC over (\d+) seeds \| \*\*([+\u2212-]?\d+\.\d+)\*\*")
_INTERVAL = re.compile(
    r"95% interval \(between-seed SD (\d+\.\d+)\) "
    r"\| \*\*\[([+\u2212-]?\d+\.\d+), ([+\u2212-]?\d+\.\d+)\]\*\*"
)
_POSITIVE = re.compile(r"Seeds positive \| (\d+) / (\d+)")
_NULL = re.compile(r"Permutation null: SD / false-positive rate \| (\d+\.\d+) / \*\*(\d+\.\d+)\*\*")


def _number(text: str) -> float:
    return float(text.replace("\u2212", "-"))


def _documented() -> dict[str, float]:
    """The run ids and summary figures the result document prints."""
    text = RESULT_DOC.read_text(encoding="utf-8")
    mean = _MEAN.search(text)
    interval = _INTERVAL.search(text)
    positive = _POSITIVE.search(text)
    null = _NULL.search(text)
    assert mean and interval and positive and null, (
        "the result document's summary table is not in the expected shape"
    )
    return {
        "seeds": int(mean.group(1)),
        "mean": _number(mean.group(2)),
        "sd": float(interval.group(1)),
        "low": _number(interval.group(2)),
        "high": _number(interval.group(3)),
        "positive": int(positive.group(1)),
        "counted": int(positive.group(2)),
        "null_sd": float(null.group(1)),
        "null_fpr": float(null.group(2)),
    }


@pytest.fixture(scope="module")
def pooled():
    cited = sorted(set(_CITED.findall(RESULT_DOC.read_text(encoding="utf-8"))))
    assert len(cited) == 20, f"the document cites {len(cited)} runs, not twenty"
    return verdict.pool(tuple(read_run(REPO_ROOT / "results" / run) for run in cited))


def test_the_cited_runs_carry_every_seed_exactly_once(pooled):
    """A repeated seed would enter the mean twice; a gap would silently shrink the design."""
    assert pooled.dataset == "eudirectlapse"
    assert {slot.seed for slot in pooled.slots} == set(range(93, 331))
    assert len(pooled.slots) == 238 * 2


def test_the_committed_evidence_produces_the_documented_figures(pooled):
    """The figures in the result document are the ones its own captures produce."""
    doc = _documented()
    (arm,) = verdict.arms(pooled)

    assert arm.name == "B_ft30"
    assert len(arm.deltas) == doc["seeds"] == doc["counted"] == 238
    assert arm.mean == pytest.approx(doc["mean"], abs=5e-5)
    assert arm.sd == pytest.approx(doc["sd"], abs=5e-5)
    se = arm.sd / math.sqrt(len(arm.deltas))
    assert arm.mean - verdict.Z_ALPHA * se == pytest.approx(doc["low"], abs=5e-5)
    assert arm.mean + verdict.Z_ALPHA * se == pytest.approx(doc["high"], abs=5e-5)
    assert sum(delta.delta_auc > 0 for delta in arm.deltas) == doc["positive"]


def test_the_null_band_lets_the_rule_claim_equivalence(pooled):
    """The instrument check and the reading the document leans on are measured here, not asserted."""
    doc = _documented()
    (arm,) = verdict.arms(pooled)
    null = verdict.null_band(pooled, arm, reps=100)

    assert null["sd"] == pytest.approx(doc["null_sd"], abs=5e-4)
    assert null["false_positive_rate"] == doc["null_fpr"]
    assert verdict.reading(arm, 0.002, null["false_positive_rate"]) == "equivalence"
