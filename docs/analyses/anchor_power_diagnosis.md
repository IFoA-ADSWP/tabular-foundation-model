# Anchor power diagnosis — was the two-seed result underpowered or null?

> **Status:** active — analysis, 2026-10-31. **Question:** did the anchor fail to replicate because
> fine-tuning does not help, or because the design could not resolve an effect of that size?
> **Data:** `results/20261031T021845Z/` (committed, eight arm records with predictions).
> **Decision it informs:** D11 (the stop) and deviation D-1 in the statistical plan.

## Answer in one paragraph

**Underpowered for R1's effect, and null at 95% once pooled.** The design resolves differences of
about **0.0036 AUC** (median 95% half-width across six comparisons), and R1's effect was
+0.0022 to +0.0034. An effect that size sits at the edge of what 1,000 test rows can distinguish,
so a single split can plausibly show it (seed 43 did) or miss it (seed 44 did not). Pooling both
seeds — exploratory, never pre-registered — gives +0.0020 / +0.0032 / +0.0034 with intervals that
all include zero. So the honest statement is **"an effect of R1's size is plausible but
unestablished"**, not "fine-tuning does not help". The stop under D9 stands regardless: the rule
asked for both seeds, and one failed.

## Method

Paired bootstrap over the 1,000 test rows, 4,000 resamples, fixed seed, percentile interval; each
arm against **its own run's** `A_raw` on identical rows. Pooled figures resample each seed's rows
independently and pool the bootstrap distribution — a stratified estimate, and **exploratory**,
because pooling was not part of D9.

## Resolution this design actually achieved

| seed | rung | ΔAUC | 95% CI | half-width |
|---|---|---|---|---|
| 43 | B_ft3 | +0.0031 | [+0.0000, +0.0063] | 0.0031 |
| 43 | B_ft10 | +0.0050 | [+0.0010, +0.0092] | 0.0041 |
| 43 | B_ft30 | +0.0057 | [+0.0013, +0.0105] | 0.0046 |
| 44 | B_ft3 | +0.0009 | [−0.0017, +0.0036] | 0.0026 |
| 44 | B_ft10 | +0.0013 | [−0.0022, +0.0048] | 0.0035 |
| 44 | B_ft30 | +0.0010 | [−0.0026, +0.0049] | 0.0038 |

**Median half-width 0.0036, maximum 0.0046.** A difference below ~0.004 cannot be distinguished from
zero at this sample size, whatever the true effect is.

## Pooled across seeds (exploratory)

| rung | mean ΔAUC | 95% CI | half-width |
|---|---|---|---|
| B_ft3 | +0.0020 | [−0.0013, +0.0059] | 0.0036 |
| B_ft10 | +0.0032 | [−0.0015, +0.0086] | 0.0051 |
| B_ft30 | +0.0034 | [−0.0020, +0.0099] | 0.0059 |

All three include zero. The point estimates sit where R1's did; the intervals are too wide to
establish them.

## Deviation D-1, reconciled

The signed plan claimed this dataset "can resolve ≥ 0.009 ROC". The probe measured half-widths of
0.0022–0.0043; this anchor measures **0.0036 median**. The 0.009 figure is **not** what this
design achieves and must not be quoted. The acceptance never rested on it — D9 uses interval
exclusion, not a resolution floor — but the plan's §12.1 sentence is now corrected by deviation.

## What would change the answer

- **More test rows.** Half-width scales as 1/√n: halving 0.0036 to ~0.0018 needs roughly **4× the
  test rows** (~4,000). That is the only lever that touches row-sampling variance.
- **More seeds** stabilise the estimate against split luck but do **not** narrow the interval, per
  the plan's own §12.1 argument. Three seeds would have made the disagreement less likely to be
  read as decisive; they would not have made a 0.002 effect significant.

## Process finding — the committed evidence was incomplete

`*.npy` is gitignored (`.gitignore:145`), so committing the run copied **metadata only**: the
records could not be re-read. The ignore file already carries a comment about exactly this failure
("a plain `git add` skipped .npy … which is how a run's predictions ended up recorded in the working
tree only"). The arrays are now force-added under `results/20261031T021845Z/` (128 KB), and the gap
is filed rather than remembered: the evidence guard checks *that* evidence changed, never that it
arrived complete.

## Files

- Records: `results/20261031T021845Z/uslapseagent/<arm>/seed<seed>_foldNone/meta.json`
- Arrays: same directories, `predictions.npy` and `ground_truth.npy` (force-added)
- Decision: `FINETUNING_DECISION_LOG.md` D11; deviation D-1 in `FINETUNING_STATISTICAL_ANALYSIS_PLAN.md`
