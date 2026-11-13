# Baseline method specification — `E_glm` and `F_catboost` on the frequency/severity folds

> **Status:** proposed — 2026-11-13, research only, no runs.
>
> **Question.** The registered fair test compares two TabPFN arms (`A_raw` vs `B_ft30`) and
> answered *does fine-tuning help*. It cannot answer *does TabPFN beat the model a pricing team
> would actually build*. This note specifies the two missing **methods** — `E_glm` and
> `F_catboost` — so that the comparison is against a defensible actuarial baseline, not a straw
> man. They are methods, not arms: `Arm` in `GLOSSARY.md` is a TabPFN training configuration, and
> a baseline is a different predictor.
>
> **Scope.** The four registered targets and folds of the fair test
> (`docs/current/REGRESSOR_FINETUNING_PREREGISTRATION_FREQ_SEV_2026-11.md`). The French rows are
> specified in full; the Spanish rows reuse the same recipe with the claim-count weight. Nothing
> here has been fitted. No number in this note is a result.

## 1. What the baseline has to match

Everything below is inherited, not chosen — a baseline that changes any of it is measuring a
different experiment.

| Element | Value | Where |
|---|---|---|
| Folds | 5 policy-grouped folds, `random_state=42`; a policy's claims never straddle a fold | `src/freq_sev_data.py`, `src/fair_test_runner.py` |
| Train budget | **full fold pool** for the baselines (primary); the fair test's 10,000-row sample as a sensitivity arm | decision #597 |
| Test rows | the capture's `test_index` — frequency targets *subsample* the fold's test policies | `src/fair_test_runner.py` |
| Frequency target | `ClaimNb` per policy; metric `src/metrics.poisson_deviance` | `src/metrics.py` |
| Severity target | `log(ClaimAmount)` per claim; metric `rmse` / `weighted_rmse` | `src/metrics.py` |

Three consequences that are easy to get wrong:

1. **The frequency metric is a total, not a mean.** `poisson_deviance` in `src/metrics.py` returns
   `2 * sum(...)` with `y_pred` clipped at `1e-12`; scikit-learn's `mean_poisson_deviance` is the
   same quantity divided by *n*. Both are legitimate; only one is registered here. Quote the
   function you used, because the two differ by the test-row count.
2. **Severity is a log-scale regression, not an amount regression.** The captures store
   `y = log(ClaimAmount)` and the verdict is RMSE *on that scale*. An arm that predicts euros and
   is scored in log-euros is penalised for Jensen's inequality, not for being wrong.
3. **Fit per (fold, seed), and say what a seed means at each budget.** At the 10,000-row
   sensitivity budget the three seeds are three *different* subsamples of the fold's training pool,
   exactly as the TabPFN arms were, so all 15 are fitted. At **full pool** there is nothing to
   sample, so the GLM's three seeds are identical fits and only CatBoost's differ. Run all 15
   anyway — a uniform matrix keeps the pairing and the citation gate's seed expectations intact —
   and state in the write-up that the GLM duplicates are duplicates, rather than special-casing
   them in code.

## 2. Recommended configuration

`≙` marks a choice that reproduces the dataset's own reference case study (Noll, Salzmann &
Wüthrich, *Case Study: French Motor Third-Party Liability Claims*, SSRN 3164764,
doi:10.2139/ssrn.3164764; code: `actuarial-data-science/Tutorials`, `1 - French Motor Third-Party
Liability Claims/`, version March 02, 2020).

| Method | Target | Family / link (or loss) | Response & weight | Exposure | Categoricals | Hyperparameters of record |
|---|---|---|---|---|---|---|
| `E_glm` | frequency_french | Poisson, log link ≙ | `y = ClaimNb / Exposure`, `w = Exposure` | offset `log(Exposure)`, elasticity pinned at 1 — realised as rate + weight (§3.1) | case-study GLM1 encoding ≙: `VehPower` capped at 9 categorical, `VehAge` 3 bins, `DrivAge` 7 bins, `VehBrand`/`Region` one-hot, `VehGas` binary, `Area` ordinal 1–6 continuous, `BonusMalus` capped 150 continuous, `log(Density)` continuous; one reference level dropped per factor | `PoissonRegressor(alpha=0.0, max_iter=500)` — the repo's frontier regression GLM, unchanged |
| `E_glm` | severity_french | Gaussian, identity link on `log(ClaimAmount)` (a lognormal severity model) | `y = log(ClaimAmount)`, `w = 1` | n/a | same encoding ≙ | `TweedieRegressor(power=0, link="identity", alpha=0.0, max_iter=500)` (≡ OLS; `LinearRegression` gives the identical fit) |
| `F_catboost` | frequency_french | `loss_function="Poisson"` (CatBoost 1.2.10) | `y = ClaimNb / Exposure`, `w = Exposure` | same offset realisation as `E_glm` | pass the **raw** `Area`, `VehBrand`, `VehGas`, `Region` strings via `cat_features`; `VehPower` as an integer column; native ordered target statistics, `one_hot_max_size` left at default (2 on CPU) | `iterations=1000, depth=6, learning_rate=0.03, l2_leaf_reg=3.0, random_seed=0` — i.e. the shipped defaults, pinned explicitly |
| `F_catboost` | severity_french | `loss_function="RMSE"` on `log(ClaimAmount)` | `y = log(ClaimAmount)`, `w = 1` | n/a | identical `cat_features` | identical |

Spanish rows: identical, except `w = N_claims_year` (claim-equivalents) and `y = log(Cost/N)` for
severity — the weight the fair test already registers for `severity_spanish`. On the French
severity rows `w ≡ 1`: the weight column exists in schema v4 but is a no-op there.

Two rows from the first draft of this note are **deliberately not run** (decision #597): the
Gamma-log severity arm and the Tweedie-on-raw CatBoost arm. Both are native-scale models and cannot
be scored on the registered metric for the reason in §3.3.

Also fit an **intercept-only reference** per target (`DummyRegressor` / a one-column GLM). It costs
nothing, and §14.15 of the master report is the cautionary tale: an apparent metric flip on Spanish
severity turned out to be *worse than predicting €0 for every policy*, and only a trivial baseline
exposed it.

## 3. Why each choice

### 3.1 Offset, not `sample_weight` — and how to get an offset out of scikit-learn

The Poisson model with exposure is `log E[Y_i] = x_i'β + log E_i`. The offset enters the **mean**:
it fixes the exposure elasticity at 1, so a 0.1-year policy and a 1.0-year policy with identical
covariates differ by a factor of ten. The case study's own frequency code is exactly this —
`glm(ClaimNb ~ …, offset=log(Exposure), family=poisson())` in `FreMTPL_2 benchmark GLM.r` — and its
companion notebook is explicit that the choice is a convention rather than a finding: *"A priori,
there is not sufficient information about this data to do a sensible decision about the best
consideration of the exposure measure, either as feature or as offset. In the following we treat
the exposure always as an offset to be consistent."* (`freMTPLfreq_glm.Rmd`)

A weight is not an offset. Passing `Exposure` as `sample_weight` on the **count** target reweights
the likelihood (variance ∝ 1/w) and leaves the mean alone, so two policies with the same covariates
get the same predicted count. Measured on synthetic data with this repo's pinned stack: fitting
`PoissonRegressor` on counts with `sample_weight=Exposure` gives coefficients
`[-0.151843, -0.073447]`, while the offset-equivalent fit gives `[-0.165918, -0.017345]`.

scikit-learn 1.6.1 has **no `offset` argument** — measured on the installed package:
`PoissonRegressor.fit(X, y, sample_weight=None)`, `TweedieRegressor.fit(X, y, sample_weight=None)`,
and `"offset" in signature` is `False` for both (also for `GammaRegressor`). The documented route is
the *rate* formulation: divide the target by exposure and pass exposure as the weight — the
scikit-learn insurance example does exactly this (`PoissonRegressor(alpha=1e-4,
solver="newton-cholesky")` on `Frequency = ClaimNb/Exposure` with `sample_weight=Exposure`;
<https://scikit-learn.org/1.6/auto_examples/linear_model/plot_tweedie_regression_insurance_claims.html>).

That route is the offset model, not an approximation to it. The weighted Poisson deviance on the
rate equals the count deviance with the offset, exactly:

```
Σ_i w_i · d(r_i, μ_i) = Σ_i d(y_i, E_i μ_i) + const,   with r_i = y_i/E_i, w_i = E_i
```

Checked numerically on 500 synthetic policies: `240.80620137173656` vs `240.80620137173653`
(difference 2.8e-14). Because the two objectives are *equal* — not merely proportional — `alpha`
does not break the equivalence; `alpha=0` is recommended only because it is the unpenalised GLM an
actuary would quote, and it is what the repo's frontier baseline already uses.

If a statsmodels dependency is ever added, `glm(..., offset=log(Exposure), family=Poisson())` is the
literal form and removes this implementation note. Adding a dependency is an engineering change
(§6), not a science one.

### 3.2 Over-dispersion changes the error bars, not the predictions or the metric

freMTPL2 claim counts are over-dispersed; a Poisson fit will report a Pearson dispersion well above
1 and understate standard errors. But:

- **quasi-Poisson gives the same coefficients.** R's own documentation says the quasi families
  "differ from the `binomial` and `poisson` families only in that the dispersion parameter is not
  fixed at one" (<https://stat.ethz.ch/R-manual/R-devel/library/stats/html/family.html>), and its
  example comments the equality of the Poisson and quasi-Poisson results.
- **The registered metric never sees φ.** The verdict is the Poisson deviance of `(y, μ)`; quasi-
  Poisson only rescales the deviance by 1/φ when you *report* a scaled deviance, and we do not.
- **Negative binomial would change the fit**, because it is a different likelihood. It is not in the
  pinned environment (no `statsmodels`, no `MASS`), and it optimises a loss the verdict does not
  score.

Recommendation: fit Poisson; report `Pearson χ²/df` on the training fold as a diagnostic; do not
switch families for the primary arm. A dispersion of 3 says the standard errors are optimistic, not
that the point predictions are wrong.

### 3.3 Severity: the actuarial convention and the registered metric disagree

Two defensible answers exist and they do not coincide:

- **Gamma with a log link on the raw amount** is the actuarial default for a positive, right-skewed
  severity distribution, and it is what the dataset's reference material uses — the scikit-learn
  example models `AvgClaimAmount` with `GammaRegressor(alpha=10.0)` and weights it by `ClaimNb`,
  citing the case study as its inspiration.
- **Lognormal (Gaussian identity on `log`) is the metric-aligned model**, because the registered
  verdict is RMSE on `log(ClaimAmount)`. A Gamma-log model estimates `E[Y]`; its `log` is not the
  `E[log Y]` the metric rewards, and the gap grows with the log-scale variance.

This specification takes the lognormal as the **sole** severity specification, on the rule that a
baseline must be scored on the loss it was fitted for. The Gamma family is not run (decision #597): a
Gamma-log model estimates `E[Y]` on the amount scale, so scoring it on log-scale RMSE would compare
`log E[Y]` against the `E[log Y]` the metric rewards. That is a different functional, not a worse
model, and putting it in the same table invites a ranking it cannot support. §7 records what this
leaves unanswered.

What must **not** happen: fitting Poisson to `log(amount)`. That is a count likelihood on a
continuous log target, and §14.8 of the master report already records it as catastrophic
("zero-inflation trap… poissonglm catastrophic on log1p amount").

### 3.4 Categorical handling

The repo's current feature builder (`src/freq_sev_data.py`) maps every non-numeric column to
`.cat.codes`, an integer. That is fine for trees — code order is irrelevant to a split — and wrong
for a GLM, where it imposes an arbitrary linear ordering and a single slope across `Region`. `E_glm`
therefore needs its own encoding stage; `F_catboost` needs the opposite (raw strings).

**GLM encoding.** Reuse the case study's GLM1 scheme, which is published, expert-binned, and gives
one reference level per factor. From `Tools/FreMTPL_1b load data.r` and `freMTPLfreq_glm.Rmd`:

| Column | Treatment |
|---|---|
| `Area` | ordinal integer 1–6, continuous (A = rural … F = urban centre) |
| `VehPower` | categorical, values ≥ 9 merged (`pmin(VehPower, 9)`) — 6 classes |
| `VehAge` | 3 classes `[0,1)`, `[1,10]`, `(10,∞)` — reference `[1,10]` |
| `DrivAge` | 7 classes `[18,21)`, `[21,26)`, `[26,31)`, `[31,41)`, `[41,51)`, `[51,71)`, `[71,∞)` — reference `[41,51)` |
| `BonusMalus` | integer, capped at 150, continuous |
| `VehBrand` | categorical, 11 classes — reference `B1` |
| `VehGas` | binary — reference `Diesel` |
| `Density` | `log(Density)`, continuous |
| `Region` | categorical, 22 classes — reference `R24` |

Dropping one level per factor is what prevents the dummy trap; the notebook notes the choice of
reference "does not influence the fitted means but provides a unique parametrization". With a
reference level dropped, the design is full rank and `alpha=0` is identifiable. `Area` as continuous
is collinear with `log(Density)`: the case study finds `Area` insignificant and drops it in GLM2,
which is *marginally better* out of sample, yet they keep GLM1 as the benchmark on AIC and
interpretability. Keep GLM1 (all components) as the primary here, so the baseline is not weakened by
a model-selection step the TabPFN arms never got; note that GLM1 is not the case study's
best-scoring variant, which makes it the conservative choice for a TabPFN comparison.

**CatBoost encoding.** Do nothing. CatBoost's documentation is unambiguous — "Do not use one-hot
encoding during preprocessing. This affects both the training speed and the resulting quality" — and
categorical columns declared as `cat_features` are converted internally to target statistics and
combinations (`one_hot_max_size` defaults to 2 on CPU, so `VehGas` is one-hot and the rest get
CTRs; <https://catboost.ai/docs/en/features/categorical-features>). Passing `.cat.codes` floats with
`cat_features` is an error; the arm needs a target-blind second view of the frame that keeps the raw
strings. Build that view once, before splitting, as the case study insists: "One of the frequent
mistakes is to do the pre-processing after the split."

`IDpol` stays dropped (identifier), and for severity `ClaimNb`/`Exposure` stay dropped (siblings of
the target — a count as a feature predicts the amount by leaking the frequency; the loader already
enforces this).

### 3.5 CatBoost objectives: what exists, measured

From CatBoost 1.2.10 (the pinned version), by fitting rather than reading:

- `Poisson` — fits; predictions come back on the mean scale, not the link scale.
- `Tweedie:variance_power=1.5` — fits; predictions also on the mean scale. The documentation
  restricts `variance_power` to the open interval `(1;2)`, requires non-negative labels and warns
  that large labels overflow, recommending labels scaled to `[0,1000]` on CPU
  (<https://catboost.ai/docs/en/concepts/loss-functions-regression>).
- `Gamma` — **not supported**: `CatBoostError: Gamma loss is not supported`, raised at `fit`. The
  regression objective list does not contain it. So the Gamma severity model cannot be the CatBoost
  primary; RMSE on `log` is.
- `RMSE` is the default objective and the only one of the three for which `boost_from_average`
  defaults to true — the Poisson and Tweedie models start from a flat rate.

`predict` defaults to `prediction_type="Exponent"` for Poisson and Tweedie and `"RawFormulaVal"`
otherwise (<https://catboost.ai/docs/en/concepts/python-reference_catboostregressor_predict>), so
the Poisson arm's `predict` returns a *rate* here (because the response was a rate) and must be
multiplied by `Exposure` before the deviance is taken.

Defaults confirmed from the parameter reference and from the installed package: `iterations=1000`,
`depth=6`, `l2_leaf_reg=3.0`, `learning_rate` automatic for `RMSE` and 0.03 otherwise
(<https://catboost.ai/docs/en/references/training-parameters/common>). Pinning 0.03 explicitly costs
nothing and stops the value drifting if the automatic rule changes.

`sample_weight` vs `group_id`: the severity weight is **per object** and goes to
`sample_weight` / `Pool(weight=…)`. `group_id` is a query/ranking concept; it changes how the loss
is aggregated and has no role in a point regression. Getting this wrong is silent.

## 4. Reuse, not invention — what the repo already justified

The project has already run the two configurations this note extends, and the history argues against
a freshly tuned baseline:

| Element | Reused from | Status |
|---|---|---|
| `PoissonRegressor(alpha=0, max_iter=500)` | frontier regression baselines, `scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py` | reused verbatim |
| `TweedieRegressor(power=1.5)` as the pure-premium form | same file | reused as the severity secondary's precedent |
| `CatBoostRegressor(random_state=0, verbose=0)` (shipped defaults) | same file; pilot arm `F_catboost` (`CatBoostClassifier(iterations=200)`) for the naming | reused as the primary |
| `lm`/`glm`-style logistic baseline named `E_glm` | `scripts/run_pilot.py` (`LogisticRegression(max_iter=1000)` + scaler) | **not reusable**: it is classification-only |

The tuned-GBDT grid the repo has already justified is `lr ∈ {0.05, 0.1} × depth ∈ {6, 10}` with
early stopping on a 10% slice of the training fold (`run_tuned_baselines.py`, master report §14.13) —
but that test *regressed against the shipped defaults on 5 of 6 datasets* (`cat_tuned` 0.663 vs
`cat` 0.688 on norauto), and §14.13.4 records the honest caveat that "properly tuned GBDT was only
partially achieved". So:

- **Primary** = shipped defaults. That is the configuration the project has evidence for.
- **Secondary** = the §14.13 grid, run as a sensitivity check with the same fold/metric. If the
  tuned grid wins, that is a finding about the baseline and it goes in the write-up; it does not
  replace the pre-registered primary.

One thing that is *new* rather than reused, and must be pre-registered: the offset realisation
(rate + weight). The repo's frontier GLM put `log(Exposure)` in as a free feature, which estimates
the exposure elasticity instead of fixing it at 1. Both are defensible; they are not the same model,
and the TabPFN arms see `log(Exposure)` as a feature. See §6.

## 5. Decisions that must be pre-registered vs left free

**Science — fix before the run, report every deviation:**

1. Family and link per target (§2): Poisson with a log link for frequency; Gaussian identity on
   `log(amount)` for severity.
2. The offset realisation for frequency (rate + weight, elasticity = 1), and separately the
   robustness arm with `log(Exposure)` as a free feature.
3. The GLM encoding: bins, merges, reference levels, `Area` continuous. A different binning is a
   different model, not an implementation detail.
4. Hyperparameters of record: `alpha=0`, `max_iter=500`, CatBoost `1000/6/0.03/3.0`.
5. No capping. The repo's rows are uncapped (`ClaimNb` up to 16, `Exposure` to 2.01, measured in
   `data/raw/`), while the case study caps at 4 and 1.0. Capping here would quietly give the
   baseline a different target from the one in the captures' ground truth.
6. The row budget is design, not implementation: **full fold pool** is the primary run and the
   fair test's **10,000-row** sample is a sensitivity arm. Scoring is always on the capture's
   `test_index`, which the new capture version records for exactly this reason.
7. The statistic and the floors, both settled in #597. The shape is the fair test's — per-fold
   relative improvement, paired t over five folds, same Go/No-go/Inconclusive vocabulary — but the
   direction is inverted to name the contender: `r = (M(baseline) − M(TabPFN)) / M(baseline)`, so a
   **positive** `r` means TabPFN has the lower metric. The **per-target registered floors carry
   over unchanged** (frequency_french 2%, frequency_spanish 4%, both severity targets 2%), which is
   what lets a baseline verdict be read on the same scale as the fine-tuning result.
8. Which metric function: `src/metrics.poisson_deviance` (total) and `metrics.rmse` /
   `metrics.weighted_rmse` (log scale).

**Engineering — may change without re-registration, recorded in the run manifest:**

- Solver (`lbfgs` vs `newton-cholesky`), `max_iter`, tolerances, `thread_count`.
- Whether the offset is expressed as rate + weight, or via `statsmodels` if a dependency is added.
- Recovering the training index: re-run the seeded sampler, or add `train_index` to the capture
  (a schema bump; the current v3/v4 captures record `test_index` and the row *count* only).
- The mechanics of the raw-categorical view for CatBoost, column order, dtype handling.
- CatBoost's `allow_writing_files=False`, `verbose=0`, `od_*` plumbing — anything that changes the
  log, not the fit.

## 6. Where the literature and the repo genuinely disagree

- **Exposure as offset or as feature.** The case study declines to decide and picks offset "to be
  consistent"; the repo's TabPFN arms and its frontier GLM use it as a feature. These are different
  models, and the difference is not a bug in either. Running the robustness arm (feature instead of
  offset) is the only way to say whether the baseline lost on model class or on specification.
- **Gamma or lognormal for severity.** Actuarial practice and the dataset's reference material use
  Gamma on the amount scale; the registered verdict is log-scale RMSE, which rewards the lognormal.
  This note does not claim the literature agrees: it runs the metric-aligned model and records the
  disagreement in §7 rather than resolving it by assertion.
- **Tuned or default GBDTs.** The repo's own evidence is that its 2×2 grid did not beat the shipped
  defaults. That is evidence about that grid, not a general claim that tuning cannot help, and the
  §14.13 note says so.
- **Capping.** The case study caps `ClaimNb` at 4 and `Exposure` at 1 on data-error grounds. This
  repo does not, and the captures' ground truth is uncapped. Both are defensible; only one is
  consistent with the existing captures.

## 7. What this cannot settle

- **It cannot say TabPFN is better than "an actuary"** — only than *these* two specifications. The
  GLM has no interactions, no splines, no GLMBoost; the case study's own GLMBoost already beat its
  GLM1 out of sample (31.47 vs 32.17, the hard-coded reference lines in
  `FreMTPL_4 boosting machine.r`), so a GLM loss here is a loss for a main-effects GLM, not for the
  GLM family.
- **It cannot fully separate model class from budget.** The full-pool primary against the
  10,000-row sensitivity arm is what makes the budget question answerable, but the result still
  rests on one CatBoost configuration and on the case study's GLM1 encoding rather than the best
  classical model available.
- **It leaves the Gamma family unanswered.** Severity runs the lognormal only, because that is the
  model the registered metric scores. A Gamma-log model fitted on amounts might rank differently on
  its own deviance, and nothing here would show it.
- **It says nothing about calibration, Gini/lift, pure premium, or the frequency × severity
  product.** Two registered metrics, one per target. §14.15 is the standing warning that a
  different metric can move a rank without moving the truth.
- **It cannot resolve the exposure specification question** — that needs the robustness arm, and
  even then only on these two portfolios.
- **All four targets, but the verdicts stay per target.** The French severity conclusion rests on
  26,444 claims; Spanish frequency is underpowered at its 4% floor, so a baseline result there can
  be Inconclusive for reasons that have nothing to do with baselines. No pooled verdict is claimed.
- **It cannot certify a "fair" baseline.** "Fair" here means "specified in advance, sourced, and not
  weaker than the dataset's own reference case study" — not "the best possible classical model".

## 8. Verification log

Read or measured for this note, with what could not be confirmed:

| Claim | Status |
|---|---|
| Case study GLM1 uses `offset=log(Exposure)`, `family=poisson()`, Poisson deviance on counts | read from the authors' code, `FreMTPL_2 benchmark GLM.r` |
| GLM1 bins/reference levels, caps, grouped split | read from `Tools/FreMTPL_1b load data.r` and `freMTPLfreq_glm.Rmd` |
| Gamma-with-log-link is the dataset's severity convention | **indirect**: from the scikit-learn example that reproduces the case study and cites it. The paper's own PDF could not be opened (§ below) |
| scikit-learn 1.6.1 GLMs have no `offset`; `sample_weight` present | measured on `.venv` (1.6.1) |
| rate + weight equals the offset model | measured: deviance identity to 2.8e-14 |
| CatBoost has no `Gamma` loss | measured on 1.2.10: `CatBoostError: Gamma loss is not supported` |
| CatBoost Poisson/Tweedie predict on the mean scale | measured (values ≈ 1 for a raw ≈ 0 model) and documented |
| CatBoost defaults 1000/6/0.03/3.0, `one_hot_max_size=2` | documented, parameter reference |
| OpenML 41214 = 677,991 policies; 41215 = claim amounts | read from the OpenML API |
| Committed data: 678,013 policies, `ClaimNb` max 16, `Exposure` max 2.01, 26,444 claims, no orphan claims | measured on `data/raw/` |

**Not verified, and deliberately not guessed.** The paper itself could not be read: the arXiv id
supplied with the request (2003.11984) resolves to an unrelated differential-geometry paper, and the
SSRN landing page (doi:10.2139/ssrn.3164764) returns a bot-check page. Crossref and OpenAlex record
the paper as **three authors** — Noll, Salzmann and Wüthrich — not the seven named in the brief, so
the author list should be corrected before it is cited anywhere. Everything attributed to the case
study above comes from its authors' published code and companion notebook, or from scikit-learn's
reproduction of it. A statement about the paper's *severity* section specifically should be checked
against the PDF before it is quoted.
