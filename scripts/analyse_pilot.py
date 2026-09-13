#!/usr/bin/env python3
"""Report a Pilot 2 output directory in the form the statistical analysis plan requires.

The pipeline writes one record per arm-run: `predictions.npy`, `ground_truth.npy` and `meta.json`
under `<outdir>/<dataset>/<arm>[/seed<S>_fold<F>]`. This script reads those records back and
produces the SAP's numbers from them -- it does not recompute any model output, so what it reports
is exactly what the run recorded.

WHAT IT COMPUTES (SAP sections 2, 4, 5)
  * per dataset, per arm: the paired difference in ROC AUC against the baseline arm, as the MEAN
    over repeats with a nested paired interval (rows within a repeat, repeats with each other);
  * across datasets: an inverse-variance summary, which is the SAP's primary aggregation, with
    heterogeneity reported rather than assumed away;
  * Holm adjustment across the per-dataset family of four.

WHY PAIRED BY (SEED, FOLD). Two arms are only comparable on identical test rows. A run whose
counterpart is missing is REPORTED as unpaired and excluded, never silently averaged against a
different split -- a comparison across different test rows is not the comparison the SAP defines.

USAGE
    python scripts/analyse_pilot.py --outdir outputs/finetune/pilot
    python scripts/analyse_pilot.py --outdir outputs/finetune/pilot --json report.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "src"))

from paired_analysis import (  # noqa: E402
    holm_adjust,
    inverse_variance_summary,
    nested_paired_bootstrap,
)

_SLOT = re.compile(r"^seed(?P<seed>-?\d+)_fold(?P<fold>-?\d+|None)$")


def roc_auc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """ROC AUC via the Mann-Whitney U statistic (ties score 0.5)."""
    y_true = np.asarray(y_true)
    y_score = np.asarray(y_score, dtype=float)
    pos, neg = y_score[y_true == 1], y_score[y_true == 0]
    if pos.size == 0 or neg.size == 0:
        raise ValueError("AUC undefined: one class missing")
    cmp = pos[:, None] - neg[None, :]
    return float((np.sum(cmp > 0) + 0.5 * np.sum(cmp == 0)) / (pos.size * neg.size))


def parse_slot(name: str) -> tuple[int, int | None] | None:
    """`seed42_foldNone` -> (42, None); a flat slot -> the default (42, None)."""
    m = _SLOT.match(name)
    if not m:
        return None
    fold = m.group("fold")
    return int(m.group("seed")), (None if fold == "None" else int(fold))


def discover(outdir: Path) -> dict:
    """Every readable arm-run record, keyed by dataset -> arm -> (seed, fold)."""
    found: dict = {}
    for dataset_dir in sorted(p for p in outdir.iterdir() if p.is_dir()):
        for arm_dir in sorted(p for p in dataset_dir.iterdir() if p.is_dir()):
            slots = []
            if (arm_dir / "predictions.npy").exists():
                slots.append(((42, None), arm_dir))  # the flat single-run slot
            for child in sorted(p for p in arm_dir.iterdir() if p.is_dir()):
                if (child / "predictions.npy").exists():
                    slot = parse_slot(child.name)
                    if slot:
                        slots.append((slot, child))
            for slot, run_dir in slots:
                record = {
                    "dir": run_dir,
                    "y_true": np.load(run_dir / "ground_truth.npy"),
                    "probs": np.load(run_dir / "predictions.npy"),
                }
                meta_path = run_dir / "meta.json"
                if meta_path.exists():
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    record["status"] = meta.get("status", "complete")
                    record["epochs"] = (meta.get("effective_config") or {}).get("kwargs", {}).get(
                        "epochs"
                    )
                else:
                    record["status"] = "complete"
                found.setdefault(dataset_dir.name, {}).setdefault(arm_dir.name, {})[slot] = record
    return found


def analyse(
    found: dict,
    baseline: str,
    arms: list[str] | None,
    *,
    n_resamples: int,
    seed: int,
) -> dict:
    """Per-dataset paired estimates, the cross-dataset summary, and the Holm adjustment."""
    report: dict = {"baseline": baseline, "datasets": {}, "unpaired": [], "summary": {}}

    for dataset, by_arm in sorted(found.items()):
        if baseline not in by_arm:
            report["unpaired"].append(f"{dataset}: baseline '{baseline}' has no record")
            continue
        base_slots = by_arm[baseline]
        per_dataset = {}
        wanted = arms or [a for a in sorted(by_arm) if a != baseline]
        for arm in wanted:
            if arm not in by_arm:
                continue
            repeats, unpaired = [], []
            for slot, record in sorted(by_arm[arm].items(), key=lambda kv: str(kv[0])):
                if slot not in base_slots:
                    unpaired.append(f"{dataset}/{arm}@{slot}: no {baseline} counterpart")
                    continue
                repeats.append((record["y_true"], base_slots[slot]["probs"], record["probs"]))
            report["unpaired"].extend(unpaired)
            if not repeats:
                continue
            out = nested_paired_bootstrap(repeats, roc_auc, n_resamples=n_resamples, seed=seed)
            half_width = (out["ci_high"] - out["ci_low"]) / 2
            out["se"] = half_width / 1.959963984540054  # for the inverse-variance summary
            out["n_test_rows"] = int(sum(len(r[0]) for r in repeats))
            out["n_unpaired_runs"] = len(unpaired)
            out["run_dirs"] = [
                str(by_arm[arm][s]["dir"]) for s in sorted(by_arm[arm], key=str) if s in base_slots
            ]
            per_dataset[arm] = out
        if per_dataset:
            report["datasets"][dataset] = per_dataset

    # cross-dataset summary per arm, then Holm across the per-dataset family
    for arm in sorted({a for d in report["datasets"].values() for a in d}):
        entries = [
            (d, report["datasets"][d][arm])
            for d in sorted(report["datasets"])
            if arm in report["datasets"][d]
        ]
        if len(entries) >= 1:
            summary = inverse_variance_summary(
                [e["estimate"] for _, e in entries],
                [e["se"] ** 2 for _, e in entries],
            )
            report["summary"][arm] = summary
        # Holm needs p-values; the plan's primary rule is the interval, so the adjustment is
        # reported as a screen on the per-dataset family rather than as the decision itself.
        if len(entries) >= 2:
            from math import erfc, sqrt

            pvals = [
                0.5 * erfc(abs(e["estimate"] / e["se"]) / sqrt(2)) if e["se"] > 0 else 1.0
                for _, e in entries
            ]
            adjusted = holm_adjust(pvals)
            for (dataset, entry), adj in zip(entries, adjusted):
                entry["holm_adjusted_p"] = adj
    return report


def print_report(report: dict, outdir: Path) -> None:
    print(f"Pilot 2 analysis -- {outdir}")
    print(f"baseline: {report['baseline']}   (paired on ROC AUC over matching seed/fold slots)\n")
    if not report["datasets"]:
        print("  no paired comparisons found -- nothing to report")
    for dataset, by_arm in report["datasets"].items():
        print(f"  {dataset}")
        for arm, out in sorted(by_arm.items()):
            flag = "*** " if not out["excludes_zero"] else "    "
            print(
                f"    {flag}{arm:<14} {out['estimate']:+.4f}  "
                f"[{out['ci_low']:+.4f}, {out['ci_high']:+.4f}]  "
                f"repeats={out['n_repeats']}  rows={out['n_test_rows']}  "
                f"noise(half-width)={((out['ci_high'] - out['ci_low']) / 2):.4f}"
            )
    print()
    for arm, summary in sorted(report["summary"].items()):
        print(
            f"  inverse-variance summary, {arm}: {summary['pooled']:+.4f} "
            f"[{summary['ci_low']:+.4f}, {summary['ci_high']:+.4f}]  "
            f"k={summary['k']}  I2={summary['i2']:.0f}%"
        )
    if report["unpaired"]:
        print("\n  unpaired run(s) EXCLUDED from the comparisons above:")
        for note in report["unpaired"]:
            print(f"    {note}")
    print("\n  a comparison whose interval covers zero is marked *** -- per the plan it is")
    print("  reported as inconclusive, not as a trend.")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "analyse").splitlines()[0])
    ap.add_argument("--outdir", required=True, type=Path)
    ap.add_argument("--baseline", default="A_raw")
    ap.add_argument("--arms", default=None, help="comma-separated; default: every arm present")
    ap.add_argument("--n-resamples", type=int, default=10_000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args(argv)

    if not args.outdir.is_dir():
        print(f"ERROR: no such directory: {args.outdir}", file=sys.stderr)
        return 2
    found = discover(args.outdir)
    if not found:
        print(f"ERROR: no arm records under {args.outdir}", file=sys.stderr)
        return 2
    arms = [a.strip() for a in args.arms.split(",")] if args.arms else None
    report = analyse(found, args.baseline, arms, n_resamples=args.n_resamples, seed=args.seed)
    print_report(report, args.outdir)
    if args.json:
        args.json.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        print(f"\n  wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
