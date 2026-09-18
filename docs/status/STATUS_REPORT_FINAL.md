> **SUPERSEDED** — this report's findings are fully covered by docs/archive/POST_HOC_OPTIMISATION.md and docs/archive/COMBINED_TABPFN_CLASSIFIER_REGRESSOR_ANALYSIS.md (identical numbers). Kept for historical reference. Do not cite as current.

# TabPFN Research Status Report (Refined)

## Purpose

This document is the current source of truth for what was tested, what was learned, and what should be deployed for the TabPFN lapse-modeling work.

Scope covered:
- Baseline model comparison (GLM, TabPFN, CatBoost, RandomForest, XGBoost)
- Post-hoc optimization for TabPFN (calibration, feature engineering, ensembling)
- Deployment recommendation based on actuarial business priorities

---

## Validated Findings

### 1. Discrimination performance is tightly clustered

From the controlled comparison, GLM and TabPFN are close on ROC AUC:
- GLM: 0.5991
- TabPFN: 0.5929

Interpretation:
- On this dataset, modern foundation modeling does not materially beat a strong classical baseline on raw discrimination.
- Complexity alone does not guarantee lift.

### 2. Calibration is the main TabPFN opportunity

Post-hoc calibration improved TabPFN probability quality:
- Raw TabPFN Brier: 0.109678
- Best optimized variant Brier: 0.107982
- Relative improvement: +1.66%

Interpretation:
- For pricing and reserve use-cases, this is the most business-relevant win.
- Isotonic calibration was consistently stronger than Platt scaling in this workflow.

### 3. Ensemble bagging did not help

3-member bagging degraded results in these tests.

Interpretation:
- Additional averaging did not create useful diversity for this TabPFN setup.
- Keep the production path simple: single model + calibration.

---

## Recommended Deployment Decision

Deploy this variant first:

`TabPFN (Engineered Features) -> Isotonic Calibration`

Why:
- Best observed Brier performance
- Zero additional infrastructure cost
- Low operational complexity
- Directly aligned to actuarial probability-quality needs

Rollback trigger:
- Revert to current baseline if monitored Brier exceeds 0.110 for sustained periods.

---

## Repository Restructuring Required

A proposed restructuring of then-orphaned quick-reference docs was not carried out; the referenced files were never committed to this repository.

---

## What Was Updated In This Refinement

- Re-centered this report on research findings rather than editorial process details.
- Added explicit deployment recommendation and rollback rule.

---

## Linked Core Files

The long-form paper and supporting documents referenced by this status report live outside this repository and were never committed here.

---

## Next Actions

1. Keep this file as the short executive research status.
2. Archive non-canonical supporting docs to reduce maintenance overhead.
3. Continue production monitoring for calibration drift after deployment.

Report date: 2026-03-29
