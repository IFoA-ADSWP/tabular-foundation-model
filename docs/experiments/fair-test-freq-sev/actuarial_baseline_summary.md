# The actuarial baseline — the finding in plain terms

> **Status:** current — plain-language summary of the result, 2026-11-14. It adds no number that
> `actuarial_baseline_result.md` does not carry; that document is the evidence and the authority.
> **Audience:** actuary, pricing lead, decision-maker. No statistics required.

## The question

The programme had only ever compared TabPFN with TabPFN — raw against fine-tuned. That answers
"does fine-tuning help?" It does not answer the question a pricing team asks: **would we deploy
this instead of the GLM or the gradient-boosted model we would build ourselves?**

## What was compared

The same four targets, the same five folds, the same test policies, the same scoring rule the
frequency/severity fair test registered. Nothing about the test was chosen after seeing results.

Five models went into each fold:

| Model | What it is |
|---|---|
| Intercept-only | Predicts one constant rate or mean. A floor, not a competitor. |
| `A_raw` | TabPFN, untouched |
| `B_ft30` | TabPFN, fine-tuned — **the contender** |
| `E_glm` | A GLM built the way the dataset's reference case study builds one |
| `F_catboost` | CatBoost with its shipped defaults, raw categoricals |

The score is the ratio `(baseline error − TabPFN error) / baseline error`. **Negative means
TabPFN's error is larger — TabPFN is worse.** The verdict is taken against whichever baseline is
stronger on that target, and each target has a pre-registered floor: a gain smaller than 2% (4% for
Spanish frequency) does not count.

## The catch: two data volumes

The two sides did not train on the same number of rows, by design:

| Target | TabPFN trained on | Baselines, "all the data" | Baselines, "matched" |
|---|---:|---:|---:|
| French frequency | 10,000 | **542,410** | 10,000 |
| Spanish frequency | 10,000 | **42,801** | 10,000 |
| French severity | 10,000 | **21,131–21,177** | 10,000 |
| Spanish severity | 10,000 | **4,760** (all it has) | 4,760 |

TabPFN's 10,000 rows are the fair test's registered budget; it was never trained on 542,000 rows.
So the experiment answers two different questions, and both are reported:

- **"All the data for the baselines"** — what a team would do with the data it has.
- **"Matched rows"** — what the models do with the same amount of data.

## The result

**When the baselines may use all the data, CatBoost wins on every target.**

| Target | TabPFN vs the better baseline | Reading |
|---|---:|---|
| French frequency | **−7.9%** | CatBoost's error is 7.9% lower |
| Spanish frequency | **−13.7%** | CatBoost's error is 13.7% lower |
| French severity | **−0.8%** | CatBoost is 0.8% better — small but certain |
| Spanish severity | **−10.1%** | CatBoost's error is 10.1% lower |

**When both sides get the same 10,000 rows, the picture changes on one target only.**

| Target | TabPFN vs the better baseline | Reading |
|---|---:|---|
| French frequency | **−1.1%** | **Too close to call** — the difference is within noise |
| Spanish frequency | **−7.2%** | CatBoost still clearly better |
| French severity | **−0.6%** | Still slightly worse |
| Spanish severity | **−10.1%** | Same fit as above — the data does not allow 10,000 rows |

## The three things worth remembering

**1. On French frequency, most of the "loss" is the data volume, not the model.** Give CatBoost
542,000 policies and TabPFN 10,000, and CatBoost wins by 7.9%. Give them both 10,000 and the
experiment cannot separate them. The registered verdict is still based on the full-data comparison
— that is what was pre-registered — but the fair sentence is "we cannot show TabPFN is better",
not "TabPFN is worse".

**2. Elsewhere the loss is real at equal data.** Spanish frequency, French severity and Spanish
severity stay behind CatBoost even when the data is matched. On Spanish severity the two arms are
the same fit, so there is no budget story at all.

**3. On French severity, fine-tuning is what loses.** The fine-tuned contender's error is
**worse than predicting a single constant** (1.1304 vs 1.1299). Raw TabPFN is the best of the five
models on that target (1.1201), slightly ahead of both baselines. The foundation model is not the
problem there; the fine-tuned configuration is. This agrees with the earlier fair test, which
already found fine-tuning made severity slightly worse (−0.92%).

And fine-tuning does still help TabPFN where the fair test said it did: on French frequency at
equal rows, raw TabPFN trails CatBoost by 12.1% and fine-tuned TabPFN by only 1.1%.

## What this does not say

- **Not** that TabPFN would lose with a large context. Nobody trained it on more than 10,000 rows
  here, so "TabPFN with enough data beats CatBoost" is untested, neither supported nor refuted.
- **Not** that CatBoost is the best model in general. One configuration, shipped defaults, these
  folds.
- **Not** that a GLM cannot compete: the GLM used is a main-effects model (the case study's GLM1),
  and CatBoost beat it everywhere, so the loss is to a gradient-boosted model, not to a GLM.
- **No task-level verdict.** Four per-target verdicts, as registered; Spanish frequency is also
  underpowered, so its size is soft.
- **Nothing about calibration, lift or pure premium.** Two metrics, one per target.

## What it would take to change the answer

One registered comparison at a large **equal** budget — say 40,000 rows for both TabPFN and
CatBoost, with CatBoost also shown 100,000+ to see whether the gap widens. Until that exists, the
honest position is: **at the volumes we actually tested, the actuarial baselines are at least as
good as fine-tuned TabPFN, and better where the baselines get more data or the target is severity.**

## Where the detail is

- `actuarial_baseline_result.md` — both tables, intervals, per-fold numbers, limits, reproduce
  commands, model versions.
- `docs/analyses/data/actuarial_baseline_timings.txt` — wall and CPU time.
- `ACTUARIAL_BASELINE_PREREGISTRATION_2026-11.md` — the design fixed before the run.
- The twelve captures under `results/`, cited in the result document.
