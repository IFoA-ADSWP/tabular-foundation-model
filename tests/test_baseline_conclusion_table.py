"""The conclusion's table is generated, and this fails when the document drifts (#631)."""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/analyses/baseline_conclusion.py"
TABLE = REPO / "docs/experiments/baseline-conclusion-2026-11/TABLE.md"


def test_committed_table_matches_the_generator():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--check", str(TABLE)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout
