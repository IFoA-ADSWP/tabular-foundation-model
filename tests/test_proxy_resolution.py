"""The proxy resolution tool measures a cell's paired half-width offline (#444).

Seam: the script's command line and its printed summary. The fixture is synthetic, so the test
does not depend on a committed CSV or on the Spanish numbers; the pre-registration quotes the
real command separately.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "analyses" / "proxy_resolution.py"


def _table(path: Path, rows: int = 200) -> Path:
    rng = np.random.default_rng(7)
    signal = rng.normal(size=rows)
    frame = pd.DataFrame(
        {
            "signal": signal,
            "noise": rng.normal(size=rows),
            "leak": rng.normal(size=rows),
            "target": (signal + rng.normal(scale=0.5, size=rows) > 0).astype(int),
        }
    )
    frame.to_csv(path, index=False)
    return path


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, cwd=REPO
    )


def test_it_prints_a_half_width_for_each_seed(tmp_path):
    csv = _table(tmp_path / "table.csv")

    result = _run(
        "--csv", str(csv), "--target", "target", "--drop", "leak",
        "--train", "100", "--test", "50", "--seeds", "7,8", "--resamples", "100",
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.count("seed ") == 2
    assert "median half-width" in result.stdout and "max" in result.stdout


def test_the_same_inputs_print_the_same_bytes(tmp_path):
    csv = _table(tmp_path / "table.csv")
    args = (
        "--csv", str(csv), "--target", "target",
        "--train", "100", "--test", "50", "--seeds", "7", "--resamples", "100",
    )

    assert _run(*args).stdout == _run(*args).stdout


def test_a_named_column_that_is_absent_is_refused(tmp_path):
    csv = _table(tmp_path / "table.csv")

    result = _run(
        "--csv", str(csv), "--target", "target", "--drop", "not_a_column",
        "--train", "100", "--test", "50", "--seeds", "7", "--resamples", "100",
    )

    assert result.returncode == 1
    assert "not in the table" in result.stderr
