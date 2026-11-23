# Pilot2 Phase2

> **Status:** index — this campaign's reading order, not a report of its own.

The fine-tuning programme: design, pre-registrations, the replication and breadth cells, the decision log and the Phase 2 outcome.

**30 documents.** Read them in this order; the table below lists every document and its status.
A document marked reference or historical is kept for provenance rather than as the current answer.

> **Phase 2 closed 2026-11-07 (D22).** In-domain fine-tuning is measured: one small gain, two
> equivalences, and one further classification target stopped on resolution. The transfer/pooling
> phase was never authorised and is **untested, not failed**. The regressor line closed separately
> on 2026-11-22 (#729).

## Read in this order

1. [Phase 2 outcome](FINETUNING_PHASE2_OUTCOME.md) — the answer, and the limits of what it claims.
2. [Findings](FINETUNING_FINDINGS.md) — the claim index; it carries no numbers of its own.
3. The regressor line: [fair-test result](../fair-test-freq-sev/freq_sev_fair_test_result.md), then
   [epoch ladder result](EPOCH_LADDER_RESULT.md), then the
   [paper matrix](../../shared/FINETUNING_RESULTS_MATRIX.md).
4. [Decision log](FINETUNING_DECISION_LOG.md) and
   [SAP](FINETUNING_STATISTICAL_ANALYSIS_PLAN.md) — the rules the results were read under.
5. The rest of the table is design, protocol and run record; current documents keep their own
   status rather than becoming provenance.


| Document | Status | What it holds |
| --- | --- | --- |
| [`FINETUNING_BREADTH_SPEC.md`](FINETUNING_BREADTH_SPEC.md) | proposed — no launch authorised; Phase 2 executed it in part | Breadth specification — the full value of in-domain fine-tuning (2026-11) |
| [`FINETUNING_COST_AND_CONTROLS.md`](FINETUNING_COST_AND_CONTROLS.md) | current — measured costs, 2026-11-10 | Fine-Tuning — What It Costs, and Why |
| [`FINETUNING_DECISION_LOG.md`](FINETUNING_DECISION_LOG.md) | current — decisions in force, 2026-11-03 | Fine-Tuning — Decision Log for Technical Review |
| [`FINETUNING_EXECUTION_RUNBOOK.md`](FINETUNING_EXECUTION_RUNBOOK.md) | current — next-run appendix, 2026-11-05 | Fine-Tuning Execution Runbook — Next-Run Appendix |
| [`FINETUNING_EXPERIMENT_REFERENCE.md`](FINETUNING_EXPERIMENT_REFERENCE.md) | reference — design and measurement record; superseded for the outcome | Fine-Tuning Experiment Reference (v6) |
| [`FINETUNING_FINDINGS.md`](FINETUNING_FINDINGS.md) | current — claims index, no numbers, 2026-11-08 | Fine-Tuning Findings — What This Repository Currently Believes |
| [`FINETUNING_LITERATURE.md`](FINETUNING_LITERATURE.md) | current — the repository’s reading, 2026-10-31 | Fine-Tuning Literature Review — What It Means Here |
| [`FINETUNING_PHASE2_OUTCOME.md`](FINETUNING_PHASE2_OUTCOME.md) | current — the Phase 2 answer, 2026-11-08 | Fine-tuning TabPFN on insurance data — the Phase 2 outcome |
| [`FINETUNING_PILOT_DESIGN.md`](FINETUNING_PILOT_DESIGN.md) | reference — design record; executed in part, Phase 2 closed | Fine-Tuning Pilot — Canonical Design and Decision Framework |
| [`FINETUNING_PREREGISTRATION_2026-11.md`](FINETUNING_PREREGISTRATION_2026-11.md) | current — pre-registration, 2026-11-04 | Pre-registration — the fine-tuning replication (2026-11) |
| [`FINETUNING_PREREGISTRATION_SPANISH_2026-11.md`](FINETUNING_PREREGISTRATION_SPANISH_2026-11.md) | current — pre-registration, 2026-11-05 | Pre-registration — the Spanish lapse cell (2026-11) |
| [`FINETUNING_PREREQUISITES.md`](FINETUNING_PREREQUISITES.md) | reference — checklist for the pilot, 2026-10-31 | Fine-Tuning — Prerequisites Checklist |
| [`FINETUNING_RUNS_LEDGER.md`](FINETUNING_RUNS_LEDGER.md) | current — generated ledger, 2026-11-20; scope note added 2026-11-22 | Cross-task runs ledger — the committed fine-tuning and fair-test runs it covers, arm, seed and fold, with a descriptive summary |
| [`FINETUNING_STATISTICAL_ANALYSIS_PLAN.md`](FINETUNING_STATISTICAL_ANALYSIS_PLAN.md) | current — signed 2026-10-30; amendments dated | Fine-Tuning — Statistical Analysis Plan |
| [`EPOCH_LADDER_DESIGN.md`](EPOCH_LADDER_DESIGN.md) | current — design record, 2026-11-22 | Epoch ladder — the design's resolution, and why each factor is what it is |
| [`EPOCH_LADDER_RESULT.md`](EPOCH_LADDER_RESULT.md) | current — result note, 2026-11-22 | Epoch ladder — result: the sign of fine-tuning flips between severity targets |
| [`EPOCH_LADDER_ESTIMAND_DIAGNOSTIC.md`](EPOCH_LADDER_ESTIMAND_DIAGNOSTIC.md) | current — post-hoc diagnostic, 2026-11-22 | Epoch ladder — how much of the severity sign flip is the estimand |
| [`FINETUNING_STATUS_BRIEF.md`](FINETUNING_STATUS_BRIEF.md) | reference — narrative, 2026-11-05; superseded for the outcome | Fine-Tuning Investigation — Status Brief |
| [`PILOT_2_DECISION_GRAPH.md`](PILOT_2_DECISION_GRAPH.md) | reference — design graph, 2026-10-31 | Pilot 2 — the decision graph |
| [`PILOT_2_DESIGN.md`](PILOT_2_DESIGN.md) | reference — design, 2026-10-31 | Pilot 2 — Design for a Fair Test of Fine-Tuning |
| [`PILOT_2_DESIGN_ALTERNATIVE.md`](PILOT_2_DESIGN_ALTERNATIVE.md) | reference — rejected alternative, 2026-10-31 | Pilot 2 — alternative design: staged isolation |
| [`PRIOR_LABS_MEETING_2026-10-14.md`](PRIOR_LABS_MEETING_2026-10-14.md) | reference — external advice, 2026-10-14 | Meeting — Prior Labs data scientist (insurance domain) |
| [`anchor_power_diagnosis.md`](anchor_power_diagnosis.md) | reference — analysis, 2026-10-31 | Anchor power diagnosis — was the two-seed result underpowered or null? |
| [`finetuning_breadth_eudirectlapse_result.md`](finetuning_breadth_eudirectlapse_result.md) | current — result, 2026-11-05 | Breadth result — fine-tuning does not generalise to `eudirectlapse` |
| [`finetuning_breadth_spanish_result.md`](finetuning_breadth_spanish_result.md) | current — result, 2026-11-06 | Breadth result — fine-tuning adds nothing measurable on `spanish_motor_lapse` |
| [`finetuning_replication_result.md`](finetuning_replication_result.md) | current — result, 2026-11-04 | Fine-tuning replication — +0.0035 AUC on `uslapseagent` at 30 epochs |
| [`replication_sizing.md`](replication_sizing.md) | reference — analysis for #390, 2026-11-03; superseded in shape by D13 | Replication sizing — what design could settle 0.002–0.006 AUC, and what it costs |
| [`spanish_motor_lapse_stage2_readiness.md`](spanish_motor_lapse_stage2_readiness.md) | reference — readiness analysis, 2026-11-03 | Is `spanish_motor_lapse` fit to carry Stage 2? |
| [`tabpfn_finetune_limit_test_plan.md`](tabpfn_finetune_limit_test_plan.md) | reference — 2026-08 plan, overtaken | TabPFN Fine-Tuning Limit Test Plan |
| [`tabpfn_small_finetune_methodology.md`](tabpfn_small_finetune_methodology.md) | reference — methodology note | Small TabPFN Classifier Fine-Tuning Methodology |

## Runs

Committed under `results/`, cited by the documents above:

```
20261031T021845Z
20261104T122235Z
20261104T123839Z
20261104T234013Z
20261104T234127Z
20261104T234132Z
20261105T001837Z
20261105T005435Z
20261105T005447Z
20261105T012925Z
20261105T013749Z
20261105T013755Z
20261105T100533Z
20261105T103841Z
20261105T103853Z
20261105T103937Z
20261105T111110Z
20261105T114320Z
20261105T114647Z
20261105T124200Z
20261105T124205Z
20261105T140236Z
20261105T140242Z
```
