# Fine-Tuning Findings — What This Repository Currently Believes

**Read this before citing any number.** Two probes have run, and the second overturned the first. Documents
from the era of the first still describe it accurately; this page says which claim is current. For the current
funded proposal and execution scope, start with `docs/current/FINETUNING_PILOT_DESIGN.md`.

**How to use it.** Each row names the document that owns the claim. Cite from there, not from this page — this
page is a pointer, and it is deliberately not a restatement. When a claim changes, its owning document is
amended with a dated note and this table follows it.

| # | Claim | Status | Owner |
| --- | --- | --- | --- |
| F1 | On lapse data (`uslapseagent`), fine-tuning beats raw TabPFN at **10,000 training rows**: all three epoch rungs, ROC AUC deltas +0.0022 / +0.0026 / +0.0034, paired 95% intervals excluding zero, monotone in epochs, Brier improving with them. | **current** — one seed, one split | `docs/current/FINETUNING_EXPERIMENT_REFERENCE.md`, front section |
| F2 | At **2,000 training rows** fine-tuning did **not** beat raw: all three rungs at or below baseline, the pre-registered outcome 3 of 3. | **superseded by F1** — a small-data artefact of our own row cap | `docs/current/FINETUNING_PROBE_RESULTS.md` (dated note at its head) |
| F3 | Raw TabPFN already leads the competing baselines on `uslapseagent` — 0.9363 ROC AUC against 0.9271 (GLM) and 0.9297 (CatBoost). | current | `docs/archive/PILOT_2_BRIEFING.md`, `docs/reference/FINE_TUNING_PILOT_RESULTS.md` |
| F4 | Any fine-tuning gain is therefore a **within-model** improvement, not the closing of a gap to another method. | current, and the reason F1 is worded as it is | `docs/current/FINETUNING_EXPERIMENT_REFERENCE.md`, front section |
| F5 | Measured cost anchors: **$0.0122** for a four-arm run at 2,000 rows, **$0.0368** at 10,000 rows. | current — measured, not modelled | `docs/current/FINETUNING_COST_AND_CONTROLS.md` |
| F6 | The ~$368 programme-scale figure is **withdrawn** and marked superseded. Do not quote it, or any figure not measured. | withdrawn | `docs/current/FINETUNING_COST_AND_CONTROLS.md`, figure checker |
| F7 | Synthetic-data and augmentation experiments previously degraded performance: TabPFN-extensions, SMOTE, and noise augmentation all hurt; noise augmentation moved ROC AUC approximately 0.83 → 0.59. | current prior evidence; not a current v3 pilot result | `docs/archive/PRE_FINETUNING_INVESTIGATIONS.md`, `docs/KNOWLEDGE-PATH.md` §S6, `notebooks/baseline_experiments/06_synthetic_data_exploration.ipynb` |
| F8 | The C/D pooled-transfer arms and shuffled-label control have not been run in the current pilot. | open — Phase 3 conditional on in-domain replication | `docs/reference/PILOT_2_DESIGN.md`, `docs/archive/SMOKE_TEST_SCOPE.md` |
| L1 | **No lapse dataset carries a usable time index**, so no temporal split is testable. Every result is conditional on a random split. | standing limitation, not a defect | `docs/current/FINETUNING_EXPERIMENT_REFERENCE.md`, front section |
| L2 | The published fine-tuning studies are TabPFN **v2-based**; this line of work runs the v3 checkpoint. Their guidance transfers, their numbers do not. | standing limitation | `docs/current/FINETUNING_LITERATURE.md` |
| L3 | One seed so far. The paired intervals are within-run and say nothing about seed variation. | open — replication is the next question | `docs/current/FINETUNING_EXPERIMENT_REFERENCE.md`, front section |

## What is not on this page

Findings from work that has not landed. A claim enters this table when its evidence is merged and its numbers
are checkable — not when a PR is opened.
