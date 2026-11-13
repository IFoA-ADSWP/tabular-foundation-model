# Replication sizing — what design could settle 0.002–0.006 AUC, and what it costs

> **Status:** active — analysis for issue #390, 2026-11-03, **superseded in shape by D13** (a
> probe-derived seed count and rung substitution replace this document's fixed "Design R-390" of 57
> seeds; the arithmetic, the cost model and the rejected-option findings stand and are cited by D12 and
> D13). **No run was performed, nothing
> was spent, no GPU was touched.** Every figure below is arithmetic over committed records.
> **Question:** what design — test rows, seeds, and aggregation rule — could settle an effect of
> about 0.002–0.006 AUC, and what does that cost?
> **Data:** `results/20261031T021845Z/` (the anchor, eight arm records), the half-widths in
> `anchor_power_diagnosis.md`, measured arm times from each record's `meta.json`, and
> the permutation null control recorded on #338 / #125 (2026-11-02).

## Answer in one paragraph

**1,000 test rows across 57 seeds, reporting a random-effects interval over seeds, at a measured cost
of $0.10–$0.12.** The row lever alone cannot do it: at 80% power the row-only design needs
**6,620** test rows, which is below the dataset's 19,317-row ceiling but rests on a variance estimate
the anchor contradicts, and the ticket's own ~3,000 rows is a **50%**-power design, not 80%. The
seed lever is the one that matters, because the noise that made the anchor ambiguous is *between
splits*, and more test rows do not shrink it at all. Under the only measured null reference available
(per-seed SD 0.0052–0.0055, #338), 80% power at 0.002 AUC needs **57 seeds at 1,000 test rows**. That
design is affordable precisely because the anchor's arms are cheap — $7.362 × 10⁻⁵ per wall-second
measured — so the whole replication is about the price of one anchor relaunch and a half. Stop reading
the per-seed conjunction (D9): at 57 seeds its power is 1.3 × 10⁻⁴¹.

## 1. Which version these numbers belong to

The anchor's provenance block records:

```
"model": { "version": "auto", "version_source": "auto",
           "weights_sha256": "d0d865d5…", "client_version": "8.5.0" }
"checkpoints": ["tabpfn-v3-classifier-v3_default.ckpt"]
```

**The anchor has no operator pin.** It says `version: auto`; what `auto` resolved to is named
separately in the same record as a checkpoint file and a weights hash. Per `docs/MODEL_VERSIONS.md`,
a pilot record says `pinned:<value>` only when a human pinned, and `auto` when nobody did. So every
timing, cost and half-width in this document is stated as **measured under `version: auto` at
tabpfn 8.5.0 on the checkpoint named in the record** — not as a `v3_default` result. A replication
must add an explicit pin, because otherwise its arm times are not comparable to these and its claim
inherits the same attribution gap.

## 2. Measured inputs, and where each comes from

| Input | Value | Source |
|---|---|---|
| Median 95% paired-bootstrap half-width, 1,000 test rows | **0.0036** (0.0026–0.0046) | `anchor_power_diagnosis.md` |
| Sum of `run_time_seconds` over the eight arm records | **265.35 s** | `results/20261031T021845Z/` |
| Per-arm mean time (A_raw / B_ft3 / B_ft10 / B_ft30) | 5.80 / 15.30 / 31.71 / 79.87 s | same |
| Launch wall clock, one launch, instance 58479781 | **6.52 min = 391.2 s** | D11 in `FINETUNING_DECISION_LOG.md` |
| Launch spend | **$0.0288** | same |
| Derived measured rate | **$7.362 × 10⁻⁵ per wall-second** | $0.0288 ÷ 391.2 s |
| Launch overhead (provision, weights, verification) | **125.85 s ($0.0093)** | 391.2 − 265.35 |
| Per-seed arm time, 2 arms (A_raw + B_ft3) | **21.10 s** | (11.598 + 30.595) ÷ 2 |
| Per-seed arm time, 4 arms | **132.68 s** | 265.35 ÷ 2 |
| Null: per-seed SD of ΔAUC; 95% half-width | **0.0052–0.0055; ≈ ±0.010** | null control, #338, 2026-11-02 |
| Null: two-seed AND rule false-positive rate | **0.0008–0.0012** | null control, #338, 2026-11-02 |
| Dataset ceiling | 29,317 rows total; 11,500 used under the row cap | `provenance.dataset` in any arm record |

The rate in row 7 is the only defensible per-second price for *this* shape on *this* instance: it is
spend divided by billed wall clock for the run whose arms produced rows 2–3. The separately measured
$0.0368 for a four-arm 10,000-row probe is **not** transferable — it works out at $0.0092 per arm
against the anchor's $0.0036, a 2.6× difference that comes from a different dataset and shape.
Quoting the probe figure here would overstate the replication by 2.6×.

## 3. Two half-widths, and which one is scaled

Two numbers in the ticket look alike and are not:

- **0.0036** — the median 95% interval half-width around an **observed** ΔAUC at 1,000 test rows. It
  is the width the design *reports*, and it is the quantity to which 1/√n applies.
- **±0.010** — the 95% band the ΔAUC **point estimate** occupies under a *known null*, from 5,000
  label permutations per seed. It is not an interval around an effect; it is the noise floor of the
  estimator with the association destroyed.

**I scale 0.0036.** The reason the other is *not* the thing to shrink: ±0.010 is a referee, not a
resolution target. It is what you check a decision rule against — and it is scale-free in the
decision, because a rule that fires on 0.002 must not also fire on H0 noise, whatever the sample size.
Shrinking it with rows would not fix the problem the anchor actually had, which was **not** an
interval that was too wide. Seed 44's intervals *did* contain zero and were *not* too wide; they were
correct and they said "indistinguishable". What failed was that one split's answer was read as the
answer.

The remaining, decisive fact is that ±0.010 is a *per-seed* band. It says a single 1,000-row split can
move the ΔAUC point estimate by ±0.010 under H0 — five times the effect of interest. Rows buy a
narrower interval; they do not buy a second split.

## 4. Rows: the arithmetic at 80% power

Standard two-sided sizing, α = 0.05, power 0.80:

```
z  = z(1−α/2) + z(power) = 1.95996 + 0.84162 = 2.80159
SE required  = δ_min / z            = 0.002 / 2.80159 = 0.0007139
SE observed  = half-width / 1.95996 = 0.0036 / 1.95996 = 0.0018370   (at n = 1,000)
n multiplier = (SE_observed / SE_required)² = (0.0018370 / 0.0007139)² = 2.5729² = 6.62
n required   = 6.62 × 1,000 = 6,620 test rows
```

Per-rung cross-check, because the half-width is rung-specific, not a constant:

| basis | half-width | SE | ×rows | test rows |
|---|---:|---:|---:|---:|
| tightest rung (seed 44, B_ft3) | 0.0026 | 0.001327 | 3.45 | 3,450 |
| **median** | **0.0036** | **0.001837** | **6.62** | **6,620** |
| widest rung (seed 43, B_ft30) | 0.0046 | 0.002347 | 10.81 | 10,810 |

**The ticket's ~3,000 rows is a 50% design.** Setting the half-width equal to the effect is, by
definition, the 50% point: at n = 3,244 the SE is 0.001021 and power is
Φ(0.002/0.001021 − 1.96) = Φ(−0.0001) = **0.500**. The 1/√n arithmetic in the ticket is right and its
target is wrong — "half-width ≤ effect" is not 80% power, it is a coin flip. 80% needs
half-width ≈ 0.70 × effect, i.e. 6,620 rows.

The row lever is also **bounded**. Lifting the row cap gives 29,317 total rows; with the 10,000
training rows held fixed for comparability, the ceiling is **19,317 test rows**. That is 2.9× the
1,000 measured, so the best case is:

| basis | SE at 19,317 rows | half-width | power at δ = 0.002 |
|---|---:|---:|---:|
| scaled from 0.0036 (bootstrap) | 0.000418 | 0.00082 | **> 0.99** |
| scaled from the null SD 0.00535 | 0.001217 | 0.00239 | **0.38** |

Two measured references give a factor-of-2.9 disagreement about the same physical noise, and two seeds
cannot arbitrate it. That disagreement is the design problem, not an inconvenience in it.

## 5. Seeds: the arithmetic, and why rows cannot substitute

Per-seed variance at n test rows decomposes as

```
V(n) = τ² + σ_w²(1,000) · (1,000 / n)
```

τ² is **split-to-split** variance: a different `random_state` takes a different 10,000 training rows,
fits a different model, and has a genuinely different true ΔAUC. σ_w² is measurement noise on the test
set. **τ does not depend on the test set at all**, so no number of extra test rows can drive V below
τ². That is the structural answer to "why not just buy rows".

Three candidate per-seed SDs, each with its provenance and its honesty budget:

| basis | per-seed SD | k for 80% power | note |
|---|---:|---:|---|
| bootstrap (row noise only) | 0.001837 | 6.62 → **7** | assumes τ = 0 — contradicted by the anchor |
| observed 2-seed spread, τ̂ | 0.00250 | 12.26 → **13** | **df = 1**; two seeds cannot estimate this |
| measured null band, #338 | 0.00535 | 56.16 → **57** | the only measured reference for the estimator's noise |

τ̂ comes from the two seeds' per-seed means (seed 43: 0.00460, seed 44: 0.00107; difference 0.00353,
÷ √2 = 0.00250) and is quoted only to show its *magnitude*. It is exactly the estimate the ticket
correctly says cannot be made: a two-point SD has one degree of freedom, and the per-seed pair
disagrees by 0.0022–0.0047 across rungs — on the same rows, with the same arms. That spread is
1.2–2.6× the bootstrap SE, which is direct committed evidence that the bootstrap half-width
understates seed-to-seed movement.

**Pre-register the 57-seed figure.** Sizing to τ̂ would repeat the anchor's error one level up: it is
a number estimated from the same two seeds that produced the ambiguity. The cost difference is $0.07
(§7), so the conservative design costs less than the argument about which estimate to believe.

The 57-seed design's operating characteristics, computed:

```
SE = 0.00535 / √57 = 0.0007086
95% half-width    = 1.96 × 0.0007086 = 0.00139
power at δ=0.002  = Φ(0.002/0.0007086 − 1.96) = Φ(0.862) = 0.806
```

Because it is symmetrical in a two-sided test, that same 0.806 is also the power to **exclude**
δ = 0.002 when the true effect is zero — which is what makes an unambiguous "no effect" answer
possible (§8).

## 6. Which statistic, and its false-positive rate

| rule | statistic | FPR | power at δ = 0.002, k = 57 |
|---|---|---|---|
| **Per-seed AND** (D9 as written) | every seed's interval excludes 0, same direction | **0.0008–0.0012** measured at k = 2 (#338) | **1.3 × 10⁻⁴¹** |
| **Pooled rows** | one bootstrap over all seeds' rows | 0.05 nominal → **0.25 truly** (see below) | > 0.99 |
| **Random-effects over seeds** (recommended) | δ̂ ± 1.96·√((τ² + σ_w²)/k) | **≈ 0.05**, verified against the null | **0.81** |

**Per-seed AND cannot be extended.** Its measured 0.001 FPR comes *from* being a conjunction: at
k = 2 the implied per-seed exclusion rate under H0 is √0.001 ≈ 0.03. Power is multiplicative in the
same way. A single seed at 1,000 rows has power Φ(0.002/0.001837 − 1.96) = Φ(−0.871) = **0.19** for
this effect, so the probability that all 57 clear is 0.19⁵⁷ = 1.3 × 10⁻⁴¹. D9's rule is not
"conservative"; it is a design that stops working the moment you add seeds, and its 0.001 FPR is
bought entirely with power.

**Pooled rows is anticonservative, and gets worse with more rows.** Pooling treats k·n rows as iid and
so reports SE = σ_w/√k, discarding τ². The true SE is √((σ_w²+τ²)/k), i.e. the reported SE is
understated by m = √(1 + τ²/σ_w²). Measured-anchor numbers:

| configuration | σ_w | m | true FPR at nominal 5% |
|---|---:|---:|---:|
| 1,000 rows/seed, τ̂ = 0.0025 | 0.001837 | 1.69 | **0.25** |
| 6,620 rows/seed, τ̂ = 0.0025 | 0.000714 | 3.64 | **0.59** |

This is the trap in "just add rows": the more test rows you buy, the *more* anticonservative pooling
becomes, because you shrink σ_w while τ stays put. A pooled 95% interval at 6,620 rows would declare
an effect 59% of the time under a true null.

**Recommended: random-effects (REML) 95% interval over the k per-seed ΔAUC values**, effect declared
when the interval excludes 0. At k = 57 the between-seed variance is estimated from 56 degrees of
freedom, so the small-k anticonservatism of DerSimonian–Laird (the reason a k=5 random-effects
interval runs 8–12% FPR) is not in play; nominal ≈ actual. The verification is empirical and cheap:
run the shipped rule over the 5,000-permutation null capture for each seed and require the measured
aggregate FPR to land in 0.03–0.07. If it does not, widen the interval before the run, not after.

The trade must be written down: 5% FPR is 40–60× the anchor's 0.001. Buying 0.001 back costs 2.18×
the sample — 124 seeds, $0.20 instead of $0.10. **Since the whole design is pennies, buy the strict
rule if a 5% false-positive rate is uncomfortable.** There is no reason to accept a weaker rule to
save $0.10.

## 7. Cost and launch shape, from measured arm times and measured spend

Built as `wall = Σ arm times + launches × 125.85 s`, priced at the measured $7.362 × 10⁻⁵/s. No
per-run modelled figure is used.

| shape | arm-seconds | launches | wall | cost |
|---|---:|---:|---:|---:|
| **57 seeds × 2 arms (A_raw + B_ft3), 1 launch** | 1,202.5 | 1 | 22.1 min | **$0.098** |
| **57 × 2, 3 launches of 19 seeds (recommended)** | 1,202.5 | 3 | 26.3 min | **$0.116** |
| 57 × 2, worst-case arm times (use each arm's slower seed) | 1,393.6 | 1 | 25.3 min | $0.112 |
| 57 seeds × 4 arms (all rungs) | 7,562.5 | 1 | 128.1 min | $0.566 |
| 76 × 2 (three primary rungs, Bonferroni α = 0.0167) | 1,603.3 | 1 | 28.8 min | $0.127 |
| 124 × 2 (α = 0.001, matching the anchor's strictness) | 2,616.0 | 1 | 45.7 min | $0.202 |
| 13 × 2 at 3,244 rows (the τ̂-based design) | 274.3 | 1 | 6.7 min | $0.030 |

**Launch shape: 3 launches of 19 seeds each, $0.12, 26 minutes.** One launch is cheaper ($0.098) but a
single failed lease loses every seed; at three launches a lost launch costs a third and the overhead
never exceeds $0.028. The worst-case arm-time row shows the arm-time jitter is real
(A_raw ran 7.37 s on seed 43 and 4.23 s on seed 44 — 74% apart) and that the plan does not depend on
the fast seed.

Two costs are deliberately **not** in the table because they are not measured:

- **Prediction time at >1,000 test rows.** A_raw's 5.80 s mixes 10,000 context rows with 1,000 test
  rows and the record cannot separate them, so a 6,620-row or 19,317-row design's cost is unknown.
  A one-arm timing probe is the measurement that would price it; until it exists, any row-heavy
  design's cost is modelled, which D10 forbids.
- **The pin.** Adding an explicit `TABPFN_MODEL_PATH` changes weight download and cache behaviour
  (`cached_before: true`, `downloaded: true` on the anchor). First-launch overhead may exceed the
  measured 125.85 s.

## 8. The design, stated as a pre-registration

> **Design R-390.** `uslapseagent`, 10,000 training rows (unchanged), **1,000 test rows**, **57
> seeds**, two arms per seed (`A_raw`, `B_ft3`). Primary estimand: the mean over seeds of the paired
> ΔAUC (arm − `A_raw`, positive = fine-tuning improves). Reported statistic: a random-effects (REML)
> 95% interval over the 57 per-seed ΔAUC values. Model pinned explicitly, not `auto`.
> `B_ft10` / `B_ft30` are secondary and unadjusted, or dropped.
>
> **"Detected"** = the interval excludes 0. **"No effect"** = the interval lies **entirely inside**
> [−0.002, +0.002]. **"Unresolved"** = the interval contains 0 but reaches beyond ±0.002 — reported
> as unresolved, never as no effect.

Both arms of that rule were checked above: detection power at a true 0.002 is 0.806, and the power to
exclude 0.002 when the truth is 0 is also 0.806. So the design can return either answer at the
pre-registered 80%, which is the property the anchor lacked.

**The one-sentence "no effect" definition:** *no effect means the pre-registered random-effects 95%
interval over all 57 seeds lies wholly inside [−0.002, +0.002]; an interval that contains zero but
reaches past ±0.002 is "unresolved at this design", never "no effect".*

That sentence exists because the anchor's failure was a reporting ambiguity, not a statistical one:
seed 44 returned intervals containing zero, and "fine-tuning does not help" was available as a
reading until the power diagnosis retired it. An equivalence bound removes the reading.

## 9. Where the ticket's own assumptions did not hold

1. **"~3.2× the test rows (~3,000)" is a 50% design, not 80%.** Half-width ≤ effect is the 50%
   point by construction. 80% needs 6,620 rows (§4). The 1/√n relation is correct; the target is not.
2. **Rows are not the only lever, and for the seed lottery they are not a lever at all.** τ² is a
   property of the training split. The ticket's sizing treats the design as one estimator with one
   variance; it is two, and the one that broke the anchor does not respond to test rows (§5).
3. **The row lever has a ceiling the ticket does not price.** 19,317 test rows is the whole remaining
   dataset, and under the conservative basis that ceiling still only reaches 38% power (§4). A design
   written as "buy 3.2× rows" has nowhere to go if the first answer is still ambiguous.
4. **"Two seeds cannot estimate between-seed variance" is right, and it bites harder than the ticket
   allows.** If τ is unestimable, no seed-based design can be sized from it — which is why the answer
   is sized to the measured null SD (0.00535) rather than to the observed 0.0036. The ticket's
   arithmetic implicitly used the 0.0036 as if it were the total noise, which is the same conflation
   it warns against in trap 1.
5. **D9's AND rule is not a rule that scales.** Its 0.001 FPR is a product of k terms, and so is its
   power. At 57 seeds power is 1.3 × 10⁻⁴¹. The ticket says the AND rule "is not an estimate of how
   much a seed can move the result" — true, and additionally it cannot be repaired by adding seeds.
6. **The ticket's 0.002–0.006 band and R1's +0.0022 to +0.0034 do not overlap at the bottom.** The
   design target (0.002) is set below R1's own lower bound, so what is being sized is "the smallest
   effect anyone would act on", not "the effect R1 saw". Those are different questions and the
   document should say which one it answered. It answered the first.
7. **The $0.0368 probe figure does not transfer.** It implies $0.0092/arm against the anchor's
   $0.0036/arm. Only the anchor's own spend-per-wall-second prices the anchor's shape (§2).

## 10. What must be measured before this launches

| Open item | Why it blocks | Cheapest measurement |
|---|---|---|
| Prediction time at >1,000 test rows | prices any row-heavy design; D10 forbids modelling it | one `A_raw` timing probe at the target row count |
| Aggregate FPR of the chosen rule | the 57-seed rule is new; only the 2-seed rule has a measured FPR | run the rule over the existing 5,000-permutation null capture (no GPU) |
| Whether τ̂ ≈ 0.0025 survives at k = 10 | would let the design stop at 13 seeds and $0.03 | 10 seeds, $0.02 — but **only as a separate, pre-declared feasibility step**, never as optional stopping on the primary test |

## 11. Sources

- Half-widths, pooling, D-1 reconciliation: `anchor_power_diagnosis.md`
- Arm times, devices, versions, dataset provenance: the eight `meta.json` records under
  `results/20261031T021845Z/uslapseagent/`
- Launch wall clock, spend, D9 rule text, D10/D11: `FINETUNING_DECISION_LOG.md`
- §12.1 resolution conflict and D-1: `FINETUNING_STATISTICAL_ANALYSIS_PLAN.md`
- Measured cost anchors: `FINETUNING_COST_AND_CONTROLS.md`
- Version attribution rules: `docs/MODEL_VERSIONS.md`
- Null control (per-seed SD 0.0052–0.0055, ±0.010 band, two-seed FPR 0.0008–0.0012):
  null control, #338, 2026-11-02 — recorded on issues #338 and #125, not in the repo
