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
