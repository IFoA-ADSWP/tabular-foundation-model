"""The baseline forest must not drift from the verdict document (#647).

The figure recomputes every point from the committed v5 captures; the document publishes the same
points from the same captures. This test parses the document's primary table and compares the two,
so a correction to one cannot leave the other silently wrong — the same guard the #607 figures use.

`severity_spanish` is the row to watch: its fold holds fewer than 10,000 rows, so the two budgets are
one fit and must be drawn once, not twice with identical intervals.
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
SCRIPT = REPO / "scripts" / "infra" / "baseline_figures.py"
RESULT = REPO / "docs" / "experiments" / "fair-test-freq-sev" / "actuarial_baseline_result.md"

NUMBER = r"[−+\-0-9.]+"


def _module():
    spec = importlib.util.spec_from_file_location("baseline_figures", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["baseline_figures"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def figures():
    return _module()


@pytest.fixture(scope="module")
def readings(figures):
    return figures.rows()


def _published_primary() -> dict[str, tuple[float, float, float]]:
    """The primary table's targets → (r, low, high), read from the result document."""
    text = RESULT.read_text(encoding="utf-8").replace("−", "-")
    section = text.split("## Result — primary")[1].split("## Result — matched")[0]
    rows = re.findall(
        rf"\|\s*(\w+)\s*\|[^|]+\|\s*\*\*({NUMBER})%\*\*\s*\|\s*\[({NUMBER})%,\s*({NUMBER})%\]",
        section,
    )
    return {name: (float(r), float(low), float(high)) for name, r, low, high in rows}


def test_the_primary_rows_match_the_published_table(figures, readings):
    """Every primary row is the document's number, recomputed from the captures."""
    published = _published_primary()
    assert set(published) == {
        "frequency_french",
        "frequency_spanish",
        "severity_french",
        "severity_spanish",
    }

    # `severity_spanish` is labelled "one fit" rather than "full pool": it is a primary row too.
    primary = {row.group: row for row in readings if not row.label.endswith("10k rows")}
    for target, (value, low, high) in published.items():
        row = primary[target]
        assert row.value == pytest.approx(value / 100, abs=5e-5), target
        assert row.low == pytest.approx(low / 100, abs=5e-5), target
        assert row.high == pytest.approx(high / 100, abs=5e-5), target


def test_every_primary_target_is_no_go(readings):
    primary = [row for row in readings if not row.label.endswith("10k rows")]

    assert len(primary) == 4
    assert {row.decision for row in primary} == {"No-go"}


def test_matched_french_frequency_is_the_only_row_that_moves(readings):
    matched = {row.group: row for row in readings if row.label.endswith("10k rows")}

    assert matched["frequency_french"].decision == "Inconclusive"
    assert matched["frequency_french"].value == pytest.approx(-0.0110, abs=1e-4)
    assert (matched["frequency_french"].low, matched["frequency_french"].high) == pytest.approx(
        (-0.0343, 0.0122), abs=1e-4
    )
    assert matched["frequency_spanish"].decision == "No-go"
    assert matched["severity_french"].decision == "No-go"


def test_severity_spanish_is_drawn_once(readings):
    """Both arms are the same fit: the figure says so in the label and does not draw it twice."""
    spanish = [row for row in readings if row.group == "severity_spanish"]

    assert len(spanish) == 1
    assert spanish[0].label == "Spanish severity · one fit"


def test_the_floors_are_the_registered_ones(readings):
    floors = {row.group: row.floor for row in readings}

    assert floors["frequency_spanish"] == pytest.approx(0.04)
    assert floors["frequency_french"] == pytest.approx(0.02)
    assert floors["severity_french"] == pytest.approx(0.02)
    assert floors["severity_spanish"] == pytest.approx(0.02)


def test_the_cli_regenerates_byte_identically(tmp_path, figures):
    first, second = tmp_path / "first", tmp_path / "second"
    assert figures.main(["--out", str(first)]) == 0
    assert figures.main(["--out", str(second)]) == 0
    plt.close("all")

    for suffix in (".pdf", ".png"):
        one = (first / f"actuarial_baseline_forest{suffix}").read_bytes()
        two = (second / f"actuarial_baseline_forest{suffix}").read_bytes()
        assert one == two
        assert len(one) > 1_000
