"""Check that this environment regenerates the committed sweep's data, before adding a model to it.

run_sweep.py fills a new model into existing cells by regenerating each cell's (X, y) from its seed.
That is only sound if the rng streams and the DGP still produce the bytes the committed rows were
scored on -- numpy does not promise Generator streams are stable across versions. This script
redraws the requested cells, refits poisson_glm (deterministic: IRLS, no random start) and compares
the result with the committed row in results.csv.

Two kinds of column are compared:
- data-only (p_zero_empirical, train_y_max, test_y_max, frac_test_y_exceeds_train_max, n_test):
  these depend on the draw alone, so any difference means the data differ. Compared exactly.
- poisson_glm's metrics (rmse, mae, cont_nll_mean, native_nll_mean, p_zero_pred_mean): compared to
  a relative tolerance, since a different statsmodels/BLAS can move the last digits of a fit.

Spends nothing and needs no API key. Exit 0 if every cell matches, 1 otherwise.

Usage (from the repo root):
    python3 scripts/eval/zero_inflation/check_reproducible.py --alpha 1.0
    python3 scripts/eval/zero_inflation/check_reproducible.py --alpha 4.0 --seeds 0 9
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from dgp import draw_cells  # noqa: E402
from metrics import summarize  # noqa: E402
from models import PoissonGLM  # noqa: E402

FULL_PI0_GRID = [0.0, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]
DATA_COLUMNS = ["n_test", "p_zero_empirical", "train_y_max", "test_y_max", "frac_test_y_exceeds_train_max"]
FIT_COLUMNS = ["rmse", "mae", "cont_nll_mean", "native_nll_mean", "p_zero_pred_mean"]


def compare_cell(stored, fresh, rtol):
    problems = []
    for col in DATA_COLUMNS:
        if float(stored[col]) != float(fresh[col]):
            problems.append(f"{col}: committed {stored[col]!r}, regenerated {fresh[col]!r}")
    for col in FIT_COLUMNS:
        if not np.isclose(float(stored[col]), float(fresh[col]), rtol=rtol, atol=0.0):
            problems.append(f"{col}: committed {stored[col]!r}, refitted {fresh[col]!r}")
    return problems


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--alpha", type=float, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", default=[0], help="seeds to redraw (default: 0)")
    parser.add_argument("--n-train", type=int, default=1000)
    parser.add_argument("--n-test", type=int, default=1000)
    parser.add_argument("--rtol", type=float, default=1e-6)
    args = parser.parse_args()

    results_path = os.path.join(HERE, "results", f"alpha_{args.alpha}", "results.csv")
    committed = pd.read_csv(results_path)
    committed = committed[committed["model"] == "poisson_glm"].copy()
    committed["pi0_key"] = committed["pi0"].round(6)

    checked = mismatched = 0
    for seed in args.seeds:
        for arm, pi0, cell in draw_cells(seed, FULL_PI0_GRID, args.alpha, args.n_train, args.n_test):
            match = committed[(committed["arm"] == arm) & (committed["pi0_key"] == round(pi0, 6)) & (committed["seed"] == seed)]
            if len(match) != 1:
                print(f"seed={seed} arm={arm} pi0={pi0}: {len(match)} committed poisson_glm rows, expected 1")
                mismatched += 1
                continue
            m = PoissonGLM().fit(cell["x_glm_train"], cell["y_train"])
            nll = -m.log_pmf_at(cell["x_glm_test"], cell["y_test"])
            fresh = summarize(
                "poisson_glm", arm, pi0, seed, cell["y_test"], m.mean(cell["x_glm_test"]), nll, nll,
                m.p_zero(cell["x_glm_test"]), float(np.max(cell["y_train"])),
            )
            problems = compare_cell(match.iloc[0], fresh, args.rtol)
            checked += 1
            if problems:
                mismatched += 1
                print(f"MISMATCH seed={seed} arm={arm} pi0={pi0}")
                for p in problems:
                    print(f"  {p}")

    print(f"alpha={args.alpha}: {checked} cells checked, {mismatched} mismatched")
    sys.exit(1 if mismatched else 0)


if __name__ == "__main__":
    main()
