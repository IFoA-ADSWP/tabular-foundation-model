"""The chart in docs/experiments/zero-inflation/ZERO_INFLATION_HURDLE_RESULT.md.

One panel per alpha: the continuity-corrected NLL gap to the correctly specified ZINB-GLM, for
single-stage TabPFN and two-stage (hurdle) TabPFN, against pi0. Each point is the mean over the
10 seeds, with a 95% t-interval. The shaded range is where #662's bar was measured (pi0 >= 0.5).

Reads only the committed CSVs and spends nothing. Writes figures/hurdle_gap_by_alpha.png and
figures/hurdle_manifest.json: the commit, whether the tree was clean, and a sha256 per source
script and results file. The September charts keep their own manifest.json, untouched.

Usage (from the repo root):
    python3 scripts/eval/zero_inflation/make_hurdle_chart.py
"""

import hashlib
import json
import os
import subprocess

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "figures")
FIGURE = "hurdle_gap_by_alpha.png"
MANIFEST = "hurdle_manifest.json"
ALPHAS = ["1.0", "2.0", "4.0"]
RESULT_FILES = [f"results/alpha_{a}/{name}" for a in ALPHAS for name in ("results.csv", "results_hurdle.csv")]
SOURCE_SCRIPTS = ["make_hurdle_chart.py", "hurdle_verdict.py", "run_sweep.py", "models.py", "hurdle.py", "dgp.py", "metrics.py"]
DPI = 144

# TabPFN keeps its colour from the September charts; the hurdle takes an orange, the pair that stays
# apart under every common colour-vision deficiency. Marker and line style differ as well, so the
# series never rely on colour alone.
SERIES = [
    ("tabpfn", "TabPFN, single-stage", "#265d8a", "o", "-"),
    ("tabpfn_hurdle", "TabPFN, two-stage (hurdle)", "#c8641c", "s", "--"),
]
REFERENCE = "zinb_glm"


def gap_by_pi0(rows, model):
    zip_arm = rows[rows["arm"] == "zip"]
    wide = zip_arm.pivot_table(index=["pi0", "seed"], columns="model", values="cont_nll_mean")
    diff = (wide[model] - wide[REFERENCE]).groupby("pi0")
    mean, sd, n = diff.mean(), diff.std(ddof=1), diff.size()
    half = stats.t.ppf(0.975, n - 1) * sd / np.sqrt(n)
    return mean, half


def sha256(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def main():
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.2), sharey=True)
    for ax, alpha in zip(axes, ALPHAS):
        run_dir = os.path.join(HERE, "results", f"alpha_{alpha}")
        rows = pd.concat([pd.read_csv(os.path.join(run_dir, f)) for f in ("results.csv", "results_hurdle.csv")])
        ax.axvspan(0.475, 0.975, color="#000000", alpha=0.05, linewidth=0)
        ax.axhline(0.0, color="#555555", linewidth=1.0)
        for model, label, color, marker, line in SERIES:
            mean, half = gap_by_pi0(rows, model)
            ax.errorbar(
                mean.index, mean.values, yerr=half.values, color=color, marker=marker, linestyle=line,
                linewidth=2, markersize=6, capsize=3, label=label,
            )
        ax.set_title(f"α = {float(alpha):g}")
        ax.set_xlabel(r"$\pi_0$ (share of structural zeros)")
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", color="#e5e5e5", linewidth=0.8)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("NLL gap to ZINB-GLM (nats)\npositive = worse than the correct model")
    axes[0].text(0.5, 0.995, "range of the bar", transform=axes[0].get_xaxis_transform(), ha="left", va="top",
                 fontsize=9, color="#555555")
    axes[0].text(0.0, 0.0015, "ZINB-GLM (correctly specified)", fontsize=9, color="#555555", va="bottom")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 1.0))
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    os.makedirs(OUT_DIR, exist_ok=True)
    fig.savefig(os.path.join(OUT_DIR, FIGURE), dpi=DPI)
    plt.close(fig)

    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=HERE).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--", *SOURCE_SCRIPTS, *RESULT_FILES],
        capture_output=True, text=True, cwd=HERE,
    ).stdout.strip()
    manifest = {
        "figure": FIGURE,
        "commit": commit,
        "sources_uncommitted_at_generation": bool(dirty),
        "scripts": {name: sha256(os.path.join(HERE, name)) for name in SOURCE_SCRIPTS},
        "results": {name: sha256(os.path.join(HERE, name)) for name in RESULT_FILES},
    }
    with open(os.path.join(OUT_DIR, MANIFEST), "w") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")
    print(f"wrote {FIGURE} and {MANIFEST} in {OUT_DIR}")


if __name__ == "__main__":
    main()
