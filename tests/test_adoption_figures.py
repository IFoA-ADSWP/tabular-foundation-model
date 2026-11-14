"""The adoption figures must not drift from the frontier CSVs (#609).

Both figures restate claims the documents make in prose — parity at small size, drift at scale, a
certain number of methods winning on a certain number of datasets. Those claims are arithmetic over
committed CSVs, so the tests recompute them from the same source the figure reads. A caption that
overstates the evidence fails here rather than in front of a reader.

The one claim this suite deliberately contradicts is the old "ratio ≥1.03" note: recomputed,
`ausprivauto0405` is off-frontier at 1.003. The test pins the true range so the stale sentence cannot
come back.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "infra" / "adoption_figures.py"


@pytest.fixture(scope="module")
def figures(load_script):
    return load_script("adoption_figures", SCRIPT)


@pytest.fixture(scope="module")
def points(figures):
    return figures.frontier_points()


def test_the_registry_gives_twelve_datasets(points):
    """Twelve, not the eighteen CSVs: the directory also holds per-seed reruns, which are not datasets."""
    assert len(points) == 12
    assert len({point.dataset for point in points}) == 12


def test_seven_datasets_are_on_the_parsimony_frontier(points):
    """`regime_characterization.md` states 7 of 12; the figure colours exactly those."""
    assert sum(point.on_frontier for point in points) == 7


def test_every_off_frontier_dataset_is_at_scale(figures, points):
    """The size half of the old claim holds: the smallest off-frontier dataset is 53,502 rows."""
    off = [point for point in points if not point.on_frontier]

    assert len(off) == 5
    assert min(point.n_rows for point in off) == 53_502


def test_the_off_frontier_ratios_span_a_calibration_tie_to_a_dominance(figures, points):
    """The ratio half of the old claim does **not** hold, and this is where that is recorded.

    `ausprivauto0405` is off-frontier at 1.003 — a tie at seven parameters, not a loss at 1.03 or worse.
    """
    off = [point for point in points if not point.on_frontier]
    ratios = sorted(point.ratio for point in off)

    assert ratios[0] == pytest.approx(1.003, abs=1e-3)
    assert ratios[-1] == pytest.approx(1.502, abs=1e-3)


def test_tabpfn_is_the_single_best_method_on_five_datasets(figures, points):
    """Exact ties only. `bemtl97` (1.003) and `norauto` (1.006) are on the frontier but not the best.

    LGBM is the best method on six of the twelve and a seven-parameter logistic GLM on one; the figure
    does not claim TabPFN wins the metric everywhere, only that it stays on the parsimony frontier.
    """
    assert sum(point.ratio == pytest.approx(1.0, abs=1e-12) for point in points) == 5
    best = {point.dataset: point.best_method for point in points}
    assert sum(method == "lgbm" for method in best.values()) == 6
    assert best["ausprivauto0405"] == "logisticglm"


def test_the_tie_is_a_seven_parameter_glm(figures):
    """The caption quotes the parameter count, so the count is checked rather than assumed.

    The first draft said 21 — the count of the Poisson and OLS arms — while `logisticglm` here has
    seven. A quoted number that no test reads is how that kind of error ships.
    """
    table = pd.read_csv(
        figures.BENCHMARK / "frontier_results_ausprivauto0405.csv"
    ).set_index("method")

    assert int(table.loc["logisticglm", "n_params"]) == 7
    assert int(table.loc["tabpfn", "n_params"]) == 10_000_000


def test_the_sweep_is_nine_cells_and_tabpfn_wins_eight(figures):
    """`regime_characterization.md` §1: TabPFN wins 8/9 cells; the loss is `bemtl97` at full size."""
    sweep = figures.sweep_cells()

    assert len(sweep) == 9
    assert int((sweep["ratio"] - 1.0).abs().lt(1e-12).sum()) == 8
    loss = sweep.loc[sweep["ratio"].idxmax()]
    assert loss["dataset"] == "bemtl97"
    assert loss["ratio"] == pytest.approx(1.003, abs=1e-3)


def test_the_matrix_is_the_union_of_methods_with_honest_gaps(figures, points):
    """Regression rows have no logistic model and classification rows have no OLS — a gap, not a zero."""
    matrix = figures.method_matrix(points)
    columns = {method: matrix[:, index] for index, method in enumerate(figures.METHOD_ORDER)}

    assert matrix.shape == (12, len(figures.METHOD_ORDER))
    # TabPFN's column is its own relative performance, row by row — not a column of ones.
    assert np.allclose(columns["tabpfn"], [point.ratio for point in points])
    # Every row is a ratio to its own best, so each row bottoms out at 1.0.
    assert np.allclose(np.nanmin(matrix, axis=1), 1.0)
    assert np.isnan(columns["ols"]).sum() == 6
    assert np.isnan(columns["logisticglm"]).sum() == 6
    assert np.isnan(columns["lr"]).sum() == 6
    assert not np.isnan(columns["lgbm"]).any()
    # Every populated cell is at least 1.0: it is a ratio to the row's own best.
    assert np.nanmin(matrix) == pytest.approx(1.0)


def test_the_cli_exports_both_pairs_and_is_deterministic(tmp_path, figures):
    """A diff in a committed figure must mean the picture changed, not that it was redrawn."""
    first, second = tmp_path / "first", tmp_path / "second"
    assert figures.main(["--only", "both", "--out", str(first)]) == 0
    assert figures.main(["--only", "both", "--out", str(second)]) == 0
    plt.close("all")

    for stem in ("tabpfn_size_drift", "frontier_method_matrix"):
        for suffix in (".pdf", ".png"):
            one = (first / f"{stem}{suffix}").read_bytes()
            two = (second / f"{stem}{suffix}").read_bytes()
            assert one == two
            assert len(one) > 1_000
