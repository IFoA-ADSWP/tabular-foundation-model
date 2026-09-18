# Proposal — the next tests

> **Status: current, 17 September.** A proposal, not a commitment. Nothing here is approved or funded, and no
> GPU spend is authorised by this document.
> **Owners:** the figures are accounted in `PILOT_2_COST_AND_CONTROLS.md`; the judging rules in
> `PILOT_2_STATISTICAL_ANALYSIS_PLAN.md`; the run itself in `NEXT_RUN.md`. This page states what is being asked.

## What we asked, and what we found

Does fine-tuning TabPFN beat using it as-is, on lapse prediction? We ran that test twice.

At **2,000 training rows**, fine-tuning was worse: every epoch budget at or below the raw model. At **10,000
rows**, every budget beat the raw model, with intervals excluding zero and calibration improving alongside
(+0.0022, +0.0026, +0.0034 ROC AUC, rising with the budget).

The difference between the two runs was not the data or the model. It was a row cap we had set ourselves in
the loader and then forgotten. The model is documented to 50,000 rows.

**The finding: fine-tuning helps on lapse data above a certain row count. Below it, it actively hurts.**

## The proposal — three stages, each gated on the one before

**Stage 1. Replicate the 10,000-row result at two further seeds.** About **$0.037 per run**, measured. One code
change is needed first: the seed is hard-coded, so repeating the run today would reproduce the same split and
prove nothing.

**Stage 2. If it holds, the same ladder on a second lapse dataset** (`spanish_motor_lapse`).

**Stage 3. Only then, an efficient-adaptation arm** — parameter-efficient or meta-learning. That carries a
higher bar than before: full fine-tuning now works, so it must *beat* it, not merely match it.

## What we are asking for

**Stage 1 only.** About **$0.07 for two runs, $0.11 for three**. A positive result from stage 1 releases stage 2
and nothing else.

## What would stop it

**If a second seed comes back flat or worse, the line stops** — rather than extending to more seeds or more
datasets. Fixed in advance, not judged afterwards.

## What we own up front

- **One seed so far.** The intervals are within-run and say nothing about seed variation. Stage 1 tests exactly that.
- **No temporal split is possible.** No lapse dataset in our set has a usable time column, so every result is
  conditional on a random split.
- **The published studies are a generation behind** — they are TabPFN v2, we run v3. Their guidance transfers,
  their numbers do not.
- **Our own materials said the opposite until today.** "Fine-tuning degrades" appears in the presentation plan;
  it is corrected there, and the 2,000-row negative it came from is marked superseded rather than deleted.

## What this is not

It is not the wider transfer programme. That is a separate proposal, still contingent, and it should not be
funded by this one.

## Where to check the working

`FINDINGS.md` — nine rows: what we currently believe, and which document owns each claim.
`FINE_TUNING_EXPERIMENT_DESIGN.md` — the design, in its front section.
`NEXT_RUN.md` — the run, the acceptance test per seed, the stop rule, the evidence obligations.
