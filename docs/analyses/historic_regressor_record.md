# The historic regressor record: what survives, and what must be re-measured

> **Status:** active — research, 2026-11-08. **Question:** what can the April-2026 TabPFN
> regressor record actually support, and what must the new design re-measure from scratch?
> **Method:** read-only. Scripts and docs read; splits recomputed from the scripts' own seeds;
> data files checksum-verified against `data/raw/MANIFEST.sha256`. **No model was fitted, no
> compute spent.** **Decision it informs:** how much weight the fine-tuning decision may put on
> the historic regressor evidence. **Recorded on:**
> [#496](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/496).

## Answer

The **protocol** survives in two scripts. Almost none of the **numbers** do, and the headline
numbers that do survive do not mean what the reports say they mean.

1. **Every fine-tuning-era regressor result file is gone.** All four cited
   `outputs/current/tables/*.csv`, both logbooks, the 13 saved models and the trial ledger are
   absent from the repository *and* from the original working directory. None of them was ever
   committed (`git log --all -- <path>` is empty for each). They were working-tree artifacts
   that were later deleted.
2. **The one committed regression table is the classical baseline**, and it reproduces exactly.
   It is the only regressor number in the repository that can be checked.
3. **The "no fine-tuning lift" verdict is mostly an inference-context artifact.** The fine-tuned
   arm evaluated with a 64-row context while the raw arm it is compared against in the report
   used all 300 training rows. The cleanest proof is AUS Auto: the fine-tune executed
   **zero steps**, so the weights are unchanged — yet the "fine-tuned" arm still loses 0.050 R²
   and 0.017 MAE. That delta is the context cut, not fine-tuning.
4. **The ClaimNb "best MAE despite 33× fewer rows" is worse than predicting zero.** On the exact
   2,000-row test subset those runs used, the zero predictor scores MAE 0.0580; raw TabPFN scores
   0.0586 and the fine-tuned arm 0.0582. On the baseline test set the zero predictor scores
   0.0534 and CatBoost 0.0763. Every model in that table is beaten by a constant.
5. **The EU Direct R²≈0.99 is target leakage.** `prem_final`, `prem_last` and `prem_market` stay
   in the feature matrix and correlate 0.991 / 0.977 / 0.864 (Spearman) with `prem_pure`.
6. **The Exposure range claim is wrong.** `STAGE_R1_PHASE1A_REPORT.md` says "continuous, 0.0–1.0
   range". freMTPL2 `Exposure` runs 0.00273–2.01, with 1,224 rows above 1.0.
7. **`SESSION_SUMMARY_APRIL2_REGRESSOR_SCALING.md` converts a 5K→10K data-scaling delta into a
   fine-tuning effect.** Its own companion report separates the two correctly; the summary does
   not, and it also overstates seed stability by quoting the two 10K seeds while ignoring a
   0.061 spread across the three 5K seeds.

What the record can support, without qualification: fine-tuning **executed** on a continuous
target (Exposure) at 5K and 10K rows without non-finite loss, and the resulting changes in R²
were small (≤0.003 in absolute terms at 10K, per the Phase 1a table). Nothing about efficacy
against a matched raw arm — that comparison was never written out.

---

## 1. The protocol as implemented

Two scripts, two different protocols. They are not interchangeable and their numbers are not
comparable.

| | `run_finetuned_tabpfn_regression_benchmark.py` | `run_small_finetune_regressor_trial.py` |
|---|---|---|
| Datasets | freMTPL2freq, eudirectlapse, ausprivauto0405 (`:49-53`) | one `--data-path`, default freMTPL2freq (`:42`) |
| Target | `ClaimNb`, `prem_pure`, `VehValue` | default `ClaimNb`; `--target-transform` ∈ none/log1p/claimfreq_raw/claimfreq_log1p (`:47-52`, `:118-136`) |
| Row selection | full file → `train_test_split(test_size=0.20, seed 42)` → train subsampled to **300**, test to **2000** (`:37-40`, `:232-251`) | `df.sample(rows)` default 1000 → **70/30** split (`:53`, `:271-275`), so 700 train / 300 test at defaults |
| Test cap | 2000 | none |
| Features | `df.drop(columns=[target])` — only the target is dropped (`:226`) | same (`:150`, `:288`) |
| Preprocess | numeric: median impute + standardise; categorical: most-frequent + ordinal (`:56-82`) | `pd.get_dummies` on one shared frame, no scaling (`:287-290`) |
| Estimator | `TabPFNRegressor`, CPU, `n_estimators=4`, `ignore_pretraining_limits=True`, fp32 (`:262-274`) | same, `n_estimators=2` (`:305-317`) |
| Inference context | `SUBSAMPLE_SAMPLES=64` on **both** arms (`:115-122`) | `SUBSAMPLE_SAMPLES=64` on both arms (`:166-172`) |
| Fine-tune | hand-rolled loop: one preprocessed batch, batch size 1, Adam lr 1e-5, **1 step**, 70/30 internal split (`:132-210`) | same loop, argument-driven steps (`:345-391`) |
| Skips | `skipped_preprocess_errors`, `skipped_nonfinite_target`, `skipped_nonfinite_loss` (`:141-143`) | same (`:341-343`) |
| Metrics | MAE, RMSE, R² on the raw target (`:89-94`) | MSE, MAE, R² (`:174-177`) |
| Seeds | 42 only | `--seed`, default 42 |

Three consequences that matter more than any single number:

**The fine-tuned arm's evaluation is a refit, not the fine-tuned model's prediction.**
`evaluate_model` clones the regressor, refits the clone on the training set, and then predicts
with a 64-row subsample (`:115-122`). So the reported "fine-tuned" score is the fine-tuned
*weights* refitted through the ordinary in-context path. That is a legitimate design, but it is
not "the model that was fine-tuned predicted the test set", and the docs describe it as if it
were.

**The report's raw numbers come from a different script with a different context.** The raw arm
in the report (`COMBINED_…ANALYSIS.md` §3) is produced by `run_raw_tabpfn_regression_benchmark.py`,
which fits on 300 rows and predicts with no subsampling (`:150-157`). The fine-tuned numbers
(§5) come from the fine-tuned script at 64-row context. `COMBINED_…ANALYSIS.md` §4 then compares
§5's fine-tuned column against §3's raw column and concludes "no material gain over raw TabPFN".
That comparison crosses a 300→64 context cut. It is the same confound
`HISTORIC_FINETUNING_APPRAISAL.md` §3 documents for the classifier, one level up the stack.

**No exposure offset and no count-aware metric.** `ClaimNb` is modelled as a raw count with
`Exposure` left in the feature matrix, scored by MAE/RMSE/R². There is no Poisson offset and no
deviance. The current canonical registry does the opposite — `experiments.toml:71-76` declares
`freMTPL2freq` with `metric = "poisson_deviance"` and `transform = "log_exposure"` — so the
historic regression protocol is not the project's protocol.

---

## 2. Evidence inventory

| Cited artifact | Status | Evidence |
|---|---|---|
| `data/processed/multi_dataset_regression_benchmark_results.csv` | **Present**, committed | Contains exactly the 9 baseline rows quoted in `COMBINED_…ANALYSIS.md` §2, to full precision |
| `outputs/current/tables/raw_tabpfn_regression_revalidation.csv` | **Absent** | Not in `origin/main`; `git log --all` empty for the path; not on disk in the original workdir either |
| `outputs/current/tables/multi_dataset_regression_benchmark_with_tabpfn_revalidated.csv` | **Absent** | same |
| `outputs/current/tables/tabpfn_regression_finetune_vs_raw.csv` | **Absent** | same |
| `outputs/current/tables/multi_dataset_regression_benchmark_with_tabpfn_finetuned.csv` | **Absent** | same |
| `outputs/current/tables/tabpfn_regression_finetune_vs_raw_run_meta.json` | **Absent** | written by the script (`:394-395`), never appears in git |
| `outputs/current/logs/tabpfn_regression_finetune_vs_raw.md` | **Absent** | only `domain_finetune_logbook.md` is committed |
| `outputs/current/tables/tabpfn_finetune_regressor_trial_results.csv` | **Absent** | See the trap below |
| `outputs/current/logs/tabpfn_finetune_regressor_logbook.md` | **Absent** | cited by `STAGE_A_B…md:29` |
| 13 serialized Exposure models (`outputs/current/models/`) | **Absent** | The directory holds 15 files, all `CARAVAN` classifier fits; no freMTPL2/Exposure model |
| `STAGE_R1_PHASE1A_REPORT.md` | **Outside git** | Exists only at the pre-restructure working directory; never committed |
| `SESSION_SUMMARY_APRIL2_REGRESSOR_SCALING.md` | **Outside git** | same |

**The trap:** `outputs/current/tables/tabpfn_finetune_trial_results.csv` *is* committed, and its
name differs from the missing regressor ledger by one word. It is the **classifier** ledger —
16 rows, all `run_small_finetune_classifier_trial.py`, target `CARAVAN`, ROC AUC / log loss. It
contains no regressor row. Anyone grepping for "tabpfn_finetune" will find it and may mistake it
for the regressor record.

**Why "untracked" is the right frame.** Nothing in `.gitignore` excludes
`outputs/current/tables/*.csv` — the classifier tables live there and are tracked. The regressor
tables were written to an unignored path and simply never added; later cleanup removed them.
Absence here is loss, not a path typo. The same applies to the two session documents: the ticket
cites them under `docs/reports/`, which no longer exists, but they are absent from
`git ls-tree -r origin/main` at *any* path, not merely moved. The report paths in the ticket are
two vintages stale — `docs/reports/` became `docs/archive/` — which is itself part of the record
loss.

**Unrecoverable numbers.** No surviving artifact can confirm or refute:

- the raw TabPFN per-dataset MAE/RMSE/R² in `COMBINED_…ANALYSIS.md` §3;
- the fine-tuned per-dataset metrics in §5, including `last_step_loss` and the skip counts;
- every row of the 5K/10K Exposure matrix (§4 below), including the initial-vs-post R² pair that
  is the only place fine-tuning's own effect is isolated;
- the Stage R2 ablation row (positive-claims-only pool, 167/3,500 rows) in `STAGE_A_B…md:117-119`;
- anything about ClaimNb fine-tuning beyond "it was unstable": the specific "extreme last loss"
  in §5 cannot be quantified.

The survivor is the classical baseline table. That is exactly the arm that never involved
fine-tuning.

---

## 3. Per-target data facts

All checksums verify against `data/raw/MANIFEST.sha256`.

| | freMTPL2 `ClaimNb` | EU Direct `prem_pure` | AUS Auto `VehValue` |
|---|---|---|---|
| Path | `data/raw/freMTPL2freq.csv` | `data/raw/eudirectlapse.csv` | `data/raw/ausprivauto0405.csv` |
| Shape | 678,013 × 12 | 23,060 × 19 | 67,856 × 7 |
| Target meaning | claim count per policy-period | pure premium (currency) | insured vehicle value (currency units, scaled) |
| Range | 0–16 | 45.55–2,716.08 | 0–34.56 |
| Zero mass | 643,953 = **94.98%** | 0 | 53 = **0.078%** |
| Positives / mean | 34,060; mean 0.0532 | 23,060; mean 355.88 | 67,803; mean 1.777 |
| Exposure / offset | `Exposure` 0.00273–2.01, mean 0.529, 1,224 rows > 1.0; total 358,499 vehicle-years | none | `Exposure` 0.00274–0.99932, mean 0.469 |
| Offset used historically | **no** — `Exposure` kept as a feature, count modelled raw | n/a | **no** — `Exposure` kept as a feature |
| Other target in the file | — | `lapse` (binary; this is a lapse dataset) | `ClaimOcc` (binary), also kept as a feature |
| Leakage risk | none (exposure-as-feature is a modelling choice, not leakage) | **high** — `prem_final`, `prem_last`, `prem_market` remain in X | moderate — `ClaimOcc` describes claim occurrence, not value, but it is another task's target |
| Canonical split | yes — `experiments.toml:71-76`, KFold(5, shuffle, seed 42) | **no** — no `prem_pure` entry in `experiments.toml`; only `pilot_datasets.eudirectlapse` with target `lapse` (`:95-97`) | yes — `experiments.toml:59-63`, KFold(5, shuffle, seed 42), `drop = []` |
| Historic split | 80/20, seed 42, train capped 300, test capped 2000 — indices not persisted | same | same |

Notes:

- **The EU Direct leakage is measurable without fitting anything.** Spearman correlation with
  `prem_pure`: `prem_final` 0.9908, `prem_last` 0.9774, `prem_market` 0.8640. `prem_final` is an
  exact match for 8.5% of rows, `prem_last` for 22.2%. A linear model given these columns reaches
  R² 0.987 (`multi_dataset_regression_benchmark_results.csv`), which is a statement about column
  redundancy, not about TabPFN's data efficiency.
- **`prem_pure` is not a registered regression target anywhere.** `experiments.toml` has no entry
  for it; `scripts/benchmarks/run_lapse_benchmark.py:110-119` defines a *second* regression view
  of the same target with `n_splits=2`, a different fold count from the 5-fold canonical. Two
  harnesses, one target, no agreement.
- **`ausprivauto0405_vehvalue` is registered with `drop = []`**, so the canonical path keeps
  `ClaimOcc` and `Exposure` in X too. The historic feature set and the canonical one agree here;
  the question of whether they should is unresolved, not a historic defect.
- **Dataset metadata in `docs/current/FINETUNING_EXPERIMENT_REFERENCE.md:145` is stale**: it
  gives 673,383 rows for freMTPL2freq (actual 678,013) and lists a `ClaimAmount` column that does
  not exist in the CSV (12 columns, no `ClaimAmount`). Use the manifest, not that table.
- The canonical freMTPL2 treatment is `log(Exposure)` as a *feature*
  (`run_frontier_benchmark.py:184-201`) plus Poisson deviance — not an offset in the GLM sense.
  That distinction is worth keeping when the new design is specified.

---

## 4. Where `SESSION_SUMMARY_APRIL2_REGRESSOR_SCALING.md` overstates

The summary is the only narrative of the 5K/10K Exposure study. Its companion,
`STAGE_R1_PHASE1A_REPORT.md`, contains the same runs but separates the two effects correctly.
The summary does not.

**(a) A data-scaling delta is presented as a fine-tuning effect.** The summary's Phase 1a table
(`:57-63`) has a column headed "Δ vs 5K" with values `+0.0095 … +0.0579 R²`. Those are
differences between the 10K and 5K **post-step** scores. They measure *row count*. The
companion report's Phase 1a table (`:25-30`) is the one that isolates fine-tuning, and its
Δ R² column reads `+0.0004, −0.0003, +0.0008, −0.0008` — initial vs post-step, same rows. The
summary then closes with "**Practical signal — R² improvements of 5–30% from fine-tuning**"
(`:150`). No fine-tuning delta in either document exceeds 0.0008 absolute. The 5–30% figure is a
misdescription of a scaling delta; the largest one (`+0.0579` on a base of 0.0775) is +75%
relative, and it belongs to 5K→10K, not to fine-tuning.

**(b) The cross-seed stability claim contradicts its own table.** "Cross-seed variance on R²
<0.002 at context=256" (`:76`, repeated as ±0.0013 at `:87`) is true only for the two 10K seeds
(0.1354 vs 0.1341). At 5K, context=256, the summary's own table (`:51-55`) gives 0.0775,
0.1250, 0.1386 — a spread of **0.0611**, roughly 45× the quoted figure. Seed stability is
asserted from the two-seed cell that happens to agree, while the three-seed cell that disagrees
is in the same table.

**(c) "13/13 success" is execution, not efficacy.** The 100% success rate (`:85`) counts runs
that executed a gradient step without a non-finite loss. It says nothing about whether the step
helped. Because `run_small_finetune_regressor_trial.py` also logs `initial_*` and `post_step_*`
side by side (`:433-438`), a genuine effect would have been visible per run — but the summary
reports only post-step values, so the reader cannot see the effect size at all.

**(d) The run counts do not reconcile.** Stage R1 is "9 runs" (`:11`, `:130`) but the table
lists **6** (`:48-55`). The session statistics claim three context sizes "64, 128, 256" (`:135`)
while both phase tables show only 64 and 256. Phase 1a is described as "Seeds tested: 42, 1337"
(`:21`) — two seeds — under a heading that elsewhere claims three. The three missing Stage R1
runs are presumably the 128-context rows, but no artifact survives to say so.

**(e) Timing is described as linear where the report's own numbers are not.** The summary says
"Wall time increases linearly: 5K→10K ≈ 2x" (`:26`). The companion report records context=256
going 126s→101s (`:46`), a decrease, which it honestly labels "variance, not systematic". The
summary keeps the linearity claim and drops the counter-example.

None of this makes the runs worthless. It makes the summary unsafe as a citation and the
companion report the better source — subject to the missing ledger, which applies to both.

---

## 5. The Exposure diagnostic's data range

`STAGE_R1_PHASE1A_REPORT.md:133` states the target as "Exposure (continuous, **0.0–1.0 range**)".

Measured on the file both documents name (`freMTPL2freq.csv`):

| | Value |
|---|---|
| Minimum | 0.002732 |
| Maximum | **2.01** |
| Mean | 0.5288 |
| Rows > 1.0 | 1,224 (0.18%) |
| Rows = 0 | 0 |

So the claim is wrong in both directions: the lower bound is not 0.0, and the upper bound is
twice the stated maximum. A model told the target lives in [0,1] is being told the wrong thing
about 1,224 rows; a reader told the target lives in [0,1] will misread the R² values, which are
computed against a target whose variance is dominated by a spread up to 2.01.

The same statement would be **correct** for the other Exposure column in the data,
`ausprivauto0405.csv` (0.00274–0.99932). Since both documents name freMTPL2freq as the dataset,
this is a transcription of the wrong dataset's range, not a coincidence.

---

## 6. What the record can support

| Claim | Verdict | Why |
|---|---|---|
| "Fine-tuning executed reliably on a continuous target." | **Supported** | Two independent documents agree on 13/13 runs and zero non-finite losses; the harness's skip counters are designed to detect exactly this. The ledger that would prove it is gone, but the claim is narrow and the failure mode loud. |
| "Fine-tune deltas were small (≤0.003 R²) at 10K rows." | **Supported, provisionally** | Phase 1a reports initial and post-step side by side for all four runs; the maximum absolute delta is 0.0008. Single-document evidence. |
| "Fine-tuning did not improve over raw TabPFN." | **Not supported** | The comparison crosses a 300→64 context cut. AUS Auto executed **zero** steps and still "degraded" (R² 0.582→0.533, MAE 0.446→0.463) — the delta cannot be fine-tuning. |
| "TabPFN had the best MAE on ClaimNb despite 33× fewer rows." | **Rejected** | Zero-predictor MAE is 0.0580 on that exact test subset; TabPFN is 0.0586. On the 10K-row baseline's test set, zero-predictor is 0.0534 vs CatBoost 0.0763. The metric cannot separate any of these models from a constant. |
| "EU Direct premium R² 0.984 shows data efficiency." | **Rejected** | `prem_final` / `prem_last` / `prem_market` are in X at Spearman 0.991 / 0.977 / 0.864. The score is column redundancy. |
| "ClaimNb fine-tuning is numerically unstable." | **Supported as an observation, not a mechanism** | Skips are logged and the narrative is consistent; Stage R2's own ablation rejected the zero-inflation explanation (`STAGE_A_B…md:113-124`). The proposed causes (log1p standardisation, unbounded forward pass, `normalized_bardist` asymmetry) were never tested. |
| "TabPFN regressor is not viable for insurance counts." | **Not supported** | Everything above is at 300 training rows with one gradient step and a 64-row inference context, on a metric that a constant beats. It is a statement about the harness. |

---

## 7. What the new design must re-measure

Grouped by why it cannot be inherited.

**Because the metric was wrong**
1. Score `ClaimNb` with Poisson deviance against an exposure offset, as `experiments.toml:71-76`
   already declares. MAE/R² on a 95%-zero count is uninformative and a constant beats every
   historic model.
2. Report the trivial baselines (zero predictor, training mean) alongside every model. One line
   of code, and it would have caught finding 4 above.

**Because the split was not the canonical one**
3. Rebuild every split through `make_folds` (`src/experiment_spec.py:558-570`) and persist the
   indices. The historic record used an unpersisted 80/20 holdout with a 300-row cap, so it
   cannot be reproduced even in principle.
4. Register `prem_pure` as a regression target, or decide it is out of scope. Two harnesses
   currently disagree about it (5-fold vs 2-fold).

**Because the comparison was not matched**
5. Run both arms at an identical, recorded inference context — `HISTORIC_FINETUNING_APPRAISAL.md`
   §6.1 already makes this the first fairness requirement, and it applies to the regressor
   exactly as it did to the classifier.
6. Publish the raw-vs-fine-tuned delta from the *same* script. The fine-tuned benchmark computes
   both arms in one process at one context (`:275-303`) and then never writes the pair out.
7. Use a fine-tune budget that could plausibly move a metric: batch size above 1, more than one
   step, and the library trainer rather than the hand-rolled loop.

**Because the data had defects**
8. Drop `prem_final`, `prem_last`, `prem_market` before modelling `prem_pure`, and say so in the
   dataset entry.
9. Decide, explicitly, whether `ClaimOcc` and `Exposure` belong in X for `VehValue`; the current
   registry entry (`drop = []`) says yes by omission.
10. Fix `FINETUNING_EXPERIMENT_REFERENCE.md:145` (673,383 rows, phantom `ClaimAmount`).

**Because the record has no capture**
11. Commit the ledger, the run metadata and per-fold predictions. The historic runs produced all
    three and none survived; `docs/analyses/prediction_capture_rescore_spec.md` and the capture
    contract already describe what "survived" should mean.

---

## 8. Method and limits

- Read-only throughout: no model fits, no API calls, no GPU.
- The zero-predictor and constant-mean MAEs were recomputed by replaying the scripts' own split
  calls (`train_test_split(..., test_size=0.20, random_state=42)`, then `train_size=300` /
  `test_size=2000`) against the checksum-verified CSVs. They are exact for those seeds and caps.
- The two session documents are read from the pre-restructure working directory because they are
  not in git; they are quoted as narrative evidence, not as verified results. Their provenance is
  weaker than any committed file's and is called out wherever they carry a number.
- The fine-tuning behaviour of `clone_model_for_evaluation` and `SUBSAMPLE_SAMPLES` is described
  from its call sites and the appraisal's account of it; the upstream `tabpfn` source is not
  vendored in this repository, so the internal semantics were not re-read.
- Nothing here was verified by rerunning TabPFN. A rerun is the only way to recover the lost
  numbers, and it is a paid run — out of scope for this ticket.
