# Fine-tuning TabPFN on insurance data — the Phase 2 outcome

> **Status:** current as of 2026-11-08. This is the closing statement of Phase 2. The pre-result narrative
> — how the programme arrived here — remains in `docs/current/FINETUNING_STATUS_BRIEF.md`, kept as history.

## 1. The answer

Fine-tuning TabPFN produced a real but very small gain on one of four insurance datasets, and no gain we
can detect on two others; the fourth could not be measured at the precision the design required. (Three of
the four targets are lapse outcomes; `coil2000` predicts caravan-insurance take-up, so "the lapse datasets"
is a convenience name for this family, not a description of all four.)

| Dataset | Δ ROC AUC | 95% interval | Reading |
| --- | --- | --- | --- |
| `uslapseagent` (anchor) | **+0.0035** | [+0.00272, +0.00428] | **gain** — the whole interval above δ |
| `eudirectlapse` | +0.0007 | [−0.0003, +0.0018] | **equivalence** — bounded inside δ |
| `spanish_motor_lapse` | +0.0003 | [−0.0002, +0.0008] | **equivalence** — bounded inside δ |
| `coil2000` | — | — | **stopped** — not measurable at this design |

The bar was **δ = 0.002 ROC AUC**, agreed on 2026-11-03 — before the replication and both breadth cells, and
after the anchor's first pass had failed. A cell is a gain when its whole interval sits above δ, an
equivalence when its whole interval sits inside ±δ, and unresolved otherwise. One cell cleared the bar, two
were bounded inside it, and one never ran because it could not be bounded.

What this says: adapting the weights helps on one dataset, by an amount you would not notice in a
deployment decision. What it does not say: that it helps on these datasets generally.

## 2. Should you care?

Less than the choice of model.

Raw TabPFN already led the actuarial baselines on the anchor dataset before any fine-tuning: 0.9363 ROC
AUC against 0.9271 for the GLM and 0.9297 for CatBoost
([owner](../reference/FINE_TUNING_PILOT_RESULTS.md)). On `coil2000` the margin over the best baseline is
**+0.068** (same owner). Set that against the anchor's +0.0035 and the tuning lever is a small fraction of
the choice lever.

Two cautions on that comparison, both of which a careful reader will ask for. The +0.068 is measured on a
different dataset, against a different contrast, so it is context for the size of the gain rather than a
ratio — the owning analysis makes the same point. And the gain is **within-model** by construction: it is
an improvement in TabPFN's own accuracy, not a narrowing of the gap to another method. Choosing whether to
use a tabular foundation model at all remains a far larger decision than choosing whether to tune one.

Costs, measured rather than modelled: the anchor's replication launch was **$0.188**
([the replication result](../analyses/finetuning_replication_result.md)); a four-arm launch at the larger
training budget was **$0.0368** ([the cost page](FINETUNING_COST_AND_CONTROLS.md)); and the Spanish cell
cost **$0.3315** — a **$0.065** replication, a **$0.153** probe across five attempts of which three failed,
and a **$0.043** single-seed measurement ([D20](FINETUNING_DECISION_LOG.md)). A programme-scale figure was
withdrawn for being modelled rather than measured, and should not be quoted.

## 3. Dataset by dataset

All three measured cells share one design: in-domain fine-tuning of the same checkpoint, at the larger
training budget, evaluated against the **`A_raw` arm of the same seeds and the same launch** — a paired
comparison, not a comparison against a stored baseline from an earlier run. The rung carried forward was
30 epochs, the top of the ladder tested. What differs between them is the seed count, and that was computed
from each dataset's own probe rather than chosen.

### `uslapseagent` — the anchor

Twenty-eight fresh seeds, 55–82, disjoint from the ten probe seeds that sized the run. The interval sits
entirely above δ, so this is a clearing rather than a marginal pass. Brier's worst seed was 0.0003 worse against
an allowance of 0.001; the null control's false-positive rate was 0.0000 over 5,000 label permutations per
seed, as pre-registered.

> **2026-11-09** (#518). This read "+0.0003 against an allowance of +0.001", which left the direction to the reader's
> knowledge of the sign convention. It is an increase of 0.0003 — worse, and inside the allowance.

Evidence: `results/20261104T123839Z/`, and the owning analysis
[`finetuning_replication_result.md`](../analyses/finetuning_replication_result.md).

### `eudirectlapse`

The dataset where, at full data, a GLM beats TabPFN — which is why it was the first breadth target.
**238 seeds** across twenty captured launches, seeds 93–330.

The effect is bounded inside δ and not separable from zero. One rung was replicated, 30 epochs; the
probe's ladder was non-monotone and every interval covered zero, so a cheaper `B_ft3` replication was
declined and this stands as a statement about the top rung. Brier's worst seed sits at the guard, so this
is **not** a calibration claim.

Evidence: twenty run directories under `results/`, and the owning analysis
[`finetuning_breadth_eudirectlapse_result.md`](../analyses/finetuning_breadth_eudirectlapse_result.md).

### `spanish_motor_lapse`

**16 seeds**, 341–356, with a between-seed standard deviation of 0.00093 — small enough that sixteen seeds
bound the effect where another dataset needed hundreds. The ladder was monotone, so carrying the top rung
was the conservative choice rather than a convenience.

The interval is the tightest of the three, and it sits inside δ.

Evidence: the owning analysis
[`finetuning_breadth_spanish_result.md`](../analyses/finetuning_breadth_spanish_result.md).

### `coil2000` — stopped, not run

`coil2000` carries 586 positives in 9,822 rows. The best paired half-width it can reach is 0.0149, at 4,000
test rows, against the design's 0.006 floor — two and a half times too wide at its most favourable split
([`FINETUNING_DECISION_LOG.md`](FINETUNING_DECISION_LOG.md), D21). No seed count and no budget closes that
gap, because the constraint is the number of positives, not the spend.

This is a stop on a property of the dataset, not a null result and not an omission. It is recorded in the
decision log (D21, amended by D22, which withdrew the part of D21 that argued about seeds rather than
resolution).

## 4. Four ways to misread this

**Equivalence is not "no effect found".** On `eudirectlapse` and `spanish_motor_lapse` the intervals bound
the effect *under* the bar. That is a stronger statement than failing to reach it, and it is the difference
between "we could not see it" and "it is smaller than we said we would care about".

**Small is not nothing.** One dataset cleared δ with its whole interval above it. Summarising the result as
"minimal improvement across three datasets" flattens one gain and two bounds into a single non-finding, and
loses the only cell in which the intervention worked.

**Untested is not failed.** Pooled transfer — fine-tuning on other datasets and applying the result to a
target the model never saw — has never been run. The `C` and `D` pooled arms and the shuffled-label control
are unexecuted, not unsuccessful. Phase 3 was cancelled before breadth began and was never reinstated for
transfer, so there is no result in either direction.

**A missing estimand is not a null.** The statistical analysis plan names the paired difference in log loss
as its primary estimand; this report carries no log-loss figure, because none was computed for Phase 2. The
claim was tested on ROC AUC with a Brier veto, which is what the tables above report. The absence is a gap in
the reporting, not evidence that the effect is absent on that measure.

## 5. What would change our mind

A transfer result would be the thing that turns a dataset-specific gain into something worth owning. The
design already states what it would take, and the bar is not δ:

- a named target dataset, with its held-out test fingerprint recorded;
- a frozen schema-matching rule and source-pool manifest, asserting that no row of the target is in it;
- the `R_random` control — the same pooled training with shuffled source labels;
- the metric, calibration tolerance and minimum practical effect declared before any result is seen.

A transfer result counts as positive only if the coherent-pool arm beats the target's raw baseline on the
pre-registered interval rule **and** beats the shuffled-label control. A positive heterogeneous-pool result
cannot rescue a negative coherent one. And it would be read against the margin between methods, not against
δ — a gain that clears 0.002 but moves nothing against a 0.068 gap has not changed the adoption decision.

None of this is authorised. It is a candidate with a written gate, not a plan with a budget.

## 6. How to check us

Every claim in this report names the document that owns it. Follow the link and you reach the analysis that
holds the number; follow that document's own evidence section and you reach the committed artefact.

- `uslapseagent` — [`finetuning_replication_result.md`](../analyses/finetuning_replication_result.md),
  evidence in `results/20261104T123839Z/`.
- `eudirectlapse` — [`finetuning_breadth_eudirectlapse_result.md`](../analyses/finetuning_breadth_eudirectlapse_result.md),
  evidence across twenty `results/` directories.
- `spanish_motor_lapse` — [`finetuning_breadth_spanish_result.md`](../analyses/finetuning_breadth_spanish_result.md),
  whose launch records live under `outputs/gpu-pilot/` and are cited by description because no run id was
  captured for them.
- `coil2000` — the decision log, `docs/current/FINETUNING_DECISION_LOG.md` (D21, D22).

Every measured cell ran on **`v3_default`** (tabpfn 8.5.0, the checkpoint asserted before each launch), and
so did the baseline comparison in section 2 — that document's version stamp records the weights and the
library, and states that its numbers sit on the same model line as the frontier work rather than the frozen
v2-era tables. The published fine-tuning literature is v2-based, so its guidance transfers and its numbers
do not.

The diagnostic tables — profiling and importance — are exported with verified hashes under
`docs/analyses/data/`, and `docs/analyses/data/README.md` states what each column means and what the export
checks. They are not needed to read this result; they are where a reader goes next if the question is *why*
rather than *how much*.
