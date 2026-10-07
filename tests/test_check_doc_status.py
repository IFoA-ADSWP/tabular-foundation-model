"""Tests for the documentation status check."""
from __future__ import annotations

import pathlib

from scripts.check_doc_status import unlabelled


def _write(tmp_path: pathlib.Path, name: str, text: str) -> None:
    (tmp_path / name).write_text(text)


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
