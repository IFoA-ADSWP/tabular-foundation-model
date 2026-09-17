import argparse
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))

MODEL_ORDER = ["poisson_glm", "zip_glm", "zinb_glm", "tabpfn", "tabpfn_log1p"]
MODEL_LABEL = {"poisson_glm": "Poisson GLM", "zip_glm": "ZIP GLM", "zinb_glm": "ZINB GLM", "tabpfn": "TabPFN", "tabpfn_log1p": "TabPFN (log1p)"}
MODEL_COLOR = {"poisson_glm": "tab:orange", "zip_glm": "tab:green", "zinb_glm": "tab:red", "tabpfn": "tab:blue", "tabpfn_log1p": "tab:purple"}


def load(results_path):
    df = pd.read_csv(results_path)
    zip_df = df[df["arm"] == "zip"].copy()
    baseline_df = df[df["arm"] == "baseline"].copy()
    return zip_df, baseline_df


def agg(df, col):
    g = df.groupby(["model", "pi0"])[col]
    return g.mean().reset_index(), g.std().reset_index(name=f"{col}_sd")


def plot_metric(zip_df, baseline_df, col, ylabel, out_name, out_dir, logy=False):
    fig, ax = plt.subplots(figsize=(7, 5))
    mean_df, sd_df = agg(zip_df, col)
    for model in MODEL_ORDER:
        sub_m = mean_df[mean_df["model"] == model].sort_values("pi0")
        sub_s = sd_df[sd_df["model"] == model].sort_values("pi0")
        ax.errorbar(sub_m["pi0"], sub_m[col], yerr=sub_s[f"{col}_sd"], label=MODEL_LABEL[model], color=MODEL_COLOR[model], marker="o", capsize=3)
        if not baseline_df.empty:
            base_val = baseline_df[baseline_df["model"] == model][col].mean()
            ax.axhline(base_val, color=MODEL_COLOR[model], linestyle="--", alpha=0.4)
    ax.set_xlabel("pi0 (zero-inflation probability)")
    ax.set_ylabel(ylabel)
    if logy:
        ax.set_yscale("log")
    ax.set_title(ylabel + " vs pi0 (dashed = baseline Poisson, no inflation)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, out_name), dpi=150)
    plt.close(fig)


def plot_p_zero_calibration(zip_df, out_dir, out_name="p_zero_calibration.png"):
    fig, ax = plt.subplots(figsize=(7, 5))
    for model in MODEL_ORDER:
        sub = zip_df[zip_df["model"] == model].groupby("pi0")[["p_zero_pred_mean", "p_zero_empirical"]].mean().reset_index().sort_values("pi0")
        ax.plot(sub["pi0"], sub["p_zero_pred_mean"], label=f"{MODEL_LABEL[model]} predicted", color=MODEL_COLOR[model], marker="o")
    ref = zip_df.groupby("pi0")["p_zero_empirical"].mean().reset_index().sort_values("pi0")
    ax.plot(ref["pi0"], ref["p_zero_empirical"], label="empirical", color="black", linestyle=":", marker="x")
    ax.set_xlabel("pi0 (zero-inflation probability)")
    ax.set_ylabel("P(Y=0)")
    ax.set_title("Predicted vs empirical P(Y=0)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, out_name), dpi=150)
    plt.close(fig)


def print_summary(zip_df):
    print("\n=== Non-finite native-NLL onset (TabPFN) ===")
    tp = zip_df[zip_df["model"] == "tabpfn"].groupby("pi0")["native_nll_frac_nonfinite"].mean().sort_index()
    print(tp.to_string())
    nonzero = tp[tp > 0]
    if len(nonzero):
        print(f"First pi0 with any non-finite native loss: {nonzero.index[0]}")
    else:
        print("No non-finite native losses observed in this run.")

    print("\n=== Continuity-corrected NLL: TabPFN - ZIP-GLM (positive = TabPFN worse) ===")
    piv = zip_df.groupby(["model", "pi0"])["cont_nll_mean"].mean().unstack("model")
    if "tabpfn" in piv and "zip_glm" in piv:
        diff = (piv["tabpfn"] - piv["zip_glm"]).sort_index()
        print(diff.to_string())

    print("\n=== Continuity-corrected NLL: TabPFN-log1p - ZIP-GLM (positive = TabPFN-log1p worse) ===")
    if "tabpfn_log1p" in piv and "zip_glm" in piv:
        diff = (piv["tabpfn_log1p"] - piv["zip_glm"]).sort_index()
        print(diff.to_string())

    print("\n=== Continuity-corrected NLL: TabPFN-log1p - TabPFN (positive = log1p transform hurts) ===")
    if "tabpfn_log1p" in piv and "tabpfn" in piv:
        diff = (piv["tabpfn_log1p"] - piv["tabpfn"]).sort_index()
        print(diff.to_string())

    print("\n=== Continuity-corrected NLL: TabPFN - ZINB-GLM (positive = TabPFN worse; ZINB-GLM is correctly specified) ===")
    if "tabpfn" in piv and "zinb_glm" in piv:
        diff = (piv["tabpfn"] - piv["zinb_glm"]).sort_index()
        print(diff.to_string())

    print("\n=== Continuity-corrected NLL: ZIP-GLM - ZINB-GLM (positive = misspecified tail costs ZIP-GLM) ===")
    if "zip_glm" in piv and "zinb_glm" in piv:
        diff = (piv["zip_glm"] - piv["zinb_glm"]).sort_index()
        print(diff.to_string())

    print("\n=== P(Y=0) calibration error: predicted - empirical ===")
    for model in MODEL_ORDER:
        sub = zip_df[zip_df["model"] == model]
        err = (sub["p_zero_pred_mean"] - sub["p_zero_empirical"]).groupby(sub["pi0"]).mean()
        print(f"-- {MODEL_LABEL[model]} --")
        print(err.to_string())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--alpha", type=float, required=True, help="which results/alpha_<alpha>/ run to plot")
    args = parser.parse_args()
    out_dir = os.path.join(HERE, "results", f"alpha_{args.alpha}")

    zip_df, baseline_df = load(os.path.join(out_dir, "results.csv"))

    plot_metric(zip_df, baseline_df, "native_nll_mean", "Native NLL (own predictive distribution)", "native_nll_vs_pi0.png", out_dir)
    plot_metric(zip_df, baseline_df, "cont_nll_mean", "Continuity-corrected NLL (comparable across models)", "cont_nll_vs_pi0.png", out_dir)
    plot_metric(zip_df, baseline_df, "native_nll_frac_nonfinite", "Fraction non-finite native loss", "frac_nonfinite_vs_pi0.png", out_dir)
    plot_metric(zip_df, baseline_df, "rmse", "RMSE of predicted mean", "rmse_vs_pi0.png", out_dir)
    plot_metric(zip_df, baseline_df, "mae", "MAE of predicted mean", "mae_vs_pi0.png", out_dir)
    plot_p_zero_calibration(zip_df, out_dir)

    print_summary(zip_df)
    print(f"\nPlots written to {out_dir}")


if __name__ == "__main__":
    main()
