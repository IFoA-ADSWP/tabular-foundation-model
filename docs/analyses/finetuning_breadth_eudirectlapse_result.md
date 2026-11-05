# Breadth result — fine-tuning does not generalise to `eudirectlapse`

> **Status:** current — result, 2026-11-05. **Question:** does the fine-tuning gain the pilot measured on
> `uslapseagent` (+0.0035 AUC) also appear on `eudirectlapse`, at 10,000 rows and 30 epochs?
> **Design:** D17. **Evidence:** twenty committed runs under `results/` (476 records, seeds 93–330).
> **Verdict:** **equivalence** — the effect is below the pre-registered δ = 0.002 and not separable
> from zero. **Decision it informs:** D17's outcome, recorded in the decision log.

## Answer

**No measurable gain.** Across **238 seeds**, 30-epoch fine-tuning beats the in-run `A_raw` by
**+0.0007 ROC AUC**, 95% interval **[−0.0003, +0.0018]**.

Both conditions of the pre-registered rule point the same way: the interval **covers zero**, and its
**upper bound sits below δ = 0.002**. This is an equivalence reading, not an unresolved one — the
sample was large enough to bound the effect under the bar rather than merely fail to reach it.

| | Value |
|---|---|
| Mean ΔAUC over 238 seeds | **+0.0007** |
| 95% interval (between-seed SD 0.0082) | **[−0.0003, +0.0018]** |
| Median ΔAUC | +0.0012 |
| Per-seed range | **−0.0245 … +0.0292** |
| Seeds positive | 134 / 238 (**56%**) |
| ΔBrier, worst seed (guard ≤ +0.001) | **+0.0010** |
| Permutation null: SD / false-positive rate | 0.0085 / **0.0000** |
| Seeds the design needed at this SD | **132** (the run carried 238) |

These figures are recomputed from the committed captures (see Reproduction). An earlier draft quoted
the mean, between-seed SD and seed requirement of the 228-seed pool that existed before the final
ten-seed batch landed, beside the 238-seed count; the mean moves from +0.0009 to +0.0007, the reading
is unchanged, and the correction is recorded because the document and its evidence must agree.

The null band is the instrument check: under permuted labels the rule fires essentially never, so the
reading is not an artefact of its own thresholds. The run was **over-powered** — 238 seeds against a
requirement of 132 — because the seed count was set from a probe whose spread (0.011) turned out to be
larger than the replication's realised spread (0.0082). That is the safe direction, and it is why the
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

Twenty paid launches — nineteen of twelve seeds, the last of ten — two arms (`A_raw` + `B_ft30`),
10,000 training rows and 1,000 test rows on `eudirectlapse`, seeds 93–330, model line
`tabpfn-v3-classifier-v3_default.ckpt` asserted before every launch (`TFM_EXPECT_CHECKPOINT`). The
batches are independent and pool by seed; the verdict tool refuses a repeated seed precisely so that a
batch cannot be counted twice.

Records are committed under `results/<run_id>/` — one directory per launch, named by its launch id —
with one `meta.json`, `predictions.npy` and `ground_truth.npy` per arm × seed, and a `capture.json`
per run written by `scripts/analyses/make_capture.py`. The verdict reads those arrays and verifies
each against both the capture and the record, so the numbers below can be recomputed from the tree
rather than trusted.

**Cost: $4.30** across 29 launches, of which roughly a quarter produced nothing: three batches lost to
poll overruns, 36 seeds measured twice through a launcher concurrency defect, and one batch killed at a
gated weight fetch. The defects and their fixes are tracked in #428; the concurrency one is #426.

## Reproduction

```
python scripts/analyses/verdict.py \
  --run results/20261104T234013Z --run results/20261105T001837Z --run results/20261104T234127Z \
  --run results/20261104T234132Z --run results/20261105T100533Z --run results/20261105T005435Z \
  --run results/20261105T005447Z --run results/20261105T124200Z --run results/20261105T012925Z \
  --run results/20261105T013749Z --run results/20261105T013755Z --run results/20261105T124205Z \
  --run results/20261105T140236Z --run results/20261105T103841Z --run results/20261105T103937Z \
  --run results/20261105T103853Z --run results/20261105T140242Z --run results/20261105T111110Z \
  --run results/20261105T114320Z --run results/20261105T114647Z \
  --delta 0.002 --reps 5000
```

Same inputs, same output: no clock, no network, and every array is hashed against its `capture.json`
and its `meta.json` before it is scored. A run whose evidence disagrees is refused by name rather than
scored.

## Evidence Files

One run directory per launch under `results/`, named by the launch id, each with a `capture.json` and
one `meta.json` / `predictions.npy` / `ground_truth.npy` per arm × seed. Three seed ranges were
launched more than once while #426 was live; only one directory per range is committed here, so the
table names one and the pool stays seed-disjoint.

| Run | Seeds | Run | Seeds |
|---|---|---|---|
| `20261104T234013Z` | 93–104 | `20261105T103841Z` | 249–260 |
| `20261105T001837Z` | 105–116 | `20261105T103937Z` | 261–272 |
| `20261104T234127Z` | 117–128 | `20261105T103853Z` | 273–284 |
| `20261104T234132Z` | 129–140 | `20261105T140242Z` | 285–296 |
| `20261105T100533Z` | 141–152 | `20261105T111110Z` | 297–308 |
| `20261105T005435Z` | 153–164 | `20261105T114320Z` | 309–320 |
| `20261105T005447Z` | 165–176 | `20261105T114647Z` | 321–330 |
| `20261105T124200Z` | 177–188 | | |
| `20261105T012925Z` | 189–200 | | |
| `20261105T013749Z` | 201–212 | | |
| `20261105T013755Z` | 213–224 | | |
| `20261105T124205Z` | 225–236 | | |
| `20261105T140236Z` | 237–248 | | |

The launch manifests (`manifest_*.json`) and the two parquet records are committed beside the arrays,
as they are for the anchor, so a reviewer can read a launch's git sha, host and clock without leaving
the tree. Two launches in the 201–224 range started within the same second on different hosts, so their
on-box manifests share filenames while recording different hosts, run stamps and seeds; each seeded
record and its capture hash are authoritative. Cost and lease records stay under `outputs/` and are
not committed.

## Reading it beside the anchor

| | `uslapseagent` (anchor) | `eudirectlapse` (this) |
|---|---|---|
| Mean ΔAUC | **+0.0035** | **+0.0007** |
| Interval | [+0.00272, +0.00428] | [−0.0003, +0.0018] |
| Seeds | 28 | 238 |
| Reading | pass | **equivalence** |
| Raw TabPFN vs best baseline | TabPFN ahead | **GLM ahead** at full data |

The pattern is consistent with D2's feature-importance finding: on `uslapseagent` all three families
used the same ten features and scored within 0.003 of each other, so a within-model gain there was
plausible; on `eudirectlapse` the families disagree about which features matter, and adaptation does not
supply the features the linear model has.
