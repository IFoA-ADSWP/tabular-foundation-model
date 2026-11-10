# Document authority — which document wins when two disagree

> Not a tiered report; a reading aid. It states the order once, then points at the decision that settled
> each known disagreement. It owns no number and restates none.

This repository is written by many documents on many dates. Where two of them describe the same subject
differently, this page says which one binds. The order is stated here and nowhere else.

## The order

Two questions, not one ranking. Applying a single ladder to both is what produced most of the disagreements
below: a run record can settle a number, and it can never settle a rule.

**A number** resolves to the **capture** of the run that produced it — the persisted predictions and truth
labels, hashed. If no capture exists, the number resolves to the document that owns the subject; the
[evidence map](EVIDENCE_MAP.md) says which tree to walk. A summary never carries a number of its own.

**A rule** resolves to the **commitment frozen before the runs ran** — the statistical analysis plan, or a
dated decision. A change after that is a **dated departure** in the decision log: it names what changed, why,
and what it affects. It is never a correction written back over the original.

## When two documents own the same subject

- **Subject ownership decides first.** Each document wins on the subject it owns (see the table below).
- **"Canonical" means read this first.** It does not mean the design outranks the plan that owns the
  statistics. Several documents call themselves canonical; the word is a reading order, not a rank.
- **The earlier dated commitment breaks the tie** between two owners. Later text that contradicts it is a
  departure to be recorded, not a correction to be applied.

## Who owns what

| Subject | The owning document | It does not own |
| --- | --- | --- |
| The design — scope, arms, rungs, what is reported | [FINETUNING_PILOT_DESIGN.md](current/FINETUNING_PILOT_DESIGN.md) | the sign conventions; the claim test |
| Analysis rules — estimand, sign, tolerances | [FINETUNING_STATISTICAL_ANALYSIS_PLAN.md](current/FINETUNING_STATISTICAL_ANALYSIS_PLAN.md) | scope; the claim test |
| The claim test — what counts as a pass | [FINETUNING_DECISION_LOG.md](current/FINETUNING_DECISION_LOG.md) | the estimand; the design |
| Per-dataset facts — target, source file, provenance | [FINETUNING_EXPERIMENT_REFERENCE.md](current/FINETUNING_EXPERIMENT_REFERENCE.md) | scope; this repository's row counts |
| Row counts, and which datasets this repository registers | [FINETUNING_COST_AND_CONTROLS.md](current/FINETUNING_COST_AND_CONTROLS.md) | targets or provenance |
| Measured and modelled cost | [FINETUNING_COST_AND_CONTROLS.md](current/FINETUNING_COST_AND_CONTROLS.md) | the spend decision |
| A measured result | the owning analysis under [`docs/analyses/`](analyses/finetuning_replication_result.md) | the claim test |
| Model eras, and whether a number may be cited at all | [MODEL_VERSIONS.md](MODEL_VERSIONS.md) | per-artifact results |
| The index of claims | [FINETUNING_FINDINGS.md](current/FINETUNING_FINDINGS.md) | any number it links to |
| The closing statement of a phase | [FINETUNING_PHASE2_OUTCOME.md](current/FINETUNING_PHASE2_OUTCOME.md) | the numbers it links to |

## The fourteen disagreements, and which document won

Each row is one decision, held in the ticket named. Where a row says "both, scoped", the losing sentence
survives with a dated note rather than being deleted.

| # | The disagreement | The winner | Decision |
| --- | --- | --- | --- |
| 1 | Three documents named three different primary metrics; the result was computed under a fourth reading of them | the decision log's dated claim rule | [#518](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/518) |
| 2 | The analysis plan forbids quoting a resolution figure, then quotes it three times | the plan's own later reconciliation | [#518](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/518) |
| 3 | The R3 gate is recommended by one page and rejected by the successor design | the successor design | [#519](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/519) |
| 4 | One dataset was priced four different ways, and one of the four is a misquotation rather than an estimate | the measured cost | [#520](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/520) |
| 5 | The batch plan and the execution disagree, and one decision contradicts its own count | the execution | [#520](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/520) |
| 6 | "Repeats buy no sensitivity" sits beside a programme that bought sensitivity in seeds | both, scoped: repeats move the between-split variance, not the row-sampling floor | [#518](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/518) |
| 7 | One model version described as never run, and as the era a committed diagnostic resolved to | the diagnostic's record; the version page was incomplete, not wrong | [#522](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/522) |
| 8 | The in-domain scope stated as three datasets and as four | the design's four-dataset family; three is the count of lapse targets | [#521](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/521) |
| 9 | Two inventories of dataset sizes, one of them another repository's and unmarked | this repository's cost page | [#521](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/521) |
| 10 | A calibration tolerance stated as unset and as set at sign-off | the same plan's later section | [#518](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/518) |
| 11 | The forbidden figure has a second owner on another page | the same reconciliation | [#518](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/518) |
| 12 | A decision contradicts its own batch count, and neither value matches the execution | the execution | [#520](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/520) |
| 13 | A dataset's row count differs between two current pages | this repository's cost page | [#521](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/521) |
| 14 | A spending ceiling attributed to a decision that explicitly sets none | the decisions that set it | [#520](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/520) |

The exact passage, the current text and the note each gains are in
[`docs/plans/document-authority-amendments.md`](plans/document-authority-amendments.md). This page
deliberately does not repeat them, so there is one place to update.

## What this page is not

- **Not a rewrite.** No passage is deleted. A losing sentence keeps its text and gains a dated note naming
  the winner, so the trail shows what was believed and when.
- **Not a ranking of people or of effort.** It ranks subjects, once.
- **Not a resolver of new questions.** A disagreement not listed here is a new decision. File it; do not
  quietly edit the losing side.

## If a new disagreement appears

1. State the two passages and the subject they share.
2. Ask which document owns that subject. If both do, take the earlier dated commitment.
3. Record the decision where it lives — the decision log for a rule, the owning analysis for a result.
4. Add the note to the losing passage, dated, naming the winner.
5. Add a row to the table above.
