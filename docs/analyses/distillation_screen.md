# Distillation headroom — the ranked screen over every Dataset with committed Records (#379)

> **Status:** desk analysis over committed records — **no new Runs, no fits, no spend, no GPU, no
> teacher calls**. 2026-10-31. Branch `research/distill-scan`; research note, never merged.

Answers one question: **for every Dataset in this repo that has committed Records, how large is the
gap between the teacher and the best *tuned* GBDT?** It extends
`docs/analyses/distillation_gap.md` (#370) from the R1 four to the whole population, and it obeys
that note's two rules:

* the student is a **tuned GBDT** (`catboost`, `xgboost`, `lightgbm`, `random_forest`) — **never a
  linear model**, because the Spanish Motor Lapse `+0.071` headline was a gap to a linear model and
  the real GBDT gap there was 6–14× smaller;
* the teacher is **raw TabPFN, as recorded**. No version is inferred from a date.

The screen's most useful output is the exclusion list (§6): it names every Dataset that cannot
support a gap, so the next proponent does not re-propose a cell that was never measurable.

## 1. How to read this note

Every number is labelled. There are no unlabelled numbers.

| Label | Meaning |
| --- | --- |
| **[M]** | **Measured** — read from a committed record. The file is named. |
| **[D]** | **Derived** — arithmetic over measured values in this note (gap, z). Inputs are named. |
| **[E]** | **Estimated** — the record does not hold the exact pinned comparison: the student is untuned, the protocol is a subsample, or the teacher config is non-canonical. The basis is named. |
| **[—]** | **Not measurable** — no committed record supports the number. A finding, not a failure. |

**Sign convention is per family, and it is stated in each table's header.** For a
higher-is-better metric (AUC) the gap is `teacher − student`, so positive is headroom. For an
error metric (RMSE, Poisson deviance) the gap is `student − teacher`, so positive is again
headroom and negative means **the teacher is behind**. Every negative gap in this note is a
dataset where distillation has nothing to transfer.

`z` is the unpaired conservative statistic `Δ / √(SE_teacher² + SE_student²)`, the convention
already used in master report §14.11.2 and in the gap note. Where the tuned-baseline record
carries a **paired** per-fold test, the paired `p` is quoted instead and marked as paired — it is
the stronger evidence and it is available for the six tuned-GBDT rows and the reframe row.

## 2. What the pinned unit actually is — and the trap inside it

The ticket's student is the **best tuned GBDT**. This repo has that record:
`scripts/eval/insurance_benchmark_v1/frontier_tuned_baseline_summary.csv` (committed 2026-08-07,
v3 era, §14.13) holds `cat_tuned`, `lgbm_tuned`, `rf_tuned` alongside the untuned panel, on the
same five folds, with a paired t-test against TabPFN per baseline.

**The tuned GBDT is usually a worse ranker than the untuned one.** The tuning objective was log
loss / Brier (§14.13), and on AUC the tuned variants lose to their own defaults on **four of the
six** classification datasets — by 0.024 to 0.042 AUC:

| Dataset | Best default GBDT | AUC | Best tuned GBDT | AUC | Tuned − default |
| --- | --- | ---: | --- | ---: | ---: |
| ausprivauto0405 | lgbm | 0.6425 | lgbm_tuned | 0.6008 | **−0.0417** |
| norauto | lgbm | 0.6971 | cat_tuned | 0.6626 | **−0.0345** |
| coil2000 | cat | 0.7469 | cat_tuned | 0.7185 | **−0.0284** |
| bemtl97 | lgbm | 0.6169 | cat_tuned | 0.5925 | **−0.0244** |
| uslapseagent | cat | 0.9440 | rf_tuned | 0.9355 | −0.0085 |
| bemtl16 | lgbm | 0.9552 | rf_tuned | 0.9527 | −0.0025 |

All cells **[M]**, same file. So "best tuned GBDT" is *not* "best GBDT": picking the tuned student
**inflates the gap by 3.1× on ausprivauto0405 and 8.6× on norauto**. This is the same class of
error as the Spanish-lapse linear-model headline, in the opposite direction — there the student
was too weak, here the student is too weak because it was tuned for a metric that is not the one
being screened.

The note therefore reports **both** students per row and ranks on the pinned unit as the ticket
requires, with the default-GBDT gap carried alongside as the robustness check. §5 gives the
shortlist both ways. Every tuned config is in §4.3 so the student's identity is auditable.

## 3. How the population was found

Discovery was exhaustive over `results/`, `outputs/` and `scripts/eval/`, and every Dataset whose
records carry a model name and a metric was considered. The files that carry a **teacher and a
GBDT on one protocol** are:

| Source | Datasets | Protocol | Teacher pin |
| --- | --- | --- | --- |
| `scripts/eval/insurance_benchmark_v1/frontier_results_*.csv` | 6 classification + 6 regression (plus seed/variant files) | 5-fold, seed 42 | v3 era (Aug 2026) |
| `scripts/eval/insurance_benchmark_v1/frontier_tuned_baseline_summary.csv` | the 6 canonical classification tables | same folds, paired | v3 era |
| `scripts/eval/lapse_benchmark_v1/results_per_split.csv` | 3 lapse datasets | 5-fold (`eudirectlapse_premium`: 2) | v3 era |
| `scripts/eval/insurance_benchmark_v1/reframe_frequency_*.csv` | `spanish_motor_freq` as binary / ordinal | 5-fold × 2 seeds (ordinal × 1) | v3 era |
| `results/20260916-*/frontier_results_*.csv` | 4 regression/count tables | 5-fold, seed 42 | **v3.5** (Sep 2026) |
| `outputs/finetune/pilot/pilot_metrics.parquet` | the R1 four | 2,000/1,000 subsample | v3, degraded config |
| `outputs/current/`, `outputs/replication/`, `outputs/gpu-pilot/` | eudirectlapse etc. | v2-era / stale | not portable |

**Version eras govern every citation.** `docs/MODEL_VERSIONS.md`: classification and
`eudirectlapse` are `v3_default` (client 0.3.3); the four re-tested regression/count tables are
`v3.5_default` (client 0.6.0), which **supersedes** v3 for those four only. One row
(`ausautoBI8999`) never got the §16 re-test and is still v3. Where a table has both eras, the
policy-current record is quoted and the superseded v3 number is footnoted, never mixed.

The result is **15 rows over 14 distinct tables**:

* **classification (9 rows)** — `coil2000`, `uslapseagent`, `ausprivauto0405`, `bemtl16`,
  `bemtl97`, `norauto`, `spanish_motor_lapse`, `eudirectlapse`, and
  `spanish_motor_freq` re-framed as claim/no-claim;
* **frequency (3 rows)** — `freMTPL2freq`, `spanish_motor_freq`, `ausautoBI8999`;
* **severity (3 rows)** — `bemtl97_amount`, `spanish_motor_severity`,
  `ausprivauto0405_vehvalue`;
* **reserving (0 rows)** — no committed record exists. See §6.

## 4. The full table

### 4.1 Classification — metric ROC AUC, gap = teacher − student, positive = headroom

| Dataset | N | Teacher AUC | Best tuned GBDT | AUC | **Gap** | Test | Best default GBDT | AUC | Gap | Record verdict | Flags |
| --- | ---: | ---: | --- | ---: | ---: | --- | --- | ---: | ---: | --- | --- |
| ausprivauto0405 | 67,856 | 0.6622 **[M]** | lgbm_tuned | 0.6008 **[M]** | **+0.0614** **[D]** | paired p=9.7e-6 | lgbm | 0.6425 **[M]** | +0.0197 **[D]** | **none** (result table only) | R, T |
| coil2000 | 9,822 | 0.7731 **[M]** | cat_tuned | 0.7185 **[M]** | **+0.0546** **[D]** | paired p=8.8e-5 | cat | 0.7469 **[M]** | +0.0263 **[D]** | **none** | R, T |
| norauto | 183,999 | 0.7016 **[M]** | cat_tuned | 0.6626 **[M]** | **+0.0389** **[D]** | paired p=2.6e-5 | lgbm | 0.6971 **[M]** | +0.0045 **[D]** | **none** | R, T |
| bemtl97 | 163,212 | 0.6224 **[M]** | cat_tuned | 0.5925 **[M]** | **+0.0299** **[D]** | paired p=1.5e-2 | lgbm | 0.6169 **[M]** | +0.0055 **[D]** | **none** | R, T |
| uslapseagent | 29,317 | 0.9466 **[M]** | rf_tuned | 0.9355 **[M]** | **+0.0111** **[D]** | paired p=1.7e-5 | cat | 0.9440 **[M]** | +0.0027 **[D]** | **none** | R |
| bemtl16 | 58,723 | 0.9560 **[M]** | rf_tuned | 0.9527 **[M]** | **+0.0032** **[D]** | paired p=2.6e-4 | lgbm | 0.9552 **[M]** | +0.0008 **[D]** | **none** | R |
| spanish_motor_lapse | 53,502 | 0.7553 **[M]** | *none recorded* → lgbm | 0.7500 **[M]** | **+0.0053** **[E]** | z=+1.54 | lgbm | 0.7500 **[M]** | +0.0053 **[E]** | **none** | R, U |
| eudirectlapse | 23,060 | 0.6101 **[M]** | *none recorded* → lgbm | 0.6138 **[M]** | **−0.0037** **[E]** | z=−0.56 | lgbm | 0.6138 **[M]** | −0.0037 **[E]** | **none** | R, U |
| spanish_motor_freq — claim/no-claim reframe | 53,502 | 0.7170 **[M]** | *none recorded* → lgbm | 0.7090 **[M]** | **+0.0080** **[E]** | paired p=1.0e-3 | lgbm (cat leads at seed 7 by 0.001) | 0.7090 **[M]** | +0.0080 **[E]** | **none** | R, U |

Sources, per row: teacher and default GBDT from
`scripts/eval/insurance_benchmark_v1/frontier_results_<dataset>.csv` (`mean_auc` column), tuned GBDT
and paired p from `frontier_tuned_baseline_summary.csv` filtered to `metric == "auc"`; lapse rows
from `scripts/eval/lapse_benchmark_v1/results_per_split.csv` recomputed as `1 − metric_error` over
5 folds, seed 42; the reframe row from `reframe_frequency_summary.csv` (`task == binary`,
`seed == 42`). N is the row count of `data/raw/<dataset>.csv`; `eudirectlapse` is 23,060 rows in
the file (the gap note rounds to 23,000).

Flags: **R** = no record-level provenance (see §4.4) · **T** = the tuned student is >0.02 AUC
*worse* than its own default, so the pinned gap is inflated ≥3× · **U** = student is untuned, so
the gap is an estimate in the conservative direction (a tuned GBDT would close it).

### 4.2 Frequency and severity — error metrics, gap = student − teacher, positive = headroom

**These families cannot be screened on AUC.** The pinned primary metric is Poisson deviance or
RMSE (`docs/analyses/metrics_explained.md`, and `primary_metric` in each capture manifest), so the
"teacher AUC" column the ticket asks for is **[—]** for every row below. That is a finding about
the population, not a hole in the screen: **the whole regression tier is invisible to an AUC
screen**, which is why §5's shortlist is classification-only.

| Dataset | Family | N | Metric | Teacher | Best GBDT | Score | **Gap** | z | Teacher version | Record verdict | Flags |
| --- | --- | ---: | --- | ---: | --- | ---: | ---: | ---: | --- | --- | --- |
| freMTPL2freq | frequency | 678,013 | Poisson deviance | 0.3013 **[M]** | lgbm | 0.2911 **[M]** | **−0.0101** **[D]** | −4.55 | v3.5 | partial | R, P |
| spanish_motor_freq | frequency | 53,502 | Poisson deviance | 0.9031 **[M]** | lgbm | 0.8916 **[M]** | **−0.0115** **[D]** | −0.77 | v3.5 | partial | R |
| ausautoBI8999 | frequency (log AggClaim) | 22,036 | RMSE | 0.9649 **[M]** | cat | 0.9688 **[M]** | **+0.0039** **[D]** | +0.34 | **v3 (not re-tested)** | none | R, U, V |
| bemtl97_amount | severity | 163,212 | RMSE | 0.7012 **[M]** | lgbm | 0.4850 **[M]** | **−0.2163** **[D]** | −28.49 | v3.5 | partial | R, P |
| spanish_motor_severity | severity | 53,502 | RMSE | 1.8607 **[M]** | lgbm | 1.8372 **[M]** | **−0.0235** **[D]** | −1.56 | v3.5 | partial | R |
| ausprivauto0405_vehvalue | severity (vehicle value, not a claim) | 67,856 | RMSE | 0.7116 **[M]** | lgbm | 0.7165 **[M]** | **+0.0048** **[D]** | +0.27 | **v3 (not re-tested)** | none | R, U, V |

Sources: the four v3.5 rows from `results/20260916-120029` (freMTPL2freq), `-103015`
(spanish_motor_freq), `-103346` (bemtl97_amount), `-102642` (spanish_motor_severity); the two v3
rows from `frontier_results_ausautoBI8999.csv` and `frontier_results_ausprivauto0405_vehvalue.csv`.
There is **no tuned-GBDT record for any regression dataset** — the tuned panel is
classification-only — so every student here is the untuned default and every gap is an **[E]-grade
upper bound on headroom**, even though the arithmetic itself is [D].

Flags: **P** = partial record · **V** = the regression tier moved to v3.5 under §16 and this table
was not re-tested, so its record is one era behind its family · **U** = untuned student.

Superseded v3 numbers, for the four tables that were re-tested (never to be mixed with the above):
`freMTPL2freq` teacher 0.3877 vs lgbm 0.2911 (gap −0.0966) · `spanish_motor_freq` 0.9876 vs
0.8916 · `spanish_motor_severity` 1.8862 vs 1.8372 · `bemtl97_amount` 0.7282 vs 0.4850. All
**[M]** from the Aug 2026 `frontier_results_*.csv`. The teacher improved on all four under v3.5
and still trails on three.

### 4.3 The tuned students' identity

| Dataset | Base | Config recorded in `frontier_tuned_baseline_results.csv` |
| --- | --- | --- |
| ausprivauto0405 | lgbm_tuned | `lr=0.1, leaves=127, iters=1000` |
| coil2000 | cat_tuned | `lr=0.1, depth=10, iters=478` |
| norauto | cat_tuned | `lr=0.1, depth=10, iters=999` |
| bemtl97 | cat_tuned | `lr=0.1, depth=10, iters=999` |
| uslapseagent | rf_tuned | `mf=sqrt, msl=1` |
| bemtl16 | rf_tuned | `mf=0.5, msl=1` |

Three of the six recorded configs sit at or near the top of the search grid's iteration range
(478, 999, 999), and the panel contains `iters=1000 [dataset cap]` entries for both CatBoost and
LightGBM. That is consistent with §2's finding: the tuning ran on log loss and was compute-capped,
so the "tuned" model is an early-stopped one on the ranking axis.

### 4.4 The record verdict — the largest single weakness in the screen

`src/provenance.py` computes a verdict from a record (`comparable` / `partial` / `unusable`) and
names the missing keys. Run over every committed record this screen could find:

| Record | Verdict | Missing |
| --- | --- | --- |
| `results/20260916-{102642,103015,103346,120029}/manifest.json` | **unusable** | `provenance` |
| `scripts/eval/…/predictions/{bemtl97_amount,freMTPL2freq,spanish_motor_freq,spanish_motor_severity}__seed42__v3.5_default.manifest.json` | **partial** | `provenance.dataset[0].sha256`, `provenance.split.sha256` |
| every classification result table, the lapse benchmark, the reframe and the tuned panel | **no record at all** | a result table is not a record |

So: **four Datasets have a partial record; eleven have none.** The six canonical classification
tables — the population with the most to say about distillation — carry a CSV and a narrative in
`docs/MODEL_VERSIONS.md`, not a manifest. That is exactly the weakness the gap note flagged in
§4.5, and it is now quantified: it is not one table's problem, it is the whole classification
tier. It is why every classification row carries flag **R**.

## 5. Shortlist

### 5.1 Top 5 by the pinned gap (best tuned GBDT)

| # | Dataset | Gap | Paired p | Same gap vs the best *default* GBDT | Is the row usable? |
| ---: | --- | ---: | --- | ---: | --- |
| 1 | **ausprivauto0405** | **+0.0614** | 9.7e-6 | +0.0197 | partly — the tuned student is 0.042 AUC below its own default, so ≥3× of this is the student, not the teacher |
| 2 | **coil2000** | **+0.0546** | 8.8e-5 | +0.0263 | **yes** — the only row whose gap clears +0.02 under both student definitions |
| 3 | **norauto** | **+0.0389** | 2.6e-5 | +0.0045 | **no** — 8.6× of the gap is the tuned student's weakness; the real headroom is ~0.005 |
| 4 | **bemtl97** | **+0.0299** | 1.5e-2 | +0.0055 | **no** — same failure, 5.4× |
| 5 | **uslapseagent** | **+0.0111** | 1.7e-5 | +0.0027 | marginal — real but inside the noise band a distillation result would need to beat |

### 5.2 The shortlist that survives both student definitions

| # | Dataset | Gap vs tuned | Gap vs default | Verdict |
| ---: | --- | ---: | ---: | --- |
| 1 | **coil2000** | +0.0546 | +0.0263 | **the one recommendation.** 9,822 rows, 6.0% positive, the ranking gap is real against every student tried, and the gap note already established it as the strongest measured headroom at v3 |
| 2 | **ausprivauto0405** | +0.0614 | +0.0197 | second, with the caveat that its tuned lgbm is a broken student |
| 3 | **uslapseagent** | +0.0111 | +0.0027 | a calibration story (Brier −0.0013 at v3), not a ranking one |
| 4 | **bemtl16** | +0.0032 | +0.0008 | saturated; the teacher's edge is calibration |
| 5 | **norauto / bemtl97** | +0.0389 / +0.0299 | +0.0045 / +0.0055 | reach this rank only through the tuned-student artifact |

**Read the two lists together.** Ranked on the pinned unit, the shortlist is
ausprivauto0405 → coil2000 → norauto → bemtl97 → uslapseagent. Cross-checked against a default
GBDT, the order becomes coil2000 → ausprivauto0405 → bemtl97 → norauto → uslapseagent, and only
**coil2000** keeps a gap above +0.02. Distillation is worth attempting on one table, defensible on
a second, and everywhere else the headroom is smaller than the run-to-run noise of the metric.

## 6. Exclusions — every Dataset and record dropped, with its reason

An exclusion list is the screen's most useful output. Twelve records were dropped; **three
Datasets** were excluded outright.

### Datasets excluded outright

| Dataset | Where it lives | Why it cannot support a gap |
| --- | --- | --- |
| **`eudirectlapse_premium`** | `scripts/eval/lapse_benchmark_v1/results_per_split.csv` | Recorded on **`prem_pure` with `metric=rmse`, on 2 folds only**, no `roc_auc` column. Recomputing `1 − metric_error` as an "AUC" yields −18 to −81, which is meaningless. A two-fold regression record of a premium cannot yield an AUC gap, and two folds cannot yield a paired test. |
| **`freMTPL2freq_binary`** | `data/raw/freMTPL2freq_binary.csv`, 50,000 rows | Data file is committed; **no model record exists**. Documented only in archived design notes. Would be a valuable classification row if anyone ran it. |
| **`fretelematic`** | `data/raw/fretelematic.csv`, 1,177 rows | Data file is committed; **no model record exists**. Also the only genuinely small table in the repo, so it would need the tiny-N flag if it were ever run. |

### Records excluded (Dataset already covered, or protocol not comparable)

| Record | Why excluded |
| --- | --- |
| `scripts/eval/insurance_benchmark_v1/frontier_results_*_seed7.csv`, `*_seed123.csv` (`ausprivauto0405`, `bemtl97`, `norauto`) | Seed-stability re-runs of tables already in the screen. Their files carry the **primary metric only** (log loss) — no `mean_auc` column — so they cannot support an AUC gap even in principle. |
| `scripts/eval/smoke_test/*` | A 2-fold smoke test on a `coil2000_smoke` subsample whose purpose is to prove the runner fires. Same table as `coil2000`, non-benchmark protocol. |
| `scripts/eval/insurance_imbalance_pilot/*` | **One method only** (`TabPFNClient-balanced`) on `coil2000` and `uslapseagent`. No GBDT on that protocol, so no gap can be formed. |
| `scripts/eval/insurance_benchmark_v1/home_turf_sweep_results.csv` | Size sweep on `bemtl97`, `coil2000`, `uslapseagent` — useful for a size story, but `n_estimators` and `trimmed` vary across cells, so the teacher is **not** the canonical `v3_default` config and the gap is not comparable to a full-data row. Quoted only as a diagnostic: at 1,000 rows the gaps are +0.026 (coil2000), +0.006 (uslapseagent) and **−0.065** (bemtl97) — the gap does not grow as data shrinks, which undercuts the "small data is where distillation pays" intuition on this suite. |
| `outputs/finetune/pilot/pilot_metrics.parquet` | Only record with a CatBoost gap for the two lapse tables, but it is a 2,000-train / 1,000-test subsample with a **degraded teacher** (`n_estimators: 2`, `context_samples: 64`). Used exclusively as **[E]** corroboration: spanish_motor_lapse CatBoost gap +0.0116 (CI −0.0060…+0.0300), eudirectlapse +0.0141 (CI −0.0210…+0.0522) — both CIs cross zero. |
| `outputs/gpu-pilot/pilot_metrics.parquet` | Its own `README.md` marks it stale and superseded by the per-run records. |
| `outputs/replication/tables/model_metrics.csv` | v2 era (Mar–Apr 2026), 70:30 single split, seed 45. `MODEL_VERSIONS.md`: numbers not portable. |
| `outputs/current/tables/Table1_Model_Performance.csv` | v2 era, 80/20 single split, no folds, no SE. The only v2 four-student panel on `eudirectlapse`; usable as a **student ordering** (logistic > CatBoost > RF > XGBoost) and nothing else. |
| `outputs/current/tables/domain_finetune_study_runs.csv`, `tabpfn_finetune_trial_results.csv` | v2-era fine-tuning trials; arms, not baselines, and no GBDT panel. |
| `reframe_frequency_summary.csv`, `task == ordinal` | The same table as the binary reframe row, on an ordinal target, one seed. Including both would double-count `spanish_motor_freq`. Recorded gap if anyone wants it: teacher 0.7167 vs cat 0.7035, **+0.0132** at seed 42. |
| `scripts/eval/insurance_benchmark_v1/frontier_tuned_baseline_*` rows for `xgb` | `xgboost` has **no tuned record** at all, so the "best tuned GBDT among four families" is a best-of-three in this repo. Stated rather than papered over. |

### Per-method defects worth naming (not exclusions)

* `tweedieglm` returns a **constant** on `bemtl16` and on the reframe binary task: AUC exactly
  0.5, and `poissonglm` scores 6.45 Poisson deviance on `bemtl97_amount`. Those rows are
  degenerate, and a screen that read "the GLM is worst" off them would be reading a bug.
* `poissonglm` and `tweedieglm` are byte-identical on `freMTPL2freq` (0.3211 both) and on
  `spanish_motor_freq` (1.0125 both) — the same fit under two names.

## 7. Family summary

**Classification (9 rows).** This is the only family where the teacher is ahead of the GBDT on
most rows — eight of nine — and the headroom is small and uneven: **+0.003 to +0.061 AUC on the
pinned unit, and +0.0008 to +0.026 against a default GBDT on the eight positive rows**. The
pattern is not "big tables, big gaps": the
two largest classification gaps that survive the cross-check are `coil2000` (9.8k rows) and
`ausprivauto0405` (67.9k), while `bemtl16` (58.7k) and `uslapseagent` (29.3k) are effectively
saturated at +0.003 and +0.011 on the pinned unit and +0.001/+0.003 on a default GBDT. On
`eudirectlapse` the teacher is **behind** the GBDT (−0.0037, z −0.56) and behind a linear model,
corroborating the gap note's negative finding with a second, independent record. The reframe row
says something the count row does not: on the *same* `spanish_motor_freq` table, the teacher's edge
is **+0.008 AUC on claim/no-claim** and **−0.0115 Poisson deviance on the claim count**. The
teacher's advantage lives in the binary occurrence question, not the count.

**Frequency (3 rows).** No headroom. The teacher loses to LightGBM on both Poisson-deviance
targets (`freMTPL2freq` −0.0101 at z −4.55, decisive; `spanish_motor_freq` −0.0115 at z −0.77,
not separable) and is level with CatBoost on `ausautoBI8999`'s log-scale RMSE (+0.0039, z 0.34,
noise). A student taught to imitate TabPFN here would learn to be **worse** than the GBDT it
replaces — the same failure the gap note found on `eudirectlapse`.

**Severity (3 rows).** No headroom, and one large negative. `bemtl97_amount` is the worst cell in
the screen: the teacher is **0.216 RMSE behind** LightGBM at z −28.5. `spanish_motor_severity`
−0.0235 at z −1.56, `ausprivauto0405_vehvalue` +0.0048 at z 0.27. Severity is a heavy-tailed
monetary target where gradient boosting's loss function is the right tool and in-context
regression is not; nothing here is a distillation candidate.

**Reserving (0 rows).** **There is no committed record of any reserving Dataset.** The repo's
severity tables are per-policy claim amounts, not development triangles; no run has produced a
chain-ladder or Bornhuetter-Ferguson baseline, and no record carries an incurred-but-not-reported
target. The family cannot be screened at all, and saying so is more useful than an empty row.

**Net.** Distillation in this repo is a **classification-only, one-table opportunity**: `coil2000`
first, `ausprivauto0405` second with a caveat about its tuned student. Every frequency, severity
and reserving cell either has the teacher behind a GBDT or has no record at all, so on two thirds
of the population the question "how much headroom would distillation close?" has the same answer:
none, because the teacher is not the ceiling.

## 8. Files

| Claim | Record |
| --- | --- |
| Teacher AUC + default GBDT panel, 8 classification datasets | `scripts/eval/insurance_benchmark_v1/frontier_results_*.csv` |
| Tuned GBDT panel, paired tests, 6 classification datasets | `scripts/eval/insurance_benchmark_v1/frontier_tuned_baseline_{summary,results}.csv` |
| Lapse teacher + LightGBM + linear, per fold | `scripts/eval/lapse_benchmark_v1/results_per_split.csv` |
| Claim/no-claim reframe, binary + ordinal, 2 seeds | `scripts/eval/insurance_benchmark_v1/reframe_frequency_{summary,results}.csv` |
| v3.5 regression/count re-test, 4 tables | `results/20260916-{102642,103015,103346,120029}/frontier_results_*.csv` + `manifest.json` |
| v3.5 capture manifests (the only partial records) | `scripts/eval/insurance_benchmark_v1/predictions/*.manifest.json` |
| Subsample teacher/student pairs, R1 four | `outputs/finetune/pilot/pilot_metrics.parquet` |
| Version eras | `docs/MODEL_VERSIONS.md` |
| Metric definitions and the AUC-vs-log-loss divergence | `docs/analyses/metrics_explained.md` |
| Record contract and verdicts | `src/provenance.py`, `docs/adr/0003-record-contract-and-model-version.md` |
| The R1-four predecessor to this note | `docs/analyses/distillation_gap.md` (#370) |
| The literature the memo must argue against | `docs/analyses/distillation_literature.md` (#369) |
