# The probe's result, and which pre-registered outcome it lands in

**Pre-registration:** `PROBE_PLAN.md` (merged, #173). **Run:** `20260913T225032Z`, pinned to
`d5aebe7`, RTX PRO 4000, 2.53 min, **$0.0122**. All four arms ran:
`ARM SUMMARY ok= A_raw B_ft3 B_ft10 B_ft30 failed=none`. Every arm's `meta.json` declares a
`predictions_sha256`, so the artifacts are attributable to this run.

## The measurement

Paired on ROC AUC over matching slots, baseline `A_raw`, as the statistical plan specifies.

| arm | ROC AUC | PR AUC | Brier | log loss | row-epochs | Δ vs A_raw (95% paired CI) |
| --- | --- | --- | --- | --- | --- | --- |
| `A_raw` | 0.9363 | 0.8367 | 0.0868 | — | — | baseline |
| `B_ft3` | 0.9338 | 0.8324 | 0.0887 | 0.2728 | 6,000 | **-0.0025** [-0.0047, -0.0003] |
| `B_ft10` | 0.9353 | 0.8342 | 0.0879 | 0.2699 | 20,000 | -0.0009 [-0.0032, +0.0014] |
| `B_ft30` | 0.9349 | 0.8403 | 0.0875 | 0.2677 | 60,000 | -0.0013 [-0.0055, +0.0030] |

Resolution actually achieved: paired CI half-widths of **0.0022 / 0.0023 / 0.0043**, i.e. this run could
have detected an effect of the size the first pilot hinted at — and found none.

## Both preconditions are discharged

**1. The executed budget is recorded, and early stopping is pinned.** `early_stopping: False` was passed
explicitly, and the ladder carries row-epochs (6,000 / 20,000 / 60,000), so "3, 10, 30 epochs" means the
training it names rather than whatever a library default allowed.

**2. The replication gate passes.** It asked whether `B_ft3` reproduces the first pilot, because if it
missed, nothing else in the run would be interpretable:

- `A_raw` reproduced the first pilot's value to **0.0003** (0.9363 against 0.9360, from the committed
  artifact) — the pipeline has not silently changed.
- The first pilot's `B_in_domain` at 3 epochs measured **-0.0008** on uslapseagent, and that value falls
  **inside** this run's interval for `B_ft3`, [-0.0047, -0.0003].

So the run is interpretable, and the gate did its job rather than being waved through.

## The outcome

Of the three pre-registered branches, this is **outcome 3**:

> **The ladder is flat and the arms do not beat `A_raw`** → the fine-tuning hypothesis is dead at this
> scale; reported with its minimum detectable effect beside it.

Not outcome 1 — nothing rises. Not outcome 2 — the arms do not beat the baseline either; every rung sits
at or below it, and the most negative comparison (`B_ft3`) is the one whose interval excludes zero.

**Minimum detectable effect beside it, as the pre-registration demands:** the measured half-widths are
0.0022–0.0043, and the effects observed are -0.0009 to -0.0025. The effects are the size of the
resolution, in the wrong direction.

**The one signal that moves in order is calibration, not ranking.** From 3 to 30 epochs, PR AUC rises
0.8324 → 0.8342 → 0.8403, Brier falls 0.0887 → 0.0879 → 0.0875, log loss falls 0.2728 → 0.2699 → 0.2677,
monotonically at every step. ROC AUC, the pre-registered primary, does not move. So if fine-tuning is
pursued at all, the effect appears to live in the probability head rather than the ranking — a secondary
observation, not a substitute for the primary result.

## Limits, stated rather than implied

- **One split, one seed** (`repeats=1`, 1,000 test rows). No interval here is a claim about repeats.
- **2,000 training rows.** The verdict is scale-conditional, as the plan says up front.
- **Small counts:** 369 test positives in this dataset. The intervals are honest about that; the effects
  are smaller than they are.
- **A reporting check is outstanding.** `B_ft3` is marked `***` (the tool's marker for "interval covers
  zero") while its interval prints as [-0.0047, -0.0003], which does not cover zero. Either the bounds are
  rounded from something that does, or the marker disagrees with the bound. **Do not quote `B_ft3` as
  resolvable until that is settled**, and note the verdict above does not depend on it: outcomes 2 and 3
  are distinguished by whether the arms *beat* `A_raw`, and none do.
- **The pulled `pilot_metrics.parquet` is stale.** The box's aggregate step refused to overwrite the
  committed aggregate file (the same class of collision that blocked `A_raw` before #179). This analysis
  used the per-arm records, which are current and hashed.

## What this does to the wider proposal

The wider testing's first gate was in-domain: show that fine-tuning helps before transfer is funded. **The
probe's stop rule fires on that gate** — training longer does not help, and fine-tuning does not beat the
raw model on the primary metric at this scale. `PILOT_2_EXECUTION_PLAN.md` step 0 says *flat or degrading →
stop*, and that is what happened.

So the wider proposal is **not** earned on the basis it was designed to test. That is a decision for the
team, not for this document, and it should be taken with the calibration trend in view: it may be worth one
narrow question about the probability head, and it is not worth the staged programme as written.

## Cost, corrected

| | |
| --- | --- |
| **the probe run itself** | **$0.0122** — 2.53 min on an RTX PRO 4000 at $0.2893/hr |
| **reaching it** — the seven runs of 13 Sep, four of which produced no result | **$0.0933** |
| **the account's authoritative cumulative spend**, all work on this account | **$0.5461** |

An earlier draft of this section said $0.0922: that was my arithmetic, and it missed one run. The ledger
now sums to $0.0933 for 13 Sep — the figure above — and the account's own cumulative total is $0.5461
against the ledger's $0.6189, so the per-run figures are estimates and **the account is the number to
quote**. The distinction that matters for the wider decision is the first row against the second: the
answer cost $0.0122, and the pipeline that could produce it cost $0.0933.

## Why this negative, per the literature

Cross-referenced against the primary sources recorded in `TABPFN_FINETUNING_LITERATURE.md`. Each condition
below is checked against this pilot's profile, in four buckets: it **fits** (we satisfy it and it predicts
the negative), it is **ruled out**, our regime is **outside the evidence**, or it **predicts the opposite**.

| Documented condition | This pilot | Bucket |
| --- | --- | --- |
| Gradual temporal shifts with rich feature sets: fine-tuning less stable, prior methods remain better | Insurance lapse is cohort-structured, temporal and rich-featured | **fits** |
| Baseline already within a few percent of the target: less likely to help; exhaust feature engineering and preprocessing first | The arms sit within about 0.25 ROC AUC points of `A_raw` | **fits** |
| Niche or specialised domain not covered by the pretraining priors: a *good* candidate for fine-tuning | Insurance lapse is exactly such a domain, and financial instruments are named as an example | **predicts the opposite** |
| Datasets under 1,000 rows: overfitting risk | 2,000 training rows | ruled out |
| The learning rate was wrong for the task | 1e-5 is the vendor's documented default | ruled out |
| The published regime: benchmark average about 15K examples, up to about 1M cells | 2,000 rows, far below both | **outside the evidence** |

Three conclusions follow, and the second is the one that matters.

**The simple story is wrong.** "The pretraining priors did not cover our data, so fine-tuning failed" is the
domain-gap explanation, and this domain is precisely the vendor's *good-candidate* case. What fits instead
is the temporal condition: fine-tuning sharpens similarity toward the training distribution, which is the
wrong thing to sharpen in a drifting one.

**Our regime is outside the evidence.** The negative is not covered by published results in either
direction, so it should not be presented as a confirmation of a studied boundary. It is consistent with one.

**One methodological gap on our side, recorded as a limitation.** The vendor requires that on time-dependent
data the split respect the time ordering. This run used the loader's stratified **random** split. That makes
the task *easier* than the domain presents, so it cannot explain the negative — but it limits how far the
verdict generalises, and it is the first thing to fix before any re-run.

**The one observation no source explains.** Calibration improved monotonically with epochs while ROC AUC did
not move. The published mechanism predicts a *ranking* gain, so this sits outside the explanation above.
Either it is noise at one seed, or it is a distinct effect — and it is the observation with commercial
relevance, since a fixed schema scored repeatedly is the amortised setting the vendor names.

**What would separate these explanations,** each one dataset and costs in cents: a **temporal split** (the
vendor's guidance, and the fix for our own limitation); an **I.I.D. academic dataset** (where the same
literature reports fine-tuning winning, which would turn a flat negative into a domain boundary); and the
**batch-size** axis the paper reports on, which we have never tested.
