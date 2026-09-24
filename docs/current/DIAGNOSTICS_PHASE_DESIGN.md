# Diagnostics Phase — Understanding Why Datasets Are Hard Before Fine-Tuning Them

> Date: 2026-09-24 | Status: **PROPOSAL — awaiting team sign-off**
> Related: #22 | Companion to `FINE_TUNING_EXPERIMENT_DESIGN.md`, `PILOT_2_BRIEFING.md`
> Builds on: `regime_characterization.md`, `class_imbalance_analysis_summary.md`, master report §14

---

## 1. Why this exists

The fine-tuning plan asks *"does adapting the model help?"* but never asks **why the model struggles on specific datasets in the first place.** Without that diagnosis, fine-tuning is a solution in search of a problem.

The regime characterization (`regime_characterization.md`) already identified three distinct failure modes — but stopped at classification-level patterns and never diagnosed the dataset-level mechanics. This phase fills that gap.

**The risk it addresses:** we spend $4–30 on fine-tuning and find a small effect, when a $0 diagnostic phase might reveal that the real lever is feature engineering, target reframing, or preprocessing — or that the datasets where fine-tuning could help are exactly the ones where the model already wins.

---

## 2. What we already know (and don't)

### Known failure modes

| Mode | Datasets | Root Cause | Fine-Tuning Fixes It? |
|---|---|---|---|
| GLM-captured | eudirectlapse, ausprivauto0405, norauto, bemtl97 | Linear model already optimal | No — no gap to close |
| Tree-extractable only | spanish_motor_freq, freMTPL2freq | Count signal requires non-linear interactions | Possibly — but §14.14 reframing already flips verdict |
| Zero-inflated severity | bemtl97_amount, spanish_motor_severity | 89–95% zero mass makes RMSE meaningless | No — target definition problem |

### Known non-causes

| Hypothesis | Tested? | Result |
|---|---|---|
| Class imbalance causes TabPFN miscalibration | Yes (§11, class_imbalance_analysis_summary) | **Rejected** — rebalancing improved baselines +19–26% but TabPFN +0.9%. Miscalibration is orthogonal to class distribution. |
| Small data causes TabPFN losses | Partially (size sweep §13) | **Mixed** — TabPFN wins 8/9 cells ≤5K, but also wins at 29K (uslapseagent) and 58K (bemtl16). Size is necessary but not sufficient. |
| n_estimators matters | Yes (§14.1) | **Closed** — bit-identical to default at these sizes. Do not re-chase. |

### Unknown (never diagnosed)

| Question | Why it matters |
|---|---|
| Why does LR beat TabPFN on eudirectlapse? | The only outright classification loss — if feature engineering closes it, fine-tuning is unnecessary |
| What features does each model actually use? | If TabPFN and GLM use different features, the "gap" may be a feature-coverage problem |
| How many frequency targets flip under binary reframe? | §14.14 showed it works on spanish_motor_freq — does it work on freMTPL2freq? |
| Does preprocessing (encoding, ID screening) change the ranking? | R1 used `get_dummies` on everything with no screening — the historic study flagged this |
| What is the actual class imbalance effect on each dataset? | The existing test was one dataset at one setting; the effect may vary |

---

## 3. The five diagnostics

Each is $0 or near-$0. All can run on CPU. All produce evidence that changes the interpretation of fine-tuning results.

### D1 — Dataset Profiling (analysis only, $0)

**Question:** What are the structural properties of each dataset that might explain model performance?

**Output:** A table per dataset with:

| Property | How measured | Why it matters |
|---|---|---|
| Class balance | Positive rate, entropy of target | Imbalance affects calibration differently per model |
| Feature count / type mix | Numeric vs categorical ratio, high-cardinality features | TabPFN's prior is calibrated for a certain feature type distribution |
| Missingness | Per-column missing rate, pattern (MCAR/MAR/MNAR) | Missing data handling differs across models |
| Target distribution | Histogram, zero-inflation rate, skewness | Zero-inflated targets break RMSE-based comparisons |
| Feature correlation | Max pairwise correlation, VIF | Highly correlated features may confuse TabPFN's attention mechanism |
| Effective sample size | After one-hot encoding, how many features vs rows? | The 86-column coil2000 at 9.8K rows has a 114:9.8K feature:row ratio |

**Where the data lives:** `data/raw/*.csv` — already committed.

**Effort:** One script, ~200 lines. Reads each CSV, computes the profile, writes a summary table.

### D2 — Feature Importance Analysis (analysis only, $0)

**Question:** What features does TabPFN use vs GLM vs LGBM? Where do they disagree?

**Approach:** For each of the 6 classification datasets, run permutation importance (or SHAP where feasible) on three models: TabPFN, best GLM, best LGBM. Compare the top-10 features per model.

**What it answers:**
- If TabPFN and GLM use **the same features** but TabPFN ranks them differently → fine-tuning might help by learning better weights
- If they use **different features** → the gap is a feature-coverage problem, not a model-adaptation problem
- If LGBM uses **interaction features** that neither TabPFN nor GLM see → feature engineering is the lever

**Where the evidence lives:** The canonical folds and models are already committed in `scripts/eval/insurance_benchmark_v1/`.

**Effort:** One script, ~300 lines. Reuse the benchmark's model objects, compute permutation importance on the test set.

### D3 — Target Reframing Ablation (analysis only, $0)

**Question:** How many "losses" flip when frequency/count targets are reframed as classification?

§14.14 showed this works on spanish_motor_freq (AUC rank #1 after reframe). Does it work on freMTPL2freq?

**Approach:** For each frequency/count target:
1. Binary reframe: claim/no-claim (threshold > 0)
2. Ordinal reframe: 0 / 1 / 2+ claims
3. Run the benchmark on the reframed target
4. Compare TabPFN's rank before and after

**Datasets:** freMTPL2freq (678K rows), spanish_motor_freq (53.5K rows), norauto (184K rows — NbClaim), bemtl16 (58.7K — liability_claims count).

**What it answers:** If reframing flips 2+ datasets, the "frequency loss" is a framing artefact, not a model limitation. This would be a $0 finding that changes the adoption rule.

**Effort:** One script, ~150 lines. The reframe logic already exists in `scripts/eval/insurance_benchmark_v1/run_reframe_frequency.py`.

### D4 — Preprocessing Ablation (near-$0, ~$0.05)

**Question:** How much of TabPFN's gap is preprocessing, not the model?

**Approach:** Re-run the frontier benchmark on 2–3 datasets with:
1. **Current:** `get_dummies` on everything, no ID/date screening (the R1/historic default)
2. **Targeted:** drop ID-like columns (policy IDs, dates, row indices), target-encode high-cardinality categoricals
3. **Minimal:** only continuous features + low-cardinality categoricals

Compare TabPFN's performance across the three preprocessing regimes.

**What it answers:** If TabPFN's rank improves substantially under targeted preprocessing, the "model limitation" is actually a preprocessing limitation. This is the cheapest way to improve performance without fine-tuning.

**Effort:** ~100 lines of preprocessing wrapper, reuse the benchmark runner.

### D5 — eudirectlapse Deep-Dive (analysis only, $0)

**Question:** Why does LR beat TabPFN on eudirectlapse — the only outright classification loss?

**Approach:**
1. Profile the dataset (D1 output)
2. Feature importance comparison (D2 output)
3. Check if any features are ID-like or leaked
4. Test if feature engineering (interactions, polynomials) closes the gap for LR
5. Test if TabPFN improves with targeted preprocessing (D4 output)

**What it answers:** If the LR advantage is explained by specific features or interactions, we can either engineer those features for TabPFN or accept that GLM is the right model for this dataset. Either way, we understand the result instead of fine-tuning blind.

**Effort:** Part of D1–D4, plus ~1 hour of directed analysis.

---

## 4. How this interacts with the fine-tuning plan

The diagnostics run **before or alongside** the fine-tuning replication — not instead of it.

| Scenario | Diagnostics say | Fine-tuning action |
|---|---|---|
| TabPFN losses are explained by preprocessing | D4 shows gap closes with better preprocessing | Run fine-tuning on preprocessed data — the lever changes |
| TabPFN losses are explained by target definition | D3 shows reframing flips verdicts | Reframe first, fine-tune on the reframed target |
| TabPFN losses are explained by feature coverage | D2 shows TabPFN and GLM use different features | Feature engineering is the lever — fine-tuning may not help |
| TabPFN losses are unexplained | D1–D5 find no structural explanation | Fine-tuning is the right next step — the model needs adaptation |
| TabPFN already wins everywhere it should | Regime characterization holds | Fine-tuning is a within-model improvement question, not a gap-closing one |

**The key insight:** if D1–D4 explain *why* datasets are hard, fine-tuning becomes a targeted intervention on the datasets where it can help, rather than a blanket approach across all 15 datasets.

---

## 5. What we are explicitly NOT proposing

1. **Not replacing the fine-tuning plan.** The diagnostics inform it; they don't supersede it.
2. **Not running new models.** All diagnostics use existing benchmark infrastructure and committed data.
3. **Not claiming the diagnostics will find something.** They might confirm that fine-tuning is the right lever. That's a valid outcome.
4. **Not delaying the fine-tuning replication.** The diagnostics can run in parallel — they're CPU-only analysis work.

---

## 6. Cost and timeline

| Diagnostic | Cost | Effort | Dependencies |
|---|---|---|---|
| D1 Dataset profiling | $0 | ~200 lines, 1 day | None |
| D2 Feature importance | $0 | ~300 lines, 2 days | D1 (for context) |
| D3 Target reframing | $0 | ~150 lines, 1 day | Existing reframe script |
| D4 Preprocessing ablation | ~$0.05 | ~100 lines, 1 day | Benchmark runner |
| D5 eudirectlapse deep-dive | $0 | ~1 hour analysis | D1–D4 outputs |
| **Total** | **~$0.05** | **~5 days** | — |

**The ask:** fund the diagnostics phase (~$0.05, ~5 days of analysis work) before or alongside the fine-tuning replication (~$0.074). Total: ~$0.13 for a complete picture.

---

## 7. Decisions needed

| # | Question | Options |
|---|---|---|
| 1 | Run diagnostics before or in parallel with fine-tuning? | Before (informs the design) / Parallel (saves time) |
| 2 | Which datasets get the full D1–D5 treatment? | All 15 / just the 4 R1 datasets / just eudirectlapse (the loss) |
| 3 | Who owns the feature importance analysis? | Needs someone familiar with insurance feature semantics |
| 4 | Is the preprocessing ablation worth running? | It changes the fine-tuning baseline if preprocessing matters |
