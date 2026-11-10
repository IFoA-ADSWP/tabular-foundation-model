"""The positive control's pass rule (#516, decided in #498).

The backend is stubbed at the module's only library seam: these tests are about what the control
accepts as evidence, not about loading 233 MB of weights. The historic failure the control exists
for — a zero-step arm that still reported a number (#496) — is one of the cases below.
"""

from __future__ import annotations

import json

import numpy as np

import positive_control as pc


def _known_signal_truth(X: np.ndarray) -> np.ndarray:
    return np.sin(6.0 * X[:, 0]) + 0.5 * X[:, 1] * X[:, 2]


class FakeBackend:
    """A backend whose errors are set by the test, so each check can be driven in isolation."""

    name = "fake"
    version = "0.0-test"

    def __init__(
        self,
        *,
        parameter_delta: float = 0.5,
        moved_tensors: int = 3,
        total_tensors: int = 3,
        losses: tuple[float, ...] = (1.0, 0.9, 0.7, 0.5, 0.4, 0.3, 0.2, 0.15),
        raw_error: float = 0.3,
        ft_errors: tuple[float, ...] = (-0.03, -0.03, -0.03, -0.03, -0.03),
    ) -> None:
        self.parameter_delta = parameter_delta
        self.moved_tensors = moved_tensors
        self.total_tensors = total_tensors
        self.losses = losses
        self.raw_error = raw_error
        self.ft_errors = ft_errors
        self._ft_calls = 0

    def fit_raw(self, X_train, y_train, X_test, seed):  # noqa: ARG002
        return _known_signal_truth(X_test) + self.raw_error

    def run_finetune(
        self,
        X_train,  # noqa: ARG002
        y_train,  # noqa: ARG002
        X_test,
        seed,  # noqa: ARG002
        epochs,  # noqa: ARG002
        measure_parameter_delta=False,
    ):
        # The overfit stage runs first; it consumes no replicate error.
        if measure_parameter_delta:
            error = 0.0
        else:
            error = self.ft_errors[self._ft_calls % len(self.ft_errors)]
            self._ft_calls += 1
        return pc.FinetuneRun(
            predictions=_known_signal_truth(X_test) + error,
            losses=self.losses,
            parameter_delta=self.parameter_delta if measure_parameter_delta else 0.0,
            moved_tensors=self.moved_tensors if measure_parameter_delta else 0,
            total_tensors=self.total_tensors if measure_parameter_delta else 0,
        )


CONFIG = pc.ControlConfig(replicates=5)


def _run(backend: FakeBackend) -> pc.ControlResult:
    return pc.run_control(backend, CONFIG)


def _check(result: pc.ControlResult, name: str) -> pc.Check:
    return next(check for check in result.verdict.checks if check.name == name)


def test_all_three_checks_pass_when_weights_move_loss_falls_and_gain_ci_excludes_zero():
    result = _run(FakeBackend())

    assert result.verdict.passed, [check.detail for check in result.verdict.checks]
    assert {check.name for check in result.verdict.checks} == {
        "parameter_delta",
        "loss_fall",
        "paired_gain",
    }


def test_zero_step_run_fails_even_with_a_falling_loss_and_a_gain():
    """The AUS Auto failure: weights unchanged, a metric still produced."""
    result = _run(FakeBackend(parameter_delta=0.0, moved_tensors=0))

    assert not result.verdict.passed
    assert not _check(result, "parameter_delta").passed
    assert _check(result, "loss_fall").passed
    assert _check(result, "paired_gain").passed


def test_unmoved_weights_fail_the_parameter_check():
    result = _run(FakeBackend(moved_tensors=0))

    assert not _check(result, "parameter_delta").passed


def test_rising_loss_fails_the_loss_check():
    result = _run(FakeBackend(losses=(0.2, 0.3, 0.5, 0.7, 0.9, 1.1, 1.3, 1.5)))

    assert not _check(result, "loss_fall").passed
    assert not result.verdict.passed


def test_no_logged_steps_fail_the_loss_check():
    result = _run(FakeBackend(losses=()))

    assert not _check(result, "loss_fall").passed


def test_gain_ci_including_zero_fails_even_with_a_positive_mean():
    # Errors straddle the raw arm, so the replicate gains disagree in sign.
    result = _run(
        FakeBackend(raw_error=0.10, ft_errors=(0.06, 0.14, 0.07, 0.13, 0.10))
    )

    assert not _check(result, "paired_gain").passed
    assert _check(result, "paired_gain").detail.find("lower bound > 0") > 0
    assert not result.verdict.passed


def test_a_single_replicate_cannot_form_an_interval():
    config = pc.ControlConfig(replicates=1)
    result = pc.run_control(FakeBackend(ft_errors=(0.01,)), config)

    assert not _check(result, "paired_gain").passed
    assert not result.verdict.passed


def test_result_records_every_parameter_the_run_used():
    result = _run(FakeBackend())
    payload = pc.result_to_dict(result)

    recorded = payload["config"]
    assert recorded["epochs"] == CONFIG.epochs
    assert recorded["replicates"] == CONFIG.replicates
    assert recorded["n_train"] == CONFIG.n_train
    assert recorded["overfit_epochs"] == CONFIG.overfit_epochs
    assert payload["environment"]["backend"] == "fake"
    assert payload["passed"] is True
    assert [check["name"] for check in payload["checks"]] == [
        "parameter_delta",
        "loss_fall",
        "paired_gain",
    ]


def test_cli_writes_the_result_and_exits_nonzero_on_failure(tmp_path, monkeypatch):
    failing = FakeBackend(parameter_delta=0.0, moved_tensors=0)
    monkeypatch.setattr(pc, "TabPFNBackend", lambda **kwargs: failing)
    out = tmp_path / "result.json"

    code = pc.main(["--out", str(out), "--replicates", "5"])

    assert code == 1
    payload = json.loads(out.read_text())
    assert payload["passed"] is False
    assert payload["schema_version"] == pc.SCHEMA_VERSION


def test_cli_exits_zero_on_pass(tmp_path, monkeypatch):
    monkeypatch.setattr(pc, "TabPFNBackend", lambda **kwargs: FakeBackend())
    out = tmp_path / "result.json"

    assert pc.main(["--out", str(out), "--replicates", "5"]) == 0
    assert json.loads(out.read_text())["passed"] is True
