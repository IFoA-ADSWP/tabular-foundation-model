# Docs Index — what to read, in what order

This repository is the evidence base for applying tabular foundation models to insurance modelling: a
benchmark, a fine-tuning programme, and the diagnostics behind both. Phase 2 of the fine-tuning programme has
closed — a small gain on one of the four anchor datasets, equivalences on two others, and one dataset
stopped because it could not be measured at the precision the design required. The outcome is in
[experiments/pilot2-phase2/FINETUNING_PHASE2_OUTCOME.md](experiments/pilot2-phase2/FINETUNING_PHASE2_OUTCOME.md), and where its numbers come from
is in [EVIDENCE_MAP.md](EVIDENCE_MAP.md).

## Start here

| If you want… | Begin with |
| --- | --- |
| **The outcome** — did fine-tuning help, and by how much? | [FINETUNING_PHASE2_OUTCOME.md](experiments/pilot2-phase2/FINETUNING_PHASE2_OUTCOME.md) — the canonical statement of what Phase 2 found |
| **To check a number** — where does this figure come from? | [EVIDENCE_MAP.md](EVIDENCE_MAP.md) — which tree holds what, and what a citation must have |
| **To run the code** — which environment, which command? | [RUNNING.md](RUNNING.md) — the four routes, what each writes, and the two environments |
| **The method and the decisions** | [FINETUNING_PILOT_DESIGN.md](experiments/pilot2-phase2/FINETUNING_PILOT_DESIGN.md) (what was proposed and why) and [FINETUNING_DECISION_LOG.md](experiments/pilot2-phase2/FINETUNING_DECISION_LOG.md) (what was decided, with its caveats) |
| **Two documents disagree** — which one wins? | [DOCUMENT_AUTHORITY.md](DOCUMENT_AUTHORITY.md) — the order, the owner of each subject, and the fourteen settled disagreements |
| **Something specific** | the role table below, or the tier list that follows it |

Every finding names the model version it was measured under — see [MODEL_VERSIONS.md](MODEL_VERSIONS.md)
before citing a number.

## How this documentation is organised

Two axes, answering two different questions.

**What happened — by experiment.** `docs/experiments/<campaign>/` holds one line of work end to end: its design,
its pre-registration, its result notes and its decision record. Its `README.md` is the way in — the question the
campaign asked, its documents in reading order, and the `results/` runs it owns. [EXPERIMENTS.md](EXPERIMENTS.md)
lists all of them.

**What it is worth now — by status.** Every report declares one tier in its first lines. A superseded document
moves to `docs/archive/<campaign>/` — same grouping, kept for the trail — and the tier says what it is worth.

| Tier | Means | Where it lives |
| --- | --- | --- |
| **current** | describes the design as built, the current answer, or a rule still in force | `docs/experiments/<campaign>/` |
| **reference** | historical, still cited for provenance — the protocol, the measurement, the rejected option | usually the campaign directory; read it when tracing a decision |
| **archive** | kept for the record, not cited | `docs/archive/<campaign>/` |

Links inside `docs/plans/` and `docs/archive/` are **citations, not promises**: those documents describe a state
of the tree at a date, and a path in them may no longer resolve. `doclinks` skips both tiers for that reason, and
`--include-citations` shows the ones that have moved on.

**The current line of work, by tier.**

- **current** — `experiments/pilot2-phase2/FINETUNING_PHASE2_OUTCOME.md` (the outcome) · `experiments/pilot2-phase2/FINETUNING_PILOT_DESIGN.md` (canonical proposal) · `experiments/pilot2-phase2/FINETUNING_FINDINGS.md` · `experiments/pilot2-phase2/FINETUNING_STATUS_BRIEF.md` · `experiments/diagnostics/FINETUNING_DIAGNOSTICS_DESIGN.md` · `experiments/pilot2-phase2/FINETUNING_EXECUTION_RUNBOOK.md` · `experiments/pilot2-phase2/FINETUNING_COST_AND_CONTROLS.md` · `experiments/pilot2-phase2/FINETUNING_STATISTICAL_ANALYSIS_PLAN.md` · `experiments/pilot2-phase2/FINETUNING_DECISION_LOG.md` · `experiments/pilot2-phase2/FINETUNING_PREREQUISITES.md` · `experiments/probe/FINETUNING_PROBE_RESULTS.md` · `experiments/pilot2-phase2/FINETUNING_LITERATURE.md`
- **historical** — `archive/pilot2-phase2/PILOT_2_BRIEFING.md`
- **reference** — `experiments/probe/PROBE_PLAN.md` · `experiments/probe/PROBE_FIRST_RUN.md` · `experiments/pilot2-phase2/PILOT_2_DESIGN.md` · `experiments/pilot2-phase2/PILOT_2_DESIGN_ALTERNATIVE.md` · `experiments/pilot2-phase2/PILOT_2_DECISION_GRAPH.md` (its step 0 fired) · `experiments/r1-pilot/FINE_TUNING_PILOT_RESULTS.md` · the five v2-era fine-tuning pages listed in the literature record
- **archive** — everything in the legacy tables further down this file: the earlier benchmark, analysis and session documents.

**Programme history.** R1 (first pilot, no reliable gain) → Pilot 2 (the wider staged proposal) → the probe at
the smaller budget, negative → **Phase 2 at the larger budget, closed 2026-11-07**: a small gain on one
dataset, equivalences on two, and one dataset stopped on resolution. Earlier-era documents carry a status
banner; where a banner and a front section disagree, the document the banner points at wins. (Code eras —
fine-tuning, scripts, notebook — are a different axis; see *Era legend* below.)

**The rule for adding a document:** it enters as **current** only if it carries content nothing else carries; otherwise it is `reference` from the start. When a current document stops being current it is amended with a dated note and its tier changes — never deleted, because the trail is the point.

**Not tiered reports.** Read these when the question is "should we build this, and how" or "where does this
number live", not "what did we measure":

- `docs/plans/` — one plan per task, written before non-trivial work and committed with it. **A plan outranks a fresh ticket**: check here before speccing or building, because the ticket you are about to write may already be covered.
- `docs/adr/` — accepted decisions that constrain the code, one per decision, cited by the plans that rely on them.
- `EVIDENCE_MAP.md`, `MODEL_VERSIONS.md`, `DOCUMENT_AUTHORITY.md`, `DEVELOPMENT_ENVIRONMENT.md`, `RUNNING.md` and `REPORT_REGISTRY.md` — lookup pages that sit at this level because a reader consults them beside a claim, not after one. `DOCUMENT_AUTHORITY.md` states which document wins when two disagree; `DEVELOPMENT_ENVIRONMENT.md` says how to build the environment the gate runs in and which checkout you are in; `RUNNING.md` says which environment each route needs and what it writes.

**Enforcement.** `scripts/check_doc_status.py` asserts that every report under `experiments/`, `shared/` and
`archive/` declares a status in its first fifteen lines, that every campaign README lists every document in its
directory, and that the findings registry carries no restated number. Run it with
`./scripts/check.sh docstatus`.

The report-level index is `docs/REPORT_REGISTRY.md` and is deliberately not restated here, so there is exactly one place to update when a report is added.

## Start here by role

| You are… | Read in order |
|---|---|
| Junior data scientist | `KNOWLEDGE-PATH-JUNIOR.md` → `shared/metrics_explained.md` → `archive/frontier-benchmark/CODE_WALKTHROUGH.md` → `MASTER-REPORT-DIGEST.md` |
| Actuary (do I adopt this?) | `archive/frontier-benchmark/TABPFN_BENCHMARK_SUMMARY.md` → `shared/metrics_explained.md` → `experiments/frontier-benchmark/regime_characterization.md` → `archive/reserving/RESERVING_WITH_FOUNDATIONAL_MODELS.md` |
| Engineer (how does it run?) | `RUNNING.md` → `archive/frontier-benchmark/CODE_WALKTHROUGH.md` → `REPRODUCIBILITY_RUNBOOK.md` → `MODEL_VERSIONS.md` → `docs/REPORT_REGISTRY.md` |
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
| `archive/frontier-benchmark/CODE_WALKTHROUGH.md` | Engineer | Scripts | `run_frontier_benchmark.py` step by step (2026-08-20) |
| `REPRODUCIBILITY_RUNBOOK.md` | Engineer | Both | Every committed result → exact command; separate frontier-era and legacy sections |
| `MODEL_VERSIONS.md` | All | Both | v2 → v2.5 → v3 timeline, what flipped, per-artifact validity, re-test rule |
| `REPLICATION_SETUP_GUIDE.md` | Replicator | Notebook | Paper replication notebook setup (v2-era, seed 45) |

## Verdicts (what we found — read newest first)

| Doc | Audience | Era | Purpose |
|---|---|---|---|
| `archive/frontier-benchmark/TABPFN_BENCHMARK_SUMMARY.md` | Actuary | Scripts/v3 | One-page adoption answer + decision rule |
| `MASTER-REPORT-DIGEST.md` | All | Scripts/v3 | Addendum arc §4→§14.14 in one paragraph each — the 5-minute story |
| `experiments/frontier-benchmark/tabpfn_vs_gbdt_baselines_finetuning.md` | Technical | Scripts/v3 | Master report: full evidence, §§1–14.14 |
| `experiments/frontier-benchmark/regime_characterization.md` | Actuary | Scripts/v3 | When default TabPFN wins — predictive adoption rule |
| `experiments/frontier-benchmark/benchmark_portfolio.md` | Colleague | Both | Living index of every benchmark: question, finding, evidence location |
| `archive/frontier-benchmark/MEETING_NARRATIVE_2026-08-20.md` | Stakeholder | Scripts/v3 | Chronological project story for the 2026-08-21 meeting |
| `archive/reserving/RESERVING_WITH_FOUNDATIONAL_MODELS.md` | Actuary | Scripts/v3 | Reserving-task findings compiled from the benchmark suite |

## Methods & metrics explainers

| Doc | Audience | Era | Purpose |
|---|---|---|---|
| `shared/metrics_explained.md` | Actuary | Both | Log loss vs AUC vs Brier: what each rewards, which to use for which decision |
| `shared/tabular_foundation_models_catalog.md` | Technical | Both | All known tabular foundation models (excludes per-dataset-trained nets) |
| `archive/frontier-benchmark/TECHNICAL_COMPANION.md` | Junior | Notebook/v2 | Metrics + GLM comparison explainer (v2-era numbers — see banner) |
| `experiments/tabarena/tabarena_reference.md` | Technical | — | TabArena background (51 IID + 142 BeyondArena sets, NeurIPS spotlight) |
| `experiments/tabarena/tabarena_insurance_benchmark_direction.md` | Technical | Scripts/v3 | What we learned from TabArena; direction for our insurance benchmark |
| `experiments/tabarena/cpu_model_feasibility.md` | Engineer | Scripts/v3 | Which TabArena method families are usable with no GPU |
| `shared/levers_assessment.md` | Technical | Scripts/v3 | Scoping: fine-tuning, HPO, ensembling (no new runs, 2026-08-04) |
| `experiments/frontier-benchmark/class_imbalance_analysis_summary.md` | Technical | Notebook | Imbalance effects; null result confirmed by master §11 |

## Design specs (proposed → implemented trail)

| Doc | Status | Purpose |
|---|---|---|
| `experiments/frontier-benchmark/insurance_frontier_benchmark_spec.md` | Agreed/executed (#27, PR #51) | Frontier benchmark D1–D5 |
| `experiments/frontier-benchmark/frontier_auc_brier_rescore_spec.md` | Implemented 2026-08-06 | AUC/Brier power columns; delivered §14.11 |
| `experiments/frontier-benchmark/prediction_capture_rescore_spec.md` | Proposed (#122) | Persisted per-fold predictions for retrospective re-scoring |
| `experiments/frontier-benchmark/altmetrics_rescore_spec.md` | Proposed (#123) | Gamma/Tweedie/MAE from stored predictions, no refits |

## Legacy reports (v2-era — see banners, cite via MODEL_VERSIONS)

| Doc | Purpose |
|---|---|
| `archive/frontier-benchmark/COMBINED_TABPFN_CLASSIFIER_REGRESSOR_ANALYSIS.md` | Consolidated classifier + regressor findings |
| `archive/frontier-benchmark/MULTI_DATASET_GLM_VS_TABPFN_SUMMARY.md` | Multi-dataset GLM vs TabPFN (non-technical) |
| `archive/frontier-benchmark/POST_HOC_OPTIMISATION.md` | Calibration/optimisation summary |
| `archive/pilot2-phase2/STAGE_A_B_FINDINGS_AND_RECOMMENDATIONS.md` | Stage A/B short report |
| `archive/pilot2-phase2/TABPFN_FINE_TUNING_LIMIT_STUDY.md` | Apple-Silicon finetune limits (classifier-only) |
| `archive/pilot2-phase2/INSURANCE_DOMAIN_FINETUNING_METHOD_PROTOCOL.md` | Domain finetune method protocol |
| `archive/pilot2-phase2/INSURANCE_SPECIFIC_FINETUNING_EVIDENCE.md` | Insurance finetune evidence review |
| `archive/pilot2-phase2/CLASSIFIER_HOMOGENEITY_HYPOTHESIS_METHOD.md` | Homogeneity-hypothesis method + evaluation |
| `docs/REPORT_REGISTRY.md` | Registry: topic keys → workbooks → evidence files (+ `model_version`) |

## Papers & follow-ups

| Doc | Purpose |
|---|---|
| `archive/papers/Theres-Life-in-the-Old-GLM-Yet.md` | Round-1 single-dataset paper (v2.0 era — historical record, see status note) |
| `archive/papers/APPENDIX_REPRODUCIBILITY.md` | Reproducibility package for round-1 results |
| `archive/papers/FOLLOW_UP_ROUND2_JOURNAL_SHORT.md` | Round-2 short journal format (multi-dataset + regression) | — **historical**
| `archive/papers/FOLLOW_UP_ROUND2_JOURNAL_PLAIN.md` | Round-2 plain-English summary | — **superseded**
| `experiments/pilot2-phase2/tabpfn_small_finetune_methodology.md` | Small classifier finetune methodology |
| `experiments/pilot2-phase2/tabpfn_finetune_limit_test_plan.md` | Finetune limit test plan (classifier-only) |

## Ops & history (read only if you need them)

| Doc | Purpose |
|---|---|
| `experiments/tabarena/merge_plan_tabarena.md` | TabArena branch staged merge plan — MERGED 2026-08-04, coordination record |
| `archive/sessions/2026-07-28-tabarena-benchmark-setup.md` | Session log: TabArena setup first step |
| `archive/status/STATUS_REPORT_FINAL.md` | SUPERSEDED — kept for history, do not cite |
| `archive/status/SECURITY_INCIDENT_RESOLVED.md` | 2024 HF token exposure — resolved/remediated |
| `REPLICATION_SETUP_GUIDE.md` | (listed above) paper replication setup |

## Outside docs/

- **Skills (the junior loop's execution step):** `.opencode/skills/` + `.opencode/agents/` — see `KNOWLEDGE-PATH-JUNIOR.md` for which skill maps to which task.
- **Reproducibility notebooks:** `notebooks/reproducibility/README.md` (referenced by runbook §§A.7–A.9).
- **Live benchmark code:** `scripts/eval/insurance_benchmark_v1/`, `scripts/benchmarks/`.
