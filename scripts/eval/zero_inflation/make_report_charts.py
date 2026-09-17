"""Regenerate the charts used in docs/reports/ZERO_INFLATION_TABPFN.md."""

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.abspath(os.path.join(HERE, "..", "..", "..", "outputs", "current", "figures"))
PREFIX = "zero_inflation_"
DPI = 144

ALPHAS = [(1.0, "#265d8a"), (2.0, "#a6541e"), (4.0, "#1f8a7a")]
MODELS = [
    ("poisson_glm", "Poisson GLM", "#e08a2c"),
    ("zip_glm", "ZIP-GLM", "#2f7238"),
    ("zinb_glm", "ZINB-GLM", "#d62728"),
    ("tabpfn", "TabPFN", "#265d8a"),
    ("tabpfn_log1p", "TabPFN (log1p)", "#8e5bb5"),
]
LABEL = {m: label for m, label, _ in MODELS}
COLOR = {m: color for m, _, color in MODELS}
PI0_LABEL = r"$\pi_0$ (zero-inflation probability)"


def load_zip_arm():
    frames = []
    for alpha, _ in ALPHAS:
        df = pd.read_csv(os.path.join(HERE, "results", f"alpha_{alpha}", "results.csv"))
        df["alpha"] = alpha
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    return df[df["arm"] == "zip"]


def style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xlabel(PI0_LABEL)


def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, PREFIX + name), dpi=DPI)
    plt.close(fig)


def where_tabpfn_sits(z):
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    sub = z[z["alpha"] == 1.0]
    for model, label in [("zip_glm", "ZIP-GLM (misspecified tail)"), ("tabpfn", "TabPFN"), ("zinb_glm", "ZINB-GLM (correctly specified)")]:
        m = sub[sub["model"] == model].groupby("pi0")["cont_nll_mean"].mean()
        ax.plot(m.index, m.values, marker="o", color=COLOR[model], label=label)
    ax.set_ylabel("continuity-corrected NLL (nats)")
    ax.set_title("TabPFN sits between the misspecified and correctly-specified GLM (alpha=1.0)")
    style(ax)
    ax.legend(frameon=False)
    save(fig, "where_tabpfn_sits.png")


def nll_gap_by_alpha(z):
    piv = z.groupby(["alpha", "model", "pi0"])["cont_nll_mean"].mean().unstack("model")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4), sharey=True)
    for ax, model in zip(axes, ["tabpfn", "zip_glm"]):
        for alpha, color in ALPHAS:
            p = piv.loc[alpha]
            gap = p[model] - p["zinb_glm"]
            ax.plot(gap.index, gap.values, marker="o", color=color, label=f"alpha={alpha:g}")
        ax.axhline(0, color="#999", linewidth=1, linestyle=":")
        ax.set_title(f"{LABEL[model]} minus ZINB-GLM")
        style(ax)
    axes[0].set_ylabel("continuity-corrected NLL gap (nats)")
    axes[0].legend(frameon=False)
    fig.suptitle("Gap to the correctly-specified model at each dispersion level (0 = as good as ZINB-GLM)")
    save(fig, "nll_gap_by_alpha.png")


def p_zero_error_by_alpha(z):
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2), sharey=True)
    for ax, (alpha, _) in zip(axes, ALPHAS):
        for model in ["zip_glm", "zinb_glm", "tabpfn"]:
            sub = z[(z["alpha"] == alpha) & (z["model"] == model)]
            err = (sub["p_zero_pred_mean"] - sub["p_zero_empirical"]).groupby(sub["pi0"]).mean()
            ax.plot(err.index, err.values, marker="o", color=COLOR[model], label=LABEL[model])
        ax.axhline(0, color="#999", linewidth=1, linestyle=":")
        ax.set_ylim(-0.05, 0.05)
        ax.set_title(f"alpha={alpha:g}")
        style(ax)
    axes[0].set_ylabel("P(Y=0) error (predicted - empirical)")
    axes[0].legend(frameon=False)
    fig.suptitle("Zero-rate calibration error at each dispersion level")
    save(fig, "p_zero_error_by_alpha.png")


def rmse_by_alpha(z):
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2))
    for ax, (alpha, _) in zip(axes, ALPHAS):
        sub = z[z["alpha"] == alpha]
        for model, label, color in MODELS:
            m = sub[sub["model"] == model].groupby("pi0")["rmse"].median()
            ax.plot(m.index, m.values, marker="o", markersize=4, color=color, label=label)
        ax.set_title(f"alpha={alpha:g}")
        style(ax)
    axes[0].set_ylabel("RMSE of predicted mean (median of 10 seeds)")
    axes[0].legend(frameon=False)
    fig.suptitle("Point-prediction error at each dispersion level")
    save(fig, "rmse_by_alpha.png")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    z = load_zip_arm()
    where_tabpfn_sits(z)
    nll_gap_by_alpha(z)
    p_zero_error_by_alpha(z)
    rmse_by_alpha(z)
    print(f"Charts written to {OUT_DIR}")


if __name__ == "__main__":
    main()
