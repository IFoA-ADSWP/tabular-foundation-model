# Breadth result — fine-tuning adds nothing measurable on `spanish_motor_lapse`

> **Status:** current — result, 2026-11-06. **Question:** does the fine-tuning gain the anchor measured on
> `uslapseagent` (+0.0035 AUC) also appear on `spanish_motor_lapse`? **Design:** D19, amended after the probe
> (#466). **Evidence:** one committed launch record under `outputs/gpu-pilot/`, 32 records, seeds 341–356.
> **Verdict:** **equivalence** — the effect is bounded under δ = 0.002. **Decision it informs:** D20.

## Answer

**No measurable gain.** Across **16 fresh seeds**, 30-epoch fine-tuning beats the in-run `A_raw` by
**+0.00029 ROC AUC**, 95% interval **[−0.00021, +0.00078]**.

Both halves of the pre-registered rule agree: the interval **covers zero**, and its **upper bound sits
below δ = 0.002**. This is an equivalence reading, not an unresolved one — the sample was large enough to
bound the effect under the bar rather than merely fail to reach it.

| | Value |
|---|---|
| ΔAUC, mean over 16 seeds | **+0.00029** |
| Between-seed SD | 0.00093 |
| 95% interval | **[−0.00021, +0.00078]** |
| Seeds with a positive delta | 11 / 16 |
| `A_raw` mean AUC | 0.7226 |
| `B_ft30` mean AUC | 0.7229 |
| ΔBrier, worst seed | +0.00034 (guard ≤ +0.001) |

## What this establishes

**Within this design**, on this dataset, adapting the weights adds nothing beyond giving raw TabPFN the
same context. Set against the two other datasets now measured:

| Dataset | ΔAUC | 95% interval | Reading |
|---|---|---|---|
| `uslapseagent` (anchor) | **+0.0035** | [+0.00272, +0.00428] | gain, clears δ |
| `eudirectlapse` (D18) | +0.0007 | [−0.0003, +0.0018] | equivalence |
| **`spanish_motor_lapse` (this)** | **+0.0003** | **[−0.0002, +0.0008]** | **equivalence** |

The anchor's effect is **twelve times** this dataset's point estimate. Two of three datasets now bound the
effect under δ, which makes the anchor's +0.0035 **dataset-specific rather than a property of the model** —
the conclusion D18 reached, with a second dataset behind it.

## What the probe bought, and what it cost

Nothing in the effect; everything in the affordability.

D18 projected **~512 seeds (~$14)** for this dataset. That projection used the **1,000-test-row**
half-width (0.0163) that the readiness study measured and **rejected**, in place of a between-seed SD
nobody had measured. The probe measured that SD — **0.0012** on the top rung — which the pre-registered rule
turns into `k = 3`. The replication ran at **16** for margin over SD uncertainty.

*2026-11-09 (#520): corrected from "~$9.50", which D18 never said — D18 projects ~$14.*

The experiment recorded as unaffordable completed for **$0.065**.

| Item | Cost (credit delta) |
|---|---|
| One seed, four arms (the measurement) | $0.043 |
| Probe, ten seeds (five attempts, three failed) | $0.153 |
| Replication, sixteen seeds | $0.065 |
| **Total for the cell** | **$0.3315** (balance $3.1127 → $2.7812) |

## What this does not establish

- **Not a statement about other datasets.** `coil2000` remains unmeasured.
- **Not a statement about other row counts.** The design fixed 10,000 training rows; a full-data cell is
  Stage 3 and was never authorised.
- **Not a statement about other epoch budgets.** 30 epochs is the top of the ladder. The probe measured the
  lower rungs at −0.0006 (3 epochs) and −0.0002 (10 epochs), so the budget is not what is missing.
- **Not a calibration claim.** Brier's worst seed is +0.00034 against a +0.001 guard — no ranking gain to
  qualify, so this is "no improvement and no calibration benefit".

## How it was run

**Probe** — one launch, four arms × seeds 331–340, 10,000 train / 10,000 test, `v3_default`, on an
`RTX 3090`. Ten seeds, 40 records. Purpose: measure the between-seed SD and the real per-seed cost.

**Replication** — one launch, arms `A_raw` and `B_ft30`, seeds **341–356** (fresh, disjoint from the probe
and from D18's 93–330), same rows and model version. Sixteen seeds, 32 records.

Both launches asserted `tabpfn-v3-classifier-v3_default.ckpt` through `TFM_EXPECT_CHECKPOINT`, and both
records name the pre-registration. The launch is cited here by description rather than by run id: its
artifacts are runtime evidence under `outputs/gpu-pilot/` on the launch machine and were never captured
under `results/` — no fine-tune arm exists there for this dataset — and a run id in `docs/` requires a
committed `results/<id>/capture.json`.

For the next author: `outputs/gpu-pilot/` is **not** git-ignored (only `outputs/gpu-pilot/leases/` is;
the rules at `.gitignore:210-211` are negations for an ignore that does not exist above them). What
guards those trees is the `evidence` check, not `.gitignore`.

**Reproduction.**

```
scripts/gpu_helpers/vast_run.sh --experiment spanish_motor_lapse_cell \
  --arms A_raw,B_ft30 --seeds 341,342,343,344,345,346,347,348,349,350,351,352,353,354,355,356 \
  --estimate-sec-per-seed 87 --max-dph 0.60
```

## What it means for the programme

The breadth question now stands at **two datasets answered "no" and one "yes"**, with the "yes" being the
dataset the pilot chose. That is a pattern worth stating plainly rather than burying in intervals: the
adaptation helps where it was tried first, and nowhere else it has since been measured.
