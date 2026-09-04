# Stage A and Stage B Findings: Short Report
> Tested: Apr 2026 · TabPFN v2.6 (`tabpfn>=7` / client 0.2.8). Do not assume results hold on v3 — see [../MODEL_VERSIONS.md](../MODEL_VERSIONS.md).


Date: 2026-04-02

## Scope Completed

Modeling mode for this report: binary classification (not regression).

1. Stage A completed: pilot feasibility and logging validation.
2. Stage B completed: all 4 insurance target datasets at seed 42 with core comparison arms.
3. Model arms executed in the Stage B matrix:
   - Raw TabPFNClassifier
   - Domain-finetuned TabPFNClassifier
   - Logistic regression (GLM)
   - Random forest
   - CatBoost rows logged as unavailable in this environment

Primary evidence sources:
- outputs/current/tables/domain_finetune_study_runs.csv
- outputs/current/logs/domain_finetune_logbook.md

Regressor extension evidence sources (separate from Stage A/B classifier matrix):
- outputs/current/tables/tabpfn_finetune_regressor_trial_results.csv
- outputs/current/logs/tabpfn_finetune_regressor_logbook.md

## Key Findings

### 1. Feasibility and pipeline integrity (Stage A objective)

- The end-to-end protocol is operational: data splits, model fitting, metric logging, and markdown logbook updates are working.
- The run table and logbook now provide a reproducible audit trail for all pilot and scale-up runs.

### 2. Domain-finetuned vs raw TabPFN (aggregate behavior)

Across the tested seed-42 configurations, domain fine-tuning did not produce aggregate improvement over raw TabPFN on primary endpoints.

Macro deltas (domain-finetuned minus raw):

- Context 64, steps 1: ROC AUC -0.0528, PR AUC -0.0225, Brier +0.0008, LogLoss +0.0066
- Context 64, steps 3: ROC AUC -0.0741, PR AUC -0.0314, Brier +0.0016, LogLoss +0.0102
- Context 64, steps 5: ROC AUC -0.0737, PR AUC -0.0312, Brier +0.0016, LogLoss +0.0107
- Context 128, steps 5: ROC AUC -0.0586, PR AUC -0.0259, Brier +0.0009, LogLoss +0.0064

Interpretation:
- Increasing fine-tune steps and then context improved some targets, but did not reverse the aggregate sign on primary metrics.

### 3. Dataset-level heterogeneity

- freMTPL2freq_binary: domain-finetuned TabPFN is strongest in the latest setting (best Brier, LogLoss, ROC, PR).
- coil2000 and ausprivauto0405: raw TabPFN remains strongest on core calibration/discrimination metrics.
- eudirectlapse: logistic regression is strongest in the latest setting.

Interpretation:
- A single global "fine-tune always" policy is not supported by current evidence.
- Best-performing model family appears dataset-dependent.
- A likely driver is cross-dataset domain mismatch; pooled fine-tuning is expected to work better when source and target datasets are more homogeneous.

## Recommendations for Proceeding

1. Move to Stage C (stability) before any deployment conclusion.
   - Repeat full Stage B matrix on seeds 1337 and 2025.
   - Produce paired bootstrap CIs for raw vs domain-finetuned deltas on Brier and LogLoss.

2. Use conditional model selection as the interim operating policy.
   - Keep raw TabPFN as default baseline.
   - Allow domain-finetuned TabPFN where validation favors it (currently freMTPL2freq_binary-like behavior).
   - Keep GLM candidate active for datasets with strong linear signal (eudirectlapse-like behavior).

3. Run Stage D ablations focused on calibration-first outcomes.
   - Fine-tune pool composition variants: all-other vs closest-domain-only.
   - Add validation-only calibration (isotonic/Platt) for raw and domain-finetuned arms.
   - Preserve fixed splits and equal tuning budgets for fairness.

4. Environment and reporting hygiene.
   - Either install CatBoost for complete tree-family comparability or formally lock tree baseline to RandomForest-only.
   - Keep using the existing CSV plus logbook as canonical records.

5. Add a homogeneous-dataset gate before domain fine-tuning.
   - Build a "homogeneous pool" option that includes only source datasets similar to the target.
   - Use lightweight similarity checks already aligned with this project: feature/schema overlap, event-rate proximity, and validation transfer performance from source to target.
   - Compare three policies under identical splits and budgets:
     - no fine-tune (raw TabPFN),
     - all-other pooled fine-tune,
     - homogeneous-only pooled fine-tune.
   - Promote fine-tuning only when homogeneous-only pool improves primary endpoints (Brier, LogLoss) versus raw with consistent direction across seeds.

## Bottom Line

Stage A and Stage B are complete, the experimentation framework is reliable, and current evidence does not yet support replacing raw TabPFN with domain-finetuned TabPFN as a universal default. The recommended next step is Stage C with multi-seed uncertainty estimates, followed by targeted Stage D ablations.

## Regressor Track Note (Current Status)

- Stage A/B conclusions above remain classification-only and unchanged.
- Regressor testing is now integrated into project logging standards (CSV + markdown logbook per run).
- Regressor methodology now includes explicit viability counters (`finetune_steps_executed` and skip counters) in addition to MSE/MAE/R2.
- Current pilot pattern to monitor in next runs: claim-target transforms can show non-finite-loss behavior while continuous-control targets execute finite steps.

**Stage R1 Completion (2026-04-02): Continuous Target Stability Matrix**
- Completed 3×2 multi-seed matrix (seeds 42, 1337, 2025 × contexts 64, 256) on Exposure (continuous target).
- All 9 runs executed fine-tuning steps (1 step per run) with zero non-finite losses.
- Key findings:
  - **MSE changes**: 6 of 9 runs improved (negative delta), 3 regressed slightly (positive delta <0.001)
  - **R² changes**: 5 of 9 runs improved, 4 regressed, all deltas <±0.004 (high stability)
  - **Timing robust**: context=64 runs ~25-35 sec, context=256 runs ~65-130 sec
  - **Consistency**: No seed-specific patterns; context size dominates runtime (~5x difference)
- Conclusion: TabPFN regressor fine-tuning is **operationally viable** on continuous targets with stable, small metric changes across seeds.

**Stage R2 Ablation Result (2026-04-02):**
- Hypothesis: Zero-inflation in claim-frequency targets is the primary cause of non-finite losses.
- Design: Restrict fine-tune training pool to ClaimNb > 0 rows only.
- Result: **Hypothesis REJECTED**
  - Baseline (all train rows, seed 1337): finetune_steps_executed=0, skipped_nonfinite_loss=14
  - Ablation (positive-claims-only pool, 167/3500 rows, seed 1337): finetune_steps_executed=0, skipped_nonfinite_loss=1
  - **Even with 95.2% data reduction (only positive-claim rows), non-finite loss persists and no steps execute.**
  - Exposure control (seed 2025): finetune_steps_executed=1, skipped_nonfinite_loss=0 ✓
- Conclusion: Root cause is **not zero-inflation**, but likely inherent numerical instability in TabPFN's regressor forward/loss function when applied to frequency-transformed targets. Alternative hypotheses:
  1. Target transform (log1p of claimfreq) produces numerically unstable standardization.
  2. Forward pass produces unbounded predictions for count-based targets.
  3. Loss function (normalized_bardist) has asymmetric behavior on sparse/heavy-tailed distributions.

Immediate regressor next steps:
- Stage R3: Test alternative target transforms (raw claimfreq without log, direct ClaimNb, Exposure as control).
- Stage R4: Investigate preprocessing target standardization and forward pass bounds.
- Decision gate: If alternatives also fail, consider whether TabPFN regressor is viable for insurance count targets pending upstream development.

## Reproducibility Note (How This Was Executed)

- Workspace: TabPFN-work-scott, with local upstream TabPFN source available at TabPFN-upstream.
- Key execution environment detail: use local upstream import path when running fine-tuning utilities.
   - `PYTHONPATH=/Users/Scott/Documents/Data Science/ADSWP/TabPFN-upstream/src`
- Runner implementation check: `scripts/legacy_finetuning/run_domain_finetune_stage_a.py` imports and uses `TabPFNClassifier` for both raw and fine-tuned TabPFN arms.
- `TabPFNRegressor` was not used in Stage A/B runs documented here.
- Core runner used for Stage A and Stage B style comparisons:
   - `python scripts/legacy_finetuning/run_domain_finetune_stage_a.py --target-dataset <dataset> --target-rows 2500 --pool-rows-per-dataset 1000 --tabpfn-device cpu --tabpfn-context-samples <64|128> --tabpfn-max-finetune-steps <1|3|5> --seed 42 --observations "..." --comments "..."`
- Datasets used:
   - `eudirectlapse`, `coil2000`, `ausprivauto0405`, `freMTPL2freq_binary`
- Fixed controls in reported runs:
   - seed `42`
   - same split discipline across model arms
   - same target/pool row budgets per run
- Canonical output artifacts:
   - run table: `outputs/current/tables/domain_finetune_study_runs.csv`
   - narrative logbook: `outputs/current/logs/domain_finetune_logbook.md`

For strict reproduction of the latest comparison snapshot referenced in this report, run all four datasets with `tabpfn_context_samples=128` and `tabpfn_max_finetune_steps=5` using the command shape above, then read the two artifact files listed.