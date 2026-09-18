# Methodology Protocol: Does Domain-Specific Fine-Tuning Improve Insurance Prediction?
> Tested: Apr 2026 · TabPFN v2 era (v2.0 via API; weights ID unrecorded). Do not assume results hold on v2.5/v3 — see [../MODEL_VERSIONS.md](../MODEL_VERSIONS.md).


Date: 2026-04-02

Scope note: this protocol covers both insurance classification and insurance regression tracks.
- Classification track uses `TabPFNClassifier` for raw and domain-finetuned TabPFN arms.
- Regression track uses `TabPFNRegressor` for raw and fine-tuned smoke/stability testing.

## 1. Research Question

Does domain-specific fine-tuning of TabPFN improve insurance prediction performance versus:
- raw (non-fine-tuned) TabPFN,
- tree-based baselines,
- GLM baselines,
on held-out insurance tasks?

## 2. Hypotheses

H1 (primary): Domain-fine-tuned TabPFN improves probability quality (Brier score, log loss, ECE) versus raw TabPFN on insurance datasets.

H2 (secondary): Domain-fine-tuned TabPFN improves ranking/discrimination (ROC AUC, PR AUC) versus raw TabPFN on insurance datasets.

H3 (comparative): Domain-fine-tuned TabPFN is competitive with or better than tuned tree and GLM baselines on at least one primary KPI per dataset.

## 3. Study Design

### 3.1 Datasets (Insurance Classification)

Use the existing insurance classification datasets already in project scope:
- EU Direct Lapse
- COIL 2000
- Aus. Vehicle
- freMTPL2 Binary

Optional extension set (if available) can be added after primary analysis is locked.

### 3.2 Domain Adaptation Split Logic

For each target dataset D_i:
- In-domain evaluation set: fixed train/validation/test split from D_i.
- Domain fine-tune pool: union of other insurance datasets D_j where j != i.
- Zero leakage rule: no row from D_i test appears in fine-tune pool or tuning.

This is leave-one-dataset-out domain adaptation and directly answers generalization to unseen insurance tasks.

### 3.3 Data Split and Randomness

- Fixed outer split seed: 42.
- Stratified splits for binary targets where valid.
- If class count makes stratification invalid, use deterministic unstratified fallback and log reason.
- Repeat with multiple seeds for stability (42, 1337, 2025) after pilot run.

## 4. Model Arms

### 4.1 TabPFN Arms

1. Raw TabPFN classifier (no additional training).
2. Domain-fine-tuned TabPFN classifier (trained on pooled insurance fine-tune pool, then evaluated on target test set).
3. Optional calibration variants for both arms:
   - isotonic calibration,
   - Platt scaling.

Calibration must be fit only on validation data, never on test.

### 4.2 Baselines

1. GLM arm:
   - LogisticRegression (with regularization tuned on validation).
2. Tree arms:
   - RandomForestClassifier,
   - CatBoostClassifier (or XGBoost if CatBoost unavailable),
   - LightGBM optional if environment permits.

All baselines use identical train/validation/test partitions as TabPFN arms.

## 5. Tuning Policy

To keep fairness and cost controlled:

- Use a bounded tuning budget per model family (same number of validation trials).
- Use predefined hyperparameter grids or low-cost Bayesian search with fixed trial counts.
- Freeze all tuning policy before final test evaluation.

Recommended initial budget:
- GLM: 8 to 12 trials.
- RandomForest: 12 to 20 trials.
- CatBoost: 20 to 30 trials.
- TabPFN fine-tune: staged steps (1, 3, 5) and context (64, 128), then lock best validation config.

## 6. Metrics and Endpoints

### 6.1 Primary Endpoints

- Brier score (lower is better)
- Log loss (lower is better)

Reason: current project evidence indicates calibration and prior mismatch are central.

### 6.2 Secondary Endpoints

- ROC AUC
- PR AUC
- ECE (Expected Calibration Error)
- Calibration slope/intercept

### 6.3 Operational Endpoints

- Wall-clock training time
- Peak memory (RSS)
- Inference latency per 1k rows

### 6.4 Regression Endpoints (Regressor Track)

- MSE (lower is better)
- MAE (lower is better)
- R2 (higher is better)
- Fine-tune-step viability indicators:
   - `finetune_steps_executed`
   - `skipped_preprocess_errors`
   - `skipped_nonfinite_target`
   - `skipped_nonfinite_loss`

Reason: current regressor pilot behavior shows non-finite loss/logit risk in some target regimes, so viability counters are required alongside predictive metrics.

## 7. Statistical Analysis

For each target dataset and each seed:
- Compute paired metric deltas between model arms on identical test rows.
- Use bootstrap confidence intervals (2000 resamples) for metric differences.
- Report 95% CI and whether CI excludes 0.

Across datasets:
- Report macro-average delta and weighted-average delta.
- Include win/loss counts by metric.
- Use hierarchical summary language (dataset-level first, pooled second).

## 8. Leakage and Validity Controls

- No test labels used in feature engineering, calibration fitting, or tuning.
- Preprocessing fit only on training partition, then applied to val/test.
- Domain fine-tune pool excludes target test set entirely.
- Log all data row counts before and after filtering.
- Record exact model/version/path (prefer local TabPFN-upstream source path).

## 9. Reproducibility Requirements

Store all outputs in the existing project structure:
- Trial table: outputs/current/tables/domain_finetune_study_runs.csv
- Aggregate summary: outputs/current/tables/domain_finetune_study_summary.csv
- Saved models: outputs/current/models/domain_finetune/
- Figure assets: outputs/current/plots/domain_finetune/

Regressor track artifacts:
- Trial table: outputs/current/tables/tabpfn_finetune_regressor_trial_results.csv
- Narrative logbook: outputs/current/logs/tabpfn_finetune_regressor_logbook.md
- Saved models: outputs/current/models/*tabpfn_finetune_regressor*.tabpfn_fit

Minimum logged fields per run:
- dataset, seed, model_family, model_variant,
- split_sizes, metric values, timing, max_rss,
- fine-tune config (device, context, steps),
- calibration method,
- model artifact path,
- git commit hash or run version tag.

## 10. Execution Plan (Staged)

Stage A (pilot feasibility):
- Run 1 dataset with 1 seed and minimal tuning budget.
- Confirm pipeline integrity and logging schema.

Stage B (core experiment):
- Run all 4 datasets with seed 42.
- Compare raw TabPFN, fine-tuned TabPFN, GLM, RandomForest, CatBoost.

Stage C (stability):
- Repeat Stage B on 2 additional seeds.
- Produce confidence intervals and pooled conclusions.

Stage D (ablation):
- Fine-tune pool composition ablation:
  - all-other-insurance datasets,
  - closest-domain-only subset,
  - no fine-tune (raw baseline).

Stage R1 (regressor smoke/stability):
- Run regressor smoke matrix with fixed feature encoding and deterministic seeds.
- Required seeds: 42, 1337, 2025.
- Required target variants:
   - Claim count target (`ClaimNb`),
   - transformed frequency targets (`claimfreq_raw`, `claimfreq_log1p`),
   - continuous-control target (`Exposure`) for pipeline-health comparison.
- Record both metric outcomes and viability counters.

Stage R2 (regressor hardening/ablation):
- Completed 2026-04-02: **Positive-claims-only fine-tune pool ablation test**.
  - Objective: Test hypothesis that zero-inflation in ClaimNb causes non-finite losses.
  - Design: Restrict fine-tune training pool to ClaimNb > 0 rows only; evaluate on full held-out test set.
  - Configuration: seed 1337, target ClaimNb, claimfreq_log1p, rows=5000, context=256, steps=1.
  - Result: **Hypothesis REJECTED** — even with 95.2% training pool reduction (3500→167 rows), finetune_steps_executed remained 0 with non-finite loss. Zero-inflation is not the primary blocker.
  - Exposure control (seed 2025): finetune_steps_executed=1, confirming script/framework are operational on viable targets.
- Next ablation (Stage R3):
  - Test alternative target transforms on claim data to isolate the numerical instability source:
    1. Raw `ClaimNb` without transforms.
    2. Raw `claimfreq` (without log1p).
    3. Alternate context sizes (64 vs 256).
  - Maintain identical split seed and evaluation discipline.
   - Readiness gate before calling a configuration “ready” for Stage R3 reruns: evaluate a small seed panel using the latest logged rows for the exact config and require `finetune_steps_executed >= 1` for every seed, finite `last_step_loss` values for every seed, `abs(last_step_loss) <= 1e6` for every seed, and cross-seed `last_step_loss` range `<= 100`.
   - Default claim-target seed panel: `42`, `1337`, `2025`.
   - Command shape: `python scripts/legacy_finetuning/evaluate_regressor_stability_gate.py --target-col ClaimNb --target-transform none --rows 5000 --context-samples 64 --device cpu --seeds 42 1337 2025 --strict-exit`
   - Decision gate: if the stability gate fails, do not call the config ready for Stage R3 reruns. If all claim-frequency variants remain blocked (`steps_executed=0`) or fail the stability gate, regressor fine-tuning is not yet viable for insurance count targets and further engineering is required.

## 11. Decision Rules

Conclude domain-specific fine-tuning is supported only if:

1. Fine-tuned TabPFN shows statistically reliable improvement versus raw TabPFN on primary metrics (Brier/log loss) on a majority of datasets.
2. Gains are not offset by severe degradation in discrimination (ROC/PR) or unacceptable operational cost.
3. Results remain directionally consistent across seeds.

If not satisfied, report that calibration-only or mixed-model selection remains the preferred strategy.

## 12. Reporting Template

Report in this exact order:
1. What was run (datasets, split policy, seeds, model arms, fine-tune config)
2. Per-dataset performance table
3. Aggregate performance table
4. Statistical significance summary (paired deltas + CI)
5. Operational cost table (time/memory/latency)
6. Final recommendation with deployment guidance

Regressor addendum format:
1. What was run (target transform, rows, device, context, steps, seed)
2. Viability table (`finetune_steps_executed`, skip counters)
3. Regression metric table (MSE/MAE/R2)
4. Stability-gate result (seed panel, thresholds, pass/fail, loss range)
5. Decision (ready to scale or blocked)
6. One next ablation

## 13. Minimal Command Shape (Project-Consistent)

Use the existing harness style and logging conventions already established in this repository.

- Pilot run first with small fine-tune settings.
- Lock configuration from validation.
- Execute full matrix.
- Save all artifacts and append summary tables.

This protocol intentionally builds on existing evidence artifacts, while correcting the main current gap: lack of controlled before/after domain fine-tune comparisons against external baselines.
