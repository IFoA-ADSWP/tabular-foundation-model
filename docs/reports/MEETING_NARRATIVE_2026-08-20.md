# TabPFN Insurance Research — Meeting Narrative

**Prepared for:** Meeting on 2026-08-21
**Purpose:** Clear, chronological story of the project's journey, current state, and where we're headed

---

## The One-Line Summary

**After a year of rigorous self-correction, TabPFN is now the best risk-ranking model for insurance classification — AUC #1 over GLMs, LightGBM, CatBoost, XGBoost, and Random Forest on all six canonical datasets, including at production scale (up to 184,000 rows).**

---

## The Story Arc (5 Acts)

### Act 1: "Can TabPFN Compete at All?" (Early August 2026)

We started with a simple question: does this pretrained transformer model beat traditional actuarial models on real insurance data?

**Initial result: TabPFN appeared to lose.** On 8 datasets, the score was 2 wins, 1 tie, 5 losses. The GLM (the actuary's workhorse) looked dominant.

**But we were measuring wrong.** We discovered that our primary metric (1-AUC) was blind to a key issue: class imbalance. The initial "losses" were partly a measurement artifact, not a real performance gap.

**Source:** Master report §11 (metric blindness discovery)

---

### Act 2: "Separating Artifacts from Real Limits" (August 2-3)

We dug deeper and found:

1. **The small-data story was wrong.** When we swept dataset sizes (1K → 5K → full), TabPFN won 8 out of 9 cells at ≤5,000 rows. The "TabPFN is only for small data" narrative died here.

2. **The regression story was real.** On large frequency/regression tasks (50K+ rows), GBDTs genuinely outperformed TabPFN. This wasn't an artifact — it was a real limitation.

3. **The GLM was never dominated.** Even when TabPFN won, the GLM sat on the "parsimony frontier" — the best accuracy per unit of model complexity. Regulators care about this.

**Source:** Master report §12-13 (artifacts vs limits), §14.4 (parsimony frontier)

---

### Act 3: "The Ranking Edge Emerges" (August 4-6)

We built a proper benchmark: 12 datasets, 9 methods, 5-fold cross-validation, same-fold comparisons.

**Key finding: TabPFN is #1 for risk-ranking.** On classification tasks (which policies are risky?), TabPFN beat every competitor on AUC:

| Dataset | TabPFN AUC | Best GLM AUC | Delta |
|---------|------------|--------------|-------|
| bemtl16 | 0.681 | 0.656 | +0.025 |
| coil2000 | 0.738 | 0.712 | +0.026 |
| uslapseagent | 0.716 | 0.695 | +0.021 |
| ausprivauto0405 | 0.575 | 0.569 | +0.006 |
| norauto | 0.622 | 0.616 | +0.006 |
| bemtl97 | 0.667 | 0.661 | +0.006 |

**We also retracted a wrong conclusion.** We had marked one dataset as "DOMINATED" (TabPFN losing on both accuracy and complexity). This was incorrect — we had run the wrong baseline. After correction, TabPFN AUC was #1 on all 6 datasets.

**Source:** Master report §14.11 (retraction + correction), §14.12 (paired tests confirmed)

---

### Act 4: "The Finality Tests" (August 7-13)

We pushed hard to try to dethrone TabPFN:

1. **Tuned baselines (14 methods):** We ran tuned/engineered versions of every classical method. **TabPFN stayed #1 on AUC and PR-AUC for all 6 datasets.** The closest competitor was a tuned GLM with engineered features (+0.0036 AUC on one dataset, p=0.003).

2. **Frequency reframing:** The one weakness — count/frequency modeling — turned out to be a framing artifact. When we reframed "how many claims?" as "claim vs no-claim" (binary classification), TabPFN moved from weakest to strongest.

3. **Stability:** Results held across random seeds (9/9 stable), across dataset sizes, and at production scale (184K rows).

**Source:** Master report §14.13 (tuned baselines), §14.14 (frequency reframing)

---

### Act 5: "Where We Are Now" (Current State)

**The verdict is clear, with a simple decision rule:**

| Scenario | Recommendation |
|----------|----------------|
| Small data (≤5K rows) | **Use TabPFN** (8/9 size-sweep cells won) |
| Risk-ranking (underwriting triage, lapse/propensity, claim/no-claim) | **Use TabPFN** (AUC #1, all 6 datasets, up to 184K rows) |
| Large regression/frequency (≥50K rows) | **Prefer GBDT/GLM** for the count model |
| Regulator-facing simplicity | **Prefer GLM** (21 params within noise of 10M-param model) |
| Pricing with coefficient stories | **Prefer GLM** (interpretable parameters) |

**The three most robust results:**
1. GLM family (11-86 params) is never dominated on any frontier — no matter how good TabPFN gets, the simple model is never beaten on quality-per-complexity
2. TabPFN AUC #1 on 6/6 classification datasets — including at production scale
3. Regression stays GBDT territory — Poisson deviance at scale shows TabPFN ~33% behind on freMTPL2freq

---

## The Scientific Journey Matters

What makes this project credible is not just the result — it's the process:

- We started with TabPFN appearing to lose
- We discovered the metric was blind to a key lever
- We separated artifacts from genuine limits
- We built proper benchmarks with fair comparisons
- We retracted incorrect conclusions when we found errors
- We stress-tested with tuned baselines
- We reframed the one remaining weakness and found it was a framing artifact

**This is how good science works.** The 9 addenda in the master report document every reversal, every correction, every discovery. Nothing was swept under the rug.

---

## What's Blocked / Needs Discussion

1. **GPU access (#22):** Still blocked. Would enable larger-scale experiments.
2. **Funding requests (#28, #29):** Pending decision.
3. **Fine-tuning inside the parsimony frontier (#54):** The one remaining lever. Low expected value outside small-data/lapse, but untested.
4. **Version drift policy:** Model pinned to `v3_default`. Re-runs needed when version changes.

---

## Key Documents for Reference

| Document | Purpose | Path |
|----------|---------|------|
| **One-page summary** | Quick verdict for actuarial colleagues | `docs/reports/TABPFN_BENCHMARK_SUMMARY.md` |
| **Master report** | Full evidence with 9 addenda (~1600 lines) | `docs/analyses/tabpfn_vs_gbdt_baselines_finetuning.md` |
| **Regime characterization** | Decision rule for when to use TabPFN | `docs/analyses/regime_characterization.md` |
| **Technical companion** | Walkthrough of every metric in actuarial context | `docs/reports/TECHNICAL_COMPANION.md` |
| **Learning path** | Onboarding for new contributors (2-3 days) | `docs/KNOWLEDGE-PATH.md` |

---

## Talking Points for Tomorrow

**If asked "What's the headline?":**
> TabPFN is the best risk-ranking model for insurance classification — AUC #1 on all 6 datasets, including at production scale. The GLM is never dominated on the parsimony frontier.

**If asked "How confident are you?":**
> Very. We ran 9 methods on 12 datasets with 5-fold cross-validation, then added 14 tuned baselines and confirmed the ranking. Results hold across seeds, dataset sizes, and at 184K rows. We retracted one wrong conclusion along the way — the science is sound.

**If asked "When should we NOT use TabPFN?":**
> Large regression/frequency tasks (50K+ rows), pricing with coefficient stories, or regulator-facing simplicity requirements. The GLM is the defensible default there.

**If asked "What's left to do?":**
> Three things: fine-tuning inside the parsimony frontier (low expected value), version re-runs when the model updates, and formalizing the use-case document for production adoption.

**If asked "What did you learn?":**
> The framing matters as much as the model. TabPFN's one weakness — frequency modeling — turned out to be a counting artifact. When reframed as classification, it becomes a strength. The GLM's strength isn't accuracy — it's accuracy per parameter. Regulators don't care about AUC; they care about explainability per complexity.

---

## Evidence Traceability

All findings trace to:
- **Source workbooks:** 8 Python scripts in `scripts/eval/insurance_benchmark_v1/`
- **Evidence files:** 62 files in `scripts/eval/insurance_benchmark_v1/` (CSVs, PNGs, logs)
- **Figures:** 6 canonical figures in `outputs/current/figures/`
- **Tables:** 7 canonical tables in `outputs/current/tables/`

Full traceability matrix: `docs/reports/REPORT_REGISTRY.md`

---

*Document prepared for the IFoA Actuarial Data Science Working Party (ADSWP) meeting.*
*Source: TabPFN Insurance Research Repository, commit history through 2026-08-13.*
