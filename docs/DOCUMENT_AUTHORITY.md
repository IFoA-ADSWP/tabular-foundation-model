# Document authority — which document wins when two disagree

> Not a tiered report; a reading aid. It states the order, then points at the decision that settled each
> known disagreement. It owns no number and restates none.

This repository is written by many documents on many dates. Where two of them describe the same subject
differently, this page says which one binds. The order is stated in full here; two narrower rules live
elsewhere and are not contradicted by it — a plan outranks a fresh ticket, and where a banner and a front
section disagree the banner points at the winner.

## The order

**A number** resolves to the **capture** of the run that produced it — the persisted predictions and truth
labels, hashed. If no capture exists, the number resolves to the document that owns the subject; the
[evidence map](EVIDENCE_MAP.md) says which tree to walk. A summary never carries a number of its own.

**A rule** resolves to the **commitment frozen before the runs ran** — the statistical analysis plan, or a
dated decision. A change after that is a **dated departure** in the decision log: it names what changed, why,
and what it affects. It is never written back over the original.

**A document against itself** resolves the same way, within one file: the **later dated statement
supersedes**, and the earlier text keeps its wording behind a note. Three of the disagreements below are of
this kind, and they are the easiest to misread, because the file looks internally consistent until the
second statement is found.

Applying one rule to all three cases is what produced the metric disagreement: a run record can settle a
number, and it can never settle a rule.

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
| A measured result | the owning analysis: [replication](analyses/finetuning_replication_result.md), [eudirectlapse](analyses/finetuning_breadth_eudirectlapse_result.md), [spanish](analyses/finetuning_breadth_spanish_result.md) | the claim test |
| Model eras, and whether a number may be cited at all | [MODEL_VERSIONS.md](MODEL_VERSIONS.md) | per-artifact results |
| The index of claims | [FINETUNING_FINDINGS.md](current/FINETUNING_FINDINGS.md) | any number it links to |
| The closing statement of a phase | [FINETUNING_PHASE2_OUTCOME.md](current/FINETUNING_PHASE2_OUTCOME.md) | the numbers it links to |

## The fourteen disagreements, and which document won

Each row is one decision. Where a row says "both, scoped", the losing sentence survives with a dated note.
Where a row says "corrected", the text is wrong rather than merely older, and the note quotes the wording it
replaced.

| # | The disagreement | The winner | Decision |
| --- | --- | --- | --- |
| 1 | Three documents named three different primary metrics; the result was computed under the third, and a fourth page reported a different priority | the decision log's dated claim rule | [Decide which metric rule governed the Phase 2 verdict](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/518) |
| 2 | A resolution figure is forbidden in one section and quoted in two documents | the plan's own later reconciliation | [Decide which metric rule governed the Phase 2 verdict](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/518) |
| 3 | A calibration tolerance stated as unset and as set at sign-off | the same plan's later section | [Decide which metric rule governed the Phase 2 verdict](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/518) |
| 4 | "Repeats buy no sensitivity" beside a programme that bought sensitivity in seeds | both, scoped: repeats move the between-split variance, not the row-sampling floor | [Decide which metric rule governed the Phase 2 verdict](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/518) |
| 5 | The R3 gate recommended by one page and rejected by the successor design | the successor design, on the reference's own finding | [Decide whether the R3 gate applies to the fine-tuning hypothesis](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/519) |
| 6 | One dataset priced four different ways | the measured cost | [Decide what a paid launch costs and how large its batch is](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/520) |
| 7 | One of those four prices is a misquotation, not a fourth estimate | the figure the decision actually states | [Decide what a paid launch costs and how large its batch is](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/520) |
| 8 | The batch plan and the execution disagree | the execution | [Decide what a paid launch costs and how large its batch is](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/520) |
| 9 | One decision contradicts its own batch count, and neither value matches the execution | the execution | [Decide what a paid launch costs and how large its batch is](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/520) |
| 10 | A spending ceiling attributed to a decision that explicitly sets none | the decisions that set it | [Decide what a paid launch costs and how large its batch is](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/520) |
| 11 | The in-domain scope stated as three datasets and as four | the design's four-dataset family; three is the count of lapse targets | [Decide the in-domain scope and the per-dataset counts](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/521) |
| 12 | A dataset's test positives counted two ways | the measured count | [Decide the in-domain scope and the per-dataset counts](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/521) |
| 13 | Two inventories of dataset sizes, one of them another repository's and unmarked | this repository's cost page | [Decide the in-domain scope and the per-dataset counts](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/521) |
| 14 | One model version described as never run, and as the era a committed diagnostic resolved to | the diagnostic's record; the version page was incomplete, not wrong | [Decide where the version timeline puts the v2.5 diagnostic](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/522) |

The exact passage, its current text, whether it gains a note or is corrected, and the note itself are in
[`docs/plans/document-authority-amendments.md`](plans/document-authority-amendments.md). This page
deliberately does not repeat them, so there is one place to update.

## What this page is not

- **Not a rank of people or of effort.** It ranks subjects, once.
- **Not a resolver of new questions.** A disagreement not listed here is a new decision. File it; do not
  quietly edit the losing side.
- **Not a licence to delete.** A passage that is merely older keeps its text and gains a note. A passage
  that is factually wrong — a misquoted figure, an inverted sign — is corrected in place, and the note
  quotes the wording it replaced, so the trail shows what was believed and when.

## If a new disagreement appears

1. State the passages and the subject they share — and say whether they are in two documents or one.
2. Ask which document owns that subject. If both do, take the earlier dated commitment. If it is one
   document, take the later dated statement.
3. Record the decision where it lives — the decision log for a rule, the owning analysis for a result.
4. Add the note to the losing passage, dated, naming the winner. Correct the text only if it is wrong
   rather than older, and quote the replaced wording in the note.
5. Add a row to the table above.
