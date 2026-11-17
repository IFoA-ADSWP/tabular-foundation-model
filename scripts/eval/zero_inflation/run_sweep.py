"""Sweep pi0 (zero-inflation probability) and compare Poisson-GLM, ZIP-GLM, ZINB-GLM,
TabPFN and log1p-transformed TabPFN (hosted API) on mean-matched Poisson vs
zero-inflated-negative-binomial (ZINB) count data -- and, since #159's hurdle
extension, the hurdle GLMs and two-stage TabPFN.

The "baseline" arm (plain Poisson(lambda(x))) does not depend on pi0, so it is
generated/fit once per seed rather than once per (seed, pi0) cell. The "zip"
arm (see dgp.sample_zinb -- overdispersed NB2 rather than Poisson under the
excess zeros) is generated fresh for every (seed, pi0) cell, reusing the same
X/lambda drawn for that seed.

Resume/extend granularity is per (arm, pi0, seed, model): rerunning this
script after adding a new model fills in only the missing model's rows for
every existing cell, without recomputing the others. The random draws (X, y)
are always regenerated in the original order (dgp.draw_cells) regardless of
which models are skipped, so a newly-added model sees exactly the same
train/test data as the models already scored for that cell. Verify that this
still holds in the current environment with check_reproducible.py before
adding a model.

Two result files per alpha:
- results/alpha_<alpha>/results.csv -- the five original models (committed
  evidence; its sha256 is in figures/manifest.json).
- results/alpha_<alpha>/results_hurdle.csv -- the hurdle extension, kept apart
  so the original evidence is never rewritten: hurdle_poisson_glm,
  hurdle_nb_glm, tabpfn_hurdle, and tabpfn_recheck (a fresh plain-TabPFN fit,
  scored like `tabpfn`, as a control that the hosted v3.5_default still
  returns what it returned when results.csv was written).

`tabpfn_recheck` is opt-in (--models). The API key is loaded only when a
TabPFN model still has a missing cell, so a GLM-only run needs no key and
spends nothing.

Usage (from the repo root, so the root .env is found):
    python3 scripts/eval/zero_inflation/run_sweep.py --alpha 1.0 --pilot
    python3 scripts/eval/zero_inflation/run_sweep.py --alpha 1.0
    python3 scripts/eval/zero_inflation/run_sweep.py --alpha 1.0 --models hurdle_poisson_glm hurdle_nb_glm
    python3 scripts/eval/zero_inflation/run_sweep.py --alpha 1.0 --models tabpfn_recheck --n-seeds 2
"""

import argparse
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(HERE, "..", "..", "..")))

from dgp import draw_cells  # noqa: E402
from metrics import summarize  # noqa: E402
from models import (  # noqa: E402
    HurdleNbGLM,
    HurdlePoissonGLM,
    PoissonGLM,
    TabPFNHurdleModel,
    TabPFNLog1pModel,
    TabPFNModel,
    ZinbGLM,
    ZipGLM,
)

ORIGINAL_MODELS = ["poisson_glm", "zip_glm", "zinb_glm", "tabpfn", "tabpfn_log1p"]
HURDLE_MODELS = ["hurdle_poisson_glm", "hurdle_nb_glm", "tabpfn_hurdle", "tabpfn_recheck"]
MODEL_NAMES = ORIGINAL_MODELS + HURDLE_MODELS
DEFAULT_MODELS = [m for m in MODEL_NAMES if m != "tabpfn_recheck"]
TABPFN_MODELS = {"tabpfn", "tabpfn_log1p", "tabpfn_hurdle", "tabpfn_recheck"}
TABPFN_CATEGORICAL = [4]  # x5_cat


def results_file(model_name):
    return "results_hurdle.csv" if model_name in HURDLE_MODELS else "results.csv"


def fit_and_score(model_name, arm, pi0, seed, cell, train_y_max):
    y_train, y_test = cell["y_train"], cell["y_test"]
    x_glm_train, x_glm_test = cell["x_glm_train"], cell["x_glm_test"]
    x_infl_train, x_infl_test = cell["x_infl_train"], cell["x_infl_test"]

    def score(mean, native_nll, cont_nll, p_zero):
        return summarize(model_name, arm, pi0, seed, y_test, mean, native_nll, cont_nll, p_zero, train_y_max)

    if model_name == "poisson_glm":
        m = PoissonGLM().fit(x_glm_train, y_train)
        nll = -m.log_pmf_at(x_glm_test, y_test)
        return score(m.mean(x_glm_test), nll, nll, m.p_zero(x_glm_test))

    if model_name in ("zip_glm", "zinb_glm"):
        m = (ZipGLM if model_name == "zip_glm" else ZinbGLM)().fit(x_glm_train, y_train, x_infl_train)
        nll = -m.log_pmf_at(x_glm_test, x_infl_test, y_test)
        return score(m.mean(x_glm_test, x_infl_test), nll, nll, m.p_zero(x_glm_test, x_infl_test))

    if model_name in ("hurdle_poisson_glm", "hurdle_nb_glm"):
        m = (HurdlePoissonGLM if model_name == "hurdle_poisson_glm" else HurdleNbGLM)().fit(x_glm_train, y_train)
        nll = -m.log_pmf_at(x_glm_test, y_test)
        row = score(m.mean(x_glm_test), nll, nll, m.p_zero(x_glm_test))
        row["hurdle_binary_fallback"] = m.binary_fallback
        return row

    if model_name in ("tabpfn", "tabpfn_log1p", "tabpfn_recheck"):
        cls = TabPFNLog1pModel if model_name == "tabpfn_log1p" else TabPFNModel
        m = cls().fit(cell["x_raw_train"], y_train, categorical_features_indices=TABPFN_CATEGORICAL)
        m.predict_full(cell["x_raw_test"])
        row = score(m.mean(), m.native_nll(y_test), m.continuity_nll(y_test), m.p_zero())
        if model_name == "tabpfn_recheck":
            row["hurdle_binary_fallback"] = False
        return row

    if model_name == "tabpfn_hurdle":
        m = TabPFNHurdleModel().fit(cell["x_raw_train"], y_train, categorical_features_indices=TABPFN_CATEGORICAL)
        m.predict_full(cell["x_raw_test"])
        row = score(m.mean(), m.native_nll(y_test), m.continuity_nll(y_test), m.p_zero())
        # The zero is a point mass: there is no native density to fail, so the fraction is
        # undefined rather than 100%.
        row["native_nll_frac_nonfinite"] = float("nan")
        row["hurdle_binary_fallback"] = m.binary_fallback
        return row

    raise ValueError(f"unknown model {model_name}")


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


def ensure_api_key():
    import tabpfn_client
    from src.api_key import load_api_key

    load_api_key()
    tabpfn_client.set_access_token(os.environ["TABPFN_API_KEY"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--alpha", type=float, required=True, help="NB2 dispersion of the zip arm (Var = mu + alpha * mu**2)")
    parser.add_argument("--pilot", action="store_true", help="small grid/seed count to validate the pipeline")
    parser.add_argument("--n-seeds", type=int, default=None)
    parser.add_argument("--n-train", type=int, default=1000)
    parser.add_argument("--n-test", type=int, default=1000)
    parser.add_argument("--pi0-grid", type=float, nargs="+", default=None)
    parser.add_argument(
        "--models", nargs="+", choices=MODEL_NAMES, default=DEFAULT_MODELS,
        help="models to fill in (default: all but tabpfn_recheck); cells already recorded are skipped",
    )
    args = parser.parse_args()

    if args.pilot:
        pi0_grid = args.pi0_grid or [0.0, 0.5, 0.9]
        n_seeds = args.n_seeds or 2
    else:
        pi0_grid = args.pi0_grid or [0.0, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]
        n_seeds = args.n_seeds or 10

    run_dir = os.path.join(HERE, "results", f"alpha_{args.alpha}")
    os.makedirs(run_dir, exist_ok=True)
    paths = {name: os.path.join(run_dir, name) for name in ("results.csv", "results_hurdle.csv")}
    done = load_done_keys(paths["results.csv"]) | load_done_keys(paths["results_hurdle.csv"])

    total_cells = n_seeds * (1 + len(pi0_grid))
    cell_i = 0
    api_ready = False

    for seed in range(n_seeds):
        for arm, pi0, cell in draw_cells(seed, pi0_grid, args.alpha, args.n_train, args.n_test):
            cell_i += 1
            label = f"[{cell_i}/{total_cells}] seed={seed} arm={arm}" + ("" if arm == "baseline" else f" pi0={pi0}")
            needed = [m for m in args.models if (arm, round(pi0, 6), seed, m) not in done]
            if not needed:
                print(f"{label} already done, skipping")
                continue
            if not api_ready and TABPFN_MODELS.intersection(needed):
                ensure_api_key()
                api_ready = True
            t0 = time.time()
            train_y_max = float(np.max(cell["y_train"]))
            rows = [fit_and_score(m, arm, pi0, seed, cell, train_y_max) for m in needed]
            for file_name, path in paths.items():
                append_rows([r for r in rows if results_file(r["model"]) == file_name], path)
            print(f"{label} models={needed} done in {time.time() - t0:.1f}s")

    print(f"Done. Results in {run_dir}")


if __name__ == "__main__":
    main()
