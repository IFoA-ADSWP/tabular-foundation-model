"""D18's evidence is committed, seed-disjoint, and reproduces the reading it is cited for (#436).

Seam: the run directories under `results/`, the verdict tool's public reading, and the figures the
result document prints. `read_run` verifies every array against its `capture.json` and its record, so
the test reads the committed evidence exactly as a reviewer would. It never calls the capture
generator, and it compares the arithmetic against the document rather than a second copy of the same
literals.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import verdict  # noqa: E402
from capture_reader import read_run  # noqa: E402

RESULT_DOC = REPO_ROOT / "docs" / "analyses" / "finetuning_breadth_eudirectlapse_result.md"

#: The twenty launches the result document cites, one directory per seed range.
RUNS = (
    "20261104T234013Z",
    "20261105T001837Z",
    "20261104T234127Z",
    "20261104T234132Z",
    "20261105T100533Z",
    "20261105T005435Z",
    "20261105T005447Z",
    "20261105T124200Z",
    "20261105T012925Z",
    "20261105T013749Z",
    "20261105T013755Z",
    "20261105T124205Z",
    "20261105T140236Z",
    "20261105T103841Z",
    "20261105T103937Z",
    "20261105T103853Z",
    "20261105T140242Z",
    "20261105T111110Z",
    "20261105T114320Z",
    "20261105T114647Z",
)

_MEAN = re.compile(r"Mean ΔAUC over (\d+) seeds \| \*\*([+\u2212-]?\d+\.\d+)\*\*")
_SD = re.compile(r"between-seed SD (\d+\.\d+)")


def _documented() -> tuple[int, float, float]:
    """The seed count, mean and SD the result document prints in its summary table."""
    text = RESULT_DOC.read_text(encoding="utf-8")
    mean = _MEAN.search(text)
    sd = _SD.search(text)
    assert mean and sd, "the result document's summary table is not in the expected shape"
    return int(mean.group(1)), float(mean.group(2).replace("\u2212", "-")), float(sd.group(1))


@pytest.fixture(scope="module")
def pooled():
    return verdict.pool(tuple(read_run(REPO_ROOT / "results" / run) for run in RUNS))


def test_the_cited_runs_carry_every_seed_exactly_once(pooled):
    """A repeated seed would enter the mean twice; a gap would silently shrink the design."""
    assert pooled.dataset == "eudirectlapse"
    assert {slot.seed for slot in pooled.slots} == set(range(93, 331))
    assert len(pooled.slots) == 238 * 2


def test_the_committed_evidence_produces_the_documented_figures(pooled):
    """The figures in the result document are the ones its own captures produce."""
    seeds, mean, sd = _documented()
    (arm,) = verdict.arms(pooled)

    assert arm.name == "B_ft30"
    assert len(arm.deltas) == seeds == 238
    assert arm.mean == pytest.approx(mean, abs=5e-5)
    assert arm.sd == pytest.approx(sd, abs=5e-5)
    assert sum(delta.delta_auc > 0 for delta in arm.deltas) == 134


def test_the_null_band_lets_the_rule_claim_equivalence(pooled):
    """The instrument check the document leans on is measured here, not asserted in prose."""
    (arm,) = verdict.arms(pooled)
    null = verdict.null_band(pooled, arm, reps=100)

    assert null["sd"] == pytest.approx(0.0085, abs=5e-4)
    assert null["false_positive_rate"] <= verdict.MAX_FALSE_POSITIVE
    assert verdict.reading(arm, 0.002, null["false_positive_rate"]) == "equivalence"
