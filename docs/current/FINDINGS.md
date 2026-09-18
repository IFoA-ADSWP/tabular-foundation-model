# Findings — what this repository currently believes

**Read this before citing any number.** Two probes have run, and the second overturned the first. Documents
from the era of the first still describe it accurately; this page says which claim is current.

**How to use it.** Each row names the document that owns the claim. Cite from there, not from this page — this
page is a pointer, and it is deliberately not a restatement. When a claim changes, its owning document is
amended with a dated note and this table follows it.

| # | Claim | Status | Owner |
| --- | --- | --- | --- |
| F1 | On lapse data (`uslapseagent`), fine-tuning beats raw TabPFN at **10,000 training rows**: all three epoch rungs, ROC AUC deltas +0.0022 / +0.0026 / +0.0034, paired 95% intervals excluding zero, monotone in epochs, Brier improving with them. | **current** — one seed, one split | `docs/current/FINE_TUNING_EXPERIMENT_DESIGN.md`, front section |
| F2 | At **2,000 training rows** fine-tuning did **not** beat raw: all three rungs at or below baseline, the pre-registered outcome 3 of 3. | **superseded by F1** — a small-data artefact of our own row cap | `docs/current/PROBE_RESULTS.md` (dated note at its head) |
| F3 | Raw TabPFN already leads the competing baselines on `uslapseagent` — 0.9363 ROC AUC against 0.9271 (GLM) and 0.9297 (CatBoost). | current | `docs/current/PILOT_2_BRIEFING.md`, `FINE_TUNING_PILOT_RESULTS.md` |
| F4 | Any fine-tuning gain is therefore a **within-model** improvement, not the closing of a gap to another method. | current, and the reason F1 is worded as it is | `docs/current/FINE_TUNING_EXPERIMENT_DESIGN.md`, front section |
| F5 | Measured cost anchors: **$0.0122** for a four-arm run at 2,000 rows, **$0.0368** at 10,000 rows. | current — measured, not modelled | `docs/current/PILOT_2_COST_AND_CONTROLS.md` |
| F6 | The ~$368 programme-scale figure is **withdrawn** and marked superseded. Do not quote it, or any figure not measured. | withdrawn | `docs/current/PILOT_2_COST_AND_CONTROLS.md`, figure checker |
| L1 | **No lapse dataset carries a usable time index**, so no temporal split is testable. Every result is conditional on a random split. | standing limitation, not a defect | `docs/current/FINE_TUNING_EXPERIMENT_DESIGN.md`, front section |
| L2 | The published fine-tuning studies are TabPFN **v2-based**; this line of work runs the v3 checkpoint. Their guidance transfers, their numbers do not. | standing limitation | `docs/current/TABPFN_FINETUNING_LITERATURE.md` |
| L3 | One seed so far. The paired intervals are within-run and say nothing about seed variation. | open — replication is the next question | `docs/current/FINE_TUNING_EXPERIMENT_DESIGN.md`, front section |

## What is not on this page

Findings from work that has not landed. A claim enters this table when its evidence is merged and its numbers
are checkable — not when a PR is opened.
