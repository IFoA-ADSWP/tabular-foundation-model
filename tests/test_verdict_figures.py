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
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pytest  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "infra" / "verdict_figures.py"
SPANISH_RESULT = REPO / "docs" / "experiments" / "pilot2-phase2" / "finetuning_breadth_spanish_result.md"


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


def test_the_cli_exports_a_pdf_and_a_png_for_both_figures(tmp_path, figures):
    """The seam a caller uses is the command line, so the test drives that rather than `_draw`."""
    assert figures.main(["--only", "both", "--out", str(tmp_path)]) == 0

    for stem in ("finetuning_phase2_forest", "freq_sev_forest"):
        pdf, png = tmp_path / f"{stem}.pdf", tmp_path / f"{stem}.png"
        assert pdf.read_bytes().startswith(b"%PDF")
        assert png.read_bytes()[1:4] == b"PNG"
        assert pdf.stat().st_size > 1_000 and png.stat().st_size > 5_000
    plt.close("all")


def test_the_quoted_spanish_cell_matches_the_owning_analysis(figures):
    """The one typed row is pinned to the document that owns it, not to itself.

    `spanish_motor_lapse` has no committed capture, so its interval is quoted. Quoting makes the
    figure the second place the number lives; this test makes a correction to the owning analysis
    fail here rather than leave the figure quietly wrong.
    """
    text = SPANISH_RESULT.read_text(encoding="utf-8").replace("\u2212", "-")
    match = re.search(
        r"\*\*\+(?P<value>[\d.]+) ROC AUC\*\*, 95% interval "
        r"\*\*\[(?P<low>[-+]?[\d.]+), (?P<high>[-+]?[\d.]+)\]\*\*",
        text,
    )
    assert match, "the owning analysis no longer states the interval this test parses"
    seeds = re.search(r"Across \*\*(\d+) fresh seeds\*\*", text)

    quoted = figures.SPANISH_PUBLISHED
    assert quoted["value"] == pytest.approx(float(match.group("value")), abs=1e-9)
    assert quoted["low"] == pytest.approx(float(match.group("low")), abs=1e-9)
    assert quoted["high"] == pytest.approx(float(match.group("high")), abs=1e-9)
    assert seeds and quoted["seeds"] == int(seeds.group(1))


def test_regeneration_is_byte_identical(tmp_path, figures):
    """A committed figure that has not changed must not produce a binary diff.

    The PDF exporter stamps a creation date by default, so two identical draws differed byte for byte
    until `save_publication` stopped writing the timestamp. This pins that: a diff in a committed
    figure now means the picture changed.
    """
    first, second = tmp_path / "first", tmp_path / "second"
    assert figures.main(["--only", "phase2", "--out", str(first)]) == 0
    assert figures.main(["--only", "phase2", "--out", str(second)]) == 0
    plt.close("all")

    for suffix in (".pdf", ".png"):
        assert (first / f"finetuning_phase2_forest{suffix}").read_bytes() == (
            second / f"finetuning_phase2_forest{suffix}"
        ).read_bytes()


def test_rendering_leaves_the_committed_figures_alone(tmp_path, figures):
    """A regenerating run aimed elsewhere must not touch cited evidence in `docs/figures/`."""
    before = {path.name: path.stat().st_mtime for path in figures.FIGURES.iterdir()}

    assert figures.main(["--only", "fair-test", "--out", str(tmp_path)]) == 0
    plt.close("all")

    after = {path.name: path.stat().st_mtime for path in figures.FIGURES.iterdir()}
    assert after == before
