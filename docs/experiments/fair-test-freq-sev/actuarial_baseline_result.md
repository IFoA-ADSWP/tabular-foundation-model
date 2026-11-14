# The actuarial baseline — result

> **Status:** current — verdict recorded 2026-11-14; the primary (full fold pool) and matched
> 10,000-row arms are reported together. It leaves the fair test's own verdict untouched.
> **Question:** does fine-tuned TabPFN (`B_ft30`) beat the **better** of a GLM (`E_glm`) and
> CatBoost (`F_catboost`) on the fair test's own folds, test rows and metric?
> **Answer:** **not at the registered primary budget** — all four targets are **No-go** against
> CatBoost (−7.93%, −13.66%, −0.79%, −10.11%). At the matched 10,000-row budget French frequency is
> **Inconclusive** (−1.10%, CI [−3.43%, +1.22%], MDE 2.35%): the interval covers zero and the target
> is underpowered against its 2% floor. The other three stay **No-go** (−7.20%, −0.62%, −10.11%).
> The two arms differ in training rows by construction, so the difference between them is a
> **budget sensitivity**, not a second verdict; what it can and cannot say is in Limits.

## Design, as registered

`ACTUARIAL_BASELINE_PREREGISTRATION_2026-11.md`. Four targets; `B_ft30` the contender (with
`A_raw` reported alongside); `E_glm`, `F_catboost` and an intercept-only anchor as methods; the
fair test's five policy-grouped folds (`random_state=42`) and three model seeds per fold; every
slot scored on the registered capture's `test_index`. The statistic is

```
r_{t,f} = ( M_{t,f}(baseline) - M_{t,f}(B_ft30) ) / M_{t,f}(baseline)
```

averaged over seeds inside each fold, with the target interval a paired t over five folds (4 df).
A **positive** `r` means TabPFN has the lower metric. The decision rule is the fair test's,
unchanged, and so are the per-target floors (2% / 4% / 2% / 2%).

Two row budgets were registered. The **primary** trains the baselines on the whole fold pool; the
**sensitivity** arm caps them at the fair test's 10,000 rows, which is what the TabPFN captures
were trained on. The primary is the registered verdict; the matched arm is the registered budget
sensitivity. `severity_spanish` has fewer than 10,000 training rows in a fold, so its two arms are
the same fit: it is captured under both run ids and reported once.

French severity is scored with **unweighted** RMSE — its weight is exactly 1 — so its metric is
`rmse`, not `weighted_rmse`; only `severity_spanish` carries the claim weight.

### Runs

| Target | TabPFN (registered) | Baselines, full pool | Baselines, 10,000 rows |
|---|---|---|---|
| frequency_french | `20261112T164543Z` | `20261113T223000Z` | `20261114T003000Z` |
| frequency_spanish | `20261112T184155Z` | `20261113T223001Z` | `20261114T003001Z` |
| severity_french | `20261112T210029Z` | `20261113T223002Z` | `20261114T003002Z` |
| severity_spanish | `20261112T220641Z` | `20261113T223003Z` | `20261114T003003Z` |

Each baseline run is capture v5: 45 entries (three methods × five folds × three seeds). The GLM's
three seeds are identical fits at full pool; they are run anyway, as registered, so the matrix
stays uniform. Before scoring, `scripts/analyses/actuarial_baseline.py` compares **every baseline
slot's** `test_index` sha256 with the registered capture's, fold by fold; any disagreement refuses
rather than prints.

## Result — primary (baselines on the full fold pool)

| Target | Better baseline | r | 95% CI | MDE | Floor | Decision |
|---|---|---:|---|---:|---:|---|
| frequency_french | `F_catboost` | **−7.93%** | [−10.99%, −4.86%] | 3.09% | 2% | **No-go** |
| frequency_spanish | `F_catboost` | **−13.66%** | [−18.26%, −9.06%] | 4.64% | 4% | **No-go** |
| severity_french | `F_catboost` | **−0.79%** | [−1.01%, −0.56%] | 0.23% | 2% | **No-go** |
| severity_spanish | `F_catboost` | **−10.11%** | [−11.62%, −8.60%] | 1.52% | 2% | **No-go** |

Mean metric per method, over the 15 slots of each target (lower is better):

| Target | Metric | Anchor | `A_raw` | `B_ft30` | `E_glm` | `F_catboost` |
|---|---|---:|---:|---:|---:|---:|
| frequency_french | Poisson deviance | 3278.38 | 3592.40 | 3238.43 | 3109.94 | **3000.68** |
| frequency_spanish | Poisson deviance | 10158.89 | 10019.05 | 9606.66 | 8888.96 | **8451.33** |
| severity_french | RMSE of `log(amount)` | 1.12994 | **1.12011** | 1.13038 | 1.12247 | 1.12160 |
| severity_spanish | weighted RMSE | 0.69047 | 0.65033 | 0.63955 | 0.59316 | **0.58073** |

The other baseline, for completeness: `E_glm` scores −4.13%, −8.08%, −0.71% and −7.79% against
`B_ft30`. CatBoost is the better of the two on all four targets, so it is the one the verdict is
taken against.

## Result — matched budget (baselines capped at 10,000 rows)

| Target | Better baseline | r | 95% CI | MDE | Floor | Decision |
|---|---|---:|---|---:|---:|---|
| frequency_french | `F_catboost` | **−1.10%** | [−3.43%, +1.22%] | 2.35% | 2% | **Inconclusive** |
| frequency_spanish | `E_glm` | **−7.20%** | [−11.92%, −2.48%] | 4.76% | 4% | **No-go** |
| severity_french | `F_catboost` | **−0.62%** | [−0.88%, −0.37%] | 0.25% | 2% | **No-go** |
| severity_spanish | `F_catboost` | **−10.11%** | [−11.62%, −8.60%] | 1.52% | 2% | **No-go** |

At 10,000 rows the GLM is the better baseline on Spanish frequency (`E_glm` −7.20%, `F_catboost`
−6.78%); CatBoost remains the better one on the other three. The matched means:

| Target | `B_ft30` | `E_glm` | `F_catboost` | Anchor |
|---|---:|---:|---:|---:|
| frequency_french | 3238.43 | 3221.22 | **3204.16** | 3279.33 |
| frequency_spanish | 9606.66 | **8961.78** | 8996.65 | 10163.28 |
| severity_french | 1.13038 | 1.12392 | **1.12340** | 1.13001 |
| severity_spanish | 0.63955 | 0.59316 | **0.58073** | 0.69047 |

## What the numbers say, and what they do not

**French frequency: the loss is mostly the budget.** At the primary budget CatBoost trains on
542,410–542,411 rows against TabPFN's 10,000 — 54× — and wins by 7.93% with every fold negative (−3.85%,
−10.08%, −8.69%, −7.54%, −9.47%). At matched rows the gap falls to 1.10% and the interval covers
zero and the floor, so the registered rule returns **Inconclusive**: on these rows this experiment
does **not** show TabPFN to be worse, and it does not show it to be better either. The honest
sentence is that the primary No-go is a statement about the registered comparison *as run*, and
the matched arm attributes most of it to data volume.

**Spanish frequency: a loss that survives the budget, with a large budget component.** At the
primary budget CatBoost is 13.66% ahead. At 10,000 rows its advantage halves to **−6.78%**, the GLM
overtakes it at **−7.20%** and becomes the better baseline, and every matched fold is negative
(−9.02%, −1.03%, −8.89%, −6.29%, −10.76%). So part of the primary gap is rows — a tree ensemble is
the data-hungry method here — but a 7% deficit remains against the GLM at equal rows, which is a
model-class result. The target is also underpowered on this arm (MDE 4.76% against its 4% floor),
so the *size* of the matched loss is soft even though its sign is not.

**French severity: fine-tuning is the cause.** The contender loses by 0.79% at full pool and 0.62%
at matched rows, with intervals excluding zero in both. But `A_raw` scores **+0.13%** and
**+0.29%** — raw TabPFN is at least level with, and marginally ahead of, both baselines. The
registered contender is the fine-tuned model, so the verdict is No-go; the mechanism is the
fine-tuning harm the fair test already measured (−0.92% against `A_raw`), not a deficit of the
foundation model. `B_ft30` is also slightly worse than the intercept-only anchor on this target
(1.13038 vs 1.12994), which is the sharpest available statement of how little the fine-tuned model
adds here.

**Spanish severity: a model-class loss.** The target's whole fold pool is below the 10,000-row cap,
so the two arms are the same fit and the −10.11% is not a budget artefact. CatBoost is 10.1% ahead
of `B_ft30`, the GLM 7.8%, and the anchor is 7.36% behind TabPFN — a clean ordering with TabPFN in
the middle.

**On French frequency, fine-tuning still helps TabPFN.** At matched rows `A_raw` is 12.06% behind
CatBoost while `B_ft30` is 1.10% behind — an 11-point swing on one target, in the same direction as
the fair test's registered +9.69% ([+7.43%, +11.95%]). That is a single derived contrast with no
interval of its own, and nothing here should be read as re-measuring the fair test: this experiment
compares each TabPFN configuration with a different model class, not the two configurations.

**Task means are descriptive.** Mean `r` against the better baseline is −10.79% (frequency) and
−5.45% (severity) at the primary budget, and −4.15% / −5.37% matched. No task-level verdict is
claimed: the two-portfolio bootstrap was registered for a different question, and the two
portfolios of the frequency task disagree about how much of the gap is budget.

## Limits

- **The GLM is not the best classical model available.** It is the case study's GLM1: main effects,
  no interactions or splines. Its own authors' GLMBoost beat it out of sample. A GLM loss is a loss
  for a main-effects GLM, not for the GLM family.
- **One CatBoost configuration.** Shipped defaults, as the repo's own evidence justified; the tuned
  grid was out of scope and is not a sensitivity arm here.
- **The Gamma family is not run**, so severity is compared on the metric the registration scores,
  not on a Gamma model's own deviance.
- **The primary budget favours the baselines.** That is the registered design, not a defect, but it
  is why the matched arm exists and why the two tables are read together.
- **Spanish frequency is underpowered** at its 4% floor (MDE 4.64%/4.76%), so its interval is wide;
  the sign is consistent across folds and arms, the magnitude is not pinned.
- **The GLM's seeds are duplicates at full pool**, as registered. They enter the fold mean three
  times identically; that does not move the point estimate and it narrows the GLM's contribution to
  the variance, which is why the verdict is taken against CatBoost.
- **The registered prose and the tool disagree on one corner of the rule.** The pre-registration
  describes Inconclusive as "CI covers both zero and the floor", but an interval can cover zero and
  sit wholly below the floor — French frequency's matched interval does. The rule as implemented by
  the shared `decide()` treats any zero-covering interval as Inconclusive, and that is the reading
  applied here, consistent with the fair test. This is recorded rather than resolved after the
  data; a future registration should state the corner explicitly.
- **What the budget sensitivity can say.** French frequency's matched arm shows the primary gap
  shrinks by 6.8 points when the baselines lose 532,410 rows; it cannot show that TabPFN matches
  CatBoost at equal data, because the matched interval covers zero and the target is underpowered.
  The other three targets lose at matched rows too, so for them budget is a component, not the
  explanation.
- **Calibration, lift, pure premium and the frequency × severity product are not assessed.** Two
  registered metrics, one per target.

## Cost and time

CPU only, measured 2026-11-13/14 on this workstation, wall and CPU seconds from `/usr/bin/time -p`
around each target's process:

| Arm | frequency_french | frequency_spanish | severity_french | severity_spanish | Total wall | CPU (user) |
|---|---:|---:|---:|---:|---:|---:|
| Primary, full pool | 6433 s | 461 s | 166 s | 55 s | **1 h 59 m** | 6.64 h |
| Matched, 10,000 rows | 246 s | 185 s | 93 s | 54 s | **9.6 m** | 1.06 h |

**$0.** The two arms together are 7.7 CPU-hours and 2 h 08 m wall; the French-frequency CatBoost
fits are almost all of it (the GLM slots land in ~13 s, the CatBoost slots in minutes). The raw
per-target `real/user/sys` lines behind this table are committed at
`docs/analyses/data/actuarial_baseline_timings.txt`. Engineering time is not instrumented and is
recorded as unmeasured rather than estimated.

## Reproduce

```
# primary: baselines on the whole fold pool
python scripts/run_fair_test.py --methods E_glm,F_catboost,M_intercept \
  --targets frequency_french --out-root results --run-id 20261113T223000Z
# ... and the other three targets with 20261113T223001Z / 223002Z / 223003Z

# matched: baselines capped at the fair test's 10,000 rows
python scripts/run_fair_test.py --methods E_glm,F_catboost,M_intercept --train-rows 10000 \
  --targets frequency_french --out-root results --run-id 20261114T003000Z
# ... and the other three with 20261114T003001Z / 003002Z / 003003Z

# the verdict, from the retained captures
python scripts/analyses/actuarial_baseline.py \
  --tabpfn-frequency-french 20261112T164543Z --baseline-frequency-french 20261113T223000Z \
  --tabpfn-frequency-spanish 20261112T184155Z --baseline-frequency-spanish 20261113T223001Z \
  --tabpfn-severity-french 20261112T210029Z --baseline-severity-french 20261113T223002Z \
  --tabpfn-severity-spanish 20261112T220641Z --baseline-severity-spanish 20261113T223003Z
```

`--json` emits the same numbers as data. Swap the four `--baseline-*` ids for the
`20261114T0030xxZ` family to reproduce the matched table. `./scripts/check.sh citation` proves
every cited id has the capture it claims.

**Version pin.** The TabPFN rows are `v3_default` (`tabpfn-v3-regressor-v3_default.ckpt`,
`tabpfn` 8.5.0), as each registered capture's record states. `docs/MODEL_VERSIONS.md` names
`v3.5_default` as the current line for these datasets on the inference path; the fine-tuning path
this experiment's contender comes from cannot express v3.5, so every TabPFN number here is v3. No
v3.5 number appears in this document. The baselines are scikit-learn 1.6.1
(`PoissonRegressor`/`TweedieRegressor`, Newton–Cholesky on a standardised design) and CatBoost
1.2.10, with their versions and fitted configuration recorded in each slot's `config`.
