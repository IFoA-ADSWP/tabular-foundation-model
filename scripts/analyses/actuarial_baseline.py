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

# The registered decision rule and its t multiplier live in the fair-test analyser; importing them
# keeps the two reports from drifting apart.
from freq_sev_fair_test import decide, target_interval  # noqa: E402

CONTENDER = "B_ft30"
ALONGSIDE = "A_raw"
BASELINES = ("E_glm", "F_catboost")
ANCHOR = "M_intercept"

TARGETS = ("frequency_french", "frequency_spanish", "severity_french", "severity_spanish")
FLOORS = {
    "frequency_french": 0.02,
    "frequency_spanish": 0.04,
    "severity_french": 0.02,
    "severity_spanish": 0.02,
}
TASKS = {
    "frequency": ("frequency_french", "frequency_spanish"),
    "severity": ("severity_french", "severity_spanish"),
}


def _mean(values) -> float:
    values = list(values)
    return sum(values) / len(values)


def slot_metrics(
    run_dir: Path, *, arm: str | None = None, method: str | None = None
) -> dict[tuple[int, int], float]:
    """`(fold, seed) -> verdict_metric_value` for the slots matching the selector.

    The selector is an Arm for the TabPFN run and a method for the baseline run. A baseline's
    record has no Arm, so the two runs select on different fields and neither can be read as the
    other (`GLOSSARY.md`).
    """
    values: dict[tuple[int, int], float] = {}
    for meta in sorted(Path(run_dir).glob("*/*/seed*_fold*/meta.json")):
        record = json.loads(meta.read_text())
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
    for meta in Path(run_dir).glob("*/*/seed*_fold*/meta.json"):
        record = json.loads(meta.read_text())
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
    """One target's `r`, interval, MDE and registered decision."""
    mean, half, sd = target_interval(ratios)
    return {
        "mean": mean,
        "ci": [mean - half, mean + half],
        "sd_fold": sd,
        "mde": 2.8016 * sd / np.sqrt(len(ratios)),
        "floor": floor,
        "decision": decide(mean, mean - half, mean + half, floor),
    }


def assert_comparability(tabpfn_dir: Path, baseline_dir: Path) -> None:
    """Every fold's test rows must be the registered capture's, or the comparison means nothing."""
    # The index belongs to the fold, so compare fold by fold across all slots.
    reference = {}
    for meta in sorted(Path(tabpfn_dir).glob("*/*/seed*_fold*/meta.json")):
        record = json.loads(meta.read_text())
        if record.get("fold") is None:
            continue
        path = meta.parent / "test_index.npy"
        if path.is_file():
            reference.setdefault(int(record["fold"]), np.load(path))
    candidate = {}
    for meta in sorted(Path(baseline_dir).glob("*/*/seed*_fold*/meta.json")):
        record = json.loads(meta.read_text())
        if record.get("fold") is None:
            continue
        path = meta.parent / "test_index.npy"
        if path.is_file():
            candidate.setdefault(int(record["fold"]), np.load(path))

    if not reference or not candidate:
        raise SystemExit(
            "comparability: a run carries no test_index, so the folds have not been checked"
        )
    for fold in sorted(set(reference) & set(candidate)):
        if not np.array_equal(reference[fold], candidate[fold]):
            raise SystemExit(
                f"comparability: fold {fold}'s test_index differs between {tabpfn_dir} and "
                f"{baseline_dir}; the rows are not the registered ones"
            )
    missing = sorted(set(reference) - set(candidate))
    if missing:
        raise SystemExit(
            f"comparability: {baseline_dir} has no test_index for fold(s) {missing}"
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
