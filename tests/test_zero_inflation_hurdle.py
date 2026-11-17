"""The zero-inflation study's hurdle extension (#159): the arithmetic, the GLMs, and the sweep's routing.

The hurdle arithmetic is numpy only and always runs. The GLM tests need statsmodels, which the lock
does not carry (the sweep runs in its own environment), so they skip without it. Nothing here calls
the hosted client: the TabPFN hurdle's distribution is exercised through the same helpers with a
known continuous distribution standing in for the regressor.
"""

import importlib.util
import pathlib
import sys

import numpy as np
import pytest
from scipy.stats import norm

STUDY = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "eval" / "zero_inflation"


def _load(name):
    spec = importlib.util.spec_from_file_location(f"zero_inflation_{name}", STUDY / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


hurdle = _load("hurdle")
dgp = _load("dgp")


def test_hurdle_pmf_puts_the_zero_mass_on_the_binary_part():
    p_pos = np.array([0.3, 0.9])
    out = hurdle.hurdle_log_pmf(p_pos, np.array([np.nan, np.nan]), np.array([0, 0]))
    assert np.allclose(np.exp(out), 1.0 - p_pos)


def test_a_continuous_count_part_renormalised_above_one_half_sums_to_one():
    # A normal centred near 1 puts real mass below 1/2: exactly the case the renormalisation is for.
    loc, scale, p_pos = 1.2, 2.0, 0.4
    ks = np.arange(0, 200)
    cdf = lambda v: norm.cdf(v, loc, scale)  # noqa: E731
    log_trunc = hurdle.truncated_interval_log_mass(cdf(ks + 0.5), cdf(ks - 0.5), np.full(len(ks), cdf(0.5)))
    total = np.exp(hurdle.hurdle_log_pmf(np.full(len(ks), p_pos), log_trunc, ks)).sum()
    assert total == pytest.approx(1.0, abs=1e-9)


def test_midpoint_quantiles_give_the_truncated_mean():
    loc, scale = 1.2, 2.0
    levels = hurdle.truncation_quantile_levels(np.array([norm.cdf(0.5, loc, scale)]), 2000)
    estimate = norm.ppf(levels, loc, scale).mean()
    a = (0.5 - loc) / scale
    exact = loc + scale * norm.pdf(a) / norm.sf(a)
    assert estimate == pytest.approx(exact, rel=1e-3)


def test_the_smoothed_rate_stays_inside_zero_and_one():
    assert 0.0 < hurdle.smoothed_positive_rate(np.ones(1000)) < 1.0
    assert 0.0 < hurdle.smoothed_positive_rate(np.zeros(1000)) < 1.0


def test_cells_come_out_in_the_committed_order():
    cells = list(dgp.draw_cells(0, [0.0, 0.5], 1.0, 50, 50))
    assert [(arm, pi0) for arm, pi0, _ in cells] == [("baseline", dgp.BASELINE_PI0), ("zip", 0.0), ("zip", 0.5)]
    again = list(dgp.draw_cells(0, [0.0, 0.5], 1.0, 50, 50))
    for (_, _, a), (_, _, b) in zip(cells, again):
        assert np.array_equal(a["y_train"], b["y_train"]) and np.array_equal(a["y_test"], b["y_test"])


@pytest.fixture
def models(monkeypatch):
    pytest.importorskip("statsmodels")
    pytest.importorskip("tabpfn_client")
    monkeypatch.syspath_prepend(str(STUDY))
    for name in ("models", "hurdle", "dgp", "metrics"):
        monkeypatch.delitem(sys.modules, name, raising=False)
    import models as module

    return module


@pytest.fixture
def zip_cell():
    cells = dict(((arm, pi0), cell) for arm, pi0, cell in dgp.draw_cells(3, [0.5], 2.0, 1000, 200))
    return cells[("zip", 0.5)]


@pytest.mark.parametrize("cls_name", ["HurdlePoissonGLM", "HurdleNbGLM"])
def test_a_hurdle_glm_is_a_distribution(models, zip_cell, cls_name):
    m = getattr(models, cls_name)().fit(zip_cell["x_glm_train"], zip_cell["y_train"])
    x = zip_cell["x_glm_test"].iloc[:3]
    ks = np.arange(0, 20000)
    for i in range(len(x)):
        rows = x.iloc[[i] * len(ks)]
        pmf = np.exp(m.log_pmf_at(rows, ks))
        assert pmf.sum() == pytest.approx(1.0, abs=1e-6)
        assert pmf[0] == pytest.approx(m.p_zero(x.iloc[[i]])[0])
        assert (ks * pmf).sum() == pytest.approx(m.mean(x.iloc[[i]])[0], rel=1e-4)
    assert not m.binary_fallback


def test_a_one_class_training_set_falls_back_to_a_constant_rate(models, zip_cell):
    y = np.maximum(zip_cell["y_train"], 1)
    m = models.HurdlePoissonGLM().fit(zip_cell["x_glm_train"], y)
    assert m.binary_fallback
    p = m.p_zero(zip_cell["x_glm_test"])
    assert np.all(p == p[0]) and 0.0 < p[0] < 0.01


def test_the_sweep_keeps_hurdle_rows_out_of_the_committed_file(models):
    run_sweep = _load("run_sweep")
    assert {run_sweep.results_file(m) for m in run_sweep.ORIGINAL_MODELS} == {"results.csv"}
    assert {run_sweep.results_file(m) for m in run_sweep.HURDLE_MODELS} == {"results_hurdle.csv"}
    assert "tabpfn_recheck" not in run_sweep.DEFAULT_MODELS
