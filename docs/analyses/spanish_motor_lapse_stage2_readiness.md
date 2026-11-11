# Is `spanish_motor_lapse` fit to carry Stage 2?

> **Status:** active — analysis, 2026-11-03. **Question:** if Stage 1 were settled positively, could
> `spanish_motor_lapse` carry Stage 2, and what must be true first? **Data:** committed
> `data/raw/*.csv`, `results/20261031T021845Z/`, and the design documents. **No spend, no launch, no
> GPU** — every number below is computed from committed files. **Decision it informs:** issue #391;
> the Stage 2 dataset choice and its pre-registered acceptance rule. **Premise note:** Stage 1 did
> not settle positively — D11 stopped the line, and was **restated on 2026-11-03** as a power stop
> rather than a null (`FINETUNING_DECISION_LOG.md`). This is a *conditional* readiness assessment,
> and it is worth having precisely because it says what a reopened Stage 2 would have to be.

## Answer in one paragraph

**Not at the planned test size — no, and the reason is resolution, not the leakage risk.** The
Spanish dataset is 53,502 rows with 18,960 positives (35.44%), the largest of the three lapse sets.
But at the anchor recipe (10,000 train / 1,000 test) it resolves a paired difference of about
**0.015–0.018 ROC AUC** and an unpaired one of **±0.034**, against an anchor that achieved **0.0036**
and an effect of interest of **+0.0009 to +0.0057**. A Spanish Stage 2 launched at the planned size
cannot see the effect it exists to test, whatever it returns. The leakage check *is* possible offline
and it clears the file of row-level label leakage, but it confirms the ticketed hazard in a sharper
form than the ticket states it: the target varies within every customer-book group (97% of rows sit
in mixed-label groups), so a policy-level outcome is being predicted partly by the customer's book
structure. It also finds a hazard the ticket does not name — two same-year claim columns that add
0.023 AUC and describe events concurrent with the lapse. **Recommendation: more seeds on
`uslapseagent`**, because the observed failure is a seed phenomenon, resolution is better there per
test row, and the pre-registered ordering already requires in-domain replication before breadth.

## 1. What the dataset actually is

Read directly from the committed CSV, not from a summary.

| | |
| --- | --- |
| rows | **53,502** (53,503 lines including header) |
| columns | 23 — 22 features + `LapseB` |
| target | `LapseB`, binary 0/1 |
| positives | **18,960** |
| positive rate | **0.354379** (35.44%) |
| missing cells | **0**, across all 23 columns |
| types | 1 object (`Type_fuel`, 3 levels), 21 numeric |

The design's scope table records "~18,961" positives; the file holds 18,960. Use 18,960.

`spanish_motor_freq.csv` shares 21 columns with this file and is **identical row-for-row** on all of
them. `spanish_motor_severity.csv` is in the same row order but its identically-named
`Cost_claims_year` is **a different quantity**: on the 5,950 rows with a claim, the lapse file's value
is a total (e.g. 2162.89) and the severity file's is a per-claim severity (e.g. 7.68). Any join across
these files therefore both leaks and silently corrupts the column. That is a trap for whoever runs
Stage 2, not a hypothetical.

## 2. The leakage / alignment check, and its result

### The check

A per-column granularity inventory — is each feature policy-level, customer-book-level, or
post-policy? — followed by three tests that the inventory makes possible:

1. **Exact label encoding.** Is any feature unique-valued, or is the label deterministic given the
   full feature vector?
2. **Within-group target variation.** Group by the customer-book columns and ask whether the labels
   disagree inside a group. If the target is policy-level and the features are book-level, they will.
3. **Post-outcome columns.** Which features describe the policy year whose end state *is* the label,
   and how much AUC do they carry?

### The inventory

| column | distinct | scope | evidence |
| --- | --- | --- | --- |
| `Distribution_channel` | 2 | channel/cohort | 2 levels, 28,086/25,416 |
| `Seniority` | 40 | customer-book | years with the insurer, 0–39 |
| `Policies_in_force` | 17 | customer-book | count of policies the customer holds |
| `Max_policies` | 17 | customer-book | equals `Policies_in_force` in 74.0% of rows; ≥ it in all but 8 |
| `Max_products` | 4 | customer-book | 1 = 50,429 rows |
| `Payment` | 2 | policy | instalment flag |
| `Premium` | 29,502 | **policy** | mean premium *falls* with `Policies_in_force` (328.66 at 1, 248.12 at 6; r = −0.10) — per-policy, not a portfolio total |
| `Type_risk`, `Area`, `Second_driver` | 4, 2, 2 | policy | — |
| `driver_age`, `licence_age` | 17,740 / 17,150 | person | — |
| `vehicle_age`, `Power`, `Cylinder_capacity`, `Value_vehicle`, `N_doors`, `Type_fuel`, `Length`, `Weight` | 69, 262, 747, 9,313, 6, 3, 1,130, 1,513 | vehicle | — |
| `N_claims_year` | 18 | **post-policy** | claims during the policy year |
| `Cost_claims_year` | 4,026 | **post-policy** | cost of those claims; `>0` iff `N_claims_year>0`, exactly, all 53,502 rows |

### Result 1 — no row-level label leakage

No column is unique-valued, so there is no hidden row identifier. Only **3 exact duplicate feature
signatures (6 rows)** exist and **none** carries disagreeing labels. The file does not encode its own
target.

### Result 2 — the ticketed hazard is real, and sharper than "portfolio-level features"

Grouping by the five customer-book columns gives **1,833 groups**. **98.8%** of rows sit in a group
with more than one row, and **906 groups covering 51,982 rows (97.2%)** contain **both** labels. The
largest group holds 3,861 rows. Lapse rate moves across the book: 0.362 at one policy in force,
0.322 at two, 0.500 at eight, 0.727 at nine (n = 22).

So the target is **policy-level** and these features are **customer-book-level**, and the label
varies freely inside every book. That is not label leakage — there is no deterministic map — but it
is exactly the mismatch the ticket names: part of any measured gain can be a cross-sell/bundling
effect read off the customer's book rather than adaptation to a policy-level decision. The offline
test **confirms** the hazard; it cannot rule it out, because with no customer key there is no
correct grouping to check against (see §4).

### Result 3 — two post-outcome columns, worth 0.023 AUC

Removing `N_claims_year` and `Cost_claims_year` costs measurable performance:

| split | all 22 features | minus the two claim columns | change |
| --- | --- | --- | --- |
| 30,000 train / 10,000 test, HGB | 0.7502 | 0.7319 | **−0.0233** |
| 10,000 train / 1,000 test, HGB | 0.7235 | 0.6993 | **−0.0242** |

Claims in the policy year are concurrent with the lapse event, not prior to it. Neither our split
assertion nor our context-disjointness assertion covers this: both check that rows do not cross, and
these columns cross in *time*, not in rows.

### Feature-block breakdown (HGB, 30,000/10,000, fixed seed)

| block | AUC |
| --- | --- |
| all 22 features | 0.7502 |
| all minus claim columns | 0.7319 |
| customer-book block only (5 cols) | 0.6727 |
| policy/driver/vehicle block only (15 cols) | 0.6646 |
| same-year claim columns only (2 cols) | ~0.52 |

No single block dominates, so the mismatch is not the whole signal — but the book block alone
reaches 0.673, which is why a gain on this dataset cannot be attributed to adaptation without an
argument.

The 10,000/1,000 HGB figure of 0.7235 reproduces the pilot's `spanish_motor_lapse` `A_raw` of 0.7230
(§5d.6 of `FINE_TUNING_PILOT_RESULTS.md`). The dataset's ceiling here is roughly 0.75, against a
`uslapseagent` `A_raw` of 0.945–0.946. That gap is **not** a task comparison — `uslapseagent`'s target
is life-policy `surrender`, while `LapseB` is a motor policy lapse, and the two datasets share no
feature vocabulary. It is a comparison of *separability*, which is what sets resolution.

## 3. Resolution at the candidate test size

`n_test = 1,000`, stratified, giving **354 positives and 646 negatives** — the size the anchor recipe
and §5d.6 both use.

### Hanley–McNeil, unpaired

With A = 0.723, n₁ = 354, n₀ = 646:

- Q₁ = A/(2−A) = 0.723/1.277 = **0.56617**
- Q₂ = 2A²/(1+A) = 1.045458/1.723 = **0.60677**
- numerator = 0.723×0.277 + 353×(0.56617−0.52273) + 645×(0.60677−0.52273)
  = 0.20027 + 15.33467 + 54.20645 = **69.7414**
- denominator = 354×646 = **228,684**
- SE = √(69.7414/228,684) = **0.017463**
- **95% half-width = 1.96 × 0.017463 = 0.0342**

The pilot's bootstrap agrees: [0.6904, 0.7539], half-width 0.0317.

### Paired — the sensitive comparison, measured

Pairing removes between-row variance, so this is the number that matters. All rows below are
measured from committed predictions or computed on committed data:

| comparison | n_test | ΔAUC | 95% CI | half-width |
| --- | --- | --- | --- | --- |
| pilot: `A_raw` vs `E_glm`, Spanish | 1,000 | +0.1065 | [+0.0754, +0.1359] | 0.0302 |
| pilot: `A_raw` vs `F_catboost`, Spanish | 1,000 | +0.0116 | [−0.0068, +0.0293] | **0.0181** |
| small-δ proxy (90% train), Spanish 10k/1k | 1,000 | −0.0038 | [−0.0194, +0.0113] | **0.0154** |
| small-δ proxy (90% train), `uslapseagent` 10k/1k | 1,000 | −0.0017 | [−0.0075, +0.0042] | **0.0058** |
| small-δ proxy, Spanish lifted to 30k/10k | 10,000 | +0.0006 | [−0.0031, +0.0041] | 0.0036 |

The proxy perturbs only the training rows (a 90% subsample of the same learner), which is the closest
offline analogue of a fine-tuned rung: a small, correlated change in the model's predictions.

### The smallest effect this can see

**At the planned 1,000 test rows: about 0.015 AUC paired, 0.034 unpaired.** Stage 1's observed effect
was +0.0009 to +0.0057, and the anchor's achieved median half-width was 0.0036 — so the Spanish
dataset at the planned size is **3–5 times coarser than the anchor and roughly 4 times coarser than
the effect**. The same proxy on `uslapseagent` at the same test size gives 0.0058; **the Spanish
dataset is the worse instrument per test row**, not the better one, because its AUC sits near 0.72
where AUC sampling variance is high, against 0.94 where it is low.

Taking the training cap to 30,000 rows *does* fix it (0.0036 measured), but that is a 10× lift on the
one lever the design already records as an artefact: *"the row cap was ours"*. Stage 2 cannot both
claim the earlier negative was a cap artefact and inherit the same cap.

For reference, the unpaired size needed for a given half-width (bisection on the Hanley–McNeil
form, p = 0.354): 0.010 → 11,695 test rows; 0.005 → 46,780; **0.003 → 129,943, which is 2.4× the
entire dataset.** Unpaired resolution at fine-tuning scale is unreachable here under any cap.

## 4. What cannot be checked offline — precisely

The dataset carries **no policy identifier, no customer identifier, and no date**. Verified: no column
is unique-valued, and no header contains a date or period token. The temporal-split limitation (L1)
is therefore confirmed from the header itself, not inherited from a summary.

Because there is no key, three things are out of reach offline:

1. **Row independence.** We cannot verify that the 53,502 rows are independent policies rather than
   repeated observations of the same customer-year. The near-absence of duplicate feature signatures
   (6 rows) is consistent with unique policies but does not prove it.
2. **A true portfolio grouping.** Test 2 approximates the group with feature-defined buckets. A real
   key would let us ask whether the target is *ever* constant within a genuine portfolio — the
   question that decides whether the book columns are covariates or aggregates. Feature-defined
   groups cannot distinguish those.
3. **A temporal split.** Unchanged from L1 and unfixable with this file.

What would close it: the vendor's row key, or the raw extract with policy/customer/effective-date
columns. Neither is obtainable from the committed CSV, and neither is worth buying for Stage 2 before
the seed question is settled.

What *is* closed offline: no label encoding, no post-outcome columns left undeclared, no cross-file
join left unguarded, and the granularity inventory is committed in §2.

## 5. Recommendation: more seeds on `uslapseagent`

**Stage 2 should be more seeds on `uslapseagent`, not `spanish_motor_lapse` and not a different
dataset.** Four pieces of evidence:

1. **The observed failure is a seed phenomenon, and two seeds cannot characterise it.** Seed 43
   passed all three rungs (+0.0031 / +0.0050 / +0.0057); seed 44 failed all three (+0.0009 / +0.0013
   / +0.0010). A 1-of-2 pass rate is consistent with a true rate anywhere from roughly 20% to 80%.
   Two more seeds bound it; a Spanish run does not touch it.
2. **`uslapseagent` is the better instrument per test row.** 0.0058 against 0.0154 for the same
   perturbation at the same test size — measured, not modelled.
3. **The pre-registered ordering already says so.** The statistical plan's Phase 2 seed gate: *"the
   10K `uslapseagent` result must repeat on two additional seeds before the four-dataset breadth
   result is treated as evidence for generalisation."* A Spanish Stage 2 ahead of the seed gate
   inverts the plan's own staging.
4. **Cost does not decide it; interpretability does.** One four-arm 10,000-row run is **$0.0368**
   measured; the anchor launch was **$0.0288 / 6.52 min** for eight arm records. Two more seeds come
   to roughly **$0.06–0.07**, and a Spanish Stage 2 costs the same order. The ticket is right that
   the cheapest path is not automatically a new dataset — but here the new dataset is not cheaper
   *or* more informative. It adds three unresolved hazards (post-outcome claim columns, the
   customer/policy mismatch, a 0.023 AUC contribution from same-year claims) and buys a question the
   design defers.

**Honest costs of this recommendation.** Two of them, both real:

- The escalation rule forbids a post-hoc seed increase — *"the current design does not authorize a
  post-hoc increase in seeds, splits, datasets, or arms."* Two more seeds need a **dated design
  amendment written before the run**, not a decision taken after seeing seeds 43 and 44 disagree.
- The anchor diagnosis is clear that more seeds **stabilise** an estimate but **do not narrow** the
  interval, and that the only lever on row-sampling variance is more test rows. So this
  recommendation buys a *pass rate*, not resolution. If the question is "is an effect of 0.002 real
  at this test size", no dataset answers it at 1,000 test rows and the answer is more test rows on
  `uslapseagent` (~4,000, per that diagnosis), not a fourth dataset.

`eudirectlapse` is ruled out on the same resolution grounds and more harshly: 23,060 rows, 2,954
positives (12.8%), and a pilot `A_raw` of 0.5879 with a 0.1078 unpaired CI width — the coarsest of
the four.

## 6. The acceptance rule for Stage 2, written before it runs

To be committed, dated, and unedited before launch. Modelled on D9, with the resolution and leakage
preconditions this ticket establishes.

**Preconditions (checked before spend, not after).**

- **P1 — Resolution floor.** The stated test size must give a paired 95% half-width of **≤ 0.006**,
  measured on the dataset by the perturbation proxy in §3 or computed by Hanley–McNeil, and the
  figure must be *measured*, not modelled. Quoting a resolution the design does not achieve is the
  D-1 failure and is not repeatable. **`spanish_motor_lapse` at 1,000 test rows fails P1
  (0.015–0.018). A Spanish run at the planned size cannot pass Stage 2 whatever it returns** — this
  rule is what converts "unresolvable" into a pre-run rejection rather than a post-hoc excuse.
- **P2 — Granularity inventory.** The per-column scope table is committed, and the same-year claim
  columns are either excluded from the primary arms or reported as a separately labelled arm. No
  join across the three Spanish files in any arm that is used to decide.
- **P3 — Row independence.** If the dataset has no policy/customer key, that is stated as a limit
  alongside the acceptance, not discovered in the write-up.
- **P4 — Provenance.** Every run carries its own in-run `A_raw` and its own version provenance. The
  anchor recorded `version: auto` with no operator pin; a Stage 2 result measured under a different
  resolution must not be pooled with it or described as the same version.

**Pass condition.** Stage 2 passes for a seed when, for **all three rungs**, the paired 95%
bootstrap interval of ΔROC AUC against that run's own `A_raw` excludes zero in the positive
direction. A rung that fails is reported as failing and is not dropped. **Stage 2 passes for a
dataset only if every pre-registered seed passes** — no majority rule, no best-of-n, no seed
excluded after the fact.

**Calibration.** Brier must not increase beyond a **numeric tolerance stated in the same document
before launch** (D9's requirement). A ranking pass with a calibration regression is reported as a
split outcome, not a pass.

**Reading, pre-registered.**

| outcome | reading | next step |
| --- | --- | --- |
| all seeds pass all rungs | in-domain gain is real across splits | the seed gate is met; breadth work may open |
| all seeds fail all rungs | fair negative, now with a variance estimate | stop the line; do not re-open on one favourable seed |
| seeds disagree | the effect is split-dependent and this design resolves it as such | report the **pass rate**, not a near miss; escalate seeds only by dated amendment |
| any run below P1 | the run is void as evidence, before it is read | do not run it; raise the test size or change instruments |
| a new dataset reaches the gate | transfer is on the table | apply P2/P3 to it first; Spanish cannot enter at the planned size |

## 7. Files and sources

- Dataset: `data/raw/spanish_motor_lapse.csv` (target `LapseB`), with `spanish_motor_freq.csv` and
  `spanish_motor_severity.csv` for the cross-file join check.
- Anchor records: `results/20261031T021845Z/uslapseagent/<arm>/seed{43,44}_foldNone/meta.json` —
  `n_rows` 29,317, `target` `surrender`, `positive_rate` 0.378552, `test_rows` 1,000, `pos_test` 377,
  `A_raw` AUC 0.9461 (seed 43) / 0.9451 (seed 44). `provenance.model.version` is `auto` — **no
  operator pin, so do not name a version era for this result.**
- Row-level predictions: `results/20261031T021845Z/pilot_predictions.parquet` (paired bootstrap
  recomputed here at 4,000 resamples, fixed seed).
- Leakage and hazard: `docs/current/FINETUNING_EXPERIMENT_REFERENCE.md` §5 (limitation 5) and the
  §"Scope decision: lapse classification" (13 Sep).
- Resolution precedent and the D-1 correction:
  `docs/analyses/anchor_power_diagnosis.md`; `docs/current/FINETUNING_STATISTICAL_ANALYSIS_PLAN.md`
  §12.1 and D-1.
- Acceptance precedent: `docs/current/FINETUNING_DECISION_LOG.md` D9 (acceptance), D11 (the stop).
- Cost: `docs/current/FINETUNING_COST_AND_CONTROLS.md`; $0.0368 measured for a four-arm 10,000-row
  run, $0.0288 / 6.52 min for the anchor launch.
- Prior Spanish pilot figures: `docs/reference/FINE_TUNING_PILOT_RESULTS.md` §5d.6 (`A_raw` 0.7230,
  CI [0.6904, 0.7539]).
