"""The calibration analysis recovers a slope it is told (#745).

Synthetic outcomes are drawn from a known logistic model of the predicted probability, so the slope is
1 by construction; rescaling the logit then moves it away from 1 by a known factor. The test asserts the
script recovers both.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/analyses/calibration.py"


def _module():
    spec = importlib.util.spec_from_file_location("calibration_for_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _draw(scale: float, n: int = 40_000, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Probabilities whose logit is true, then outcomes drawn from them."""
    rng = np.random.default_rng(seed)
    latent = rng.normal(0.0, 1.5, n)
    p = 1.0 / (1.0 + np.exp(-latent))
    y = rng.binomial(1, p).astype(float)
    # The model is told a distorted probability: its logit is `scale` times the true one.
    told = 1.0 / (1.0 + np.exp(-scale * latent))
    return told, y


def test_a_calibrated_forecast_has_slope_one():
    cal = _module()
    told, y = _draw(scale=1.0)
    slope, intercept = cal.slope_intercept(told, y)
    assert slope == pytest.approx(1.0, abs=0.05)
    assert intercept == pytest.approx(0.0, abs=0.05)


def test_an_overconfident_forecast_has_slope_below_one():
    cal = _module()
    told, y = _draw(scale=2.0)
    slope, _ = cal.slope_intercept(told, y)
    assert slope < 0.8


def test_deciles_cover_every_row_and_stay_ordered():
    cal = _module()
    told, y = _draw(scale=1.0, n=5_000)
    rows = cal.deciles(told, y)
    assert len(rows) == cal.DECILES
    assert sum(r["n"] for r in rows) == y.size
    predicted = [r["predicted"] for r in rows]
    assert predicted == sorted(predicted)


def test_a_missing_capture_names_the_file(tmp_path):
    cal = _module()
    with pytest.raises(SystemExit, match="no committed capture"):
        cal.load("not_a_target", predictions=tmp_path)
