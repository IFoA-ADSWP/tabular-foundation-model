"""Tests for the documentation link checker."""
from __future__ import annotations

import pathlib

from scripts.check_doc_links import check, candidates


def test_finds_broken_reference(tmp_path: pathlib.Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text("See `docs/missing_page.md` for detail.\n")
    broken = check(sorted((tmp_path / "docs").rglob("*.md")), tmp_path)
    assert [r for _, _, r in broken] == ["docs/missing_page.md"]


def test_resolves_relative_and_root_paths(tmp_path: pathlib.Path) -> None:
    (tmp_path / "docs" / "sub").mkdir(parents=True)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "docs" / "sub" / "b.md").write_text("`../c.md` then `scripts/run.py`\n")
    (tmp_path / "docs" / "c.md").write_text("x\n")
    (tmp_path / "scripts" / "run.py").write_text("x\n")
    assert check(sorted((tmp_path / "docs").rglob("*.md")), tmp_path) == []


def test_skips_placeholders_and_urls(tmp_path: pathlib.Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "d.md").write_text("`runs/<run_id>/meta.json` and https://example.com/a.md\n")
    assert check(sorted((tmp_path / "docs").rglob("*.md")), tmp_path) == []
    assert candidates("plain text with no paths") == []


def test_checks_workbooks_like_any_other_path(tmp_path: pathlib.Path) -> None:
    """A .xlsx reference is a path too.

    The root README's roadmap workbook moved into docs/ in #582, and the acceptance
    criterion was "doclinks resolves the reference" — which was vacuous, because
    .xlsx was not in EXTS and the checker passed a path that did not exist.
    """
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text("See `docs/roadmap/missing.xlsx`.\n")
    broken = check(sorted((tmp_path / "docs").rglob("*.md")), tmp_path)
    assert [r for _, _, r in broken] == ["docs/roadmap/missing.xlsx"]

    (tmp_path / "docs" / "roadmap").mkdir()
    (tmp_path / "docs" / "roadmap" / "present.xlsx").write_text("x\n")
    (tmp_path / "docs" / "a.md").write_text("See `docs/roadmap/present.xlsx`.\n")
    assert check(sorted((tmp_path / "docs").rglob("*.md")), tmp_path) == []
