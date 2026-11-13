"""Tests for the cost ledger writer (#416).

The ledger appends one CSV row per paid run. It broke twice in the same way: the record gained a
field, the file's header did not, and `DictWriter` wrote the wider row against the narrower header
so every column after the new one shifted. The first fix quarantined the file; that lost 12 runs.
These tests pin the behaviour that replaced it.
"""
from __future__ import annotations

import csv
import pathlib

from scripts.gpu_helpers import ledger


def _rows(path: pathlib.Path) -> list[dict[str, str]]:
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle))


def _header(path: pathlib.Path) -> list[str]:
    with open(path, newline="") as handle:
        return next(csv.reader(handle))


def test_a_new_ledger_is_created_with_the_record_as_its_header(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "run_ledger.csv"
    record = {"run_id": "20261113T000000Z", "est_cost_usd": 0.25}

    status = ledger.append(path, record, "20261113T000000Z")

    assert status == ledger.NEW
    assert _header(path) == ["run_id", "est_cost_usd"]
    assert _rows(path) == [{"run_id": "20261113T000000Z", "est_cost_usd": "0.25"}]


def test_a_matching_header_just_appends(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "run_ledger.csv"
    ledger.append(path, {"run_id": "a", "est_cost_usd": 0.1}, "a")

    status = ledger.append(path, {"run_id": "b", "est_cost_usd": 0.2}, "b")

    assert status == ledger.APPENDED
    assert [row["run_id"] for row in _rows(path)] == ["a", "b"]


def test_a_new_field_migrates_instead_of_quarantining(tmp_path: pathlib.Path) -> None:
    """The 2026-11-12 failure: `credit_before_usd` arrived and the ledger was moved aside."""
    path = tmp_path / "run_ledger.csv"
    ledger.append(path, {"run_id": "a", "est_cost_usd": 0.1}, "a")

    status = ledger.append(
        path,
        {"run_id": "b", "credit_before_usd": "10.5", "est_cost_usd": 0.2},
        "b",
    )

    assert status == ledger.MIGRATED
    assert _header(path) == ["run_id", "credit_before_usd", "est_cost_usd"]
    rows = _rows(path)
    assert [row["run_id"] for row in rows] == ["a", "b"]
    # the old row keeps its value and gains an empty column rather than shifting
    assert rows[0]["est_cost_usd"] == "0.1"
    assert rows[0]["credit_before_usd"] == ""
    assert rows[1]["credit_before_usd"] == "10.5"
    assert not list(tmp_path.glob("*.stale-*"))


def test_a_dropped_column_is_named(tmp_path: pathlib.Path, capsys) -> None:
    path = tmp_path / "run_ledger.csv"
    ledger.append(path, {"run_id": "a", "retired": "x", "est_cost_usd": 0.1}, "a")

    ledger.append(path, {"run_id": "b", "est_cost_usd": 0.2}, "b")

    assert "retired" in capsys.readouterr().out
    assert _header(path) == ["run_id", "est_cost_usd"]


def test_an_unreadable_ledger_is_quarantined_and_restarted(tmp_path: pathlib.Path) -> None:
    """The one case where starting fresh is the only option — and it must say so."""
    path = tmp_path / "run_ledger.csv"
    path.write_bytes(b"\xff\xfe\x00not a csv")

    status = ledger.append(path, {"run_id": "a", "est_cost_usd": 0.1}, "20261113T000000Z")

    assert status == ledger.QUARANTINED
    assert [p.name for p in tmp_path.glob("*.stale-20261113T000000Z")]
    assert _rows(path) == [{"run_id": "a", "est_cost_usd": "0.1"}]
