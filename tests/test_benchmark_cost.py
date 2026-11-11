"""The fair test's cost model (#526).

The benchmark fit itself is the paid step and is not exercised here: these tests hold the
extrapolation, the ceiling rule and the refusals that stop a modelled number being quoted as a
measured one.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

import benchmark_cost as bc

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "benchmarks" / "benchmark_regressor_fit.py"


@pytest.fixture(scope="module")
def cli():
    spec = importlib.util.spec_from_file_location("benchmark_regressor_fit", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["benchmark_regressor_fit"] = module
    spec.loader.exec_module(module)
    return module


MEASUREMENT = bc.Measurement(
    wall_seconds=600.0,
    rows=10_000,
    epochs=30,
    device="cuda",
    tabpfn_version="8.5.0",
    frame="freMTPL2freq:ClaimNb",
)


def _fit(arm: str) -> bc.Fit:
    return next(fit for fit in bc.MATRIX if fit.arm == arm)


def test_matrix_counts_are_the_pre_registered_design():
    counts = {fit.arm: fit.n_fits for fit in bc.MATRIX}

    assert counts == {
        "A_raw": 45,  # 3 targets x 5 folds x 3 seeds
        "B_ft30": 45,
        "B_ft10": 45,
        "B_ft3": 45,
        "X_log1p": 15,  # ClaimNb only
        "S_50k": 45,
        "D_exposure": 15,  # ClaimNb only
    }
    assert sum(counts.values()) == 255


def test_epoch_scaling_keeps_a_fixed_share():
    # 600 s measured at 30 epochs; 20% is fixed, the rest is linear in epochs.
    assert bc.fit_seconds(MEASUREMENT, _fit("B_ft30")) == pytest.approx(600.0)
    assert bc.fit_seconds(MEASUREMENT, _fit("B_ft10")) == pytest.approx(120.0 + 160.0)
    assert bc.fit_seconds(MEASUREMENT, _fit("B_ft3")) == pytest.approx(120.0 + 48.0)


def test_row_scaling_is_linear_in_the_per_epoch_part():
    at_10k = bc.fit_seconds(MEASUREMENT, _fit("B_ft30"))
    at_50k = bc.fit_seconds(MEASUREMENT, _fit("S_50k"))
    fixed = bc.FIXED_OVERHEAD_FRACTION * MEASUREMENT.wall_seconds

    assert (at_50k - fixed) / (at_10k - fixed) == pytest.approx(5.0)


def test_raw_is_costed_at_the_full_measured_rate():
    assert bc.fit_seconds(MEASUREMENT, _fit("A_raw")) == pytest.approx(
        MEASUREMENT.wall_seconds
    )


def test_estimate_totals_the_matrix_and_fits_the_ceiling():
    est = bc.estimate(MEASUREMENT, rate_per_hour=0.29)

    assert est.total_fits == 255
    assert est.within_ceiling is True
    assert est.compute_usd == pytest.approx(est.total_gpu_hours * 0.29)
    assert est.total_usd == pytest.approx(est.compute_usd + est.cold_start_usd)
    assert est.headroom_usd == pytest.approx(est.ceiling_usd - est.total_usd)


def test_a_slow_measurement_puts_the_estimate_over_the_ceiling():
    est = bc.estimate(MEASUREMENT, rate_per_hour=1.0)

    assert est.within_ceiling is False
    assert est.headroom_usd < 0
    assert est.total_usd > est.ceiling_usd


def test_assumptions_are_named_not_implied():
    est = bc.estimate(MEASUREMENT, rate_per_hour=0.29)
    text = " ".join(est.assumptions)

    assert "S_50k" in text
    assert "linear in rows" in text
    assert "upper bound" in text


def test_a_zero_fit_is_not_a_measurement():
    with pytest.raises(ValueError):
        bc.Measurement(
            wall_seconds=0.0,
            rows=10_000,
            epochs=30,
            device="cuda",
            tabpfn_version="8.5.0",
            frame="freMTPL2freq:ClaimNb",
        )


def test_a_non_positive_rate_is_refused():
    with pytest.raises(ValueError):
        bc.estimate(MEASUREMENT, rate_per_hour=0.0)


def test_the_record_round_trips_through_json():
    est = bc.estimate(MEASUREMENT, rate_per_hour=0.29)
    payload = json.loads(json.dumps(est.to_dict()))

    assert payload["measurement"]["wall_seconds"] == 600.0
    assert payload["totals"]["fits"] == 255
    assert payload["totals"]["within_ceiling"] is True
    assert [arm["arm"] for arm in payload["arms"]][1] == "B_ft30"


def test_the_regressor_checkpoint_is_fetched_before_the_clock_starts(cli, monkeypatch, tmp_path):
    """The bootstrap preflight warms the CLASSIFIER file; the regressor has its own.

    On a cold rented box a download inside `fit()` would be timed, and the "fit time" would be
    mostly network. This holds the control flow either side of that line: fetch once on a miss,
    and do nothing on a warm cache.
    """
    import types

    pytest.importorskip("tabpfn")
    target = tmp_path / "tabpfn-v3-regressor-v3_default.ckpt"
    downloads = []

    fake = types.ModuleType("tabpfn.model_loading")
    fake.resolve_model_path = lambda *a, **k: ([target], [tmp_path], [target.name], "regressor")

    def fake_download(path, **kwargs):
        downloads.append((path, kwargs))
        path.write_bytes(b"checkpoint")
        return "ok"

    fake.download_model = fake_download
    monkeypatch.setitem(sys.modules, "tabpfn.model_loading", fake)

    cold = cli.ensure_regressor_weights()
    assert cold == {"checkpoint": target.name, "downloaded": True}
    assert len(downloads) == 1
    assert downloads[0][1]["which"] == "regressor"

    warm = cli.ensure_regressor_weights()
    assert warm == {"checkpoint": target.name, "downloaded": False}
    assert len(downloads) == 1, "a cached checkpoint was downloaded again inside the timing region"


def _write_measurement(path: Path, wall_seconds: float = 600.0) -> Path:
    path.write_text(
        json.dumps(
            {
                "schema_version": bc.SCHEMA_VERSION,
                "kind": "benchmark_fit",
                "measurement": {
                    "wall_seconds": wall_seconds,
                    "rows": 10_000,
                    "epochs": 30,
                    "device": "cuda",
                    "tabpfn_version": "8.5.0",
                    "frame": "freMTPL2freq:ClaimNb",
                    "seed": 42,
                },
            }
        )
    )
    return path


def test_estimate_without_a_measurement_is_refused(cli, tmp_path):
    with pytest.raises(SystemExit) as raised:
        cli.main(["--estimate", "--out", str(tmp_path / "cost.json"), "--rate-per-hour", "0.29"])

    assert raised.value.code == 2


def test_estimate_exits_zero_and_writes_the_record_within_ceiling(cli, tmp_path):
    measurement = _write_measurement(tmp_path / "measurement.json")
    out = tmp_path / "cost.json"

    code = cli.main(
        [
            "--estimate",
            "--measurement",
            str(measurement),
            "--rate-per-hour",
            "0.29",
            "--out",
            str(out),
        ]
    )

    assert code == 0
    payload = json.loads(out.read_text())
    assert payload["totals"]["within_ceiling"] is True
    assert payload["ceiling_usd"] == bc.CEILING_USD


def test_estimate_exits_nonzero_over_the_ceiling(cli, tmp_path):
    measurement = _write_measurement(tmp_path / "measurement.json")
    out = tmp_path / "cost.json"

    code = cli.main(
        [
            "--estimate",
            "--measurement",
            str(measurement),
            "--rate-per-hour",
            "1.0",
            "--ceiling",
            "20",
            "--out",
            str(out),
        ]
    )

    assert code == 1
    payload = json.loads(out.read_text())
    assert payload["totals"]["within_ceiling"] is False
    assert payload["ceiling_usd"] == 20.0


def test_a_foreign_record_is_not_a_measurement(cli, tmp_path):
    foreign = tmp_path / "foreign.json"
    foreign.write_text(json.dumps({"kind": "something_else"}))

    with pytest.raises(ValueError):
        cli.load_measurement(foreign)
