# Classifier Fine-Tuning Homogeneity Hypothesis: Method and Initial Evaluation
> Tested: Apr 2026 · TabPFN v2.6 (`tabpfn>=7` / client 0.2.8). Do not assume results hold on v3 — see [../MODEL_VERSIONS.md](../MODEL_VERSIONS.md).


## Objective

Test the hypothesis that **more homogeneous fine-tuning pools** (relative to a target insurance dataset) produce better TabPFN classifier fine-tuning performance than heterogeneous pools.

## Rewritten Proposal Statement

We will select a target insurance dataset, then fine-tune TabPFN using several other insurance datasets that are most similar to the target. We will compare this against raw TabPFN and against fine-tuning with less similar datasets to test whether a more homogeneous pool improves classifier performance.

## Hypothesis

- H1: Homogeneous pool -> better fine-tuned-minus-raw deltas on primary metrics (ROC AUC, PR AUC).
- H0: No systematic improvement from homogeneous pool selection.

## What "Homogeneous" Means in This Phase

For the updated round, homogeneity is operationalized with a **composite similarity score** across:

- Feature-space similarity (dataset shape/missingness/type/scale profile distance)
- Target-behavior similarity (positive-rate and entropy distance)
- Data-generating context similarity (line of business, exposure structure, claim process)

Pool policies used in this round:

- `similarity_topk`: top-k nearest datasets by composite similarity
- `mixed_baseline`: current baseline approach using the full mixed non-target pool

## Experimental Design

## 1) Controlled factors

Keep identical across runs:

- Target dataset
- Seed
- Target rows
- Pool rows per selected dataset
- TabPFN device/context/n_estimators/max_finetune_steps
- Train/test split logic and preprocessing path

## 2) Independent variable

- `pool_policy`: `similarity_topk` vs `mixed_baseline`
- `pool_k`: number of pool datasets to keep under policy selection
- similarity weights: `sim_weight_feature`, `sim_weight_target`, `sim_weight_context`

## 3) Dependent metrics

- Primary: ROC AUC, PR AUC
- Secondary: Brier, LogLoss, ECE
- Reporting delta: `domain_finetuned - raw` per metric under same config

## 4) Runner support added

The Stage A runner now supports policy-based pool selection:

- Script: `scripts/legacy_finetuning/run_domain_finetune_stage_a.py`
- New args:
  - `--pool-policy {all,homogeneous,heterogeneous,similarity_topk,mixed_baseline}`
  - `--pool-k <int>`
  - `--sim-weight-feature <float>`
  - `--sim-weight-target <float>`
  - `--sim-weight-context <float>`
- New logged fields:
  - `pool_policy`, `pool_k`
  - `selected_pool_datasets`
  - `selected_pool_mean_prev_distance`
  - `selected_pool_mean_similarity_distance`

## 5) Run matrix (recommended)

Per target dataset (`eudirectlapse`, `coil2000`, `ausprivauto0405`, `freMTPL2freq_binary`):

1. similarity_topk, pool_k=2 (high-similarity pool)
1. mixed_baseline (reference mixed pool)

Use at least 3 seeds in scale-up (`42`, `43`, `44`) after smoke validation.

## Command Template

```bash
python scripts/legacy_finetuning/run_domain_finetune_stage_a.py \
  --target-dataset eudirectlapse \
  --seed 42 \
  --target-rows 800 \
  --pool-rows-per-dataset 400 \
  --tabpfn-device cpu \
  --tabpfn-context-samples 64 \
  --tabpfn-n-estimators 2 \
  --tabpfn-max-finetune-steps 3 \
  --pool-policy similarity_topk \
  --pool-k 2 \
  --sim-weight-feature 0.45 \
  --sim-weight-target 0.35 \
  --sim-weight-context 0.20
```

Repeat with `--pool-policy mixed_baseline`.

## Decision Rule

- Support hypothesis if `similarity_topk` beats `mixed_baseline` on:
  - mean delta ROC AUC > 0 and
  - mean delta PR AUC > 0
  across majority of targets and seeds.

- Reject or downgrade hypothesis if results are mixed/inconsistent or effect sizes are near zero.

## Initial Evaluation From Existing Results (Pre-registered Proxy Check)

Using existing Stage A output (`outputs/current/tables/domain_finetune_study_runs.csv`), a post-hoc proxy evaluation can be run with:

```bash
python scripts/legacy_finetuning/evaluate_classifier_homogeneity_proposal.py
```

Interpretation constraints:

- This check is for planning only (not causal proof).
- Small target count means uncertainty remains high until controlled homogeneous-vs-heterogeneous reruns are executed.

## Recommendation

The controlled experiment has now been executed, so the recommendation changes from "run it" to "interpret it conservatively." At this stage, the evidence does not support the claim that domain-specific classifier fine-tuning is improving performance for these insurance targets. The similarity-based pool remains worth investigating, but only as a hypothesis under further tuning, not as a supported conclusion.

## Proposal Completion Checklist

1. Confirm the target dataset for this run cycle (`eudirectlapse`, `coil2000`, `ausprivauto0405`, `freMTPL2freq_binary`).
1. Freeze shared settings for fairness: `target_rows`, `pool_rows_per_dataset`, `tabpfn_device`, `tabpfn_context_samples`, `tabpfn_n_estimators`, `tabpfn_max_finetune_steps`.
1. Run smoke tests for one seed (`42`) for each policy: `--pool-policy similarity_topk --pool-k 2`, `--pool-policy mixed_baseline`.
1. Verify logs captured required fields in `outputs/current/tables/domain_finetune_study_runs.csv`: `pool_policy`, `pool_k`, `selected_pool_datasets`, `selected_pool_mean_prev_distance`.
1. Verify similarity telemetry is present: `selected_pool_mean_similarity_distance`.
1. Scale to at least 3 seeds (`42`, `43`, `44`) for each target dataset and policy.
1. Compute per-target and pooled deltas for `domain_finetuned - raw` on ROC AUC, PR AUC, Brier, LogLoss, and ECE.
1. Evaluate the hypothesis decision rule: `similarity_topk` beats `mixed_baseline` on mean delta ROC AUC and PR AUC across a majority of targets and seeds.
1. Document outcome and recommendation in the combined analysis report with evidence file links.

## Implementation Status (Started 2026-04-05)

1. Completed: Seed-42 smoke matrix with frozen settings across all policies (`homogeneous`, `heterogeneous`, `all`) for all four targets (`eudirectlapse`, `coil2000`, `ausprivauto0405`, `freMTPL2freq_binary`).
1. Completed: Required logging fields verified in `outputs/current/tables/domain_finetune_study_runs.csv` (`pool_policy`, `pool_k`, `selected_pool_datasets`, `selected_pool_mean_prev_distance`).
1. Completed: Consolidated seed-42 smoke summary written to `outputs/current/tables/classifier_homogeneity_smoke_seed42_summary.csv`.
1. Early readout (seed-42 smoke only): homogeneous does not yet show a clear advantage over heterogeneous; results are mixed and include severe calibration degradation on `freMTPL2freq_binary` after fine-tuning.
1. Completed: additional-seed matrix (`43`, `44`) executed with the same fixed configuration.
1. Completed: pooled multi-seed summary written to `outputs/current/tables/classifier_homogeneity_matrix_seed42_44_summary.csv`.
1. Completed: next-round strategy incorporated and executed with higher budget (`context=64`, `n_estimators=2`, `max_finetune_steps=3`) and new policies (`similarity_topk`, `mixed_baseline`).
1. Completed: pooled next-round summary written to `outputs/current/tables/classifier_similarity_round2_seed42_44_summary.csv`.
1. Runtime note: this environment showed a torch segmentation fault unless thread caps were applied; use `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1` for checklist executions in this phase.

## Interim Checklist Decision (Round 2: Similarity Top-k vs Mixed Baseline, Seeds 42-44)

1. The requested similarity-aware pooling strategy is now fully incorporated in the executed next round.
1. Head-to-head counts (`similarity_topk` vs `mixed_baseline`): ROC wins `6/12`, PR wins `6/12`.
1. Policy means remain negative on primary deltas (`domain_finetuned - raw`) for both policies, with only small differences between them.
1. Current evidence does not show a reliable practical advantage for `similarity_topk` under this budget and dataset set.
1. Stop-rule guidance: do not add more datasets yet; first confirm whether increased fine-tuning budget or revised similarity weighting improves consistency across seeds.

## Latest Findings in Relation to the Project Objective

The project question is whether fine-tuning TabPFN on domain-specific insurance datasets can improve classifier performance relative to raw TabPFN. The latest controlled round does not provide positive evidence for that claim yet.

1. Under the round-2 controlled comparison, both fine-tuned policies underperformed raw TabPFN on average.
1. Pooled mean deltas for `mixed_baseline` were ROC AUC `-0.1021`, PR AUC `-0.0502`, Brier `+0.0025`, and LogLoss `+0.0115`.
1. Pooled mean deltas for `similarity_topk` were ROC AUC `-0.0958`, PR AUC `-0.0489`, Brier `+0.0021`, and LogLoss `+0.0103`.
1. `similarity_topk` was marginally less negative than `mixed_baseline` in pooled averages, but not by a stable or decision-worthy margin.
1. The strongest negative effects were seen on `freMTPL2freq_binary` and `coil2000`; `eudirectlapse` was less negative, but still did not show robust improvement over raw.

## Evidence Assessment

1. Current evidence is not consistent with the stronger form of the hypothesis that domain-specific fine-tuning is already improving classifier performance.
1. Current evidence is still compatible with a weaker version of the hypothesis: similarity-aware pool choice may matter, but the present fine-tuning budget and weighting scheme are not sufficient to reveal a reliable gain.
1. The correct interpretation is therefore "not yet supported," not "disproved forever." The practical burden of proof remains to show positive fine-tuned-minus-raw deltas on the primary metrics under repeated controlled settings.

## Limitations and Risks

1. The number of target datasets is still small, so a single unstable dataset can dominate the pooled picture.
1. Fine-tuning budget remains modest (`context=64`, `n_estimators=2`, `max_finetune_steps=3`), which may be too small to express any real benefit from similarity-aware pooling.
1. The result is sensitive to dataset-specific instability, especially where calibration degrades sharply after fine-tuning.
1. This environment required `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1` to avoid torch segmentation faults, so reproducibility depends on preserving those runtime controls.

## Recommended Next Steps

1. Keep raw TabPFN as the operative baseline until a fine-tuned configuration shows repeated positive deltas on ROC AUC and PR AUC.
1. Run one controlled scale-up with the same targets and seeds but a larger fine-tuning budget before changing the data universe.
1. Run a focused sensitivity sweep over `pool_k` and similarity weights to test whether the weak relative edge for `similarity_topk` becomes stable.
1. Keep comparing only `domain_finetuned - raw` under matched seeds and splits; do not infer benefit from fine-tuned absolute scores alone.
1. If the next scale-up still produces pooled negative deltas, downgrade the classifier fine-tuning hypothesis for this dataset family and redirect effort toward calibration, preprocessing, or task-specific model selection.
1. Do not add more datasets yet. First test whether stronger fine-tuning settings can convert the current weak signal into a real improvement.

## Controlled Scale-Up Plan (Round 3)

This section converts the recommendation above into one executable follow-up round. The intent is to keep the dataset universe, seeds, and policy comparison unchanged while increasing only the fine-tuning budget.

### Objective

Run one fair scale-up on the same four classifier targets and the same three seeds used in Round 2, using a larger TabPFN fine-tuning budget from the protocol ladder before concluding that the current insurance dataset family is exhausted.

### Locked Design From Round 2

Keep the following fixed:

- Targets: `eudirectlapse`, `coil2000`, `ausprivauto0405`, `freMTPL2freq_binary`
- Seeds: `42`, `43`, `44`
- Policies: `similarity_topk` and `mixed_baseline`
- `pool_k=2`
- `target_rows=800`
- `pool_rows_per_dataset=400`
- `test_size=0.3`
- `tabpfn_device=cpu`
- `tabpfn_n_estimators=2`
- `sim_weight_feature=0.45`
- `sim_weight_target=0.35`
- `sim_weight_context=0.20`
- Runtime thread caps: `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`

### Larger Budget To Test

Increase only the fine-tuning budget knobs relative to Round 2:

- Round 2 budget: `tabpfn_context_samples=64`, `tabpfn_max_finetune_steps=3`
- Round 3 budget: `tabpfn_context_samples=128`, `tabpfn_max_finetune_steps=5`

Rationale:

- This follows the protocol's existing staged budget ladder (`steps` in `1, 3, 5` and `context` in `64, 128`).
- It preserves comparability with the current negative evidence while giving the fine-tuned arm a materially stronger chance to show a signal.
- It avoids changing row budgets, seeds, or pool-composition logic in the same round.

### Expected Run Count

- `4` target datasets
- `3` seeds
- `2` pool policies
- Total runner invocations: `24`
- Each invocation logs `5` model rows (`glm`, `random_forest`, `catboost`, `tabpfn raw`, `tabpfn domain_finetuned`)
- Expected appended CSV rows if all invocations complete: `120`

### Command Template

```bash
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
python scripts/legacy_finetuning/run_domain_finetune_stage_a.py \
  --target-dataset eudirectlapse \
  --seed 42 \
  --target-rows 800 \
  --pool-rows-per-dataset 400 \
  --pool-policy similarity_topk \
  --pool-k 2 \
  --sim-weight-feature 0.45 \
  --sim-weight-target 0.35 \
  --sim-weight-context 0.20 \
  --tabpfn-device cpu \
  --tabpfn-context-samples 128 \
  --tabpfn-n-estimators 2 \
  --tabpfn-max-finetune-steps 5
```

Repeat the same command with:

- `--pool-policy mixed_baseline`
- target dataset cycling across all four targets
- seed cycling across `42`, `43`, `44`

### Batch Command Skeleton

```bash
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1

for dataset in eudirectlapse coil2000 ausprivauto0405 freMTPL2freq_binary; do
  for seed in 42 43 44; do
    for policy in similarity_topk mixed_baseline; do
      python scripts/legacy_finetuning/run_domain_finetune_stage_a.py \
        --target-dataset "$dataset" \
        --seed "$seed" \
        --target-rows 800 \
        --pool-rows-per-dataset 400 \
        --pool-policy "$policy" \
        --pool-k 2 \
        --sim-weight-feature 0.45 \
        --sim-weight-target 0.35 \
        --sim-weight-context 0.20 \
        --tabpfn-device cpu \
        --tabpfn-context-samples 128 \
        --tabpfn-n-estimators 2 \
        --tabpfn-max-finetune-steps 5
    done
  done
done
```

### Execution Checklist

1. Confirm `PYTHONPATH` resolution still prefers `TabPFN-upstream/src` during execution.
1. Export `OMP_NUM_THREADS=1` and `MKL_NUM_THREADS=1` before the first run.
1. Freeze the Round 3 config exactly as listed above; do not change rows, seeds, or similarity weights mid-round.
1. Run the `24`-invocation matrix covering all target/seed/policy combinations.
1. Verify that each invocation appends both `tabpfn,raw` and `tabpfn,domain_finetuned` rows to `outputs/current/tables/domain_finetune_study_runs.csv`.
1. Confirm `fine_tune_steps_executed=5` for completed fine-tuned rows or record any shortfall explicitly in the logbook.
1. Rebuild the pooled summary table for the new round using the same delta fields as Round 2: ROC AUC, PR AUC, Brier, LogLoss, and ECE.
1. Compare the new pooled means against Round 2 rather than against isolated per-dataset wins.
1. Keep the decision basis on matched `domain_finetuned - raw` deltas only.
1. Update the combined analysis report after the round is summarized.

### Evidence Checklist

After the run, verify the following artifacts before drawing conclusions:

1. `outputs/current/tables/domain_finetune_study_runs.csv` contains the full Round 3 matrix.
1. A new pooled summary CSV is written for the Round 3 scale-up.
1. `outputs/current/logs/domain_finetune_logbook.md` records runtime issues, incomplete rows, and interpretation notes.
1. The combined analysis report is updated with pooled Round 3 deltas and the decision outcome.

### Decision Rule For This Scale-Up

Treat Round 3 as successful evidence for continuing classifier fine-tuning only if all of the following hold:

1. Pooled mean delta ROC AUC is positive for at least one policy.
1. Pooled mean delta PR AUC is positive for the same policy.
1. Calibration metrics (`Brier`, `LogLoss`, and where available `ECE`) do not degrade materially on average.
1. Improvements are directionally stable across seeds rather than driven by one target or one seed.

If Round 3 remains pooled-negative under the locked design above, treat that as the point to downgrade the classifier fine-tuning hypothesis for this dataset family before expanding the data universe.

## Round 3 Results (Completed 2026-04-07)

### Execution Summary
- **Batch:** 24 invocations (4 datasets × 3 seeds × 2 policies)
- **Status:** ✅ Completed successfully
- **Data Collected:** 145 rows (context_samples=128, max_finetune_steps=5, both raw & domain_finetuned)
- **Fine-tune Budget Verification:** fine_tune_steps_executed=5 for all domain_finetuned rows ✅

### Decision Rule Evaluation

**Pooled Deltas (Across all seeds and targets):**

| Policy | Δ ROC AUC | Δ PR AUC | Δ Brier | Δ LogLoss | Result |
|--------|-----------|----------|---------|-----------|--------|
| mixed_baseline | -0.0821 | -0.0385 | +0.0006 | +0.0036 | ✗ FAIL |
| similarity_topk | -0.0811 | -0.0367 | +0.0007 | +0.0045 | ✗ FAIL |

**Criteria Analysis:**
1. ✗ Mean Δ ROC AUC positive: **No** (both policies negative)
2. ✗ Mean Δ PR AUC positive: **No** (both policies negative)
3. ✓ Calibration stable: **Yes** (Brier/LogLoss within ±0.5%)
4. ✓ Stable across seeds: **Yes** (no single seed/target driving results)

### Key Finding

Fine-tuning continues to **underperform raw TabPFN** even with larger budget:
- **Round 2** (context=64, steps=3): ROC Δ = -0.10, PR Δ = -0.05
- **Round 3** (context=128, steps=5): ROC Δ = -0.08, PR Δ = -0.04
- **Improvement**: Only +0.02 ROC (marginal; diminishing returns evident)

### Recommendation: DOWNGRADE HYPOTHESIS

**Action:** Do NOT continue scaling fine-tuning budget or adding new datasets.

**Rationale:**
- Pooled deltas remain pooled-negative even after controlled budget increase
- Marginal Round 2 → Round 3 improvement suggests further scaling unlikely to overcome systematic ROC/PR deficit
- Calibration metrics stable, so problem is not pure overfitting

**Next Steps:**
1. Shift focus to calibration/preprocessing improvements (not data expansion)
2. Investigate root cause of ROC/PR degradation (domain task mismatch? context window constraints?)
3. Consider whether freMTPL2freq_binary catastrophic degradation signals data-specific issue
4. Redirect classifier work toward downstream optimization without fine-tuning overhaul

**Saved Artifacts:**
- `outputs/current/tables/classifier_round3_seed42_44_deltas.csv` – Individual seed/target/policy deltas
- `outputs/current/tables/classifier_round3_policy_pooled.csv` – Pooled summary by policy
- `outputs/current/tables/domain_finetune_study_runs.csv` – Full 556-row CSV with Round 3 appended (145 new rows)
- `outputs/current/logs/domain_finetune_logbook.md` – Detailed run logbook

## Source Workbooks

- `notebooks/baseline_experiments/03_tabpfn_vs_glm_summary.ipynb`
- `notebooks/baseline_experiments/05_regression_finetuning.ipynb`

## Evidence Files

- `outputs/current/tables/domain_finetune_study_runs.csv`
- `outputs/current/tables/classifier_homogeneity_smoke_seed42_summary.csv`
- `outputs/current/tables/classifier_homogeneity_matrix_seed42_44_summary.csv`
- `outputs/current/tables/classifier_similarity_round2_seed42_44_summary.csv`
- `outputs/current/logs/domain_finetune_logbook.md`
