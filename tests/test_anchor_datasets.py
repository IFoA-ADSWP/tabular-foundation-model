"""`src/anchor_datasets.py`: the four anchors, as the pilot declares them.

D1 and D2 both say "the four anchor datasets", so this pins the wiring that lets them agree: the
names are the pilot's own, the files sit under `data/raw/`, and every target is a real column in
the bytes. The last check is the one that earns the file — a renamed column would otherwise surface
as a `KeyError` ten minutes into a CPU-bound run rather than in a second.

Run:  python -m pytest tests/test_anchor_datasets.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from anchor_datasets import load_anchor_datasets  # noqa: E402  (after the src path insert)

# Written out rather than derived from the loader: a test that reads the same declaration it is
# checking cannot notice the declaration changing.
EXPECTED = {
    "coil2000": ("coil2000.csv", "CARAVAN"),
    "uslapseagent": ("uslapseagent.csv", "surrender"),
    "eudirectlapse": ("eudirectlapse.csv", "lapse"),
    "spanish_motor_lapse": ("spanish_motor_lapse.csv", "LapseB"),
}


def test_the_anchors_are_the_pilot_declared_ones():
    registry = load_anchor_datasets()

    assert set(registry) == set(EXPECTED)
    for name, (file, target) in EXPECTED.items():
        assert registry[name]["file"] == REPO_ROOT / "data" / "raw" / file
        assert registry[name]["target"] == target


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_every_anchor_has_its_file_and_its_target_column(name):
    entry = load_anchor_datasets()[name]

    assert entry["file"].exists(), f"{name}: {entry['file']} is not on disk"
    header = pd.read_csv(entry["file"], nrows=0).columns
    assert entry["target"] in header, f"{name}: no {entry['target']!r} column in {entry['file'].name}"


def test_a_runner_that_cannot_be_loaded_refuses(tmp_path):
    with pytest.raises(SystemExit, match="cannot load the anchor datasets"):
        load_anchor_datasets(tmp_path / "not_the_runner.py")
