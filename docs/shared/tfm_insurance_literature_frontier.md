# Tabular foundation models on insurance tasks — the literature frontier, 2024–26

> **Status:** current as of 2026-11-22 — a reading of the external literature for map
> [#716](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/716). It reports no measurement
> performed in this repository and supersedes none of its results.

**Purpose.** Answer [#717](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/717): what is
published about tabular foundation models (TFMs) on actuarial and insurance prediction; what this
repository has already settled against it; what published evidence contradicts the programme's current
position; and which questions the literature has closed, so a candidate does not pay to re-run them.

**The rule for every claim.** It carries a DOI or arXiv id, or it is marked **unverified lead**. A
paper cited here was read at least to abstract; where a number is quoted it was read in the paper's own
text. First-party vendor pages are cited by URL and labelled *(first-party)*: they are evidence of what
the vendor claims, not independent evidence.

**Why this file is here.** `docs/analyses/` is now only an evidence directory — its
[README](../analyses/README.md) sends notes to `docs/experiments/` and `docs/archive/`, and this
note belongs to no single campaign. `docs/shared/` is the repository's cross-campaign home for the
metric registry, the explainers, the model catalog and the levers assessment, so the literature frontier
goes here.

## What was searched, and what was not

**Searched (2026-11-22).** OpenAlex works 2023–2026 for `TabPFN`, `tabular foundation model`,
`fine-tuning`, `calibration`, `conformal`, `distribution shift`, `insurance pricing`, `loss reserving`,
`IBNR`, `exposure offset`, `interpretability`, plus title/author follow-ups from the TabPFN, TabICL and
TabArena reference lists. Read in full: Deprez et al. (insurance pricing), Rubachev et al.
(fine-tuning), Richman & Wüthrich (reserving), Rundel et al. (interpretability), and the Prior Labs
insurance cookbook. Read to abstract: every other citation below.

**Not searched.** SSRN full texts and insurer-internal work behind paywalls; conference proceedings not
indexed in OpenAlex; non-English literature; anything posted after the search date; vendor model cards for
TabICL, Mitra, TabDPT and LimiX beyond their abstracts; the TabArena live leaderboard (it moves, so this
note cites the papers instead). There is no systematic-review protocol, no screening log and no PRISMA
count. **A missing citation below means the search did not find it, not that the field is silent.**

## The six families at a glance

| Family | Published position, 2024–26 | What this repository has settled | What is still open |
|---|---|---|---|
| Fine-tuning and adaptation | Full fine-tuning helps most on IID data; it does not rescue gradual temporal drift | Classifier: one small gain in four; regressor: frequency Go, severity No-go | Adaptation to grouped/insurance data at 10k–678k rows; thinking-mode and distillation |
| Calibration and distributional output | TFMs emit full predictive distributions; rankings depend on the scoring rule; the joint is not coherent | Classification calibration is a tie-to-win; regression quantiles degrade under fine-tuning | Proper-scoring comparison against GLM/GBDT on insurance targets; joint multi-target |
| Exposure and offsets | No native offset or sample weight; exposure-as-feature is the published workaround | The exposure-aware GLM contrast is measured on five datasets; `norauto` is the exception | A method that imposes proportionality; extrapolation beyond the observed exposure range |
| Ensembles and hybrids with GBDTs | Cross-model ensembles advance the general SOTA; TabPFN is not the only strong family | Only the estimator-count and context levers are closed; no TabPFN+GBDT hybrid run | Any insurance hybrid, and whether it survives the weight licence |
| Interpretability | SHAP/LOCO/SAGE adaptations, transparent GAM and kernel heads, zero-shot attributions | Permutation importance exists for one diagnostic; parsimony is a parameter-count proxy | Explanation stability and actuarial/regulatory acceptance |
| Loss reserving | Micro-level and ensemble distributional reserving; **no TFM evaluation at all** | No reserve arm; a severity proxy only | The entire family: triangles, development factors, IBNR |

---

## 1. Fine-tuning and adaptation

**Published.** Full fine-tuning is the practical choice for TabPFNv2, and its mechanism is now
explained: gradient adaptation sharpens the retrieval weights between test queries and in-context
training rows rather than teaching a new function. On IID academic splits this reaches
state-of-the-art; on datasets with **gradual temporal shifts and rich feature sets, TabPFNv2 is less
stable and prior methods remain better** ([arXiv:2506.08982](https://arxiv.org/abs/2506.08982),
Rubachev et al., 2025). Earlier work had already found fine-tuned in-context transformers to be strong
tabular classifiers ([arXiv:2405.13396](https://arxiv.org/abs/2405.13396), Feuer et al., 2024), which
is why the 2025 paper re-ran the question rather than trusting the earlier result.

The vendor's own line has moved from "fine-tune the weights" to "spend inference compute": TabPFN-3
introduces test-time compute scaling, and TabPFN-3.5-Thinking is claimed up to 12× faster than the
previous thinking mode ([arXiv:2605.13986](https://arxiv.org/abs/2605.13986);
[arXiv:2609.17895](https://arxiv.org/abs/2609.17895), both first-party technical reports). Fine-tuning
guidance, DDP support and the commercial-vs-research distinction live in the vendor docs
([Fine-Tuning](https://docs.priorlabs.ai/capabilities/fine-tuning), *first-party*).

**What this repository has established.**

- **Classifier fine-tuning is a small, dataset-specific gain, not a general one** — +0.0035 ROC AUC on
  `uslapseagent`, equivalence on two cells, `coil2000` unmeasurable at design precision. Owner:
  [FINETUNING_PHASE2_OUTCOME.md](../experiments/pilot2-phase2/FINETUNING_PHASE2_OUTCOME.md).
- **Regressor fine-tuning separates by target** — frequency pooled +6.85% against a 2% floor (Go);
  severity pooled +0.36%, heterogeneous — no task-level gain. Owner:
  [freq_sev_fair_test_result.md](../experiments/fair-test-freq-sev/freq_sev_fair_test_result.md).
- **Fine-tuning moves the conditional mean and not the uncertainty** — pinball loss is unchanged on
  two targets and significantly worse on the other two, and the count quantile head is unusable as
  configured. Owner:
  [freq_sev_quantiles.md](../experiments/fair-test-freq-sev/freq_sev_quantiles.md).

The repository's own reading of the fine-tuning literature already sits in
[FINETUNING_LITERATURE.md](../experiments/pilot2-phase2/FINETUNING_LITERATURE.md); this note does not
restate it, and a candidate should read that file first.

**Still open.** Rubachev's temporal-shift finding is the closest published statement to this
repository's targets — lapse and surrender are temporal and rich-featured — yet the repository's
splits are random or policy-grouped, not temporal. No published study fine-tunes on an insurance
portfolio with a genuine out-of-time split. **Named silence:** insurance fine-tuning under temporal
split. Whether thinking-mode beats weight fine-tuning on these targets is also unpublished.

## 2. Calibration and uncertainty for distributional outputs

**Published.** TabPFN's regression head returns a discretised predictive distribution rather than a
point ([Nature 637, 319–326](https://doi.org/10.1038/s41586-024-08328-6), Hollmann et al., 2025), and
the vendor exposes quantiles and the full distribution through one call
([Regression](https://docs.priorlabs.ai/capabilities/regression), *first-party*). Four independent
results qualify how far that can be trusted.

1. **The scoring rule can reorder the leaderboard.** On 101 regression datasets, models strong on RMSE
   can rank lower on CRPS, energy score or interval score
   ([arXiv:2603.29928](https://arxiv.org/abs/2603.29928), ScoringBench, 2026). Metric choice is a
   modelling decision, not a reporting detail.
2. **Data-scarce uncertainty favours Gaussian processes.** Against TabPFN v2.5 on regression problems,
   GPs "often provide superior predictive accuracy and UQ in data-scarce settings", while TabPFN is
   competitive on complex, high-dimensional problems with sufficient data
   ([DOI 10.1109/mcse.2026.3701626](https://doi.org/10.1109/mcse.2026.3701626), Johnson et al., 2026).
3. **Prediction regions need post-hoc repair.** TFM regression regions can under- or over-cover even
   when point predictions are accurate; highest-density split conformal restores marginal coverage and
   reduces group-coverage error, at the cost of calibration rows
   ([arXiv:2609.34887](https://arxiv.org/abs/2609.34887), Park et al., 2026).
4. **The multivariate distribution is not a coherent stochastic process.** Every TFM tested violates
   both marginalization and factorization consistency, for classification and regression, on all
   datasets ([arXiv:2608.06004](https://arxiv.org/abs/2608.06004), Klötergens et al., 2026). A
   per-policy marginal can be usable while a joint claim across linked targets is not.

The vendor now offers held-out NLL/CRPS calibration of the ensemble distribution
([August 2026 changelog](https://docs.priorlabs.ai/changelog/august-2026), *first-party*) — an
admission that the default distribution is not calibrated by construction.

**What this repository has established.**

- **Classification calibration is at worst a narrow, seed-specific loss and at best a paired win**, on
  the canonical suite and on the three Tier 3 datasets, with two named v3-era exceptions that the v3.5
  re-test reverses. Owner:
  [tabpfn_vs_gbdt_baselines_finetuning.md](../experiments/frontier-benchmark/tabpfn_vs_gbdt_baselines_finetuning.md)
  §11.5, §14.11–§14.13, §18–§20.
- **The regression distribution is measured, and it does not inherit the point gain** — coverage is
  near nominal in the middle, under-covers at the top, and the count quantile head emits negative
  counts at low levels. Owner:
  [freq_sev_quantiles.md](../experiments/fair-test-freq-sev/freq_sev_quantiles.md).

**Still open.** The repository has never scored a regression arm with CRPS or an interval score against
a GLM or GBDT on an insurance target, and has never tested the joint distribution across frequency and
severity. Both are $0 re-scores of existing captures in principle, and both are exactly where the
published literature says a point-metric verdict can invert. **Named silence:** no published
proper-scoring comparison of a TFM against GLM/GBDT on insurance severity or pure premium.

## 3. Exposure and offset handling

**Published — and this is the sharpest practical finding in the literature.** TabPFN supports neither
an offset nor observation weights; the public `fit` signature takes `X` and `y` only
([regressor fitting](https://docs.priorlabs.ai/api-reference/python/tabpfn/regressor/fitting-and-prediction),
*first-party*). The only published insurance-pricing evaluation states the consequence: exposure enters
as an ordinary feature, predictions are read at a counterfactual full year of exposure, and "this is
not equivalent to an offset" because proportionality is learned rather than imposed
([arXiv:2605.22892](https://arxiv.org/abs/2605.22892), Deprez, Verbeke & Verdonck, 2026). The vendor's
own insurance cookbook uses the same workaround, adds a single portfolio-level rescale estimated on a
held-out slice — balance 0.83 → 0.93 — and notes that constant rescaling leaves the ranking untouched
([Insurance Claim Modeling](https://docs.priorlabs.ai/cookbook/insurance_claim_modeling), *first-party*).
The actuarial comparators already handle exposure properly: frequency GBDTs take exposure offsets and
probabilistic boosting has an exposure-aware formulation
([DOI 10.1007/s13385-025-00428-5](https://doi.org/10.1007/s13385-025-00428-5), Chevalier & Côté, 2025;
[DOI 10.1080/10920277.2025.2451860](https://doi.org/10.1080/10920277.2025.2451860), Holvoet, Antonio &
Henckaerts, 2025).

**What this repository has established.**

- **The limitation and its substitute were documented here before the pricing paper appeared** — the
  harness already replaces `Exposure` with `log(Exposure)` as a feature for every model on
  `freMTPL2freq`, and the regime note quotes the "neither an offset nor observation weights" sentence
  against it. Owner:
  [regime_characterization.md](../experiments/frontier-benchmark/regime_characterization.md) §2
  (external corroboration, #684).
- **The exposure-aware contrast is measured across five datasets, which no published paper found in
  this search does** — a
  one-hot logistic GLM with `log(exposure)` is fitted on identical folds for the five datasets that
  carry an exposure column; TabPFN keeps the AUC lead on four, and `norauto` is the exception where the
  GLM wins on log loss and AUC. Owner:
  [exposure_aware_glm_followup.md](../experiments/frontier-benchmark/exposure_aware_glm_followup.md)
  (#695), summarised in
  [CONCLUSION.md](../experiments/baseline-conclusion-2026-11/CONCLUSION.md) §3.
- **The count verdict is already a count-with-exposure-feature verdict on `freMTPL2freq`** — that
  target is scored on Poisson deviance with log-exposure as a feature, and it is off the frontier by
  +0.0966; both frequency regressions and the severity regression are off the frontier. Owner:
  [CONCLUSION.md](../experiments/baseline-conclusion-2026-11/CONCLUSION.md) §3, table 1.

**Still open.** No published or internal work tests whether TabPFN extrapolates sensibly when a
policy's exposure lies outside the training range, which is the operational case the feature workaround
is least able to guarantee. No work tests the rate-target alternative (`count / exposure`) against the
count-target-plus-feature form on insurance data, and the one paper that considered it rejected it on
tail grounds without measuring it (Deprez et al. §3). **Named silences:** exposure extrapolation; a weights-aware TFM
formulation; and the bias that arises when the exposure distribution differs between train and
deployment.

## 4. Ensembles and hybrids with GBDTs

**Published.** TabArena, the living benchmark, concludes that **gradient-boosted trees remain strong
contenders**, that deep learning caught up only under larger tuning budgets with ensembling, that
foundation models excel on smaller datasets, and that **cross-model ensembles advance the
state of the art** ([DOI 10.52202/085713-0519](https://doi.org/10.52202/085713-0519), Erickson et al.,
2025). On the vendor side, TabPFN-2.5 claims a 100% win rate against default XGBoost up to 10k rows and
87% on larger data, and ships a distillation engine that turns TabPFN into an MLP or tree ensemble with
most of the accuracy and far lower latency
([arXiv:2511.08667](https://arxiv.org/abs/2511.08667), *first-party*). TabPFN-3 claims a single forward
pass beats tuned and ensembled baselines on TabArena
([arXiv:2605.13986](https://arxiv.org/abs/2605.13986), *first-party*). But TabPFN is not the only
frontier: TabICLv2, with no tuning, is reported to surpass RealTabPFN-2.5 — itself tuned, ensembled and
fine-tuned on real data — on TabArena and TALENT
([arXiv:2602.11139](https://arxiv.org/abs/2602.11139), Qu et al., 2026). Mitra is a further independent
family ([DOI 10.52202/085713-0535](https://doi.org/10.52202/085713-0535)).

**What this repository has established.**

- **Only the cheap levers are closed, and neither is a hybrid** — `n_estimators=8` equals the server
  default and 1 is worse; context-window ensembling is already exercised by the full-size hosted runs.
  Owner: [levers_assessment.md](levers_assessment.md) (§13, §14.2, §12.1).
- **No TabPFN+GBDT stack, no blend and no distillation arm has been run here** — distillation is its
  own map (#368), and the model-line feasibility work covers TabICL v2 on CPU only. Owner:
  [cpu_model_feasibility.md](../experiments/tabarena/cpu_model_feasibility.md);
  [CONCLUSION.md](../experiments/baseline-conclusion-2026-11/CONCLUSION.md) §4.

**Still open.** No published study stacks a TFM with a GBDT on insurance data, so the general TabArena
result has not been transferred to this domain. The deployment path interacts with the weight licence:
TabPFN's weights are non-commercial, and adapted or distilled derivatives remain non-commercial
([tabular_foundation_models_catalog.md](tabular_foundation_models_catalog.md); Deprez et al. §2), so a
hybrid that wins on accuracy may still be undeliverable. **Named silence:** the accuracy/licence
frontier of an insurance TFM+GBDT hybrid.

## 5. Interpretability

**Published.** The TabPFN-specific toolkit is real: in-context learning makes exact-retraining Shapley
values and leave-one-covariate-out feasible, with data valuation for context selection
([arXiv:2403.10923](https://arxiv.org/abs/2403.10923), Rundel et al., 2024). Transparent architectures
also exist — GAMformer estimates GAM shape functions in one forward pass and performs comparably to
leading GAMs ([arXiv:2410.04560](https://arxiv.org/abs/2410.04560), Mueller et al., 2024) — and KernelICL
replaces the final prediction layer with kernels so each prediction is a weighted average of training
labels, at parity on 55 TALENT datasets
([arXiv:2602.02162](https://arxiv.org/abs/2602.02162), Miftachov et al., 2026). Zero-shot Shapley-style
attribution without model access is also proposed
([arXiv:2601.23068](https://arxiv.org/abs/2601.23068), Fonseca & Stoyanovich, 2026). The vendor ships
SHAP, partial dependence and a decoder attention readout
([Interpretability](https://docs.priorlabs.ai/capabilities/interpretability), *first-party*).

The insurance literature's own verdict is blunter: exposure, sparse counts and heterogeneous variance
are not the only missing pieces — TabPFN also has "the absence of transparent coefficients", and the
paper's future-work list asks whether it recovers the same risk drivers as a GLM
([arXiv:2605.22892](https://arxiv.org/abs/2605.22892), §1, §5).

**What this repository has established.**

- **Feature importance was measured once, and the first reading was partly an artefact** — D2's
  top-ten Jaccard of 0.54 between TabPFN and the GLM is partly collinearity, not a different risk
  story. Owner:
  [d5_eudirectlapse_explanation.md](../experiments/diagnostics/d5_eudirectlapse_explanation.md) §2;
  the design is [FINETUNING_DIAGNOSTICS_DESIGN.md](../experiments/diagnostics/FINETUNING_DIAGNOSTICS_DESIGN.md)
  and the exported table is indexed by
  [docs/analyses/data/README.md](../analyses/data/README.md).
- **Interpretability in the benchmark is a parameter count** — the frontier's parsimony axis treats
  fitted parameter count as a proxy, which is a governance convenience rather than an explanation.
  Owner:
  [insurance_frontier_benchmark_spec.md](../experiments/frontier-benchmark/insurance_frontier_benchmark_spec.md)
  §2.

**Still open.** No published study measures explanation stability for a TFM on insurance data, compares
its attributions with a GLM's coefficients on the same portfolio, or reports what a regulator accepted.
The toolkit exists; the acceptance evidence does not. **Named silence:** actuarial and regulatory
validation of TFM explanations.

## 6. Loss reserving

**Published.** Reserving has a live methodological literature and **no TFM evaluation**. The 2024–26
state of the art is micro-level and distributional: multinomial multi-state reserving for IBNR and RBNS
([DOI 10.3934/jimo.2026097](https://doi.org/10.3934/jimo.2026097), Menvouta et al., 2026); a
restructured chain-ladder that projects latest observations to ultimate through multi-period factors,
with a neural-network individual-claims application
([arXiv:2602.15385](https://arxiv.org/abs/2602.15385), Richman & Wüthrich, 2026); ensemble distributional
forecasting that combines stochastic reserving models on their full distributions
([DOI 10.1080/03461238.2024.2365392](https://doi.org/10.1080/03461238.2024.2365392), Avanzi et al.,
2024); and hybrid neural individual-development models
([DOI 10.1111/jori.12501](https://doi.org/10.1111/jori.12501), 2024). A 2026 review names reserving as a
plausible TFM use — "loss reserving with run-off triangles" — without evaluating one
([arXiv:2609.14576](https://arxiv.org/abs/2609.14576), Blier-Wong, 2026). Deprez et al. name the same
gap in their conclusion.

**What this repository has established.**

- **Nothing measured on a triangle.** There is no reserve arm, no development-factor benchmark and no
  IBNR target; the gap register says so explicitly. Owner:
  [CONCLUSION.md](../experiments/baseline-conclusion-2026-11/CONCLUSION.md) §4 ("Reserving and tails").
- **The earlier reserving note is a severity proxy, and is historical** — it infers unsuitability from
  claim-amount regression, not from reserving data, and predates the v3.5 re-tests. Read it as history:
  [RESERVING_WITH_FOUNDATIONAL_MODELS.md](../archive/reserving/RESERVING_WITH_FOUNDATIONAL_MODELS.md).

**Still open.** The whole family. There is also no published benchmark protocol for a TFM on a
triangle: rows are development periods, the grouped/time structure is exactly the regime where
independent benchmarks find trees strongest (counter-evidence item 2 below), and the target is a sum of
correlated cells rather than an i.i.d. row. **Named silence:** TFM loss reserving, in every part.

---

## The strongest published counter-evidence to the programme's position

The position under test is: *TabPFN leads conditional baselines on these targets.* The literature
supports a narrower version — it leads on small, IID, classification-like tables — and contradicts the
general claim in five ways, ordered by how directly they bear on a candidate here.

1. **On insurance pricing, TabPFN loses to a plain GLM on frequency.** Two public MTPL portfolios
   (`freMTPL2`, 678k policies; `beMTPL97`, 163k), 5-fold CV, TabPFN-v2.6 and v3 against a Poisson/gamma
   GLM and XGBoost: the GLM has the best Poisson deviance on both datasets; TabPFN-v3 is close on RMSE
   on the French data (0.490 vs 0.487) but clearly worse on deviance (0.343 vs 0.296), and the paper
   concludes it "is not yet ready to replace established actuarial methods for claim frequency". It is
   competitive on severity, where data are scarce. Inference reaches minutes at the capacity limit,
   against seconds for GLM/XGBoost, and the weights are non-commercial
   ([arXiv:2605.22892](https://arxiv.org/abs/2605.22892), Deprez, Verbeke & Verdonck, 2026). **This is
   the strongest counter-evidence in the search, and it is not news to this repository**: the
   same ordering was ingested on 2026-11-21 (#684) into
   [regime_characterization.md](../experiments/frontier-benchmark/regime_characterization.md), with the
   two correct citation limits — it tests v2.6 and v3, not v3.5, and its deviance is on rates while ours
   is on counts, so only the ordering carries. What is *not* yet absorbed is the structural claim: the
   gap is not a tuning artefact but missing offset, weights and distribution-specific loss, and no
   amount of seed-adding closes it.
2. **Grouped and large data still favour trees.** The first holistic benchmark beyond IID — 11 models,
   142 datasets, IID/temporal/grouped tasks — finds open-source TFMs competitive or better only up to
   about 100k rows, while "traditional tree-based and deep learning models still dominate on grouped or
   large data", and argues standard benchmarks are biased toward tasks where TFMs already excel
   ([arXiv:2606.30410](https://arxiv.org/abs/2606.30410), Purucker et al., 2026). This repository knows
   the BeyondArena suite exists and has called it "directly relevant to actuarial forecasting use cases
   we haven't tested yet" ([tabarena_reference.md](../experiments/tabarena/tabarena_reference.md)), but
   the *finding* — trees win on grouped/large — is the part that bears on the fair test's policy-grouped
   folds and on targets of 163k–678k rows.
3. **The general benchmark does not crown a single model class.** GBDTs remain strong, deep learning
   catches up only with larger budgets plus ensembling, foundation models excel on smaller datasets,
   and cross-model ensembles beat any one family
   ([DOI 10.52202/085713-0519](https://doi.org/10.52202/085713-0519), TabArena, 2025). A portfolio that
   only varies TabPFN's weights is measuring one cell of that picture.
4. **TabPFN is not uniquely state of the art.** TabICLv2 is reported to beat RealTabPFN-2.5 without
   tuning ([arXiv:2602.11139](https://arxiv.org/abs/2602.11139)); in credit risk, TabPFN-3 and TabICLv2
   are jointly strongest, with gains concentrated in small-sample and imbalanced settings
   ([arXiv:2605.18147](https://arxiv.org/abs/2605.18147), Baesens et al., 2026). Credit risk is the
   closest published financial analogue, and its result is *more* favourable to TFMs than the insurance
   pricing paper — the domain, not the model family, is doing the work.
5. **The distribution is not a joint, and the metric picks the winner.** All tested TFMs violate
   marginalization and factorization consistency ([arXiv:2608.06004](https://arxiv.org/abs/2608.06004)),
   GPs beat TabPFN on accuracy and UQ when data are scarce
   ([DOI 10.1109/mcse.2026.3701626](https://doi.org/10.1109/mcse.2026.3701626)), and rankings shift
   between point and proper scoring rules ([arXiv:2603.29928](https://arxiv.org/abs/2603.29928)). Any
   verdict stated in one metric, on marginal predictions, is a partial verdict.

**What the positive insurance literature actually contains.** Three application papers were found, and
none is a pricing study. Health-insurance claim-cost regression reports TabPFN-2.5 at R² 0.9776 on
13,904 records against classical ML, but on a random 70/30 split with RMSE/MAE/R² only
([DOI 10.3389/fpubh.2026.1880390](https://doi.org/10.3389/fpubh.2026.1880390), Shawosh et al., 2026); a
provider-fraud benchmark compares TabPFN with traditional and relational models
([DOI 10.2991/978-94-6239-693-7_77](https://doi.org/10.2991/978-94-6239-693-7_77), 2026); and a
cross-selling classification application is cited by Deprez et al. as the only peer-reviewed insurance
use, but no identifier was found in this search — **unverified lead**, not relied on. None tests
exposure, proper scoring, a temporal split or an exposure-aware baseline. The positive evidence is
thinner and weaker-designed than the single negative pricing paper, which runs against the usual
publication-bias direction and is worth saying plainly.

**One conflict inside the literature, which matters here.** The independent grouped-data finding
(BeyondArena, June 2026) predates TabPFN-3.5, whose report claims state of the art on temporal and
grouped splits ([arXiv:2609.17895](https://arxiv.org/abs/2609.17895), September 2026). No independent
evaluation of 3.5 on grouped insurance folds was found. The repo's policy-grouped fair test ran on
`v3_default`, not 3.5, so the question is open rather than settled either way.

## Questions the literature has settled — rule these out of the portfolio

| Question | Settled answer | Source |
|---|---|---|
| Does an untuned TFM beat a default GBDT on small IID tables? | Yes for ≤10k rows, by a wide margin against tuned baselines; re-running it buys nothing | [Nature 637, 319](https://doi.org/10.1038/s41586-024-08328-6); [arXiv:2511.08667](https://arxiv.org/abs/2511.08667) |
| Does TabPFN need per-dataset hyperparameter tuning to be competitive on small IID data? | No — default beats tuned baselines; the exposed knobs are temperature and estimator count | [Nature](https://doi.org/10.1038/s41586-024-08328-6); [model parameters](https://docs.priorlabs.ai/improving-performance/model-parameters) *(first-party)* |
| Does full fine-tuning beat parameter-efficient fine-tuning for TabPFNv2? | Yes, on time-efficiency and effectiveness | [arXiv:2506.08982](https://arxiv.org/abs/2506.08982) |
| Is fine-tuning the remedy for gradual temporal drift? | No; in-context drift adaptation is a separate method line | [arXiv:2506.08982](https://arxiv.org/abs/2506.08982); [arXiv:2411.10634](https://arxiv.org/abs/2411.10634) |
| Does TabPFN accept an offset or sample weight? | No; exposure must enter as a feature or a target transform | [regressor API](https://docs.priorlabs.ai/api-reference/python/tabpfn/regressor/fitting-and-prediction); [arXiv:2605.22892](https://arxiv.org/abs/2605.22892) |
| Is TabPFN the only frontier TFM? | No; TabICLv2 and Mitra are independent, competitive alternatives | [arXiv:2602.11139](https://arxiv.org/abs/2602.11139); [DOI 10.52202/085713-0535](https://doi.org/10.52202/085713-0535) |
| Is RMSE an adequate evaluation of a distributional model? | No; use proper scoring rules and interval coverage | [arXiv:2603.29928](https://arxiv.org/abs/2603.29928) |
| Does TabPFN need hand preprocessing of categoricals and missing values? | No; raw frames are accepted by design | [Nature](https://doi.org/10.1038/s41586-024-08328-6); [quickstart](https://docs.priorlabs.ai/quickstart) *(first-party)* |
| Are TabPFN's weights usable in commercial production without a licence? | No; non-commercial, and derivatives inherit it | [arXiv:2605.22892](https://arxiv.org/abs/2605.22892); [catalog](tabular_foundation_models_catalog.md) |

Two questions often assumed settled are **not**: whether a two-stage/hurdle formulation beats a
single-stage regressor on zero-inflated targets (the vendor cookbook finds the single-stage log-target
model matches it on accuracy, and Deprez et al. do not test it), and whether tree dominance holds
against TabPFN-3.5 on grouped folds. Neither belongs in the table above; both are live.

## Named silences — the supply of candidates

Stated as silences, not as recommendations; ranking belongs to #716.

1. **TFM loss reserving.** No published evaluation, no benchmark protocol, no repository arm.
2. **Exposure-native TFMs.** The literature documents the absence of offsets and settles for a feature
   workaround; nothing tests extrapolation, train/deployment exposure shift, or a weights-aware model.
3. **Proper-scoring evaluation on insurance targets.** CRPS, interval score and coverage against
   GLM/GBDT on severity or pure premium is unpublished here and outside.
4. **Independent grouped-split evaluation of TabPFN-3.5.** The vendor claims the regime the
   independent benchmark found hardest; nobody has published the test.
5. **Joint frequency–severity distributions from a TFM.** The consistency result says the joint is not
   coherent by construction; no actuarial application measures the consequence.
6. **Insurance TFM+GBDT hybrids**, and their interaction with the non-commercial weight licence.
7. **Interpretation acceptance.** No stability study, no coefficient-to-attribution comparison, no
   regulatory evidence.
8. **Temporal-split insurance fine-tuning.** The published place where fine-tuning fails is the shape
   of this repository's targets, and no insurance study tests it.

## What would change this note

A peer-reviewed TFM reserving evaluation; an independent TabPFN-3.5 grouped-data result; a
proper-scoring insurance comparison; a first-party weights/offset API; or an insurance-pricing paper
that reverses Deprez et al. on frequency with a matched tuning budget. None was found by 2026-11-22.

## Identifier ledger

| Source | Id | Type | Status |
|---|---|---|---|
| Hollmann et al., TabPFN | [10.1038/s41586-024-08328-6](https://doi.org/10.1038/s41586-024-08328-6) | Nature article | verified (abstract) |
| Rubachev et al., fine-tuning | [arXiv:2506.08982](https://arxiv.org/abs/2506.08982) | preprint | verified (full text) |
| Deprez et al., insurance pricing | [arXiv:2605.22892](https://arxiv.org/abs/2605.22892) | preprint | verified (full text) |
| TabPFN-2.5 report | [arXiv:2511.08667](https://arxiv.org/abs/2511.08667) | first-party report | verified (abstract) |
| TabPFN-3 report | [arXiv:2605.13986](https://arxiv.org/abs/2605.13986) | first-party report | verified (abstract) |
| TabPFN-3.5 report | [arXiv:2609.17895](https://arxiv.org/abs/2609.17895) | first-party report | verified (abstract) |
| TabICL | [arXiv:2502.05564](https://arxiv.org/abs/2502.05564) | ICML paper | verified (abstract) |
| TabICLv2 | [arXiv:2602.11139](https://arxiv.org/abs/2602.11139) | preprint | verified (abstract) |
| TabArena | [10.52202/085713-0519](https://doi.org/10.52202/085713-0519) | proceedings paper | verified (abstract) |
| BeyondArena | [arXiv:2606.30410](https://arxiv.org/abs/2606.30410) | preprint | verified (abstract) |
| ScoringBench | [arXiv:2603.29928](https://arxiv.org/abs/2603.29928) | preprint | verified (abstract) |
| TFM consistency | [arXiv:2608.06004](https://arxiv.org/abs/2608.06004) | preprint | verified (abstract) |
| Conformal coverage | [arXiv:2609.34887](https://arxiv.org/abs/2609.34887) | preprint | verified (abstract) |
| UQ of TFMs vs GPs | [10.1109/mcse.2026.3701626](https://doi.org/10.1109/mcse.2026.3701626) | journal article | verified (abstract) |
| Rundel et al., interpretability | [arXiv:2403.10923](https://arxiv.org/abs/2403.10923) | conference paper | verified (full text) |
| GAMformer | [arXiv:2410.04560](https://arxiv.org/abs/2410.04560) | preprint | verified (abstract) |
| KernelICL | [arXiv:2602.02162](https://arxiv.org/abs/2602.02162) | preprint | verified (abstract) |
| ExplainerPFN | [arXiv:2601.23068](https://arxiv.org/abs/2601.23068) | preprint | verified (abstract) |
| Drift-Resilient TabPFN | [arXiv:2411.10634](https://arxiv.org/abs/2411.10634) | NeurIPS paper | verified (abstract) |
| Credit-risk TFMs | [arXiv:2605.18147](https://arxiv.org/abs/2605.18147) | preprint | verified (abstract) |
| Insurance foundation-model review | [arXiv:2609.14576](https://arxiv.org/abs/2609.14576) | preprint | verified (abstract) |
| Health-insurance TabPFN | [10.3389/fpubh.2026.1880390](https://doi.org/10.3389/fpubh.2026.1880390) | journal article | verified (abstract) |
| Provider-fraud TabPFN | [10.2991/978-94-6239-693-7_77](https://doi.org/10.2991/978-94-6239-693-7_77) | proceedings paper | verified (title only) |
| Chevalier & Côté, probabilistic boosting | [10.1007/s13385-025-00428-5](https://doi.org/10.1007/s13385-025-00428-5) | journal article | verified (abstract) |
| Holvoet et al., NN pricing benchmark | [10.1080/10920277.2025.2451860](https://doi.org/10.1080/10920277.2025.2451860) | journal article | verified (abstract) |
| So, zero-inflated boosting | [10.1080/03461238.2024.2365390](https://doi.org/10.1080/03461238.2024.2365390) | journal article | verified (abstract) |
| Richman & Wüthrich, reserving | [arXiv:2602.15385](https://arxiv.org/abs/2602.15385) | preprint | verified (abstract) |
| mCube | [10.3934/jimo.2026097](https://doi.org/10.3934/jimo.2026097) | journal article | verified (abstract) |
| Ensemble distributional reserving | [10.1080/03461238.2024.2365392](https://doi.org/10.1080/03461238.2024.2365392) | journal article | verified (abstract) |
| Hybrid NN individual reserving | [10.1111/jori.12501](https://doi.org/10.1111/jori.12501) | journal article | verified (title/venue only) |
| Prior Labs docs and cookbook | [docs.priorlabs.ai](https://docs.priorlabs.ai/llms.txt) | first-party documentation | verified (pages named inline) |

No unverified lead is relied on in the body: the cross-selling application is named and marked as one,
and two further leads were checked and dropped for want of an identifier — a credit-risk conference
version superseded by `arXiv:2605.18147`, and a vendor blog post on insurance pricing that adds no claim
the cookbook does not carry.
