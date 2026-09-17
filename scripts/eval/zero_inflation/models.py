"""Thin wrappers around Poisson-GLM, ZIP-GLM, ZINB-GLM and TabPFN exposing a
common interface: mean(), p_zero(), and per-row log-densities at held-out y.
"""

import numpy as np
import statsmodels.api as sm
import torch
from scipy.stats import poisson as sp_poisson
from statsmodels.discrete.count_model import ZeroInflatedNegativeBinomialP, ZeroInflatedPoisson
from tabpfn_client import TabPFNRegressor

# Pinned: the server's unpinned default moved from v3 to v3.5 on 2026-09-15.
MODEL_PATH = "v3.5_default"


class PoissonGLM:
    name = "poisson_glm"

    def fit(self, x_glm, y):
        self.result = sm.GLM(y, x_glm, family=sm.families.Poisson()).fit()
        return self

    def mean(self, x_glm):
        return np.asarray(self.result.predict(x_glm), dtype=float)

    def p_zero(self, x_glm):
        return np.exp(-self.mean(x_glm))

    def log_pmf_at(self, x_glm, y):
        lam = self.mean(x_glm)
        return sp_poisson.logpmf(np.asarray(y, dtype=int), lam)


class ZipGLM:
    name = "zip_glm"

    def fit(self, x_glm, y, x_infl):
        self.model = ZeroInflatedPoisson(y, x_glm, exog_infl=x_infl, inflation="logit")
        self.result = self.model.fit(disp=False, maxiter=200)
        return self

    def mean(self, x_glm, x_infl):
        out = self.result.predict(exog=x_glm, exog_infl=x_infl, which="mean")
        return np.asarray(out, dtype=float)

    def p_zero(self, x_glm, x_infl):
        out = self.result.predict(exog=x_glm, exog_infl=x_infl, which="prob-zero")
        return np.asarray(out, dtype=float)

    def log_pmf_at(self, x_glm, x_infl, y):
        y = np.asarray(y, dtype=int)
        y_max = int(y.max())
        grid = np.asarray(
            self.result.predict(exog=x_glm, exog_infl=x_infl, which="prob", y_values=np.arange(0, y_max + 1)),
            dtype=float,
        )
        idx = np.clip(y, 0, y_max)
        p = grid[np.arange(len(y)), idx]
        p = np.clip(p, 1e-300, 1.0)
        return np.log(p)


class ZinbGLM:
    """Zero-inflated negative binomial (NB2), the correctly-specified model
    for the "zip" arm's DGP: same logit zero-inflation as ZipGLM, but the
    count component estimates its own dispersion (alpha) instead of assuming
    Poisson (Var=Mean).

    statsmodels' BFGS fit is fragile on this DGP in two distinct ways, both
    of which land on a negative fitted alpha -- mathematically invalid, and
    it silently makes mean()/p_zero() degenerate (e.g. predicted mean
    collapsing to exactly 0) rather than raising:

    1. Small, extremely heavy-tailed non-zero training subsample at high
       pi0 -- fixed by retrying from an explicit alpha=1.0 starting point
       instead of statsmodels' all-zeros default.
    2. True zero-inflation near 0 (e.g. the pi0-invariant baseline arm,
       which is plain Poisson): the inflation logit's MLE is at/near the
       boundary of its parameter space, so BFGS drives its intercept to
       +-1000+ from *any* starting point and never converges, dragging
       alpha along with it. Fixed by switching optimizer (L-BFGS) rather
       than just the starting point -- confirmed to land on a small,
       plausible alpha (~0.14, i.e. near-Poisson) on every case tested.
    """

    name = "zinb_glm"

    def fit(self, x_glm, y, x_infl):
        self.model = ZeroInflatedNegativeBinomialP(y, x_glm, exog_infl=x_infl, inflation="logit", p=2)
        n_params = np.asarray(x_glm).shape[1] + np.asarray(x_infl).shape[1] + 1
        start_params = np.zeros(n_params)
        start_params[-1] = 1.0

        self.result = self.model.fit(disp=False, maxiter=200)
        if not self._usable(self.result):
            self.result = self.model.fit(start_params=start_params, disp=False, maxiter=200)
        if not self._usable(self.result):
            self.result = self.model.fit(start_params=start_params, disp=False, maxiter=500, method="lbfgs")
        return self

    @staticmethod
    def _usable(result):
        # mle_retvals["converged"] isn't populated consistently across
        # statsmodels optimizers (e.g. lbfgs never sets it), so validity is
        # judged directly by what actually breaks mean()/p_zero() downstream:
        # a positive dispersion and a finite achieved log-likelihood.
        return result.params[-1] > 0 and np.isfinite(result.llf)

    def mean(self, x_glm, x_infl):
        out = self.result.predict(exog=x_glm, exog_infl=x_infl, which="mean")
        return np.asarray(out, dtype=float)

    def p_zero(self, x_glm, x_infl):
        out = self.result.predict(exog=x_glm, exog_infl=x_infl, which="prob-zero")
        return np.asarray(out, dtype=float)

    def log_pmf_at(self, x_glm, x_infl, y):
        y = np.asarray(y, dtype=int)
        y_max = int(y.max())
        grid = np.asarray(
            self.result.predict(exog=x_glm, exog_infl=x_infl, which="prob", y_values=np.arange(0, y_max + 1)),
            dtype=float,
        )
        idx = np.clip(y, 0, y_max)
        p = grid[np.arange(len(y)), idx]
        p = np.clip(p, 1e-300, 1.0)
        return np.log(p)


def _icdf_batch(criterion, logits, left_probs):
    """Vectorized batched quantile function.

    logits: (n, num_bars). left_probs: (n, K) -- K quantile targets per row
    (K=1 for a single shared query per row, e.g. the median).

    Unlike calling FullSupportBarDistribution.icdf per-sample, this computes
    the per-row softmax/cumsum ONCE (n, num_bars) and reuses it for all K
    targets via torch.searchsorted's/gather's batch broadcasting -- it never
    materializes an (n, K, num_bars) tensor. (An earlier version expanded
    logits to that shape before calling softmax, which for n=1000, K=200,
    num_bars=5000 allocates ~8GB and can bring a machine to a crawl.)
    """
    probs = torch.softmax(logits, -1)  # (n, num_bars)
    cumprobs = torch.cumsum(probs, -1)  # (n, num_bars)
    idx = torch.searchsorted(cumprobs, left_probs).clamp(0, cumprobs.shape[-1] - 1)  # (n, K)
    zeros = torch.zeros(cumprobs.shape[0], 1, dtype=cumprobs.dtype)
    cumprobs_padded = torch.cat([zeros, cumprobs], dim=-1)  # (n, num_bars+1)
    prob_left = cumprobs_padded.gather(-1, idx)  # (n, K)
    rest_prob = left_probs - prob_left
    left_border = criterion.borders[idx]  # (n, K)
    right_border = criterion.borders[idx + 1]  # (n, K)
    p_bucket = probs.gather(-1, idx)  # (n, K)
    return left_border + (right_border - left_border) * rest_prob / p_bucket


class _TabPFNBase:
    def fit(self, x_raw, y, categorical_features_indices=None):
        y = np.asarray(y, dtype=float)
        self._train_y_max = float(y.max())
        self.reg = TabPFNRegressor(model_path=MODEL_PATH, random_state=0, categorical_features_indices=categorical_features_indices)
        self.reg.fit(x_raw, self._to_model_scale(y))
        return self

    def predict_full(self, x_raw):
        full = self.reg.predict(x_raw, output_type="full")
        self._logits = torch.as_tensor(full["logits"], dtype=torch.float64)
        self._criterion = full["criterion"]
        return self

    def _cdf_at_model_scale(self, model_values):
        v = torch.as_tensor(np.asarray(model_values, dtype=float), dtype=torch.float64).reshape(-1, 1)
        with torch.no_grad():
            out = self._criterion.cdf(self._logits, v).squeeze(-1)
        return out.numpy()

    def _to_model_scale(self, y):
        raise NotImplementedError

    def _cdf_at(self, y_values):
        return self._cdf_at_model_scale(self._to_model_scale(np.asarray(y_values, dtype=float)))

    def p_zero(self):
        return self._cdf_at(np.full(self._logits.shape[0], 0.5))

    def continuity_nll(self, y):
        y = np.asarray(y, dtype=float)
        upper = self._cdf_at(y + 0.5)
        lower = self._cdf_at(y - 0.5)
        mass = np.clip(upper - lower, 1e-300, 1.0)
        return -np.log(mass)


class TabPFNModel(_TabPFNBase):
    """TabPFN fit directly on the raw count target."""

    name = "tabpfn"

    def _to_model_scale(self, y):
        return y

    def mean(self):
        return self._criterion.mean(self._logits).numpy()

    def native_nll(self, y):
        y_t = torch.as_tensor(np.asarray(y, dtype=float), dtype=torch.float64)
        with torch.no_grad():
            nll = self._criterion.forward(self._logits, y_t)
        return nll.numpy()


class TabPFNLog1pModel(_TabPFNBase):
    """TabPFN fit on log1p(y); predictions are mapped back to the original
    count scale. The median and CDF-based quantities (p_zero, continuity_nll)
    commute exactly with the monotonic log1p transform. The mean does not, so
    it's estimated by Monte Carlo sampling in log1p-space (via a vectorized
    batch quantile function) and back-transforming with expm1. The native NLL
    needs a Jacobian correction: f_Y(y) = f_Z(log1p(y)) / (1 + y).

    FullSupportBarDistribution's histogram is piecewise-uniform in log1p-space,
    with residual (non-zero but tiny, ~1e-6) probability routinely leaked into
    bins tens of log1p-units wide out past the observed data. expm1 of a
    uniform density is dominated by its bin's right edge, so a handful of MC
    draws landing in those bins can make the raw sample mean explode by 30-70
    orders of magnitude -- this is exact given the fitted histogram, not a
    quantile-function bug (verified: even the closed-form E[e^Z] blows up the
    same way). Since nothing beyond the observed training range is actually
    informative here, MC draws are clipped to a generous multiple of the
    largest count seen in training before averaging.
    """

    name = "tabpfn_log1p"
    MC_SAMPLES = 200
    MEAN_CLIP_MULTIPLIER = 10.0

    def _to_model_scale(self, y):
        return np.log1p(y)

    def mean(self):
        n = self._logits.shape[0]
        gen = torch.Generator().manual_seed(0)
        u = torch.rand(n, self.MC_SAMPLES, generator=gen, dtype=torch.float64)
        with torch.no_grad():
            z_samples = _icdf_batch(self._criterion, self._logits, u)
        y_samples = torch.expm1(z_samples).clamp(min=0.0, max=self.MEAN_CLIP_MULTIPLIER * self._train_y_max)
        return y_samples.mean(dim=1).numpy()

    def native_nll(self, y):
        y = np.asarray(y, dtype=float)
        z_t = torch.as_tensor(np.log1p(y), dtype=torch.float64)
        with torch.no_grad():
            nll_z = self._criterion.forward(self._logits, z_t)
        jacobian = torch.as_tensor(np.log1p(y), dtype=torch.float64)
        return (nll_z + jacobian).numpy()
