#!/usr/bin/env python3
"""The actuarial baseline's verdict, from the registered captures (#597).

    python scripts/analyses/actuarial_baseline.py \\
        --tabpfn-frequency-french 20261112T164543Z \\
        --tabpfn-frequency-spanish 20261112T184155Z \\
        --tabpfn-severity-french 20261112T210029Z \\
        --tabpfn-severity-spanish 20261112T220641Z \\
        --baseline-frequency-french 20261114T090001Z \\
        --baseline-frequency-spanish 20261114T090002Z \\
        --baseline-severity-french 20261114T090003Z \\
        --baseline-severity-spanish 20261114T090004Z

The statistic is the registered one, with the direction inverted so it names the contender:

    r_{t,f} = ( M_{t,f}(baseline) - M_{t,f}(B_ft30) ) / M_{t,f}(baseline)

averaged over the three seeds inside each fold; the target's interval is the fair test's paired t
over five folds (4 df). A **positive** `r` means TabPFN has the lower metric. The verdict is taken
against the **better** of `E_glm` and `F_catboost` — the lower mean metric on that target's own
test rows — because a win against the weaker baseline is true and useless.

The decision rule is imported from the fair-test analyser rather than restated: `Go`, `No-go` and
`Inconclusive` keep exactly the meaning the pre-registration gave them, and the per-target floors
carry over unchanged.

Before anything is scored, the baseline run's `test_index` is compared fold by fold with the
registered TabPFN capture's. If they differ the comparison is refused: "same folds" is the one
assumption that makes the number mean anything, and it is checked rather than asserted.

Task means are printed **descriptively**. No pooled or task-level verdict is claimed: the
two-portfolio bootstrap was registered for a different question.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

_ANALYSES = Path(__file__).resolve().parent
_REPO = _ANALYSES.parents[1]
RESULTS = _REPO / "results"
sys.path.insert(0, str(_ANALYSES))
sys.path.insert(0, str(_REPO / "src"))

# The registered decision rule and its t multiplier live in the fair-test analyser; importing them
# keeps the two reports from drifting apart.
from freq_sev_fair_test import (  # noqa: E402
    FLOOR_FREQUENCY,
    FLOOR_FREQUENCY_SPANISH,
    FLOOR_SEVERITY,
    target_summary,
)
from provenance import sha256_array  # noqa: E402

CONTENDER = "B_ft30"
ALONGSIDE = "A_raw"
BASELINES = ("E_glm", "F_catboost")
ANCHOR = "M_intercept"

TARGETS = ("frequency_french", "frequency_spanish", "severity_french", "severity_spanish")
# The registered per-target floors, taken from the fair-test analyser so the two reports cannot
# disagree about what a `Go` on this target required.
FLOORS = {
    "frequency_french": FLOOR_FREQUENCY,
    "frequency_spanish": FLOOR_FREQUENCY_SPANISH,
    "severity_french": FLOOR_SEVERITY,
    "severity_spanish": FLOOR_SEVERITY,
}
TASKS = {
    "frequency": ("frequency_french", "frequency_spanish"),
    "severity": ("severity_french", "severity_spanish"),
}


def _mean(values) -> float:
    values = list(values)
    return sum(values) / len(values)


def _records(run_dir: Path):
    """Every slot record under a run, with the path that holds its arrays."""
    for meta in sorted(Path(run_dir).glob("*/*/seed*_fold*/meta.json")):
        yield meta, json.loads(meta.read_text())


def slot_metrics(
    run_dir: Path, *, arm: str | None = None, method: str | None = None
) -> dict[tuple[int, int], float]:
    """`(fold, seed) -> verdict_metric_value` for the slots matching the selector.

    The selector is an Arm for the TabPFN run and a method for the baseline run. A baseline's
    record has no Arm, so the two runs select on different fields and neither can be read as the
    other (`GLOSSARY.md`).
    """
    values: dict[tuple[int, int], float] = {}
    for _meta, record in _records(run_dir):
        if arm is not None and record.get("arm") != arm:
            continue
        if method is not None and record.get("method") != method:
            continue
        seed, fold = record.get("seed"), record.get("fold")
        if seed is None or fold is None:
            continue
        values[(int(fold), int(seed))] = float(record["verdict_metric_value"])
    return values


def train_rows(run_dir: Path) -> list[int]:
    """The distinct training budgets the slots recorded, ascending."""
    rows = set()
    for _meta, record in _records(run_dir):
        if record.get("train_rows") is not None:
            rows.add(int(record["train_rows"]))
    return sorted(rows)


def fold_ratios(
    tabpfn: dict[tuple[int, int], float],
    baseline: dict[tuple[int, int], float],
) -> dict[int, float]:
    """`r_{t,f}`: the per-seed ratios, paired by seed and averaged inside the fold.

    Pairing by seed matters: the two runs share a seed's training sample only when the seed is the
    same one, so averaging each side's sorted values would compare seed 0 against seed 1 whenever
    an ordering differed.
    """
    paired = sorted(set(tabpfn) & set(baseline))
    if not paired:
        raise SystemExit("the TabPFN and baseline runs share no (fold, seed) slot")
    by_fold: dict[int, list[float]] = {}
    for fold, seed in paired:
        reference = baseline[(fold, seed)]
        by_fold.setdefault(fold, []).append(
            (reference - tabpfn[(fold, seed)]) / reference
        )
    return {fold: _mean(values) for fold, values in sorted(by_fold.items())}


def target_verdict(ratios: dict[int, float], floor: float) -> dict:
    """One target's `r`, interval, MDE and registered decision.

    `target_summary` is the fair test's own function, so the statistic, the t multiplier and the
    rule are one definition rather than two that agree today. It carries `T975_DF4` and the
    4-degrees-of-freedom MDE constant, so a run that is not five folds cannot be summarised by it:
    a 1-fold run divides by zero and a 3-fold run silently reports a 4-df interval.
    """
    if len(ratios) != 5:
        raise SystemExit(
            f"the registered interval is a paired t over five folds (4 df); this target has "
            f"{len(ratios)} fold(s), so the summary would not be the registered statistic"
        )
    row = target_summary(ratios, "", floor)
    row.pop("run_id")
    return row


def _fold_index_hashes(run_dir: Path) -> dict[int, list[str]]:
    """Every slot's `test_index` sha256, grouped by fold.

    Per slot, not one per fold: the acceptance criterion is that *each* baseline slot's index
    equals the registered capture's, and taking the first slot of a fold would let the rest differ.
    """
    hashes: dict[int, list[str]] = {}
    for meta, record in _records(run_dir):
        if record.get("fold") is None:
            continue
        path = meta.parent / "test_index.npy"
        if path.is_file():
            hashes.setdefault(int(record["fold"]), []).append(sha256_array(np.load(path)))
    return hashes


def assert_comparability(tabpfn_dir: Path, baseline_dir: Path) -> None:
    """Every fold's test rows must be the registered capture's, or the comparison means nothing."""
    reference = _fold_index_hashes(tabpfn_dir)
    candidate = _fold_index_hashes(baseline_dir)

    if not reference or not candidate:
        raise SystemExit(
            "comparability: a run carries no test_index, so the folds have not been checked"
        )
    if set(reference) != set(candidate):
        missing = sorted(set(reference) - set(candidate))
        extra = sorted(set(candidate) - set(reference))
        raise SystemExit(
            f"comparability: the runs do not cover the same folds (missing {missing}, "
            f"not in the registered run {extra})"
        )
    for fold in sorted(reference):
        # One hash per fold in the registered run: the index belongs to the fold, not the slot.
        registered = set(reference[fold])
        if len(registered) != 1:
            raise SystemExit(
                f"comparability: {tabpfn_dir} disagrees with itself at fold {fold}; its slots "
                "carry different test_index arrays"
            )
        expected = registered.pop()
        mismatched = [value for value in candidate[fold] if value != expected]
        if mismatched:
            raise SystemExit(
                f"comparability: {len(mismatched)} slot(s) of fold {fold} in {baseline_dir} "
                f"score rows other than the registered capture's ({expected[:12]}…)"
            )


def _print_row(label: str, row: dict) -> None:
    low, high = row["ci"]
    print(
        f"{label:<24}{row['mean']:>+8.2%}   [{low:>+6.2%}, {high:>+6.2%}]"
        f"{row['mde']:>7.2%}{row['floor']:>7.0%}  {row['decision']}"
    )


def analyse(
    tabpfn_runs: dict[str, Path],
    baseline_runs: dict[str, Path],
) -> dict:
    """The per-target verdicts against the better baseline, plus the descriptive extras."""
    summary: dict = {"targets": {}, "tasks": {}}
    for target in TARGETS:
        tabpfn_dir = tabpfn_runs[target]
        baseline_dir = baseline_runs[target]
        assert_comparability(tabpfn_dir, baseline_dir)

        contender = slot_metrics(tabpfn_dir, arm=CONTENDER)
        if not contender:
            raise SystemExit(f"{tabpfn_dir}: no {CONTENDER} slots")
        by_baseline = {}
        for method in BASELINES:
            values = slot_metrics(baseline_dir, method=method)
            if not values:
                raise SystemExit(
                    f"{baseline_dir}: no {method} slots; the registered comparison is against "
                    "both baselines"
                )
            by_baseline[method] = {
                "ratios": fold_ratios(contender, values),
                "metric": _mean(values.values()),
                "train_rows": train_rows(baseline_dir),
            }
        better = min(by_baseline, key=lambda name: by_baseline[name]["metric"])
        verdict = target_verdict(by_baseline[better]["ratios"], FLOORS[target])

        alongside = slot_metrics(tabpfn_dir, arm=ALONGSIDE)
        alongside_row = (
            target_verdict(
                fold_ratios(alongside, slot_metrics(baseline_dir, method=better)),
                FLOORS[target],
            )
            if alongside
            else None
        )
        anchor_values = slot_metrics(baseline_dir, method=ANCHOR)
        anchor_row = None
        if anchor_values and contender:
            anchor_row = target_verdict(
                fold_ratios(contender, anchor_values), FLOORS[target]
            )
            anchor_row["metric"] = _mean(anchor_values.values())

        summary["targets"][target] = {
            "tabpfn_run_id": Path(tabpfn_dir).name,
            "baseline_run_id": Path(baseline_dir).name,
            "better_baseline": better,
            "verdict": verdict,
            "by_baseline": {
                name: {
                    "mean_metric": row["metric"],
                    "mean_r": _mean(row["ratios"].values()),
                }
                for name, row in by_baseline.items()
            },
            "alongside": None if alongside_row is None else {
                "arm": ALONGSIDE,
                "mean": alongside_row["mean"],
                "decision": alongside_row["decision"],
            },
            "anchor": anchor_row,
            "folds": {str(fold): value for fold, value in by_baseline[better]["ratios"].items()},
            "train_rows": by_baseline[better]["train_rows"],
        }

    # Descriptive only: the mean of the two per-target `r`s. No interval and no decision, because
    # the registered task-level claim belongs to a different design.
    for task, members in TASKS.items():
        summary["tasks"][task] = {
            "members": list(members),
            "mean_r": _mean(summary["targets"][member]["verdict"]["mean"] for member in members),
            "note": "descriptive; no task-level verdict is claimed",
        }
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for target in TARGETS:
        flag = target.replace("_", "-")
        parser.add_argument(f"--tabpfn-{flag}", required=True, metavar="RUN_ID")
        parser.add_argument(f"--baseline-{flag}", required=True, metavar="RUN_ID")
    parser.add_argument("--json", action="store_true", help="print the summary as JSON")
    args = parser.parse_args(argv)

    tabpfn_runs = {
        target: RESULTS / getattr(args, f"tabpfn_{target}") for target in TARGETS
    }
    baseline_runs = {
        target: RESULTS / getattr(args, f"baseline_{target}") for target in TARGETS
    }
    summary = analyse(tabpfn_runs, baseline_runs)

    if args.json:
        print(json.dumps(summary, indent=2))
        return 0

    print(
        f"{'target':<24}{'r vs better baseline':>9}{'95% CI':>20}{'MDE':>7}{'floor':>7}  decision"
    )
    for target, row in summary["targets"].items():
        _print_row(f"{target} ({row['better_baseline']})", row["verdict"])
    print()
    for target, row in summary["targets"].items():
        beside = row["alongside"]
        anchor = row["anchor"]
        parts = [f"{target}: better={row['better_baseline']}"]
        for name, values in row["by_baseline"].items():
            parts.append(f"{name} r={values['mean_r']:+.2%}")
        if beside:
            parts.append(f"{beside['arm']} r={beside['mean']:+.2%} ({beside['decision']})")
        if anchor:
            parts.append(f"anchor r={anchor['mean']:+.2%}")
        print("  " + "; ".join(parts))
    print()
    for task, row in summary["tasks"].items():
        print(f"task {task:<13}{row['mean_r']:>+8.2%}   (descriptive; no pooled verdict)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
