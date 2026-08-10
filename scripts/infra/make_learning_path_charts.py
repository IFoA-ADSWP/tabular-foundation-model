"""Generate the charts embedded in docs/LEARNING-PATH-JUNIOR.md.

Real-data charts read outputs/current/tables/*.csv (source of truth);
the reliability chart is a labeled schematic for teaching.

Run from repo root: .venv-ta/bin/python scripts/infra/make_learning_path_charts.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from pathlib import Path

TABLES = Path("outputs/current/tables")
OUT = Path("docs/figures")
OUT.mkdir(parents=True, exist_ok=True)

# 1. Discrimination: Table1 ROC AUC (top panel) / PR AUC (bottom panel)
# Two panels, not one shared axis: ROC (0.55-0.60) and PR (0.15-0.19) need
# opposite zooms; a shared 0-0.7 axis flattens the story into noise.
t1 = pd.read_csv(TABLES / "Table1_Model_Performance.csv")
x = np.arange(len(t1))
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6.5), sharex=True,
                               gridspec_kw={"hspace": 0.08},
                               constrained_layout=True)

ax1.bar(x, t1["roc_auc"], 0.55, color="#4C72B0", label="ROC AUC")
ax1.axhline(0.5, color="gray", ls="--", lw=1.5, label="chance (0.5)")
ax1.set_ylabel("ROC AUC"); ax1.set_ylim(0.44, 0.66)
ax1.set_title("Table1: discrimination on eudirectlapse (real results)")
ax1.legend(fontsize=8, loc="lower right")
for xi, v in zip(x, t1["roc_auc"]):
    ax1.text(xi, v + 0.004, f"{v:.3f}", ha="center", fontsize=8)
ax1.annotate("", xy=(-0.4, 0.628), xytext=(len(t1) - 0.6, 0.628),
             arrowprops=dict(arrowstyle="-", lw=1.2, color="#333333"))
ax1.text(len(t1) / 2 - 0.5, 0.645, "tight band 0.55\u20130.60 \u2014 models \u2248 equal",
         ha="center", fontsize=8, color="#333333")

ax2.bar(x, t1["pr_auc"], 0.55, color="#DD8452", label="PR AUC")
ax2.axhline(0.128, color="gray", ls=":", lw=1.5,
            label="chance = prevalence (0.128)")
ax2.set_ylabel("PR AUC"); ax2.set_ylim(0.10, 0.22)
ax2.legend(fontsize=8, loc="lower right")
for xi, v in zip(x, t1["pr_auc"]):
    ax2.text(xi, v + 0.003, f"{v:.3f}", ha="center", fontsize=8)
ax2.set_xticks(x); ax2.set_xticklabels(t1["model"], rotation=15)
fig.savefig(OUT / "lp_discrimination.png", dpi=150, bbox_inches="tight"); plt.close(fig)

# 2. Calibration: Table4 Brier vs constant-predictor floor.
# Axis must be zoomed or the floor "grazes" the bars and the chart looks
# broken; value labels + gap annotation carry the <1% story.
t4 = pd.read_csv(TABLES / "Table4_Brier_Scores.csv")
floor = 0.1281 * (1 - 0.1281)  # pi*(1-pi): Brier of predicting the base rate for everyone
gap = floor - t4["Brier Score"].min()
fig, ax = plt.subplots(figsize=(7, 4))
ax.bar(t4["Method"], t4["Brier Score"], color="#55A868", width=0.5)
ax.axhline(floor, color="crimson", ls="--", lw=1.5,
           label=f"constant-predictor floor = {floor:.4f}")
ax.set_ylabel("Brier (lower is better)")
ax.set_title("Table4: Brier on eudirectlapse (real results)")
ax.set_ylim(0.105, 0.117); ax.legend(fontsize=8, loc="upper left")
for xi, v in zip(range(len(t4)), t4["Brier Score"]):
    ax.text(xi, v + 0.00025, f"{v:.4f}", ha="center", fontsize=8)
ax.text(0.99, 0.06, f"gap to floor \u2248 {gap:.4f} (< 1%)",
        transform=ax.transAxes, ha="right", fontsize=8, color="crimson")
fig.tight_layout(); fig.savefig(OUT / "lp_brier.png", dpi=150); plt.close(fig)

# 3. Class balance: Table3 full vs stratified 10K subset, with the values
# shown so the "they match" lesson is verifiable, not decorative.
t3 = pd.read_csv(TABLES / "Table3_Class_Balance.csv")
x = np.arange(2); w = 0.35
fig, ax = plt.subplots(figsize=(7, 4))
ax.bar(x - w/2, t3["Full Dataset %"], w, label="Full dataset", color="#4C72B0")
ax.bar(x + w/2, t3["Subset (10K) %"], w, label="10K subset", color="#DD8452")
ax.set_xticks(x); ax.set_xticklabels(["no lapse (0)", "lapse (1)"])
ax.set_ylabel("% of rows"); ax.set_ylim(0, 105)
ax.set_title("Table3: stratified subset holds the 12.8% balance (real results)")
ax.legend(fontsize=8)
for xi, v in zip(x, t3["Full Dataset %"]):
    ax.text(xi - w/2, v + 1.5, f"{v:.2f}", ha="center", fontsize=8)
for xi, v in zip(x, t3["Subset (10K) %"]):
    ax.text(xi + w/2, v + 1.5, f"{v:.2f}", ha="center", fontsize=8)
ax.annotate("\u0394 0.01 pp", xy=(1, 12.82), xytext=(1, 55), ha="center",
            fontsize=8, arrowprops=dict(arrowstyle="->", lw=1))
fig.tight_layout(); fig.savefig(OUT / "lp_class_balance.png", dpi=150); plt.close(fig)

# 4. Schematic: how to read a reliability diagram (teaching, not evidence).
# Crimson is reserved for reference lines in this doc set; the overconfident
# curve gets dark red instead.
p = np.linspace(0, 1, 200)
fig, ax = plt.subplots(figsize=(6, 5))
ax.plot([0, 1], [0, 1], color="green", lw=2, label="perfectly calibrated")
ax.plot(p, p**1.6, color="#C44E52", lw=2, label="overconfident (schematic)")
ax.plot(p, p**0.6, color="#4C72B0", lw=2, label="underconfident (schematic)")
ax.set_xlabel("predicted probability"); ax.set_ylabel("observed frequency")
ax.set_title("Reliability diagram \u2014 how to read it")
ax.legend(fontsize=8); ax.set_aspect("equal")
fig.tight_layout(); fig.savefig(OUT / "lp_reliability_schematic.png", dpi=150); plt.close(fig)

print("wrote:", sorted(p.name for p in OUT.glob("lp_*.png")))
