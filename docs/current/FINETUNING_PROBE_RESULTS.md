> **Superseded 17 Sep.** This recorded the probe at 2,000 training rows, where fine-tuning did not beat
> raw. At 10,000 rows every rung beat raw, intervals excluding zero, monotone in epochs. The measurement
> below stands as the 2,000-row result; it is not the current answer. See the front section of
> `docs/current/FINETUNING_EXPERIMENT_REFERENCE.md`.

# Fine-Tuning Probe Results

**Pre-registration:** `docs/reference/PROBE_PLAN.md` (merged, #173). **Run:** `20260913T225032Z`, pinned to
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
