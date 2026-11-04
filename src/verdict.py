"""What a run can claim: per-seed deltas, the null band, and the design's resolution (#398).

The decision this serves is D12–D14: an effect of `delta` ROC AUC over the in-run `A_raw`, judged on the
mean of per-seed deltas with the interval taken from the **between-seed** standard deviation, and a null
measured on the same run's own predictions.

Three quantities, each refused rather than guessed:

- **Per-seed deltas** — every tuned arm against that seed's `A_raw`, in both AUC and Brier.
- **The null band** — permuting the truth labels, which is the sharp null: the scores cannot know the
  labels, so whatever the rule reports is noise by construction.
- **Resolution** — the seed count a target effect needs, and the power a given seed count gives.

Batches are pooled; **rows** are not. D17 delivers one design as eight launches, so `--run` may be
given more than once and the batches are merged by arm × seed, refusing runs from different datasets
and refusing a seed that appears twice -- a repeated seed would enter the mean twice and understate
the spread.

Rows are never pooled across seeds. Pooling treats rows inside a seed as independent; they are not, and
the standard error is understated by about 1.69× at this design's variance ratio, which lifts the
false-positive rate to roughly 0.25 — the exact error the seed axis exists to fix. For the same reason
the interval below is built from the spread *between seeds*, not from the rows inside one.

Two claims are withheld even when the arithmetic would produce them:

- **Zero between-seed variance.** Identical deltas on every seed make a zero-width interval, which would
  turn any point estimate into a "pass". That is not evidence; it is a run that cannot estimate its own
  noise, and it reads *unresolved*.
- **A rule that fails its instrument check.** If the observed false-positive rate under permutation
  exceeds `MAX_FALSE_POSITIVE`, the verdict is **void** — an instrument failure, not an effect. A rate
  *below* the bound is not a failure: a conjunction is deliberately conservative.

Refusals, each naming what is missing: a run with no `A_raw`; no tuned arm; fewer than two seeds; arms
that disagree on truth; a non-positive target effect; too few replicates to support a band.
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
#: A rule that fires more often than this under the null is not trusted. The bound is one-sided on
#: purpose: a conjunction fires *less* often than nominal (the anchor's measured 0.001), and voiding a
#: conservative rule for being conservative would void the only rule that protects the claim.
MAX_FALSE_POSITIVE = 0.07
#: How far the gate's regression check lets the measured band drift from the committed figure.
BAND_TOLERANCE = 0.002
MIN_SEEDS = 2
MIN_REPS = 100
#: Identifies the arithmetic that produced a row, so a citation can name its tool.
TOOL_VERSION = "verdict/1"


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


def _pairs(run: VerifiedRun) -> dict[tuple[str, int], object]:
    return {(slot.arm, slot.seed): slot for slot in run.slots}


def _check(run: VerifiedRun) -> None:
    arms = {slot.arm for slot in run.slots}
    if BASELINE not in arms:
        raise CaptureRefused(f"{run.run_id} has no {BASELINE} arm; every delta is against it")
    seeds = {slot.seed for slot in run.slots}
    if len(seeds) < MIN_SEEDS:
        raise CaptureRefused(
            f"{run.run_id} has {len(seeds)} seed(s); between-seed variance needs at least {MIN_SEEDS}"
        )


def _pair(run: VerifiedRun, arm: str, seed: int):
    """One arm's slot on one seed, refused if the comparison would cross seeds."""
    by_slot = _pairs(run)
    slot, base = by_slot.get((arm, seed)), by_slot.get((BASELINE, seed))
    if slot is None or base is None:
        raise CaptureRefused(
            f"{run.run_id}: {arm} and {BASELINE} do not both cover seed {seed}; "
            "a comparison must come from one seed"
        )
    return slot, base


def arms(run: VerifiedRun) -> tuple[Arm, ...]:
    """Every tuned arm's per-seed deltas, sorted by name."""
    _check(run)
    tuned = sorted({slot.arm for slot in run.slots if slot.arm != BASELINE})
    if not tuned:
        raise CaptureRefused(f"{run.run_id} holds only {BASELINE}; there is nothing to compare")
    seeds = sorted({slot.seed for slot in run.slots})

    out = []
    for arm in tuned:
        rows = []
        for seed in seeds:
            slot, base = _pair(run, arm, seed)
            auc = roc_auc(slot.truth, slot.predictions)
            rows.append(
                Delta(
                    arm=arm,
                    seed=seed,
                    auc=auc,
                    delta_auc=auc - roc_auc(base.truth, base.predictions),
                    delta_brier=brier(slot.truth, slot.predictions)
                    - brier(base.truth, base.predictions),
                )
            )
        out.append(Arm(name=arm, deltas=tuple(rows)))
    return tuple(out)


def null_band(run: VerifiedRun, arm: Arm, reps: int = DEFAULT_REPS, rng_seed: int = 20261102) -> dict:
    """The false-positive behaviour of the rule when the labels are known to carry no signal."""
    if reps < MIN_REPS:
        raise CaptureRefused(f"{reps} permutations cannot support a band; use at least {MIN_REPS}")
    _check(run)
    draws = {}
    for delta in arm.deltas:
        slot, base = _pair(run, arm.name, delta.seed)
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
    seeds = sorted(draws)
    joint = np.ones(reps, dtype=bool)
    for seed in seeds:
        joint &= np.abs(draws[seed]) > per_seed_band[seed]
        joint &= np.sign(draws[seed]) == np.sign(draws[seeds[0]])
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


def reading(arm: Arm, delta: float, false_positive_rate: float | None = None) -> str:
    """What this run's own seeds license: pass, equivalence, unresolved, or void.

    `void` outranks everything: a rule that failed its instrument check cannot close a lever. `pass`
    and `equivalence` are both withheld when the between-seed variance is zero, because the interval
    is then a point and either claim would be manufactured rather than measured.
    """
    if false_positive_rate is not None and false_positive_rate > MAX_FALSE_POSITIVE:
        return "void"
    if arm.sd <= 0:
        return "unresolved"
    se = arm.sd / math.sqrt(len(arm.deltas))
    low, high = arm.mean - Z_ALPHA * se, arm.mean + Z_ALPHA * se
    if low > 0 and arm.mean >= delta and arm.brier_worst <= 0.001:
        return "pass"
    if -delta <= low and high <= delta:
        return "equivalence"
    return "unresolved"


def pool(runs: tuple[VerifiedRun, ...]) -> VerifiedRun:
    """Several verified runs as one, for a design delivered in batches.

    D17 splits the replication into eight launches so that one host failure costs a batch rather
    than the programme. Seeds are the unit of analysis, so pooling is exact -- provided the runs
    share a dataset and their seeds are disjoint.

    A repeated seed is refused rather than merged: it would enter the mean twice and understate the
    between-seed spread, which is the row-pooling error in a different costume.
    """
    runs = tuple(runs)
    if not runs:
        raise CaptureRefused("no runs to pool")
    datasets = sorted({run.dataset for run in runs})
    if len(datasets) > 1:
        raise CaptureRefused(
            f"cannot pool runs from different datasets ({', '.join(datasets)}); "
            "a pooled reading would average two experiments"
        )
    owner: dict[tuple[str, int], str] = {}
    combined = []
    for run in runs:
        for slot in run.slots:
            key = (slot.arm, slot.seed)
            if key in owner:
                raise CaptureRefused(
                    f"{slot.arm} seed {slot.seed} appears in both {owner[key]} and {run.run_id}; "
                    "a pooled reading needs each seed exactly once"
                )
            owner[key] = run.run_id
            combined.append(slot)
    return VerifiedRun(
        run_id="+".join(run.run_id for run in runs),
        dataset=datasets[0],
        slots=tuple(sorted(combined, key=lambda slot: (slot.arm, slot.seed))),
    )


def check_seeds(
    run: VerifiedRun, declared: int | None = None, exclude_run: Path | None = None
) -> None:
    """Refuse a run that cannot carry the pre-registered design.

    `declared` is the seed count the pre-registration fixed; a run with fewer cannot answer it.
    `exclude_run` is a run whose seeds must not be reused — the probe's seeds may not appear in the
    replication, or the "fresh seeds" claim is false and the verdict indistinguishable from a
    reused one.
    """
    seeds = {slot.seed for slot in run.slots}
    if declared is not None and len(seeds) < declared:
        raise CaptureRefused(
            f"{run.run_id} has {len(seeds)} seed(s) but the pre-registration declares {declared}; "
            "a short run cannot answer the declared design"
        )
    if exclude_run is not None:
        other = read_run(Path(exclude_run))
        overlap = sorted(seeds & {slot.seed for slot in other.slots})
        if overlap:
            raise CaptureRefused(
                f"{run.run_id} reuses seed(s) {overlap} from {other.run_id}; "
                "the replication's seeds must be disjoint from the probe's"
            )


def rows(run: VerifiedRun, delta: float, reps: int = DEFAULT_REPS) -> list[dict]:
    """Long-format rows: one per arm × seed × metric, each carrying its capture hash."""
    out = []
    for arm in arms(run):
        null = null_band(run, arm, reps=reps)
        for record in arm.deltas:
            slot, _ = _pair(run, arm.name, record.seed)
            for metric, value in (("delta_auc/1", record.delta_auc), ("delta_brier/1", record.delta_brier)):
                out.append(
                    {
                        "arm": arm.name,
                        "seed": record.seed,
                        "metric": metric,
                        "value": f"{value:.6f}",
                        "capture_sha": slot.capture_sha,
                        "tool_version": TOOL_VERSION,
                        "delta_target": f"{delta:.6f}",
                        "null_fpr": f"{null['false_positive_rate']:.6f}",
                        "reading": reading(arm, delta, null["false_positive_rate"]),
                    }
                )
    return sorted(out, key=lambda row: (row["arm"], row["seed"], row["metric"]))


def render_csv(records: list[dict]) -> str:
    """Byte-stable rendering: fixed column order, one row per record, no clock."""
    fields = ["arm", "seed", "metric", "value", "capture_sha", "tool_version", "delta_target",
              "null_fpr", "reading"]
    lines = [",".join(fields)]
    lines += [",".join(str(record[field]) for field in fields) for record in records]
    return "\n".join(lines) + "\n"


def mean_band(run: VerifiedRun, reps: int = DEFAULT_REPS) -> float:
    """The run's mean per-seed null band — the number the committed analysis quotes."""
    return float(
        np.mean([np.mean(list(null_band(run, arm, reps)["band95"].values())) for arm in arms(run)])
    )


def report(run: VerifiedRun, delta: float, reps: int) -> list[str]:
    lines = [f"run {run.run_id} | dataset {run.dataset} | target delta {delta:+.4f} AUC"]
    for arm in arms(run):
        null = null_band(run, arm, reps=reps)
        design = resolution(arm.sd, delta) if arm.sd > 0 else None
        needs = f"needs {design['seeds_needed']} seeds" if design else "needs an unmeasurable sd"
        lines.append(
            f"{arm.name}: mean {arm.mean:+.4f} sd {arm.sd:.4f} "
            f"brier worst {arm.brier_worst:+.4f} | null sd {null['sd']:.4f} "
            f"fpr {null['false_positive_rate']:.4f} | {needs} "
            f"| reading {reading(arm, delta, null['false_positive_rate'])}"
        )
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--run",
        type=Path,
        action="append",
        required=True,
        help="a run directory under results/; repeat it to pool the batches of one design (D17)",
    )
    parser.add_argument(
        "--delta", type=float, default=0.002, help="target effect in AUC (default 0.002)"
    )
    parser.add_argument(
        "--reps", type=int, default=DEFAULT_REPS, help=f"permutations (default {DEFAULT_REPS})"
    )
    parser.add_argument(
        "--expect-band",
        type=float,
        default=None,
        help=f"fail unless the mean null band is within {BAND_TOLERANCE} of this value",
    )
    parser.add_argument("--seeds", type=int, default=None, help="the seed count the pre-registration declares")
    parser.add_argument("--exclude-run", type=Path, default=None, help="a run whose seeds must not be reused")
    parser.add_argument("--out", type=Path, default=None, help="write the long-format CSV here")
    args = parser.parse_args(argv)
    if args.delta <= 0:
        print(f"verdict: target effect must be positive; got {args.delta}")
        return 2
    try:
        runs = [read_run(path) for path in args.run]
        run = runs[0] if len(runs) == 1 else pool(tuple(runs))
        check_seeds(run, args.seeds, args.exclude_run)
        if args.out is not None:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(render_csv(rows(run, args.delta, args.reps)), encoding="utf-8")
            print(f"verdict: wrote {args.out}")
            return 0
        if args.expect_band is not None:
            got = mean_band(run, args.reps)
            ok = abs(got - args.expect_band) <= BAND_TOLERANCE
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
