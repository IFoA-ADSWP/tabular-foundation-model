# Breadth result — fine-tuning does not generalise to `eudirectlapse`

> **Status:** current — result, 2026-11-05. **Question:** does the fine-tuning gain the pilot measured on
> `uslapseagent` (+0.0035 AUC) also appear on `eudirectlapse`, at 10,000 rows and 30 epochs?
> **Design:** D17. **Verdict:** **equivalence** — the effect is below the pre-registered δ = 0.002 and
> not separable from zero. **Decision it informs:** D17's outcome, recorded in the decision log.

## Answer

**No measurable gain.** Across **238 seeds**, 30-epoch fine-tuning beats the in-run `A_raw` by
**+0.0009 ROC AUC**, 95% interval **[−0.0001, +0.0019]**.

Both conditions of the pre-registered rule point the same way: the interval **covers zero**, and its
**upper bound sits below δ = 0.002**. This is an equivalence reading, not an unresolved one — the
sample was large enough to bound the effect under the bar rather than merely fail to reach it.

| | Value |
|---|---|
| Mean ΔAUC over 238 seeds | **+0.0009** |
| 95% interval (between-seed SD 0.0081) | **[−0.0001, +0.0019]** |
| Median ΔAUC | +0.0012 |
| Per-seed range | **−0.0245 … +0.0292** |
| Seeds positive | 134 / 238 (**56%**) |
| ΔBrier, worst seed (guard ≤ +0.001) | **+0.0010** |
| Permutation null: SD / false-positive rate | 0.0085 / **0.0000** |
| Seeds the design needed at this SD | **129** (the run carried 238) |

The null band is the instrument check: under permuted labels the rule fires essentially never, so the
reading is not an artefact of its own thresholds. The run was **over-powered** — 238 seeds against a
requirement of 129 — because the seed count was set from a probe whose spread (0.011) turned out to be
larger than the replication's realised spread (0.0081). That is the safe direction, and it is why the
interval is tight enough to call equivalence rather than shrug.

## What this establishes

**Within this design**, on this dataset, adaptation of the weights adds nothing beyond giving raw
TabPFN the same context. The probe's +0.0037 at 10 seeds was within its own standard error
(±0.0035) of this answer; the anchor's +0.0035 on `uslapseagent` is therefore **dataset-specific
rather than a general property of the model**.

`eudirectlapse` is the case this mattered most: it is the only R1 dataset where a baseline beats
TabPFN at full data, so it is the one place fine-tuning had a *gap to close* rather than a lead to
extend. It closed nothing.

## What this does not establish

- **Not a statement about other datasets.** `coil2000` and `spanish_motor_lapse` remain unmeasured.
  `spanish_motor_lapse` projects to roughly 512 seeds from its measured half-width, which the
  remaining balance does not cover.
- **Not a statement about other row counts.** The design fixed 10,000 training rows. `eudirectlapse`
  has 23,060 rows; a 22,000-row cell is Stage 3 in the design and was never authorised.
- **Not a statement about other epoch budgets.** 30 epochs is the top of the ladder; the probe here
  measured 3 / 10 / 30 and 30 was highest, but the replication carried only 30.
- **Not a calibration claim.** Brier's worst seed sits at the guard (+0.0010 against +0.001). There is
  no ranking gain to qualify, so this is "no improvement and no calibration benefit", not a breach
  that vetoes one.

## How it was run

Twenty paid launches of twelve seeds each, two arms (`A_raw` + `B_ft30`), 10,000 training rows and
1,000 test rows on `eudirectlapse`, seeds 93–330, model line `tabpfn-v3-classifier-v3_default.ckpt`
asserted before every launch (`TFM_EXPECT_CHECKPOINT`). The batches are independent and pool by seed;
the verdict tool refuses a repeated seed precisely so that a batch cannot be counted twice.

Records live under `outputs/gpu-pilot/runs/` — one directory per launch, one `meta.json` per arm ×
seed, with prediction hashes verified at pull. They are runtime evidence and are not committed.

**Cost: $4.30** across 29 launches, of which roughly a quarter produced nothing: three batches lost to
poll overruns, 36 seeds measured twice through a launcher concurrency defect, and one batch killed at a
gated weight fetch. The defects and their fixes are tracked in #428; the concurrency one is #426.

## Reading it beside the anchor

| | `uslapseagent` (anchor) | `eudirectlapse` (this) |
|---|---|---|
| Mean ΔAUC | **+0.0035** | **+0.0009** |
| Interval | [+0.00272, +0.00428] | [−0.0001, +0.0019] |
| Seeds | 28 | 238 |
| Reading | pass | **equivalence** |
| Raw TabPFN vs best baseline | TabPFN ahead | **GLM ahead** at full data |

The pattern is consistent with D2's feature-importance finding: on `uslapseagent` all three families
used the same ten features and scored within 0.003 of each other, so a within-model gain there was
plausible; on `eudirectlapse` the families disagree about which features matter, and adaptation does not
supply the features the linear model has.
