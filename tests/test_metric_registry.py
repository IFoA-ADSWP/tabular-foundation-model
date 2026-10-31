"""The registry names the metrics the tool computes — one list, not two.

`docs/analyses/METRIC_REGISTRY.md` is the claim a report cites ("measured with `ece/1`"); the
tool is the behaviour. If they can disagree, the claim is unverifiable, so the suite reads the
table and compares it to `src/rescore.py`.
"""

from __future__ import annotations

import re
from pathlib import Path

import rescore

REGISTRY = Path(__file__).resolve().parents[1] / "docs" / "analyses" / "METRIC_REGISTRY.md"


def _table_rows() -> list[list[str]]:
    rows = []
    for line in REGISTRY.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
        if len(cells) < 4 or not re.fullmatch(r"\d+(\.\d+)*", cells[1]):
            continue  # header separator, header row, or prose table
        rows.append(cells)
    return rows


def test_the_registry_rows_are_exactly_the_metrics_the_tool_computes():
    rows = _table_rows()

    assert {(name, version) for name, version, *_ in rows} == {
        (metric.name, metric.version) for metric in rescore.RECORDED_FIVE
    }


def test_every_registry_row_states_a_definition_and_why_it_exists():
    for name, version, definition, motivation in _table_rows():
        assert definition, f"{name}/{version} has no definition"
        assert motivation, f"{name}/{version} names no finding behind it"
