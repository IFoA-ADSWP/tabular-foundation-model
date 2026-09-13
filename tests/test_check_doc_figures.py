"""Tests for `scripts/check_doc_figures.py`.

The fixtures are synthetic, so the check is proven on this branch even though the Pilot 2
documents themselves live on the proposal branch. A final test runs the check against the real
documents when they are present, and skips otherwise.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
SCRIPT = _REPO / "scripts" / "check_doc_figures.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_doc_figures", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["check_doc_figures"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def cdf():
    return _load()


CLEAN = """# A document

The recommended path costs ~$4.70, the design as written ~$31, and full scale ~$368.
Credit available is $9.60. One successful four-dataset comparison cost 5p.
The ladder probe is 7c and a designed interaction probe $1.11.
"""


def _write(tmp_path: Path, name: str, text: str) -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_a_clean_document_set_passes(cdf, tmp_path, capsys):
    _write(tmp_path, "PILOT_2_A.md", CLEAN)
    assert cdf.main(["--docs-dir", str(tmp_path)]) == 0
    assert "consistent" in capsys.readouterr().out


def test_a_superseded_figure_without_a_marker_is_a_finding(cdf, tmp_path, capsys):
    _write(tmp_path, "PILOT_2_A.md", CLEAN)
    _write(tmp_path, "PILOT_2_B.md", "The old plan came to $4.15 in total.\n")
    assert cdf.main(["--docs-dir", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "superseded figure $4.15" in out
    assert "PILOT_2_B.md:1" in out


def test_the_same_figure_marked_as_historical_passes(cdf, tmp_path):
    _write(tmp_path, "PILOT_2_A.md", CLEAN)
    _write(tmp_path, "PILOT_2_B.md",
           "Earlier revisions quoted $4.15, which counted two pooled arms instead of three.\n")
    assert cdf.main(["--docs-dir", str(tmp_path)]) == 0


def test_every_superseded_figure_is_caught(cdf, tmp_path, capsys):
    """Neither a stale total nor a stale step cost may survive in a document."""
    _write(tmp_path, "PILOT_2_A.md", CLEAN)
    body = "\n".join(f"figure {s} appears here" for s in cdf.SUPERSEDED)
    _write(tmp_path, "PILOT_2_B.md", body + "\n")
    assert cdf.main(["--docs-dir", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    for s in cdf.SUPERSEDED:
        assert s in out, f"{s} was not reported"


def test_a_missing_canonical_figure_is_a_finding(cdf, tmp_path, capsys):
    _write(tmp_path, "PILOT_2_A.md", CLEAN.replace("~$4.70", "the current figure"))
    assert cdf.main(["--docs-dir", str(tmp_path)]) == 1
    assert "steps 0-4" in capsys.readouterr().out


def test_a_variant_spelling_is_reported_but_not_fatal(cdf, tmp_path, capsys):
    _write(tmp_path, "PILOT_2_A.md", CLEAN)
    _write(tmp_path, "PILOT_2_B.md", "At full scale the figure is ~$367.\n")
    assert cdf.main(["--docs-dir", str(tmp_path)]) == 0
    assert "note:" in capsys.readouterr().out


def test_a_missing_directory_is_an_error(cdf, tmp_path):
    assert cdf.main(["--docs-dir", str(tmp_path / "nope")]) == 2


def test_no_matching_documents_is_an_error_not_a_pass(cdf, tmp_path):
    """Silence must never read as success: an empty match set is an error."""
    _write(tmp_path, "UNRELATED.md", CLEAN)
    assert cdf.main(["--docs-dir", str(tmp_path)]) == 2


def test_the_real_documents_pass_when_they_are_present(cdf):
    docs = _REPO / "docs" / "reports"
    if not list(docs.glob("PILOT_2_*.md")):
        pytest.skip("the Pilot 2 documents live on the proposal branch")
    assert cdf.main(["--docs-dir", str(docs), "--quiet"]) == 0
