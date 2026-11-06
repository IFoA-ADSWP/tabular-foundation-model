# D5 — why the linear method beats TabPFN on `eudirectlapse`

> **Status:** **provisional** — diagnostic, 2026-11-06. Recorded for later consideration, **not
> conclusive**: the mechanism claim is underpowered at five seeds and its decisive feature is the
> competitor's own output. It is measured on **both** model lines — `v2_5` and `v3_default` — and
> the mechanism reproduces on each (§4). §7 states what would still be required; §9 records it.
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
3. **Handing TabPFN the linear form closes 88% of the gap at `v2_5` and 82% at `v3_default`.** With the linear method's fitted
   log-odds supplied as a feature, the residual difference is `+0.0031` with an interval that covers
   zero at five seeds — down from `+0.0256`.

So the evidence points to a **functional form** deficit, provisionally — the strength of that claim is
bounded by five seeds and a decisive feature that is the competitor's own output (§7); the model
line is no longer one of them, because the mechanism reproduces on both. What makes the ticket's own distinction answerable:

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

**The version boundary, measured rather than argued around.** The rows above are `v3_default`. This
diagnostic's own regimes were first run at `v2_5` — the repo pin is `tabpfn>=6,<7`, and 6.4.1
enumerates only `V2` and `V2_5` — and then **re-run at `v3_default`** by installing `tabpfn` 8.5.0 in
an isolated environment and loading the gated `tabpfn-v3-classifier-v3_default.ckpt`
(`sha256 d0d865d5…`). The label in each record is derived from the checkpoint that actually loaded,
not from the package version and not from what the caller asked for, which is ADR 0003's rule.

Both runs are reported side by side in §4. Measuring on the line the programme uses is what makes the
mechanism a claim about `eudirectlapse` rather than a claim about a superseded model.

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
Both methods are refitted in every cell. The linear model is unaffected by the TabPFN line, so its
column is identical in both runs — only the right-hand column moves.

| Regime | Linear | TabPFN `v2_5` | TabPFN `v3_default` | Δ `v2_5` | Δ `v3_default` | Seeds linear ahead (`v3`) | Features |
|---|---|---|---|---|---|---|---|
| `benchmark` | 0.5855 | 0.5598 | 0.5650 | +0.0256 ± 0.0077 | **+0.0205 ± 0.0069** | 4/5 | all 18, category codes |
| `glm_top5` | 0.5701 | 0.5564 | 0.5611 | +0.0137 ± 0.0140 | +0.0090 ± 0.0176 | 2/5 | the 5 the linear method leans on |
| `engineered` | 0.5853 | 0.5823 | 0.5816 | +0.0031 ± 0.0029 | **+0.0037 ± 0.0026** | 3/5 | 18 + linear log-odds; premium block → PC1 |

**`v3_default` narrows the benchmark gap by 20%** — `+0.0256` → `+0.0205` — because TabPFN improves in
the first two regimes while the linear model cannot move. The mechanism survives the version change,
which is the point of running it: the engineered residual is `+0.0037` at v3 against `+0.0031` at v2.5,
and it still closes **82%** of the benchmark gap (88% at v2.5) with an interval that covers zero,
`[−0.0036, +0.0111]`.

**`glm_top5` is inconclusive, and the v2.5 reading of it does not survive.** At v3 the linear model is
ahead on only **2 of 5 seeds**, with a standard error of 0.0176 that swamps the point estimate. At v2.5
I read this regime as "fewer features is not the lever". At v3 the honest reading is weaker: **dropping
to five features brings TabPFN near level, and this design cannot say whether that is signal or noise.**
The claim is downgraded rather than carried forward, because the run that could have supported it is
the one that disagrees with it.

**`engineered` is the load-bearing result, and it holds on both lines.** Per-seed deltas at v3, in seed
order: `+0.0009, +0.0113, +0.0088, −0.0013, −0.0011`. Mean `+0.0037`, 95% t interval
`[−0.0036, +0.0111]`. Two seeds reverse. So:

- **the gap is closed to within this design's resolution**, which is what five seeds and a
  between-seed SD of 0.0058 can resolve at this row cap; and
- **equality is not proven.** A residual of +0.004 would be consistent with this interval too. The
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
| TabPFN closes the gap when given the linear form, and overtakes | **Tested** | It closes it — 88% at `v2_5`, 82% at `v3_default` — and does not overtake on either line. Interval covers zero; it does not clear it. |
| TabPFN closes the gap given fewer, cleaner features | **Tested** | No. `glm_top5` left TabPFN slightly worse than the benchmark regime. |
| TabPFN closes the gap under better preprocessing | **Not tested** | D4 (#305) has not run. See §7. |
| An authored interaction term closes the gap | **Not tested** | Out of this tool's scope; the refuter is recorded so a later run can take it. |

## 7. What this does not establish

- **Not a preprocessing finding.** D4 (#305) has not run: the ticket is blocked on D10's
  measured-estimate rule, and the ~$3.1 balance is reserved by D19. No preprocessing ablation exists
  to cite, and none is claimed. A reader who wants "preprocessing is the cause" does not get it here.
- **Not a full-data finding.** The regimes run on a 2,000-row subsample, where the gap is larger than
  at full data (−0.0205 at v3 versus −0.0159 in §14.10). The linear model's column is unaffected by the
  TabPFN line, but the *size* of any gap here is a subsample artefact and must not be quoted as §14.10's.
- **Not an equality claim.** The engineered residual is not separable from zero at five seeds; it is
  not shown to be zero. At `v3_default` the interval is `[−0.0036, +0.0111]`, a half-width of
  **0.0073** against this programme's readiness floor of 0.006 and its δ of 0.002. At the measured
  between-seed SD of 0.0058, bounding that residual below δ = 0.002 needs **≈66 seeds** — the bar D18
  met with 238 — so this design is roughly thirteen times short of it.
- **Not a generalisation.** One dataset, the one ticket #306 names. What the linear-form mechanism
  does on `coil2000`, `spanish_motor_lapse` or `uslapseagent` is not measured here.

## 9. What would upgrade this, recorded for later

Two changes remain. The third — the model line — was closed by running at `v3_default`, so it is
recorded under §1 rather than here:

1. **Break the circularity.** Supply an *authored* additive transform — the standardised premium sum,
   or a monotone encoding — instead of the linear method's fitted log-odds. If an authored feature
   also closes the gap, the finding no longer depends on the competitor's output.
2. **Power it.** ≈66 seeds at 2,000 rows bounds the residual below δ = 0.002, for $0 and roughly
   50 minutes of local fitting at 46 s a fit. That is now the only thing between this diagnosis and
   a conclusive `v3_default` result, because the version gap was closed by installing the checkpoint
   rather than by paying for a launch.

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
# On the programme's line: tabpfn 8.5.0 + the gated v3 checkpoint (212 MB).
TABPFN_MODEL_PATH=~/.cache/tabpfn/tabpfn-v3-classifier-v3_default.ckpt \
  python scripts/diagnostics/d5_eudirectlapse.py --run-id <id>          # ~12 min at 46 s a fit, $0
python scripts/diagnostics/d5_eudirectlapse.py --run-id <id> --skip-regimes   # baselines + ladder, ~2 min
```

`--model-path` (or `TABPFN_MODEL_PATH`) selects the checkpoint, and the record's `model_version` is
derived from **the checkpoint that loaded**, with its sha256 — not from the package version and not
from what was asked for. With no path, `tabpfn` 6.4.1 resolves `auto` to v2.5 and says so.

The record is written under `outputs/diagnostics/d5_eudirectlapse/<id>/` and is **git-ignored**, as
D1–D3's are: it is runtime evidence, reproducible from the command and seed rather than from a diff.
The numbers above are the record's; the script prints them on every run and exits non-zero if the
§14.10 reproduction stops matching.
