"""Tests for the documentation status check."""
from __future__ import annotations

import pathlib

from scripts.check_doc_status import (
    CLAIM_REGISTRY,
    DEFAULT_DIRS,
    main,
    registry_problems,
    unlabelled,
)


def _write(tmp_path: pathlib.Path, name: str, text: str) -> None:
    (tmp_path / name).write_text(text)


def _registry(tmp_path: pathlib.Path, rows: str) -> pathlib.Path:
    path = tmp_path / "FINDINGS.md"
    path.write_text(
        "> **Status:** current\n\n| Claim | Status | Owner |\n| --- | --- | --- |\n" + rows
    )
    return path


def test_marked_report_passes(tmp_path: pathlib.Path) -> None:
    _write(tmp_path, "marked.md", "> **Historical document.** Superseded by X.\n\nbody\n")
    missing, total = unlabelled(tmp_path)
    assert missing == []
    assert total == 1


def test_unmarked_report_is_listed(tmp_path: pathlib.Path) -> None:
    _write(tmp_path, "bare.md", "# A report\n\nBody text mentioning the current design.\n")
    missing, total = unlabelled(tmp_path)
    assert missing == ["bare.md"]
    assert total == 1


def test_titles_do_not_pass_but_markers_below_the_window_do_not_either(tmp_path: pathlib.Path) -> None:
    _write(tmp_path, "late.md", "\n".join(["# A report"] + ["filler"] * 20 + ["> **Status:** current"]))
    missing, _ = unlabelled(tmp_path)
    assert missing == ["late.md"], "a marker past the window is not a status"


def test_default_scope_is_the_three_report_tiers(tmp_path: pathlib.Path, monkeypatch) -> None:
    """The default must reach current/, reference/ and archive/ -- not the dissolved docs/reports/.

    docs/reports/ was folded into these three in #200-#202 and the default was left behind, so the
    check exited 2 ("no such directory") and enforced nothing at all.
    """
    assert set(DEFAULT_DIRS) == {"docs/current", "docs/reference", "docs/archive"}
    for tier in DEFAULT_DIRS:
        (tmp_path / tier).mkdir(parents=True)
    (tmp_path / "docs/current/marked.md").write_text("> **Status:** current\n\nbody\n")
    (tmp_path / "docs/archive/bare.md").write_text("# A report\n\nbody\n")

    monkeypatch.chdir(tmp_path)
    assert main([]) == 1, "a bare report in archive/ must fail the run"


def test_each_tier_can_be_checked_on_its_own(tmp_path: pathlib.Path, monkeypatch) -> None:
    for tier in ("current", "reference"):
        (tmp_path / tier).mkdir()
    (tmp_path / "current/marked.md").write_text("> **Status:** current\n")
    (tmp_path / "reference/bare.md").write_text("# A report\n\nbody\n")

    monkeypatch.chdir(tmp_path)
    assert main(["--dir", "current"]) == 0
    assert main(["--dir", "current", "--dir", "reference"]) == 1


def test_a_missing_directory_fails_rather_than_passing_silently(tmp_path: pathlib.Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["--dir", "docs/reports"]) == 2



def test_a_registry_row_that_restates_a_number_fails(tmp_path: pathlib.Path) -> None:
    """The failure this check exists to stop: a copied number that drifts from its owner."""
    problems = registry_problems(
        _registry(tmp_path, "| **F1** beats raw at 10,000 training rows | current | docs/owner.md |\n")
    )
    assert len(problems) == 1
    assert "F1" in problems[0] and "restates a number" in problems[0]


def test_row_ids_and_dates_are_identifiers_not_numbers(tmp_path: pathlib.Path) -> None:
    problems = registry_problems(
        _registry(
            tmp_path,
            "| **L3** superseded by F1 on 2026-11-08 | superseded | docs/owner.md |\n",
        )
    )
    assert problems == [], "an id or a date is not a measurement"


def test_a_registry_row_must_be_three_columns(tmp_path: pathlib.Path) -> None:
    problems = registry_problems(
        _registry(tmp_path, "| F1 | a claim | current | docs/owner.md |\n")
    )
    assert len(problems) == 1
    assert "Claim | Status | Owner" in problems[0]


def test_a_moved_registry_fails_rather_than_passing_silently(tmp_path: pathlib.Path) -> None:
    problems = registry_problems(tmp_path / "gone.md")
    assert problems and "missing claim registry" in problems[0]


def test_the_committed_registry_carries_no_numbers() -> None:
    """The shipped artefact, not a fixture: this is the check running on the real page."""
    root = pathlib.Path(__file__).resolve().parents[1]
    assert registry_problems(root / CLAIM_REGISTRY) == []
