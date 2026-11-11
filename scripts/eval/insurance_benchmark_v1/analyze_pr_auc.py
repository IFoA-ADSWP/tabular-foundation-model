"""Analyze the frontier PR-AUC / top-decile-lift robustness runs (--pr-auc).

Input:  frontier_pr_auc_results.csv — per-fold rows (dataset, seed, method, fold,
        log_loss, auc, brier, pr_auc, lift10), accumulated across runs A (seed 42),
        B (seed 7) and C (seed 123) in append mode.
Output: frontier_pr_auc_summary.csv — per dataset x metric: TabPFN vs best GLM
        (family {lr, logisticglm, tweedieglm, poissonglm}), unpaired z on the
        mean±SE summary, paired t-test on the 5 per-fold deltas (df=4, two-sided),
        TabPFN rank among the 9 methods. Plus printed tables and a seed-stability
        table (runs B/C vs A on ausprivauto0405, bemtl97, norauto).

Usage:  python analyze_pr_auc.py [path/to/frontier_pr_auc_results.csv]
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
PER_FOLD_CSV = HERE / "frontier_pr_auc_results.csv"
SUMMARY_CSV = HERE / "frontier_pr_auc_summary.csv"
GLM_FAMILY = ["lr", "logisticglm", "tweedieglm", "poissonglm"]
METHODS = [m.name for m in mode_methods(_REGISTRY, CLASSIFICATION)]
DATASETS = [d.name for d in datasets_by_mode(_REGISTRY, CLASSIFICATION)]
SEED_DATASETS = ["ausprivauto0405", "bemtl97", "norauto"]  # runs B/C scope
METRICS = ["log_loss", "auc", "pr_auc", "lift10"]
DIRECTION = {"log_loss": "min", "auc": "max", "pr_auc": "max", "lift10": "max"}  # better =


def mean_se(rows: pd.DataFrame) -> tuple[float, float]:
    v = rows.to_numpy(dtype=float)
    n = len(v)
    return float(v.mean()), float(v.std(ddof=1)) / np.sqrt(n)


def paired_test(tabpfn_fold: np.ndarray, glm_fold: np.ndarray) -> tuple[float, float]:
    """Paired t-test on per-fold deltas (tabpfn - glm), df = n-1, two-sided."""
    d = tabpfn_fold - glm_fold
    n = len(d)
    sd = d.std(ddof=1)
    if sd == 0:
        t = float(np.inf) if d.mean() != 0 else float("nan")
        return t, (0.0 if np.isfinite(t) else float("nan"))
    t = d.mean() / (sd / np.sqrt(n))
    p = 2.0 * stats.t.sf(abs(t), n - 1)
    return float(t), float(p)


def summarize(df: pd.DataFrame, seed: int) -> pd.DataFrame:
    """Per dataset x metric summary for one seed: TabPFN vs best GLM + rank."""
    rows: list[dict] = []
    d = df[df.seed == seed]
    for ds in DATASETS:
        sub = d[d.dataset == ds]
        for metric in METRICS:
            means = {}
            for m in METHODS:
                f = sub[(sub.method == m)][metric]
                if len(f) == 0:
                    continue
                means[m] = mean_se(f)
            if "tabpfn" not in means:
                continue
            # best GLM for THIS metric (direction-aware)
            better = max if DIRECTION[metric] == "max" else min
            glm = better(
                (m for m in GLM_FAMILY if m in means),
                key=lambda m: means[m][0],
            )
            tm, ts = means["tabpfn"]
            gm, gs = means[glm]
            delta = tm - gm
            z = delta / np.sqrt(ts**2 + gs**2) if (ts**2 + gs**2) > 0 else float("nan")
            tf = sub[sub.method == "tabpfn"].sort_values("fold")[metric].to_numpy(dtype=float)
            gf = sub[sub.method == glm].sort_values("fold")[metric].to_numpy(dtype=float)
            t_paired, p_paired = paired_test(tf, gf)
            # TabPFN rank among ALL methods by this metric (min-rank ties)
            order = sorted(means, key=lambda m: means[m][0], reverse=(DIRECTION[metric] == "max"))
            rank = order.index("tabpfn") + 1
            rows.append({
                "dataset": ds, "metric": metric, "seed": seed,
                "best_glm": glm,
                "tabpfn_mean": tm, "tabpfn_se": ts,
                "glm_mean": gm, "glm_se": gs,
                "delta": delta, "z_unpaired": z,
                "t_paired": t_paired, "p_paired": p_paired,
                "tabpfn_rank": rank,
            })
    return pd.DataFrame(rows)


def print_table(s: pd.DataFrame) -> None:
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 50)
    t = s.copy()
    for c in ["tabpfn_mean", "tabpfn_se", "glm_mean", "glm_se", "delta", "z_unpaired", "t_paired"]:
        t[c] = t[c].map(lambda v: f"{v:+.4f}" if c == "delta" and v != v else f"{v:.4f}")
    t["p_paired"] = t["p_paired"].map(lambda v: f"{v:.4f}")
    print(t[["dataset", "metric", "best_glm", "tabpfn_mean", "tabpfn_se",
             "glm_mean", "glm_se", "delta", "z_unpaired", "t_paired", "p_paired", "tabpfn_rank"]]
          .to_string(index=False))


def seed_stability(df: pd.DataFrame) -> pd.DataFrame:
    """TabPFN AUC rank vs best-GLM AUC delta per seed on the 3 marginal datasets."""
    out: list[dict] = []
    for ds in SEED_DATASETS:
        for seed in sorted(df.seed.unique()):
            sub = df[(df.dataset == ds) & (df.seed == seed)]
            aucs = {}
            for m in METHODS:
                f = sub[(sub.method == m)]["auc"]
                if len(f):
                    aucs[m] = mean_se(f)
            if "tabpfn" not in aucs:
                continue
            glm = max((m for m in GLM_FAMILY if m in aucs), key=lambda m: aucs[m][0])
            order = sorted(aucs, key=lambda m: aucs[m][0], reverse=True)
            rank = order.index("tabpfn") + 1
            out.append({
                "dataset": ds, "seed": seed,
                "tabpfn_auc": aucs["tabpfn"][0], "tabpfn_se": aucs["tabpfn"][1],
                "best_glm": glm, "glm_auc": aucs[glm][0],
                "delta_auc": aucs["tabpfn"][0] - aucs[glm][0],
                "tabpfn_auc_rank": rank,
            })
    return pd.DataFrame(out)


def main() -> None:
    csv = Path(sys.argv[1]) if len(sys.argv) > 1 else PER_FOLD_CSV
    df = pd.read_csv(csv)
    print(f"per-fold rows: {len(df)}  seeds: {sorted(df.seed.unique())}  "
          f"datasets: {sorted(df.dataset.unique())}")

    # ---- 1. Full per-method table, seed 42 ----
    d42 = df[df.seed == 42]
    print("\n=== SEED 42: mean +/- SE per method (auc / pr_auc / lift10) ===")
    for ds in DATASETS:
        sub = d42[d42.dataset == ds]
        print(f"\n-- {ds} --")
        print(f"{'method':<12} {'auc':>14} {'pr_auc':>14} {'lift10':>14} {'ll':>12}")
        for m in METHODS:
            f = sub[sub.method == m]
            if len(f) == 0:
                continue
            cells = []
            for metric in ["auc", "pr_auc", "lift10", "log_loss"]:
                mu, se = mean_se(f[metric])
                cells.append(f"{mu:.4f}+-{se:.4f}")
            print(f"{m:<12} {cells[0]:>14} {cells[1]:>14} {cells[2]:>14} {cells[3]:>12}")

    # ---- 2. Paired tests / ranks, seed 42 ----
    s42 = summarize(df, 42)
    print("\n=== SEED 42: TabPFN vs best GLM (paired t, df=4; delta = tabpfn - glm) ===")
    print_table(s42)

    # ---- 3. Seed stability ----
    ss = seed_stability(df)
    print("\n=== SEED STABILITY: TabPFN AUC rank + delta vs best GLM (by AUC) ===")
    pd.set_option("display.width", 200)
    t = ss.copy()
    for c in ["tabpfn_auc", "glm_auc", "delta_auc"]:
        t[c] = t[c].map(lambda v: f"{v:.4f}")
    print(t.to_string(index=False))

    # ---- 4. Persist summary (seed-42 rows per spec) ----
    s42.to_csv(SUMMARY_CSV, index=False)
    print(f"\nwrote {SUMMARY_CSV} ({len(s42)} rows)")


if __name__ == "__main__":
    main()
