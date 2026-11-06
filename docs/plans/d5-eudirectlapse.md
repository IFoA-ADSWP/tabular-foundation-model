# Plan — D5: why the linear model beats TabPFN on `eudirectlapse` (#306)

**Status:** Current — implementing 2026-11-06.
**Origin:** ticket #306 under campaign spec #300.
**Design:** `docs/current/FINETUNING_DIAGNOSTICS_DESIGN.md` §D5 · **Record shape:** ADR 0003.

## What the ticket asks for, and what it assumes

D5 consumes D1's profile, D2's feature comparison and D4's preprocessing result, and produces one
explanation with the evidence behind it. Two conclusions are allowed and they are not the same
sentence: **"GLM is the right model here"** versus **"TabPFN needs these features"**.

**D4 does not exist.** #305 is open, unstarted, and blocked by D10 (a paid diagnostic needs a
measured estimate first); its own comment records that the money rule landed and the ticket has been
waiting on it since 2026-10-30. So this plan cannot consume D4, and the record must say the
preprocessing regime was **not tested** rather than assume it. Writing "preprocessing explains it"
without the ablation would be the exact failure D10 exists to prevent.

That leaves a choice: is a D5 with no D4 worth anything? It is, if it stops resting on D4. The
feature-coverage hypothesis can be tested directly on this dataset without touching preprocessing
at all, which is what this plan does.

## The claim under test

`eudirectlapse`, 23,060 rows, 12.8% lapse rate, target `lapse`, AUC:

| Method | AUC (§14.10, 5 folds) |
|---|---|
| LR | **0.6260 ± 0.0037** |
| GBM | 0.6138 ± 0.0043 |
| TabPFN | 0.6101 ± 0.0049 |

The repo already attributes this to "additive structure the model doesn't capture"
(`docs/MODEL_VERSIONS.md`, `docs/archive/PRE_FINETUNING_INVESTIGATIONS.md`). That attribution has
never been given evidence of its own; it is asserted in three places and measured in none. D5 is
where it either gets a measurement or gets downgraded to a guess.

## Two rival explanations

- **E1 — feature coverage.** TabPFN lacks something the GLM has: a column, a transformation, or an
  interaction. D2 supports this prima facie with a top-10 Jaccard of 0.54 between TabPFN and GLM.
  If E1 holds, the lever is feature engineering and fine-tuning is irrelevant.
- **E2 — additive structure.** The target is close to additive in a few features, and a
  low-variance linear fit is the better inductive bias on a weak signal. Nothing is "missing"; the
  extra flexibility costs more than it buys. If E2 holds, GLM is simply the right model here.

They predict different things about the same experiment, which is why the experiment can decide
between them.

## Design — three regimes, matched everything else

2,000-row stratified subsample (1,500 train / 500 test), the same cap D2 used, five folds, three
seeds. Both families see identical folds and identical rows; only the feature set changes.

| Regime | Features |
|---|---|
| `benchmark` | all 18 columns, the benchmark's own encoding (category codes, `NaN`→0) |
| `glm_top5` | only the five features the logistic model ranks top |
| `engineered` | `benchmark` plus the GLM's fitted log-odds as one column, and the four premium columns replaced by their first principal component |

`engineered` is the falsifier. It hands TabPFN what E1 says it lacks — the additive signal, made
explicit and noise-free — so **if TabPFN still trails the linear method when given its functional form
as a column, E1 is refuted on this dataset** and E2 is what remains.

**The measurement did not split the way that sentence does, and the sentence is left here rather than
rewritten to fit.** The gap fell from `+0.0256` to `+0.0031` — 88% closed — and the residual covers
zero at five seeds. So E1 is *not* refuted: handing TabPFN the linear form genuinely closes the gap.
What it does not do is make TabPFN **better** than the linear method, and the reason is circular — the
feature that closes the gap is the linear method's own output. The plan's binary "refuted / remains"
framing could not express that; the verdict rule in the tool is now three-way and reports the fraction
closed, the interval and the reason together.

The linear predictor is fitted on the training rows of each fold only. Computing it once on the whole
table would leak the test rows into a feature.

## The additivity ladder — free, and at full data

LR at full data is seconds, so the ladder runs where the claim lives rather than on a subsample: 5
folds at 23,060 rows, adding features in order of univariate signal, recording AUC at k = 1, 2, 3, 5,
10 and all 18.

**The plan predicted that three features would reproduce ~0.62, and the measurement refused it.**
The ladder rises all the way: **0.5659 (k=1), 0.5821 (k=2), 0.5857 (k=3), 0.5903 (k=5), 0.6117
(k=10), 0.6159 (k=18)**. That is not three magic columns; it is a weak, diffuse, roughly additive
signal that keeps paying for more features. The prediction was wrong and is kept here as the reason
the reading changed: "additive" survives, "a few features" does not. The consequence for the
explanation is that **no single missing feature can be the mechanism**, which is what makes E1
unlikely before any model is fitted.

The top rung, 0.6159, sits 0.0101 below §14.10's Linear (0.6260) — a different estimator
(standardised, L2) on this tool's own folds, not a reproduction of that row. The reproduction is
carried by the committed evidence instead, where it passes to within 0.00005.

This is the part that does not depend on a model version: it is a property of the data, so it holds
whatever TabPFN does.

## The version trap, stated up front

The committed claim is **v3_default**, measured through the hosted client on a GPU box. The local
package here is **6.4.1, which enumerates `V2` and `V2_5` only** — there is no V3 checkpoint and no
fine-tuning path, so a local run cannot reproduce or adjudicate a v3 number.

The falsifier is therefore designed as a **within-experiment paired comparison**: same version, same
folds, same rows, one feature set changed. That is internally valid at v2.5, and the record states
the version it ran on. What it will **not** do is quote a v2.5 delta beside a v3 delta as if the two
were one table.

## Wrongness check

The reproduction of §14.10 from `scripts/eval/lapse_benchmark_v1/results_per_split.csv`: the tool
re-derives 0.62596 / 0.61375 / 0.61007 from the committed per-fold rows and fails if it does not get
them. A gap explanation built on a misread baseline explains the wrong thing.

The second check is the one this ticket's own subject invites: D2's "different features" reading is
measured on a premium block whose columns are **0.99 correlated** (`prem_final` vs `prem_pure`). The
tool reports that correlation, so a disagreement inside one collinear block is not read as a
disagreement about information.

## Not in scope

- Fine-tuning `eudirectlapse` (ticket's own exclusion; D18 already answered it).
- Any preprocessing regime comparison — that is #305, and this record says so.
- Generalising to other datasets.

## Verification

- `./scripts/check.sh` green, all eight checks.
- The reproduction step fails loudly if the committed baselines stop matching.
- Tests: the ladder is monotone-or-flat, the repaired-vs-raw split has no leakage, the record
  writes once and refuses a second write to the same run id.
- `python scripts/diagnostics/d5_eudirectlapse.py --run-id <id>` writes one record under
  `outputs/diagnostics/d5_eudirectlapse/<id>/` (git-ignored, as D1–D3's are).

## Amendment — measured at `v3_default`, not only `v2_5` (2026-11-06)

**What the plan got wrong.** It treated "the local package has no V3" as a fixed constraint and made
the regime comparison a `v2_5`-only experiment. That was the repo pin (`tabpfn>=6,<7`) described as a
capability limit, and the pilot had already deviated from the pin to run v3 on rented boxes. The
constraint was one install deep.

**What closed it.** `tabpfn` 8.5.0 in an isolated environment (`--system-site-packages`, so the repo's
pin is untouched) enumerates `V2, V2_5, V2_6, V3`, and the gated checkpoint is **212 MB**, not the
multi-gigabyte download the 6 GiB of free disk made risky to assume. `TABPFN_MODEL_PATH` selects it; a
fit at 1,500 rows takes 46 s on MPS against 21 s at v2.5.

**The consequence for the plan's own claims.** The regimes were re-run on the programme's line. The
mechanism reproduces: the engineered residual is `+0.0037` at v3 against `+0.0031` at v2.5, closing
82% and 88% of the benchmark gap respectively. One earlier reading does **not** survive — `glm_top5`
was reported as "fewer features is not the lever" on 3/5 seeds at v2.5, and at v3 it is 2/5 seeds with
a standard error that swamps the estimate. It is now reported as inconclusive, which is the honest
result of the run that disagrees with it.

**A rule this produced.** The tool no longer hardcodes a model label. `model_version` is derived from
the checkpoint that actually loaded, with its sha256, which is ADR 0003's rule and was the one place
the diagnostic violated it.
