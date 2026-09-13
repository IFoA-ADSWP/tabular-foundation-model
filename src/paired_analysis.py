"""Paired analysis for Pilot 2, as fixed by `docs/reports/PILOT_2_STATISTICAL_ANALYSIS_PLAN.md`.

Three primitives, and nothing else:

* `paired_bootstrap_ci` -- the paired interval for one comparison on identical test rows.
* `inverse_variance_summary` -- the aggregation across datasets/targets (density D4).
* `holm_adjust` -- the multiplicity correction for the per-dataset family.

WHY PAIRED. Every comparison in Pilot 2 is between arms evaluated on the SAME test rows, so
the interval must resample ROWS and use the per-row pairing. R1's *unpaired* interval widths
(0.031-0.118 on ROC) are not the yardstick for a paired comparison and must not be quoted as
one; the relevant noise floor is the interval this module computes.

WHY THE METRIC IS INJECTED. Resampling rows for a ranking metric needs the predictions, not a
pre-computed score, so the caller passes `metric_fn(y_true, y_score) -> float`. This keeps the
module free of sklearn and lets a test use a hand-verifiable metric.

DEGENERATE RESAMPLES ARE COUNTED, NOT HIDDEN. A bootstrap resample of a small or imbalanced
test set can contain one class only, where a ranking metric is undefined. Those resamples are
skipped AND reported in `n_degenerate`; a high count is a finding about the experiment's power,
not a detail to swallow. See SAP 12.1 -- three of four datasets cannot resolve R1-scale effects
at 1,000 test rows, and this counter is where that shows up first.
"""

from __future__ import annotations

from typing import Callable

import numpy as np

SHIPPED_ALPHA = 0.05
SHIPPED_RESAMPLES = 10_000
SHIPPED_SEED = 42

MetricFn = Callable[[np.ndarray, np.ndarray], float]


def paired_bootstrap_ci(
    y_true: np.ndarray,
    scores_a: np.ndarray,
    scores_b: np.ndarray,
    metric_fn: MetricFn,
    *,
    n_resamples: int = SHIPPED_RESAMPLES,
    alpha: float = SHIPPED_ALPHA,
    seed: int = SHIPPED_SEED,
) -> dict:
    """Paired percentile-bootstrap interval for `metric(b) - metric(a)`.

    The point estimate uses all rows; the interval resamples row indices with replacement and
    recomputes BOTH arms on the same resample (that is what makes it paired). Returns a dict
    with `estimate`, `ci_low`, `ci_high`, `n_rows`, `n_resamples`, `n_degenerate`, `alpha`,
    `seed`, and `metric` (the metric's own value per arm).

    Raises ValueError if the metric is undefined on the full sample -- typically a single-class
    test set, which is a design failure rather than a bootstrap artefact.
    """
    y_true = np.asarray(y_true)
    scores_a = np.asarray(scores_a, dtype=float)
    scores_b = np.asarray(scores_b, dtype=float)
    if not (len(y_true) == len(scores_a) == len(scores_b)):
        raise ValueError("y_true, scores_a and scores_b must have the same length")
    if y_true.size == 0:
        raise ValueError("empty sample")

    point_a = metric_fn(y_true, scores_a)
    point_b = metric_fn(y_true, scores_b)

    rng = np.random.default_rng(seed)
    n = y_true.size
    diffs = np.empty(n_resamples, dtype=float)
    degenerate = 0
    filled = 0
    while filled < n_resamples:
        idx = rng.integers(0, n, size=n)
        yb = y_true[idx]
        if np.unique(yb).size < 2:  # ranking metrics undefined on a single-class resample
            degenerate += 1
            if degenerate > n_resamples * 4:  # stop runaway loops on an unusable sample
                raise ValueError(
                    f"metric undefined on most resamples ({degenerate} degenerate of "
                    f"{filled} drawn): the test set cannot support this comparison"
                )
            continue
        diffs[filled] = metric_fn(yb, scores_b[idx]) - metric_fn(yb, scores_a[idx])
        filled += 1

    lo = float(np.percentile(diffs, 100 * (alpha / 2)))
    hi = float(np.percentile(diffs, 100 * (1 - alpha / 2)))
    return {
        "metric": {"a": float(point_a), "b": float(point_b)},
        "estimate": float(point_b - point_a),
        "ci_low": lo,
        "ci_high": hi,
        "excludes_zero": bool(lo > 0.0 or hi < 0.0),
        "n_rows": int(n),
        "n_resamples": int(n_resamples),
        "n_degenerate": int(degenerate),
        "alpha": float(alpha),
        "seed": int(seed),
    }


def inverse_variance_summary(
    estimates: np.ndarray | list[float],
    variances: np.ndarray | list[float],
    *,
    alpha: float = SHIPPED_ALPHA,
) -> dict:
    """Precision-weighted (fixed-effect inverse-variance) summary across datasets or targets.

    This is the SAP's primary aggregation: a plain mean over targets of 9.8K-53.5K rows lets the
    largest target dominate, whereas weighting by precision does not. Heterogeneity is REPORTED
    (`i2`, and `q`) rather than assumed away -- a high `i2` means a single pooled number is not a
    fair summary and the per-dataset estimates should carry the claim.

    `i2` is Cochran's I-squared as a percentage; `q` is Cochran's Q on `k - 1` degrees of freedom.
    """
    est = np.asarray(estimates, dtype=float)
    var = np.asarray(variances, dtype=float)
    if est.shape != var.shape:
        raise ValueError("estimates and variances must have the same shape")
    if est.size == 0:
        raise ValueError("no estimates to summarise")
    if np.any(var <= 0):
        raise ValueError("variances must be positive")

    w = 1.0 / var
    pooled = float(np.sum(w * est) / np.sum(w))
    se = float(np.sqrt(1.0 / np.sum(w)))
    z = 1.959963984540054 if abs(alpha - 0.05) < 1e-12 else float(
        np.sqrt(2.0) * _erfinv(1.0 - alpha)
    )
    q = float(np.sum(w * (est - pooled) ** 2))
    k = int(est.size)
    i2 = 0.0 if k < 2 else max(0.0, (q - (k - 1)) / q) * 100.0 if q > 0 else 0.0
    return {
        "pooled": pooled,
        "se": se,
        "ci_low": pooled - z * se,
        "ci_high": pooled + z * se,
        "excludes_zero": bool(pooled - z * se > 0.0 or pooled + z * se < 0.0),
        "k": k,
        "q": q,
        "i2": i2,
        "alpha": float(alpha),
    }


def nested_paired_bootstrap(
    repeats: list[tuple],
    metric_fn: MetricFn,
    *,
    n_resamples: int = SHIPPED_RESAMPLES,
    alpha: float = SHIPPED_ALPHA,
    seed: int = SHIPPED_SEED,
) -> dict:
    """Paired interval for the MEAN over repeats (SAP section 5).

    `repeats` is a list of `(y_true, scores_a, scores_b)` -- one per seed or fold, each with its
    OWN test rows. Rows are resampled *within* a repeat and repeats are resampled *with each
    other*, which is what makes this the interval for the mean over repeats rather than the
    interval for a single split. Using one repeat's interval as the dataset's would understate the
    uncertainty that comes from the split itself, which is precisely the component the repeats are
    there to measure.

    A drawn repeat whose row-resample has one class only is redrawn (bounded); if the sample
    cannot support the metric the failure is raised rather than papered over.
    """
    if not repeats:
        raise ValueError("no repeats to summarise")
    prepared = []
    for y_true, scores_a, scores_b in repeats:
        y = np.asarray(y_true)
        a = np.asarray(scores_a, dtype=float)
        b = np.asarray(scores_b, dtype=float)
        if not (len(y) == len(a) == len(b)):
            raise ValueError("y_true, scores_a and scores_b must have the same length")
        prepared.append((y, a, b))

    point = float(np.mean([metric_fn(y, b) - metric_fn(y, a) for y, a, b in prepared]))

    rng = np.random.default_rng(seed)
    n_rep = len(prepared)
    draws = np.empty(n_resamples, dtype=float)
    degenerate = 0
    for i in range(n_resamples):
        chosen = rng.integers(0, n_rep, size=n_rep)
        diffs = []
        for j in chosen:
            y, a, b = prepared[j]
            for _ in range(16):  # bounded redraw for a single-class row-resample
                idx = rng.integers(0, y.size, size=y.size)
                yb = y[idx]
                if np.unique(yb).size >= 2:
                    diffs.append(metric_fn(yb, b[idx]) - metric_fn(yb, a[idx]))
                    break
            else:
                degenerate += 1
        if not diffs:
            raise ValueError(
                "metric undefined on every resample: the repeats cannot support this comparison"
            )
        draws[i] = float(np.mean(diffs))

    lo = float(np.percentile(draws, 100 * (alpha / 2)))
    hi = float(np.percentile(draws, 100 * (1 - alpha / 2)))
    return {
        "estimate": point,
        "ci_low": lo,
        "ci_high": hi,
        "excludes_zero": bool(lo > 0.0 or hi < 0.0),
        "n_repeats": n_rep,
        "n_resamples": int(n_resamples),
        "n_degenerate_repeats": int(degenerate),
        "alpha": float(alpha),
        "seed": int(seed),
    }


def holm_adjust(pvalues: np.ndarray | list[float]) -> list[float]:
    """Holm-Bonferroni adjusted p-values, order preserved.

    The SAP applies this to the family of per-dataset claims inside a step (four comparisons).
    It is deliberately NOT applied to the step's primary comparison, which is a single
    comparison by construction -- that is the point of the isolation design.
    """
    p = np.asarray(pvalues, dtype=float)
    if p.ndim != 1:
        raise ValueError("pvalues must be one-dimensional")
    if p.size == 0:
        return []
    if np.any((p < 0.0) | (p > 1.0)):
        raise ValueError("p-values must lie in [0, 1]")

    order = np.argsort(p, kind="stable")
    adjusted = np.empty(p.size, dtype=float)
    running = 0.0
    for rank, idx in enumerate(order):
        scaled = (p.size - rank) * p[idx]
        running = max(running, scaled)
        adjusted[idx] = min(1.0, running)
    return [float(v) for v in adjusted]


def _erfinv(x: float) -> float:
    """Inverse error function (no scipy): Winitzki's approximation, ample for a z-multiplier."""
    a = 0.147
    ln1 = np.log(1.0 - x * x)
    term = 2.0 / (np.pi * a) + ln1 / 2.0
    return float(np.sign(x) * np.sqrt(np.sqrt(term * term - ln1 / a) - term))
