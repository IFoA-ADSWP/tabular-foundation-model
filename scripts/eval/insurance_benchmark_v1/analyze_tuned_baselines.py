"""Analyze the tuned-baseline "finality" experiment (Part C).

Inputs:
  frontier_tuned_baseline_results.csv — per-fold rows for lr (identity ref),
    lr_tuned, glm_eng, lgbm_tuned, cat_tuned, rf_tuned (all 6 datasets, seed 42)
    and tabfm (3 smallest datasets, seed 42).
  frontier_pr_auc_results.csv — canonical 9 methods incl. tabpfn (seed 42 rows).
Outputs:
  frontier_tuned_baseline_summary.csv — per dataset x metric x baseline:
    tabpfn vs baseline mean±SE, delta, paired t (df=4, two-sided), tabpfn rank
    among {9 canonical + tuned baselines + tabfm}.
  Printed tables incl. the key question (does ANY tuned baseline beat tabpfn on
  auc/pr_auc with paired significance?) and tuning-effectiveness (tuned vs
  default config).

Usage: python analyze_tuned_baselines.py [results_csv]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
sys.path.insert(0, str(REPO))  # repo root
from src.experiment_spec import (  # noqa: E402
    CLASSIFICATION,
    datasets_by_mode,
    load_registry,
    mode_methods,
)

_REGISTRY = load_registry(HERE / "experiments.toml")
TUNED_CSV = HERE / "frontier_tuned_baseline_results.csv"
CANON_CSV = HERE / "frontier_pr_auc_results.csv"
SUMMARY_CSV = HERE / "frontier_tuned_baseline_summary.csv"

CANON_METHODS = [m.name for m in mode_methods(_REGISTRY, CLASSIFICATION)]
# Tuned variants are a method study, not a registry experiment (#235).
TUNED_METHODS = ["lr_tuned", "glm_eng", "lgbm_tuned", "cat_tuned", "rf_tuned", "tabfm"]
DATASETS = [d.name for d in datasets_by_mode(_REGISTRY, CLASSIFICATION)]
METRICS = ["auc", "pr_auc", "lift10", "log_loss", "brier"]
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
    tuned = pd.read_csv(sys.argv[1] if len(sys.argv) > 1 else TUNED_CSV)
    canon = pd.read_csv(CANON_CSV)
    canon = canon[canon.seed == 42]
    print(f"tuned rows: {len(tuned)}  methods: {sorted(tuned.method.unique())}  "
          f"datasets: {sorted(tuned.dataset.unique())}")
    print(f"canonical rows (seed 42): {len(canon)}")

    # Plain `lr` exists in BOTH CSVs (the tuned run fit it as the fold-identity
    # reference — values identical, verified). Keep only the tuned-run copy so
    # every method appears exactly once (5 folds) in the merged frame.
    canon = canon[canon.method != "lr"]
    allm = pd.concat([
        canon[canon.method.isin(CANON_METHODS)][
            ["dataset", "method", "fold", "log_loss", "auc", "brier", "pr_auc", "lift10"]],
        tuned[["dataset", "method", "fold", "log_loss", "auc", "brier", "pr_auc", "lift10"]],
    ], ignore_index=True)

    # ---- 1. Per dataset x metric: method means, tabpfn rank, paired tests ----
    rows: list[dict] = []
    for ds in DATASETS:
        sub = allm[allm.dataset == ds]
        for metric in METRICS:
            means = {}
            for m in sorted(sub.method.unique()):
                f = sub[(sub.method == m)][metric]
                if len(f):
                    means[m] = mean_se(f)
            if "tabpfn" not in means or len(means) < 3:
                continue
            better = max if DIRECTION[metric] == "max" else min
            order = sorted(means, key=lambda m: means[m][0],
                           reverse=(DIRECTION[metric] == "max"))
            rank = order.index("tabpfn") + 1
            tm, ts = means["tabpfn"]
            tf = sub[sub.method == "tabpfn"].sort_values("fold")[metric].to_numpy(dtype=float)
            for b in sorted(means):
                if b == "tabpfn":
                    continue
                bm, bs = means[b]
                bf = sub[sub.method == b].sort_values("fold")[metric].to_numpy(dtype=float)
                n = min(len(tf), len(bf))  # tabfm may have fewer folds (capped)
                t_p, p_p = paired_test(tf[:n], bf[:n])
                rows.append({
                    "dataset": ds, "metric": metric, "baseline": b,
                    "tabpfn_mean": tm, "tabpfn_se": ts,
                    "base_mean": bm, "base_se": bs,
                    "delta": tm - bm,  # tabpfn - baseline (sign per direction in table)
                    "t_paired": t_p, "p_paired": p_p,
                    "tabpfn_rank": rank, "n_folds": n,
                })
    summ = pd.DataFrame(rows)

    # ---- 2. Printed: tabpfn vs each tuned baseline (auc / pr_auc / lift10 / ll / brier) ----
    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 60)
    for metric in METRICS:
        print(f"\n=== {metric} — tabpfn vs baselines (delta = tabpfn - base; "
              f"{'+' if DIRECTION[metric]=='max' else '-'}=tabpfn better) ===")
        t = summ[summ.metric == metric].copy()
        t["delta"] = t["delta"].map(lambda v: f"{v:+.5f}")
        t["p_paired"] = t["p_paired"].map(lambda v: f"{v:.4f}")
        t["tabpfn"] = (t["tabpfn_mean"]).map(lambda v: f"{v:.4f}")
        t["base"] = t["base_mean"].map(lambda v: f"{v:.4f}")
        print(t[["dataset", "baseline", "tabpfn", "base", "delta", "p_paired",
                 "tabpfn_rank"]].to_string(index=False))

    # ---- 3. Key question: any tuned baseline beats tabpfn on auc / pr_auc? ----
    print("\n=== KEY QUESTION: does any tuned baseline beat tabpfn (paired p<0.05)? ===")
    for metric in ("auc", "pr_auc"):
        t = summ[summ.metric == metric].copy()
        # "baseline beats tabpfn": for max metrics, base_mean > tabpfn_mean AND p<0.05
        wins = t[(t.base_mean > t.tabpfn_mean) & (t.p_paired < 0.05)]
        if len(wins):
            print(f"{metric}: BEATEN on:")
            print(wins[["dataset", "baseline", "tabpfn_mean", "base_mean",
                        "delta", "p_paired", "tabpfn_rank"]].to_string(index=False))
        else:
            print(f"{metric}: no tuned baseline beats tabpfn with paired significance "
                  f"({len(t)} comparisons)")

    # ---- 4. Tuning effectiveness: tuned vs default config ----
    print("\n=== TUNING EFFECTIVENESS (tuned vs its default-config counterpart, seed 42) ===")
    pairs = [("lr", "lr_tuned"), ("cat", "cat_tuned"), ("lgbm", "lgbm_tuned"),
             ("rf", "rf_tuned"), ("logisticglm", "glm_eng")]
    for default, tuned_name in pairs:
        for metric in ("log_loss", "auc", "pr_auc"):
            print(f"-- {tuned_name} vs {default} ({metric}) --")
            for ds in DATASETS:
                d = allm[(allm.dataset == ds) & (allm.method == default)].sort_values("fold")
                t = allm[(allm.dataset == ds) & (allm.method == tuned_name)].sort_values("fold")
                if len(d) == 0 or len(t) == 0:
                    continue
                dm, ds_ = mean_se(d[metric])
                tm, ts_ = mean_se(t[metric])
                tp, pp = paired_test(t[metric].to_numpy(dtype=float),
                                     d[metric].to_numpy(dtype=float))
                better = ("-" if tm < dm else "+") if DIRECTION[metric] == "min" \
                    else ("+" if tm > dm else "-")
                print(f"  {ds:<16} default={dm:.4f} tuned={tm:.4f} "
                      f"({better} {abs(tm-dm):.4f}, p={pp:.3f})")

    summ.to_csv(SUMMARY_CSV, index=False)
    print(f"\nwrote {SUMMARY_CSV} ({len(summ)} rows)")


if __name__ == "__main__":
    main()
