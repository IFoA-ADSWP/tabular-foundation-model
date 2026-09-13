# Pilot 2 — the decision graph

**How to read this page.** Each node is one experiment, and each node is also a **stopping point**.
The edges are outcomes, not hopes: a designed experiment has to say in advance what it will do with
each one. Costs are cumulative along a path; the figure at each node is what *that step* adds.

Why a graph rather than a list: the design's whole claim is that **nothing is bought in advance**, and
that claim is a statement about the *edges* — what happens after each result — not about the steps.

## Recommendation

**Adopt the staged-isolation design as the route. Keep the bundled design as the reference
specification. Let the 7p probe decide the rest.**

| Decision | Recommendation | Why |
| --- | --- | --- |
| **Route** | staged isolation (this page) | reaches the same decisions as the bundled design for ~$4.15, and a negative **names its cause** |
| **First spend** | the **7p probe** | tests the assumption carrying 65% of the programme's cost; if it fails, the programme stops for seven pence |
| **Datasets** | the four registered ones for the in-domain steps; the pool decided *after* the probe | if 3 epochs wins, an 11-dataset pool costs ~$7; if 30 epochs is needed, the pool must stay small (same-schema) |
| **Interactions** | gated off-ramp only | $1.11 for an attributable answer, against $31 for an ambiguous one |
| **Repeat structure** | 3 seeds x 1 split first; 5 folds only after an effect exists | a visible effect is a precondition for buying precision, not a reward for having none |
| **Budget** | ~$4.15 to the same decisions as the ~$31 design | fits the ~$9.60 credit with **no top-up** |
| **Bundled design** | retained as the reference specification | the isolation route arrives at it once each factor is known to matter — a better position to spend from, not a retreat |

**Not recommended, for the record:** running the bundled design first (~$31, needs a ~$21 top-up, and
a negative would be unattributable); running at full data scale (~$367, with no evidence yet that the
effect grows with rows); pursuing an interaction before the isolation steps have produced a mechanism
and a near-miss to justify it.

**Spending note.** The recommendation is that the next action is the 7p probe — which is spend, and
therefore needs an explicit, current go-ahead. Nothing is provisioned on the strength of this page.

## The graph

```mermaid
flowchart TD
    S0["<b>0 · Probe</b> — 7c<br/>1 dataset, 1 split, 3/10/30 ladder<br/><i>does training longer help?</i>"]
    S0N["<b>Budget hypothesis dead</b><br/>report it; everything below<br/>is answerable at 3 epochs for cents"]
    S1["<b>1 · Is it real?</b> — 12-14c<br/>1 dataset, 3 seeds, 1 split<br/><i>does the effect survive a split?</i>"]
    S1N["<b>Stop.</b> Report: the R1<br/>delta was split luck"]
    S2["<b>2 · Across datasets</b> — 7-43c<br/>4 datasets, 3 seeds, 1 split<br/><i>does it hold beyond one dataset?</i>"]
    S2N["<b>Stop.</b> Report: no consistent<br/>gain. Transfer is not funded"]
    S3["<b>3 · Transfer signal</b> — 8-70c<br/>1 target + shuffled-label control<br/><i>does adaptation carry at all?</i>"]
    S3N["<b>Stop.</b> Report: a clean,<br/>interpretable transfer negative"]
    S4["<b>4 · All targets</b> — 33c-$2.82<br/>4 held-out targets<br/><i>is the signal consistent?</i>"]
    S5["<b>5 · Confidence</b> — $0.41-$3.24<br/>5-fold on the decisive arms<br/><i>how large is it, precisely?</i>"]
    OUT["<b>Reportable answer</b><br/>effect size, interval, noise floor"]
    INT{"<b>Interaction gate</b><br/>all four criteria met?<br/>mechanism · implied by isolation<br/>attributing design · pre-registered"}
    I1["<b>Designed 2x2 probe</b> — $1.11<br/>training length x pool, one target<br/>+ control at both pooled cells"]

    S0 -->|"flat or degrading"| S0N
    S0 -->|"gain grows with epochs"| S1
    S0N --> OUT
    S1 -->|"below the noise floor"| S1N
    S1 -->|"effect confirmed"| S2
    S1N --> OUT
    S2 -->|"one dataset only"| S2N
    S2 -->|"consistent"| S3
    S2N --> OUT
    S3 -->|"negative vs the control"| S3N
    S3 -->|"positive"| S4
    S3N --> OUT
    S4 --> S5
    S5 --> OUT
    S2 -.->|"two near-misses,<br/>in the predicted direction"| INT
    S3 -.->|"main effects unclear<br/>but mechanistically linked"| INT
    INT -->|"all four met"| I1
    INT -->|"any criterion missing"| OUT
    I1 --> OUT

    classDef stop fill:#5b2c2c,stroke:#c66,color:#fff
    classDef go fill:#1e3a2f,stroke:#4c9,color:#fff
    classDef gate fill:#3a3320,stroke:#cc9,color:#fff
    class S0N,S1N,S2N,S3N stop
    class S1,S2,S3,S4,S5,I1 go
    class INT gate
```

## The same information as a table

| # | Test | Comparison | Positive → | Negative → | Cost | Cumulative |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | Training ladder, 1 dataset, 1 split | 30 vs 10 vs 3 epochs | step 1 | **stop, report** | 7c | 7c |
| 1 | 1 dataset, 3 seeds, 1 split | fine-tuned vs raw | step 2 | **stop, report** | 12-14c | ~20c |
| 2 | 4 datasets, 3 seeds, 1 split | fine-tuned vs raw, per dataset | step 3 | **stop, report, no transfer** | 7-43c | ~60c |
| 3 | 1 target, coherent pool + control | pooled vs raw, vs shuffled labels | step 4 | **stop, report** | 8-70c | ~$1.30 |
| 4 | 4 targets | pooled vs raw, per target | step 5 | report at sample scale | 33c-$2.82 | ~$4.15 |
| 5 | 5-fold on decisive arms | effect with an interval | report | report | $0.41-$3.24 | ~$7.40 |
| I | Interaction, 2x2, 1 target | difference of differences | report as an estimate | report | $1.11 | — |

## What each stopping point lets us claim

This is the table that matters for assessing the proposal: **every leaf is a deliverable**, including
the negative ones.

| If we stop at | We can state |
| --- | --- |
| 0 | "Training longer than 3 epochs does not improve fine-tuned TabPFN on this dataset." The budget hypothesis — the largest cost in the programme — is closed |
| 1 | "The R1 in-domain delta was within split variation." No fine-tuning case at any scale |
| 2 | "Fine-tuning gives no consistent gain across the four datasets." In-domain adaptation is not supported |
| 3 | "Adaptation does not transfer to an unseen dataset under a coherent pool." The question the historic work never answered cleanly |
| 4 | "Transfer is consistent across the four held-out targets, at sample scale." |
| 5 | "The effect is *X* with interval *Y*, against a noise floor of *Z*." The definitive figure |
| I | "Factors *P* and *Q* interact: *X* with interval *Y*." Attributable, because the design isolates the pair |

## Three things a plain binary tree would get wrong

1. **Outcomes are not binary.** Each node's rule is a comparison against R1's *measured* noise floor
   (0.031-0.118 on ROC), not a yes/no. The graph branches on "clears the noise", "below it", and — not
   drawn, because it is the dangerous branch — "inconclusive". **The pre-registered rule for
   inconclusive is what stops this being a fishing trip**: it is stated before the run (extend the
   repeats to a pre-set maximum, or report the interval as inconclusive), never decided afterwards.
2. **Every node is also an exit.** The stop edges are first-class, and several are the *likely*
   outcome. A tree that only draws the happy path implies the programme is expected to reach the
   bottom, which is the opposite of the design's claim.
3. **Cost is cumulative along a path.** A per-step figure without the running total lets a reader add
   it up wrongly in either direction — as a fixed cost of the programme, or as never large.

## The interaction is an off-ramp, not a branch

Drawn dashed, entered from steps 2 and 3 only, and **gated by four criteria**: a stated technical
mechanism, an isolation result that implies it (two near-misses in the predicted direction), a design
that attributes it, and pre-registration. If any criterion is missing, the edge returns to *report*
rather than to *run*.

That is the whole visual argument for "isolation by default, interaction by decision": **the default
path never touches the interaction node, and the off-ramp has a guard on it.**
