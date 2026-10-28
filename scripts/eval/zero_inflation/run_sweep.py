"""Sweep pi0 (zero-inflation probability) and compare Poisson-GLM, ZIP-GLM,
TabPFN, and log1p-transformed TabPFN (all in-context, hosted API) on
mean-matched Poisson vs zero-inflated-negative-binomial (ZINB) count data.

The "baseline" arm (plain Poisson(lambda(x))) does not depend on pi0, so it is
generated/fit once per seed rather than once per (seed, pi0) cell. The "zip"
arm (see dgp.sample_zinb -- overdispersed NB2 rather than Poisson under the
excess zeros) is generated fresh for every (seed, pi0) cell, reusing the same
X/lambda drawn for that seed.

Resume/extend granularity is per (arm, pi0, seed, model): rerunning this
script after adding a new model to MODEL_NAMES fills in only the missing
model's rows for every existing cell, without recomputing the others. The
random draws (X, y) are always regenerated in the original order regardless
of which models are skipped, so a newly-added model sees exactly the same
train/test data as the models already scored for that cell.

Results go to results/alpha_<alpha>/results.csv.

Usage (from the repo root, so the root .env is found):
    python3 scripts/eval/zero_inflation/run_sweep.py --alpha 1.0 --pilot
    python3 scripts/eval/zero_inflation/run_sweep.py --alpha 1.0
"""

import argparse
import os
import sys
import time

import numpy as np
import pandas as pd
import tabpfn_client

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(HERE, "..", "..", "..")))

from dgp import build_glm_exog, compute_lambda, generate_covariates, sample_poisson, sample_zinb  # noqa: E402
from metrics import summarize  # noqa: E402
from models import PoissonGLM, TabPFNLog1pModel, TabPFNModel, ZinbGLM, ZipGLM  # noqa: E402
from src.api_key import load_api_key  # noqa: E402

BASELINE_PI0 = -1.0  # sentinel for the pi0-invariant baseline arm
MODEL_NAMES = ["poisson_glm", "zip_glm", "zinb_glm", "tabpfn", "tabpfn_log1p"]


def fit_and_score(model_name, arm, pi0, seed, x_raw_train, x_raw_test, x_glm_train, x_glm_test, x_infl_train, x_infl_test, y_train, y_test, train_y_max):
    if model_name == "poisson_glm":
        m = PoissonGLM().fit(x_glm_train, y_train)
        nll = -m.log_pmf_at(x_glm_test, y_test)
        return summarize(model_name, arm, pi0, seed, y_test, m.mean(x_glm_test), nll, nll, m.p_zero(x_glm_test), train_y_max)

    if model_name == "zip_glm":
        m = ZipGLM().fit(x_glm_train, y_train, x_infl_train)
        nll = -m.log_pmf_at(x_glm_test, x_infl_test, y_test)
        return summarize(model_name, arm, pi0, seed, y_test, m.mean(x_glm_test, x_infl_test), nll, nll, m.p_zero(x_glm_test, x_infl_test), train_y_max)

    if model_name == "zinb_glm":
        m = ZinbGLM().fit(x_glm_train, y_train, x_infl_train)
        nll = -m.log_pmf_at(x_glm_test, x_infl_test, y_test)
        return summarize(model_name, arm, pi0, seed, y_test, m.mean(x_glm_test, x_infl_test), nll, nll, m.p_zero(x_glm_test, x_infl_test), train_y_max)

    if model_name in ("tabpfn", "tabpfn_log1p"):
        cls = TabPFNModel if model_name == "tabpfn" else TabPFNLog1pModel
        m = cls().fit(x_raw_train, y_train, categorical_features_indices=[4])
        m.predict_full(x_raw_test)
        native_nll = m.native_nll(y_test)
        cont_nll = m.continuity_nll(y_test)
        return summarize(model_name, arm, pi0, seed, y_test, m.mean(), native_nll, cont_nll, m.p_zero(), train_y_max)

    raise ValueError(f"unknown model {model_name}")


def evaluate_cell(models_needed, arm, pi0, seed, x_raw_train, x_raw_test, x_glm_train, x_glm_test, x_infl_train, x_infl_test, y_train, y_test):
    train_y_max = float(y_train.max())
    return [
        fit_and_score(m, arm, pi0, seed, x_raw_train, x_raw_test, x_glm_train, x_glm_test, x_infl_train, x_infl_test, y_train, y_test, train_y_max)
        for m in models_needed
    ]


def load_done_keys(results_path):
    if not os.path.exists(results_path):
        return set()
    existing = pd.read_csv(results_path)
    return set(zip(existing["arm"], existing["pi0"].round(6), existing["seed"], existing["model"]))


def append_rows(rows, results_path):
    if not rows:
        return
    df = pd.DataFrame(rows)
    header = not os.path.exists(results_path)
    df.to_csv(results_path, mode="a", header=header, index=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--alpha", type=float, required=True, help="NB2 dispersion of the zip arm (Var = mu + alpha * mu**2)")
    parser.add_argument("--pilot", action="store_true", help="small grid/seed count to validate the pipeline")
    parser.add_argument("--n-seeds", type=int, default=None)
    parser.add_argument("--n-train", type=int, default=1000)
    parser.add_argument("--n-test", type=int, default=1000)
    parser.add_argument("--pi0-grid", type=float, nargs="+", default=None)
    args = parser.parse_args()

    if args.pilot:
        pi0_grid = args.pi0_grid or [0.0, 0.5, 0.9]
        n_seeds = args.n_seeds or 2
    else:
        pi0_grid = args.pi0_grid or [0.0, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]
        n_seeds = args.n_seeds or 10

    n_train, n_test = args.n_train, args.n_test

    results_path = os.path.join(HERE, "results", f"alpha_{args.alpha}", "results.csv")
    os.makedirs(os.path.dirname(results_path), exist_ok=True)
    done = load_done_keys(results_path)

    load_api_key()
    tabpfn_client.set_access_token(os.environ["TABPFN_API_KEY"])

    total_cells = n_seeds * (1 + len(pi0_grid))
    cell_i = 0

    for seed in range(n_seeds):
        rng = np.random.default_rng(seed)
        x_raw_train = generate_covariates(rng, n_train)
        x_raw_test = generate_covariates(rng, n_test)
        lam_train = compute_lambda(x_raw_train)
        lam_test = compute_lambda(x_raw_test)
        x_glm_train, x_infl_train = build_glm_exog(x_raw_train)
        x_glm_test, x_infl_test = build_glm_exog(x_raw_test)

        # Baseline arm: draw y regardless (keeps the rng sequence identical to
        # earlier runs), but only fit/score models not already recorded.
        cell_i += 1
        y_train = sample_poisson(rng, lam_train)
        y_test = sample_poisson(rng, lam_test)
        needed = [m for m in MODEL_NAMES if ("baseline", round(BASELINE_PI0, 6), seed, m) not in done]
        if needed:
            t0 = time.time()
            rows = evaluate_cell(needed, "baseline", BASELINE_PI0, seed, x_raw_train, x_raw_test, x_glm_train, x_glm_test, x_infl_train, x_infl_test, y_train, y_test)
            append_rows(rows, results_path)
            print(f"[{cell_i}/{total_cells}] seed={seed} arm=baseline models={needed} done in {time.time()-t0:.1f}s")
        else:
            print(f"[{cell_i}/{total_cells}] seed={seed} arm=baseline already done, skipping")

        for pi0 in pi0_grid:
            cell_i += 1
            y_train = sample_zinb(rng, lam_train, pi0, alpha=args.alpha)
            y_test = sample_zinb(rng, lam_test, pi0, alpha=args.alpha)
            needed = [m for m in MODEL_NAMES if ("zip", round(pi0, 6), seed, m) not in done]
            if not needed:
                print(f"[{cell_i}/{total_cells}] seed={seed} arm=zip pi0={pi0} already done, skipping")
                continue
            t0 = time.time()
            rows = evaluate_cell(needed, "zip", pi0, seed, x_raw_train, x_raw_test, x_glm_train, x_glm_test, x_infl_train, x_infl_test, y_train, y_test)
            append_rows(rows, results_path)
            print(f"[{cell_i}/{total_cells}] seed={seed} arm=zip pi0={pi0} models={needed} done in {time.time()-t0:.1f}s")

    print(f"Done. Results at {results_path}")


if __name__ == "__main__":
    main()
