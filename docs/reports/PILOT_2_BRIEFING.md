# Pilot 2 — one-page briefing

**The question.** Does fine-tuning TabPFN beat the model straight out of the box, on our insurance data?

## What we already know

From the first pilot — four datasets, about **5p** of compute:

- **Fine-tuning made no reliable difference:** +0.001 to +0.009 ROC, one dataset slightly worse. That is inside the noise.
- **Using TabPFN at all beat the best baseline by +0.068** on one dataset, at roughly a third of the compute.
- **The loose end:** the first pilot trained the model **3 times**; the library's default is **30**. Nobody has tested the fair budget.

So TabPFN has earned its place. Fine-tuning has not — yet.

## What we propose

Five steps. Each is cheap, and each can stop the whole programme.

| # | Step | Cost | If it fails |
| --- | --- | --- | --- |
| 1 | Train longer — one dataset, one split | **7p** | **Stop.** The budget question is closed |
| 2 | Does it survive a different data split? | 12p | **Stop.** The first pilot's effect was split luck |
| 3 | Does it hold across all four datasets? | 43p | **Stop.** Report "no consistent gain" |
| 4 | Does it work on a dataset it has **never seen**? | from $1 | **Stop.** A clean transfer negative |
| 5 | How big is the effect, precisely? | only if 1–4 are positive | — |

**Nothing is bought in advance.** Each step's result decides whether the next one is paid for.

## What it costs

| | |
| --- | --- |
| **This plan** | **~$4.70** |
| The full design as written | ~$31 |

> **No programme-scale figure is quoted.** An earlier draft gave one (~$368) by stacking three
> unmeasured assumptions at once -- the training-length curve, the pool sizes and the row scaling --
> before the probe that measures the largest of them. A number for that scope returns only when it
> can be derived from measurements, not from a curve we have not run.
| Credit available | **$9.60** |

The comparison we have already run cost 5p, so the recommended path is about **90 of those**. The larger
figure is the same computation repeated fifteen times rather than three — volume, not overhead.

**What "modelled" means, and why it is said plainly:** every figure except the 5p and the credit comes
from the first pilot's measured timings multiplied by a plan — and the plan rests on **one**
relationship nobody has measured: how cost grows with training length. **The 7p first step measures
it.** No later figure should be quoted as a cost until it has been re-derived from that result.

## Why it is safe

Destroyed on **every** exit path including crashes · a watchdog checking every 5 minutes · a hard price ceiling per machine · a pre-flight that **refuses to start** if anything is wrong · every stage funded only after the last produced a result · and the first step costs **7p**.

## What we are asking for

**Two decisions now:**

1. **The route** — the staged, gated plan above (recommended), or the full design as written?
2. **Whether to fund the 7p first step.**

**Then a review, not a snap answer in this meeting.** The design has deliberate holes, and they need
reading rather than deciding on the spot. `PILOT_2_DECISION_LOG.md` holds each with options, a
recommendation and a blank:

3. Does the transfer test get to see rows from the dataset it is tested on?
4. Who owns the rule for **which datasets may be pooled together**? *(Undefined today — and it is a way to leak data.)*
5. How many datasets: the **4** we have used, the **12** the frontier work uses, or all **15**?
6. How much calibration drift is acceptable?
7. Which dataset is the primary target?

**We are asking for seven pence, not a programme budget — precisely because those holes exist.**
Nothing beyond the first step is funded until the step before it has produced a result, and if the
first step is negative the programme ends there with an answer rather than an invoice.

## The close

> "The whole thing starts for seven pence. If training longer doesn't help, we find that out for 7p instead of $15 — and either way we end up with an answer we can defend."

## Where to check the working

Everything below is appendix. It exists for whoever wants to challenge a number — not for the presenter.

| To check | Read |
| --- | --- |
| What the first pilot actually found | `FINE_TUNING_PILOT_RESULTS.md` |
| What it did and did **not** test | `SMOKE_TEST_SCOPE.md` |
| The plan as a graph, and what each stopping point lets us claim | `PILOT_2_DECISION_GRAPH.md` |
| The full experiment specification | `PILOT_2_DESIGN.md` |
| Why this is a correction, not a scale-up — and the interaction policy | `PILOT_2_DESIGN_ALTERNATIVE.md` |
| Every cost figure, in units of a run we have already done | `PILOT_2_COST_AND_CONTROLS.md` |
| How the numbers will be computed, and what counts as a positive | `PILOT_2_STATISTICAL_ANALYSIS_PLAN.md` |
| The decisions, with options and recommendations | `PILOT_2_DECISION_LOG.md` |
| Why the historic "don't chase fine-tuning" verdict is unusable | `HISTORIC_FINETUNING_APPRAISAL.md` |
| The infrastructure and the analysis code | PR #172 |
