# Where TabPFN loses on our own captures — the November 2026 capture audit

> **Status:** current — analysis, 2026-11-22 (#718). Reads committed captures and published tables;
> **$0, CPU-only, no TabPFN fit and no hosted call.** Written for map [#716](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/716).
>
> **Model eras are not mixed.** Tables 1–2 are `v3_default`; table 3 is the `v3.5_default` drift re-test;
> table 4 names the version in every row. A gap measured against the wrong era is not evidence
> (`docs/MODEL_VERSIONS.md`).

## 1. The answer

1. **TabPFN loses on count and severity targets, and the loss is large enough to act on.** Against the
   strongest reproducible baseline, it gives up **19.7% of Poisson deviance on French frequency**,
   **18.6% on Spanish frequency** and **12.0% on Spanish severity** in the policy-grouped 10,000-row
   regime — and **33.2% / 10.8% / 2.7%** in the full-data random-fold regime. Those are the three cells
   that justify a candidate under the threshold in §8. The mechanism is a model class, not a tuning miss:
   CatBoost and an exposure-offset Poisson GLM both beat it.
2. **On classification it mostly wins, and the losses are small.** At `v3_default` it loses log loss on
   three of seven cells and ties a fourth; the largest loss is **1.07%** (`norauto`). At `v3.5_default`
   the only surviving classification loss is `norauto`, by **0.08%**. It keeps the AUC lead on every
   other dataset, so these are calibration losses, not ranking losses.
3. **The `norauto` exposure finding is not one dataset — but it is not a v3.5 property either.** At
   `v3_default` an exposure-aware one-hot GLM beats TabPFN on log loss on **three of the five**
   exposure-carrying datasets (`norauto`, `ausprivauto0405`, `bemtl97`). At `v3.5_default` two of those
   reverse and only `norauto` survives, at 0.08%. On **frequency** targets the same idea is large and
   robust: a Poisson GLM with `log(Exposure)` as an offset beats TabPFN by 15.5% on French and 12.7% on
   Spanish Poisson deviance.
4. **A loss justifies a candidate when it clears three tests at once** — paired significance on ≥4/5
   folds, the task's registered floor in the metric's own units (2% relative for frequency/severity;
   0.002 AUC or 1% relative log loss for classification), and the same sign at matched training rows.
   Three cells pass all three. Everything else is a tie, a calibration quirk, or below the noise.

## 2. What counts as a cell, and what was audited

A **cell** here is one (dataset, metric, model version) triple with a committed artefact behind both
sides of the comparison. To enter a cell table it must have:

- a **committed capture** (a `results/<run>/capture.json` tree, or a committed per-fold CSV beside its
  runner) carrying the metric for TabPFN and for the baseline on **identical test rows**;
- a **pinned model version** — a checkpoint file or a literal `v3_default` / `v3.5_default` alias, not
  `auto`;
- a **reproducible baseline** from the set the repository already owns: tuned or default CatBoost /
  LightGBM, the one-hot or expert-binned linear model, and the exposure-aware variants of each;
- no new spend and no hosted fit to obtain either side.

Cells that fail a condition are listed in §9 rather than silently dropped. The inventory:

| Dataset | Target | In the audit? | Why |
|---|---|---|---|
| `coil2000` | purchase propensity | yes, both eras | v3 tuned baselines; v3.5 seed 42 |
| `uslapseagent` | lapse | yes, both eras | v3 tuned baselines; v3.5 seed 42 |
| `norauto` | claim propensity | yes, both eras | v3 + v3.5, **3 seeds**, exposure-aware GLM |
| `bemtl97` | claim propensity | yes, both eras | v3 + v3.5, 3 seeds, exposure-aware GLM |
| `ausprivauto0405` | claim propensity | yes, both eras | v3 + v3.5, 3 seeds, exposure-aware GLM |
| `bemtl16` | claim propensity | yes, clean data only | the 2026-08 numbers carry a target leak (#216); §21 supersedes them |
| `eudirectlapse` | lapse | yes, frontier harness | §17 re-test, 3 seeds; the lapse harness cell is excluded (§9) |
| `spanish_motor_lapse` | lapse | **no** | identical TabPFN version is not established in that harness (§9) |
| `freMTPL2freq` | frequency | yes, two fold regimes | frontier + the policy-grouped fair test |
| `spanish_motor_freq` | frequency | yes, two fold regimes | frontier + the policy-grouped fair test |
| `spanish_motor_severity` | severity | yes, two fold regimes | frontier + the policy-grouped fair test |
| `freMTPL2sev` | severity | yes, fair test only | no frontier cell |
| `bemtl97_amount` | claim amount | yes, clean data only | leak (#216) fixed 2026-10-08; §22 supersedes §16 |
| `ausautoBI8999` | claim amount | yes, both eras | v3 and v3.5 |
| `ausprivauto0405_vehvalue` | vehicle value | yes, both eras | v3 and v3.5 |

## 3. Classification, `v3_default` (seed 42, five folds) — table 1

Strongest baseline is chosen per row as the **lowest log loss among every baseline on record for that
dataset** — not a favoured method. Δ = TabPFN − baseline, so a negative Δ is a TabPFN win.

**Table 1 — classification cells, `v3_default`, seed 42**

| Dataset | TabPFN | Strongest baseline | Baseline | Δ | Δ% | Evidence | Verdict |
|---|---:|---|---:|---:|---:|---|---|
| `coil2000` | 0.20059 | `lr_tuned` | 0.20532 | −0.00473 | −2.30% | p=0.041 | win |
| `uslapseagent` | 0.24909 | `cat` | 0.25286 | −0.00377 | −1.49% | p=0.037 | win |
| `bemtl16` (clean) | 0.59681 | `lgbm` | 0.59849 | −0.00168 | −0.28% | p=0.015, 5/5 | win |
| `bemtl97` | 0.34279 | `lgbm` | 0.34177 | +0.00101 | +0.30% | p=0.0003, 0/5 | **loss** |
| `ausprivauto0405` | 0.24026 | one-hot LR + log(exposure) | 0.23853 | +0.00173 | +0.73% | p=1.8e-5, 0/5 | **loss** |
| `norauto` | 0.17619 | one-hot LR + log(exposure) | 0.17432 | +0.00186 | +1.07% | p=2.0e-5, 0/5 | **loss** |
| `eudirectlapse` | 0.37255 | one-hot LR | 0.37180 | +0.00075 | +0.20% | p=0.19, 1/5 | tie |

**Seed interval: unmeasured in every row of this table.** These v3 classification captures are
single-seed (42); the only interval they carry is the between-fold SE, which is not a seed interval. The
Phase 2 design's own convention is the opposite — a 95% interval **from the between-seed spread**, with
δ = 0.002 ROC AUC (`docs/experiments/pilot2-phase2/FINETUNING_PHASE2_OUTCOME.md`). By that convention this
table cannot resolve any of its three losses: one seed leaves nothing to compute a seed spread from.

**Ranking is a different answer.** Among the fourteen methods in the tuned-baseline suite, TabPFN is AUC #1
and PR-AUC #1 on all six frontier classification datasets at v3
(`frontier_tuned_baseline_summary.csv`). The exposure-aware GLM sits outside that suite, and it is the one
specification that also edges `norauto`'s AUC (−0.00034). So the three frontier losses above are
**calibration-axis losses while TabPFN keeps the ranking**, and `norauto` is the only dataset where it
loses both.

Sources: `scripts/eval/insurance_benchmark_v1/frontier_tuned_baseline_summary.csv`; §21.3 for clean
`bemtl16`; `scripts/eval/insurance_benchmark_v1/exposure_aware_glm_followup.csv` for the exposure-aware
rows; `scripts/eval/insurance_benchmark_v1/version_retest_eudirectlapse.csv`.

## 4. Count and severity, `v3_default` — and the matched-row regime

Two fold regimes exist and **must not be differenced**: the frontier suite uses random `KFold`, which can
put claims from one policy on both sides of a split; the fair test uses **policy-grouped** folds, where a
policy's claims never straddle a fold — the honest out-of-sample question. Same datasets, different
question.

### 4a. Full-data random folds (frontier harness, seed 42) — table 2a

**Table 2a — count and severity, full-data random folds, `v3_default`, seed 42**

| Dataset | Metric | TabPFN | Strongest baseline | Baseline | Δ | Δ% | ±SE (5 folds) |
|---|---|---:|---|---:|---:|---:|---:|
| `freMTPL2freq` | Poisson dev. | 0.38770 | `lgbm` | 0.29113 | +0.09657 | **+33.17%** | 0.00201 |
| `spanish_motor_freq` | Poisson dev. | 0.98764 | `lgbm` | 0.89157 | +0.09606 | **+10.77%** | 0.01624 |
| `spanish_motor_severity` | RMSE | 1.88616 | `lgbm` | 1.83719 | +0.04897 | **+2.67%** | 0.01165 |
| `bemtl97_amount` (clean) | RMSE | 2.04664 | `lgbm` | 1.99545 | +0.05120 | **+2.57%** | 0.0075 |
| `ausautoBI8999` | RMSE | 0.96490 | `cat` | 0.96883 | −0.00393 | −0.41% | 0.00868 — 3/5 folds, p=0.15: tie |
| `ausprivauto0405_vehvalue` | RMSE | 0.71162 | `lgbm` | 0.71645 | −0.00483 | −0.67% | 0.01246 — 5/5 folds, p=0.084: win on mean, not significant |

### 4b. Policy-grouped folds, 10,000-row TabPFN context (fair test, `v3_default` pin, **3 seeds**) — table 2b

This is the only regime in the audit with a real seed spread on the regression targets. Δ is relative
(`(baseline − TabPFN) / baseline`, positive = TabPFN better), per seed, recomputed from the committed
`meta.json` records (§10). The registered contender is the fine-tuned `B_ft30`; the audit's object is the
**default** `A_raw`, because that is the model a new project would start from.

**Table 2b — count and severity, policy-grouped 10,000-row folds, three seeds**

| Target | Metric | Baseline | `A_raw` vs baseline, seed 0 / 1 / 2 | Mean | Registered `B_ft30` |
|---|---|---|---:|---:|---|
| French frequency | Poisson dev. | `F_catboost`, full pool | −16.39 / −20.48 / −22.29% | **−19.72%** | −7.93% (CI [−10.99, −4.86]) |
| French frequency | Poisson dev. | `F_catboost`, 10k rows | −9.60 / −13.31 / −13.42% | **−12.11%** | −1.10% (CI [−3.43, +1.22], Inconclusive) |
| Spanish frequency | Poisson dev. | `F_catboost`, full pool | −17.46 / −20.03 / −18.15% | **−18.55%** | −13.66% (CI [−18.26, −9.06]) |
| Spanish frequency | Poisson dev. | `E_glm`, 10k rows | −10.93 / −12.91 / −11.55% | **−11.80%** | −7.20% (CI [−11.92, −2.48]) |
| French severity | RMSE | `F_catboost`, full pool | +0.17 / +0.17 / +0.07% | **+0.13%** | −0.79% (CI [−1.01, −0.56]) |
| Spanish severity | weighted RMSE | `F_catboost` | −11.94 / −11.90 / −12.11% | **−11.98%** | −10.11% (CI [−11.62, −8.60]) |

Three things this table shows that table 2a cannot:

- **Default TabPFN loses far more than the headline verdict says.** The fair test's "Inconclusive
  −1.10%" on French frequency is a statement about the **fine-tuned** arm. The default model loses
  **12.11%** at the same rows against the same CatBoost. Fine-tuning closes eleven of those twelve
  points.
- **The seed spread is small next to the gap.** Every seed's gap is on the same side of zero, and the
  three-seed range is 0.1–5.9 points wide against gaps of 12–20 points.
- **French severity is a tie, not a loss.** Raw TabPFN is 0.13% *better* than CatBoost, and the
  `A_raw` row is inside the 2% floor. The registered No-go for `B_ft30` is a fine-tuning harm
  (0.79%), which is the fair test's own verdict, not a TabPFN deficit.

## 5. The `v3.5_default` drift re-test, where three seeds exist — table 3

Everything here is `v3.5_default` against the same-version baseline on identical folds. Positive Δ% is
TabPFN ahead. The Δ% column is the mean over the seeds shown.

**Table 3 — `v3.5_default` cells**

| Dataset | Metric | Strongest baseline | Δ (seeds 42 / 7 / 123) | Δ% | Verdict |
|---|---|---|---:|---:|---|
| `norauto` | log loss | one-hot LR + log(exposure) | +0.00014 / +0.00020 / +0.00015 | +0.08% | **loss, 3/3 seeds** |
| `ausprivauto0405` | log loss | one-hot LR + log(exposure) | −0.00037 / −0.00031 / −0.00025 | −0.13% | win, 3/3 |
| `bemtl97` | log loss | `lgbm` | −0.00133 / −0.00125 / −0.00127 | −0.38% | win, 3/3 |
| `eudirectlapse` | log loss | one-hot LR | −0.00245 / −0.00266 / −0.00216 | −0.66% | win, 3/3 |
| `coil2000` | log loss | `lr` | −0.00866 | −4.21% | win (seed 42 only) |
| `uslapseagent` | log loss | `cat` | −0.00905 | −3.58% | win (seed 42 only) |
| `bemtl16` (clean) | log loss | `lgbm` | −0.00303 | −0.51% | win (seed 42 only) |
| `freMTPL2freq` | Poisson dev. | `lgbm` | +0.0102 | +3.5% | **loss, 0/5 folds** |
| `spanish_motor_freq` | Poisson dev. | `lgbm` | +0.0115 | +1.29% | **tie** (p=0.47) |
| `spanish_motor_severity` | RMSE | `lgbm` | +0.0235 | +1.28% | **loss, 0/5** |
| `bemtl97_amount` (clean) | RMSE | `lgbm` | +0.0289 | +1.45% | **loss, 0/5** |
| `ausautoBI8999` | RMSE | `cat` | −0.0169 | −1.74% | win, 5/5 |
| `ausprivauto0405_vehvalue` | RMSE | `lgbm` | −0.0060 | −0.83% | win, 5/5, p=0.078 |

**The version change is the single largest mover in this audit.** It turns the count losses from
33.2% → 3.5% (French frequency), 10.8% → 1.3% (Spanish frequency), 2.7% → 1.3% (Spanish severity) and
2.6% → 1.4% (`bemtl97_amount`), and it removes three of the four classification losses. The losses that
survive v3.5 are the ones a candidate should target; the ones it removed are a version artefact and
should not be re-litigated.

Sources: master report §16 and §22; `scripts/eval/insurance_benchmark_v1/version_retest_*.csv`;
`scripts/eval/insurance_benchmark_v1/home_turf_sweep_results.csv` for the size axis (§6).

## 6. Loses, ties, wins — by target, metric, regime and seed

**Loses.**

| Cell | Gap in the metric's units | Seed behaviour |
|---|---:|---|
| French frequency, 10k policy-grouped | +19.72% Poisson deviance (3-seed −16.4 to −22.3%) | same sign 3/3 |
| Spanish frequency, 10k policy-grouped | +18.55% Poisson deviance (−17.5 to −20.0%) | same sign 3/3 |
| Spanish severity, 10k policy-grouped | +11.98% weighted RMSE (−11.9 to −12.1%) | same sign 3/3 |
| French frequency, full random folds, v3 | +33.17% deviance | 1 seed |
| Spanish frequency, full random folds, v3 | +10.77% deviance | 1 seed |
| French frequency, v3.5 | +3.5% deviance (0/5 folds) | 1 seed |
| Spanish severity, full random folds, v3 | +2.67% RMSE | 1 seed |
| `bemtl97_amount`, clean | +2.57% RMSE (v3), +1.45% (v3.5) | 1 seed |
| `norauto` | +1.07% log loss (v3), +0.08% (v3.5); AUC −0.0003 (v3), −0.0010 to −0.0016 (v3.5) | 3/3 seeds |
| `ausprivauto0405` | +0.73% log loss at **v3 only** | 1 seed (v3) |
| `bemtl97` | +0.30% log loss at **v3 only** | 1 seed (v3) |

**Ties.** `spanish_motor_freq` at v3.5 (+1.29%, paired p=0.47 — not distinguishable);
`eudirectlapse` at v3 (+0.20% log loss, p=0.19); French severity raw (+0.13%, inside the 2% floor);
`ausautoBI8999` at v3 (−0.41%, p=0.15); `ausprivauto0405_vehvalue` on RMSE (−0.67%, p=0.084).

**Wins.** `coil2000` (−2.30% log loss, and −4.21% at v3.5); `uslapseagent` (−1.49% / −3.58%);
`bemtl16` clean (−0.28% / −0.51%); `eudirectlapse` at v3.5 (−0.66%, 3/3 seeds); `bemtl97` at v3.5
(−0.38%); `ausautoBI8999` at v3.5 (−1.74%); `ausprivauto0405` at v3.5 (−0.13%).

**By data regime.** On classification the win shrinks with size but never reverses: at 1,000 / 5,000 /
full rows TabPFN's log-loss lead over the best GBDT is 8.0 / 7.2 / 5.5% on `coil2000`, 16.1 / 9.1 / 3.6%
on `uslapseagent` and 4.9 / 3.0 / 0.4% on `bemtl97` (`version_retest_home_turf_sweep.csv`). On count and
severity the opposite is true — **the gap grows when the baseline gets the whole fold pool**
(12.11% → 19.72% French frequency; 11.80% → 18.55% Spanish frequency) — which is what a
data-hungry baseline should do. There is no TabPFN arm at 1,000–5,000 rows on the count targets, so
that regime is unmeasured (§9), not a win.

## 7. Does the `norauto` exposure finding generalise?

**At `v3_default`, yes — to three of five exposure-carrying datasets.** The exposure-aware specification
is one-hot categoricals + numerics + `log(exposure)`. Δ = TabPFN − GLM log loss; positive means the GLM
is ahead. Fold counts are given for the v3 contrasts whose artefact records them.

**Table 4 — exposure-aware GLM vs TabPFN, by dataset and version**

| Dataset | v3, seed 42 | v3.5, seeds 42 / 7 / 123 | v3.5 verdict |
|---|---:|---|---|
| `norauto` | +0.00186 (0/5 folds) | +0.00014 / +0.00020 / +0.00015 | **GLM ahead 3/3 seeds** |
| `ausprivauto0405` | +0.00173 (0/5) | −0.00037 / −0.00031 / −0.00025 | TabPFN ahead 3/3 |
| `bemtl97` | +0.00069 (1/5) | −0.00166 / −0.00175 / −0.00166 | TabPFN ahead 3/3 |
| `bemtl16` | −0.01222 | −0.01356 | TabPFN ahead (1 seed) |
| `uslapseagent` | −0.02071 | −0.02596 | TabPFN ahead (1 seed) |

So the honest answer has three parts:

- **On v3 the finding is not a `norauto` curiosity.** Two other datasets lose log loss to the same GLM,
  and `ausprivauto0405` loses by 0.73% — larger than any v3.5 classification loss.
- **On v3.5 it is `norauto` only**, and the gap has collapsed to 0.08% (p=0.11 / 0.049 / 0.057 by seed).
  `norauto` is also the one dataset where the GLM takes the **AUC** lead, on every seed.
- **On frequency targets the exposure-aware GLM is unambiguously ahead of TabPFN** — 15.5% on French and
  12.7% on Spanish Poisson deviance against `E_glm`, a Poisson GLM with `log(Exposure)` as an offset.
  Those targets are also where CatBoost beats the GLM, so exposure is necessary but not sufficient for
  the strongest baseline.

The correction from #695 stands, and the version should be read with it: the four-of-five AUC sentence
excludes `norauto` at **both** versions (at v3 the GLM leads by 0.00034 on the one seed measured). What
differs by version is the **log-loss** claim. At v3 the same GLM also takes log loss on
`ausprivauto0405` and `bemtl97`; at v3.5 it does not.

Sources: `docs/experiments/frontier-benchmark/exposure_aware_glm_followup.md` (#695);
`scripts/eval/insurance_benchmark_v1/exposure_aware_glm_followup.csv`;
`scripts/eval/insurance_benchmark_v1/version_retest_norauto.csv`; fair-test baseline spec `E_glm`.

## 8. What threshold makes a loss a candidate

Stated as a rule, not a ranking. A loss justifies a candidate when **all three** hold:

- **A — resolved.** Paired test p<0.05 and the same sign on ≥4 of 5 folds (or ≥2 of 3 seeds). Where the
  artefact records no fold count, the seed test is the one applied.
- **B — above the registered floor, in the metric's own units.** For frequency, severity and count:
  ≥2% relative (the fair test's floor; Spanish frequency carries 4%). For classification: ≥0.002 ROC AUC
  on the ranking axis (the Phase 2 δ), or ≥1% relative on the calibration axis — no calibration floor has
  been registered, and 1-in-100 is the scale δ sets.
- **C — not a budget artefact.** At matched training rows the gap still clears B.

Applied to the tables:

**Table 5 — the threshold applied**

| Cell | A | B | C | Candidate? |
|---|---|---|---|---|
| French frequency | yes, 3/3 seeds | 19.7% ≥ 2% | 12.1% ≥ 2% | **yes** |
| Spanish frequency | yes, 3/3 seeds | 18.6% ≥ 4% | 11.4% ≥ 4% | **yes** |
| Spanish severity | yes, 3/3 seeds | 12.0% ≥ 2% | same fit (folds < 10k rows) | **yes** |
| `freMTPL2freq` at v3.5 | yes — p=0.0004, TabPFN wins 0/5 folds | 3.5% ≥ 2% | not measured at v3.5 | **borderline** — above the floor, below the v3 gap |
| `bemtl97_amount` | yes — p<0.001, TabPFN wins 0/5 folds | 2.6% (v3) / 1.4% (v3.5) | n/a | **no on v3.5**; the loss is mean-prediction bias, not ranking |
| `norauto` | yes at v3, no at v3.5 | 1.07% / 0.08%, both < 1% | n/a | **no** — below floor even where significant |
| every other classification cell | mixed | < 1% relative | n/a | **no** |

**Read plainly:** three cells justify a candidate and all three are count/severity; one is borderline and
is a version-drift question; nothing on the classification side is big enough to spend on. The candidate
these cells point at is **"close the count/severity gap against CatBoost, at matched rows, on
policy-grouped folds"** — it is an existing, measured loss, not a re-test of a win.

## 9. What was not searched, and what stays unmeasured

- **AutoGluon.** It is configured only inside the TabArena lapse harness
  (`scripts/eval/lapse_benchmark_v1/`), not in the frontier harness. That harness's TabPFN version is not
  established in its artefact, and §17 showed it scores `eudirectlapse` 0.023 AUC below the frontier
  harness on identical test folds. So `spanish_motor_lapse` (TabPFN 0.7553 vs GBM 0.7500) and
  `eudirectlapse_premium` are **era-unresolved**, not audited. `eudirectlapse` is recovered through the
  frontier harness; `spanish_motor_lapse` is not.
- **A GLM with splines.** No spline basis has been fitted anywhere in the repository. The strongest
  linear baselines available are expert-binned / one-hot with `log(exposure)`; a spline GLM is
  **UNMEASURED**, not substituted. (`docs/experiments/fair-test-freq-sev/baseline_method_specification.md`
  records the expert-bin encoding as the case study's GLM1 scheme.)
- **Tuned CatBoost on count and severity.** None exists; the fair test pins CatBoost at shipped defaults
  by design. On classification, tuned CatBoost **regressed** on all six datasets (e.g. `norauto` log loss
  0.18302 vs 0.17676 default), so the default is the stronger reproducible CatBoost and is what the
  tables use.
- **Seed intervals on `v3_default`.** Every v3 classification cell and all six v3 frontier regression
  cells are single-seed. Their loss claims are **not** seed-resolved; table 1 says so row by row.
- **The 1,000–5,000-row count regime.** `docs/experiments/fair-test-freq-sev/` and the row curve ran
  baselines only; no TabPFN arm was run at those budgets (stage 2 is unfunded). The conclusion that
  "nothing beat the intercept" there is a statement about the baselines, not about TabPFN.
- **Other foundation models.** TabFM was never executed (OOM on `coil2000`, §14.13.4); TabICL v2 was
  measured for feasibility only (#687). No comparison arm exists.
- **Hosted fits and new spend.** Excluded by the ticket. Every number above was already committed
  before this audit.

## 10. Evidence and reproduction

**Revision.** This audit reads the tree at commit `669db1de309517c686cba5da7b26000b75310f6f` (the tip of
`main` when it started). No experiment output was regenerated.

**What was read, not recomputed.** Every classification and frontier number is the owning document's or
its committed CSV's. Where a document and its CSV disagree, the CSV wins — the rule is applied once, to
the label corrected at the end of this section.

**What was recomputed.** Only the per-seed relative gaps in table 2b, from the committed `meta.json`
records. The recipe is unambiguous — mean `verdict_metric_value` over the five folds for `A_raw`, the
same for `F_catboost` or `E_glm`, then `(baseline − tabpfn) / baseline`:

```python
import json
# run ids: TabPFN 20261112T164543Z / ...184155Z / ...210029Z / ...220641Z
#          baselines 20261113T223000Z / ...223001Z / ...223002Z / ...223003Z
cap = json.load(open(f"results/{run}/capture.json"))
for c in cap["captures"]:
    m = json.load(open(f"results/{run}/{cap['dataset']}/{c['record']}"))
    # m["verdict_metric_value"], m["seed"], m["fold"], c.get("method") or c.get("arm")
```

**Run ids cited** (all resolve to a committed `capture.json`): `20261112T164543Z`,
`20261112T184155Z`, `20261112T210029Z`, `20261112T220641Z`, `20261113T223000Z`,
`20261113T223001Z`, `20261113T223002Z`, `20261113T223003Z`, `20261114T003000Z`,
`20261114T003001Z`, `20261114T003002Z`, `20261114T003003Z`. The TabPFN captures record
`weights.path = tabpfn-v3-regressor-v3_default.ckpt`, which is how the v3 pin is established for the
fair test; the baseline captures are schema 5 and record `method` per slot.

**One correction to a owning document.** The #695 note's Reading bullet calls `bemtl97`'s v3
"+0.00002" a log-loss loss; that figure is the **Brier** Δ. The log-loss gap at v3 is **+0.00069**
(GLM ahead) and the v3.5 rows win it back (−0.00166). The note's conclusion — small in size and
reversed on v3.5 — is unchanged; only the label is.

## 11. Identifiers for the external claims

Internal measurements are cited to their owning artefact above. The external methods named carry an
identifier:

| Claim | Source |
|---|---|
| TabPFN is a prior-data fitted network; fine-tuning is a supported use | Hollmann et al., *Accurate predictions on small data with a tabular foundation model*, Nature 637, 319–326 (2025), DOI [10.1038/s41586-024-08328-6](https://doi.org/10.1038/s41586-024-08328-6) |
| CatBoost's ordered target statistics and ordered boosting | Prokhorenkova et al., *CatBoost: unbiased boosting with categorical features*, arXiv:[1706.09516](https://arxiv.org/abs/1706.09516) |
| AutoGluon's stacked-ensemble tabular baseline | Erickson et al., *AutoGluon-Tabular: Robust and Accurate AutoML for Structured Data*, arXiv:[2003.06505](https://arxiv.org/abs/2003.06505) |
| The TabArena harness the lapse benchmark runs on | Erickson et al., *TabArena: A Living Benchmark for Machine Learning on Tabular Data*, arXiv:[2506.16791](https://arxiv.org/abs/2506.16791) |
| GLMs, and the exposure offset as an additive log-scale covariate | Nelder & Wedderburn, *Generalized Linear Models*, JRSS A 135(3), 370–384 (1972), DOI [10.2307/2344614](https://doi.org/10.2307/2344614) |
