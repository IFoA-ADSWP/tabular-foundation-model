"""The positive control that gates the regressor fair test (#516; decided in #498).

A null from a pipeline that cannot learn is uninterpretable, so the fair test runs only after this
control passes. The control asserts evidence rather than a metric, because the historic "fine-tuned"
arm that executed zero steps still reported a number (#496): the weights must have moved, the
training loss must have fallen, and a fine-tuned arm must beat the raw arm on a synthetic target
with a known low-noise function, paired on identical rows, with a 95% CI excluding zero.

The library sits behind `Backend`, the only seam that imports `tabpfn`. The tests stub that seam, so
this module imports on a machine without the pinned environment.

Run it (Python 3.12 with `tabpfn==8.5.0`)::

    python src/positive_control.py --out docs/analyses/data/regressor_positive_control.json

The runner writes the result and exits non-zero when any check fails. The spec says stop on
failure; it does not say retune the control.
"""

from __future__ import annotations

import argparse
import json
import math
import platform
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Protocol

import numpy as np

SCHEMA_VERSION = 1


# ---------------------------------------------------------------------------
# Squares used by both stages. Fixed here so a run cannot quietly change them.
# ---------------------------------------------------------------------------
def overfit_frame(seed: int, n_train: int, n_test: int) -> tuple[np.ndarray, ...]:
    """A small, noisy frame used only to prove the optimiser moves the weights."""
    rng = np.random.default_rng(seed)
    X = rng.uniform(-1.0, 1.0, size=(n_train + n_test, 3))
    y = X[:, 0] * X[:, 1] + 0.1 * rng.normal(size=n_train + n_test)
    return X[:n_train], y[:n_train], X[n_train:], y[n_train:]


def known_signal_frame(seed: int, n_train: int, n_test: int) -> tuple[np.ndarray, ...]:
    """A low-noise target with a known function that raw inference underfits at this context size.

    Probe 1 (a smooth product-plus-sine at 512 rows) put the raw arm at the noise floor, leaving no
    headroom: fine-tuning can only lose there, so that target cannot serve as a control. This one
    keeps the noise low (SD 0.02) and the signal high-frequency, so a gain is possible.
    """
    rng = np.random.default_rng(seed)
    X = rng.uniform(-1.0, 1.0, size=(n_train + n_test, 3))
    y = (
        np.sin(6.0 * X[:, 0])
        + 0.5 * X[:, 1] * X[:, 2]
        + 0.02 * rng.normal(size=n_train + n_test)
    )
    return X[:n_train], y[:n_train], X[n_train:], y[n_train:]


# ---------------------------------------------------------------------------
# Configuration and results
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ControlConfig:
    """Everything the control is allowed to vary. Defaults fit the 15-minute CPU budget."""

    n_train: int = 96
    n_test: int = 256
    epochs: int = 30
    overfit_n_train: int = 256
    overfit_n_test: int = 64
    overfit_epochs: int = 30
    replicates: int = 5
    seed: int = 0
    alpha: float = 0.05
    min_parameter_delta: float = 0.0


@dataclass(frozen=True)
class FinetuneRun:
    """One fine-tune: what it predicted, its step losses, and how far its weights moved."""

    predictions: np.ndarray
    losses: tuple[float, ...]
    parameter_delta: float
    moved_tensors: int
    total_tensors: int


@dataclass(frozen=True)
class Replicate:
    seed: int
    raw_mse: float
    ft_mse: float
    relative_gain: float


@dataclass(frozen=True)
class OverfitStage:
    losses: tuple[float, ...]
    parameter_delta: float
    moved_tensors: int
    total_tensors: int
    first_fifth_loss: float
    last_fifth_loss: float
    loss_fall: float


@dataclass(frozen=True)
class SignalStage:
    replicates: tuple[Replicate, ...]
    gain_mean: float
    gain_sd: float
    ci_low: float
    ci_high: float
    degrees_of_freedom: int


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class ControlVerdict:
    checks: tuple[Check, ...]

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(check.passed for check in self.checks)


@dataclass(frozen=True)
class ControlResult:
    config: ControlConfig
    overfit: OverfitStage
    signal: SignalStage
    verdict: ControlVerdict
    environment: dict[str, str] = field(default_factory=dict)
    wall_time_seconds: float | None = None


# ---------------------------------------------------------------------------
# The library seam
# ---------------------------------------------------------------------------
class Backend(Protocol):
    """The only surface the control needs from `tabpfn`."""

    name: str
    version: str

    def fit_raw(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_test: np.ndarray,
        seed: int,
    ) -> np.ndarray:
        """Raw TabPFN, in-context, no training."""

    def run_finetune(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_test: np.ndarray,
        seed: int,
        epochs: int,
        measure_parameter_delta: bool = False,
    ) -> FinetuneRun:
        """`FinetunedTabPFNRegressor` for `epochs`, with its own loss trace."""


class _LossRecorder:
    """The trainer's public `FinetuningLogger` seam: one `log_step` per executed optimiser step."""

    def __init__(self) -> None:
        self.losses: list[float] = []

    def setup(self, config: dict) -> None:
        del config

    def log_step(self, metrics: dict[str, float], step: int) -> None:
        del step
        loss = metrics.get("train/loss")
        if loss is not None and math.isfinite(float(loss)):
            self.losses.append(float(loss))

    def log_epoch(self, metrics: dict[str, float], step: int) -> None:
        del metrics, step

    def finish(self) -> None:
        pass


class TabPFNBackend:
    """Drives the shipped regressor and trainer on the pinned v3 line."""

    name = "tabpfn"

    def __init__(
        self,
        device: str = "cpu",
        n_estimators: int = 8,
        model_version_name: str = "V3",
    ) -> None:
        import tabpfn  # noqa: PLC0415  (optional dependency; imported only when the control runs)

        self.version = tabpfn.__version__
        self.device = device
        self.n_estimators = n_estimators
        self.model_version_name = model_version_name

    def _model_version(self):
        from tabpfn.constants import ModelVersion  # noqa: PLC0415

        return getattr(ModelVersion, self.model_version_name)

    def _raw(self, seed: int):
        from tabpfn import TabPFNRegressor  # noqa: PLC0415

        # Pinned through `create_default_for_version`, which resolves the v3 checkpoint path
        # rather than accepting the package default (`auto`).
        return TabPFNRegressor.create_default_for_version(
            self._model_version(),
            device=self.device,
            n_estimators=self.n_estimators,
            random_state=seed,
        )

    def _finetuner(self, seed: int, epochs: int, logger: _LossRecorder):
        from tabpfn.finetuning.finetuned_regressor import (  # noqa: PLC0415
            FinetunedTabPFNRegressor,
        )

        return FinetunedTabPFNRegressor(
            device=self.device,
            epochs=epochs,
            random_state=seed,
            # The spec fixes the epoch budget: early stopping off, validation off, so the
            # epochs in the record are the epochs that ran.
            validation_split_ratio=0.0,
            early_stopping=False,
            n_estimators_finetune=2,
            n_estimators_validation=2,
            n_estimators_final_inference=self.n_estimators,
            model_version=self._model_version(),
            experiment_logger=logger,
        )

    @staticmethod
    def _state_dict(finetuner) -> dict[str, "np.ndarray"]:
        return {
            name: tensor.detach().cpu().numpy().copy()
            for name, tensor in finetuner.finetuned_estimator_.model_.state_dict().items()
        }

    def fit_raw(self, X_train, y_train, X_test, seed) -> np.ndarray:
        model = self._raw(seed)
        model.fit(X_train, y_train)
        return np.asarray(model.predict(X_test), dtype=float)

    def run_finetune(
        self,
        X_train,
        y_train,
        X_test,
        seed,
        epochs,
        measure_parameter_delta: bool = False,
    ) -> FinetuneRun:
        initial: dict[str, np.ndarray] | None = None
        if measure_parameter_delta:
            # A zero-epoch fit at the same seed initialises the same weights and never enters
            # the epoch loop, so it is the "before" state without patching the library.
            probe_logger = _LossRecorder()
            probe = self._finetuner(seed, 0, probe_logger)
            probe.fit(X_train, y_train)
            initial = self._state_dict(probe)

        logger = _LossRecorder()
        model = self._finetuner(seed, epochs, logger)
        model.fit(X_train, y_train)
        predictions = np.asarray(model.predict(X_test), dtype=float)

        parameter_delta = 0.0
        moved = 0
        total = 0
        if initial is not None:
            final = self._state_dict(model)
            for name, before in initial.items():
                after = final[name]
                total += 1
                if not np.array_equal(before, after):
                    moved += 1
                parameter_delta = max(parameter_delta, float(np.max(np.abs(after - before))))

        return FinetuneRun(
            predictions=predictions,
            losses=tuple(logger.losses),
            parameter_delta=parameter_delta,
            moved_tensors=moved,
            total_tensors=total,
        )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def mean_squared_error(truth: np.ndarray, predictions: np.ndarray) -> float:
    return float(np.mean((truth - predictions) ** 2))


def _fifth_mean(losses: tuple[float, ...], from_end: bool) -> float:
    if not losses:
        return float("nan")
    width = max(1, len(losses) // 5)
    window = losses[-width:] if from_end else losses[:width]
    return float(np.mean(window))


def paired_t_interval(
    gains: list[float], alpha: float
) -> tuple[float, float, float, float, int]:
    """Mean, SD and the paired t interval over replicate gains. Returns nan when undefined."""
    n = len(gains)
    if n < 2:
        nan = float("nan")
        return (float(np.mean(gains)) if gains else nan, nan, nan, nan, max(n - 1, 0))
    from scipy.stats import t as student_t  # noqa: PLC0415

    mean = float(np.mean(gains))
    sd = float(np.std(gains, ddof=1))
    df = n - 1
    half_width = float(student_t.ppf(1.0 - alpha / 2.0, df)) * sd / math.sqrt(n)
    return mean, sd, mean - half_width, mean + half_width, df


def run_control(backend: Backend, config: ControlConfig) -> ControlResult:
    started = time.monotonic()

    X_train, y_train, X_test, y_test = overfit_frame(
        config.seed, config.overfit_n_train, config.overfit_n_test
    )
    overfit_run = backend.run_finetune(
        X_train,
        y_train,
        X_test,
        seed=config.seed,
        epochs=config.overfit_epochs,
        measure_parameter_delta=True,
    )
    first_fifth = _fifth_mean(overfit_run.losses, from_end=False)
    last_fifth = _fifth_mean(overfit_run.losses, from_end=True)
    overfit = OverfitStage(
        losses=overfit_run.losses,
        parameter_delta=overfit_run.parameter_delta,
        moved_tensors=overfit_run.moved_tensors,
        total_tensors=overfit_run.total_tensors,
        first_fifth_loss=first_fifth,
        last_fifth_loss=last_fifth,
        loss_fall=first_fifth - last_fifth,
    )

    replicates: list[Replicate] = []
    for index in range(config.replicates):
        seed = config.seed + 1000 + index
        X_train, y_train, X_test, y_test = known_signal_frame(
            seed, config.n_train, config.n_test
        )
        raw_predictions = backend.fit_raw(X_train, y_train, X_test, seed=seed)
        ft_run = backend.run_finetune(
            X_train, y_train, X_test, seed=seed, epochs=config.epochs
        )
        raw_mse = mean_squared_error(y_test, raw_predictions)
        ft_mse = mean_squared_error(y_test, ft_run.predictions)
        replicates.append(
            Replicate(
                seed=seed,
                raw_mse=raw_mse,
                ft_mse=ft_mse,
                relative_gain=(raw_mse - ft_mse) / raw_mse,
            )
        )

    gains = [replicate.relative_gain for replicate in replicates]
    gain_mean, gain_sd, ci_low, ci_high, df = paired_t_interval(gains, config.alpha)
    signal = SignalStage(
        replicates=tuple(replicates),
        gain_mean=gain_mean,
        gain_sd=gain_sd,
        ci_low=ci_low,
        ci_high=ci_high,
        degrees_of_freedom=df,
    )

    result = ControlResult(
        config=config,
        overfit=overfit,
        signal=signal,
        verdict=evaluate(overfit, signal, config),
        environment={
            "python": platform.python_version(),
            "platform": platform.platform(),
            "backend": backend.name,
            "backend_version": backend.version,
            "device": getattr(backend, "device", "unknown"),
            "model_version": getattr(backend, "model_version_name", "unknown"),
        },
        wall_time_seconds=time.monotonic() - started,
    )
    return result


def evaluate(
    overfit: OverfitStage, signal: SignalStage, config: ControlConfig
) -> ControlVerdict:
    """The pre-registered pass rule: all three evidence items, each reported separately."""
    checks = [
        Check(
            name="parameter_delta",
            passed=overfit.parameter_delta > config.min_parameter_delta
            and overfit.moved_tensors > 0,
            detail=(
                f"max |dw| = {overfit.parameter_delta:.3e} over "
                f"{overfit.moved_tensors}/{overfit.total_tensors} tensors "
                f"(required > {config.min_parameter_delta:.1e} and at least one moved tensor)"
            ),
        ),
        Check(
            name="loss_fall",
            passed=math.isfinite(overfit.loss_fall) and overfit.loss_fall > 0.0,
            detail=(
                f"first-fifth mean {overfit.first_fifth_loss:.4f} -> "
                f"last-fifth mean {overfit.last_fifth_loss:.4f} "
                f"(required a fall; {len(overfit.losses)} steps logged)"
            ),
        ),
        Check(
            name="paired_gain",
            passed=math.isfinite(signal.ci_low) and signal.ci_low > 0.0,
            detail=(
                f"mean relative gain {signal.gain_mean:+.3%}, "
                f"{100 * (1 - config.alpha):.0f}% CI "
                f"[{signal.ci_low:+.3%}, {signal.ci_high:+.3%}] over "
                f"{len(signal.replicates)} replicates (df={signal.degrees_of_freedom}; "
                "required lower bound > 0)"
            ),
        ),
    ]
    return ControlVerdict(checks=tuple(checks))


# ---------------------------------------------------------------------------
# Record and CLI
# ---------------------------------------------------------------------------
def result_to_dict(result: ControlResult) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "control": "regressor_positive_control",
        "ticket": 516,
        "decision": 498,
        "spec": "docs/experiments/fair-test-freq-sev/REGRESSOR_FINETUNING_PREREGISTRATION_2026-11.md",
        "environment": result.environment,
        "config": asdict(result.config),
        "overfit": asdict(result.overfit),
        "known_signal": asdict(result.signal),
        "checks": [asdict(check) for check in result.verdict.checks],
        "passed": result.verdict.passed,
        "wall_time_seconds": result.wall_time_seconds,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True, help="where to write result.json")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--replicates", type=int, default=ControlConfig.replicates)
    parser.add_argument("--epochs", type=int, default=ControlConfig.epochs)
    parser.add_argument("--n-train", type=int, default=ControlConfig.n_train)
    parser.add_argument("--n-test", type=int, default=ControlConfig.n_test)
    parser.add_argument("--seed", type=int, default=ControlConfig.seed)
    args = parser.parse_args(argv)

    config = ControlConfig(
        n_train=args.n_train,
        n_test=args.n_test,
        epochs=args.epochs,
        replicates=args.replicates,
        seed=args.seed,
    )
    result = run_control(TabPFNBackend(device=args.device), config)
    payload = result_to_dict(result)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n")

    print(
        f"positive control {'PASSED' if result.verdict.passed else 'FAILED'} "
        f"in {payload['wall_time_seconds']:.0f}s -> {args.out}"
    )
    for check in result.verdict.checks:
        print(f"  [{'pass' if check.passed else 'FAIL'}] {check.name}: {check.detail}")
    return 0 if result.verdict.passed else 1


if __name__ == "__main__":
    sys.exit(main())
