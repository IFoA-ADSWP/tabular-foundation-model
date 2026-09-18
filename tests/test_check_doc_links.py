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
