# Docs Index — what to read, in what order

Start from your role, not the file list. Deliberately no document count here: this index held a stale one for as long as the work outgrew it, and a number nobody checks is a claim waiting to be false. Every finding is version-pinned — see [MODEL_VERSIONS.md](MODEL_VERSIONS.md) before citing a number.

## How this documentation is organised

Every report declares **one tier** in its first lines. Nothing is moved, so no link breaks; the tier says what
the document is worth to you now.

| Tier | Means | Where it lives |
| --- | --- | --- |
| **current** | describes the design as built, the current answer, or a rule still in force | read it; cite it |
| **reference** | historical, still cited for provenance — the protocol, the measurement, the rejected option | read it when tracing a decision |
| **archive** | kept for the record, not cited | read it only for history |

**The current line of work, by tier.**

- **current** — `docs/current/FINETUNING_PILOT_DESIGN.md` (canonical proposal) · `docs/current/FINETUNING_STATUS_BRIEF.md` · `docs/current/FINETUNING_FINDINGS.md` · `docs/current/FINETUNING_DIAGNOSTICS_DESIGN.md` · `docs/current/FINETUNING_EXECUTION_RUNBOOK.md` · `docs/current/FINETUNING_COST_AND_CONTROLS.md` · `docs/current/FINETUNING_STATISTICAL_ANALYSIS_PLAN.md` · `docs/current/FINETUNING_DECISION_LOG.md` · `docs/current/FINETUNING_PREREQUISITES.md` · `docs/current/FINETUNING_PROBE_RESULTS.md` · `docs/current/FINETUNING_LITERATURE.md`
- **historical** — `docs/archive/PILOT_2_BRIEFING.md`
- **reference** — `docs/reference/PROBE_PLAN.md` · `docs/reference/PROBE_FIRST_RUN.md` · `docs/reference/PILOT_2_DESIGN.md` · `docs/reference/PILOT_2_DESIGN_ALTERNATIVE.md` · `docs/reference/PILOT_2_DECISION_GRAPH.md` (its step 0 fired) · `docs/reference/FINE_TUNING_PILOT_RESULTS.md` · the five v2-era fine-tuning pages listed in the literature record
- **archive** — everything in the legacy tables further down this file: the earlier benchmark, analysis and session documents.

**The rule for adding a document:** it enters as **current** only if it carries content nothing else carries; otherwise it is `reference` from the start. When a current document stops being current it is amended with a dated note and its tier changes — never deleted, because the trail is the point.

**Enforcement.** `scripts/check_doc_status.py` asserts that every report declares a status in its first fifteen lines. **27 of 33 reports do not yet**, which is the backfill this structure makes visible rather than fixes by reorganisation.

## Start here — the current line of work (fine-tuning on lapse data)

Everything below indexes the whole repository. **If you are here for the fine-tuning programme, read these first.**

| Question | Document |
| --- | --- |
| What is being proposed, and why | `docs/current/FINETUNING_PILOT_DESIGN.md` — the canonical funded proposal and decision framework |
| What is the short stakeholder summary? | `docs/current/FINETUNING_STATUS_BRIEF.md` |
| What did the probes actually find? | `docs/current/FINETUNING_PROBE_RESULTS.md` — the 2,000-row result is superseded by the 10,000-row measurement |
| What diagnostics are planned? | `docs/current/FINETUNING_DIAGNOSTICS_DESIGN.md` — Phase 1 methods |
| What does the evidence registry say? | `docs/current/FINETUNING_FINDINGS.md` — current versus superseded claims |
| What does the execution runbook contain? | `docs/current/FINETUNING_EXECUTION_RUNBOOK.md` — commands and acceptance procedure |
| What did it cost? | `docs/current/FINETUNING_COST_AND_CONTROLS.md` — measured anchors and cost controls |
| What is the statistical plan? | `docs/current/FINETUNING_STATISTICAL_ANALYSIS_PLAN.md` |
| Where is the technical history? | `docs/current/FINETUNING_EXPERIMENT_REFERENCE.md` and `docs/reference/` |
| Where is the raw evidence? | `../outputs/gpu-pilot/` — records, logs, manifests, and per-arm predictions under `runs/<run_id>/` |

**Eras.** R1 (first pilot, no reliable gain) → Pilot 2 (the wider staged proposal) → the probe (2,000 rows, negative) → **the current funded diagnostics and full pilot**, where the row cap was lifted to 10,000 and every fine-tuning rung beat raw with intervals excluding zero. Earlier-era documents carry a status banner; where a banner and a front section disagree, the canonical pilot design wins.

The report-level index is `docs/REPORT_REGISTRY.md` and is deliberately not restated here, so there is exactly one place to update when a report is added.

## Start here by role

| You are… | Read in order |
|---|---|
| Junior data scientist | `KNOWLEDGE-PATH-JUNIOR.md` → `analyses/metrics_explained.md` → `docs/archive/CODE_WALKTHROUGH.md` → `MASTER-REPORT-DIGEST.md` |
| Actuary (do I adopt this?) | `docs/archive/TABPFN_BENCHMARK_SUMMARY.md` → `analyses/metrics_explained.md` → `analyses/regime_characterization.md` → `docs/archive/RESERVING_WITH_FOUNDATIONAL_MODELS.md` |
| Engineer (how does it run?) | `docs/archive/CODE_WALKTHROUGH.md` → `REPRODUCIBILITY_RUNBOOK.md` → `MODEL_VERSIONS.md` → `docs/REPORT_REGISTRY.md` |
| Contributor (how do I add work?) | `KNOWLEDGE-PATH.md` → `REPRODUCIBILITY_RUNBOOK.md` → `docs/REPORT_REGISTRY.md` → `MODEL_VERSIONS.md` (re-test policy §15) |
| Replicator (paper numbers) | `REPLICATION_SETUP_GUIDE.md` → `archive/papers/APPENDIX_REPRODUCIBILITY.md` → `archive/papers/Theres-Life-in-the-Old-GLM-Yet.md` |

## Era legend

- **Fine-tuning / lapse era (current):** `scripts/run_pilot.py`, `scripts/analyse_pilot.py`,
  `scripts/gpu_helpers/`, `outputs/gpu-pilot/`. Owns the fine-tuning question; see the section at the
  top of this file.
- **Scripts era (v3, predecessor line):** `scripts/eval/`, `scripts/benchmarks/`, hosted API (`tabpfn-client` 0.3.3, `v3_default`). Verdicts live here.
- **Notebook era (legacy, v2):** `notebooks/baseline_experiments/01–08` + `src/`, laptop runs, `outputs/current/`. Historical arc; banners mark validity. See `KNOWLEDGE-PATH.md` "two eras" and `REPRODUCIBILITY_RUNBOOK.md` §B.

## On-ramps & how the code runs

| Doc | Audience | Era | Purpose |
|---|---|---|---|
| `KNOWLEDGE-PATH-JUNIOR.md` | Junior | Both | 2-week run-first on-ramp; graduation = question → skill → experiment → report → registry |
| `KNOWLEDGE-PATH.md` | All | Both | Full staged map from new joiner to extending the research |
| `docs/archive/CODE_WALKTHROUGH.md` | Engineer | Scripts | `run_frontier_benchmark.py` step by step (2026-08-20) |
| `REPRODUCIBILITY_RUNBOOK.md` | Engineer | Both | Every committed result → exact command; separate frontier-era and legacy sections |
| `MODEL_VERSIONS.md` | All | Both | v2 → v2.5 → v3 timeline, what flipped, per-artifact validity, re-test rule |
| `REPLICATION_SETUP_GUIDE.md` | Replicator | Notebook | Paper replication notebook setup (v2-era, seed 45) |

## Verdicts (what we found — read newest first)

| Doc | Audience | Era | Purpose |
|---|---|---|---|
| `docs/archive/TABPFN_BENCHMARK_SUMMARY.md` | Actuary | Scripts/v3 | One-page adoption answer + decision rule |
| `MASTER-REPORT-DIGEST.md` | All | Scripts/v3 | Addendum arc §4→§14.14 in one paragraph each — the 5-minute story |
| `analyses/tabpfn_vs_gbdt_baselines_finetuning.md` | Technical | Scripts/v3 | Master report: full evidence, §§1–14.14 |
| `analyses/regime_characterization.md` | Actuary | Scripts/v3 | When default TabPFN wins — predictive adoption rule |
| `analyses/benchmark_portfolio.md` | Colleague | Both | Living index of every benchmark: question, finding, evidence location |
| `docs/archive/MEETING_NARRATIVE_2026-08-20.md` | Stakeholder | Scripts/v3 | Chronological project story for the 2026-08-21 meeting |
| `docs/archive/RESERVING_WITH_FOUNDATIONAL_MODELS.md` | Actuary | Scripts/v3 | Reserving-task findings compiled from the benchmark suite |

## Methods & metrics explainers

| Doc | Audience | Era | Purpose |
|---|---|---|---|
| `analyses/metrics_explained.md` | Actuary | Both | Log loss vs AUC vs Brier: what each rewards, which to use for which decision |
| `analyses/tabular_foundation_models_catalog.md` | Technical | Both | All known tabular foundation models (excludes per-dataset-trained nets) |
| `docs/archive/TECHNICAL_COMPANION.md` | Junior | Notebook/v2 | Metrics + GLM comparison explainer (v2-era numbers — see banner) |
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
| `docs/archive/COMBINED_TABPFN_CLASSIFIER_REGRESSOR_ANALYSIS.md` | Consolidated classifier + regressor findings |
| `reports/MULTI_DATASET_GLM_VS_TABPFN_SUMMARY.md` | Multi-dataset GLM vs TabPFN (non-technical) |
| `docs/archive/POST_HOC_OPTIMISATION.md` | Calibration/optimisation summary |
| `docs/archive/STAGE_A_B_FINDINGS_AND_RECOMMENDATIONS.md` | Stage A/B short report |
| `docs/archive/TABPFN_FINE_TUNING_LIMIT_STUDY.md` | Apple-Silicon finetune limits (classifier-only) |
| `docs/archive/INSURANCE_DOMAIN_FINETUNING_METHOD_PROTOCOL.md` | Domain finetune method protocol |
| `docs/archive/INSURANCE_SPECIFIC_FINETUNING_EVIDENCE.md` | Insurance finetune evidence review |
| `docs/archive/CLASSIFIER_HOMOGENEITY_HYPOTHESIS_METHOD.md` | Homogeneity-hypothesis method + evaluation |
| `docs/REPORT_REGISTRY.md` | Registry: topic keys → workbooks → evidence files (+ `model_version`) |

## Papers & follow-ups

| Doc | Purpose |
|---|---|
| `archive/papers/Theres-Life-in-the-Old-GLM-Yet.md` | Round-1 single-dataset paper (v2.0 era — historical record, see status note) |
| `archive/papers/APPENDIX_REPRODUCIBILITY.md` | Reproducibility package for round-1 results |
| `archive/papers/FOLLOW_UP_ROUND2_JOURNAL_SHORT.md` | Round-2 short journal format (multi-dataset + regression) | — **historical**
| `archive/papers/FOLLOW_UP_ROUND2_JOURNAL_PLAIN.md` | Round-2 plain-English summary | — **superseded**
| `analyses/tabpfn_small_finetune_methodology.md` | Small classifier finetune methodology |
| `analyses/tabpfn_finetune_limit_test_plan.md` | Finetune limit test plan (classifier-only) |

## Ops & history (read only if you need them)

| Doc | Purpose |
|---|---|
| `analyses/merge_plan_tabarena.md` | TabArena branch staged merge plan — MERGED 2026-08-04, coordination record |
| `archive/sessions/2026-07-28-tabarena-benchmark-setup.md` | Session log: TabArena setup first step |
| `archive/status/STATUS_REPORT_FINAL.md` | SUPERSEDED — kept for history, do not cite |
| `archive/status/SECURITY_INCIDENT_RESOLVED.md` | 2024 HF token exposure — resolved/remediated |
| `REPLICATION_SETUP_GUIDE.md` | (listed above) paper replication setup |

## Outside docs/

- **Skills (the junior loop's execution step):** `.github/skills/` + `.opencode/` runbooks — see `KNOWLEDGE-PATH-JUNIOR.md` for which skill maps to which task.
- **Reproducibility notebooks:** `notebooks/reproducibility/README.md` (referenced by runbook §§A.7–A.9).
- **Live benchmark code:** `scripts/eval/insurance_benchmark_v1/`, `scripts/benchmarks/`.
