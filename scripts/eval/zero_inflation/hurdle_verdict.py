"""The #662 analysis: two-stage against single-stage TabPFN, by the rule frozen on the ticket.

Reads only the committed CSVs (`results.csv` and `results_hurdle.csv` per alpha), spends nothing and
needs neither statsmodels nor an API key.

The bar (#662): per alpha, for each seed, average cont_nll_mean(tabpfn_hurdle) - cont_nll_mean(tabpfn)
over pi0 in {0.5, 0.6, 0.7, 0.8, 0.9, 0.95}, giving 10 paired values; a two-sided t-interval at
98.33% (Bonferroni over the three alphas). Met when the upper bound is below 0 at all three alphas;
falsified when, at any alpha, the lower bound is above 0. Otherwise UNRESOLVED.

Precondition: tabpfn_recheck against the committed tabpfn rows, mean |difference| in cont_nll_mean at
most 0.001 nats at every alpha, or the verdict is UNTESTED.

Everything printed under "alongside" is descriptive and carries no verdict.

Usage (from the repo root):
    python3 scripts/eval/zero_inflation/hurdle_verdict.py
"""

import os

import numpy as np
import pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
ALPHAS = ["1.0", "2.0", "4.0"]
HIGH_PI0 = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95]
LOW_PI0 = [0.0, 0.05, 0.1, 0.2, 0.3, 0.4]
CONFIDENCE = 1 - 0.05 / len(ALPHAS)
DRIFT_THRESHOLD = 0.001


def load(alpha):
    run_dir = os.path.join(HERE, "results", f"alpha_{alpha}")
    frames = [pd.read_csv(os.path.join(run_dir, name)) for name in ("results.csv", "results_hurdle.csv")]
    rows = pd.concat(frames, ignore_index=True)
    rows["pi0_key"] = rows["pi0"].round(6)
    return rows


def per_seed_contrast(rows, model, reference, grid, column="cont_nll_mean", arm="zip"):
    """Per seed, the mean over `grid` of model - reference; one value per seed."""
    keys = [round(p, 6) for p in grid]
    cells = rows[(rows["arm"] == arm) & rows["pi0_key"].isin(keys)]
    wide = cells.pivot_table(index=["seed", "pi0_key"], columns="model", values=column)
    if wide[[model, reference]].isna().any().any():
        raise SystemExit(f"missing cells for {model} or {reference} on {grid}")
    counts = wide.groupby("seed").size()
    if not (counts == len(keys)).all():
        raise SystemExit(f"a seed lacks some of the {len(keys)} pi0 cells: {counts.to_dict()}")
    return (wide[model] - wide[reference]).groupby("seed").mean()


def interval(values, confidence=CONFIDENCE):
    n = len(values)
    mean = float(values.mean())
    half = float(stats.t.ppf(1 - (1 - confidence) / 2, n - 1) * values.std(ddof=1) / np.sqrt(n))
    return mean, mean - half, mean + half


def drift(rows):
    recheck = rows[rows["model"] == "tabpfn_recheck"]
    committed = rows[rows["model"] == "tabpfn"]
    paired = recheck.merge(committed, on=["arm", "pi0_key", "seed"], suffixes=("_recheck", "_committed"))
    if len(paired) != len(recheck) or len(paired) == 0:
        raise SystemExit("tabpfn_recheck rows do not all pair with a committed tabpfn row")
    diff = (paired["cont_nll_mean_recheck"] - paired["cont_nll_mean_committed"]).abs()
    return len(paired), float(diff.mean()), float(diff.max()), int((diff > 0).sum())


def main():
    print(f"# #662 analysis — {CONFIDENCE:.2%} t-intervals, 10 seeds, nats of continuity-corrected NLL\n")

    print("## Precondition: drift control (tabpfn_recheck vs committed tabpfn)\n")
    print("| alpha | cells | mean abs diff | max abs diff | cells not bit-exact | precondition |")
    print("| --- | ---: | ---: | ---: | ---: | --- |")
    drift_ok = True
    for alpha in ALPHAS:
        n, mean, worst, nonzero = drift(load(alpha))
        ok = mean <= DRIFT_THRESHOLD
        drift_ok &= ok
        print(f"| {alpha} | {n} | {mean:.1e} | {worst:.1e} | {nonzero}/{n} | {'met' if ok else 'FAILED'} |")

    print("\n## The bar: tabpfn_hurdle - tabpfn, pi0 in {0.5 ... 0.95}\n")
    print("| alpha | mean | lower | upper | seed SD | seeds better | bar met | falsifier hit |")
    print("| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |")
    met_all, falsified_any = True, False
    for alpha in ALPHAS:
        values = per_seed_contrast(load(alpha), "tabpfn_hurdle", "tabpfn", HIGH_PI0)
        mean, lower, upper = interval(values)
        met, falsified = upper < 0, lower > 0
        met_all &= met
        falsified_any |= falsified
        print(
            f"| {alpha} | {mean:+.4f} | {lower:+.4f} | {upper:+.4f} | {values.std(ddof=1):.4f} | "
            f"{int((values < 0).sum())}/{len(values)} | {'yes' if met else 'no'} | {'yes' if falsified else 'no'} |"
        )

    if not drift_ok:
        verdict = "UNTESTED (drift precondition failed)"
    elif falsified_any:
        verdict = "REFUTED"
    elif met_all:
        verdict = "CONFIRMED"
    else:
        verdict = "UNRESOLVED"
    print(f"\n**Verdict by the frozen rule: {verdict}**\n")

    print("## Alongside, no verdict attached\n")
    contrasts = [
        ("tabpfn_hurdle - tabpfn, pi0 < 0.5", "tabpfn_hurdle", "tabpfn", LOW_PI0, "cont_nll_mean"),
        ("tabpfn - zinb_glm, pi0 >= 0.5", "tabpfn", "zinb_glm", HIGH_PI0, "cont_nll_mean"),
        ("tabpfn_hurdle - zinb_glm, pi0 >= 0.5", "tabpfn_hurdle", "zinb_glm", HIGH_PI0, "cont_nll_mean"),
        ("hurdle_nb_glm - zinb_glm, pi0 >= 0.5", "hurdle_nb_glm", "zinb_glm", HIGH_PI0, "cont_nll_mean"),
        ("hurdle_poisson_glm - zip_glm, pi0 >= 0.5", "hurdle_poisson_glm", "zip_glm", HIGH_PI0, "cont_nll_mean"),
        ("RMSE: tabpfn_hurdle - tabpfn, pi0 >= 0.5", "tabpfn_hurdle", "tabpfn", HIGH_PI0, "rmse"),
    ]
    print("| contrast | " + " | ".join(f"alpha = {a}" for a in ALPHAS) + " |")
    print("| --- |" + " --- |" * len(ALPHAS))
    loaded = {alpha: load(alpha) for alpha in ALPHAS}
    for label, model, reference, grid, column in contrasts:
        cells = []
        for alpha in ALPHAS:
            mean, lower, upper = interval(per_seed_contrast(loaded[alpha], model, reference, grid, column))
            cells.append(f"{mean:+.4f} [{lower:+.4f}, {upper:+.4f}]")
        print(f"| {label} | " + " | ".join(cells) + " |")

    baseline = []
    for alpha in ALPHAS:
        rows = loaded[alpha]
        wide = rows[rows["arm"] == "baseline"].pivot_table(index="seed", columns="model", values="cont_nll_mean")
        baseline.append(f"{(wide['tabpfn_hurdle'] - wide['tabpfn']).mean():+.4f}")
    print("| tabpfn_hurdle - tabpfn, baseline arm (mean only) | " + " | ".join(baseline) + " |")

    print("\nZero calibration, mean |predicted P(0) - empirical P(0)| over the pi0 >= 0.5 cells:\n")
    models = ["tabpfn", "tabpfn_hurdle", "zinb_glm", "hurdle_nb_glm"]
    print("| alpha | " + " | ".join(models) + " |")
    print("| --- |" + " ---: |" * len(models))
    for alpha in ALPHAS:
        rows = loaded[alpha]
        high = rows[(rows["arm"] == "zip") & rows["pi0_key"].isin([round(p, 6) for p in HIGH_PI0])]
        error = (high["p_zero_pred_mean"] - high["p_zero_empirical"]).abs().groupby(high["model"]).mean()
        print(f"| {alpha} | " + " | ".join(f"{error[m]:.4f}" for m in models) + " |")

    print("\nOne-class fallback cells (tabpfn_hurdle):\n")
    for alpha in ALPHAS:
        rows = loaded[alpha]
        hurdle = rows[rows["model"] == "tabpfn_hurdle"]
        used = hurdle[hurdle["hurdle_binary_fallback"].astype(str) == "True"]
        cells = ", ".join(f"{arm} seed {seed}" for arm, seed in zip(used["arm"], used["seed"])) or "none"
        print(f"- alpha = {alpha}: {len(used)} of {len(hurdle)} ({cells})")


if __name__ == "__main__":
    main()
