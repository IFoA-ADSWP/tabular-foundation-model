# Fine-Tuning Pilot — Canonical Design and Decision Framework

> Date: 2026-09-24 | Status: **Funded research workstream — design to be executed**
> Related: #22 | Follows the two measured probes documented in `docs/current/FINETUNING_FINDINGS.md`
> Diagnostics: `docs/current/FINETUNING_DIAGNOSTICS_DESIGN.md`
> Status summary: `docs/current/FINETUNING_STATUS_BRIEF.md`

> **Start here.** This is the canonical current proposal. The status brief is the short stakeholder summary; the diagnostics, cost, statistical, decision, and execution documents are supporting appendices. If another document appears to describe a different programme, this document takes precedence.

---

## 1. Purpose

The two probes establish a useful but incomplete result:

- At **2,000 training rows**, full supervised fine-tuning did not beat raw TabPFN.
- At **10,000 training rows**, full supervised fine-tuning beat raw TabPFN at 3, 10, and 30 epochs, with paired intervals excluding zero and calibration improving alongside ranking.

This is a hypothesis about a data-scale threshold, not yet a general finding about TabPFN on insurance data. The full pilot must determine whether the 10K result is robust, whether it is caused by genuine domain adaptation, and whether preprocessing, feature engineering, class imbalance, or target definition explain part of the effect.

**Research context.** Christoph Molnar's *Tabular Foundation Models* describes PFN-style models as in-context predictors whose pretraining prior supplies an inductive bias. That framing sharpens this pilot: raw TabPFN is not a conventional zero-training model; it uses the supplied table as prediction context. The comparison must therefore ask whether weight adaptation adds value beyond simply giving raw TabPFN more context. The book also distinguishes synthetic pretraining tasks from downstream synthetic-data augmentation; this proposal preserves that distinction. Source: [Molnar, *Tabular Foundation Models*](https://tabularfoundationmodels.com/).

This is an authorized, funded workstream. The stages below are scientific decision boundaries, not requests to release new funding.

## Programme scope map

| Workstream | Current role | When addressed |
|---|---|---|
| Diagnostics and prior-mismatch analysis | Understand why the two probes differed and which data structures may not match the model's learned prior | Phase 1 |
| In-domain fine-tuning | Test full SFT on the four R1 datasets | Phase 2 |
| Dataset pooling | Test whether source datasets can be combined | Phase 3, conditional on in-domain replication |
| Transfer learning | Test a model on a target dataset absent from its training pool | Phase 3, conditional on in-domain replication |
| Synthetic data / augmentation | Review prior negative evidence and run a targeted ablation where diagnostics justify it | Phase 1 / confirmatory follow-up |
| Regression, count, and severity extensions | Outside this in-domain classification pilot | Separate proposal if justified |

The full proposal therefore includes the earlier transfer and pooling work as explicit conditional phases, while keeping the current in-domain pilot as the prerequisite. Synthetic data is not treated as an assumed benefit: the existing negative evidence is recorded and revisited only as a controlled ablation.

## Run order and evidence status

| Order | Work | Status |
|---:|---|---|
| 1 | Dataset, feature, preprocessing, imbalance, target, and synthetic-data diagnostics | Run now |
| 2 | Two additional `uslapseagent` seeds at 10,000 rows | Run now |
| 3 | Four-dataset in-domain breadth pilot | After the seed gate |
| 4 | Targeted synthetic-data ablation, if diagnostics justify it | Conditional |
| 5 | Same-schema pooled transfer | Conditional on in-domain replication |
| 6 | Heterogeneous pooled transfer | Conditional on coherent-pool result |
| 7 | Use-case interpretation and deployment recommendation | Final synthesis |

**Measured now:** the 2,000-row probe and the 10,000-row `uslapseagent` probe.

**Not yet measured:** multi-seed replication, four-dataset breadth, a current-v3 synthetic-data ablation, pooled transfer, the shuffled-label control, and temporal validation.

---

## 2. Research questions

1. Does the 10K-row gain reproduce across seeds and splits?
2. Does it reproduce across the four R1 classification datasets?
3. Is the effect primarily discrimination, calibration, or both?
4. Is ordinary full supervised fine-tuning sufficient, or does a parameter-efficient method add value?
5. Does the gain survive better preprocessing, feature screening, and class-imbalance treatment?
6. Is the result a genuine in-domain adaptation effect, or an artefact of the experiment design?
7. If in-domain adaptation works, does it transfer to a target dataset absent from the training pool?
8. Does pool composition — same-schema versus heterogeneous — determine transfer success?
9. Can synthetic data or augmentation add useful training signal, or does it reproduce the earlier negative result?
10. Does fine-tuning outperform simply providing raw TabPFN with more context rows, and which insurance structures appear mismatched to the model's learned prior?

The pilot answers the in-domain question first. Transfer and pooling are included as conditional Phase 3 work, not as claims that can be made before in-domain replication.

---

## 3. Work phases

### Phase 1 — Diagnostics

Run the five diagnostics in `docs/current/FINETUNING_DIAGNOSTICS_DESIGN.md`, plus the synthetic-data evidence review described below, before drawing conclusions from the pilot.

The diagnostics cover:

1. dataset structure and target distributions;
2. prior-mismatch proxies: feature type mix, missingness, class balance, nonlinear interactions, target complexity, and row-to-feature ratio;
3. feature-importance differences between TabPFN, GLM, and tree models;
4. target reframing where count or frequency targets are involved;
5. preprocessing and feature-engineering ablations;
6. a focused `eudirectlapse` investigation;
7. a review of the existing synthetic-data and augmentation results, followed by a targeted ablation if the diagnostics identify a plausible mechanism.

The prior synthetic-data evidence is negative: TabPFN-extensions, SMOTE, and noise-based augmentation degraded performance, including a reported ROC AUC change from approximately 0.83 to 0.59 for noise augmentation. This does not contradict the use of synthetic tasks during model pretraining: pretraining data define a broad task prior, while augmentation adds synthetic rows to this project's downstream fine-tuning set. The relevant downstream evidence is in `docs/archive/PRE_FINETUNING_INVESTIGATIONS.md`, `docs/KNOWLEDGE-PATH.md` §S6, and `notebooks/baseline_experiments/06_synthetic_data_exploration.ipynb`. We do not rerun augmentation broadly by default; if tested, it must be a controlled arm against the same real-data baseline.

Diagnostics are not a substitute for the fine-tuning pilot. They identify confounds and determine which fine-tuning comparisons are meaningful.

### Phase 2 — Full in-domain fine-tuning pilot

The pilot uses the existing two probes as fixed reference conditions:

| Condition | Rows | Role |
|---|---:|---|
| Probe 1 reference | 2,000 | Reproduce the low-data negative regime |
| Probe 2 reference | 10,000 | Test the positive regime discovered by Probe 2 |
| Scale extension | larger available size, if practical | Determine whether improvement saturates |

The primary dataset is `uslapseagent`, because it produced the 10K positive result. The pilot then tests the same protocol on the other three R1 datasets:

- `coil2000`;
- `eudirectlapse`;
- `spanish_motor_lapse`.

The four-dataset family is the in-domain pilot scope. A wider 15-dataset sweep, pooled training, and cross-dataset transfer are not part of Phase 2; pooling and transfer are addressed conditionally in Phase 3.

### Phase 2.1 — Canonical arm labels

Display labels are phase-qualified. Implementation labels preserve the names already used by the pilot runner and artifacts.

| Display label | Implementation/run label | Phase | Required? | Description |
|---|---|---|---|---|
| `I_RAW` | `A_raw` | 2 | yes | Raw TabPFN control in every in-domain run |
| `I_SFT_3` | `B_ft3` | 2 | yes | Full SFT, 3 epochs |
| `I_SFT_10` | `B_ft10` | 2 | yes | Full SFT, 10 epochs |
| `I_SFT_30` | `B_ft30` | 2 | yes | Full SFT, 30 epochs |
| `I_DATA_TREATMENT` | `B_ft_data_treatment` | 2 | conditional | Class weighting, resampling, or calibration treatment |
| `I_PEFF` | `B_ft_peft` | 2 | conditional | Parameter-efficient or meta-learning comparison |
| `I_GLM` | `E_glm` | 2 | reference | Existing GLM baseline |
| `I_TREE` | `F_catboost` | 2 | reference | Existing tree baseline |
| `T_RAW` | `A_raw(T)` | 3 | conditional | Raw TabPFN on held-out target `T` |
| `T_POOL_ALL` | `C_pooled_all(T)` | 3 | conditional | Heterogeneous source pool |
| `T_POOL_SCHEMA` | `D_pooled_schema(T)` | 3 | conditional, primary | Coherent same-schema pool |
| `T_RANDOM_LABELS` | `R_random(T)` | 3 | conditional, control | Pooled training with shuffled source labels |

The display label is what appears in the proposal, tables, and interpretation. The implementation label is what appears in manifests, output directories, and analysis code. The mapping must be frozen before the next run; no arm may be renamed silently after results are inspected.

`A_raw` is re-run in every Phase 2 condition. Transfer comparisons use `A_raw(T)` on the held-out target. The parameter-efficient arm is a comparison point, not a requirement for the main conclusion.

### Phase 2.2 — Experiment matrix and training design

| Condition | Datasets | Rows | Seeds | Required arms | Epochs |
|---|---|---:|---:|---|---|
| Anchor replication | `uslapseagent` | 10,000 | 3 total, including the existing probe | `I_RAW`, `I_SFT_3`, `I_SFT_10`, `I_SFT_30` | 3, 10, 30 |
| Low-data reference | `uslapseagent` | 2,000 | 1 historical reference; additional seeds only if needed to resolve a conflict | `I_RAW`, `I_SFT_3`, `I_SFT_10`, `I_SFT_30` | 3, 10, 30 |
| In-domain breadth | all four R1 datasets | 2,000 and 10,000, subject to data availability | at least 2 | `I_RAW`, `I_SFT_3`, `I_SFT_10`, `I_SFT_30` | 3, 10, 30 |
| Synthetic ablation | one preselected dataset | matched to the chosen in-domain condition | at least 2 | matched real-data control plus one synthetic treatment | matched |
| Transfer | one preselected target `T` and eligible source pool | matched to the in-domain condition | at least 2 | `T_RAW`, `T_POOL_SCHEMA`, `T_RANDOM_LABELS`; `T_POOL_ALL` confirmatory | matched |

The matrix is frozen before the run. If a dataset cannot supply the requested row count, record the actual count and explain the deviation rather than silently substituting another size.

- Epoch budgets: 3, 10, and 30.
- Early stopping state is recorded explicitly.
- Training-row count is recorded for every run.
- Random seeds and split identifiers are persisted.
- The same preprocessing is used within each controlled comparison.
- Any class weighting or resampling is recorded as a separate arm.
- No result is promoted from a single run without a replication or an explicit limitation.

**Seed and split policy.** A seed controls both the train/test split and model initialisation. Within a seed, every arm sees the identical test rows and identical preprocessing. The existing Probe 2 seed is 42; two additional seeds are required for the 10K `uslapseagent` anchor. The four-dataset breadth phase uses at least two seeds per dataset. The split is random and stratified because no usable temporal index is available; this limitation is reported with every result.

### Phase 2.3 — Metrics

Probability quality is primary because insurance decisions depend on usable probabilities:

| Priority | Metrics |
|---|---|
| Primary | Brier score, log loss, calibration error |
| Secondary | ROC AUC, PR AUC |
| Diagnostic | Prediction distributions, subgroup error, calibration by score band |

Report discrimination and calibration separately. A fine-tuned model that improves ROC AUC while worsening calibration is not a general performance improvement for pricing or probability decisions.

The existing GLM and tree baselines remain comparison points. Fine-tuning is not being treated as a replacement for every baseline; it is being tested as an in-domain improvement to TabPFN.

### Phase 3 — Conditional transfer and dataset pooling

Phase 3 is released only if Phase 2 establishes a reproducible in-domain gain. It asks a different question: can one model adapt to an insurance target it has never seen during fine-tuning?

The target dataset must be absent from the training pool. Every transfer run must assert this exclusion, record the pool manifest, and use a shuffled-label control.

| Arm | Description | Purpose |
|---|---|---|
| `A_raw(T)` | Raw TabPFN evaluated on held-out target `T` | Target baseline |
| `C_pooled_all(T)` | Fine-tune on all other eligible datasets | Heterogeneous-pool test |
| `D_pooled_schema(T)` | Fine-tune on a coherent same-schema pool | Recommended first transfer test |
| `R_random(T)` | Same pooled training with shuffled source labels | Control for spurious pooling effects |

The primary transfer pool is the coherent same-schema pool because it reduces schema harmonisation as a confound. The heterogeneous pool is confirmatory and should be interpreted only after the coherent result. The transfer gain must be reported both against `A_raw(T)` and as a fraction of the corresponding in-domain gain, so a small absolute effect is not mistaken for a general transfer result.

**Transfer pre-registration, before any pooled run:**

1. Name the primary target `T` and record its held-out test fingerprint.
2. Freeze the schema-matching rule and the source-pool manifest.
3. Assert that no row, split, or derived context from `T` enters the pool.
4. Freeze the `T_RANDOM_LABELS` (`R_random(T)`) control and the matched in-domain comparison.
5. Declare the primary metric, calibration tolerance, and minimum practical effect before inspecting transfer results.

A transfer result is positive only if the coherent-pool arm beats `T_RAW` with the pre-registered interval rule and beats `T_RANDOM_LABELS`. A positive heterogeneous-pool result cannot rescue a negative coherent-pool result.

The prior transfer design and leakage rules are preserved in `docs/reference/PILOT_2_DESIGN.md` §6 and `docs/archive/SMOKE_TEST_SCOPE.md`. No transfer claim is made from the in-domain probe.

### Cross-cutting data-treatment ablation — synthetic data and augmentation

This is not a Phase 3 transfer arm. It belongs to the diagnostic/data-treatment workstream and, if justified, runs as one controlled follow-up to Phase 2.

Synthetic data is a separate data-treatment question, not another name for domain adaptation or evidence about the model's pretraining prior. Existing evidence says broad augmentation harmed performance, so the default is not to add synthetic rows. If diagnostics justify a rerun, use one dataset and one controlled treatment, compare against the real-data fine-tuned control, and report whether the result changes ranking, calibration, or both.

---

## 4. Decision framework

These are interpretation rules, not funding gates.

| Result | Interpretation |
|---|---|
| 10K gain does not reproduce on additional seeds | Treat Probe 2 as unstable or split-specific |
| Gain repeats on `uslapseagent` but not other datasets | Treat the effect as dataset-specific |
| Gain repeats across datasets | Fine-tuning has credible in-domain value |
| Gain disappears after preprocessing or feature treatment | The main lever is data preparation, not model adaptation |
| Gain is mainly calibration | Consider fine-tuning for probability use cases, not ranking claims |
| Gain is mainly ranking | Treat probability deployment as unresolved |
| In-domain gain is positive, coherent-pool transfer is positive | Insurance-domain adaptation has evidence of transfer; test the heterogeneous pool as confirmation |
| In-domain gain is positive, transfer is negative under the coherent pool | Report in-domain adaptation as the limit; do not claim general transfer |
| Synthetic augmentation remains negative | Do not use it in the deployment path; record the negative result |
| No gain remains after diagnostics and replication | Stop or narrow the fine-tuning line |

No single metric, seed, or dataset is allowed to determine the conclusion by itself.

---

## 5. Expected outputs

The pilot will produce:

1. a dataset diagnostic report;
2. a preprocessing and feature-engineering comparison;
3. a row-count × dataset × epoch experiment matrix;
4. raw-versus-full-SFT paired results;
5. calibration and ranking results for each arm;
6. seed-to-run variation;
7. comparison with GLM and tree baselines;
8. a recommendation by use case: lapse probability, risk ranking, underwriting triage, or other insurance decisions;
9. a controlled synthetic-data/augmentation result or an explicit decision not to rerun it;
10. if released, a leakage-audited transfer result with coherent and heterogeneous pool comparisons;
11. a clear statement of what remains untested, especially temporal validation and any unrun transfer extension.

---

## 6. Boundaries

This pilot does not:

- claim that a random split is equivalent to a temporal split;
- treat one seed as proof of generalisation;
- infer that a 10K result automatically applies to 50K rows;
- claim that fine-tuning is superior where a simple GLM already captures the signal;
- treat Phase 3 transfer results as available before the in-domain gate is passed;
- treat a pooled result as valid without target-exclusion and shuffled-label controls;
- include the full 15-dataset sweep, regression/count/severity extensions, or synthetic-data scale-up;
- replace the diagnostics with a single fine-tuning score.

No lapse dataset currently provides a usable time index, so all results remain conditional on the available random-split protocol.

---

## 7. Relationship to the existing documents

| Document | Role |
|---|---|
| `docs/current/FINETUNING_FINDINGS.md` | Current claims and their evidence status |
| `docs/current/FINETUNING_STATUS_BRIEF.md` | Stakeholder-facing summary of the two probes |
| `docs/current/FINETUNING_DIAGNOSTICS_DESIGN.md` | Phase 1 diagnostic work |
| `docs/current/FINETUNING_EXPERIMENT_REFERENCE.md` | Technical experiment design and caveats |
| `docs/current/FINETUNING_COST_AND_CONTROLS.md` | Measured cost accounting |
| `docs/current/FINETUNING_STATISTICAL_ANALYSIS_PLAN.md` | Statistical analysis rules |
| `docs/current/FINETUNING_DECISION_LOG.md` | Decisions and owners |
| `docs/reference/PILOT_2_DESIGN.md` | Historical transfer and pooling design; Phase 3 technical reference |
| `docs/archive/SMOKE_TEST_SCOPE.md` | Evidence that the C/D transfer arms were not run |
| `docs/archive/PRE_FINETUNING_INVESTIGATIONS.md` | Earlier questions covering transfer, pooling, small-n, and synthetic data |
| `notebooks/baseline_experiments/06_synthetic_data_exploration.ipynb` | Existing synthetic-data and augmentation evidence |

This document is the full current programme design. It supersedes the narrower “replicate one seed first” framing in earlier proposal text, while retaining that replication as the first robustness step and transfer/pooling as a conditional later phase.
