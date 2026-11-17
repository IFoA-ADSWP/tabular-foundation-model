"""Hurdle arithmetic shared by the GLM and TabPFN hurdle models.

A hurdle model splits a count into two independent parts:

    P(Y = 0 | x)      = 1 - p(x)                        # the hurdle: a binary model
    P(Y = k | x)      = p(x) * g(k | x) / (1 - g(0 | x))  for k >= 1  # a count model truncated at zero

so every zero comes from the binary part and every positive count from the truncated part. This
module holds only numpy arithmetic, so it can be tested without statsmodels or the hosted client.

For TabPFN the "count model" is the regressor's continuous predictive distribution, fit on the
positive training rows only. Its mass on k is the continuity-corrected interval [k - 1/2, k + 1/2],
and the truncation renormalises by the mass above 1/2, because a regressor trained on y >= 1 can
still put some probability below 1/2.
"""

import numpy as np

TINY = 1e-300
MIN_TRUNCATED_MASS = 1e-12


def smoothed_positive_rate(y):
    """P(Y > 0) estimated as (n_pos + 1/2) / (n + 1).

    The fallback for a binary part that cannot be fitted because the training set has no zeros
    or no positives (the Poisson baseline arm at lambda ~ 8 has only a handful of zeros in
    1,000 rows, and sometimes none). Smoothing keeps both log(p) and log(1 - p) finite.
    """
    y = np.asarray(y)
    return (float(np.sum(y > 0)) + 0.5) / (len(y) + 1.0)


def hurdle_log_pmf(p_pos, log_trunc_pmf_pos, y):
    """Per-row log P(Y = y) under a hurdle model.

    p_pos: P(Y > 0) per row. log_trunc_pmf_pos: log of the zero-truncated count pmf at y, per
    row; read only where y > 0, so its value at y == 0 rows is ignored.
    """
    y = np.asarray(y)
    p_pos = np.clip(np.asarray(p_pos, dtype=float), TINY, 1.0 - 1e-16)
    log_trunc = np.asarray(log_trunc_pmf_pos, dtype=float)
    return np.where(y == 0, np.log1p(-p_pos), np.log(p_pos) + np.where(y == 0, 0.0, log_trunc))


def truncated_interval_log_mass(cdf_upper, cdf_lower, cdf_half):
    """log of the continuity-corrected mass on k, renormalised to the part above 1/2.

    cdf_upper = F(k + 1/2), cdf_lower = F(k - 1/2), cdf_half = F(1/2), all per row.
    """
    upper = np.asarray(cdf_upper, dtype=float)
    lower = np.asarray(cdf_lower, dtype=float)
    above_half = np.clip(1.0 - np.asarray(cdf_half, dtype=float), MIN_TRUNCATED_MASS, 1.0)
    mass = np.clip(upper - lower, TINY, 1.0)
    return np.log(mass) - np.log(above_half)


def truncation_quantile_levels(cdf_half, n_levels):
    """Midpoint quantile levels of the distribution truncated to (1/2, inf), per row.

    Returns an (n, n_levels) array u with u[i, j] = F_i(1/2) + (1 - F_i(1/2)) * (j + 1/2) / n_levels.
    Averaging the inverse CDF at these levels is the midpoint rule for E[Z | Z > 1/2]: deterministic,
    so the mean does not move between reruns the way a Monte Carlo draw would.
    """
    f0 = np.clip(np.asarray(cdf_half, dtype=float), 0.0, 1.0 - MIN_TRUNCATED_MASS).reshape(-1, 1)
    grid = (np.arange(n_levels) + 0.5) / n_levels
    return f0 + (1.0 - f0) * grid.reshape(1, -1)
