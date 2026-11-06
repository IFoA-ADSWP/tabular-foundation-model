# Pre-registration — the Spanish lapse cell (2026-11)

> **Status:** current — pre-registration, 2026-11-05. **Authorises:** **nothing.** The probe is a
> separate spend-gate decision; this document fixes the design that decision would approve.
> **Scores:** δ = 0.002 ROC AUC, Brier veto. **Model:** the anchor's line, `v3_default`.
> **Cost:** probe ceiling **$0.50**; replication ceiling **$3.00**; no launch authorised.
> **Decision it applies:** D16's breadth programme and #444. **Data:** `spanish_motor_lapse.csv`,
> two post-outcome columns dropped.

This document is the dated pre-registration [#444](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/444)
requires. It exists so that a Spanish result cannot be relaunched, resized or reinterpreted after its
probe is seen. A launch record must name this document.

## What is being tested

**Dataset:** `spanish_motor_lapse`, target `LapseB`, **10,000 training rows and 10,000 test rows**,
stratified random split. The runner loads `train + test + 500` = 20,500 rows and records the cap; the
remaining 33,002 are never read, exactly as the anchor loaded 11,500 for 10,000 + 1,000 + 500.

**Leak-drops.** `N_claims_year` and `Cost_claims_year` are excluded from every arm. Both describe claims
during the policy year whose end state *is* the label; the readiness study measured a **0.023 AUC**
contribution from them. The runner applies the declaration's drop in `load_dataset`, and the record's
`provenance.dataset.drop` names the columns. The same fingerprint entry's `columns` describes the source
file; the encoded matrix is that list minus the target and the drops.

**Model:** `v3_default`, the anchor's line. A different model line is not comparable and must say so.

**Comparator:** the `A_raw` arm of the **same seed**, in the same launch. No comparison crosses runs,
launches or model versions.

## Why 10,000 test rows

The readiness study's P1 requires a paired 95% half-width of **≤ 0.006** at the stated test size. At
1,000 rows the dataset measures 0.015–0.018 and cannot pass, whatever it returns. The test size is
therefore fixed here, before data, by a measurement on the committed CSV.

**Method.** `HistGradientBoostingClassifier` at scikit-learn defaults, 10,000 stratified training rows,
holdout of `T` rows, the perturbation is the same learner fitted on a **90% subsample** of the training
rows, half-width from **4,000 paired bootstrap resamples** of the test rows. Leak-drops applied. Split
seeds 42, 43, 44.

```
python scripts/analyses/proxy_resolution.py --csv data/raw/spanish_motor_lapse.csv \
  --target LapseB --drop N_claims_year,Cost_claims_year \
  --train 10000 --test 10000 --seeds 42,43,44 --resamples 4000
```

The same command with `--test 1000 --seeds 42` gives the rejected size.

| Test rows | Half-width, seeds 42 / 43 / 44 | Max |
|---|---|---|
| 1,000 — **rejected** | 0.0163 / — / — | 0.0163 |
| 6,600 | 0.0057 / 0.0057 / 0.0061 | 0.0061 |
| **10,000 — chosen** | **0.0047 / 0.0045 / 0.0051** | **0.0051** |

The 1/√n scaling from this document's 1,000-row figure implies `1000 × (0.0163 / 0.006)² ≈ 7,380`
rows. The measured 6,600-row figure (max 0.0061) shows the scaling is optimistic, so the cell runs at
10,000 for margin. The 1,000-row number here is 0.0163 against the readiness study's 0.0154: the same
proxy family, not the same code, so this document quotes its own measurement and states its command. A
result that changes the test size is a different cell and needs a new pre-registration.

## Stage 1 — the probe (4 arms × 10 seeds)

Arms `A_raw`, `B_ft3`, `B_ft10`, `B_ft30`. Seeds **331–340**, fresh: disjoint from the D18 replication's
93–330 and from every prior Spanish seed.

**Cost.** The measured anchor is **$0.0368** for one four-arm 10,000-row run
(`FINETUNING_COST_AND_CONTROLS.md`), so ten seeds model at **≈ $0.37**. **Ceiling $0.50.** No per-seed
cost at 10,000 test rows is measured; the probe measures it, and a ceiling overrun is recorded rather
than absorbed.

Output: a **Capture** per arm × seed, per-seed ΔAUC and ΔBrier against that seed's `A_raw`, and the
**per-seed SD** of ΔAUC for each rung.

**Rung rule, fixed now.** Choose the rung with the highest probe mean ΔAUC among rungs whose implied
replication cost fits the ceiling; if the highest does not fit, take the next best that does. The
substitution is recorded as an amendment, never made silently.

## Stage 2 — the resolution gate (no spend)

Before any replication is approved, compute

**k = ceil((sd / 0.000714)²)**

where `sd` is the chosen rung's per-seed SD and `0.000714 = δ / (Z_ALPHA + Z_POWER)` is the standard
error giving 80% power at δ = 0.002. The verdict tool's `resolution()` is the arithmetic; the document
and the tool are kept equal by a test. For reference, the anchor's realised SD 0.0081 gives 129 seeds;
the Spanish probe's own SD sets its `k`.

**Stop** if the power at δ is below 0.80, or if `k`'s cost exceeds the ceiling on every rung. A stop is
recorded as a stop; δ is never relaxed to make a no-go look like a go.

**Ceiling.** The probe ceiling is **$0.50**. The replication ceiling is **$3.00**. At the 1,000-row unit
price the cell was projected at **≈ $6.3** (D17, `FINETUNING_DECISION_LOG.md`) and the breadth
specification's pessimistic line puts a 512-seed replication at **≈ $18.8** per dataset; 10,000 test rows
add inference on top and no per-seed cost is measured at this size. Both exceed $3.00, so the documented
default outcome is a **stop**. The owner may amend the ceiling before approval; this document authorises
no spend.

## Stage 3 — the replication (unauthorised)

If, and only if, Stage 2 passes and the owner approves the spend: `A_raw` plus the chosen rung over `k`
fresh seeds (disjoint from the probe), 10,000 test rows, aggregated exactly as the anchor's was.

**Aggregation:** the mean of the per-seed ΔAUCs, interval from the **between-seed** standard deviation.
Rows are never pooled across seeds.

**Two claims are withheld even when the arithmetic offers them.** Zero between-seed variance makes a
zero-width interval, so any point estimate would become a pass; that run reads *unresolved*. And a rule
that fails the instrument check below reads *void*, never *pass*.

## The decision rule, fixed now

| Result | Claim |
|---|---|
| Interval lower bound > 0 **and** point estimate ≥ 0.002 **and** Brier ≤ `A_raw` + 0.001 | **Pass** — publish; no expansion |
| Interval wholly inside **±0.002** | **"No effect larger than 0.002"** — archive |
| Anything else | **Unresolved** — licenses nothing |

## The instrument check

The replication's own **Capture** is permuted (5,000 label permutations per seed, fixed RNG seed). If the
rule fires more often than **0.07** under the null, the verdict is **void** and the run is recorded as an
instrument failure, not an effect. A rate below the bound is not a failure.

## Limitations, stated before the run

- **No temporal split.** The dataset carries no date, period or policy key; every result says so.
- **No row key.** Row independence cannot be verified; the 53,502 rows may repeat customers.
- **Mixed-label book groups.** 97% of rows sit in mixed-label groups defined by the customer-book
  columns, so a policy outcome is predicted partly by the book structure. A gain on this dataset cannot
  be attributed to adaptation without that argument.
- **No cross-file join.** The frequency and severity files are not joined in any deciding arm; their
  identically named `Cost_claims_year` is a different quantity.

## Out of scope

Breadth beyond this dataset, `coil2000`, the 2,000-row cells, a model-version change, and any expansion
after a pass. The #428 hardening tickets are prerequisites in time, not work in this document.

## Amendments

| Date | Change |
|---|---|
| 2026-11-05 | Filed. `k` is blank until the probe reports; filling it is an amendment to this table, not an edit to the rule |

## Amendment — the probe's reading, and the replication's `k` (2026-11-06)

**This is the amendment D19 anticipated.** Stage 2 says `k` is filled in after the probe; this fills it.

### What the probe measured

The probe launch — one launch, four arms × seeds 331–340, 10,000 train / 10,000 test, `v3_default`,
`RTX 3090`, bootstrap rc 0. Forty records, predictions verified, instance destroyed.

| Arm | Mean ΔAUC | Between-seed SD | 95% interval |
|---|---|---|---|
| `B_ft3` | −0.0006 | 0.0016 | [−0.0018, +0.0005] |
| `B_ft10` | −0.0002 | 0.0010 | [−0.0009, +0.0005] |
| **`B_ft30`** | **+0.0008** | **0.0012** | **[−0.0001, +0.0016]** |

**No gain is demonstrated.** The top rung's interval covers zero. What the probe establishes is the
*variance*, which is what it was for.

### `k`, and why it is not 512

Stage 2's rule on the measured SD: `k = ceil((0.0012 / 0.000714)²) = 3`.

The ≈512 projection in D18 came from the **1,000-test-row** half-width (0.0163) that the readiness study
measured and **rejected**. That number describes resolution at a test size this cell does not use, standing
in for a between-seed SD that had never been measured. At the pre-registered 10,000 test rows the half-width
is 0.0051 (≈51 seeds), and against the measured SD the rule gives 3.

**Ten seeds estimate an SD; they do not establish one.** At n = 10 the SD estimate carries roughly 24%
relative error, so the replication runs at **k = 16**, not 3:

- at the measured SD 0.0012, half-width ≈ 0.00084;
- even if the true SD is twice the measurement (0.0024), half-width ≈ 0.0017, still under δ = 0.002.

### What the replication runs

**Arms `A_raw` and `B_ft30` only.** The probe singled out the top rung; the two lower rungs would add 35%
to the cost for a comparison already answered. **Seeds 341–356**, fresh under D13 — disjoint from the
probe's 331–340 and from the D18 replication's 93–330.

**Ceiling: $0.15**, well inside this document's $3.00 replication ceiling. At the measured rate (87 s of
compute per seed for two arms, 191 s of boot) sixteen seeds project to ~$0.15.

### What this does not change

The arms declared for the cell, the 10,000/10,000 row sizes, `v3_default`, and δ = 0.002 all stand. Only
`k` and the seed range are amended, which is what Stage 2 says happens here.
