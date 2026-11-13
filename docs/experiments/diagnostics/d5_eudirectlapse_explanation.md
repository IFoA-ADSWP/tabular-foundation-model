# D5 — why the linear method beats TabPFN on `eudirectlapse`

> **Status:** **current — negative result**, 2026-11-06. **Question:** why does the linear method beat
> TabPFN on `eudirectlapse`, and is the deficit a missing feature or a wrong functional form?
> **Design:** D5 / ticket #306. **Evidence:** `scripts/eval/lapse_benchmark_v1/results_per_split.csv`
> (reproduction), `scripts/diagnostics/d5_eudirectlapse.py` (regimes, ladder),
> `scripts/diagnostics/d1_profiling.py` (profile).
> **Verdict:** **at the 2,000-row working set the gap does not establishedly exist, so this experiment
> cannot explain it.** The five-seed version of the same run reported a gap of +0.0205 and a clean
> mechanism; sixty-six seeds report +0.0054 with an interval covering zero. The mechanism story was
> measured on a gap that is not there at this resolution.

## Answer

The full-data claim is real: §14.10 puts the linear method 0.0159 AUC ahead of TabPFN on `eudirectlapse`
at 23,060 rows. This diagnostic set out to explain it at a 2,000-row working set, which is the cap D2
used and the cap that keeps the work free.

**It could not, because the gap does not reproduce at that cap.** Sixty-six seeds, `v3_default`:

| Regime | Linear | TabPFN | Δ (linear − TabPFN) | 95% interval | TabPFN ahead |
|---|---|---|---|---|---|
| `benchmark` | 0.5949 | 0.5896 | **+0.0054 ± 0.0033** | **[−0.0012, +0.0120]** | 29/66 |
| `engineered` | 0.5947 | 0.5962 | **−0.0015 ± 0.0011** | **[−0.0038, +0.0007]** | 38/66 |

Both intervals cover zero. So the honest readings are:

1. **At 2,000 rows there is no established gap to explain.** The linear method's advantage at this row
   cap is +0.0054 with an interval spanning zero.
2. **Supplying the linear form moves the point estimate across zero** — `−0.0015`, TabPFN ahead on
   38 of 66 seeds — and the interval covers zero there too. That is parity, not a win, and it is the
   opposite sign to the benchmark regime.
3. **The five-seed result was a small-sample artefact.** It reported `+0.0205` for the benchmark gap
   and `+0.0037` for the engineered residual, with a tidy "82% closed" story. Both numbers were
   inflated roughly four-fold by seed variance, and the story they supported does not survive.

**Why this matters more than a null:** the handoff's rule for this phase is that "interesting" is not a
finding, and that if the diagnostics find nothing of the required shape the correct output is to say
so. This is that output. The mechanism that looked established at five seeds is not established at
sixty-six, and the difference between those two sentences is the entire justification for running the
extra sixty-one.

## 1. The gap, and which model version it belongs to

| Method | AUC | Source |
|---|---|---|
| Linear (`lr`) | **0.6260 ± 0.0037** | §14.10, 5 folds, `v3_default` |
| GBM | 0.6138 ± 0.0043 | §14.10 |
| TabPFN | 0.6101 ± 0.0049 | §14.10 |

**Wrongness check, passed.** Re-deriving those three from the committed per-fold rows gives 0.62596,
0.61375 and 0.61007 — a worst deviation of **0.00005**. The gap this document is about is the gap the
evidence records.

**The version boundary, measured rather than argued around.** The regimes were first run at `v2_5` —
the repo pin is `tabpfn>=6,<7`, and 6.4.1 enumerates only `V2` and `V2_5` — and then re-run at
**`v3_default`** by installing `tabpfn` 8.5.0 in an isolated environment and loading the gated
`tabpfn-v3-classifier-v3_default.ckpt` (`sha256 d0d865d5…`, 212 MB). The label in each record is
derived from the checkpoint that actually loaded, per ADR 0003.

That correction mattered: **`v2_5` overstated the benchmark gap**, and the `v3_default` run is the one
this document reports. A 1,500-row fit costs 46 s on MPS against 21 s at v2.5, so the line the
programme uses was affordable all along.

## 2. D2's "different features" is partly a collinearity artefact

D2 (#303) read `eudirectlapse` as **mixed**: top-ten Jaccard 0.54 between TabPFN and the GLM, with the
GLM's extra features `prem_final`, `prem_freqperyear`, `polholder_job` and TabPFN's `prem_pure`,
`policy_caruse`, `polholder_BMCevol`.

The premium block defeats that reading. Measured correlation, all 23,060 rows:

| | `prem_final` | `prem_last` | `prem_market` | `prem_pure` |
|---|---|---|---|---|
| `prem_final` | 1.000 | 0.951 | 0.895 | **0.991** |
| `prem_last` | 0.951 | 1.000 | 0.839 | 0.926 |
| `prem_market` | 0.895 | 0.839 | 1.000 | 0.899 |
| `prem_pure` | **0.991** | 0.926 | 0.899 | 1.000 |

`prem_final` and `prem_pure` are the same column to three decimal places of correlation. A permutation
importance that ranks one first and the other second has split credit inside a collinear block; it has
not found two different features.

**D1's profile agrees.** `scripts/diagnostics/d1_profiling.py` on the same bytes
(`sha256 c05777d1…`) reports `max_abs_feature_correlation` **0.990542** — the same figure this tool
measured independently — and a **max VIF of 92.8**. The profile also fixes the shape: 23,060 rows, 18
features (9 numeric, 9 categorical), **no missing values**, 63 columns after one-hot, feature:row ratio
0.0027, and target entropy **0.552 bits** against a 1-bit ceiling.

## 3. The signal is additive but diffuse

Full data, 5 folds, standardised logistic regression, features added in order of marginal signal:

| k | 1 | 2 | 3 | 5 | 10 | 18 |
|---|---|---|---|---|---|---|
| AUC | 0.5659 | 0.5821 | 0.5857 | 0.5903 | 0.6117 | **0.6159** |

No knee. That is what a weak, spread-out additive signal looks like: each feature contributes a little
and none carries the problem. It is the strongest evidence **before any model is fitted** that no small
group of missing features can be the mechanism — which is why the "feature coverage" hypothesis was
always the weaker of the two.

The top rung, 0.6159, sits 0.0101 below §14.10's Linear (0.6260) because it is a different estimator
(standardised, L2, this tool's folds) rather than a rebuild of that row. The reproduction of §14.10 is
carried by §1.

## 4. Three regimes, two sample sizes, and what the larger one did

2,000-row subsample (1,500 train / 500 test), identical rows across methods and regimes, both methods
refitted in every cell. The linear model's column is unaffected by the TabPFN version, so only the
right-hand side moves between runs.

| Regime | Linear | TabPFN `v3`, 5 seeds | TabPFN `v3`, **66 seeds** | Δ 5 seeds | Δ **66 seeds** |
|---|---|---|---|---|---|
| `benchmark` | 0.5949 | 0.5650 | 0.5896 | +0.0205 ± 0.0069 | **+0.0054 ± 0.0033** |
| `engineered` | 0.5947 | 0.5816 | 0.5962 | +0.0037 ± 0.0026 | **−0.0015 ± 0.0011** |
| `glm_top5` | 0.5701 | 0.5611 | — | +0.0090 ± 0.0176 | not run |

**The five-seed estimate was wrong by four-fold.** The benchmark gap is `+0.0054` at sixty-six seeds,
not `+0.0205`: the first five seeds happened to include several large positive cases, and a five-seed
standard error of 0.0069 was never tight enough to say so. This is the same lesson D18 recorded and
this diagnostic ignored until it was forced to.

**The engineered regime reverses sign**, from `+0.0037` to `−0.0015`, and TabPFN leads on 38 of 66
seeds. With an interval of `[−0.0038, +0.0007]` that is **parity, not a victory** — and the reversal is
the interesting part only because of what it does to the earlier story.

**`glm_top5` is not reported at sixty-six seeds.** At five seeds its standard error was 0.0176, wider
than any effect it could have measured; at v3 it put the linear model ahead on 2 of 5 seeds. Spending
90 minutes to confirm that a five-feature regime is underdetermined was not the best use of the time,
and the regime is recorded as inconclusive rather than quietly dropped.

## 4b. The non-circular falsifier, and why it could not bite (#460)

The `engineered` regime closed the gap by handing TabPFN the linear model's fitted log-odds — the
competitor's own output, which nobody could ship without already having that model. A fourth regime
supplies an **authored** summary instead, pre-registered before the run: the four premium columns
replaced by `premium_sum_z`, the sum of their z-scored values, scaler fitted on training rows only,
no labels and no fitted model contributing.

Sixty-six seeds, `v3_default`, same rows and folds:

| Regime | Linear | TabPFN | Δ (linear − TabPFN) | 95% interval | TabPFN ahead |
|---|---|---|---|---|---|
| `benchmark` | 0.5938 | 0.5896 | +0.0054 ± 0.0033 | [−0.0012, +0.0120] | 29/66 |
| `authored` | 0.5938 | 0.5915 | **+0.0024 ± 0.0037** | **[−0.0051, +0.0098]** | 33/66 |

**Both intervals cover zero**, and the pre-registered table said what that means before the numbers
existed: *neither closes it — there is no gap at this row cap to close.*

The authored summary moves the point estimate further towards parity (+0.0024 against +0.0054), as an
additive feature that captures the premium level should. But it cannot be reported as closing
anything, because there is no established gap for it to close. **The circularity question is
therefore unresolved at 2,000 rows** rather than answered: the circular regime's apparent success and
the authored regime's near-parity are both measured against a gap that is itself indistinguishable
from zero.

This is the honest limit of the design, and it was written down before the run precisely so that a
favourable-looking point estimate could not be promoted into a finding afterwards.

## 5. What this says about the two explanations

The ticket asked which is true: *"the linear method is the right method here"* or *"TabPFN needs these
features"*.

**Neither is supportable at this row cap**, because both presuppose a gap — and the authored
regime (§4b) was added specifically to test E1 without the circularity, and could not, for the same
reason:

- **E1, feature coverage** — the engineered regime supplies the linear form explicitly and the point
  estimate crosses zero. That is the direction E1 predicts, and the interval does not exclude zero, so
  it is consistent with E1 without establishing it.
- **E2, additive structure makes the linear method right** — the benchmark gap itself covers zero at
  this cap, so there is no established advantage for additive structure to explain.

**The honest statement is that this design cannot reach the full-data question.** §14.10's gap is
measured at 23,060 rows; the working set is 2,000. A diagnostic at one eighth the data can fail to
reproduce a full-data gap for reasons that have nothing to do with the models, and that is the most
likely reading here — TabPFN is known to be weaker at small row counts, but at 2,000 rows on this
table the two methods are simply indistinguishable.

## 6. What would refute this, and whether it was tested

| Refuter | Tested? | Result |
|---|---|---|
| The benchmark gap survives at 66 seeds | **Tested** | It does not: `+0.0054`, interval covers zero. |
| TabPFN overtakes when given the linear form | **Tested** | Point estimate does (`−0.0015`, 38/66); interval covers zero. |
| The gap reproduces at full data with the same regimes | **Not tested** | Requires 23,060-row fits. Local v3 at that size is hours per fit, and a hosted run is spend. |
| Preprocessing explains it | **Not tested** | D4 (#305) has not run: blocked on D10's measured-estimate rule. |
| An authored **interaction** closes it | **Not tested** | Out of this tool's scope. The authored **additive** transform was tested (§4b) and could not close the gap — because at this row cap there is no gap. |

## 7. What this does not establish

- **Not a claim that the linear method is or is not better at full data.** §14.10 stands as recorded;
  this document does not overturn it, it fails to reproduce it at a smaller cap.
- **Not a preprocessing finding.** D4 has not run and none is claimed.
- **Not an equality claim at full data.** The subsample intervals cover zero; that is a statement
  about 2,000 rows on `v3_default`.
- **Not a generalisation.** One dataset, the one #306 names.

## 8. What it means for the diagnostics

The most useful thing this diagnostic produced is a **demonstration that five seeds cannot measure an
effect of this size**. The same run, same data, same code, moved a "clean 82%-closed mechanism" to a
pair of intervals that straddle zero. Any diagnostic in this programme that reports a delta from a
handful of seeds should be read the way D18 reads its own: with the seed count in the sentence.

For the programme, this is a $0 result that narrows the question rather than answering it. Explaining
the full-data gap needs full-data fits, and that is a different, paid experiment — which D19's balance
does not currently cover.

## 9. What would upgrade this

1. **Run the regimes at full data.** 23,060 rows, five folds, `v3_default`. This is the only version of
   the experiment that can address §14.10's gap, and it is the one this diagnostic's row cap excludes.
2. **Keep the seed count honest.** The 66-seed design is the minimum that made the result readable;
   anything reported from five seeds should carry that in the sentence.
3. **Break the circularity** if the engineered regime is ever to be decisive: an authored additive
   transform rather than the competitor's fitted log-odds.

None of these is authorised here.

## Reproduction

```
# On the programme's line: tabpfn 8.5.0 + the gated v3 checkpoint (212 MB).
TABPFN_MODEL_PATH=~/.cache/tabpfn/tabpfn-v3-classifier-v3_default.ckpt \
  python scripts/diagnostics/d5_eudirectlapse.py --run-id <id> \
  --regime benchmark --regime engineered --seed-range 42-107      # 66 seeds, ~100 min, $0
```

`--model-path` (or `TABPFN_MODEL_PATH`) selects the checkpoint, and the record's `model_version` is
derived from **the checkpoint that loaded**, with its sha256 — not from the package version and not
from what was asked for. `--seed-range A-B` sets the seed count; the default five cannot resolve an
effect of 0.002.

The record is written under `outputs/diagnostics/d5_eudirectlapse/<id>/` and is **git-ignored**, as
D1–D3's are: runtime evidence, reproducible from the command and seed rather than from a diff.
