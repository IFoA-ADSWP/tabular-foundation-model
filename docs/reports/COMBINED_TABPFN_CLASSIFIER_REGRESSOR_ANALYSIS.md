# Combined Analysis: TabPFN Classifier and Regressor vs Existing Models
> Tested: Apr 2026 · TabPFN v2 era (v2.0 via API; weights ID unrecorded). Do not assume results hold on v2.5/v3 — see [../MODEL_VERSIONS.md](../MODEL_VERSIONS.md).


## Objective
Provide one consolidated view of findings from:
1. Classification benchmarking (TabPFN vs GLM)
2. Regression benchmarking (classical baselines on expanded datasets, plus prior TabPFN regression evidence)

This report distinguishes between:
- **Current reproducible artifacts on disk**
- **Prior TabPFN regression observations captured earlier in the workflow**

## Research Question Answer

**Research question:** Does fine-tuning TabPFN on insurance data yield a better-performing model on insurance data?

**Answer from current evidence:** **Not consistently.** Under the tested setup in this repository, fine-tuning did not improve TabPFN performance overall across insurance classification and regression tasks.

### Evidence-based interpretation
- **Classifier track:** Domain fine-tuning produced mixed outcomes with net degradation across most datasets/metrics, while one dataset (freMTPL2 binary) showed improvement.
- **Regressor track:** One-step fine-tuned TabPFN did not deliver a material lift over raw TabPFN and remained unstable for key settings (for example ClaimNb loss-scale behavior and zero-step cases).
- **Cross-task conclusion:** Fine-tuning benefit is currently **dataset-specific**, not a robust general improvement across the insurance portfolio.

### Decision-level statement
For this project phase, the research question can be answered as: **fine-tuning has not yet demonstrated reliable overall performance gains on insurance data**. It should remain an experimental path until stability-gated, multi-seed runs show consistent gains on primary metrics.

## Experimental Setup (What Was Run in This Phase)

This report summarizes completed experiments and generated artifacts for the current phase only.

### Classification track
- Head-to-head TabPFN vs GLM analysis from existing processed artifact.
- Datasets: EU Direct Lapse, COIL 2000, Aus. Vehicle, freMTPL2 Binary.
- Metrics emphasized: ROC AUC and PR AUC.

### Regression baseline track
- Classical baseline benchmark across three datasets.
- Models: LinearRegression, RandomForestRegressor, CatBoostRegressor.
- Metrics: MAE, RMSE, R2.

### TabPFN regressor revalidation track
- Raw TabPFN regressor rerun in current environment.
- CPU settings used for feasibility: 300 train rows, 2000 test rows, n_estimators=4, seed=42.

### Fine-tuned regressor pilot track
- One-step fine-tuned TabPFN regressor benchmark vs raw TabPFN and classical baselines.
- Pilot settings: CPU, context=64, max_finetune_steps=1, seed=42.
- Viability counters tracked: finetune_steps_executed, skipped_nonfinite_loss, and related stability signals.

---

## Data Sources

### Current artifacts (reproducible now)
- `data/processed/glm_vs_tabpfn_head_to_head.csv`
- `data/processed/multi_dataset_regression_benchmark_results.csv`
- `outputs/current/tables/raw_tabpfn_regression_revalidation.csv` (TabPFN regressor, 2026-04-05)
- `outputs/current/tables/multi_dataset_regression_benchmark_with_tabpfn_revalidated.csv` (combined)
- `outputs/current/tables/tabpfn_regression_finetune_vs_raw.csv` (raw vs fine-tuned TabPFN regressor, 2026-04-05)
- `outputs/current/tables/multi_dataset_regression_benchmark_with_tabpfn_finetuned.csv` (baseline + raw TabPFN + fine-tuned TabPFN)

---

## 1) Classification Findings (TabPFN vs GLM)

Datasets evaluated:
- EU Direct Lapse
- COIL 2000 (NL)
- Aus. Vehicle (AU)
- freMTPL2 Binary (FR)

### Head-to-head summary
- **ROC AUC wins (TabPFN over GLM): 3/4 datasets**
- **PR AUC wins (TabPFN over GLM): 2/4 datasets**

### Per-dataset deltas (TabPFN - GLM)
- **EU Direct Lapse:** ROC -0.0080, PR +0.0031
- **COIL 2000:** ROC +0.0222, PR -0.0047
- **Aus. Vehicle:** ROC +0.0004, PR -0.0004
- **freMTPL2 Binary:** ROC +0.0151, PR +0.0078

### Interpretation
- TabPFN is generally stronger on ranking quality (ROC) across these binary tasks.
- PR behavior is mixed, indicating sensitivity to class imbalance and score calibration by dataset.
- The strongest overall classification lift appears on freMTPL2 Binary (both ROC and PR improved).

---

## 2) Regression Findings (Current 3-dataset baseline run)

Datasets currently executed in the latest artifact:
- freMTPL2 Frequency (FR), target ClaimNb
- EU Direct Premium (pure), target prem_pure
- AUS Auto Vehicle Value, target VehValue

Models in latest artifact:
- LinearRegression
- RandomForestRegressor
- CatBoostRegressor

### Best model by dataset (current artifact)
- **freMTPL2 Frequency:** CatBoost (best MAE, RMSE, R2)
- **EU Direct Premium:** RandomForest (best MAE, RMSE, R2)
- **AUS Auto Vehicle Value:** CatBoost (best MAE, RMSE, R2)

### Interpretation
- For noisy/count-like targets, boosted trees (CatBoost) are strongest among classical baselines.
- For premium prediction with already high explainability, RandomForest slightly edges other baselines.
- For nonlinear continuous value prediction (vehicle value), CatBoost shows clear superiority.

---

## 3) Revalidated TabPFN Regressor Results (3 datasets, current environment)

**Run date:** 2026-04-05 | **Artifact:** `outputs/current/tables/raw_tabpfn_regression_revalidation.csv`

**Run settings:** TabPFN upstream src, device=CPU, seed=42, n_estimators=4, ignore_pretraining_limits=True.
**Important caveat:** CPU inference speed required capping to 300 train rows and 2000 test rows for TabPFN.
Classical baselines used up to 10,000 training rows. Comparison is directional, not fully equivalent.

### freMTPL2 Frequency (FR) — Target: ClaimNb

| Model | Train N | MAE | RMSE | R2 |
|---|---|---|---|---|
| LinearRegression | 10K | 0.0996 | 0.2352 | 0.026 |
| RandomForestRegressor | 10K | 0.0830 | 0.2216 | 0.135 |
| CatBoostRegressor | 10K | 0.0763 | 0.2169 | **0.172** |
| TabPFNRegressor | 300 | **0.0586** | 0.2545 | -0.051 |

TabPFN achieves best MAE despite 33x fewer training rows, but negative R2 indicates poor variance capture — consistent with the zero-inflated ClaimNb distribution.

### EU Direct Premium (pure) — Target: prem_pure

| Model | Train N | MAE | RMSE | R2 |
|---|---|---|---|---|
| LinearRegression | 10K | 13.70 | 21.99 | 0.987 |
| RandomForestRegressor | 10K | **12.28** | **19.79** | **0.990** |
| CatBoostRegressor | 10K | 12.63 | 23.92 | 0.985 |
| TabPFNRegressor | 300 | 12.85 | 24.82 | 0.984 |

TabPFN with only 300 training rows reaches R2=0.984, which is close to the classical models in this pilot comparison. This is a strong signal for TabPFN's data efficiency on insurance premium regression, while uncertainty remains due to limited seed coverage.

### AUS Auto Vehicle Value — Target: VehValue

| Model | Train N | MAE | RMSE | R2 |
|---|---|---|---|---|
| LinearRegression | 10K | 0.719 | 1.079 | 0.233 |
| RandomForestRegressor | 10K | 0.485 | 0.836 | 0.539 |
| CatBoostRegressor | 10K | 0.432 | 0.750 | **0.629** |
| TabPFNRegressor | 300 | 0.446 | 0.801 | 0.582 |

TabPFN (300 rows) beats RF on MAE and achieves R2=0.582 vs CatBoost R2=0.629 — strong performance given the training-row disparity.

### Interpretation (revalidated)
- **Strongest TabPFN signal:** EU Direct Premium — near-equivalent to classical models using 33x fewer rows.
- **Competitive TabPFN performance:** AUS Auto — within 0.05 R2 of CatBoost; beats RF on MAE.
- **Weakest TabPFN performance:** freMTPL2 ClaimNb — MAE is best but R2 is negative due to zero-inflation; this target is a known challenge for in-context learners.
- Net pattern: TabPFN shows strong data efficiency for insurance-domain regression targets. The ClaimNb result suggests count/frequency targets may need specialized treatment (Poisson-like objectives or fine-tuning).

---

## 4) Combined Cross-Task Conclusions

1. **TabPFN is broadly competitive and often strong, but not universally dominant.**
2. **Classification:** Most robust gains appear in ROC across diverse datasets; PR gains are dataset-specific.
3. **Regression (raw revalidated):** TabPFN shows strong data efficiency on EU Direct and AUS Auto with 300 train rows.
4. **Regression (fine-tuned, 1-step pilot):** No material gain over raw TabPFN across the three datasets at this pilot scale.
5. **Count/frequency targets (ClaimNb):** Fine-tune step can execute, but loss-scale behavior remains unstable and R2 stays negative.
6. **Best baseline competitor:** CatBoost/RandomForest remain stronger on variance-sensitive metrics (RMSE, R2) in this benchmark.
7. **Practical takeaway:** Current 1-step fine-tuned regressor is not yet competitive enough to replace top classical baselines.

---

## 5) Fine-Tuned Regressor vs Baselines (Current Pilot)

**Run date:** 2026-04-05  
**Artifacts:** `outputs/current/tables/tabpfn_regression_finetune_vs_raw.csv`, `outputs/current/tables/multi_dataset_regression_benchmark_with_tabpfn_finetuned.csv`

**Run settings:** CPU, seed=42, n_estimators=4, 300 train rows, 2000 test rows, context=64, max_finetune_steps=1.

### Summary table (fine-tuned TabPFN vs best classical baseline)

| Dataset | Fine-tune viability | Fine-tuned MAE | Best baseline MAE | Fine-tuned RMSE | Best baseline RMSE | Fine-tuned R2 | Best baseline R2 |
|---|---|---:|---:|---:|---:|---:|---:|
| freMTPL2 Frequency (ClaimNb) | steps=1, nonfinite-loss skips=1, extreme last loss | **0.0582** | 0.0763 (CatBoost) | 0.2550 | **0.2169** (CatBoost) | -0.0547 | **0.1716** (CatBoost) |
| EU Direct Premium (prem_pure) | steps=1, nonfinite-loss skips=1 | 17.3260 | **12.2848** (RF) | 57.8052 | **19.7943** (RF) | 0.9152 | **0.9899** (RF) |
| AUS Auto Vehicle Value (VehValue) | steps=0, nonfinite-loss skips=5 | 0.4627 | **0.4325** (CatBoost) | 0.8468 | **0.7503** (CatBoost) | 0.5330 | **0.6290** (CatBoost) |

### Interpretation
- Fine-tuning did not deliver a practical lift over raw TabPFN in this pilot configuration.
- ClaimNb still shows numerical-stability concerns (astronomical loss magnitude despite one executed step).
- On EU Direct and AUS Auto, fine-tuned TabPFN trails best classical baselines by a large margin on RMSE/R2.

---

## 6) Practical Recommendations

1. Keep TabPFN as a primary candidate for:
   - Binary classification where ranking quality (ROC) is critical
   - Continuous premium-style regression targets
2. Keep CatBoost as a primary classical fallback/challenger for:
   - Count-frequency style regression targets
   - Cases requiring fast inference with strong baseline reliability
3. Keep fine-tuned regressor in experimental status; do not promote over CatBoost/RF until stability-gated runs show consistent RMSE/R2 gains.

---

## 7) This-Phase Limitations and Impact on Findings

To keep interpretation honest for this phase, the following factors likely influenced outcomes:

1. **Regression fairness mismatch (train rows):**
   - Raw/fine-tuned TabPFN regression revalidation used capped train rows (300) for CPU feasibility.
   - Classical baseline benchmark rows are larger (up to 10,000).
   - **Impact:** comparisons are still informative, but effect sizes should be treated as directional rather than strict apples-to-apples superiority tests.

2. **Fine-tuning budget is pilot-scale:**
   - Regressor fine-tuning is mostly one-step and low-context in this phase.
   - **Impact:** negative or neutral deltas indicate current configuration underperformance, but do not prove that larger or better-tuned fine-tune schedules cannot improve results.

3. **Classifier/regressor design asymmetry:**
   - Classifier uses leave-one-dataset-out domain pool logic.
   - Regressor benchmark fine-tuning is mostly within-dataset train/fine-tune/test splitting.
   - **Impact:** combined cross-task claims should focus on practical observed outcomes, not strict methodological symmetry across tasks.

4. **Seed/stability depth is stronger for diagnostics than for all benchmark endpoints:**
   - Stability diagnostics were run where issues emerged, but not every benchmark table is multi-seed with CIs yet.
   - **Impact:** conclusions are strong for "tested setup" but still provisional for broad generalization.

### What this means for this phase
- It is valid to conclude that **the current fine-tuning setup did not produce consistent overall improvement**.
- It is not yet valid to claim that **all possible TabPFN fine-tuning strategies on insurance data are exhausted**.

---

## 8) Research-Exhaustion Decision Criteria

Use these criteria to decide whether to continue optimization or declare this line exhausted.

### Criteria to continue optimization
Continue if any of the following are true:
1. Regressor stability gate fails for key targets (for example ClaimNb).
2. Fine-tuned vs raw comparisons are based on pilot training budgets only.
3. Multi-seed pooled evidence with uncertainty bounds is incomplete for final decision endpoints.

### Criteria to declare this line exhausted (for this project scope)
Declare exhausted only after all of the following are met:
1. Fair-comparison reruns completed (matched row budgets or justified resource-normalized comparison).
2. Multi-seed (at least 3 seeds) baseline vs fine-tuned comparisons completed on primary metrics.
3. Regressor stability gate passes or repeatedly fails despite targeted ablations.
4. Fine-tuned TabPFN still fails to show reliable primary-metric gains on a majority of target datasets.

### Current status against criteria — UPDATED 2026-04-07
- **Criteria 1-2 now fully met.** Round 3 scale-up (controlled budget increase: context 64→128, steps 3→5) completed across all 4 target datasets with seeds 42, 43, 44 and both fine-tuning policies.
- **Criteria 3:** Regressor stability gate already failed in prior phases; classifier focus remains.
- **Criteria 4 met with evidence of failure:** Round 3 pooled deltas remain pooled-negative despite larger budget (Δ ROC−0.08, Δ PR−0.04) with only marginal improvement from Round 2 (+0.02 ROC).

**Decision: Downgrade classifier fine-tuning hypothesis for this dataset family.** Do not pursue larger budgets or new data expansion. Shift focus to calibration/preprocessing improvements.

Details: See `docs/reports/CLASSIFIER_HOMOGENEITY_HYPOTHESIS_METHOD.md::Round 3 Results` for execution summary, decision rule evaluation, and saved deltas.

---

## 9) Reproducibility Note

This combined report is transparent about evidence layers:
- Classification conclusions come directly from current CSV artifact (`data/processed/glm_vs_tabpfn_head_to_head.csv`).
- Regression baseline conclusions come directly from current CSV artifact (`data/processed/multi_dataset_regression_benchmark_results.csv`).
- TabPFN regression conclusions are now confirmed from the current-environment revalidation run (`outputs/current/tables/raw_tabpfn_regression_revalidation.csv`, 2026-04-05).
- Fine-tuned regressor pilot conclusions come from `outputs/current/tables/tabpfn_regression_finetune_vs_raw.csv`.
- **Caveat on comparability:** TabPFN revalidation used 300 train rows; classical baselines used up to 10,000. All comparisons in Section 3 should be interpreted with this disparity in mind.

---

## 10) Circumstances Matrix: When TabPFN Performs Well / Not Well

### TabPFN tends to perform well when
1. **The task is binary classification and ranking quality matters most (ROC AUC).**
   - Evidence: TabPFN ROC wins on 3/4 classification datasets.
2. **The regression target is continuous with strong structured signal (premium-style).**
   - Evidence: In the current revalidation, TabPFN is close to leading baselines on EU premium with far fewer training rows; earlier runs also reported stronger TabPFN outcomes for this target.
3. **Feature interactions are likely nonlinear and not fully captured by linear baselines.**
   - Evidence: Gains over GLM in most ROC comparisons suggest richer pattern capture.

### TabPFN tends to perform less well when
1. **Count/noisy regression targets are evaluated using variance-sensitive metrics (RMSE, R2).**
   - Evidence: On freMTPL2 Frequency, TabPFN MAE was best but CatBoost was better on RMSE/R2.
2. **PR AUC is the primary metric in highly imbalanced classification.**
   - Evidence: PR wins were mixed (2/4), even where ROC improved.
3. **A strong tree baseline is already near the practical ceiling.**
   - Evidence: RandomForest/CatBoost remain strongest classical competitors across regression datasets.

---

## 11) Practical Decision Rule (Current Evidence)

Use this as a default selection heuristic before full retuning:

1. **Classification:**
   - If KPI is ROC AUC -> start with TabPFN, then compare CatBoost.
   - If KPI is PR AUC -> run TabPFN and CatBoost side by side; pick by PR directly.
2. **Regression:**
   - Continuous premium/value target -> prioritize TabPFN and CatBoost.
   - Count-frequency target -> prioritize CatBoost first; include TabPFN as challenger for MAE-focused use cases.
3. **Production fallback:**
   - If TabPFN gain over best baseline is small (<1-2% relative on primary KPI), prefer the faster/simpler baseline.

---

## 12) What to Measure Next to Confirm These Circumstances

To make the "when it works" map rigorous, the next run should log the following per dataset:

1. Target type: binary / count / continuous
2. Imbalance and sparsity: positive rate, zero-inflation, missingness
3. Signal profile: baseline linear R2 (or separability proxy)
4. Metric split: ROC vs PR for classification; MAE vs RMSE/R2 for regression
5. Relative lift of TabPFN over best classical baseline

This will convert current qualitative patterns into a quantitative operating policy for model selection.

---

## 13) Source Workbooks

- notebooks/baseline_experiments/03_tabpfn_vs_glm_summary.ipynb
- notebooks/baseline_experiments/08_multi_dataset_regression_benchmark.ipynb
- notebooks/baseline_experiments/05_regression_finetuning.ipynb

## 14) Evidence Files

- data/processed/glm_vs_tabpfn_head_to_head.csv
- data/processed/multi_dataset_regression_benchmark_results.csv
- outputs/current/tables/raw_tabpfn_regression_revalidation.csv
- outputs/current/tables/multi_dataset_regression_benchmark_with_tabpfn_revalidated.csv
- outputs/current/tables/tabpfn_regression_finetune_vs_raw.csv
- outputs/current/tables/multi_dataset_regression_benchmark_with_tabpfn_finetuned.csv
- outputs/current/tables/domain_finetune_study_runs.csv
- outputs/current/logs/tabpfn_regression_finetune_vs_raw.md
