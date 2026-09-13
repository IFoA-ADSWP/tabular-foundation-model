# Pilot 2 — what it costs, and why

**Written for a non-specialist reader.** One page. No jargon.

## The headline

| | Cost | In units of the run we have already done |
| --- | --- | --- |
| The first pilot's successful comparison (four datasets) | **5p** | 1 |
| **Pilot 2, as recommended** | **~$1.50** | about 31 |
| Pilot 2, repeating each experiment 15 times for confidence | ~$15 | about 312 |
| Pilot 2, and using the full datasets instead of a 2,000-row sample | ~$83 | about 1721 |
| Credit available | $9.60 | |

**The recommended path costs about a dollar fifty and fits the credit.** The two larger figures are
what the same experiment costs with two optional extras, explained below.

## Everything is priced in units of a run that already happened

We know what this costs because we have done it. The first pilot ran a complete comparison across
four insurance datasets — two methods, same data, same test rows — and the bill was **five pence**.

The larger figures are not a different kind of cost. They are that same comparison, **repeated and
enlarged**:

- **$1.50 is about 30 of those comparisons.**
- **$15 is about 300.**
- **$83 is about 1,700.**

So the question "why does it cost $83?" has a plain answer: **because at that level we run roughly
1,700 times as much computation.** Nothing in the figure is a mystery, a contingency, or a
management overhead. It is volume.

## The two things that make it bigger

**1. Doing it many times, so one lucky result cannot fool us (15x).**
Running an experiment once and seeing "it was better" is weak evidence — the split of data into
training and testing might simply have favoured one method. Repeating the same experiment fifteen
times on different slices turns *"it looked better once"* into *"it was better consistently"*, which
is what a reader should require before believing it.

Fifteen repeats therefore cost fifteen times as much as one. **This is optional**: three repeats give
a weaker but still real answer for a fifth of the price.

**2. Using all the data instead of a sample (about 10x).**
The first pilot worked from a 2,000-row sample of each dataset. The datasets actually hold up to
53,000 rows. Using all of them gives a sharper answer — and tests whether the effect grows with more
data, which is the question that decides whether any of this is worth doing in production.

It costs about ten times as much as the same experiment on the sample. **Also optional**, and
already gated behind a positive result at the smaller scale.

| | Extras included |
| --- | --- |
| ~$1.50 | neither |
| ~$15 | confidence |
| ~$83 | confidence and scale |

## What we test: four datasets, two experiments, and pooling

**Four datasets**, all used in both experiments:

| Dataset | Rows | Raw model | Fine-tuned (3 epochs) |
| --- | --- | --- | --- |
| coil2000 | 9,822 | 15.9 s | 35.6 s |
| eudirectlapse | 23,060 | 12.3 s | 36.4 s |
| uslapseagent | 29,317 | 6.3 s | 26.6 s |
| spanish_motor_lapse | 53,502 | 6.5 s | 18.3 s |

*(Times are the first pilot's measured figures, per dataset, at a 2,000-row sample.)*

### Experiment 1 — in-domain: fine-tune and test on the *same* dataset

Each dataset is split into training and test rows. The model is fine-tuned on a dataset's training
rows, then tested on **that same dataset's** held-out rows. Six methods per dataset: the existing
model (no training), fine-tuned at 3, 10 and 30 epochs, and two actuarial baselines.

**24 runs per repeat** (4 datasets x 6 methods). It answers: *does fine-tuning help at all, and does
training longer help more?*

### Experiment 2 — transfer: fine-tune on *other* datasets, test on a dataset never seen

Each dataset takes a turn being **held out entirely**. The model is fine-tuned on the *other*
datasets and tested on the one it has never seen. Seven methods per target dataset — including the
in-domain arm, so we can report the transfer gain as a fraction of the in-domain one.

**28 runs per repeat** (4 targets x 7 methods). It answers your generalisation question: *does
adaptation carry to a dataset the model has never seen?*

### Pooling — what it is, and why it costs the most

Pooling is how experiment 2 works: rather than fine-tuning on one dataset, the model is fine-tuned
on **rows concatenated from several datasets at once**, then tested on the held-out target. Three
pooled methods run per target:

- **All-comers pool** — every other dataset, harmonised, missing values imputed.
- **Same-schema pool** — only datasets with a compatible column layout. *Recommended first*, because
  a negative result under a coherent pool is interpretable; under an all-comers pool it is not.
- **A control** — the same pooled training with **shuffled labels**, so we can separate "pooling
  helped" from "any fine-tuning at all did something".

**One pooled method trains on three datasets' rows (3x a single dataset) for 30 epochs — 23x the
work of the 3-epoch single-dataset method the first pilot used.** Three of them run for each of four
targets. That is where the money goes.

### Runs and cost, both experiments

| Experiment | Runs per repeat | Cost per repeat | At 3 repeats | Cost | At 15 repeats | Cost |
| --- | --- | --- | --- | --- | --- | --- |
| **In-domain** (same dataset) | 24 | **$0.21** | 72 runs | $0.63 | 360 runs | $3.13 |
| **Transfer** (held-out dataset) | 28 | **$1.34** | 84 runs | $4.01 | 420 runs | $20.07 |
| **Total** | 52 | $1.55 | **156 runs** | **$4.64** | **780 runs** | **$23.20** |

**The transfer experiment costs about six times the in-domain one**, because each pooled method
trains on three datasets at once and three pooled methods run for each of four targets.

> **Correction to earlier figures in this document.** The previous version of this page put transfer
> at $4.08 for 15 repeats. That was wrong twice: it counted **two** pooled methods rather than three
> (the shuffled-label control is a full pooled training run), and it modelled the pool at 10 epochs
> instead of the 30 the design freezes. Transfer at 15 repeats is **$20.07**, not $4.08.

### What this does to the headline

| Scenario | Runs | Cost | vs ~$9.60 credit |
| --- | --- | --- | --- |
| **Lean** (probe + both experiments, 3 repeats) | ~156 | **~$4.70** | fits |
| **As the design specifies** (P1a + P1b, 15 repeats, transfer at sample scale) | ~780 | **~$31** | needs +$21 |
| **Everything at full data scale** | ~11,300 | **~$367** | not affordable |

**The single largest lever is still the epoch budget.** If the 5p probe shows three epochs is as good
as thirty, the pooled training divides by about eight: transfer at 15 repeats falls from **$20.07 to
about $2.35**, and the whole programme with it. That is the same five pence, buying a decision worth
hundreds.

**One number here is still soft**: the same-schema pool's size is undefined until the schemas are
inspected, and that arm is the recommended starting point. A smaller coherent pool makes transfer
proportionally cheaper.

## What the runs actually are, and where the volume comes from

A **run** is one dataset, one method, one repeat. Counting them:

| | Runs |
| --- | --- |
| Stage 1 (in-domain), one data scale, 15 repeats | 4 datasets x 4 methods x 15 = **240** |
| Stage 2 (transfer), 15 repeats | 4 target datasets x ~7 methods x 15 = **420** |
| The full programme | ~**1,140 runs** |

**But the cost is not spread evenly across those runs, and that is the important part.** Measured on
the first pilot's own timings, one repeat of Stage 1 breaks down as:

| Method | Time per repeat | Share of the work |
| --- | --- | --- |
| The existing model, no training | 41 s | **3%** |
| Fine-tuned, 3 epochs (what the first pilot did) | 117 s | **8%** |
| Fine-tuned, 10 epochs | 320 s | **23%** |
| Fine-tuned, 30 epochs (the library default) | 899 s | **65%** |

**Two-thirds of the entire computing volume is one method: training the model thirty times longer
than the first pilot trained it.** The baseline that answers "is this better than doing nothing?" is
3% of the cost. So the headline figures are not driven by "the number of runs" in any vague sense —
they are driven by a single, deliberate question: *does training longer help?*

### The three things that multiply the volume

| Knob | Effect on cost | What it buys |
| --- | --- | --- |
| Repeat each experiment 15 times | **x15** | so one lucky split of the data cannot produce a false result |
| Train 30 times longer instead of 3 | **x~10** on the training part | the actual hypothesis under test |
| Use all the rows instead of a sample | **x2.5 to x10** | whether the effect grows with more data |

### Why this is the argument for spending 5p first

If the small probe shows that **training longer does not help**, the 10- and 30-epoch methods are
dropped — and with them **89% of Stage 1's computing**. The programme shrinks to roughly a seventh
of the figures above, and the answer arrives just as clearly, because the remaining question (does
fine-tuning help at all) is answered by the 3-epoch method the first pilot already ran.

**That is the confidence argument in one line: the largest cost in the programme is attached to the
one question we can settle for five pence before committing to any of it.**

## Why the first pilot's 53p is *not* the benchmark

The first pilot spent **53p in total**, but only **8p of it produced a result**. The rest created
instances that failed, stalled, or never started — a connection that could not run commands, a
monitor that silently read nothing, machines that could never boot, and a licence check that
rejected every dataset.

That is what a first attempt at a new pipeline costs: **we were buying the pipeline, not the
result.** Six of the thirteen instances produced nothing at all, and five more never got past the
starting checks.

Two things follow, and neither is optimism:

- The right figure for planning Pilot 2 is **5p per successful comparison**, not the 53p average.
  Budgeting Pilot 2 at 53p would price in a mistake already paid for.
- **None of those four failures can recur silently.** Each now has an automatic check that refuses
  to run — and a test that fails if the check is ever removed. That is the difference between a
  one-off cost and a recurring one.

## The controls that stop us wasting money

| Control | What it prevents |
| --- | --- |
| Each run's instance is destroyed on **every** exit path, including a crash | a machine left running and billing |
| An independent watchdog checks every 5 minutes | a run that outlives its own shutdown |
| A hard price ceiling per machine (about 50p/hour) | drifting onto an expensive host |
| Retries are bounded (two) and skip a machine that just failed | an unattended retry loop spending freely |
| A pre-flight that **refuses to start** if a credential, the licence, or the data is wrong | paying for a run that cannot succeed |
| Every stage is gated: the next is funded only if the previous produced a result | spending on a question already answered |
| A **5p first step** that can stop the whole programme | committing to $15 before knowing it is worth it |
| Every run's true cost is recorded and checked against the account | the bill being a guess |

## What we will not do

- No run without a stated ceiling, agreed in advance.
- No unattended or open-ended spending.
- No stage funded before the previous one has produced a result.

## The one thing we are still assuming

Every figure above rests on one assumption: **how much longer training costs more.** We have
measured everything else; that relationship we have modelled.

It is worth **5p** to replace the assumption with a measurement — one small run, which also answers
whether training longer helps at all. If it does not, the programme stops there for five pence
rather than fifteen dollars.
