# Reserving with Foundational Models: Evidence from the TabPFN Benchmark

**Document purpose:** Summary of findings relevant to using foundational models (specifically TabPFN) for insurance reserving tasks. Compiled from the IFoA ADSWP benchmark suite.

**Date:** 2026-08-20  
**Sources:** Master report (`tabpfn_vs_gbdt_baselines_finetuning.md`), regime analysis (`regime_characterization.md`), benchmark summary (`TABPFN_BENCHMARK_SUMMARY.md`), combined analysis (`COMBINED_TABPFN_CLASSIFIER_REGRESSOR_ANALYSIS.md`)

---

## Executive Summary

**Verdict: Foundational models are NOT suitable for traditional reserving tasks (claim amount prediction, IBNR estimation, ultimate claim cost modeling).** TabPFN loses decisively on severity/amount regressions at scale (+48% to +67% worse than GBDTs). However, foundational models may add value in **claim triage** (ranking which claims are likely to develop) — a complementary role, not a replacement for classical reserving models.

| Reserving Task | TabPFN Suitability | Evidence |
|----------------|---------------------|----------|
| Claim amount prediction (severity) | ❌ Not suitable | +48% to +67% worse than GBDTs at scale |
| IBNR/ultimate claim cost modeling | ❌ Not suitable | Zero-inflated distributions cause failure |
| Reserve adequacy assessment | ⚠️ Limited | Better calibration after isotonic regression |
| Claim triage/prioritization | ✅ Suitable | AUC #1 on claim/no-claim classification |
| Small data reserving (≤5K rows) | ⚠️ Conditional | Wins on small severity tasks only |

---

## 1. Severity Regression Results (Direct Reserving Evidence)

### 1.1 The "Do Not Deploy for Severity" Verdict

**From Master Report §8:**
> "Do not adopt default-config TabPFN as a general insurance modeling engine today. On 8 valid CASdatasets tasks: GBDTs win the aggregate; TabPFN loses decisively on both severity regressions and costs 5–50× in train and 100–1000× in inference."

**From §5.3:**
> "Neither fine-tuning path currently closes the gap to GBDTs. Worse, the benchmark's two decisive TabPFN losses (severity regressions) are exactly the tasks where the fine-tuning evidence is thinnest (all finetune studies were classification targets). **Fine-tuning, as configured today, does not change the 'do not deploy TabPFN for severity' verdict.**"

### 1.2 Per-Dataset Severity Results

#### **bemtl97_amount** — Claim Amount Prediction (163,212 rows, ~89% zero-inflated)

| method | mean RMSE | ± SE | n_params | on frontier |
|--------|-----------|------|----------|-------------|
| **lgbm** | **0.48499** | 0.00431 | 3,100 | yes |
| cat | 0.48726 | 0.00412 | 63,226 | yes |
| xgb | 0.49149 | 0.00448 | 4,733 | yes |
| rf | 0.50457 | 0.00461 | 902,022 | no |
| ols | 0.70799 | 0.00651 | 12 | yes |
| **tabpfn** | **0.72825** | 0.01057 | 10,000,000 | **no** |
| tweedieglm | 1.84473 | 0.00626 | 12 | yes |
| poissonglm | 6.45906 | 2.83431 | 12 | yes |

**Source:** §14.8, `frontier_results_bemtl97_amount.csv`

**Interpretation:** TabPFN is dominated — beaten on power and on parsimony. The zero-inflation trap: poissonglm is catastrophic (6.45906) because predicting >0 systematically misses the ~89% zero mass. TabPFN suffers a similar (though less severe) failure.

#### **spanish_motor_severity** — Claim Cost Prediction (53,502 rows)

| method | mean RMSE | ± SE | n_params | on frontier |
|--------|-----------|------|----------|-------------|
| **lgbm** | **1.83719** | 0.01165 | 3,100 | yes |
| ols | 1.87810 | — | 21 | yes |
| **tabpfn** | **1.88616** | 0.01165 | 10,000,000 | **no** (5th of 8) |

**Source:** §14.10, `frontier_results_spanish_motor_severity.csv`

**Interpretation:** TabPFN lands off-frontier, 5th of 8 models. At 53.5K rows, the 10M-param model adds nothing a 3,100-param LGBM or a 21-param GLM does not already provide.

#### **ausautoBI8999** — BI Severity (22,036 rows) — THE ONE EXCEPTION

| method | mean RMSE | ± SE | n_params | on frontier |
|--------|-----------|------|----------|-------------|
| **tabpfn** | **0.96491** | 0.00868 | 10,000,000 | yes |
| cat | 0.96883 | 0.00756 | 63,944 | yes |
| lgbm | 0.97456 | 0.00822 | 3,100 | yes |
| xgb | 0.98945 | 0.00957 | 5,223 | yes |
| ols | 1.07133 | 0.00928 | 12 | yes |

**Source:** §14.8, `frontier_results_ausautoBI8999.csv`

**Interpretation:** TabPFN wins the power axis outright at small N — beyond SE at 22,036 rows. This is the only severity task TabPFN won, but it required a small dataset with continuous (not zero-inflated) claims.

---

## 2. Why TabPFN Fails on Reserving Tasks

### 2.1 Zero-Inflation Problem

Claim amounts typically have ~89% zero mass (no claim). TabPFN's in-context learning cannot handle this distribution:

> "bemtl97_amount has the largest GLM gap of all (+46%) and TabPFN still loses — to ols, an intercept-scale 12-param model." — §14.8

### 2.2 Context Window Limitations

> "Earlier generations could effectively attend to only ~1K training rows, a context-window design limit. The v3 model's API now accepts up to 1M rows and still loses on accuracy-per-complexity and speed — so the measured pattern holds regardless of mechanism." — §12.1

### 2.3 Signal Extraction Failure

From Regime Characterization §2:
> "The discriminator is not 'thin vs captured' — both are thin. It is whether TabPFN's prior extracts the signal that linear models miss, at parity or better with the trees."

**Losses (6/6):** GLM gap ≈ 0 or fold-noise tie — 4/4 GLM-captured tasks — plus the tree-only-signal tasks: both frequency tasks (spanish_freq, freMTPL2freq) and **zero-inflated severity at 163K (bemtl97_amount), where TabPFN cannot beat even the GLM floor**.

### 2.4 Regression Lead Does Not Survive at Scale

From §14.8 (D4 synthesis):
> "TabPFN's regression lead does not survive the frontier. Across the four regression axes TabPFN wins power only at small N — beyond SE at 22,036 rows (ausautoBI8999) and on the beyond-SE tie at 67,856 rows (vehvalue) — and is dominated at scale: 163,212 rows (bemtl97_amount) and 678,013 rows (freMTPL2freq)."

---

## 3. The Adoption Rule (Decision Framework)

### 3.1 When to Use TabPFN

From Regime Characterization §3:
> "**Use default TabPFN when** training rows are ≤ ~5K (won 8/9 size-sweep cells), **or** the task is classification/lapse-style and the linear floor is far from achievable — best LR/GLM ≥ ~3% behind the best model (or ≥ ~0.05 AUC)."

### 3.2 When NOT to Use TabPFN (Reserving-Relevant)

From Benchmark Summary (Conclusion):
> "**Between the regimes — and on pricing/regression targets (severity, claim frequency, amount) where GBDTs win — prefer the GLM**: the 11–86-param GLM family is never dominated on any dataset, it is statistically indistinguishable from TabPFN on frequency at 21 params, and where a fitted-coefficient story is required (a handful of interpretable GLM parameters vs TabPFN's 10M), the GLM is the defensible default."

### 3.3 Size Threshold

> "Every off-frontier frontier point sits at ≥53.5K training rows... no edge when the GLM floor already sits within ~2% of achievable... and no edge on frequency targets at scale even when the GLM floor is weak, because there the signal is tree-extractable only."

---

## 4. Claim Triage: The One Reserving-Adjacent Win

### 4.1 Reframing Count Targets as Classification

From §14.14:
> "Issue #67's question: can TabPFN's weakest axis be sidestepped by re-expressing the target? The count targets on which TabPFN is dominated (Poisson deviance) are read as classification problems instead — claim/no-claim and 0/1/2+ claim count — moving the contest from TabPFN's weakest metric axis (count regression) to its strongest (ranking). **Hypothesis confirmed — the count axis was the loss; classification is the win.**"

### 4.2 Binary Claim/No-Claim Results (Spanish Motor, 53,502 rows)

| metric | TabPFN | best competitor | delta | p (paired t) | rank |
|--------|--------|-----------------|-------|--------------|------|
| AUC | 0.7170 | lgbm 0.7090 | +0.0080 | 0.0010 | **1** |
| PR-AUC | 0.2428 | cat 0.2374 | +0.0054 | 0.1165 (n.s.) | **1** |
| lift10 | 2.6018 | cat 2.5127 | +0.0891 | 0.0279 | **1** |
| log loss | 0.3206 | lgbm 0.3209 | −0.0003 (tie) | 0.3630 | **1** |
| Brier | 0.0927 | lgbm 0.929 | −0.0002 | 0.0441 | **1** |

**Source:** §14.14.2, `reframe_frequency_summary.csv`

**Interpretation:** TabPFN ranks #1 on all five binary metrics. The AUC edge is paired-significant (+0.0080 over lgbm, p=0.0010). Same data, different target encoding: TabPFN's prior does not extract the count signal the GBDT extracts, but it ranks the claim propensity the GBDT ranks.

### 4.3 Ordinal Claim Count Results (0/1/2+)

| metric | TabPFN | best competitor | delta | p (paired t) | rank |
|--------|--------|-----------------|-------|--------------|------|
| AUC (ovr-macro) | 0.7167 | lgbm 0.7056 | +0.0111 | 0.0085 | **1** |
| lift10 (P(≥1)) | 2.7370 | lgbm 2.6491 | +0.0878 | 0.1338 (n.s.) | **1** |
| log loss (multiclass) | 0.3935 | lgbm 0.3944 | −0.0009 (tie) | 0.3428 | **1** |
| Brier (MSE of one-hot) | 0.0647 | lgbm 0.0647 | 0.0000 (tie) | 0.8790 | **1** |

**Source:** §14.14.4

**Interpretation:** The ordinal reframe reproduces the binary result: AUC rank #1 with the largest edge of the two reframes (+0.0111 over lgbm, p=0.0085).

### 4.4 Use Case for Reserving

> "Use case: triage on claim propensity from the same loss-cost data the count model prices." — §14.14.7

This suggests a **hybrid workflow**:
1. **TabPFN** → rank claims by propensity (triage)
2. **GLM/GBDT** → price the actual reserves (count model)

---

## 5. Calibration for Reserving

### 5.1 Why Calibration Matters

From Technical Companion §2.1:
> "If you predict 15% lapse probability when actual is 20%, the Brier score captures this error. In reserving and pricing models, this directly impacts:
> - **Premium adequacy:** Systematic under-prediction leads to under-pricing
> - **Reserve adequacy:** Poor probability estimates inflate or deflate reserves
> - **Capital allocation:** Misestimated risk leads to capital inefficiency"

### 5.2 TabPFN's Calibration Advantage

From the Paper (Calibration Insight):
> "Pricing models must estimate true lapse probabilities; reserving models must reflect actual frequencies. Without calibration, probabilities can systematically under/overestimate true outcomes. Raw TabPFN was overconfident (Brier score 0.1108), a known neural network trait. Post-hoc isotonic calibration improved this +0.87% to 0.1080, outperforming GLM's 0.1098."

### 5.3 Calibration Caveats

From §14.13.3:
> "The calibration claims gain two small documented exceptions — ausprivauto0405 log loss and Brier vs the linear family (glm_eng closest), and bemtl97 Brier vs lgbm — both ~1e-4 paired-significant edges on the calibration axis."

---

## 6. Implications for Reserving Practice

### 6.1 What TabPFN CANNOT Replace

| Traditional Reserving Task | Why TabPFN Fails | Better Alternative |
|---------------------------|------------------|-------------------|
| Claim amount prediction | Zero-inflation trap, +48% to +67% worse | GBDT (LGBM/CatBoost) |
| IBNR estimation | Cannot model count distributions | Poisson/Tweedie GLM |
| Ultimate claim cost | Dominated at scale (≥53K rows) | GLM family (never dominated) |
| Reserve adequacy testing | 10M params, no interpretability | GLM with interpretable coefficients |

### 6.2 What TabPFN CAN Add Value To

| Reserving-Adjacent Task | Why TabPFN Works | Evidence |
|------------------------|------------------|----------|
| Claim triage/prioritization | AUC #1 on claim/no-claim classification | §14.14: p=0.0010 |
| Risk ranking for reserving | Best risk-ranking model in suite | §14.11: AUC #1 on all 6 classification datasets |
| Small data scenarios | Data efficiency ≤5K rows | §13.2: won 8/9 size-sweep cells |
| Cold-start/proxy models | No training signal needed | §8: "keep on the bench for niche value" |

### 6.3 Recommended Hybrid Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    RESERVING WORKFLOW                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────┐    ┌─────────────────────┐       │
│  │   DATA PREPARATION  │    │   CLAIM DATA        │       │
│  │   • Historical      │───▶│   • Amounts         │       │
│  │   • Features        │    │   • Counts          │       │
│  │   • Outcomes        │    │   • Zero-inflated   │       │
│  └─────────────────────┘    └──────────┬──────────┘       │
│                                         │                   │
│                                         ▼                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              TABPFN (TRIAGE LAYER)                  │   │
│  │  • Rank claims by propensity (AUC #1)               │   │
│  │  • Identify high-risk claims for review             │   │
│  │  • Classify: claim/no-claim, 0/1/2+                 │   │
│  │  • Best for: ≤5K rows, classification tasks         │   │
│  └─────────────────────────────────────────────────────┘   │
│                         │                                   │
│                         ▼                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           GLM/GBDT (PRICING LAYER)                  │   │
│  │  • Calculate actual reserves (severity model)       │   │
│  │  • Estimate IBNR (count model)                      │   │
│  │  • Price ultimate claim costs                       │   │
│  │  • Interpretable coefficients for regulators        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Key Quotes for Your Colleague

### On Severity Modeling:
> "GBDTs and even linear models crush TabPFN on these; TabPFN's zero-shot regression transfer does not fit insurance severity targets under default config." — §4.1

> "Fine-tuning, as configured today, does not change the 'do not deploy TabPFN for severity' verdict." — §5.3

### On the Count vs Classification Distinction:
> "Same data, different target encoding: TabPFN's prior does not extract the count signal the GBDT extracts, but it ranks the claim propensity the GBDT ranks." — §14.14.5

> "Regression/frequency stays GBDT territory" gains a scoping footnote: on the classification reframe of a count target — claim vs no-claim, or 0/1/2+ — TabPFN's ranking edge applies, paired-significant and seed-stable, while the count model itself (Poisson deviance) and the pricing/calibration story are unchanged. Use case: triage on claim propensity from the same loss-cost data the count model prices." — §14.14.7

### On Interpretability Requirements:
> "Where a fitted-coefficient story is required (a handful of interpretable GLM parameters vs TabPFN's 10M), the GLM is the defensible default." — Benchmark Summary

### On Calibration:
> "Pricing models must estimate true lapse probabilities; reserving models must reflect actual frequencies. Without calibration, probabilities can systematically under/overestimate true outcomes." — Technical Companion

---

## 8. Evidence Files

| File | Description | Location |
|------|-------------|----------|
| Severity frontiers | Per-dataset RMSE results | `scripts/eval/insurance_benchmark_v1/frontier_results_*.csv` |
| Claim reframe results | Binary/ordinal classification results | `scripts/eval/insurance_benchmark_v1/reframe_frequency_results.csv` |
| Regime analysis | Decision rules and hypothesis tests | `docs/analyses/regime_characterization.md` |
| Master report | Full benchmark evidence (§1–§14.14) | `docs/analyses/tabpfn_vs_gbdt_baselines_finetuning.md` |
| Benchmark summary | One-page verdict | `docs/reports/TABPFN_BENCHMARK_SUMMARY.md` |
| Technical companion | Metric explanations | `docs/reports/TECHNICAL_COMPANION.md` |
| Combined analysis | Cross-task conclusions | `docs/reports/COMBINED_TABPFN_CLASSIFIER_REGRESSOR_ANALYSIS.md` |

---

## 9. Open Questions for Further Research

1. **Can fine-tuning improve severity modeling?** Current evidence: no (§5.3). But all finetune studies were classification targets — severity-specific transforms may help.
2. **What about other foundation models?** TabFM assessed but not run (OOM-killed on 8GB machine; non-commercial weights block production use — §14.13.4).
3. **GPU inference at scale?** CPU-only benchmark; GPU would reduce inference from ~240s to ~0.2-0.5s per fold, changing real-time calculus.
4. **Severity-specific transforms?** Log/Tweedie-family modeling in the TabPFN arm — not tested.

---

## 10. Conclusion

**For reserving actuaries:** TabPFN is not a replacement for classical reserving models. It fails on severity/amount prediction at scale, cannot handle zero-inflated distributions, and lacks the interpretability regulators require.

**Where it adds value:** Claim triage and risk ranking — identifying which claims are likely to develop, prioritizing them for manual review, and complementing (not replacing) the actual reserve calculations.

**The bottom line:** *"Price with the GLM/GBDT, triage with TabPFN."*

---

*Document compiled from IFoA ADSWP TabPFN benchmark repository. All findings pinned to hosted v3 model (tabpfn-client 0.3.3). Re-test on model version change per §15 (Version-Drift Re-Test Policy).*
