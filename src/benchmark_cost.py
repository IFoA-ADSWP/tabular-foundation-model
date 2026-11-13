"""What the regressor fair test will cost, from one measured fit (#526).

The pre-registration funds the fair test only if a measured benchmark sits inside a ceiling. This
module is the cost model, not the benchmark: it turns a single measured fine-tune (10,000 rows, 30
epochs) into the full matrix of Arms x folds x model seeds x epochs plus the 50k sensitivity, and
refuses to do it without a measurement.

No `tabpfn`, no GPU, no network: the model is importable and testable in CI. The measurement itself
lives in `scripts/benchmarks/benchmark_regressor_fit.py`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

SCHEMA_VERSION = 1

CEILING_USD = 50.0
BENCHMARK_ROWS = 10_000
BENCHMARK_EPOCHS = 30
FOLDS = 5
SEEDS = 3

# A three-epoch fit is not a tenth of a thirty-epoch fit: model load and final inference do not
# scale with epochs. The measured point is 30 epochs, so a fixed share is separated out; the
# fraction is an assumption and is printed with every estimate.
FIXED_OVERHEAD_FRACTION = 0.2

# A cold machine re-pulls weights; the cost page measured about $0.05 per attempt. Reported apart
# from the science so neither number hides the other.
COLD_START_USD = 0.05

TARGETS = ("claimnb", "severity", "vehvalue")
CLAIMNB_ONLY = ("claimnb",)


@dataclass(frozen=True)
class Fit:
    """One arm of the fair test, and how many fits it is."""

    arm: str
    targets: tuple[str, ...]
    epochs: int = BENCHMARK_EPOCHS
    rows: int = BENCHMARK_ROWS
    folds: int = FOLDS
    seeds: int = SEEDS
    kind: Literal["raw", "finetune"] = "finetune"

    @property
    def n_fits(self) -> int:
        return len(self.targets) * self.folds * self.seeds


# Fixed from `docs/experiments/fair-test-freq-sev/REGRESSOR_FINETUNING_PREREGISTRATION_2026-11.md` §"Design".
# `S_50k`'s target set is not named by the spec; costing all three is the conservative reading and
# is listed as an assumption in every estimate.
MATRIX: tuple[Fit, ...] = (
    Fit("A_raw", TARGETS, epochs=0, kind="raw"),
    Fit("B_ft30", TARGETS, epochs=30),
    Fit("B_ft10", TARGETS, epochs=10),
    Fit("B_ft3", TARGETS, epochs=3),
    Fit("X_log1p", CLAIMNB_ONLY, epochs=30),
    Fit("S_50k", TARGETS, epochs=30, rows=50_000),
    Fit("D_exposure", CLAIMNB_ONLY, epochs=30),
)

ASSUMPTIONS: tuple[str, ...] = (
    "epoch scaling: fixed share "
    f"{FIXED_OVERHEAD_FRACTION:.0%} of a 30-epoch fit, the rest linear in epochs",
    "row scaling: linear in rows (conservative; inference context grows sublinearly)",
    "A_raw costed at the full measured fine-tune rate (upper bound)",
    "S_50k costed on all three targets because the spec does not name them",
    "one fit = one fold x model seed; folds and seeds are independent by the pre-registration",
    f"cold-start overhead ${COLD_START_USD:.2f} per attempt, reported separately",
)


class NoMeasurement(Exception):
    """An estimate was asked for without the measurement it must rest on."""


@dataclass(frozen=True)
class Measurement:
    """The one benchmark fit, as the box measured it."""

    wall_seconds: float
    rows: int
    epochs: int
    device: str
    tabpfn_version: str
    frame: str
    seed: int = 42

    def __post_init__(self) -> None:
        if self.wall_seconds <= 0:
            raise ValueError("wall_seconds must be positive; a zero fit is not a measurement")
        if self.rows <= 0 or self.epochs <= 0:
            raise ValueError("rows and epochs must be positive")


@dataclass(frozen=True)
class ArmCost:
    arm: str
    fits: int
    seconds_each: float
    seconds_total: float
    gpu_hours: float
    usd: float


@dataclass(frozen=True)
class Estimate:
    measurement: Measurement
    rate_per_hour: float
    ceiling_usd: float
    fixed_overhead_fraction: float
    cold_start_usd: float
    assumptions: tuple[str, ...]
    arms: tuple[ArmCost, ...]
    total_fits: int
    total_gpu_hours: float
    compute_usd: float
    cold_start_usd_total: float
    total_usd: float
    headroom_usd: float
    within_ceiling: bool

    def to_dict(self) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "measurement": asdict(self.measurement),
            "rate_per_hour": self.rate_per_hour,
            "ceiling_usd": self.ceiling_usd,
            "fixed_overhead_fraction": self.fixed_overhead_fraction,
            "cold_start_usd": self.cold_start_usd,
            "assumptions": list(self.assumptions),
            "arms": [asdict(arm) for arm in self.arms],
            "totals": {
                "fits": self.total_fits,
                "gpu_hours": self.total_gpu_hours,
                "compute_usd": self.compute_usd,
                "cold_start_usd": self.cold_start_usd_total,
                "total_usd": self.total_usd,
                "headroom_usd": self.headroom_usd,
                "within_ceiling": self.within_ceiling,
            },
        }


def fit_seconds(
    measurement: Measurement,
    fit: Fit,
    fixed_overhead_fraction: float = FIXED_OVERHEAD_FRACTION,
) -> float:
    """Seconds for one fit of `fit`, from the measured 30-epoch point."""
    if not 0.0 <= fixed_overhead_fraction < 1.0:
        raise ValueError("fixed_overhead_fraction must be in [0, 1)")
    if fit.kind == "raw":
        return measurement.wall_seconds
    overhead = fixed_overhead_fraction * measurement.wall_seconds
    per_epoch = (
        (1.0 - fixed_overhead_fraction)
        * measurement.wall_seconds
        / measurement.epochs
    )
    return overhead + per_epoch * fit.epochs * (fit.rows / measurement.rows)


def estimate(
    measurement: Measurement,
    rate_per_hour: float,
    *,
    ceiling_usd: float = CEILING_USD,
    fixed_overhead_fraction: float = FIXED_OVERHEAD_FRACTION,
    cold_start_usd: float = COLD_START_USD,
) -> Estimate:
    """The full matrix in GPU-hours and dollars, checked against the ceiling."""
    if rate_per_hour <= 0:
        raise ValueError("rate_per_hour must be positive")
    if measurement is None:
        raise NoMeasurement("an estimate must rest on a measured fit")

    arms = []
    total_fits = 0
    total_seconds = 0.0
    for fit in MATRIX:
        seconds_each = fit_seconds(measurement, fit, fixed_overhead_fraction)
        seconds_total = seconds_each * fit.n_fits
        total_fits += fit.n_fits
        total_seconds += seconds_total
        arms.append(
            ArmCost(
                arm=fit.arm,
                fits=fit.n_fits,
                seconds_each=seconds_each,
                seconds_total=seconds_total,
                gpu_hours=seconds_total / 3600.0,
                usd=(seconds_total / 3600.0) * rate_per_hour,
            )
        )

    total_gpu_hours = total_seconds / 3600.0
    compute_usd = total_gpu_hours * rate_per_hour
    total_usd = compute_usd + cold_start_usd
    return Estimate(
        measurement=measurement,
        rate_per_hour=rate_per_hour,
        ceiling_usd=ceiling_usd,
        fixed_overhead_fraction=fixed_overhead_fraction,
        cold_start_usd=cold_start_usd,
        assumptions=ASSUMPTIONS,
        arms=tuple(arms),
        total_fits=total_fits,
        total_gpu_hours=total_gpu_hours,
        compute_usd=compute_usd,
        cold_start_usd_total=cold_start_usd,
        total_usd=total_usd,
        headroom_usd=ceiling_usd - total_usd,
        within_ceiling=total_usd <= ceiling_usd,
    )
