"""Analyze the classification-reframe experiment (issue #67).

Inputs:
  reframe_frequency_results.csv — per-fold rows for spanish_motor_freq:
    binary task (seed 42 + seed 7, canonical 9 methods) and ordinal task
    (seed 42, 6 multiclass methods): dataset, task, method, fold, seed,
    log_loss, auc, brier, pr_auc, lift10, fit_s, infer_s.
Outputs:
  reframe_frequency_summary.csv — per task x seed x metric x baseline:
    tabpfn vs baseline mean±SE, delta, paired t (df=4, two-sided),
    tabpfn rank among methods. Mirrors the structure/format of
    frontier_tuned_baseline_summary.csv so the docs agent can reuse it.
Printed tables: per metric, tabpfn vs each baseline (delta + paired p),
plus the key question (is tabpfn rank #1 on auc/pr_auc, and does the
best baseline beat it with paired significance?).

Usage: python analyze_reframe_frequency.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
RESULTS_CSV = HERE / "reframe_frequency_results.csv"
SUMMARY_CSV = HERE / "reframe_frequency_summary.csv"

BINARY_METRICS = ["auc", "pr_auc", "lift10", "log_loss", "brier"]
ORDINAL_METRICS = ["auc", "lift10", "log_loss", "brier"]  # pr_auc is NaN for ordinal
DIRECTION = {"auc": "max", "pr_auc": "max", "lift10": "max",
             "log_loss": "min", "brier": "min"}  # better =


def mean_se(v: pd.Series) -> tuple[float, float]:
    a = v.to_numpy(dtype=float)
    n = len(a)
    return float(a.mean()), float(a.std(ddof=1)) / np.sqrt(n)


def paired_test(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    """Paired t-test on per-fold deltas (a - b), df = n-1, two-sided."""
    d = a - b
    n = len(d)
    sd = d.std(ddof=1)
    if sd == 0:
        t = float(np.inf) if d.mean() != 0 else float("nan")
        return t, (0.0 if np.isfinite(t) else float("nan"))
    t = d.mean() / (sd / np.sqrt(n))
    return float(t), float(2.0 * stats.t.sf(abs(t), n - 1))


def main() -> None:
    res = pd.read_csv(RESULTS_CSV)
    print(f"rows: {len(res)}  tasks: {sorted(res.task.unique())}  "
          f"seeds: {sorted(res.seed.unique())}")
    for task in sorted(res.task.unique()):
        sub = res[res.task == task]
        for seed in sorted(sub.seed.unique()):
            s = sub[sub.seed == seed]
            print(f"  {task} seed {seed}: methods={sorted(s.method.unique())} "
                  f"rows={len(s)}")

    rows: list[dict] = []
    for task in ("binary", "ordinal"):
        sub = res[res.task == task]
        metrics = BINARY_METRICS if task == "binary" else ORDINAL_METRICS
        for seed in sorted(sub.seed.unique()):
            sub2 = sub[sub.seed == seed]
            for metric in metrics:
                means = {}
                for m in sorted(sub2.method.unique()):
                    f = sub2[sub2.method == m][metric]
                    if len(f) == 5 and f.notna().all():
                        means[m] = mean_se(f)
                if "tabpfn" not in means or len(means) < 3:
                    continue
                order = sorted(means, key=lambda m: means[m][0],
                               reverse=(DIRECTION[metric] == "max"))
                rank = order.index("tabpfn") + 1
                tm, ts = means["tabpfn"]
                tf = sub2[sub2.method == "tabpfn"].sort_values("fold")[metric].to_numpy(dtype=float)
                for b in sorted(means):
                    if b == "tabpfn":
                        continue
                    bm, bs = means[b]
                    bf = sub2[sub2.method == b].sort_values("fold")[metric].to_numpy(dtype=float)
                    t_p, p_p = paired_test(tf, bf)
                    rows.append({
                        "dataset": "spanish_motor_freq", "task": task, "metric": metric,
                        "seed": seed, "baseline": b,
                        "tabpfn_mean": tm, "tabpfn_se": ts,
                        "base_mean": bm, "base_se": bs,
                        "delta": tm - bm,  # tabpfn - baseline (sign per direction)
                        "t_paired": t_p, "p_paired": p_p,
                        "tabpfn_rank": rank, "n_folds": len(tf),
                    })
    summ = pd.DataFrame(rows)

    pd.set_option("display.width", 240)
    pd.set_option("display.max_columns", 60)
    for (task, seed), g in summ.groupby(["task", "seed"]):
        print(f"\n{'=' * 80}\n{task.upper()} TASK seed={seed}\n{'=' * 80}")
        for metric in sorted(g.metric.unique(), key=lambda m: list(DIRECTION).index(m)):
            t = g[g.metric == metric].copy()
            best = max if DIRECTION[metric] == "max" else min
            bm = t.sort_values("base_mean", ascending=(DIRECTION[metric] == "min")).iloc[0]
            print(f"\n--- {metric} (rank of tabpfn: {t.iloc[0]['tabpfn_rank']}) "
                  f"tabpfn={bm['tabpfn_mean']:.4f} vs best baseline "
                  f"{bm['baseline']}={bm['base_mean']:.4f} "
                  f"(delta {bm['delta']:+.4f}, p={bm['p_paired']:.3f}) ---")
            t = t.sort_values("baseline")
            t["delta"] = t["delta"].map(lambda v: f"{v:+.5f}")
            t["p_paired"] = t["p_paired"].map(lambda v: f"{v:.4f}")
            t["tabpfn"] = t["tabpfn_mean"].map(lambda v: f"{v:.4f}")
            t["base"] = t["base_mean"].map(lambda v: f"{v:.4f}")
            print(t[["baseline", "tabpfn", "base", "delta", "p_paired",
                     "tabpfn_rank"]].to_string(index=False))

    # Key question: does any baseline beat tabpfn with paired significance?
    # The `***` below means "this comparison is significant" -- the opposite of the pilot
    # report's marker, which marks an interval covering zero (#296).
    print(f"\n{'=' * 80}\nKEY QUESTION: best baseline vs tabpfn (paired p<0.05)\n{'=' * 80}")
    print("  `***` = paired-significant (p<0.05); no marker = not significant")
    for (task, seed), g in summ.groupby(["task", "seed"]):
        for metric in ("auc", "pr_auc") if task == "binary" else ("auc",):
            t = g[g.metric == metric]
            if t.empty:
                continue
            better = max if DIRECTION[metric] == "max" else min
            best = t.loc[t["base_mean"].idxmax()] if better == max else t.loc[t["base_mean"].idxmin()]
            win = (best["delta"] > 0) if better == max else (best["delta"] < 0)
            sig = best["p_paired"] < 0.05
            print(f"  {task} seed={seed} {metric}: tabpfn rank {int(best['tabpfn_rank'])}, "
                  f"vs best baseline {best['baseline']} "
                  f"(delta {best['delta']:+.4f}, p={best['p_paired']:.4f}, "
                  f"{'tabpfn wins' if win else 'baseline wins'}"
                  f"{'***' if sig else ''})")

    summ.to_csv(SUMMARY_CSV, index=False)
    print(f"\nwrote {SUMMARY_CSV} ({len(summ)} rows)")


if __name__ == "__main__":
    main()
