#!/usr/bin/env python3
"""Generate the baseline conclusion's tables from committed evidence (#631).

    python scripts/analyses/baseline_conclusion.py --out <path>    # write the block
    python scripts/analyses/baseline_conclusion.py --check <path>  # fail on drift

The conclusion is the designated owner of the headline table, so the table is generated
here and a test fails when the document drifts from this output. Nothing is transcribed.

Table 1 — the frontier verdicts. One row per dataset: the model, the rival that matched it
best, the difference, the model's own standard error, and the D3 decision.

Table 2 — the checks run on 2026-11-21: the exposure-aware GLM re-test and the row curve.
These are re-analyses of committed captures and baselines at lower budgets, not new arms.

Known gap, recorded rather than papered over: the frontier results CSVs carry no run id, so
`source` for table 1 is the CSV path. #632 asks for a run id per row; producing one needs a
dataset -> run mapping that does not exist yet, and inventing one here would be a
transcription error waiting to happen.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FRONTIER = REPO / "scripts/eval/insurance_benchmark_v1"

# The twelve canonical frontier datasets, their metric, and the direction of "better".
DATASETS = {
    "coil2000": ("log_loss", "min"),
    "bemtl16": ("log_loss", "min"),
    "uslapseagent": ("log_loss", "min"),
    "norauto": ("log_loss", "min"),
    "bemtl97": ("log_loss", "min"),
    "ausprivauto0405": ("log_loss", "min"),
    "ausautoBI8999": ("rmse", "min"),
    "ausprivauto0405_vehvalue": ("rmse", "min"),
    "bemtl97_amount": ("rmse", "min"),
    "freMTPL2freq": ("poisson_deviance", "min"),
    "spanish_motor_freq": ("poisson_deviance", "min"),
    "spanish_motor_severity": ("rmse", "min"),
}

BEGIN = "<!-- BEGIN GENERATED: baseline-conclusion -->"
END = "<!-- END GENERATED: baseline-conclusion -->"


def read_frontier(name: str) -> list[dict]:
    path = FRONTIER / f"frontier_results_{name}.csv"
    with path.open() as f:
        return list(csv.DictReader(f))


def table1() -> str:
    lines = ["| dataset | era | model | metric | value | best rival | Δ | interval (±SE) | decision | source |",
             "|---|---|---|---|---:|---|---:|---:|---|---|"]
    for ds, (metric, _) in DATASETS.items():
        rows = read_frontier(ds)
        model = next(r for r in rows if r["method"] == "tabpfn")
        rivals = [r for r in rows if r["method"] != "tabpfn"]
        best = min(rivals, key=lambda r: float(r["mean"]))
        value, se = float(model["mean"]), float(model["se"])
        delta = value - float(best["mean"])
        decision = "on frontier" if model["on_frontier"] == "yes" else "off frontier"
        lines.append(
            f"| `{ds}` | v3 | `v3_default` | {metric} | {value:.5f} | `{best['method']}` "
            f"{float(best['mean']):.5f} | {delta:+.5f} | {se:.5f} | {decision} | "
            f"`frontier_results_{ds}.csv` |")
    return "\n".join(lines)


def table2() -> str:
    lines = ["| check | dataset | contrast | metric | Δ | interval | decision | source |",
             "|---|---|---|---|---:|---|---|---|"]
    exp = FRONTIER / "exposure_aware_glm_followup.csv"
    if exp.exists():
        with exp.open() as f:
            for r in csv.DictReader(f):
                if r["seed"] != "42":
                    continue
                d = float(r["delta_log_loss"])
                verdict = "model ahead" if d < 0 else "GLM ahead"
                lines.append(f"| exposure-aware GLM | `{r['dataset']}` | one-hot LR + log(exposure) | "
                             f"log loss | {d:+.5f} | p={float(r['p_log_loss']):.3f} | {verdict} | "
                             f"`exposure_aware_glm_followup.csv` |")
    curve = REPO / "scripts/analyses/row_curve_stage1.csv"
    if curve.exists():
        with curve.open() as f:
            rows = list(csv.DictReader(f))
        for ds, budget in sorted({(r["target"], r["budget"]) for r in rows}):
            grp = sorted([r for r in rows if r["target"] == ds and r["budget"] == budget],
                         key=lambda r: float(r["mean"]))
            b, s = grp[0], grp[1]
            delta = float(s["mean"]) - float(b["mean"])
            ok = delta > float(b["mde"])
            lines.append(f"| row curve | `{ds}` @ {budget} | `{s['method']}` | {b['metric']} | "
                         f"{delta:.5f} vs `{b['method']}` | MDE {float(b['mde']):.5f} | "
                         f"{'resolvable' if ok else 'Inconclusive'} | `row_curve_stage1.csv` |")
    return "\n".join(lines)


def block() -> str:
    banner = ("# Baseline conclusion — generated tables\n\n> **Status:** current — generated 2026-11-21 (#631). Regenerate with\n> `scripts/analyses/baseline_conclusion.py --out`; a test fails when this file drifts.\n\n")
    return banner + f"{BEGIN}\n\n### Table 1 — frontier verdicts\n\n{table1()}\n\n### Table 2 — checks run 2026-11-21\n\n{table2()}\n\n{END}\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--check")
    a = ap.parse_args()
    generated = block()
    if a.out:
        Path(a.out).write_text(generated)
        print(f"wrote {a.out} ({len(generated.splitlines())} lines)")
        return 0
    if a.check:
        text = Path(a.check).read_text()
        if BEGIN not in text or END not in text:
            print(f"{a.check}: no generated-table markers", file=sys.stderr)
            return 1
        if text.strip() != generated.strip():
            print(f"{a.check}: the table has drifted from its generator", file=sys.stderr)
            return 1
        print(f"{a.check}: table matches the generator")
        return 0
    print(generated)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
