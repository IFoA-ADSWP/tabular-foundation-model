# Pilot 2 — Statistical Analysis Plan

> **Supporting technical appendix.** The canonical current proposal is `docs/current/FULL_FINE_TUNING_PILOT_DESIGN.md`. This plan owns the statistical rules for the pilot; it does not define the overall proposal or scope.
>
> **Status: DRAFT for sign-off.** This plan fixes the analysis **before** any data exists, so that the
> result cannot be chosen after seeing it. Any departure is recorded as a dated deviation (§10).
> Related historical design: `docs/reference/PILOT_2_DESIGN.md` (§5, §6.5), `docs/current/PILOT_2_DECISION_LOG.md` (D4, D8), `docs/reference/PILOT_2_DECISION_GRAPH.md`.

## 1. Purpose and scope

The design says what will be *run*. This plan says what will be *computed* from it, how the numbers
will be combined, what counts as a positive result, and how the result will be reported.

It exists for one reason: the design tests many things in sequence (an epoch ladder, two experiments,
two pool policies, a control, several metrics). **Without a fixed analysis, a programme with that many
outputs will find something positive in it**, and the finding will be an artefact of which comparison
was reported.

Scope: the five gated steps of `docs/reference/PILOT_2_DECISION_GRAPH.md` and the guarded interaction off-ramp. It does
not re-open anything the design has settled.

## 2. Estimands — what is actually being estimated

**Sign convention is stated once and used everywhere.** For loss-type metrics, Δ is *arm − `A_raw`*, so
**negative means the fine-tuned arm wins**. For discrimination and calibration metrics (ROC AUC, PR AUC,
Brier), positive means improvement. Every reported number states which convention it uses.

| Level | Estimand |
| --- | --- |
| **Primary** | The **paired** difference in log loss between the fine-tuned arm and `A_raw`, on the **same test rows**, for one dataset at one budget and one split |
| **Co-primary** | The same paired difference in ROC AUC |
| **Secondary (transfer)** | The paired difference for the pooled arms against `A_raw(T)` **and** against `R_random(T)`; and the transfer gain expressed as a **fraction of `B_in_domain`'s gain** |
| **Tertiary (ladder)** | Marginal differences between adjacent epoch rungs (30 vs 10 vs 3) — exploratory, not a decision |
| **Interaction (off-ramp only)** | The difference-of-differences between two factors, with everything else held fixed |

## 3. Metrics

- **Primary:** log loss — the metric the design's Gate 1 criterion is written in terms of.
- **Co-primary:** ROC AUC.
- **Also reported, no decision role:** PR AUC (average precision), Brier, and calibration (ECE).
- **Calibration tolerance must be numeric.** Design §6.5 criterion 5 requires the ECE/Brier tolerance to
  be set **in advance** — *an unset tolerance is not a pre-registration*. This is currently **TBD** and
  is flagged in §12 as a required number before sign-off.

All metrics are computed on the held-out test rows only. What the pipeline **asserts** is that no test row
is in the training indices, the dropped remainder, the pool, or the inference **context** we construct
(design section 3.1) — each is a set operation on indices we own.

What it **cannot** assert is the same guarantee inside the library: the shipped trainer carves its own
validation split out of the rows we hand it, for early stopping. The guarantee there is that we pass it
training rows only, and the trainer's `validation_split_ratio` is **recorded per arm rather than
asserted**, so a reader can check it rather than take it on trust.

## 4. Unit of analysis, pairing, and how intervals are built

- **Unit of analysis:** one test row. Comparisons are **paired on identical test rows**, which is why
  arms are always evaluated on the same split.
- **Intervals:** paired bootstrap (10,000 resamples, percentile interval) for log loss, Brier and PR AUC;
  a paired bootstrap or DeLong interval for ROC AUC. The bootstrap resamples **rows**, not repeat-level
  means, so a split's uncertainty is not overstated by pretending its rows are independent across seeds.
- **A caution that governs every reading of this plan.** R1's *unpaired* interval widths on ROC
  (0.031–0.118) are **not** the yardstick for a paired comparison, and must not be quoted as though they
  were. The relevant noise floor is the **paired interval computed for that comparison**. R1's unpaired
  widths appear in the cost documents only as context for why one split cannot resolve small effects.
- **Repeat structure is reported separately from row-level uncertainty.** The spread across seeds is
  optimisation noise; across folds it is data noise; across rows it is sampling noise. These are three
  different quantities and are never collapsed into a single "error bar".

## 5. Aggregation and multiplicity (decision D4)

**Per dataset.** The estimate is the mean Δ over repeats, with a paired interval, reported per dataset
rather than only pooled — a pooled mean can hide a dataset where the sign reverses.

**Across datasets and targets — the primary statistic is an inverse-variance (random-effects) summary,
not a plain mean.** Targets span 9.8K–53.5K rows, so a plain mean over targets lets the largest target
dominate. Each target contributes its estimate weighted by its precision, with between-target
heterogeneity reported (the I²-style spread) rather than assumed away.

**One pre-specified primary target** for the transfer step, fixed before the run (a D4 decision). The
others are secondary and are reported as such.

**The primary pool policy is `D_pooled_schema`** (design §6.3, the coherent pool). `C_pooled_all` is
**confirmatory only** — "positive for at least one policy" across two policies is a multiplicity hazard,
and with the order fixed in advance there is no justification for choosing the winner after seeing both.

**Multiplicity.**

| Family | Comparisons | Handling |
| --- | --- | --- |
| Primary comparison, per step | **one** | no correction needed — this is the point of the isolation design |
| Per-dataset claims within a step | 4 | **Holm** correction across the family of four |
| Transfer per-target claims | 4 | Holm, reported as secondary to the primary target |
| Exploratory (epoch ladder, pool policies, calibration metrics, per-seed spread) | several | labelled **exploratory**, no decision role, no correction claimed |

**What counts as a positive claim — all three must hold:**

1. the primary comparison's **interval excludes zero**;
2. the direction matches the **pre-registered** direction for that metric's sign convention;
3. for transfer, the arm also **beats `R_random`** — without which "the pool's signal helps" cannot be
   separated from "fine-tuning on signal-free data helps".

## 6. Precision, escalation, and the rule for "inconclusive"

**Screening is separated from estimation.** Steps 0–4 are screening: *does an effect exist, and is it
bigger than the noise?* Step 5 is estimation: *how large is it, with what interval?* The two are never
mixed in a single report.

**Escalation rule, pre-registered.** If the primary interval **excludes zero** but is wider than the
decision threshold, or if it **includes zero** while the point estimate favours the arm, then extend the
repeat structure **once**, from 3 seeds × 1 split to 3 seeds × 5 folds, and no further. The escalation is
a pre-set maximum, not a judgement call made when the result is disappointing.

**If it is still inconclusive, the result is reported as inconclusive.** Not "trending", not "marginally
significant", not "underpowered but encouraging". The programme stops and reports the interval.

**The decision threshold is zero** — the rule is whether the interval excludes it — **and the measured
noise floor for that comparison is always reported alongside**, so a reader can see how much of the
interval is sampling noise.

**Interactions** carry four times the variance of a main effect in a 2×2 with equal cells, so an
interaction claim requires the pre-set maximum repeats **and** the four entry criteria in
`docs/reference/PILOT_2_DESIGN_ALTERNATIVE.md`. An interaction is never reported as a headline.

## 7. Decision rules — linkage, not restatement

This plan does **not** restate the decision rules, so it cannot drift from them. The rules are:

- **Gate 1** (design §4.4/§5), with the winning configuration **frozen** there — Stage 2 inherits the
  budget and does not re-tune per target. This is a statistical requirement, not a convenience: choosing
  the budget per target would make the result N configurations rather than one model tested once.
- **The transfer rule** (design §6.5), including the requirement that the control `R_random` is tested
  **first** — any criterion the control passes is not discriminating and must be replaced before the run.
- **The pre-registered outcome mapping** (decision log §3), followed exactly as written.

This plan specifies only **how the inputs to those rules are computed**.

## 8. Missing, failed and incomplete runs

Three states are explicit, and none of them is inferred from an absence: **incomplete** (a
`status: "running"` manifest that survived a kill), **failed arm** (`meta.FAILED.json` with error type
and effective config), and **dry run** (`dry_run: true`).

- **No imputation.** A failed arm is reported as failed, with its error type. It is not silently
  dropped, and it is not quietly replaced by a re-run under a different seed.
- A comparison is reported on the arms actually present, **with the missing arm named** — and the
  denominator states the runs attempted, not only those that produced output.
- **"No record" is never reported as "no effect."** The first pilot's arm B existed only inside an
  aggregate file for several days; that ambiguity is what this section exists to prevent.

## 9. Reporting format

Every reported comparison states: the estimand, the **sign convention**, the point estimate, the
interval, the number of test rows, the number of repeats, **the noise floor for that comparison**, the
run ids the numbers came from, and whether the step was gated and on what result.

**A negative is reported with the same detail as a positive.** The negative outcomes are deliverables
(they are the stopping points in `docs/reference/PILOT_2_DECISION_GRAPH.md`), so they are reported as findings, not as
failures to find something.

The transfer result is additionally reported **as a fraction of `B_in_domain`'s gain**, so a small
absolute gain cannot be presented as a large one.

## 10. Deviations

Any departure from this plan is recorded as a **dated deviation** stating what changed, why, and the
result computed **both ways** where that is possible. Deviations are listed in the report itself; they
are never resolved silently. A deviation agreed after seeing the result is stated as such.

## 11. Reproducibility linkage

Seeds, splits, data ref, container image and package versions are recorded per run by the pipeline's
fingerprint, and the analysis reads the **per-arm predictions** rather than re-deriving them. **Their
hashes are recorded but the analysis does not yet verify them** — stated as the gap it is, rather than
implied by the word "hashes". Reproducibility is defined as **same code, data, config and seeds — not
bit-identical output**; GPU nondeterminism is explicitly out of scope by decision, and no tolerance is
pinned to it.

## 12. What this plan does not yet settle

Stated so a reviewer can see the remaining gaps rather than assume the plan is complete:

1. **The numeric ECE/Brier calibration tolerance** (design §6.5 criterion 5) — required in advance, and
   currently unset. **This must be a number before sign-off, or criterion 5 is not pre-registered.**
2. **The primary target for the transfer step** (D4) — named before the run, not after.
3. **The minimum detectable effect** — computed rather than deferred: see §12.1.

### 12.1 The minimum detectable effect, computed

Using R1's own **paired** 95% intervals on 1,000 test rows, each dataset resolves:

| Dataset | Test rows | Positives | Can resolve |
| --- | --- | --- | --- |
| coil2000 | 1,000 | 57 | **>= 0.061** ROC |
| eudirectlapse | 1,000 | 132 | >= 0.026 |
| spanish_motor_lapse | 1,000 | 354 | >= 0.030 |
| uslapseagent | 1,000 | 369 | >= 0.009 |
| **Pooled** (inverse-variance) | | | **~>= 0.008** |

R1's observed in-domain deltas were **0.0008-0.0095**. So **three of the four datasets cannot resolve
an effect of that size at 1,000 test rows**, and this design is a test for **large** effects
(roughly >= 0.02 per dataset), not for the R1 band. Stated here so that "we were underpowered" cannot
be discovered after a null.

**The lever is not repeats.** Repeats reduce **seed and split** variance; they do not touch
**row-sampling** variance, which is what sets this floor. Only more test rows (or more positives) move
it. The 15x repeat structure therefore buys **stability, not sensitivity**, and should not be expected
to convert a 0.005 effect into a detectable one.

Two worked consequences:

- To resolve **0.02** (the band this design can address): 533 positives on coil2000, 67 on
  uslapseagent, 215 on eudirectlapse, 778 on spanish_motor_lapse - about 8,882 test rows for
  coil2000, against 9,822 in the whole dataset.
- To resolve **0.01** on coil2000 would need ~2,100 positives, about **35,500 test rows** where 9,822
  exist. **Not attainable** - a reason to state the limitation, not to fund repeats against it.

**The mechanism behind that spread: the row cap is unstratified.** `load_dataset` caps rows with a
*uniform* sample (`df.sample(n=max_rows, random_state=42)`) and only then splits **stratified**. So the
split is stratified but the cap is not, and the test set's positive count is whatever the uniform cap
happened to include -- which is why coil2000 carries 57 positives and an MDE of 0.061 while
uslapseagent carries 369 and 0.009. **A stratified cap is the cheapest available improvement to the
minimum detectable effect** -- it costs nothing at run time, and it is worth strictly more than
additional repeats, which (above) buy no sensitivity at all. Recorded here as a candidate change
rather than made, because it changes the split every existing number was computed on.

**What this means for the design's claims.** A positive result at these settings is evidence of a
large effect; a null is *not* evidence that fine-tuning is worthless at the 0.001-0.010 scale. Every
null is therefore reported **with its minimum detectable effect beside it**, so a reader can see what
the experiment could and could not have seen.

## 13. Sign-off

| Role | Name | Date |
| --- | --- | --- |
| Statistical review | ______ | ______ |
| Technical review | ______ | ______ |
| Owner (@scotthawes) | ______ | ______ |

**Once signed, this plan is fixed.** Changes are deviations under §10.
