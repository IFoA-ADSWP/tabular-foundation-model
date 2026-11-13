# Frontier Benchmark

> **Status:** index — this campaign's reading order, not a report of its own.

The 2026-07→08 frontier suite: the benchmark that produced master report §14, its re-scores, and the v3.5 re-test.

**8 documents.** Read them in the order below; each declares its own status, and a document
marked reference or historical is kept for provenance rather than as the current answer.

| Document | Status | What it holds |
| --- | --- | --- |
| [`altmetrics_rescore_spec.md`](altmetrics_rescore_spec.md) |  | Alternative-Metrics Re-score for Regression Benchmarks — Design Spec |
| [`benchmark_portfolio.md`](benchmark_portfolio.md) |  | Benchmark Portfolio — Custom Insurance Benchmarks Index |
| [`class_imbalance_analysis_summary.md`](class_imbalance_analysis_summary.md) | reference — a 2026-08 analysis note; w | Class Imbalance Analysis: Effects on TabPFN and Baseline Model Performance |
| [`frontier_auc_brier_rescore_spec.md`](frontier_auc_brier_rescore_spec.md) |  | Frontier AUC/Brier Re-score — Design Spec |
| [`insurance_frontier_benchmark_spec.md`](insurance_frontier_benchmark_spec.md) |  | Insurance Frontier Benchmark — Design Spec |
| [`prediction_capture_rescore_spec.md`](prediction_capture_rescore_spec.md) |  | Prediction Capture for Retrospective Re-scoring — Design Spec |
| [`regime_characterization.md`](regime_characterization.md) | current as of 2026-11-13 — the adoptio | Regime Characterization — When Default TabPFN Wins (Issue #53) |
| [`tabpfn_vs_gbdt_baselines_finetuning.md`](tabpfn_vs_gbdt_baselines_finetuning.md) | current as of 2026-11-13 — the master  | TabPFN vs GBDT Baselines on Insurance Datasets, and Domain Fine-Tuning Effectiveness |

## Runs

The v3.5 re-test (§16 of the master report) captured four runs. The benchmark's own results are the CSVs beside
its runner in `scripts/eval/insurance_benchmark_v1/`; these are the re-test captures.

```
20260916-102642
20260916-103015
20260916-103346
20260916-120029
```
