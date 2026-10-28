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
