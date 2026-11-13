# Analyses — result notes, specs and explainers

Working documents behind the repository's claims: a design spec written before an experiment, the result note that
follows it, and the explainers that make the metrics legible. **These are not the tiered reports** — those live in
[`../current/`](../current/), [`../reference/`](../reference/) and [`../archive/`](../archive/) and declare a status
marker. A document here earns its place by being working material rather than a citable report.

Ordered by what you are looking for, not alphabetically.

## Registries and indexes

| Document | What it holds |
| --- | --- |
| [`METRIC_REGISTRY.md`](METRIC_REGISTRY.md) | Metric registry |
| [`benchmark_portfolio.md`](benchmark_portfolio.md) | Benchmark Portfolio — Custom Insurance Benchmarks Index |

## The master report

| Document | What it holds |
| --- | --- |
| [`tabpfn_vs_gbdt_baselines_finetuning.md`](tabpfn_vs_gbdt_baselines_finetuning.md) | TabPFN vs GBDT Baselines on Insurance Datasets, and Domain Fine-Tuning Effectiveness |

## Design specs and plans

| Document | What it holds |
| --- | --- |
| [`insurance_frontier_benchmark_spec.md`](insurance_frontier_benchmark_spec.md) | Insurance Frontier Benchmark — Design Spec |
| [`frontier_auc_brier_rescore_spec.md`](frontier_auc_brier_rescore_spec.md) | Frontier AUC/Brier Re-score — Design Spec |
| [`altmetrics_rescore_spec.md`](altmetrics_rescore_spec.md) | Alternative-Metrics Re-score for Regression Benchmarks — Design Spec |
| [`prediction_capture_rescore_spec.md`](prediction_capture_rescore_spec.md) | Prediction Capture for Retrospective Re-scoring — Design Spec |
| [`tabpfn_finetune_limit_test_plan.md`](tabpfn_finetune_limit_test_plan.md) | TabPFN Fine-Tuning Limit Test Plan |
| [`freq_sev_power.md`](freq_sev_power.md) | Frequency/severity power — what the new targets can resolve, and what must be measured |

## Results and diagnostics

| Document | What it holds |
| --- | --- |
| [`finetuning_replication_result.md`](finetuning_replication_result.md) | Fine-tuning replication — +0.0035 AUC on `uslapseagent` at 30 epochs |
| [`finetuning_breadth_eudirectlapse_result.md`](finetuning_breadth_eudirectlapse_result.md) | Breadth result — fine-tuning does not generalise to `eudirectlapse` |
| [`finetuning_breadth_spanish_result.md`](finetuning_breadth_spanish_result.md) | Breadth result — fine-tuning adds nothing measurable on `spanish_motor_lapse` |
| [`freq_sev_fair_test_result.md`](freq_sev_fair_test_result.md) | Frequency/severity fair test — result |
| [`freq_sev_quantiles.md`](freq_sev_quantiles.md) | Frequency/severity fair test — what the quantiles say |
| [`anchor_power_diagnosis.md`](anchor_power_diagnosis.md) | Anchor power diagnosis — was the two-seed result underpowered or null? |
| [`d5_eudirectlapse_explanation.md`](d5_eudirectlapse_explanation.md) | D5 — why the linear method beats TabPFN on `eudirectlapse` |
| [`regressor_positive_control.md`](regressor_positive_control.md) | The regressor positive control: result |
| [`null_control_scoring_path.md`](null_control_scoring_path.md) | Null control — can the scoring path detect a known-null effect? |
| [`class_imbalance_analysis_summary.md`](class_imbalance_analysis_summary.md) | Class Imbalance Analysis: Effects on TabPFN and Baseline Model Performance |
| [`replication_sizing.md`](replication_sizing.md) | Replication sizing — what design could settle 0.002–0.006 AUC, and what it costs |
| [`regime_characterization.md`](regime_characterization.md) | Regime Characterization — When Default TabPFN Wins (Issue #53) |
| [`spanish_motor_lapse_stage2_readiness.md`](spanish_motor_lapse_stage2_readiness.md) | Is `spanish_motor_lapse` fit to carry Stage 2? |

## Method and explainers

| Document | What it holds |
| --- | --- |
| [`metrics_explained.md`](metrics_explained.md) | Metrics Explained — Log Loss vs AUC vs Brier |
| [`tabpfn_small_finetune_methodology.md`](tabpfn_small_finetune_methodology.md) | Small TabPFN Classifier Fine-Tuning Methodology |
| [`cpu_model_feasibility.md`](cpu_model_feasibility.md) | Model Feasibility — TabArena Methods We Can Access |
| [`levers_assessment.md`](levers_assessment.md) | TabPFN levers assessment — fine-tuning, HPO, ensembling (issue #54) |
| [`skill_sets_for_ds_research.md`](skill_sets_for_ds_research.md) | Skill Sets for Data-Science Research — RunCell vs. what is already installed |

## References

| Document | What it holds |
| --- | --- |
| [`tabular_foundation_models_catalog.md`](tabular_foundation_models_catalog.md) | Tabular Foundation Models — Catalog |
| [`tabarena_reference.md`](tabarena_reference.md) | TabArena Reference |
| [`tabarena_insurance_benchmark_direction.md`](tabarena_insurance_benchmark_direction.md) | TabArena — Insurance Benchmark Direction |

## Coordination records

| Document | What it holds |
| --- | --- |
| [`merge_plan_tabarena.md`](merge_plan_tabarena.md) | TabArena Benchmark Branch — Staged Merge Plan |
