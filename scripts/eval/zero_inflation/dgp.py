"""Data-generating process: shared covariates/lambda, Poisson and ZINB sampling.

lambda(x) is identical for the baseline (Poisson) and "zip" arms. The "zip"
arm's internal NB2 rate is inflated to lambda(x) / (1 - pi0) so that
E[y_zip | x] == E[y_baseline | x] == lambda(x) exactly, row for row. The
non-structural-zero component is negative-binomial (NB2: Var = mu + alpha *
mu**2) rather than Poisson, so the arm carries overdispersion in addition to
excess zeros -- Poisson is the alpha -> 0 limit.
"""

import numpy as np
import pandas as pd

BETA0 = np.log(8.0)
BETA_CONT = np.array([0.25, -0.20, 0.15, 0.15])
CAT_LEVELS = [0, 1, 2]
CAT_EFFECT = {0: 0.0, 1: 0.25, 2: -0.20}
NB_ALPHA = 4.0  # NB2 dispersion of the non-structural-zero component: Var = mu + NB_ALPHA * mu**2


def generate_covariates(rng, n):
    x_cont = rng.normal(size=(n, 4))
    x_cat = rng.choice(CAT_LEVELS, size=n)
    df = pd.DataFrame(x_cont, columns=["x1", "x2", "x3", "x4"])
    df["x5_cat"] = x_cat
    return df


def compute_lambda(x_raw):
    eta = BETA0 + x_raw[["x1", "x2", "x3", "x4"]].to_numpy() @ BETA_CONT
    eta = eta + x_raw["x5_cat"].map(CAT_EFFECT).to_numpy()
    return np.exp(eta)


def sample_poisson(rng, lam):
    return rng.poisson(lam)


def sample_zinb(rng, lam, pi0, alpha=NB_ALPHA):
    mu_inflated = lam / (1.0 - pi0)
    n = 1.0 / alpha
    p = n / (n + mu_inflated)
    structural_zero = rng.random(len(lam)) < pi0
    counts = rng.negative_binomial(n, p)
    return np.where(structural_zero, 0, counts)


def build_glm_exog(x_raw):
    x5 = pd.Categorical(x_raw["x5_cat"], categories=CAT_LEVELS)
    dummies = pd.get_dummies(x5, prefix="x5", drop_first=True).astype(float)
    exog = pd.concat(
        [x_raw[["x1", "x2", "x3", "x4"]].reset_index(drop=True), dummies.reset_index(drop=True)],
        axis=1,
    )
    exog.insert(0, "const", 1.0)
    infl = np.ones((len(x_raw), 1))
    return exog, infl


BASELINE_PI0 = -1.0  # sentinel for the pi0-invariant baseline arm


def draw_cells(seed, pi0_grid, alpha, n_train, n_test):
    """Yield every (arm, pi0) cell of one seed, in the exact rng order the committed runs used.

    One rng per seed: covariates for train and test, then the baseline arm's Poisson draws, then
    one ZINB draw per pi0 in grid order. A cell's data therefore depends on every draw before it,
    so a model added later must consume the cells in this order, whichever models it skips --
    which is why the sweep and the reproducibility check both go through this one function.
    """
    rng = np.random.default_rng(seed)
    x_raw_train = generate_covariates(rng, n_train)
    x_raw_test = generate_covariates(rng, n_test)
    lam_train = compute_lambda(x_raw_train)
    lam_test = compute_lambda(x_raw_test)
    x_glm_train, x_infl_train = build_glm_exog(x_raw_train)
    x_glm_test, x_infl_test = build_glm_exog(x_raw_test)
    shared = {
        "x_raw_train": x_raw_train, "x_raw_test": x_raw_test,
        "x_glm_train": x_glm_train, "x_glm_test": x_glm_test,
        "x_infl_train": x_infl_train, "x_infl_test": x_infl_test,
    }

    y_train = sample_poisson(rng, lam_train)
    y_test = sample_poisson(rng, lam_test)
    yield "baseline", BASELINE_PI0, {**shared, "y_train": y_train, "y_test": y_test}

    for pi0 in pi0_grid:
        y_train = sample_zinb(rng, lam_train, pi0, alpha=alpha)
        y_test = sample_zinb(rng, lam_test, pi0, alpha=alpha)
        yield "zip", pi0, {**shared, "y_train": y_train, "y_test": y_test}
