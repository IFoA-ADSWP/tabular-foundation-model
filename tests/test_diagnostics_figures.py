"""The D2 agreement figure must not drift from the exported table (#610).

The figure restates three readings the data dictionary defines in prose, so the tests recompute them
from `docs/analyses/data/d2_importance.csv` — the committed, hash-checked export — and pin the values
the caption quotes. The at-chance flag is tested as well as drawn: a ranking of noise must never be
presented as a ranking of signal.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pytest  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "infra" / "diagnostics_figures.py"


@pytest.fixture(scope="module")
def figures(load_script):
    return load_script("diagnostics_figures", SCRIPT)


@pytest.fixture(scope="module")
def readings(figures):
    return {reading.dataset: reading for reading in figures.agreements()}


def test_every_dataset_and_family_pair_is_present(readings):
    assert set(readings) == {
        "coil2000",
        "eudirectlapse",
        "spanish_motor_lapse",
        "uslapseagent",
    }
    for reading in readings.values():
        assert len(reading.overlap) == 3
        assert len(reading.correlation) == 3


def test_uslapseagent_top_ten_overlap_is_forced_by_its_width(figures, readings):
    """The dataset has exactly ten features, so every top ten is the whole set and 1.00 is tautological.

    The figure must not read as agreement without that caveat, and neither must this test: the rank
    correlation is the reading with content here, so it is what the assertion carries.
    """
    table = figures.load_table()
    assert table[table["dataset"] == "uslapseagent"]["feature"].nunique() == 10

    reading = readings["uslapseagent"]
    assert all(overlap == pytest.approx(1.0) for overlap in reading.overlap.values())
    assert all(0.55 <= value <= 0.73 for value in reading.correlation.values())
    assert reading.at_chance == frozenset()


def test_eudirectlapse_lgbm_is_flagged_as_noise(readings):
    """Its own test AUC is 0.494, so its ranking describes the measurement's error, not the dataset."""
    reading = readings["eudirectlapse"]

    assert reading.at_chance == frozenset({"lgbm"})
    # The GLM and the LGBM order features almost independently.
    assert reading.correlation[("glm", "lgbm")] == pytest.approx(0.02, abs=0.05)


def test_coil2000_is_the_dataset_where_the_families_disagree_most(readings):
    """TabPFN and the GLM share two features of an eighteen-feature union."""
    reading = readings["coil2000"]

    assert reading.overlap[("tabpfn", "glm")] == pytest.approx(2 / 18, abs=1e-9)
    assert reading.overlap[("tabpfn", "glm")] < 0.2


def test_overlaps_are_jaccard_indices_and_correlations_are_bounded(readings):
    for reading in readings.values():
        for value in reading.overlap.values():
            assert 0.0 <= value <= 1.0
        for value in reading.correlation.values():
            assert -1.0 <= value <= 1.0


def test_the_cli_exports_a_deterministic_pair(tmp_path, figures):
    first, second = tmp_path / "first", tmp_path / "second"
    assert figures.main(["--out", str(first)]) == 0
    assert figures.main(["--out", str(second)]) == 0
    plt.close("all")

    for suffix in (".pdf", ".png"):
        one = (first / f"diagnostics_feature_agreement{suffix}").read_bytes()
        two = (second / f"diagnostics_feature_agreement{suffix}").read_bytes()
        assert one == two
        assert len(one) > 1_000
