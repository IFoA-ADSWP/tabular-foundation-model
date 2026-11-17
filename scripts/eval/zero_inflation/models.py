"""Thin wrappers around Poisson-GLM, ZIP-GLM, ZINB-GLM, the hurdle GLMs and TabPFN
(single-stage and hurdle) exposing a common interface: mean(), p_zero(), and per-row
log-densities at held-out y.
"""

import numpy as np
import statsmodels.api as sm
import torch
from hurdle import hurdle_log_pmf, smoothed_positive_rate, truncated_interval_log_mass, truncation_quantile_levels
from scipy.stats import nbinom as sp_nbinom
from scipy.stats import poisson as sp_poisson
from statsmodels.discrete.count_model import ZeroInflatedNegativeBinomialP, ZeroInflatedPoisson
from statsmodels.discrete.truncated_model import TruncatedLFNegativeBinomialP, TruncatedLFPoisson
from tabpfn_client import TabPFNClassifier, TabPFNRegressor

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


class _HurdleGLM:
    """Hurdle GLM: a logit for P(Y > 0 | x) and a zero-truncated count GLM fit on the positive rows.

    The binary part takes the full covariate set. Under this DGP P(Y = 0 | x) = pi0 + (1 - pi0) *
    NB2(0 | x) depends on x through the NB zeros, so an intercept-only hurdle (the form ZIP/ZINB use
    for their inflation) would be wrong by construction; a logit in x is close but not exact. The
    zero-truncated NB2 count part, on the other hand, is exactly the DGP's positive part.

    When the binary part cannot be fitted -- one class absent from the training rows, perfect
    separation, or a non-finite fit -- it falls back to a constant smoothed rate, and
    ``binary_fallback`` records that it did.
    """

    name = None

    def fit(self, x_glm, y):
        x = np.asarray(x_glm, dtype=float)
        y = np.asarray(y, dtype=int)
        pos = y > 0
        self.binary_fallback = False
        self._logit = None
        if 0 < pos.sum() < len(y):
            try:
                result = sm.Logit(pos.astype(float), x).fit(disp=False, maxiter=200)
                if np.all(np.isfinite(result.params)) and np.isfinite(result.llf):
                    self._logit = result
            except Exception:  # statsmodels raises PerfectSeparationError, LinAlgError, ...
                self._logit = None
        if self._logit is None:
            self.binary_fallback = True
            self._p_pos_const = smoothed_positive_rate(y)
        self.count_result = self._fit_count(x[pos], y[pos])
        return self

    def _fit_count(self, x_pos, y_pos):
        raise NotImplementedError

    def p_positive(self, x_glm):
        x = np.asarray(x_glm, dtype=float)
        if self._logit is None:
            return np.full(len(x), self._p_pos_const)
        return np.asarray(self._logit.predict(x), dtype=float)

    def _mu(self, x_glm):
        x = np.asarray(x_glm, dtype=float)
        return np.exp(x @ np.asarray(self.count_result.params[: x.shape[1]], dtype=float))

    def p_zero(self, x_glm):
        return 1.0 - self.p_positive(x_glm)

    def mean(self, x_glm):
        return self.p_positive(x_glm) * self._truncated_mean(self._mu(x_glm))

    def log_pmf_at(self, x_glm, y):
        y = np.asarray(y, dtype=int)
        log_trunc = self._log_truncated_pmf(self._mu(x_glm), np.maximum(y, 1))
        return hurdle_log_pmf(self.p_positive(x_glm), log_trunc, y)


class HurdlePoissonGLM(_HurdleGLM):
    """Logit hurdle + zero-truncated Poisson: the count tail is misspecified (Var = Mean), as in ZIP."""

    name = "hurdle_poisson_glm"

    def _fit_count(self, x_pos, y_pos):
        return TruncatedLFPoisson(y_pos, x_pos, truncation=0).fit(disp=False, maxiter=200)

    @staticmethod
    def _truncated_mean(mu):
        return mu / -np.expm1(-mu)

    @staticmethod
    def _log_truncated_pmf(mu, y):
        return sp_poisson.logpmf(y, mu) - np.log(-np.expm1(-mu))


class HurdleNbGLM(_HurdleGLM):
    """Logit hurdle + zero-truncated NB2: the count part is the DGP's own positive part.

    The truncated NB2 fit can land on a non-positive dispersion or a non-finite likelihood on the
    small, heavy-tailed positive subsample at high pi0 -- the failure ZinbGLM documents. The same
    ladder applies: default start, then an explicit alpha = 1 start, then L-BFGS.
    """

    name = "hurdle_nb_glm"

    def _fit_count(self, x_pos, y_pos):
        model = TruncatedLFNegativeBinomialP(y_pos, x_pos, truncation=0, p=2)
        start_params = np.zeros(x_pos.shape[1] + 1)
        start_params[-1] = 1.0
        result = model.fit(disp=False, maxiter=200)
        if not self._usable(result):
            result = model.fit(start_params=start_params, disp=False, maxiter=200)
        if not self._usable(result):
            result = model.fit(start_params=start_params, disp=False, maxiter=500, method="lbfgs")
        return result

    _usable = staticmethod(ZinbGLM._usable)

    @property
    def nb_alpha(self):
        return float(self.count_result.params[-1])

    def _log_p0(self, mu):
        a = self.nb_alpha
        return -np.log1p(a * mu) / a

    def _truncated_mean(self, mu):
        return mu / -np.expm1(self._log_p0(mu))

    def _log_truncated_pmf(self, mu, y):
        a = self.nb_alpha
        n = 1.0 / a
        p = n / (n + mu)
        return sp_nbinom.logpmf(y, n, p) - np.log(-np.expm1(self._log_p0(mu)))


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


class TabPFNHurdleModel(_TabPFNBase):
    """Two-stage TabPFN: TabPFNClassifier for P(Y > 0 | x), TabPFNRegressor fit on the positive
    training rows only, for the count given that it is positive.

    The regressor's predictive distribution is continuous; its mass on k >= 1 is the
    continuity-corrected interval [k - 1/2, k + 1/2], renormalised by its mass above 1/2 (see
    hurdle.py). The zero is a point mass from the classifier, so there is no native density at
    y = 0: native_nll() returns NaN everywhere and only the continuity-corrected NLL is comparable.

    The mean is P(Y > 0) * E[Z | Z > 1/2], the second factor by the midpoint rule over
    N_MEAN_LEVELS quantiles of the truncated distribution -- deterministic, unlike the Monte
    Carlo mean of TabPFNLog1pModel. No clipping is needed: the regressor works on the raw count
    scale, so its tail is not exponentiated.

    If the training rows hold only one class the classifier is not called and P(Y > 0) falls back
    to a constant smoothed rate (``binary_fallback``), as in the hurdle GLMs.
    """

    name = "tabpfn_hurdle"
    N_MEAN_LEVELS = 500

    def _to_model_scale(self, y):
        return y

    def fit(self, x_raw, y, categorical_features_indices=None):
        y = np.asarray(y, dtype=float)
        pos = y > 0
        self._train_y_max = float(y.max())
        self.binary_fallback = not (0 < pos.sum() < len(y))
        self.clf = None
        if self.binary_fallback:
            self._p_pos_const = smoothed_positive_rate(y)
        else:
            self.clf = TabPFNClassifier(model_path=MODEL_PATH, random_state=0, categorical_features_indices=categorical_features_indices)
            self.clf.fit(x_raw, pos.astype(int))
        self.reg = TabPFNRegressor(model_path=MODEL_PATH, random_state=0, categorical_features_indices=categorical_features_indices)
        self.reg.fit(x_raw[pos].reset_index(drop=True), y[pos])
        return self

    def predict_full(self, x_raw):
        super().predict_full(x_raw)
        if self.clf is None:
            self._p_pos = np.full(len(x_raw), self._p_pos_const)
        else:
            proba = np.asarray(self.clf.predict_proba(x_raw), dtype=float)
            classes = list(getattr(self.clf, "classes_", [0, 1]))
            self._p_pos = proba[:, classes.index(1)]
        return self

    def p_positive(self):
        return self._p_pos

    def p_zero(self):
        return 1.0 - self._p_pos

    def _cdf_half(self):
        return self._cdf_at(np.full(self._logits.shape[0], 0.5))

    def continuity_nll(self, y):
        y = np.asarray(y, dtype=float)
        log_trunc = truncated_interval_log_mass(self._cdf_at(y + 0.5), self._cdf_at(y - 0.5), self._cdf_half())
        return -hurdle_log_pmf(self._p_pos, log_trunc, y)

    def mean(self):
        levels = torch.as_tensor(truncation_quantile_levels(self._cdf_half(), self.N_MEAN_LEVELS), dtype=torch.float64)
        with torch.no_grad():
            z = _icdf_batch(self._criterion, self._logits, levels)
        return self._p_pos * z.mean(dim=1).numpy()

    def native_nll(self, y):
        return np.full(len(np.asarray(y)), np.nan)
