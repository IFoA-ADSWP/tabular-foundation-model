# Experiment Design: Insurance-Specialized TabPFN Fine-Tuning (v5)

> Date: 2026-09-11 | Status: draft (v5) | Related: #22, #129, #156
> Builds on: STAGE_A_B_FINDINGS_AND_RECOMMENDATIONS.md (v2 API-based)
> Diagnostic: COMPLETE — both datasets linear on Brier (see Pre-Experiment Diagnostic)



---

## Research Question

Does fine-tuning TabPFN on insurance data improve performance on **unseen insurance tasks** versus raw TabPFN and external insurance-specific baselines?

---

## External Evidence Assessment (v4 addition)

### What external research shows

**1. RealTabPFN-2.5 — already fine-tuned on real tabular data**

Izbicki & Rodrigues (arXiv:2603.26611, March 2026) benchmark three foundation models as conditional density estimators across 39 datasets at n=50 to n=20,000:

| Model | CDE Loss Rank at n=1,000 | CDE Loss Rank at n=20,000 |
|---|---|---|
| RealTabPFN-2.5 | 1st | 3rd |
| TabPFN-2.5 | 2nd | 1st |
| TabICL | 3rd | 2nd |

RealTabPFN-2.5 is TabPFN **already fine-tuned on curated real-world tabular datasets**. This is exactly what our design proposes to do for insurance specifically.

**Finding**: RealTabPFN-2.5 dominates at small n but **loses to raw TabPFN-2.5 at n=20,000**. Fine-tuning on real data helps for small datasets but can hurt at scale. Our design must test this crossover.

**2. Tab-TRM — insurance-specific architecture, already fine-tuned**

Padayachy, Richman, Wüthrich (arXiv:2601.07675, Jan 2026) introduce Tab-TRM, a transformer architecture **explicitly designed for insurance pricing** with:
- Poisson deviance loss (not cross-entropy)
- Exposure offset handling
- Fine-tuned on French MTPL data

Tab-TRM achieves out-of-sample Poisson deviance of 23.589 × 10^-2 on French MTPL with only 14,820 parameters — competitive with Gradient Boosted Machines.

**Finding**: An insurance-specific model already exists and beats GLM. Our experiment should **compare against Tab-TRM or cite it as the insurance-specific baseline**.

**3. Burning Cost practitioner assessment (March 2026)**

An honest assessment of tabular foundation models for insurance pricing:

> "XGBoost/CatBoost hold. Tab-TRM is the one to watch."

Key gaps identified:
- No insurance-specific benchmarks with UK motor/home datasets
- No validated production deployment of TabPFN for insurance
- "Promising laboratory result, no validated production deployment" phase

**Finding**: External community agrees that TabPFN fine-tuning for insurance is **promising but unvalidated**. Our experiment addresses this gap directly.

### Evidence summary

| Source | What it tells us | Implication for design |
|---|---|---|
| RealTabPFN-2.5 benchmarks | Fine-tuning helps at small n, may hurt at large n | Test crossover; don't assume fine-tuning always helps |
| Tab-TRM | Insurance-specific model already exists | Include as baseline or cite as state-of-the-art |
| Burning Cost | No validated insurance benchmarks | Our experiment is novel and needed |
| Stage A/B (our work) | All-other pooled fine-tuning hurt (v2 API) | v3 local weights may behave differently; test pool composition |

### Evidence gaps

- **No study fine-tunes TabPFN specifically on insurance data** and evaluates on held-out insurance tasks. RealTabPFN-2.5 uses general real-world data, not insurance-specific.
- **No study compares TabPFN fine-tuned on insurance vs. Tab-TRM**. This is the key competitive question.
- **No study tests TabPFN v3 fine-tuning** — our work extends v2 Stage A/B results to local CUDA weights.

---

## Context: Prior Work (Stage A/B)

Stage A/B tested domain fine-tuning with TabPFN v2 (remote API, client backend). Key findings:

- **Pooled all-other fine-tuning did NOT help overall** — aggregate deltas were negative (ROC AUC -0.05 to -0.07)
- **Dataset-level heterogeneity**: freMTPL2freq_binary benefited; EU Lapse, COIL 2000, Aus. Vehicle did not
- **Key recommendation**: build a "homogeneous pool" option using similarity checks (feature/schema overlap, event-rate proximity, validation transfer performance)
- **EU Direct Lapse**: GLM was strongest — the only dataset where raw TabPFN loses to GLM

**This experiment extends Stage A/B with TabPFN v3 (local weights, CUDA GPU) and adds external baselines.**

---

## Hypothesis

By fine-tuning TabPFN on insurance data that is **similar** to the target dataset, the model becomes specialized to insurance-domain structure and outperforms raw TabPFN on held-out insurance tasks.

**Based on external evidence, we further hypothesize:**
- Fine-tuning helps more at small n (aligned with RealTabPFN-2.5 crossover)
- Fine-tuned TabPFN is competitive with Tab-TRM on classification tasks (not regression — Tab-TRM is regression-optimized)

---

## Critical Insights

### From prior research
**Pool composition matters more than scale.** Naive all-other pooled fine-tuning can be WORSE than raw TabPFN due to cross-dataset domain mismatch.

### From external research
**RealTabPFN-2.5 shows fine-tuning helps at small n but may hurt at large n.** The fine-tuned model's prior can conflict with the data when n is large enough to override it.

### Combined implication
The optimal fine-tuning strategy is:
1. Select similar sources (homogeneous pool) — avoids hurting from mismatched data
2. Fine-tune — helps at small n where prior mismatch dominates
3. Test at multiple scales — find the crossover where fine-tuning stops helping

---

## Pre-Experiment Diagnostic: Results (v5)

### Problem

EU Direct Lapse was **level with GLM** in initial testing. If the insurance datasets are fundamentally **linear problems** (GLM ≈ best possible), then:

- TabPFN's transformer architecture has nothing to exploit
- Fine-tuning can't help because there's no latent pattern beyond what GLM captures
- You're paying compute to learn a linear function with a 100M-parameter model

### Diagnostic Results

Ran `scripts/diagnostic_complexity.py` on 3,500 rows of each dataset:

| Dataset | Rows | Features | GLM Brier | RF Brier | Delta | GLM ROC | RF ROC | Verdict |
|---|---|---|---|---|---|---|---|
| EU Direct Lapse | 3,500 | 62 | 0.1067 | 0.1078 | -0.001 | 0.657 | 0.632 | **LINEAR** |
| freMTPL2 Binary | 3,500 | 47 | 0.0485 | 0.0479 | +0.001 | 0.555 | 0.583 | **LINEAR** |

**Decision rule:** Delta (GLM Brier − RF Brier) < 0.005 = linear. Both datasets pass.

### Contradiction with Stage A/B

Stage A/B found domain-fine-tuned TabPFN was **strongest** on freMTPL2 (v2 API). The diagnostic says the problem is linear. Resolving this:

| Explanation | What it means | Action |
|---|---|---|
| **Metric mismatch** | Stage A/B used ROC; RF beat GLM on ROC (0.583 vs 0.555) but Brier shows no calibration improvement | The ROC gain may be ranking, not probability quality |
| **v2 vs v3** | Stage A/B used remote API (v2); local v3 weights may behave differently | The fine-tuning signal in v2 may not replicate in v3 |
| **Scale** | Diagnostic used 3K rows; Stage A/B may have used more | Non-linear structure may only emerge at larger n |

### Resolution

Both datasets show **linear structure on the primary metric (Brier)**. This means fine-tuning is **unlikely to add value** for probability quality. However:

1. **freMTPL2 has ROC signal** — RF beats GLM on ranking (0.583 vs 0.555). If the use case values ranking over calibration, fine-tuning may help.
2. **Stage A/B found signal in v2** — we should verify whether this replicates in v3 before concluding.
3. **The pilot is cheap** — $0 on Colab T4 for ~30 minutes. Worth running to confirm.

**Decision: Proceed with pilot, but with revised expectations.** Fine-tuning is unlikely to improve Brier on these linear datasets. If it does, that's a surprising positive result. If it doesn't, we've learned that TabPFN fine-tuning doesn't help linear insurance problems — a useful negative result.

---

## Datasets

| Dataset | Rows | Positive Rate | Role |
|---|---|---|---|
| **freMTPL2 Binary** | 50,000 | 5.02% | **Primary target** — fine-tuning showed signal in Stage A/B (v2); diagnostic shows linear on Brier but ROC signal exists |
| EU Direct Lapse | 23,060 | 12.81% | **Secondary target** — GLM ≈ RF (linear), fine-tuning unlikely to help |
| COIL 2000 | 9,822 | 5.97% | Pool candidate |
| Aus. Vehicle | 67,856 | 6.81% | Pool candidate |

---

## Split Policy

Two levels of splitting:

1. **Outer split (experiment level)** — applied BEFORE feeding to TabPFN:
   - 70/30 train/test stratified, seed=42
   - 15% of train held out as validation (for config selection)
   - Test set used exactly once per arm

2. **Inner split (TabPFN level)** — `get_preprocessed_dataset_chunks` does its own 80/20 internally for ensemble construction. This is automatic and does not affect the outer test set.

---

## Pool Composition Strategy

### Problem
All three pool candidates have materially lower event rates than EU Lapse (12.81%). The similarity table:

| Source Dataset | Positive Rate | Rate Delta to EU Lapse |
|---|---|---|
| freMTPL2 Binary | 5.02% | -7.8pp |
| COIL 2000 | 5.97% | -6.8pp |
| Aus. Vehicle | 6.81% | -6.0pp |

### Resolution: Tiered Homogeneous Selection

Since no single candidate is clearly homogeneous, we use a **validation transfer test**:

1. Fine-tune on each candidate **individually** (single-source pools)
2. Evaluate on EU Lapse **validation** set
3. Select only candidates where fine-tuned Brier < raw Brier on validation
4. The selected set = Arm D's homogeneous pool

If zero candidates pass → Arm D = Arm C (all-other) and the finding is: "no homogeneous insurance source for EU Lapse exists."

### Pool Sampling

For each pool dataset, sample proportionally to its row count (not uniform). Per-dataset cap: 10K rows.

---

## Experimental Arms

| Arm | Fine-tune data | Eval data | Tests |
|---|---|---|---|
| **A — Raw TabPFN** | none | all 4 datasets | Baseline |
| **B — In-domain** | freMTPL2 (train) | freMTPL2 (test) | Does in-domain help? |
| **C — All-other pooled** | EU Lapse + COIL + Aus. Vehicle | freMTPL2 (held-out) | Does ANY insurance help? |
| **D — Homogeneous pooled** | candidates passing transfer test | freMTPL2 (held-out) | Does MATCHED insurance help? |
| **E — GLM baseline** | — | all 4 datasets | Linear baseline |
| **F — CatBoost baseline** | — | all 4 datasets | Tree baseline |

### Arm Interpretation

| Outcome | Meaning |
|---|---|
| C wins, D wins | Any insurance fine-tuning helps |
| C loses, D wins | Only matched/similar insurance data helps (similarity gate) |
| C loses, D loses | Fine-tuning doesn't help for EU Lapse in v3 either |
| B wins, C/D lose | Only in-domain memorization, not transferable |
| D > E and D > F | Fine-tuned TabPFN is competitive with tuned baselines |

---

## Config Grid

Matches Stage A/B for comparability:

| Parameter | Values |
|---|---|
| context_samples | 64, 128 |
| max_finetune_steps | 1, 3, 5 |
| n_estimators | 8 |
| learning_rate | 1e-5 (default) |
| fit_mode | "batched" |

n_estimators=8 is production quality (vs Stage A/B's n_estimators=2). If R1 shows OOM, fall back to n_estimators=2.

---

## Pilot Strategy

**Phase 1a — Pilot (run first):**
- Rung: R1 only
- Arms: A, B, C, D (with single-source transfer test), E, F
- Config: context=64, steps=3 only
- Seeds: 42 only
- **Target: freMTPL2 Binary capped at 5K rows** (memory safety; primary target per diagnostic)
- Expected duration: ~30 min on T4

**Phase 1b — Expand (only if pilot shows signal):**
- Add rungs R2, R3
- Add configs: context=128, steps=1,5
- Add seeds: 1337, 2025
- Target: full EU Lapse (23K rows, if memory allows)

**Phase 1c — Full (only if 1b confirms signal):**
- Full grid: all arms × rungs × configs × seeds
- Add other datasets as secondary targets (freMTPL2, COIL, Aus. Vehicle)

---

## Rung Definitions

| Rung | Fine-tune Pool N | Target Train N | Target Test N | Device |
|---|---|---|---|---|
| R1 | 2K (subsample pool, proportional) | 5K (EU Lapse subsample) | 3K | Colab T4 (free) |
| R2 | 10K (pool) | 10K | 6K | Colab T4 (free) |
| R3 | Full pool (~127K) | Full EU Lapse (16K) | 7K (30% of 23K) | Colab T4 / Vast RTX 4090 |

### Memory Safety

EU Lapse at 23K rows with context=128 and n_estimators=8 may exceed T4's 16 GB VRAM. Mitigation:
- R1 caps target at 5K rows
- R2 caps target at 10K rows
- R3 only runs if R2 completes without OOM; if OOM on T4, move to Vast RTX 4090 (24 GB)

---

## R3 Gate

Proceed to R3 if **any** of the following hold in R2 (seed 42):
- Arm B Brier < Arm A Brier (in-domain helps)
- Arm C Brier < Arm A Brier (all-other helps)
- Arm D Brier < Arm A Brier (homogeneous helps)

If none hold, stop at R2 and report: "fine-tuning does not improve over raw TabPFN for insurance tasks in v3."

---

## Metrics (primary first)

All computed offline from persisted predictions — add/swap metrics without re-running.

1. **Brier score** (primary — project's established probability-quality metric)
2. **ROC AUC** (discrimination — where GLM beats TabPFN)
3. **PR AUC** (imbalanced-target discrimination)
4. **Log loss** (probabilistic calibration)
5. **ECE** (expected calibration error)

---

## Persistence Strategy

For each arm × rung × seed × config:

```
outputs/finetune/
├── arm_A_raw/
│   ├── predictions_c64_s3_seed42_r1.npy
│   └── meta_c64_s3_seed42_r1.json
├── arm_B_in_domain/
│   ├── model_c64_s3_seed42_r1.tabpfn_fit
│   ├── predictions_c64_s3_seed42_r1.npy
│   └── meta_c64_s3_seed42_r1.json
├── arm_C_all_other_pooled/
│   ├── model_c64_s3_seed42_r1.tabpfn_fit
│   ├── predictions_c64_s3_seed42_r1.npy
│   └── meta_c64_s3_seed42_r1.json
├── arm_D_homogeneous_pooled/
│   ├── model_c64_s3_seed42_r1.tabpfn_fit
│   ├── predictions_c64_s3_seed42_r1.npy
│   └── meta_c64_s3_seed42_r1.json
├── arm_E_glm/
│   ├── predictions_c64_s3_seed42_r1.npy
│   └── meta_c64_s3_seed42_r1.json
└── arm_F_catboost/
    ├── predictions_c64_s3_seed42_r1.npy
    └── meta_c64_s3_seed42_r1.json
```

### Metadata Schema

```json
{
  "arm": "B",
  "rung": "R1",
  "config": {"context_samples": 64, "max_finetune_steps": 5, "n_estimators": 8, "learning_rate": 1e-5},
  "seed": 42,
  "target_dataset": "eudirectlapse",
  "target_train_rows": 5000,
  "target_test_rows": 3000,
  "pool_datasets": ["eudirectlapse"],
  "pool_total_rows": 5000,
  "pool_per_source": {"eudirectlapse": 5000},
  "device": "cuda",
  "device_name": "Tesla T4",
  "gpu_time_seconds": 45.2,
  "peak_vram_bytes": 8589934592,
  "wall_time_seconds": 52.1,
  "status": "success",
  "error": null,
  "timestamp": "2026-09-11T12:00:00Z",
  "tabpfn_version": "3.x.x",
  "python_version": "3.13.0"
}
```

### Failure Handling

If `fit_from_preprocessed` raises or returns non-finite loss:
- Set `status: "failed_nonfinite"`
- Log error message in `error` field
- Continue to next config (don't abort the run)
- Report failure rate per arm in results

---

## Success Criteria

| Criterion | Threshold |
|---|---|
| Arm D > Arm A (raw) | Brier improves on EU Lapse (homogeneous transfer works) |
| Arm D > Arm C (all-other) | Homogeneous pool beats naive pooling |
| Arm B > Arm A | In-domain fine-tuning helps (baseline expectation) |
| Arm D > Arm E (GLM) | Fine-tuned TabPFN beats GLM on EU Lapse |
| Arm D > Arm F (CatBoost) | Fine-tuned TabPFN competitive with tuned tree |

### Reporting Format

Summary table per arm (mean ± std across seeds):

| Arm | Brier | ROC AUC | PR AUC | Log loss | ECE |
|---|---|---|---|---|---|
| A (raw) | 0.1080 ± 0.001 | 0.586 ± 0.003 | 0.172 ± 0.002 | 0.310 ± 0.002 | 0.045 ± 0.001 |
| B (in-domain) | ... | ... | ... | ... | ... |

Paired delta table (fine-tuned minus raw):

| Comparison | ΔBrier | ΔROC | Significant? |
|---|---|---|---|
| B - A | -0.002 | +0.005 | yes (p<0.05) |
| C - A | +0.001 | -0.003 | no |

---

## Budget

| Item | Cost |
|---|---|
| Phase 1a (pilot, R1, seed 42, 1 config, 6 arms) | $0 (free T4, ~30 min) |
| Phase 1b (expand, R1-R2, 3 seeds, 6 configs) | $0 (free T4, ~2 hrs) |
| Phase 1c (full, R1-R3, 3 seeds, 6 configs, 6 arms) | ~$5-10 (Vast RTX 4090 if needed) |
| Total worst case | ~$10 |

---

## GPU Access

Smoke test passed on Colab T4 (see #156, 2026-09-11). Time-per-sample: 1.8ms. Full pipeline proven.

---

## Phase 2 (deferred — only if Phase 1 shows fine-tuning helps)

These are NOT part of the initial experiment. Deferred to avoid confounding.

| Technique | What it does | When to use |
|---|---|---|
| **Synthetic dataset generation** | Generate insurance-like tabular data to augment the fine-tune pool | If Phase 1 shows fine-tuning helps but real data is too small |
| **TabPFN embeddings** | Use transformer internal representations as features for similarity scoring or other models | If Phase 1 needs better similarity metric for homogeneous pool selection |
| **Calibration (isotonic/Platt)** | Post-hoc probability calibration on top of fine-tuned model | If Phase 1 shows fine-tuning improves ranking but not calibration |
| **Alternative context/epoch regimes** | Longer training (epochs 10-50), larger context (256+) | If Phase 1 shows signal but not enough |
| **Regression extension** | Repeat design with TabPFNRegressor on continuous insurance targets (Exposure, ClaimNb) | If Phase 1 classifier results justify |
| **Tab-TRM comparison** | Benchmark fine-tuned TabPFN against Tab-TRM (insurance-specific architecture) | If Phase 1 shows fine-tuning helps — Tab-TRM is the competitive bar |

---

## Risks

| Risk | Mitigation |
|---|---|
| No homogeneous source exists for EU Lapse | Arm D falls back to Arm C; report defines when fine-tuning is/isn't applicable |
| EU Lapse 23K OOMs on T4 (16 GB) | Cap target at 5K/10K for R1/R2; move R3 to Vast RTX 4090 (24 GB) |
| Colab quota exhausted | Fall back to M1 MPS for R1/R2; Vast for R3 |
| Pooled fine-tuning hurts (replicates Stage A/B) | Report as v3 confirmation |
| Non-finite losses | Log as `failed_nonfinite`, continue, report failure rate |
| n_estimators=8 OOMs | Fall back to n_estimators=2 with note |
| API drift (v3 vs v2 results) | Note version explicitly; don't compare across versions |

---

## Deliverables

- `scripts/run_finetune_experiment.py` — parameterized runner (arm, pool, N, context, steps, device, seed)
- `scripts/analyze_finetune_results.py` — computes metrics from persisted predictions, generates summary tables
- `outputs/finetune/` — persisted models, predictions, metadata per arm/rung/seed/config
- `docs/reports/FINE_TUNING_EXPERIMENT_RESULTS.md` — results per rung, arm, dataset with paired deltas
- `docs/reports/FINE_TUNING_EXPERIMENT_DESIGN.md` — this document

---

## Evidence Assessment: Do We Have Enough?

### Sufficient evidence to proceed
- Stage A/B (our work): pool composition matters, all-other hurts, homogeneous may help
- RealTabPFN-2.5 benchmarks: fine-tuning helps at small n, crossover exists
- Burning Cost: no validated insurance benchmarks — gap exists

### Insufficient evidence
- **No study fine-tunes TabPFN specifically on insurance data** for held-out insurance evaluation
- **No study compares TabPFN fine-tuning vs. Tab-TRM** for classification
- **v3 local weight fine-tuning is untested** — Stage A/B used v2 API

### Verdict
**Proceed.** The evidence strongly suggests:
1. Fine-tuning CAN help if pool composition is right (homogeneous)
2. The effect likely depends on n (small n helps, large n may not)
3. No one has done this specifically for insurance classification

The experiment is well-motivated, the design addresses all blockers, and the cost is near-zero for the pilot phase.
