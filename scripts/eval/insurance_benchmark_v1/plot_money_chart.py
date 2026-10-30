"""Money chart — TabPFN vs the best method, one scatter for the whole benchmark.

Story: TabPFN is at/near parity (ratio ~1.0, often the best method itself) on
smaller datasets, and drifts above 1.0 (worse) as datasets grow; every
off-frontier point sits at >= 53.5K training rows with ratio >= 1.03.

x = dataset size in training rows (log scale; raw CSV row count == full train
    size used by the frontier harness — load_Xy drops no rows for these files,
    and freMTPL2freq's log_exposure transform preserves the count).
y = TabPFN mean metric / best mean metric per dataset (log scale, lower is
    better; 1.0 = TabPFN is the best method). Best = min mean over the frontier
    panel (9 methods classification / 8 regression).
Color = on_frontier flag of the tabpfn row in each frontier_results CSV.
Sweep series = home_turf_sweep_results.csv 9 cells (bemtl97/coil2000/
    uslapseagent x 1K/5K/full), ratio of mean tabpfn log_loss vs best of the
    sweep's 4-method panel (cat/lgbm/xgb/tabpfn) — shows the small-data wins:
    TabPFN is the best method in 8/9 sweep cells.

Usage:
    /tmp/tabarena/.venv-ta/bin/python scripts/eval/insurance_benchmark_v1/plot_money_chart.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import pandas as pd

HERE = Path(__file__).resolve().parent
RAW = HERE.parent.parent.parent / "data" / "raw"
sys.path.insert(0, str(HERE.parent.parent.parent))  # repo root
from src.experiment_spec import load_registry  # noqa: E402

_DATASETS = load_registry(HERE / "experiments.toml").datasets

# label offsets in POINTS (textcoords="offset points") per dataset — hand-tuned
# to separate the same-file pairs (67,856; 163,212; 53,502) and the 1.0-line cluster
OFFSETS = {
    "ausautoBI8999": (8, 10), "ausprivauto0405": (6, -14),
    "ausprivauto0405_vehvalue": (-10, 10), "bemtl16": (8, 10),
    "bemtl97": (0, -14), "bemtl97_amount": (-10, 22),
    "coil2000": (12, -14), "freMTPL2freq": (-12, 20),
    "norauto": (-20, 10), "spanish_motor_freq": (-20, 20),
    "spanish_motor_severity": (10, 10), "uslapseagent": (14, 10),
}

# Plot only the datasets with a committed frontier result and a label offset; a new
# registry Dataset must not make a committed chart crash (file, then KeyError).
DATASETS = {name: _DATASETS[name].file for name in OFFSETS}


def load_points() -> pd.DataFrame:
    rows = []
    for ds, src in DATASETS.items():
        df = pd.read_csv(HERE / f"frontier_results_{ds}.csv")
        t = df[df.method == "tabpfn"].iloc[0]
        best = df.loc[df["mean"].idxmin()]
        n_rows = sum(1 for _ in open(RAW / src)) - 1
        rows.append({
            "dataset": ds, "n_rows": n_rows,
            "tabpfn": t["mean"], "best": best["mean"], "best_method": best["method"],
            "ratio": t["mean"] / best["mean"], "on_frontier": t["on_frontier"],
        })
    return pd.DataFrame(rows)


def load_sweep() -> pd.DataFrame:
    sw = pd.read_csv(HERE / "home_turf_sweep_results.csv")
    cells = []
    for key, g in sw.groupby(["dataset", "n_rows"]):
        ds = g["dataset"].iloc[0]
        n = int(g["n_rows"].iloc[0])
        m = g.groupby("method")["log_loss"].mean()
        cells.append({"dataset": ds, "n_rows": n, "ratio": m["tabpfn"] / m.min()})
    return pd.DataFrame(cells)


def main() -> None:
    pts = load_points()
    swp = load_sweep()

    fig, ax = plt.subplots(figsize=(14, 8.5), dpi=150)
    ON, OFF, GREY = "#1f77b4", "#d62728", "#888888"

    # size sweep: hollow grey diamonds (TabPFN is best in 8/9 cells -> all ~1.0)
    ax.scatter(swp["n_rows"], swp["ratio"] * 1.001, s=70, facecolors="none",
               edgecolors=GREY, alpha=0.6, linewidths=1.2, zorder=2,
               label="size sweep 1K/5K/full (9 cells, TabPFN best in 8)")

    # frontier datasets: on-frontier blue, off-frontier red
    for _, r in pts.iterrows():
        ds, n, ratio = str(r["dataset"]), int(r["n_rows"]), float(r["ratio"])
        color = ON if r["on_frontier"] == "yes" else OFF
        ax.scatter([n], [ratio], s=110, color=color, zorder=3,
                   edgecolors="white", linewidths=0.8)
        dx, dy = OFFSETS[ds]
        ax.annotate(ds, (n, ratio), textcoords="offset points",
                    xytext=(dx, dy), fontsize=9, color=color, zorder=4)

    ax.axhline(1.0, color="black", ls="--", lw=1.0, alpha=0.6, zorder=1)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(5e3, 1.2e6)
    ax.set_ylim(0.98, 1.65)
    ax.set_xlabel("Dataset size — training rows (log scale)")
    ax.set_ylabel("TabPFN metric \u00f7 best metric (log scale, 1.0 = ties the best)")
    ax.set_title("TabPFN vs the best method on every insurance benchmark dataset",
                 fontsize=15, pad=12)
    ax.grid(True, which="both", alpha=0.25)
    handles = [Line2D([], [], marker="o", ls="", color=ON, markersize=9, label="on frontier"),
               Line2D([], [], marker="o", ls="", color=OFF, markersize=9, label="off frontier"),
               Line2D([], [], marker="D", ls="", color="none", markerfacecolor="none",
                      markeredgecolor=GREY, markersize=9, label="size sweep (1K/5K/full)")]
    ax.legend(handles=handles, loc="lower right", fontsize=10, framealpha=0.9)
    ax.text(0.01, 0.015,
            "12 frontier datasets (6 classification, 6 regression), 5-fold CV; ratio = TabPFN mean metric \u00f7 best mean metric. "
            "Parity at small size, drift > 1.0 as datasets grow; all off-frontier points sit at \u2265 53.5K rows.",
            transform=ax.transAxes, fontsize=9.5, color="#444444",
            bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#bbbbbb", alpha=0.9))
    fig.tight_layout()
    out = HERE / "money_chart_tabpfn_relative.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"saved {out} ({out.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
