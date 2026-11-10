# Breadth specification — the full value of in-domain fine-tuning (2026-11)

> **Status:** proposed — **no launch is authorised by this document.** **Decision it applies:** D16,
> which amends D14. **Question:** how large is the fine-tuning gain on the other three R1 datasets,
> and where does the row-scale threshold sit? **Cost:** measured anchors plus a labelled range; the
> probe stage prices it exactly before any replication is authorised.

This document is the **breadth specification** #300 says a passing gate releases. D14 removed the
follow-on even on a pass; D16 restores it, and this is the specification it demands. Nothing here may
be launched until D10's per-run approval carries a **measured** estimate, which the probe stage
produces.

## What changed, and why this document exists at all

D14 (2026-11-03) stopped the line after one replication and gave a reason: a 0.002–0.003 effect is
"roughly 20 times smaller than raw TabPFN's margin over the best actuarial baseline, so scaling it buys
a larger sample of something no modelling choice depends on."

D16 records the owner's override, on three grounds:

1. **The comparison is a category mismatch.** F4 in `FINETUNING_FINDINGS.md` states that the
   fine-tuning gain is a *within-model* improvement. Measuring it against a *between-model* margin
   sets a bar the question never raised. On its own terms — does adapting the weights add value beyond
   giving the model more context? — +0.0035 with an interval excluding zero is an answer, and the
   question generalises.
2. **The evidence is one dataset.** One lapse dataset, one pair of row counts, one model line. Nothing
   in the tree says the effect is not specific to `uslapseagent`, and the diagnostics cannot answer it
   either: D2 measured *which features* the families use, not how much adaptation buys.
3. **The cost is small in absolute terms** — measurably so, below — and the *measurement* itself has
   value independent of any deployment decision, because it is what a paper claims.

The honest cost of the override: the stop was **pre-registered before the result existed**, which is
why the 0.0035 is credible. Reopening after a pass is exactly the pattern pre-registration exists to
resist, so it is recorded as an override with a named reason rather than presented as new information.
Nothing about the replication's result changes.

## The question

Two questions, in this order:

1. **Generalisation.** Does in-domain fine-tuning beat raw TabPFN on `coil2000`, `eudirectlapse` and
   `spanish_motor_lapse`, by how much, and with what sign? `eudirectlapse` is the interesting one: it
   is the only R1 dataset where a baseline beats TabPFN, so adaptation there asks whether fine-tuning
   can *close* a gap rather than extend a lead.
2. **The row-scale threshold.** The 2,000-row probe lost (−0.0025 on `B_ft3`) and the 10,000-row run
   won (+0.0035). Nobody has located the threshold between them, and `spanish_motor_lapse` and
   `coil2000` both have enough rows to test it.

## What is being tested

**Datasets and row caps.** All four R1 datasets. `coil2000` has **9,822 rows total**, so a 10,000-row
cell does not exist; its cell runs at the largest available size and the actual count is recorded. The
design's rule holds: record the actual count and explain the deviation rather than substituting a
different size silently.

**Split.** Stratified random, 1,000 test rows, as the anchor. No temporal split exists on any lapse
dataset (limitation L1), and every result carries that caveat.

**Model.** The same line the replication ran: `v3`, resolved by `auto` on `tabpfn` 8.5.0 to
`tabpfn-v3-classifier-v3_default.ckpt`. Fine-tuning is local-package only, so the pin question is the
launcher's (#402), not this document's. A cell that ran a different model line is not comparable with
the anchor and must say so.

**Arms.** `A_raw` plus `B_ft3`, `B_ft10`, `B_ft30` — the four-arm set, so both questions are answerable
from one launch. The rung that carries the verdict is chosen by the anchor's rule (highest probe mean
that fits the per-launch ceiling), applied per dataset and recorded.

**Comparator.** The `A_raw` arm of the **same seed, same launch**. No comparison crosses runs, launches
or model versions.

## Resolution: what is measured, and what is not

The only thing that sets the price is how many seeds each dataset needs, and that is set by its
per-seed variance — not by class balance, which is why two of the four cannot be projected.

| Dataset | Rows | Positives per 1,000 test rows | Measured half-width at 1,000 test rows | Seeds for ~0.0036 |
|---|---:|---:|---|---:|
| `uslapseagent` | 29,317 | 379 | **0.0036** — anchor's median paired; realised at 28 seeds | **28** (measured) |
| `spanish_motor_lapse` | 53,502 | 354 | **0.0154** — small-δ proxy, 10k/1k, readiness study | **≈512** (projected) |
| `eudirectlapse` | 23,060 | 128 | not measured | unknown — probe |
| `coil2000` | 9,822 | 60 | not measured | unknown — probe |

**Why `coil2000` and `eudirectlapse` are not projected.** The obvious projection — scale by positive
count — is falsified by the table above: `spanish_motor_lapse` and `uslapseagent` have almost the same
number of test positives (354 against 379) and half-widths that differ **four-fold**. Resolution is a
property of the dataset's signal, not of its class balance, so the two unknown datasets are measured
rather than guessed.

**The seed rule**, unchanged from D13: `k = ceil((sd / 0.000714)²)`, where `0.000714` is the standard
error giving 80% power at δ = 0.002. The anchor's probe SD (~0.0038) produced k = 28; its realised
between-seed SD was 0.0021, so the probe was conservative and the realised power was higher than
designed. The same conservatism applies to every dataset here.

**`spanish_motor_lapse`, arithmetic shown:** 28 × (0.0154 / 0.0036)² = 28 × 18.3 ≈ **512 seeds**.
That is a projection from a single measured half-width, and it is the reason this dataset is the last
cell, not the first.

## The staged design

Per dataset, three stages. No stage starts before the one before it reports.

**Stage 1 — variance probe.** Four arms × 10 seeds at the cell's row count. Output: per-seed ΔAUC
against that seed's `A_raw`, the per-seed SD, and therefore `k`. This is what turns "unknown" into a
number, and it is the measurement D10 requires before a replication is approved.

**Stage 2 — resolution gate, no spend.** Compute `k`. **Stop** if the power at δ = 0.002 is below 0.80,
or if `k`'s cost exceeds the per-launch ceiling that applies to the run. A stop is reported as a stop;
the target effect is never relaxed to make a no-go look like a go.

> **2026-11-09** (#520). This read "the per-launch ceiling that **D10** sets for the run". D10 sets no ceiling
> (`FINETUNING_DECISION_LOG.md:177-178`). The ceilings that exist are D12's $0.15 and D17's $0.60, and a cell
> may set its own — D19 set $0.50 for its probe and $3.00 for its replication.

**Stage 3 — replication.** `A_raw` plus the chosen rung over `k` fresh seeds, random-effects (REML)
interval, aggregated exactly as the anchor's was. A fresh permutation null on the replication's own
capture over the same 5,000 permutations per seed, with the pre-registered 0.03–0.07 false-positive
band, voids the verdict on instrument failure.

**Order.** `eudirectlapse` first and `uslapseagent`'s 10,000-row cell is already done, so:

1. `eudirectlapse` at 10,000 — the gap-closing question, and the one most likely to differ in sign.
2. `spanish_motor_lapse` at 10,000 — but probe first; its projected 512 seeds make it the expensive one.
3. `coil2000` at ~8,800 (its ceiling) — the only dataset where the 10,000-row cell cannot exist.
4. The 2,000-row cells last: they answer the threshold question, and they are worthless until the
   10,000-row direction is known per dataset.

## Cost

**Measured anchors** (`FINETUNING_COST_AND_CONTROLS.md`, which owns cost figures): **$0.0122** for a
four-arm run at 2,000 rows, **$0.0368** at 10,000 rows.

**Measured since the first probe (D17, 2026-11-04).** `eudirectlapse` at 10,000 rows: per-seed SD
**0.0110**, so `k = 238` for `B_ft30`, and the projection below is superseded for that dataset:
three launches cost **$0.2189** in total, the two-arm replication shape costs **≈ $2.95** for all 238
seeds, and a single batch of thirty seeds is **≈ $0.37**. The range below is retained because the other
two datasets remain unmeasured, and because the probe's own figures are what falsified its optimistic end.

**Measured-and-projected range for the whole programme**, at those anchors:

| Stage | Basis | Cost |
|---|---|---:|
| Variance probes for the two unmeasured datasets (2 × 10 launches) | measured unit price | **$0.74** |
| Replication, if every dataset resolved like `uslapseagent` (3 × 28 seeds) | projected | **$3.09** |
| Replication, if every dataset resolved like `spanish_motor_lapse` (3 × 512 seeds) | projected | **$56.53** |
| 2,000-row cells (four datasets, same seed rule) | projected, at $0.0122 | $1.37 – $25.00 |

So the programme is bounded by roughly **$5 at the optimistic end and $82 at the pessimistic end**, and
the **$0.74 probe stage replaces both bounds with a measured total** before a single replication is
approved. That is the point of running the probes first: the decision to proceed becomes a measured one
rather than this document's estimate.

Wall clock is the real constraint, not money: 512 launches at the anchor's ~2–3 minutes each is 17–26
hours sequential for `spanish_motor_lapse` alone, so that cell is parallelised across launches or
declared out of scope on the strength of its own probe.

## What would stop this

- **A probe whose `k` exceeds the per-launch ceiling** — the dataset is reported as unresolvable at δ
  rather than run underpowered.
- **A replication whose fresh null falls outside 0.03–0.07** — instrument failure, verdict void.
- **A dataset that cannot supply the row count** — `coil2000` at 9,822 rows is the known case; the
  actual count is recorded, never substituted silently.

## What this will not claim

- **Not a breadth result until each replication lands.** A probe is not a result.
- **Not a model-choice claim.** The gain, if it generalises, remains a within-model improvement (F4).
  Whether to fine-tune is a different decision from which model to use, and this document does not
  reopen the second.
- **Not a transfer or pooling claim.** Those are Phase 3 and remain conditional.
- **Not a calibrated result unless Brier holds.** The Brier veto (+0.001 over the in-run `A_raw`)
  applies per dataset exactly as it did for the anchor.

## Authorisation

Each launch is approved separately, on the estimate its own probe produced (D10). This document
authorises nothing by itself.
