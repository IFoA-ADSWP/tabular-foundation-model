"""The verdict figures must not drift from the tables they illustrate (#607).

A forest plot is a second rendering of numbers that already exist in a report. If the figure computes
them, a correction to the analysis reaches both or neither; if the plotting code types them, the next
correction makes the figure quietly wrong. So these tests recompute the rows from the committed
artefacts and compare them with the published tables.

The rendering test is a smoke test with one substantive assertion: a figure written to a temporary
directory leaves `docs/figures/` untouched.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pytest  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "infra" / "verdict_figures.py"


def _module():
    spec = importlib.util.spec_from_file_location("verdict_figures", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["verdict_figures"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def figures():
    return _module()


def _by_label(rows, fragment):
    return next(row for row in rows if fragment in row.label)


def test_the_phase2_figure_reproduces_the_outcome_table(figures):
    """`FINETUNING_PHASE2_OUTCOME.md` §1 publishes these four cells; the figure draws them."""
    rows = figures.phase2_rows()

    anchor = _by_label(rows, "uslapseagent")
    assert anchor.value == pytest.approx(0.0035, abs=1e-4)
    assert (anchor.low, anchor.high) == pytest.approx((0.00272, 0.00428), abs=1e-4)
    assert anchor.decision == "gain"

    eudirectlapse = _by_label(rows, "eudirectlapse")
    assert eudirectlapse.value == pytest.approx(0.0007, abs=1e-4)
    assert (eudirectlapse.low, eudirectlapse.high) == pytest.approx((-0.0003, 0.0018), abs=1e-4)
    assert eudirectlapse.decision == "equivalence"

    spanish = _by_label(rows, "spanish_motor_lapse")
    assert spanish.value == pytest.approx(0.00029, abs=1e-4)
    assert (spanish.low, spanish.high) == pytest.approx((-0.00021, 0.00078), abs=1e-4)
    assert spanish.decision == "equivalence"


def test_only_the_spanish_cell_is_quoted(figures):
    """It has no committed capture, and the marker's fill is how a reader sees that.

    If a capture ever lands, this test fails and the row should be recomputed rather than re-marked.
    """
    rows = figures.phase2_rows()

    quoted = {row.label: row.computed for row in rows if row.value is not None}
    assert quoted[_by_label(rows, "spanish_motor_lapse").label] is False
    assert all(computed for label, computed in quoted.items() if "spanish" not in label)


def test_a_stopped_cell_carries_no_interval(figures):
    """`coil2000` is a stop, not a null: there is no estimate to draw and the figure must not invent one."""
    coil = _by_label(figures.phase2_rows(), "coil2000")

    assert coil.value is None and coil.low is None and coil.high is None
    assert coil.decision == "stopped"
    assert "0.0149" in coil.detail


def test_the_fair_test_figure_reproduces_the_verdict_table(figures):
    """`freq_sev_fair_test_result.md` publishes these rows; `build_summary` is the one definition."""
    rows = figures.fair_test_rows()

    french = _by_label(rows, "French portfolio")
    assert french.value == pytest.approx(0.0969, abs=1e-4)
    assert (french.low, french.high) == pytest.approx((0.0743, 0.1195), abs=1e-4)
    assert french.decision == "Go"

    frequency_task = rows[0]
    assert frequency_task.label.startswith("Task: frequency")
    assert frequency_task.value == pytest.approx(0.0685, abs=1e-4)
    assert frequency_task.decision == "Go"

    severity_task = _by_label(rows, "Task: severity")
    assert severity_task.value == pytest.approx(0.0036, abs=1e-4)
    assert severity_task.decision == "Heterogeneous"


def test_every_row_states_where_its_number_came_from(figures):
    for row in figures.phase2_rows() + figures.fair_test_rows():
        assert row.decision
        assert isinstance(row.computed, bool)


def test_both_figures_export_a_pdf_and_a_png(tmp_path, figures):
    figures.apply_static_style()
    rows = [
        ("phase2", figures.phase2_rows(), False, figures.DELTA),
        ("fair", figures.fair_test_rows(), True, None),
    ]

    for name, data, percent, band in rows:
        pdf, png = figures._draw(
            data, stem=tmp_path / name, xlabel="x", percent=percent, band=band
        )
        assert pdf.read_bytes().startswith(b"%PDF")
        assert png.read_bytes()[1:4] == b"PNG"
        assert pdf.stat().st_size > 1_000 and png.stat().st_size > 5_000
        plt.close("all")


def test_rendering_leaves_the_committed_figures_alone(tmp_path, figures):
    """A regenerating run aimed elsewhere must not touch cited evidence in `docs/figures/`."""
    figures.apply_static_style()
    before = {path.name: path.stat().st_mtime for path in figures.FIGURES.iterdir()}

    figures._draw(
        figures.fair_test_rows(),
        stem=tmp_path / "elsewhere" / "fair",
        xlabel="x",
        percent=True,
    )
    plt.close("all")

    after = {path.name: path.stat().st_mtime for path in figures.FIGURES.iterdir()}
    assert after == before
