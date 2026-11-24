# Two-stage TabPFN on zero-inflated counts — result: the hurdle closes most of the gap to ZINB

**Status:** current — result note, 2026-11-23. **Ticket:** #662, the protocol: hypothesis, bar, falsifier and
analysis plan, all fixed before the run. **Plan:** [`159-zero-inflation-hurdle.md`](../../plans/159-zero-inflation-hurdle.md).
**Builds on:** [`ZERO_INFLATION_TABPFN.md`](ZERO_INFLATION_TABPFN.md), the September study: same data, same metrics.
This note is written to be read on its own; the setup below is all of the earlier context it needs.
**Model:** TabPFN `v3.5_default` (hosted, `tabpfn-client` 0.5.3), pinned in `scripts/eval/zero_inflation/models.py`.
Every TabPFN number below is measured against `v3.5_default`; no version era is mixed.
**Evidence:** `scripts/eval/zero_inflation/results/alpha_{1.0,2.0,4.0}/results_hurdle.csv`, read together with
the committed `results.csv` beside each. Every number in this note is printed by
`python3 scripts/eval/zero_inflation/hurdle_verdict.py`, and the figure is drawn by
`make_hurdle_chart.py` in the same directory; both read only those CSVs and spend nothing.

## Short answer

On synthetic counts with many structural zeros, splitting TabPFN into two stages — a classifier for "is the
count zero?" and a regressor for "how large, given that it is not?" — gives a better predictive distribution
than TabPFN applied to the counts directly. The test was pre-registered, and it passed at all three dispersion levels, on all 30 seed-level comparisons: **CONFIRMED**.

The gain is about 0.03 nats per observation, which is almost exactly how far single-stage TabPFN was behind the correctly specified statistical model (a zero-inflated negative binomial GLM). Posed as a hurdle, TabPFN comes within about 0.004 nats of that model at two dispersion levels and cannot be told apart from it at the third.
The improvement is in the distribution — chiefly the probability of a zero — not in the point prediction.

## Setup

**Why this was tested.** In September, single-stage TabPFN was compared with Poisson, zero-inflated Poisson (ZIP)
and zero-inflated negative binomial (ZINB) GLMs on zero-inflated counts. It matched them on the mean and came
within a few hundredths of a nat of the correct model (ZINB) on the predictive distribution, without ever being
told the data were zero-inflated. At a meeting on 2026-10-14, Prior Labs, TabPFN's developer, said that a
two-stage (hurdle) formulation is usually best for zero-inflated targets. #662 turned that remark into a
pre-registered test.

**The data** are synthetic, so the true model is known. Each row has five covariates — four standard normal, one
categorical with three levels — and a true mean λ(x) = exp(linear predictor), about 8 at the centre. Two arms
share that mean exactly, row for row:

```
baseline arm   Y ~ Poisson(λ(x))
inflated arm   Y = 0 with probability π₀ (a structural zero),
               otherwise Y ~ NB2 with mean λ(x)/(1 − π₀) and variance μ + αμ²
```

- **π₀** is the share of structural zeros, swept over 0, 0.05, 0.1, 0.2, …, 0.9, 0.95.
- **α** is the overdispersion of the non-zero part: 1, 2 and 4, each run as its own full sweep.
- A **cell** is one (π₀, seed) pair. Every cell draws fresh data: 1,000 training rows and 1,000 test rows. There
  are 10 seeds, i.e. 10 independent replicates of the whole grid, so 130 cells per α (12 π₀ values plus the
  baseline arm, times 10).

**The models.** Every model is fitted on each cell's training rows and scored on its test rows.

| Model | What it is |
| --- | --- |
| `zinb_glm` | ZINB GLM: a constant probability of a structural zero, plus an NB2 count model with a log link in x. The **correctly specified** model — the reference. |
| `zip_glm` | ZIP GLM: the same, with a Poisson count part. The usual practical fix, with the wrong tail. |
| `tabpfn` | **Single-stage TabPFN**: the hosted TabPFN regressor fitted on the raw counts. It returns a continuous predictive distribution and is not told that the data are counts or inflated. |
| `tabpfn_hurdle` | **Two-stage TabPFN**: a TabPFN classifier fitted on all training rows to predict p(x) = P(Y > 0 \| x), and a TabPFN regressor fitted only on the positive rows, giving a continuous distribution F for the size of a non-zero count. |
| `hurdle_nb_glm` | The GLM version of the same idea: a logistic regression in x for P(Y > 0), plus a zero-truncated NB2 count model. |
| `hurdle_poisson_glm` | The same with a zero-truncated Poisson count part. |

The two-stage model's probabilities are P(Y = 0) = 1 − p(x), and, for k ≥ 1,

```
P(Y = k) = p(x) · [F(k + ½) − F(k − ½)] / [1 − F(½)]
```

The regressor was trained on counts of at least 1, but it can still put some probability below ½; dividing by
1 − F(½) removes that part, so the probabilities sum to one.

The GLM hurdles are not exactly right for this data either. Under the DGP, P(Y = 0 | x) = π₀ + (1 − π₀)·NB2(0 | x),
which a logistic regression in x approximates closely but not exactly. ZINB and ZIP do not have this problem,
because their structural-zero probability really is a constant here.

**The metric** is the **continuity-corrected negative log-likelihood (NLL)**. TabPFN's regressor predicts a
continuous distribution, but the outcomes are integers, so the probability it gives an observed count y is taken
as the mass of its distribution over [y − ½, y + ½]; for the GLMs it is simply the probability of y. The NLL is
the average of −log(probability) over the 1,000 test rows, in nats. **Lower is better.**

For scale: a difference of 0.03 nats means the better model gives the observed test counts, on average, about
3 % more probability per observation (e^0.03 ≈ 1.03). In September, the wrong-tailed ZIP GLM was 2 to 8 nats
behind ZINB on the same data, and single-stage TabPFN about 0.03.

## The verdict, in the pre-registered rule's terms

#662 fixed the rule before the run. For each α:

1. For each seed, average the NLL difference `tabpfn_hurdle − tabpfn` over the six cells π₀ ∈ {0.5, 0.6, 0.7,
   0.8, 0.9, 0.95} — the range where at least half of the data are structural zeros. That gives 10 paired values,
   one per seed.
2. Compute a two-sided t-interval for their mean at 98.33 % (95 %, Bonferroni-corrected for the three α).
3. **Bar met** if the upper bound is below 0 at all three α — the hurdle is better everywhere. **Falsified** if the
   lower bound is above 0 at any α — the hurdle is worse somewhere. Anything else is UNRESOLVED.

The `tabpfn` rows are the ones committed in September; the new rows were scored on exactly the same data. In all
390 `tabpfn_hurdle` cells, and in every GLM-hurdle and drift-control cell, the columns that depend only on the
data — `n_test`, `p_zero_empirical`, `train_y_max`, `test_y_max`, `frac_test_y_exceeds_train_max` — equal the
committed rows' exactly.

| α | mean Δ NLL (nats) | 98.33 % interval | SD across seeds | seeds where the hurdle is better | bar | falsifier |
| --- | ---: | --- | ---: | ---: | --- | --- |
| 1 | **−0.0302** | [−0.0347, −0.0256] | 0.0049 | 10/10 | met | not hit |
| 2 | **−0.0338** | [−0.0385, −0.0292] | 0.0050 | 10/10 | met | not hit |
| 4 | **−0.0316** | [−0.0383, −0.0248] | 0.0073 | 10/10 | met | not hit |

**Verdict: CONFIRMED.** The effect is about five times the interval half-width, and all 30 seed-level contrasts
point the same way.

Before the run, #662 estimated how noisy such a contrast would be from existing rows (the seed SD of
TabPFN − ZINB: 0.0065, 0.0065 and 0.0151 nats). The contrast turned out less noisy than that, so the design was,
if anything, conservative.

## What the effect is the size of

![Three panels, one per alpha: NLL gap to ZINB-GLM against pi0 for single-stage TabPFN (blue, solid) and two-stage TabPFN (orange, dashed); the blue line stays at about +0.03 across pi0, the orange line starts close to it at pi0 = 0 and falls to about zero from pi0 = 0.5 onwards](../../../scripts/eval/zero_inflation/figures/hurdle_gap_by_alpha.png)

*hurdle_gap_by_alpha.png — each point is the mean over 10 seeds of the model's NLL minus ZINB's in one π₀ cell,
with a 95 % t-interval; zero (the black line) is the correctly specified model. Single-stage TabPFN (blue) sits
about 0.03 nats above it at every π₀. The hurdle (orange) starts close to it when there are few structural zeros
and falls towards zero as π₀ grows. The shaded range is where the bar was measured. At π₀ = 0.95 both TabPFN
variants dip below zero, because ZINB itself becomes unstable there: with 5 % of rows non-zero, some of its fits
extrapolate badly (the September study recorded one with an RMSE above 1,300 at α = 4).*

Averaged over the bar's range, with the same 98.33 % intervals (no verdict attached to these):

| α | single-stage TabPFN − ZINB | two-stage TabPFN − ZINB |
| --- | --- | --- |
| 1 | +0.0343 [+0.0282, +0.0404] | **+0.0041** [+0.0001, +0.0082] |
| 2 | +0.0377 [+0.0317, +0.0438] | **+0.0039** [+0.0005, +0.0072] |
| 4 | +0.0256 [+0.0116, +0.0396] | **−0.0059** [−0.0186, +0.0067] |

The hurdle recovers about 90 % of the gap at α = 1 and 2; at α = 4 it cannot be told apart from ZINB. ZINB is
still ahead by about 0.004 nats at α = 1 and 2 — a small residual, but its interval excludes zero.

## Reported alongside, with no verdict

The analysis plan named these before the run. None carries a verdict: they describe, they do not test.

| Contrast (98.33 % interval) | α = 1 | α = 2 | α = 4 |
| --- | --- | --- | --- |
| two-stage − single-stage TabPFN, π₀ < 0.5 | −0.0087 [−0.0128, −0.0045] | −0.0076 [−0.0110, −0.0042] | −0.0124 [−0.0169, −0.0080] |
| two-stage − single-stage TabPFN, baseline arm (mean) | +0.0038 | +0.0038 | +0.0038 |
| RMSE of the mean, two-stage − single-stage, π₀ ≥ 0.5 | −0.050 [−0.151, +0.052] | −0.055 [−0.164, +0.055] | −0.065 [−0.130, −0.000] |
| `hurdle_nb_glm` − `zinb_glm`, π₀ ≥ 0.5 | +0.0010 [−0.0018, +0.0038] | +0.0021 [−0.0006, +0.0049] | +0.0003 [−0.0128, +0.0135] |
| `hurdle_poisson_glm` − `zip_glm`, π₀ ≥ 0.5 | +0.056 [−0.011, +0.124] | +0.575 [−0.068, +1.218] | +1.190 [+0.656, +1.724] |

- **Fewer structural zeros.** The hurdle still helps at π₀ < 0.5, by roughly a quarter to two-fifths as much as at
  π₀ ≥ 0.5.
- **No inflation.** On the plain-Poisson baseline arm it costs 0.004 nats. That arm does not depend on α, so the
  three columns are the same ten cells.
- **The mean.** RMSE moves in the hurdle's favour, but only at α = 4 does the interval exclude zero: the gain is
  in the distribution, not the point prediction.
- **The GLM hurdles.** `hurdle_nb_glm` is within about 0.002 nats of ZINB despite its slightly misspecified zero
  part. `hurdle_poisson_glm` fails on the tail the way ZIP does, increasingly with α: a hurdle does not repair a
  wrong count distribution.

**The probability of a zero.** Mean |predicted P(Y = 0) − observed share of zeros| over the π₀ ≥ 0.5 cells:

| α | single-stage TabPFN | two-stage TabPFN | `zinb_glm` | `hurdle_nb_glm` |
| --- | ---: | ---: | ---: | ---: |
| 1 | 0.0254 | 0.0150 | 0.0151 | 0.0153 |
| 2 | 0.0197 | 0.0131 | 0.0129 | 0.0132 |
| 4 | 0.0214 | 0.0156 | 0.0155 | 0.0156 |

With a classifier dedicated to the zero, TabPFN's share of zeros is as well calibrated as the parametric models'.
That is where most of the gain sits: a single continuous predictive distribution has to approximate a spike of
probability at exactly zero, and does so less precisely than a separate yes/no prediction.

**When there is nothing to classify.** A classifier cannot be trained when every training row is positive (or
every row is zero). The code then uses a constant probability of a positive count, (n_pos + ½)/(n + 1), and flags
the row. That happened once per α — the baseline arm at seed 7, where none of the 1,000 Poisson training rows
with mean about 8 was zero — outside the bar's range.

## Caveats

- **The TabPFN server answered slightly differently than in September.** The comparison pairs new hurdle rows
  with single-stage rows computed two months earlier on a hosted service, which is fair only if the service
  still behaves the same. As a check, #662 required refitting single-stage TabPFN (`tabpfn_recheck`) on seeds 0
  and 1 — 26 cells per α — and stopping the analysis if its NLL moved by more than 0.001 nats on average. It moved
  by 5.2e-5, 5.9e-5 and 5.4e-5 nats (at most 1.3e-4, 1.7e-4 and 1.3e-4 in one cell), so the check passed. But all
  78 cells differ slightly, where in September TabPFN reproduced bit-exactly. The largest difference (1.7e-4) is
  about 25 times smaller than the narrowest half-width in the verdict table (0.0046), so it cannot change the
  verdict. Its cause — the server, the client version, or the bar distribution now built locally from `tabpfn`
  8.5.0 — is not separated by this run.
- **Synthetic data, one data-generating process,** with a known α and π₀ and 1,000 training rows. Whether the
  decomposition helps on a real insurance target is a separate question, asked by #682 on `bemtl97_amount`.
- **One metric decides.** The continuity-corrected NLL. The hurdle puts an exact point mass at zero, so a density
  ("native") NLL is not comparable across the two TabPFN variants and is recorded as NaN for the hurdle.
- **One model version.** `v3.5_default` only. Prior Labs has said its next release is better on zero-inflated
  data; testing it is a new ticket, not a re-run of this one.

## What this changes

The September conclusion — single-stage TabPFN handles zero-inflated counts, within a few hundredths of a nat of
the correct model — still stands. This result adds that the remaining gap is mostly the way the problem is posed,
not the model: as a hurdle, the same `v3.5_default` comes within about 0.004 nats of ZINB at α = 1 and 2 and is
indistinguishable from it at α = 4. What follows from the verdict in practice is for #662's owner to decide.

## Run record

| | |
| --- | --- |
| Revision | `982447f72dd4b58adf496d152a73cfefb1229f76` (main), run 2026-11-23 |
| Environment | own venv: Python 3.12.0, numpy 1.26.4, scipy 1.17.1, pandas 2.3.3, scikit-learn 1.9.0, statsmodels 0.14.6, tabpfn-client 0.5.3, tabpfn 8.5.0, torch 2.13.0 |
| Model | `v3.5_default` |
| Order, as #662 fixed it | 1. `check_reproducible.py --alpha <α> --seeds 0 5 9` (the environment regenerates the committed data); 2. `run_sweep.py --alpha <α> --models hurdle_poisson_glm hurdle_nb_glm`; 3. `run_sweep.py --alpha <α> --models tabpfn_recheck --n-seeds 2` (the drift check); 4. `run_sweep.py --alpha <α> --models tabpfn_hurdle` — each for α ∈ {1.0, 2.0, 4.0} |
| Analysis and figure | `hurdle_verdict.py`; `make_hurdle_chart.py`, which records the commit and a sha256 per script and CSV in `scripts/eval/zero_inflation/figures/hurdle_manifest.json` |
| Rows written | per α, 130 each of `hurdle_poisson_glm`, `hurdle_nb_glm`, `tabpfn_hurdle`, and 26 of `tabpfn_recheck` |
| Hosted fits | 780 for `tabpfn_hurdle` (a classifier and a regressor per cell), 78 for the drift check, and one cell's fit spent before a missing local dependency (`tabpfn`) stopped the first drift-check attempt; it wrote no row |
