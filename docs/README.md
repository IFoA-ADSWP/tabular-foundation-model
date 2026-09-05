# Docs Index — what to read, in what order

45 docs (this index included). Start from your role, not the file list. Every finding is version-pinned — see [MODEL_VERSIONS.md](MODEL_VERSIONS.md) before citing a number.

## Start here by role

| You are… | Read in order |
|---|---|
| Junior data scientist | `KNOWLEDGE-PATH-JUNIOR.md` → `analyses/metrics_explained.md` → `reports/CODE_WALKTHROUGH.md` → `MASTER-REPORT-DIGEST.md` |
| Actuary (do I adopt this?) | `reports/TABPFN_BENCHMARK_SUMMARY.md` → `analyses/metrics_explained.md` → `analyses/regime_characterization.md` → `reports/RESERVING_WITH_FOUNDATIONAL_MODELS.md` |
| Engineer (how does it run?) | `reports/CODE_WALKTHROUGH.md` → `REPRODUCIBILITY_RUNBOOK.md` → `MODEL_VERSIONS.md` → `reports/REPORT_REGISTRY.md` |
| Contributor (how do I add work?) | `KNOWLEDGE-PATH.md` → `REPRODUCIBILITY_RUNBOOK.md` → `reports/REPORT_REGISTRY.md` → `MODEL_VERSIONS.md` (re-test policy §15) |
| Replicator (paper numbers) | `REPLICATION_SETUP_GUIDE.md` → `papers/APPENDIX_REPRODUCIBILITY.md` → `papers/Theres-Life-in-the-Old-GLM-Yet.md` |

## Era legend

- **Scripts era (current, v3):** `scripts/eval/`, `scripts/benchmarks/`, hosted API (`tabpfn-client` 0.3.3, `v3_default`). Verdicts live here.
- **Notebook era (legacy, v2):** `notebooks/baseline_experiments/01–08` + `src/`, laptop runs, `outputs/current/`. Historical arc; banners mark validity. See `KNOWLEDGE-PATH.md` "two eras" and `REPRODUCIBILITY_RUNBOOK.md` §B.

## On-ramps & how the code runs

| Doc | Audience | Era | Purpose |
|---|---|---|---|
| `KNOWLEDGE-PATH-JUNIOR.md` | Junior | Both | 2-week run-first on-ramp; graduation = question → skill → experiment → report → registry |
| `KNOWLEDGE-PATH.md` | All | Both | Full staged map from new joiner to extending the research |
| `reports/CODE_WALKTHROUGH.md` | Engineer | Scripts | `run_frontier_benchmark.py` step by step (2026-08-20) |
| `REPRODUCIBILITY_RUNBOOK.md` | Engineer | Both | Every committed result → exact command; separate frontier-era and legacy sections |
| `MODEL_VERSIONS.md` | All | Both | v2 → v2.5 → v3 timeline, what flipped, per-artifact validity, re-test rule |
| `REPLICATION_SETUP_GUIDE.md` | Replicator | Notebook | Paper replication notebook setup (v2-era, seed 45) |

## Verdicts (what we found — read newest first)

| Doc | Audience | Era | Purpose |
|---|---|---|---|
| `reports/TABPFN_BENCHMARK_SUMMARY.md` | Actuary | Scripts/v3 | One-page adoption answer + decision rule |
| `MASTER-REPORT-DIGEST.md` | All | Scripts/v3 | Addendum arc §4→§14.14 in one paragraph each — the 5-minute story |
| `analyses/tabpfn_vs_gbdt_baselines_finetuning.md` | Technical | Scripts/v3 | Master report: full evidence, §§1–14.14 |
| `analyses/regime_characterization.md` | Actuary | Scripts/v3 | When default TabPFN wins — predictive adoption rule |
| `analyses/benchmark_portfolio.md` | Colleague | Both | Living index of every benchmark: question, finding, evidence location |
| `reports/MEETING_NARRATIVE_2026-08-20.md` | Stakeholder | Scripts/v3 | Chronological project story for the 2026-08-21 meeting |
| `reports/RESERVING_WITH_FOUNDATIONAL_MODELS.md` | Actuary | Scripts/v3 | Reserving-task findings compiled from the benchmark suite |

## Methods & metrics explainers

| Doc | Audience | Era | Purpose |
|---|---|---|---|
| `analyses/metrics_explained.md` | Actuary | Both | Log loss vs AUC vs Brier: what each rewards, which to use for which decision |
| `analyses/tabular_foundation_models_catalog.md` | Technical | Both | All known tabular foundation models (excludes per-dataset-trained nets) |
| `reports/TECHNICAL_COMPANION.md` | Junior | Notebook/v2 | Metrics + GLM comparison explainer (v2-era numbers — see banner) |
| `analyses/tabarena_reference.md` | Technical | — | TabArena background (51 IID + 142 BeyondArena sets, NeurIPS spotlight) |
| `analyses/tabarena_insurance_benchmark_direction.md` | Technical | Scripts/v3 | What we learned from TabArena; direction for our insurance benchmark |
| `analyses/cpu_model_feasibility.md` | Engineer | Scripts/v3 | Which TabArena method families are usable with no GPU |
| `analyses/levers_assessment.md` | Technical | Scripts/v3 | Scoping: fine-tuning, HPO, ensembling (no new runs, 2026-08-04) |
| `analyses/class_imbalance_analysis_summary.md` | Technical | Notebook | Imbalance effects; null result confirmed by master §11 |

## Design specs (proposed → implemented trail)

| Doc | Status | Purpose |
|---|---|---|
| `analyses/insurance_frontier_benchmark_spec.md` | Agreed/executed (#27, PR #51) | Frontier benchmark D1–D5 |
| `analyses/frontier_auc_brier_rescore_spec.md` | Implemented 2026-08-06 | AUC/Brier power columns; delivered §14.11 |
| `analyses/prediction_capture_rescore_spec.md` | Proposed (#122) | Persisted per-fold predictions for retrospective re-scoring |
| `analyses/altmetrics_rescore_spec.md` | Proposed (#123) | Gamma/Tweedie/MAE from stored predictions, no refits |

## Legacy reports (v2-era — see banners, cite via MODEL_VERSIONS)

| Doc | Purpose |
|---|---|
| `reports/COMBINED_TABPFN_CLASSIFIER_REGRESSOR_ANALYSIS.md` | Consolidated classifier + regressor findings |
| `reports/MULTI_DATASET_GLM_VS_TABPFN_SUMMARY.md` | Multi-dataset GLM vs TabPFN (non-technical) |
| `reports/POST_HOC_OPTIMISATION.md` | Calibration/optimisation summary |
| `reports/STAGE_A_B_FINDINGS_AND_RECOMMENDATIONS.md` | Stage A/B short report |
| `reports/TABPFN_FINE_TUNING_LIMIT_STUDY.md` | Apple-Silicon finetune limits (classifier-only) |
| `reports/INSURANCE_DOMAIN_FINETUNING_METHOD_PROTOCOL.md` | Domain finetune method protocol |
| `reports/INSURANCE_SPECIFIC_FINETUNING_EVIDENCE.md` | Insurance finetune evidence review |
| `reports/CLASSIFIER_HOMOGENEITY_HYPOTHESIS_METHOD.md` | Homogeneity-hypothesis method + evaluation |
| `reports/REPORT_REGISTRY.md` | Registry: topic keys → workbooks → evidence files (+ `model_version`) |

## Papers & follow-ups

| Doc | Purpose |
|---|---|
| `papers/Theres-Life-in-the-Old-GLM-Yet.md` | Round-1 single-dataset paper (v2.0 era — historical record, see status note) |
| `papers/APPENDIX_REPRODUCIBILITY.md` | Reproducibility package for round-1 results |
| `papers/FOLLOW_UP_ROUND2_JOURNAL_SHORT.md` | Round-2 short journal format (multi-dataset + regression) |
| `papers/FOLLOW_UP_ROUND2_JOURNAL_PLAIN.md` | Round-2 plain-English summary |
| `analyses/tabpfn_small_finetune_methodology.md` | Small classifier finetune methodology |
| `analyses/tabpfn_finetune_limit_test_plan.md` | Finetune limit test plan (classifier-only) |

## Ops & history (read only if you need them)

| Doc | Purpose |
|---|---|
| `analyses/merge_plan_tabarena.md` | TabArena branch staged merge plan — MERGED 2026-08-04, coordination record |
| `sessions/2026-07-28-tabarena-benchmark-setup.md` | Session log: TabArena setup first step |
| `status/STATUS_REPORT_FINAL.md` | SUPERSEDED — kept for history, do not cite |
| `status/SECURITY_INCIDENT_RESOLVED.md` | 2024 HF token exposure — resolved/remediated |
| `REPLICATION_SETUP_GUIDE.md` | (listed above) paper replication setup |

## Outside docs/

- **Skills (the junior loop's execution step):** `.github/skills/` + `.opencode/` runbooks — see `KNOWLEDGE-PATH-JUNIOR.md` for which skill maps to which task.
- **Reproducibility notebooks:** `notebooks/reproducibility/README.md` (referenced by runbook §§A.7–A.9).
- **Live benchmark code:** `scripts/eval/insurance_benchmark_v1/`, `scripts/benchmarks/`.
