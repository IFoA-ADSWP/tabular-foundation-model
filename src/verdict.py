"""What a run can claim: per-seed deltas, the null band, and the design's resolution (#398).

The decision this serves is D12–D14: an effect of `delta` ROC AUC over the in-run `A_raw`, judged on a
random-effects interval over seeds, with the null measured on the same run's own predictions.

Three quantities, each refused rather than guessed:

- **Per-seed deltas** — every tuned arm against that seed's `A_raw`, in both AUC and Brier.
- **The null band** — permuting the truth labels, which is the sharp null: the scores cannot know the
  labels, so whatever the rule reports is noise by construction.
- **Resolution** — the seed count a target effect needs, and the power a given seed count gives.

Rows are never pooled across seeds. Pooling treats rows inside a seed as independent; they are not, and
the standard error is understated by about 1.69× at this design's variance ratio, which lifts the
false-positive rate to roughly 0.25 — the exact error the seed axis exists to fix.

Refusals, each naming what is missing: a run with no `A_raw`; fewer than two seeds; a non-positive
target effect; too few replicates to support a band.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from capture_reader import VerifiedRun, read_run
from metrics import brier, roc_auc
from run_capture import CaptureRefused

BASELINE = "A_raw"
Z_ALPHA = 1.959964
Z_POWER = 0.841621
DEFAULT_REPS = 5000
#: A decision rule whose false-positive rate under the null lands outside this is not trusted.
NULL_BAND = (0.03, 0.07)
MIN_SEEDS = 2
MIN_REPS = 100


@dataclass(frozen=True)
class Delta:
    """One arm's difference from the in-run baseline, on one seed."""

    arm: str
    seed: int
    auc: float
    delta_auc: float
    delta_brier: float


@dataclass(frozen=True)
class Arm:
    """A tuned arm's per-seed deltas, and what they imply."""

    name: str
    deltas: tuple[Delta, ...]

    @property
    def mean(self) -> float:
        return float(np.mean([d.delta_auc for d in self.deltas]))

    @property
    def sd(self) -> float:
        return float(np.std([d.delta_auc for d in self.deltas], ddof=1))

    @property
    def brier_worst(self) -> float:
        return float(np.max([d.delta_brier for d in self.deltas]))


def _check(run: VerifiedRun) -> None:
    arms = {slot.arm for slot in run.slots}
    if BASELINE not in arms:
        raise CaptureRefused(f"{run.run_id} has no {BASELINE} arm; every delta is against it")
    seeds = {slot.seed for slot in run.slots}
    if len(seeds) < MIN_SEEDS:
        raise CaptureRefused(
            f"{run.run_id} has {len(seeds)} seed(s); between-seed variance needs at least {MIN_SEEDS}"
        )


def arms(run: VerifiedRun) -> tuple[Arm, ...]:
    """Every tuned arm's per-seed deltas, sorted by name."""
    _check(run)
    by_slot = {(slot.arm, slot.seed): slot for slot in run.slots}
    seeds = sorted({slot.seed for slot in run.slots})
    tuned = sorted({slot.arm for slot in run.slots if slot.arm != BASELINE})
    if not tuned:
        raise CaptureRefused(f"{run.run_id} holds only {BASELINE}; there is nothing to compare")

    out = []
    for arm in tuned:
        rows = []
        for seed in seeds:
            slot = by_slot.get((arm, seed))
            base = by_slot.get((BASELINE, seed))
            if slot is None or base is None:
                raise CaptureRefused(
                    f"{run.run_id}: {arm} and {BASELINE} do not both cover seed {seed}; "
                    "a comparison must come from one seed"
                )
            auc, base_auc = roc_auc(slot.truth, slot.predictions), roc_auc(
                base.truth, base.predictions
            )
            rows.append(
                Delta(
                    arm=arm,
                    seed=seed,
                    auc=auc,
                    delta_auc=auc - base_auc,
                    delta_brier=brier(slot.truth, slot.predictions)
                    - brier(base.truth, base.predictions),
                )
            )
        out.append(Arm(name=arm, deltas=tuple(rows)))
    return tuple(out)


def null_band(run: VerifiedRun, arm: Arm, reps: int = DEFAULT_REPS, rng_seed: int = 20261102) -> dict:
    """The false-positive behaviour of a `delta` rule when the labels are known to carry no signal."""
    if reps < MIN_REPS:
        raise CaptureRefused(
            f"{reps} permutations cannot support a band; use at least {MIN_REPS}"
        )
    _check(run)
    by_slot = {(slot.arm, slot.seed): slot for slot in run.slots}
    draws = {}
    for delta in arm.deltas:
        slot, base = by_slot[(arm.name, delta.seed)], by_slot[(BASELINE, delta.seed)]
        if not np.array_equal(slot.truth, base.truth):
            raise CaptureRefused(f"seed {delta.seed}: {arm.name} and {BASELINE} disagree on truth")
        rng = np.random.default_rng(rng_seed + delta.seed)
        draw = np.empty(reps)
        for i in range(reps):
            truth = rng.permutation(slot.truth)
            draw[i] = roc_auc(truth, slot.predictions) - roc_auc(truth, base.predictions)
        draws[delta.seed] = draw

    per_seed_band = {seed: float(np.percentile(np.abs(d), 95)) for seed, d in draws.items()}
    # The rule fires when every seed clears its own band in the same direction.
    clears = [
        np.abs(draws[seed]) > per_seed_band[seed] for seed in sorted(draws)
    ]
    same_sign = [
        np.sign(draws[seed]) == np.sign(draws[sorted(draws)[0]]) for seed in sorted(draws)
    ]
    joint = np.ones(reps, dtype=bool)
    for cleared, signed in zip(clears, same_sign):
        joint &= cleared & signed
    return {
        "sd": float(np.mean([d.std(ddof=1) for d in draws.values()])),
        "band95": per_seed_band,
        "false_positive_rate": float(joint.mean()),
    }


def resolution(sd: float, delta: float, seeds: int | None = None) -> dict:
    """The seed count a target effect needs, or the power a given seed count gives."""
    if delta <= 0:
        raise CaptureRefused(f"target effect must be positive; got {delta}")
    if sd <= 0:
        raise CaptureRefused(f"per-seed SD must be positive; got {sd}")
    required = math.ceil((sd / (delta / (Z_ALPHA + Z_POWER))) ** 2)
    k = required if seeds is None else int(seeds)
    se = sd / math.sqrt(k)
    power = 0.5 * (1.0 + math.erf((delta / se - Z_ALPHA) / math.sqrt(2.0)))
    return {
        "seeds_needed": required,
        "seeds": k,
        "se": se,
        "half_width": Z_ALPHA * se,
        "power": power,
    }


def reading(arm: Arm, delta: float) -> str:
    """What this run's own seeds license: pass, equivalence, or unresolved."""
    se = arm.sd / math.sqrt(len(arm.deltas))
    low, high = arm.mean - Z_ALPHA * se, arm.mean + Z_ALPHA * se
    if low > 0 and arm.mean >= delta and arm.brier_worst <= 0.001:
        return "pass"
    if -delta <= low and high <= delta:
        return "equivalence"
    return "unresolved"


def mean_band(run: VerifiedRun, reps: int = DEFAULT_REPS) -> float:
    """The run's mean per-seed null band — the number the committed analysis quotes."""
    return float(np.mean([np.mean(list(null_band(run, arm, reps)["band95"].values())) for arm in arms(run)]))


def report(run: VerifiedRun, delta: float, reps: int) -> list[str]:
    lines = [f"run {run.run_id} | dataset {run.dataset} | target delta {delta:+.4f} AUC"]
    for arm in arms(run):
        null = null_band(run, arm, reps=reps)
        design = resolution(arm.sd, delta)
        lines.append(
            f"{arm.name}: mean {arm.mean:+.4f} sd {arm.sd:.4f} "
            f"brier worst {arm.brier_worst:+.4f} | null sd {null['sd']:.4f} "
            f"fpr {null['false_positive_rate']:.4f} | needs {design['seeds_needed']} seeds "
            f"| reading {reading(arm, delta)}"
        )
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", type=Path, required=True, help="a run directory under results/")
    parser.add_argument("--delta", type=float, default=0.002, help="target effect in AUC (default 0.002)")
    parser.add_argument(
        "--reps", type=int, default=DEFAULT_REPS, help=f"permutations (default {DEFAULT_REPS})"
    )
    parser.add_argument(
        "--expect-band",
        type=float,
        default=None,
        help="fail unless the mean null band is within 0.002 of this value (the gate's regression check)",
    )
    args = parser.parse_args(argv)
    if args.delta <= 0:
        print(f"verdict: target effect must be positive; got {args.delta}", flush=True)
        return 2
    try:
        run = read_run(args.run)
        if args.expect_band is not None:
            got = mean_band(run, args.reps)
            ok = abs(got - args.expect_band) <= 0.002
            print(
                f"verdict: mean null band {got:.4f} vs expected {args.expect_band:.4f} "
                f"({'ok' if ok else 'OUT OF TOLERANCE'})"
            )
            return 0 if ok else 1
        for line in report(run, args.delta, args.reps):
            print(line)
    except CaptureRefused as exc:
        print(f"verdict: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
