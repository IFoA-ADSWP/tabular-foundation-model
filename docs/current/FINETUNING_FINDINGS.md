# Fine-Tuning Findings — What This Repository Currently Believes

> **Status:** current as of 2026-11-08.

**Read this before citing any number.** Every claim below names the one document that owns it. Cite from
there, not from this page.

**How to use it — and why there are no numbers here.** A claim here carries **no number**. A copied number
goes stale silently, which is exactly what happened to this page between 31 October and 8 November: two rows
kept asserting what their owners had since contradicted, and nothing failed. The number lives in the owning
document, one link away, where it is amended when it changes. If you want a figure, follow the owner.

| Claim | Status | Owner |
| --- | --- | --- |
| **F1** Fine-tuning beats raw TabPFN on the anchor lapse dataset at the pilot's larger training budget. | current | `docs/analyses/finetuning_replication_result.md` |
| **F2** At the pilot's smaller training budget, no epoch rung beat raw TabPFN. | superseded | `docs/current/FINETUNING_PROBE_RESULTS.md` |
| **F3** Raw TabPFN already led the competing actuarial baselines on the anchor dataset, before any fine-tuning. | current | `docs/reference/FINE_TUNING_PILOT_RESULTS.md` |
| **F4** Any fine-tuning gain is a within-model improvement, not a closing of the gap to another method. | current | `docs/current/FINETUNING_EXPERIMENT_REFERENCE.md` |
| **F5** Measured cost anchors exist for a four-arm run at both of the pilot's training budgets. | current | `docs/current/FINETUNING_COST_AND_CONTROLS.md` |
| **F6** A programme-scale cost figure was withdrawn because it was modelled rather than measured. | withdrawn | `docs/current/FINETUNING_COST_AND_CONTROLS.md` |
| **F7** Synthetic-data and augmentation experiments, run before this pilot, degraded performance. | current | `docs/archive/PRE_FINETUNING_INVESTIGATIONS.md` |
| **F8** The pooled-transfer arms and the shuffled-label control have not run. | current | `docs/reference/PILOT_2_DESIGN.md` |
| **L1** No lapse dataset carries a usable time index, so every result is conditional on a random split. | limitation | `docs/current/FINETUNING_EXPERIMENT_REFERENCE.md` |
| **L2** The published fine-tuning studies predate the checkpoint this line of work runs; their guidance transfers, their numbers do not. | limitation | `docs/current/FINETUNING_LITERATURE.md` |
| **L3** The early intervals were within-run, so seed variation was unestimated. | superseded | `docs/analyses/finetuning_replication_result.md` |

## What is not on this page

Findings from work that has not landed. A claim enters this table when its evidence is merged and its numbers
are checkable — not when a PR is opened. A claim leaves it only by changing status, never by deletion: F2 is
still true of the budget it measured, and L3 was still true on the day it was written.
