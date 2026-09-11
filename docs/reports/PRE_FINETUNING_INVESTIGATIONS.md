# Pre-Fine-Tuning Investigation Log

> Date: 2026-09-11 | Purpose: Single source of truth for all pre-pilot investigations
> Related: #22 (GPU), #129 (E4), #156 (provider), #159 (feedback)
> Consumes: ~~STAGE_A_B_FINDINGS_AND_RECOMMENDATIONS~~, ~~TABPFN_FINE_TUNING_LIMIT_STUDY~~, ~~INSURANCE_DOMAIN_FINETUNING_METHOD_PROTOCOL~~, ~~INSURANCE_SPECIFIC_FINETUNING_EVIDENCE~~, ~~MULTI_DATASET_GLM_VS_TABPFN_SUMMARY~~, ~~POST_HOC_OPTIMISATION~~, ~~MODEL_VERSIONS~~, **master report**

---

## 0. Goal

**Primary goal:** Does fine-tuning TabPFN on insurance data improve performance on held-out insurance tasks, versus raw TabPFN and actuarial baselines (GLM, post-hoc calibrated)?

**Baselines to beat:**
- Raw TabPFN (no fine-tuning)
- GLM (LogisticRegression)
- Post-hoc calibrated TabPFN (isotonic, engineered features) — the +1.66% Brier bar

---

## CRITICAL: Master Report Findings (v3 API, canonical folds)

The master report (`docs/analyses/tabpfn_vs_gbdt_baselines_finetuning.md`) tested TabPFN v3 on 6 canonical insurance datasets with 5-fold canonical folds. **This is the authoritative benchmark for our datasets.**

### Classification: TabPFN is AUC/PR-AUC #1 on ALL 6 datasets

| Dataset | Rows | Target | TabPFN position | GLM gap | Outcome |
|---|---|---|---|---|---|
| coil2000 | 9,822 | CARAVAN | **on frontier, best** | +2.5% | WIN |
| bemtl16 | 58,723 | liability claims | **on frontier, best** | +10.6% | WIN |
| uslapseagent | 29,317 | surrender | **on frontier, best** | +10.9% | WIN |
| ausautoBI8999 | 22,036 | log AggClaim | **on frontier, best** | +11.0% | WIN |
| ausprivauto0405_vehvalue | 67,856 | VehValue | **on frontier, best** | +41.8% | WIN |
| norauto | 184,000 | NbClaim | on frontier (fold-noise tie) | +1.9% | TIE |

**Key finding:** TabPFN wins on ALL 6 classification datasets, including at production scale (163K-184K rows). Calibration (Brier) never significantly worse at default settings.

### Regime characterization: WHEN TabPFN wins

From `docs/analyses/regime_characterization.md`:

**Adoption rule:** Adopt default TabPFN when:
- Data is scarce (≤ ~5K training rows) — 8/9 size-sweep cells won, OR
- Classification/lapse-style tasks where the linear floor is far from achievable — best GLM ≥ ~3% behind, or ≥ ~0.05 AUC gap

**EU Lapse is the disclosed exception** — TabPFN AUC 0.6101 vs best GLM 0.6260 (additive-lapse structure the model doesn't capture). GLM gap ≈ 0.

### Reframe finding (issue #67)

Count/frequency targets (like ClaimNb) lose on the count axis — TabPFN Poisson deviance is dominated by GBDT/GLM. **But when reframed as classification** (claim/no-claim, binary or ordinal 0/1/2+), TabPFN is AUC rank #1, paired-significant at both seeds:

| Metric | TabPFN | delta vs best | p | rank |
|---|---|---|---|---|
| AUC (binary, seed 42) | 0.7170 | +0.0080 | 0.0010 | 1 |
| AUC (binary, seed 7) | 0.7165 | +0.0098 | 0.0020 | 1 |

**Implication:** For frequency targets, reframe as classification to get TabPFN value.

### Small-finetune trials in the master report

The small-finetune trials were on **coil2000** (from the limit study), not freMTPL2:
- coil2000, rows 300-3,000, 1-3 steps, context 64/128, seed 42
- Results in `outputs/current/tables/tabpfn_finetune_trial_results.csv`

**Stage A/B's "strongest on freMTPL2" claim is NOT in the master report's small-finetune trials.** This needs verification.

### Breakdown into achievable questions

**Q0: Does fine-tuning help on classification?**
The master report found raw TabPFN v3 is AUC rank #1 on all 6 canonical insurance datasets — no fine-tuning needed. This question asks whether fine-tuning can push performance even further, or whether TabPFN is already at ceiling.
- If no → TabPFN is already optimal for classification. Check regression (Q3).
- If yes → Identify where the gain comes from (Q1, Q2).

**Q1: Can fine-tuning close the gap on EU Lapse?**
EU Lapse is the only canonical dataset where TabPFN loses to GLM (AUC 0.6101 vs 0.6260). The diagnostic shows it's a linear problem (GLM ≈ RandomForest on Brier). This question tests whether fine-tuning can help where raw TabPFN fails — even on linear data.
- If yes → fine-tuning works where needed most. Proceed to understand mechanism.
- If no → fine-tuning can't help on linear problems. Boundary identified.

**Q2: Does fine-tuning help at small-n?**
RealTabPFN-2.5 showed fine-tuning helps at small n but hurts at large n. This question tests whether the small-n sweet spot exists for insurance data — the regime where data is scarce enough that fine-tuning the prior adds value.
- If yes → fine-tuning is for thin-segment/small-data use cases.
- If no → no scale-dependent effect.

**Q3: Does fine-tuning help on regression/frequency targets?**
The master report shows TabPFN loses on count/frequency targets (Poisson deviance). This question asks whether fine-tuning can close the gap on regression tasks where raw TabPFN currently fails.
- If yes → regression is the fine-tuning opportunity.
- If no → fine-tuning doesn't help insurance data broadly.

**Q4: Does pool composition matter?**
Stage A/B found all-other pooled fine-tuning hurt (v2 API). This question tests whether the hurt was due to cross-dataset mismatch or fine-tuning itself. If homogeneous pooling beats all-other, pool composition is the gate.
- If yes → build similarity-based pool selection.
- If no → pool composition irrelevant for these datasets.

**Q5: How does the effect scale with n and train ratio?**
RealTabPFN-2.5 showed fine-tuning helps at small n but hurts at large n. This question tests two interacting factors: **total dataset size** AND **train/test split ratio**.

In insurance, thin segments (new products, niche markets, low-credibility cells) have small N. If fine-tuning helps more when data is scarce, we need to know: is it the total N, the train ratio, or the interaction?

**Factors:**

| Factor | Levels | Rationale |
|---|---|---|
| Total N | 1K, 2K, 5K, full | Does fine-tuning help more when data is scarce? |
| Train ratio | 20/80, 50/50, 80/20 | Does having more training data help or hurt fine-tuning? |

**Hypothesis:** Fine-tuning helps most at **small N + high train ratio** (80/20). At low N, there's little test data for evaluation, so a higher train ratio gives the model more signal. At high N, TabPFN already performs well, so fine-tuning adds little.

**Design:** 3×3 factorial on one dataset (coil2000, 9.8K rows). If the interaction is significant, repeat on eudirectlapse.

| | N=1K | N=2K | N=5K |
|---|---|---|---|
| 20/80 split | fine-tuned vs raw | fine-tuned vs raw | fine-tuned vs raw |
| 50/50 split | fine-tuned vs raw | fine-tuned vs raw | fine-tuned vs raw |
| 80/20 split | fine-tuned vs raw | fine-tuned vs raw | fine-tuned vs raw |

**Outcome:** A surface plot of fine-tuning benefit (ΔROC = fine_tuned − raw) across N × ratio. If the surface peaks at small N + high ratio, we have a clear use case: thin-segment fine-tuning.

- If peak at small N + high ratio → fine-tuning is for thin segments
- If flat (no interaction) → fine-tuning effect is independent of data scarcity
- If peak at large N → fine-tuning scales, contradicting RealTabPFN-2.5

---

## Master Report Extensions

The master report (`docs/analyses/tabpfn_vs_gbdt_baselines_finetuning.md`) contains findings that directly inform the fine-tuning design. These are not new questions — they are extensions that refine how we answer the existing questions.

### E1: Reframe frequency as classification (informs Q3)

**Master report finding (issue #67):** Count/frequency targets lose on the count axis, but when reframed as classification (binary claim/no-claim, or ordinal 0/1/2+), TabPFN is AUC rank #1, paired-significant at both seeds.

**Extension:** Fine-tune on the reframed classification version of frequency targets. If TabPFN already wins at default, fine-tuning may widen the gap. If it doesn't help, we learn that fine-tuning doesn't add value even on TabPFN's home ground.

**Refined Q3:** Fine-tune on `ClaimIndicator` (binary) from freMTPL2 — does it improve over default? If yes, regression fine-tuning should target reframed classification, not raw count regression.

### E2: Small-n sweet spot (informs Q2, Q5)

**Master report finding (§13.2):** TabPFN wins 8/9 size-sweep cells at ≤5K rows. The small-data regime is real.

**Extension:** Does fine-tuning help more at small n than at large n? RealTabPFN-2.5 showed this crossover — test it on insurance data. If fine-tuning only helps at small-n, it's for thin-segment use cases (new products, niche markets, low-credibility cells).

**Refined Q2/Q5:** Run the scale ladder (1K, 5K, full) on the same dataset. Does the delta shrink with n? If fine-tuning only helps at small-n, it's for thin-segment use cases.

### E3: EU Lapse exception (informs Q1)

**Master report finding (regime characterization):** EU Lapse is the disclosed exception — TabPFN AUC 0.6101 vs GLM 0.6260. The gap is attributed to "additive-lapse structure the model doesn't capture."

**Extension:** If fine-tuning can close this gap, it proves fine-tuning works where TabPFN's prior is wrong. If it can't, we learn that fine-tuning can't fix fundamental prior mismatch.

**Refined Q1:** This is the headline test. Fine-tuning on EU Lapse (in-domain, Arm B) — does it beat GLM? The answer defines whether fine-tuning is a viable insurance tool.

### E4: Calibration is already good (informs all)

**Master report finding (§14.11):** Brier is never significantly worse at default settings — TabPFN is already well-calibrated. Two ~1e-4 exceptions vs tuned/engineered baselines.

**Extension:** If calibration is already good, fine-tuning may not help Brier. But it may help ROC/ranking. This suggests the primary metric for fine-tuning should be ROC, not Brier.

**Refined metric strategy:** Track ROC and Brier separately. Does fine-tuning move ROC without moving Brier? If so, fine-tuning helps ranking but not pricing.

### E5: Focus on off-frontier datasets (informs Q0, Q3)

**Master report finding (§14.2–§14.10):** TabPFN is on the frontier for 7 of 12 datasets (log-loss axis), off it 5× at scale. The 5 off-frontier datasets are: ausprivauto0405, eudirectlapse, norauto, bemtl97, freMTPL2freq.

**Extension:** Focus fine-tuning on the 5 off-frontier datasets — where there's room to improve. For the 7 datasets already on the frontier, fine-tuning may not help (already optimal).

**Refined Q0:** Fine-tune on ausprivauto0405, eudirectlapse, norauto, bemtl97, freMTPL2freq. Does it push any onto the frontier?

### E6: Flat size curve (informs Q5)

**Master report finding (§13.3):** TabPFN leads on all six practical-size cells (1K and 5K) and on two of the three full-size cells. Performance doesn't degrade with scale.

**Extension:** If TabPFN doesn't degrade with scale, fine-tuning may help uniformly at all scales. No crossover expected (unlike RealTabPFN-2.5).

**Refined Q5:** Run the scale ladder — does fine-tuning help at all scales or just small-n? If TabPFN is flat, fine-tuning may be uniformly helpful or uniformly unhelpful.

### E7: Synthetic data generation (new investigation)

**Feedback (#159 Q6):** Does the synthetic data generation process consider joint distribution? If features are generated independently, the model's prior may not capture real-world insurance correlations.

**nanoTabPFN repo:** The [stprnvsh/nanoTabPFN fork](https://github.com/stprnvsh/nanoTabPFN) has a `generate_synthetic_data.py` script that generates large synthetic datasets for benchmarking. This uses the same prior-based generation as TabPFN v2.

**Extension for insurance:** Adapt the nanoTabPFN generator to produce synthetic insurance data with:
- **High noise/signal ratio** — insurance data is noisy; the model needs to see this
- **Skewed targets** — claim frequencies are zero-inflated and heavy-tailed
- **Joint feature correlations** — age, vehicle type, region are correlated in real insurance

**Investigation plan:**
1. Clone `github.com/stprnvsh/nanoTabPFN` and inspect `generate_synthetic_data.py`
2. Adapt the generator to produce data matching insurance distributions (zero-inflation, skew, correlations)
3. Use synthetic data as a fine-tune pool — does it improve performance on real insurance data?

**Risk:** If synthetic data doesn't capture real insurance structure, it may add noise rather than signal. Test on one dataset first (coil2000) before scaling.

### E8: Conformal prediction intervals (new investigation)

**Feedback (#159 Q10):** Are confidence intervals around predictions statistically correct?

**Extension:** Use TabPFN's prediction intervals to inform a GLM. If TabPFN intervals are well-calibrated, they could identify which predictions are uncertain — and the GLM could be used as a fallback for those cases. This creates a TabPFN-GLM ensemble: TabPFN for confident predictions, GLM for uncertain ones.

**Investigation:** Run conformal prediction on TabPFN outputs. Are the intervals statistically valid (correct coverage)? If yes, use them to route between TabPFN and GLM.

---

## Missing Metrics

We've tracked ML metrics (Brier, ROC, AUC, etc.). Insurance-native metrics are also needed:

| Metric | What it captures | Why it matters |
|---|---|---|
| **Poisson deviance** | Count/frequency model quality | Insurance-native for claim counts. Brier doesn't apply. |
| **Top-decile lift** | Business value of ranking | Does TabPFN correctly identify the 10% riskiest policies? |
| **Gini coefficient** | Ranking discrimination | More interpretable to actuaries than AUC. |
| **Calibration by segment** | Miscalibration in subgroups | Overall calibration can hide systematic errors for high-risk segments. |
| **Prediction stability (CV)** | Variance across folds/seeds | High variance = unreliable for production pricing. |
| **Marginal effect plausibility** | Do learned relationships make actuarial sense? | Regulators require interpretable, plausible relationships. |
| **Inference cost per prediction** | $/time per policy | Real-time pricing requires fast inference. |
| **Data efficiency** | Minimum n for acceptable performance | Thin-segment insurance (new products, niche markets). |

**Action:** Add Poisson deviance and top-decile lift to the pilot's metric suite.

---

## Novel Directions (Outside-the-Box Ideas)

### N1: TabPFN as a Feature for GLM (Stacking)
Instead of TabPFN OR GLM, use TabPFN's predicted probabilities **as an input feature** to a GLM. The GLM gets TabPFN's ranking power but outputs interpretable coefficients that regulators accept. This is the simplest ensemble — and it may close the EU Lapse gap because the GLM can learn to correct TabPFN's systematic errors.

### N2: TabPFN Disagreement as an Uncertainty Signal
Run TabPFN with multiple seeds or configs. Where predictions agree → high confidence. Where they disagree → flag for manual review or GLM fallback. This is cheaper than conformal prediction (no calibration set needed) and naturally captures model uncertainty.

### N3: Attention as Feature Importance
Use TabPFN's attention patterns to identify which features drive predictions. Then build a **parsimonious GLM** with just those features. You get a 5-parameter GLM that captures what TabPFN learned from 10M parameters — regulator-friendly and accurate.

### N4: The "Regulator's Dilemma" Composite Score
Build a composite score that captures what regulators actually care about:
- Calibration (pricing accuracy)
- Fairness (no protected-class bias)
- Stability (low variance across time/samples)
- Parsimony (interpretable complexity)

TabPFN fails on parsimony by design. But does it win so much on calibration and stability that the composite score favors it? This is the real adoption question.

### N5: Cross-Dataset Transfer Coefficient
Quantify exactly how much knowledge transfers from one insurance dataset to another. If you fine-tune on freMTPL2, what fraction of that knowledge applies to EU Lapse? This could create a **dataset similarity index** that tells you in advance whether fine-tuning will help.

### N6: TabPFN as a Data Generator for Stress Testing
Instead of using TabPFN for predictions, **invert** it: use TabPFN's generative capabilities to create adversarial insurance scenarios. What's the worst-case portfolio? What combination of features would produce extreme losses? This is counter-cyclical stress testing without historical data.

### N7: TabPFN as a "Second Opinion" System
Use TabPFN's disagreement with a GLM as a **flag for manual review**. Where both models agree → automate. Where they disagree → escalate. This is a practical deployment pattern that doesn't require beating the GLM — just being different enough to be useful.

---

### Question dependency graph

```
Q0: Does fine-tuning help at all on classification?
├── No → Check Q3: Does regression help?
└── Yes → Q1: Does fine-tuning help EU Lapse (exception)?
    ├── Yes → Fine-tuning works where needed most
    └── No → Q2: Does fine-tuning help at small-n?
        ├── Yes → Sweet spot identified
        └── No → Q4: Does pool composition matter?
            ├── Yes → Build homogeneous selection
            └── No → Q5: Does scaling with n explain it?
                ├── Yes → Define crossover
                └── No → STOP (negative result)

Q3: Does fine-tuning help on regression targets?
├── Yes → Regression is the opportunity
└── No → Fine-tuning doesn't help insurance data
```

---

## 1. Data Inventory

| Dataset | File | Rows | Targets | Positive Rate |
|---|---|---|---|---|
| EU Direct Lapse | `eudirectlapse.csv` | 23,060 | `lapse` | 12.81% |
| freMTPL2 Binary | `freMTPL2freq_binary.csv` | 50,000 | `ClaimIndicator` | 5.02% |
| freMTPL2 (full) | `freMTPL2freq.csv` | 673,383 | `ClaimNb`, `Exposure`, `ClaimAmount` | mixed |
| COIL 2000 | `coil2000.csv` | 9,822 | `CARAVAN` | 5.97% |
| Aus. Vehicle | `ausprivauto0405.csv` | 67,856 | `ClaimOcc` | 6.81% |

---

## 2. Prior Results (What We Already Know)

### 2.1 TabPFN vs GLM (Multi-Dataset Benchmark, v2 API)

| Dataset | GLM ROC | TabPFN ROC | Winner |
|---|---|---|---|
| EU Direct Lapse | 0.5943 | 0.5863 | **GLM** |
| COIL 2000 | 0.6956 | 0.7178 | TabPFN |
| Aus. Vehicle | 0.6587 | 0.6591 | TabPFN |
| freMTPL2 Binary | 0.5981 | 0.6131 | TabPFN |

**TabPFN wins 3/4 on ROC.** EU Lapse is the exception.

### 2.2 Post-Hoc Optimisation (v2 API, EU Lapse)

| Variant | Brier | ROC |
|---|---|---|
| Raw baseline | 0.109678 | 0.6158 |
| Engineered + Isotonic Cal | **0.107982** | **0.6233** |

**The bar to beat: Brier < 0.1080, ROC > 0.623.**

### 2.3 Domain Fine-Tuning Results (Stage A/B, v2 API)

**Pooled all-other fine-tuning HURT performance:**

| Config | ROC AUC delta | Brier delta |
|---|---|---|
| context=64, steps=1 | -0.0528 | +0.0008 |
| context=64, steps=3 | -0.0741 | +0.0016 |
| context=64, steps=5 | -0.0737 | +0.0016 |
| context=128, steps=5 | -0.0586 | +0.0009 |

**But dataset-level heterogeneity:**
- **freMTPL2freq_binary:** domain-fine-tuned TabPFN was **strongest** (best Brier, LogLoss, ROC, PR)
- **coil2000, Aus. Vehicle:** raw TabPFN remained strongest
- **EU Lapse:** logistic regression strongest

**Key recommendation from Stage A/B:** Build a "homogeneous pool" using similarity checks (feature/schema overlap, event-rate proximity, validation transfer performance). Compare: no fine-tune vs all-other pooled vs homogeneous-only pooled.

### 2.4 M1 Local Fine-Tuning Limits (v2 API)

| Rows | Context | Device | Wall Time | Max RSS |
|---|---|---|---|---|
| 1000 | 64 | cpu | 14.5s | 663 MB |
| 1000 | 64 | mps | 19.2s | 496 MB |
| 3000 | 128 | cpu | 36.3s | 1.2 GB |
| 3000 | 128 | mps | 34.9s | 638 MB |

**CPU faster at small N, MPS faster at 3K. MPS uses ~half memory at context=128.**
**Practical M1 ceiling: ~3,000 rows.**

### 2.5 Regressor Stability (Stage R2, v2 API)

Zero-inflation hypothesis for non-finite losses **REJECTED**. Even with 95.2% data reduction (positive-claims-only pool), non-finite loss persists. Root cause likely numerical instability in TabPFN's forward/loss for frequency-transformed targets.

---

## 3. Pre-Experiment Diagnostic (COMPLETE)

**Script:** `scripts/diagnostic_complexity.py`
**Method:** GLM vs RandomForest (50 trees, depth 6) on 3,500 rows

| Dataset | Features | GLM Brier | RF Brier | Delta | GLM ROC | RF ROC | Verdict |
|---|---|---|---|---|---|---|---|
| EU Lapse | 62 | 0.1067 | 0.1078 | -0.001 | 0.657 | 0.632 | **LINEAR** |
| freMTPL2 | 47 | 0.0485 | 0.0479 | +0.001 | 0.555 | 0.583 | **LINEAR** |

**Both datasets linear on Brier.** freMTPL2 shows ROC signal (RF 0.583 > GLM 0.555).

**Implication:** Fine-tuning unlikely to improve Brier. But ROC signal on freMTPL2 means ranking may improve.

---

## 4. Open Investigations

### 4.1 Stage A/B Metric Re-Examination
**File:** `outputs/current/tables/domain_finetune_study_runs.csv`
**Question:** What metric showed "strongest"? If ROC, freMTPL2 is still viable. If Brier, contradiction needs resolving.
**Status:** pending

### 4.2 Regression Diagnostic
**Script needed:** `scripts/diagnostic_regression.py`
**Method:** GLM vs RandomForest on continuous targets (Exposure, ClaimNb, ClaimAmount)
**Hypothesis:** Continuous targets may have non-linear structure that classification misses.
**Status:** pending

### 4.3 GPU Pipeline Validation
**Test:** Run raw TabPFN inference on freMTPL2 (5K rows, n_estimators=8) on Colab T4.
**Checks:** No OOM, runtime < 5 min, model saves/loads, predictions valid.
**Status:** pending

### 4.4 Pool Dry Run
**Test:** Assemble pool (EU Lapse + COIL + Aus. Vehicle, proportional, 10K cap).
**Checks:** Size as expected, no duplicates, fits on T4.
**Status:** pending

---

## 5. Design Decisions (Pending Investigations)

| Decision | Options | Current lean |
|---|---|---|
| **Primary target** | freMTPL2 Binary vs Exposure (regression) | freMTPL2 (pending regression diagnostic) |
| **Pool composition** | All-other vs homogeneous-only | Homogeneous-only if pool matters for linear data |
| **Metrics** | Brier (flat expected) + ROC + ECE + LogLoss | Track all; ROC may show signal |
| **Config grid** | Match Stage A/B (steps 1/3/5, context 64/128) | Yes, for comparability |

---

## 6. Acceptance Criteria for Full Pilot

- [ ] Stage A/B results examined — confirm what "strongest" means
- [ ] Regression diagnostic complete
- [ ] GPU pipeline validated on real data
- [ ] Pool assembly verified
- [ ] Primary target selected
- [ ] Success criteria agreed

---

## 7. Key Open Questions

1. **Why did Stage A/B find fine-tuning strongest on freMTPL2 if it's linear?** — Re-examine the data
2. **Does fine-tuning help ROC even when Brier is flat?** — Track ROC separately
3. **Are continuous targets non-linear?** — Run regression diagnostic
4. **What's the memory limit for n_estimators=8 on freMTPL2?** — Profile on T4
5. **Does pool composition matter for linear data?** — Test in pilot

---

## 8. Version Note

All prior fine-tuning results (Stage A/B, limit study) used **TabPFN v2 API (remote)**. This experiment uses **TabPFN v3 (local weights, CUDA)**. Results may differ. Track version explicitly in all artifacts.

---

_Consumes prior reports. See `docs/reports/archive/` for original documents._
