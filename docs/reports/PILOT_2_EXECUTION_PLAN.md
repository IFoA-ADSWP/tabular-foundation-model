# Pilot 2 — execution plan: five gated steps

**Goal.** Answer one question: *does fine-tuning TabPFN beat raw TabPFN and the actuarial baselines
on insurance data — first on the same dataset, then on a dataset it has never seen?* Nothing else is
in scope.

**Method.** Five steps, ordered so each is cheap enough to abandon, and each is funded only when the
step before it justifies it. No experiment is bought in advance.

| # | Step | Cost | The assumption it tests | Stop rule |
| --- | --- | --- | --- | --- |
| 0 | **Probe.** One dataset, one split, the full training ladder (3 / 10 / 30 epochs) | **7c** | *training longer than 3 epochs helps.* This one assumption carries 65% of the programme's cost | If the ladder is flat or degrades: stop. The budget hypothesis is dead, and everything after this can be answered at 3 epochs for cents |
| 1 | **Is it real?** One dataset, 3 seeds, one split, winning budget vs raw | **2-11c** | *the in-domain effect survives more than one split* | If the effect vanishes: stop. R1's +0.001-0.010 was split luck |
| 2 | **Does it hold across datasets?** 4 datasets, 3 seeds, one split | **7-43c** | *the effect generalises across the four datasets* | If only one dataset shows it: report "no consistent gain" and **do not fund transfer** |
| 3 | **Is there any transfer signal?** One held-out target, coherent pool + label-shuffled control, 3 seeds, one split | **12c-$1.02** | *adaptation carries to an unseen dataset at all* | If negative: stop. That is a clean, interpretable negative for transfer — the answer the historic work never established |
| 4 | **All targets.** 4 held-out targets, 3 seeds, one split | **35c-$3.07** | *the signal is consistent across targets* | Report at the sample scale; decide on widening only with a positive in hand |
| 5 | **Confidence.** Repeat the decisive comparisons at 5 folds | **~$0.9-$6.3** | *the effect is stable across data splits* | Optional, and only ever bought **after** an effect exists |

**Steps 0-4 cost about $4.70, or about 66c if the probe shows three epochs is enough.** The design as
written costs ~$31; the full-scale version ~$368.

**Two notes on method, because both affected an earlier revision of this page.** The transfer steps
count **three** pooled arms per target (`C_pooled_all`, `D_pooled_schema`, and the label-shuffled
control `R_random`, which is a full pooled training run), and **step 4 does not re-run step 3's
target** — its result is carried forward. An earlier revision did neither and understated the total. This path reaches the same decisions.

## The assumptions we choose to make

Being surgical means deciding in advance what we are willing to *assume* rather than measure, and
choosing assumptions that are cheap to be wrong about.

1. **An effect invisible on one split will not be rescued by five folds.** If three seeds on a single
   split cannot see it, more folds buy precision on a null. Five folds are the *last* thing we buy,
   not the first.
2. **The test set's own noise is the floor, and we have already measured it.** R1's unpaired 95%
   interval width on ROC is 0.031-0.118 depending on the dataset, while R1's own in-domain deltas
   were 0.0008-0.0095 — an order of magnitude inside it. Comparing each delta against that width
   tells us whether more repeats are worth buying, so we need not buy them to find out.
3. **The heterogeneous pool is only worth running if the coherent one is interpretable.** This is
   already the design's pre-registered order; it saves a third of the transfer cost at every scale
   until the coherent pool has a result.
4. **Full data scale is only worth running if the sample shows the effect growing with rows.** The
   sample-to-full multiplier is ~14x; it is a reward for evidence, not an entry fee.
5. **The cheap baselines do not need re-running at every scale.** The GLM and CatBoost arms take
   seconds on CPU and are already recorded at every scale they matter.

## What we deliberately do not do

These are the experiments that would fill a schedule without changing the answer:

- five folds before an effect exists on one split;
- four targets before one target shows any signal;
- two pool policies before the coherent one has been read;
- the full epoch ladder at full data scale;
- fifteen repeats where the test set's own noise exceeds the effect being measured;
- any full-dataset run before the sample shows the effect growing.

## Monitoring: what we record at every step

Each step reports **the effect size, its interval, and the test set's noise floor**, and then asks a
single question: *is the effect bigger than the noise?* Only a yes buys the next step.

That is the whole control mechanism. Progress is visible after every step, the programme can stop at
any step with a reportable answer, and the largest cost in it sits behind the cheapest test in it.
