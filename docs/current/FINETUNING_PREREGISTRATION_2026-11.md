# Pre-registration — the fine-tuning replication (2026-11)

> **Status:** current — pre-registration, 2026-11-04. **Authorises:** one probe **Launch**, then one
> replication **Launch**. **Scores:** δ = 0.002 ROC AUC, Brier veto. **Model:** `v3_default`, pinned by
> checkpoint path. **Cost:** about $0.23 measured; ceiling $0.15 per launch. **Decision it applies:**
> D12–D14 in `FINETUNING_DECISION_LOG.md`. **Tickets:** #396 (this document), #398 (the verdict tool),
> #399 (the probe).

This document is the **dated amendment** the escalation rule requires: that rule forbids adding seeds
after seeing data, and this fixes the seed count's formula before any data exists. A launch record
must name this document.

## What is being tested

**Dataset:** `uslapseagent`, 10,000 training rows, 1,000 test rows, stratified random split — the
anchor's shape. No temporal split exists; that limitation is reported with every result.

**Model:** `v3_default`, the same line the anchor ran (`version: auto` resolved to
`tabpfn-v3-classifier-v3_default.ckpt`), now **pinned** by checkpoint path. A pin passes a path, not a
label (#285, #345). `v3.5` is **not usable**: the local package exposes `V2, V2_5, V2_6, V3` and no
v3.5 classifier checkpoint, and fine-tuning is local-package only.

**Comparator:** the `A_raw` arm of the **same seed**, in the same launch. No comparison crosses runs,
launches or model versions.

## Stage 1 — the probe (4 arms × 10 seeds)

Arms `A_raw`, `B_ft3`, `B_ft10`, `B_ft30`. Seeds **45–54** (fresh; the anchor's 43 and 44 are prior
evidence and are not reused). Estimated **$0.11**.

Output: a **Capture** per arm × seed, per-seed ΔAUC and ΔBrier against that seed's `A_raw`, and the
**per-seed SD** of ΔAUC for each rung.

**Rung rule, fixed now.** Choose the rung with the highest probe mean ΔAUC among rungs whose implied
replication cost fits the $0.15 ceiling; if the highest does not fit, take the next best that does. The
substitution is recorded on the probe ticket, never made silently.

## Stage 2 — the resolution gate (no spend)

Before the replication launches, compute the design's resolution at `k` seeds:

- `k = ceil((sd / 0.000714)²)`, where `sd` is the chosen rung's per-seed SD and `0.000714` is the
  standard error giving 80% power at δ (δ / 2.80159).
- **Stop if power at δ is below 0.80**, or if `k`'s cost exceeds the ceiling for every rung. A stop
  reopens D14; the target effect is never relaxed to make a no-go look like a go.

## Stage 3 — the replication (`A_raw` + the chosen rung, k seeds)

Seeds **disjoint from the probe** (55 upward), 1,000 test rows, one rung. Estimated **$0.12**.

**Aggregation:** the mean of the per-seed ΔAUCs, with the interval taken from the **between-seed**
standard deviation. Rows are never pooled: pooling treats rows inside a seed as independent,
understates the standard error by 1.69× and inflates the false-positive rate to 0.25.

**Two claims are withheld even when the arithmetic offers them.** Zero between-seed variance makes a
zero-width interval, so any point estimate would become a pass; that run reads *unresolved*. And a
rule that fails the instrument check below reads *void*, never *pass*.

## The decision rule, fixed now

| Result | Claim |
|---|---|
| Interval lower bound > 0 **and** point estimate ≥ 0.002 **and** Brier ≤ `A_raw` + 0.001 | **Pass** — publish, and stop. No expansion |
| Interval wholly inside **±0.002** | **"No effect larger than 0.002"** — archive; code and evidence to #340/#341 |
| Anything else | **Unresolved** — licenses nothing; reopens D14, never reported as a soft pass |

## The instrument check

The replication's own **Capture** is permuted (5,000 label permutations per seed, fixed RNG seed).
If the observed rule fires more often than **0.07** under the null, the verdict is **void** and the run
is recorded as an instrument failure, not an effect. The bound is one-sided: a rate *below* it is not a
failure, because a conjunction is deliberately conservative (the anchor's rule fires at about 0.001). A permutation null measured on another
run or model version cannot certify this one.

## What is out of scope

Breadth across the four R1 datasets, Stage 2 transfer, additional rungs, and any expansion after a
pass. The diagnostics (#303–#307) are separate work and are not gated by this document.

## Amendments

| Date | Change |
|---|---|
| 2026-11-04 | Filled in at filing. `k` is left blank until the probe reports; the fill is an amendment to this table, not an edit to the rule |
| 2026-11-04 | **`k` = 28** (`B_ft30`), from the probe's per-seed SD of 0.0037 over seeds 45–54. Replication seeds 55–82. Projected $0.122, actual **$0.188** — the per-launch ceiling was breached by 25% because the projection used the probe host's arm timings (38.9 s/seed vs 62 s/seed). Recorded, not adjusted |
| 2026-11-04 | **Result: pass.** Mean ΔAUC +0.0035, 95% interval [+0.00272, +0.00428], Brier +0.0003. Published; no expansion |
