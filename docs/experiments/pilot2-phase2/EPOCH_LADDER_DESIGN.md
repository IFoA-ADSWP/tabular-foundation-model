# Epoch ladder — the design's resolution, and why each factor is what it is

**Status:** current — design record, written 2026-11-22 while the severity runs were executing.
**Tickets:** #672 (the ladder), #629 (the direction decision and its 2026-11-21 amendment).

This note records what the frame buys and what it cannot resolve. It does **not** move a bar: the
bar, falsifier, analysis plan and 20-seed count were frozen by the owner on 2026-11-21 in #672, and
a moved bar is a new ticket. It is written because the first verdict (`eudirectlapse`, flat) can be
read as "no dose-response" when the design's honest statement is "no detectable dose-response at
this resolution", and nothing in the tree said which.

## The frame, and what each factor buys

| Factor | Value | Why it is that value | What it would cost to reduce |
| --- | --- | --- | --- |
| Arms | `A_raw`, `B_ft3`, `B_ft10`, `B_ft30` | the **shape** is the question. With one fine-tuned rung you cannot separate "fine-tuning at all" from "more epochs"; with only raw and 30 you cannot tell saturation from a step | dropping `B_ft10` removes the 30−10 vs 10−3 contrast — the comparison that distinguishes "the gain saturates" from "the gain is early" |
| Seeds | 20, paired across arms, seeds 1001–1020 | the unit of inference. Arms share test rows within a seed, so the *difference* is tested, not the levels | halving to 10 widens every interval by √2 and raises the detectable effect from ~0.9 to ~1.3 AUC points (below) |
| Folds | 5, the campaign's own | folds define the **splits**; they are the estimand, not a knob. Changing them compares numbers computed on different rows | changing them would make the ladder's numbers incomparable with the fair test and the baselines |
| Targets | `eudirectlapse`, `freMTPL2sev`, `spanish_motor_severity` | one target is an anecdote; the frequency targets already show a positive effect, so the open question is whether severity — where 30 epochs is worse — behaves the same in a second dataset | Spanish costs ~$1.5 and caps at 4,760 rows, so it is the cheap half of the class claim |
| Rows | 10,000, or the data's cap | fixed by the earlier row ladder (#674), which showed the gain arrives by 5,000 rows and then plateaus | fewer rows would confound the epoch axis with the row axis |

## The resolution arithmetic

The paired spread is measurable from the first verdict. `eudirectlapse`, 30−raw = **+0.0021 AUC**
with **t = 0.63** over **n = 20** paired seeds gives a per-seed SD of the difference of about
**0.0145**. At 80 % power and α = 0.05 (two-sided):

| Seeds | Smallest detectable 30−raw difference |
| --- | --- |
| 20 (as run) | `2.8 × 0.0145 / √20` ≈ **0.009 AUROC points** |
| 10 | `2.8 × 0.0145 / √10` ≈ **0.013 AUROC points** |
| 40 | ≈ **0.006 AUROC points** |

So the design's observed resolution is about **0.9 AUROC points** on a classification target, and the
`eudirectlapse` result (interval covering zero, effects of ~0.2 points) is **inside** that floor.

**Corrected 2026-11-22.** The t and SD above are the recomputed values (0.63 and 0.0145); the first
version quoted 0.65 and 0.0144 from the earlier ticket comment. The **registered** floor is a
different number and was not met: #672 froze an MDE of 0.0021 AUROC (SD 0.0034), while the observed
paired SD is 0.0145, so the run's half-width is ~0.0068 — about 4× the registered MDE. UNRESOLVED
remains the right verdict, but it is a statement at the observed resolution, not at the registered
one.
For the severity targets the metric is a relative weighted RMSE, whose paired SD has not been
measured; its resolution is of a similar order and should be read from the intervals the run
produces, not assumed.

## What this means for reading a verdict

- A **flat** ladder is a statement at this resolution: "no effect larger than ~0.9 points". It is
  not "no effect".
- A **monotone** ladder with intervals clearing zero is a positive finding the design was built for.
- `B_ft30` losing to `A_raw` by ~1 % (French severity) is at the edge of resolution; its interval is
  the claim, not the point estimate.
- Twenty seeds is **generous in arms and folds, tight in seeds**. If the programme later needs
  sub-1 % effects, that is a larger design (≈40 seeds for ~0.6 points), and the analysis plan's
  escalation rule says it must be a dated amendment before a run, not a quiet increase.

## What is not claimed here

No new bar, no new falsifier, no re-reading of any result. The frozen decision rule in #672 stands;
this note says what frame produced it and where its floor is.
