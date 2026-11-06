# D5 — why the linear method beats TabPFN on `eudirectlapse`

> **Status:** **provisional** — diagnostic, 2026-11-06. Recorded for later consideration, **not
> conclusive**: the mechanism claim is underpowered at five seeds, measured at `v2_5` while the
> phenomenon is `v3_default`, and its decisive feature is the competitor's own output. §7 states what
> would be required; §9 records it as a follow-up.
> **Question:** why does the linear method beat TabPFN on
> `eudirectlapse`, and is the deficit a missing feature or a wrong functional form?
> **Design:** D5 / ticket #306. **Evidence:** `scripts/eval/lapse_benchmark_v1/results_per_split.csv`
> (reproduction), `scripts/diagnostics/d5_eudirectlapse.py` (regimes, ladder), and
> `scripts/diagnostics/d1_profiling.py` (dataset profile).
> **Verdict:** the lever is **the additive functional form**, and the feature that supplies it is the
> linear method's own fitted log-odds — provisionally (§7, §9).

## Answer

On `eudirectlapse` the linear method leads TabPFN by 0.0159 AUC at full data (§14.10, `v3_default`).

Three measurements say why, and they point the same way:

1. **The two methods do not use "different features" so much as different columns holding the same
   information.** The premium columns are 0.9905 correlated, and D2's top-ten disagreement sits
   inside that block.
2. **The signal is additive but diffuse.** It is not carried by a handful of features: the linear
   model's AUC keeps rising as features are added, all the way to all eighteen.
3. **Handing TabPFN the linear form closes 88% of the gap.** With the linear method's fitted
   log-odds supplied as a feature, the residual difference is `+0.0031` with an interval that covers
   zero at five seeds — down from `+0.0256`.

So the evidence points to a **functional form** deficit, provisionally — the strength of that claim is
bounded by five seeds, a `v2_5` measurement, and a decisive feature that is the competitor's own
output (§7). What makes the ticket's own distinction answerable:

- **"TabPFN needs these features"** is true only in a circular form: the feature that closes the gap
  is the output of the very model it is being compared against. It cannot be given without first
  fitting the linear model.
- **"The linear method is the right method for this dataset"** is what remains once that circularity
  is stated. Nothing here shows TabPFN doing better than the linear method on this dataset; the best
  it achieves is not worse.

## 1. The gap, and which model version it belongs to

| Method | AUC | Source |
|---|---|---|
| Linear (`lr`) | **0.6260 ± 0.0037** | §14.10, 5 folds, `v3_default` |
| GBM | 0.6138 ± 0.0043 | §14.10 |
| TabPFN | 0.6101 ± 0.0049 | §14.10 |

**Wrongness check, passed.** Re-deriving those three from the committed per-fold rows gives 0.62596,
0.61375 and 0.61007 — a worst deviation of **0.00005**. The gap being explained is the gap the
evidence records.

**The version boundary is load-bearing, and this diagnostic crosses it deliberately.** The rows above
are `v3_default` through the hosted client. Everything this diagnostic measured itself is `v2_5`: the
local package is `tabpfn` 6.4.1, which enumerates `V2` and `V2_5` and has no V3 checkpoint, so a local
run **cannot** reproduce or adjudicate a v3 number. The regime comparison is therefore a
within-experiment paired comparison — same version, same folds, same rows, one feature set changed —
which is internally valid and externally says nothing about v3. No number here is quoted beside a v3
number as if the two were one table.

## 2. D2's "different features" is partly a collinearity artefact

D2 (#303) read `eudirectlapse` as **mixed**: top-ten Jaccard 0.54 between TabPFN and
the GLM, with the GLM's extra features `prem_final`, `prem_freqperyear`, `polholder_job` and TabPFN's
`prem_pure`, `policy_caruse`, `polholder_BMCevol`.

The premium block defeats that reading. Measured correlation, all 23,060 rows:

| | `prem_final` | `prem_last` | `prem_market` | `prem_pure` |
|---|---|---|---|---|
| `prem_final` | 1.000 | 0.951 | 0.895 | **0.991** |
| `prem_last` | 0.951 | 1.000 | 0.839 | 0.926 |
| `prem_market` | 0.895 | 0.839 | 1.000 | 0.899 |
| `prem_pure` | **0.991** | 0.926 | 0.899 | 1.000 |

`prem_final` and `prem_pure` are the same column to three decimal places of correlation. A permutation
importance that ranks one first and the other second has split credit inside a collinear block; it has
not found two different features. **D2's disagreement on this dataset is smaller than its Jaccard
makes it look**, and it should not be read as evidence of feature coverage.

**D1's profile agrees, and strengthens the point.** `scripts/diagnostics/d1_profiling.py` on the same
bytes (`sha256 c05777d1…`, run `20261106T-d5-cites-d1`) reports `max_abs_feature_correlation`
**0.990542** — the same figure this tool measured independently — and a **max VIF of 92.8**, which
is severe multicollinearity by anyone's threshold. The profile also fixes the shape of the problem:
23,060 rows, 18 features (9 numeric, 9 categorical, ratio 1.0), **no missing values at all**, 63
columns after one-hot encoding, and a feature:row ratio of 0.0027. And the target itself is thin —
12.81% positive, 2,954 positives, **entropy 0.552 bits** against a 1-bit ceiling.

Two consequences follow before any model is fitted. The premium block is one signal wearing four
names; and there is no missingness or high-cardinality pathology for TabPFN to be defeated by. That
leaves functional form as the open candidate, which is what §4 tests.

## 3. The signal is additive but diffuse

Full data, 5 folds, standardised logistic regression, features added in order of marginal signal:

| k | 1 | 2 | 3 | 5 | 10 | 18 |
|---|---|---|---|---|---|---|
| AUC | 0.5659 | 0.5821 | 0.5857 | 0.5903 | 0.6117 | **0.6159 |

The plan predicted that three features would reach ~0.62. They do not. The AUC keeps climbing with
every rung added, which is what a **weak, spread-out additive** signal looks like: each feature
contributes a little, and none carries the problem.

This is the strongest evidence against a coverage explanation **before any model is fitted**. If the
answer were "TabPFN is missing the key features", the key features would have to be identifiable, and
they are not — there is no knee in this curve.

The top rung, 0.6159, is 0.0101 below §14.10's Linear (0.6260) because it is a different estimator
(standardised, L2, this tool's folds) rather than a rebuild of that row. The reproduction of §14.10 is
carried by the committed evidence in §1, not by this table.

## 4. Three regimes: what closes the gap

2,000-row subsample (1,500 train / 500 test), five seeds, identical rows across methods and regimes.
Both methods are refitted in every cell.

| Regime | Linear | TabPFN | Δ (linear − TabPFN) | Seeds linear ahead | Features |
|---|---|---|---|---|---|
| `benchmark` | 0.5855 | 0.5598 | **+0.0256 ± 0.0077** | 5/5 | all 18, category codes |
| `glm_top5` | 0.5701 | 0.5564 | +0.0137 ± 0.0140 | 3/5 | the 5 the linear method leans on |
| `engineered` | 0.5853 | 0.5823 | **+0.0031 ± 0.0029** | 4/5 | 18 + linear log-odds; premium block → PC1 |

**`glm_top5` shows fewer features is not the lever.** TabPFN scored *slightly worse* than in the
benchmark regime (0.5564 vs 0.5598). The gap narrowed because the linear method lost more
(0.5855 → 0.5701), not because TabPFN gained. Dropping the columns the linear method does not lean on
does nothing for TabPFN.

**`engineered` closes 88% of the gap.** Per-seed deltas, in seed order: `+0.0031, −0.0064, +0.0069,
+0.0007, +0.0111`. Mean `+0.0031`, 95% t interval `[−0.0051, +0.0113]`. The interval covers zero and
one seed reverses, so:

- **the gap is closed to within this design's resolution**, which is what five seeds and a
  between-seed SD of 0.0066 can resolve at this row cap; and
- **equality is not proven.** A residual of +0.003 would be consistent with this interval too. The
  honest statement is "not separable from zero", not "no difference".

**The earn-back is not a new method.** The `engineered` regime gives TabPFN the linear method's
fitted log-odds as a column. That column *is* the linear method. So the finding is that TabPFN needs
a linear model beside it to draw level with a linear model — which is not a case for TabPFN.

## 5. Statement A or Statement B

The ticket asks which of two sentences is true. On this evidence:

| Candidate | Verdict |
|---|---|
| **B — "TabPFN needs these features"** | Partly true and self-defeating: the feature is the linear method's output. A feature engineering change that is not a linear model has not been shown to help. |
| **A — "the linear method is the right method here"** | Supported. TabPFN's best result on this dataset is level with the linear method, and only when given a linear model inside its inputs. |

**The one thing that would make B a genuine finding** is a feature TabPFN can use that is *not* a
linear model's output — an explicit interaction, or a domain transform — that closes the gap. The
`glm_top5` result suggests the answer is not "fewer columns". Nothing in this diagnostic tests an
authored interaction term, and that is a real gap in the evidence, stated rather than hidden.

## 6. What would refute this, and whether it was tested

The explanation is falsifiable in three ways, and each has been tested or is named as untested:

| Refuter | Tested? | Result |
|---|---|---|
| TabPFN closes the gap when given the linear form, and overtakes | **Tested** | It closes it (88%) and does not overtake. Interval covers zero; it does not clear it. |
| TabPFN closes the gap given fewer, cleaner features | **Tested** | No. `glm_top5` left TabPFN slightly worse than the benchmark regime. |
| TabPFN closes the gap under better preprocessing | **Not tested** | D4 (#305) has not run. See §7. |
| An authored interaction term closes the gap | **Not tested** | Out of this tool's scope; the refuter is recorded so a later run can take it. |

## 7. What this does not establish

- **Not a preprocessing finding.** D4 (#305) has not run: the ticket is blocked on D10's
  measured-estimate rule, and the ~$3.1 balance is reserved by D19. No preprocessing ablation exists
  to cite, and none is claimed. A reader who wants "preprocessing is the cause" does not get it here.
- **Not a v3 finding.** Everything measured here is `v2_5` on 2,000 rows. The §14.10 baselines it
  reproduces are `v3_default` at full data. The two are not interchangeable, and the reproduction is
  the only place in this document where a v3 number appears.
- **Not an equality claim.** The engineered residual is not separable from zero at five seeds; it is
  not shown to be zero. The interval is `[−0.0051, +0.0113]`, a half-width of **0.0082** against
  this programme's readiness floor of 0.006 and its δ of 0.002. At the measured between-seed SD of
  0.0066, bounding that residual below δ = 0.002 needs **≈86 seeds** — the bar D18 met with 238 — so
  this design is roughly seventeen times short of it.
- **Not a generalisation.** One dataset, the one ticket #306 names. What the linear-form mechanism
  does on `coil2000`, `spanish_motor_lapse` or `uslapseagent` is not measured here.

## 9. What would upgrade this, recorded for later

Three changes, in order of what they would change:

1. **Break the circularity.** Supply an *authored* additive transform — the standardised premium sum,
   or a monotone encoding — instead of the linear method's fitted log-odds. If an authored feature
   also closes the gap, the finding no longer depends on the competitor's output.
2. **Power it.** ≈86 seeds at 2,000 rows bounds the residual below δ = 0.002 for $0 and about an hour
   of local fitting. That makes the claim conclusive **at `v2_5`** and leaves the era gap open.
3. **Close the era gap**, which only a paid `v3_default` run can do. Under D10 that needs a measured
   estimate first, and the balance is spoken for by D19.

None of the three is authorised here. This document records the diagnosis and its strength; the
decision to buy the third is a later spending decision, not a conclusion of this ticket.

## 8. What it means for the diagnostics

The repo has attributed this loss to "additive structure the model doesn't capture" in three places
since August, and never measured it. That attribution now has a measurement, and it holds — with one
correction: it is **not** that a few features carry the signal. The signal is diffuse, and the method
that handles a diffuse additive signal on a weak target is the linear one.

For the programme, this is a $0 answer to the anchor's question of why a dataset is hard: the failure
is a **prior/functional-form mismatch**, not missing information. That is the shape #307 needs, and it
argues against a feature-engineering workstream on this dataset.

## Reproduction

```
python scripts/diagnostics/d5_eudirectlapse.py --run-id <id>          # everything, ~15 min, $0
python scripts/diagnostics/d5_eudirectlapse.py --run-id <id> --skip-regimes   # baselines + ladder, ~2 min
```

The record is written under `outputs/diagnostics/d5_eudirectlapse/<id>/` and is **git-ignored**, as
D1–D3's are: it is runtime evidence, reproducible from the command and seed rather than from a diff.
The numbers above are the record's; the script prints them on every run and exits non-zero if the
§14.10 reproduction stops matching.
