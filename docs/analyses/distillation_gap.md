# Distillation gap on the R1 four — what our own records support (issue #370)

Status: desk analysis over committed records — **no new runs, no fits, no spend, no GPU**.
2026-10-31. Branch `research/distill-gap`; research note, never merged.

Answers one question: how large is the gap distillation would have to close, **per dataset and
per student**, measured from records we already hold rather than from the literature? The gap is
defined as `AUC(teacher) − AUC(student)` on the pinned primary metric, ROC AUC
(`docs/analyses/metrics_explained.md`). A positive gap is headroom; a negative gap means the
student already beats the teacher and distillation has nothing to transfer.

## 1. How to read this note

Every number carries one of four labels. There are no unlabelled numbers.

| Label | Meaning |
| --- | --- |
| **[M]** | **Measured** — read directly from a committed record. The file is named. |
| **[D]** | **Derived** — arithmetic over measured values in this note (gap, z, CI). Inputs are named. |
| **[E]** | **Estimated** — inferred from a record that does **not** hold the exact comparison: a subsample, a proxy estimator, or a different protocol. The basis is named. |
| **[—]** | **Not measurable** — no record in the repo supports the number. This is a finding, not a failure. |

### Version eras — the constraint that governs every citation

`docs/MODEL_VERSIONS.md` splits the repo across two model lines. The R1 four are **classification**,
so the valid era is **`v3_default` / tabpfn-client 0.3.3** (Aug 2026). The **v2-era** rows
(Mar–Apr 2026) are frozen: "Methods reusable; numbers not portable." They are quoted in §5 only as
a *student ordering* check, never as a teacher number.

`results/` was checked and is **not** usable here: its four run directories
(`20260916-102642`, `-103015`, `-103346`, `-120029`) hold `spanish_motor_severity`,
`spanish_motor_freq`, `bemtl97_amount` and `freMTPL2freq` — **regression/count** datasets on
**v3.5** (`v3.5_default`, client 0.6.0). Wrong tier and wrong era for the R1 four. The R1 four
live under `scripts/eval/` and `outputs/finetune/pilot/`.

## 2. Headline table — the R1 four, full-data records

Teacher = raw TabPFN v3 (`v3_default`). Students = the four pinned in `src/baseline_config.py`.
Gap = teacher − student, in AUC points. `z` is the **unpaired** conservative statistic
`Δ / √(SE_teacher² + SE_student²)`, the convention already used in master report §14.11.2.

### 2.1 COIL 2000 — `coil2000`, 9,822 rows, 6.0% positive

5-fold `StratifiedKFold(5, shuffle=True, random_state=42)`. Source
`scripts/eval/insurance_benchmark_v1/frontier_results_coil2000.csv`.

| Model | AUC | ± SE | Gap vs teacher | z | Brier gap | Status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| **tabpfn** (teacher) | 0.7731 | 0.0074 | — | — | — | [M] |
| catboost (`cat`) | 0.7469 | 0.0076 | **+0.0263** | +2.48 | −0.00181 | [M] / [D] |
| logistic_regression (`lr`) | 0.7405 | 0.0095 | **+0.0326** | +2.71 | −0.00086 | [M] / [D] |
| xgboost (`xgb`) | 0.7059 | 0.0065 | **+0.0672** | +6.82 | −0.00664 | [M] / [D] |
| random_forest (`rf`) | 0.6890 | 0.0072 | **+0.0842** | +8.18 | −0.00861 | [M] / [D] |

All four gaps are the strongest evidence in this note: full data, canonical folds, every pinned
student present.

### 2.2 US Lapse Agent — `uslapseagent`, 29,317 rows, 37.9% positive

Same protocol. Source `scripts/eval/insurance_benchmark_v1/frontier_results_uslapseagent.csv`.

| Model | AUC | ± SE | Gap vs teacher | z | Brier gap | Status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| **tabpfn** (teacher) | 0.9466 | 0.0020 | — | — | — | [M] |
| catboost (`cat`) | 0.9440 | 0.0018 | **+0.0027** | **+0.97** | −0.00127 | [M] / [D] |
| xgboost (`xgb`) | 0.9407 | 0.0020 | +0.0059 | +2.06 | −0.00500 | [M] / [D] |
| random_forest (`rf`) | 0.9345 | 0.0016 | +0.0121 | +4.61 | −0.00715 | [M] / [D] |
| logistic_regression (`lr`) | 0.9254 | 0.0025 | +0.0212 | +6.65 | −0.01033 | [M] / [D] |

The CatBoost gap (+0.0027, z = 0.97) is **indistinguishable from zero**. Distillation has
essentially no AUC headroom against the best student here.

### 2.3 Spanish Motor Lapse — `spanish_motor_lapse`, 53,502 rows, 35.4% positive

5-fold, `scripts/benchmarks/run_lapse_benchmark.py`. Source
`scripts/eval/lapse_benchmark_v1/results_per_split.csv` (per-fold AUC recomputed as
`1 − metric_error`; reproduces §14.10 and `regime_characterization.md` exactly).

| Model | AUC | ± SE | Gap vs teacher | Folds teacher wins | Paired t | Status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| **TabPFN** (teacher) | 0.7553 | 0.0026 | — | — | — | [M] |
| `LinearModel` (proxy for `lr`) | 0.6841 | 0.0015 | **+0.0711** | 5/5 | +28.3 | [M] pair, **[E] estimator identity** |
| LightGBM (not a pinned student) | 0.7500 | 0.0022 | +0.0053 | 5/5 | +7.9 | [M] |
| catboost | [—] | [—] | [—] | [—] | [—] | **[—]** |
| xgboost | [—] | [—] | [—] | [—] | [—] | **[—]** |
| random_forest | [—] | [—] | [—] | [—] | [—] | **[—]** |

The headline +0.0711 is measured **against a linear model, not against the best student**.
LightGBM sits only +0.0053 behind the teacher, so the +0.0711 figure overstates the headroom a
distillation student would actually have to recover. CatBoost/XGBoost/RandomForest were never
fitted (see §4).

### 2.4 EU Direct Lapse — `eudirectlapse`, 23,000 rows, 12.8% positive

Same 5-fold lapse protocol and source as §2.3.

| Model | AUC | ± SE | Gap vs teacher | Folds teacher wins | Paired t | Status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| **TabPFN** (teacher) | 0.6101 | 0.0049 | — | — | — | [M] |
| `LinearModel` (proxy for `lr`) | 0.6260 | 0.0037 | **−0.0159** | **0/5** | **−12.9** | [M] pair, **[E] estimator identity** |
| LightGBM (not a pinned student) | 0.6138 | 0.0043 | −0.0037 | 1/5 | −1.2 | [M] |
| catboost | [—] | [—] | [—] | [—] | [—] | **[—]** |
| xgboost | [—] | [—] | [—] | [—] | [—] | **[—]** |
| random_forest | [—] | [—] | [—] | [—] | [—] | **[—]** |

**The teacher loses.** On EU Direct Lapse the gap is negative and decisive: raw TabPFN is behind
a linear model on all five folds. The ceiling is a linear model, not the teacher, so distillation
from TabPFN into a student cannot help — a student trained to imitate the teacher would be
*worse* than the logistic regression it replaced.

### 2.5 Summary — teacher minus best known student

| Dataset | Best known student | Best-student AUC | Headroom (AUC) | Status |
| --- | --- | ---: | ---: | --- |
| coil2000 | catboost | 0.7469 | **+0.0263** | [M] / [D] |
| uslapseagent | catboost | 0.9440 | **+0.0027** (z 0.97) | [M] / [D] |
| spanish_motor_lapse | `LinearModel` (+ CatBoost estimate 0.7114) | 0.6841 (0.7114) | **+0.0711** (+0.0116 [E]) | mixed |
| eudirectlapse | `LinearModel` | 0.6260 | **−0.0159** (teacher behind) | [M] pair, proxy estimator |

## 3. The one record that covers all four — and why it only estimates

`outputs/finetune/pilot/` holds a single protocol-matched teacher/student run on **all four**
datasets: 2,000 train / 1,000 test rows, seed 42, arms `A_raw` (TabPFN), `E_glm`
(`LogisticRegression(max_iter=1000)`, i.e. the pinned `logistic_regression`) and `F_catboost`
(CatBoost). Sources `outputs/finetune/pilot/pilot_metrics.parquet` and
`outputs/finetune/pilot/pilot_predictions.parquet`. Gaps and 95% CIs below are [D]: paired
bootstrap, 3,000 resamples of the shared 1,000-row test set, seed 42. Recomputed AUC agrees with
the stored `roc_auc` column to ≤ 0.0005 (stored probabilities are rounded to 6 dp).

| Dataset | Teacher `A_raw` | `logistic_regression` | Gap [CI] | CatBoost | Gap [CI] | Status |
| --- | ---: | ---: | --- | ---: | --- | --- |
| coil2000 | 0.7679 | 0.6830 | +0.0849 [+0.0228, +0.1508] | 0.6993 | +0.0686 [+0.0288, +0.1095] | [E] subsample |
| eudirectlapse | 0.5879 | 0.5744 | +0.0136 [−0.0118, +0.0386] | 0.5738 | +0.0141 [−0.0210, +0.0522] | [E] subsample |
| spanish_motor_lapse | 0.7230 | 0.6166 | +0.1065 [+0.0771, +0.1359] | 0.7114 | **+0.0116 [−0.0060, +0.0300]** | [E] subsample |
| uslapseagent | 0.9360 | 0.9271 | +0.0090 [+0.0001, +0.0175] | 0.9297 | +0.0064 [+0.0006, +0.0125] | [E] subsample |

Three hard limits keep this out of §2:

1. **2,000 training rows.** COIL 2000 is 9,822 rows and Spanish Motor Lapse 53,502 — this is a
   fifth to a twenty-seventh of the data.
2. **1,000 test rows**, so intervals are wide; COIL 2000 has only 57 positives in the test set.
3. **A degraded teacher.** The recorded config carries `n_estimators: 2` and `context_samples: 64`;
   master report §13 records that `n_estimators` 8 is the server default and 1 is worse. This is a
   fine-tuning-ladder harness, not a baseline harness.

It is still the only record where a CatBoost gap exists for the two lapse datasets at all — so it
is the basis for the [E] entries in §2, and the reason the Spanish Motor Lapse estimate is the
weakest consequential number in this note.

## 4. What is not measurable, stated plainly

1. **CatBoost, XGBoost and RandomForest on both lapse datasets.** No full-data record exists.
   `scripts/benchmarks/run_lapse_benchmark.py` lists them commented out under
   `# --- Deferred to the GPU run ---` (XGBoost, CatBoost, RandomForest, LogisticGlm), and the
   recorded panel is `TabPFNClient`, `LightGBM`, `Linear` only — confirmed by grouping
   `results_per_split.csv` (5 folds × 3 methods per classification dataset). The GPU run that was
   to supply them has no record. This is the single largest hole in the question.
2. **The identity of `Linear`.** The record names it `[Lapse] LinearModel`
   (`LinearModel_c1_default_HOLDOUT`), not `logistic_regression`. TabArena is not installed or
   vendored in this clone, so the record **cannot** settle whether it is an unregularized or
   differently-configured logistic regression. The §2.3/§2.4 linear rows are therefore proxy
   comparisons, and the eudirectlapse sign rests on a proxy.
3. **Per-fold AUC for coil2000 / uslapseagent.** `alt_metrics_per_fold.csv` is regression-only, and
   the AUC re-score's per-fold output went to `/tmp/opencode` (§14.11) and was never committed. So
   no *paired* test is possible on those two datasets — only mean ± SE with an unpaired,
   conservative `z`. The gaps there are likely understated in significance, not overstated.
4. **Brier on both lapse datasets.** The lapse record carries only `roc_auc` and `rmse`. There is
   no calibration record for eudirectlapse or spanish_motor_lapse at v3, so the secondary metric
   cannot be quoted for §2.3/§2.4.
5. **A machine-readable version pin for the full-data records.** `frontier_results_*.csv` and
   `results_per_split.csv` carry no version field. The `v3_default` attribution rests on
   `docs/MODEL_VERSIONS.md`'s timeline (Aug 2026 → v3) plus master report §14.11's narrative
   (client 0.3.3, `model_path="v3_default"`). That is documented provenance, but not a manifest.
   The **only** machine-readable v3 pin among these sources is
   `outputs/finetune/pilot/pilot_metrics.parquet`, whose `checkpoints` field reads
   `tabpfn-v3-classifier-v3_default.ckpt` — which is the *estimated* record, not the measured one.
6. **`outputs/gpu-pilot/pilot_metrics.parquet`** was ignored: its own README marks it stale and
   superseded by the per-run records.

## 5. The v2-era four-student panel — usable only as an ordering, not a gap

`outputs/current/tables/Table1_Model_Performance.csv` (committed 2026-03-29) is the **only**
record holding all four pinned students on a lapse dataset:

| Model | AUC (eudirectlapse) |
| --- | ---: |
| LogisticRegression | 0.5991 |
| TabPFN | 0.5929 |
| CatBoost | 0.5909 |
| RandomForest | 0.5777 |
| XGBoost | 0.5512 |

It cannot produce a gap, for two independent reasons: the teacher is **v2 era** (`MODEL_VERSIONS.md`:
"numbers not portable"), and the protocol is a **single 80/20 split** with no folds and no SE
(`src/baseline_config.py`: `TEST_SIZE = 0.2`, `RANDOM_SEED = 42`, and the table has no fold
column). Subtracting it from the v3 5-fold teacher would mix an era and a protocol.

Its one legitimate use is a **student ordering**, which is version-independent because students
never see TabPFN: logistic > CatBoost > RandomForest > XGBoost on eudirectlapse. That ordering
corroborates §2.4's sign — the linear model leads, and the teacher sits below it — in a fully
independent, earlier record.

## 6. Headroom available to distillation

Total available headroom across the R1 four is small, uneven, and on one dataset negative.
Measured against the best *student* rather than the weakest, distillation can recover
**≈ +0.026 AUC on COIL 2000** (`+0.0263` over CatBoost, z 2.48 — real but the thinnest of the
COIL gaps, since logistic_regression is only 0.0063 behind CatBoost), and **essentially nothing on
US Lapse Agent**, where CatBoost already sits `+0.0027` behind the teacher at z 0.97 — inside
noise — so the teacher's genuine edge there is calibration and log loss (Brier `−0.00127`), not
ranking. On **Spanish Motor Lapse** the quoted `+0.0711` gap is a gap to a *linear* model and is
not the headroom a distillation student would have to close: LightGBM is `+0.0053` behind the
teacher and the CatBoost estimate is `+0.0116` with a CI containing zero, so the plausible headroom
against a real GBDT student is **~0.005–0.012 AUC, a factor of 6–14 below the headline** — and that
number is estimated, not measured. On **EU Direct Lapse the teacher is the loser**: `−0.0159`
against the linear model on 0/5 folds (paired t −12.9), corroborated in sign by the independent
v2 80/20 panel, so there is no headroom to distil and a student imitating TabPFN would be worse
than the logistic regression it replaced. Net: distillation is worth attempting on COIL 2000,
marginal on US Lapse Agent, unattractive on EU Direct Lapse, and its value on Spanish Motor Lapse
is entirely hostage to a comparison we have never run.

## 7. The single run that would convert the weakest estimate into a measurement

**Re-run the lapse benchmark on `spanish_motor_lapse` and `eudirectlapse` with the deferred students
enabled**, on the existing 5-fold protocol, seed 42, pin pinned and manifested.

Concretely: in `scripts/benchmarks/run_lapse_benchmark.py`, the block marked
`# --- Deferred to the GPU run ---` currently comments out `XGBoost`, `CatBoost`, `RandomForest`
and `LogisticGlmModel`. Uncomment them, keep `StratifiedKFold(5, shuffle=True, random_state=42)`
as it stands, set `TABPFN_MODEL_PATH=v3_default`, and commit a `manifest.json` recording model,
client version, seed and dataset SHA.

Why this run and no other:

- It converts the **weakest consequential estimate** — Spanish Motor Lapse CatBoost `+0.0116`,
  whose CI `[−0.0060, +0.0300]` straddles zero — into a measurement on the *same five folds* as the
  teacher, which is the only way the comparison becomes paired.
- It additionally fills the **entire eudirectlapse student panel**, which today exists only in the
  v2-era 80/20 table, and so tests whether §2.4's negative sign survives against `logistic_regression`
  proper rather than the `LinearModel` proxy.
- It needs **no GPU and no new teacher spend**: TabPFN's five folds for both datasets are already
  computed and committed in `results_per_split.csv`, so the marginal work is CPU-side
  CatBoost/XGBoost/RandomForest/LogisticRegression fits on 53.5K and 23K rows, plus re-scoring.
- It closes findings §4.1, §4.2 and §4.4 above in one pass.

The COIL 2000 and US Lapse Agent gaps in §2.1/§2.2 need no further run to be citable as measured.

## 8. Files

| Claim | Record |
| --- | --- |
| Teacher + 4 students, coil2000 / uslapseagent, 5-fold, AUC+Brier | `scripts/eval/insurance_benchmark_v1/frontier_results_{coil2000,uslapseagent}.csv` |
| Teacher + Linear + LightGBM, both lapse datasets, 5-fold, per fold | `scripts/eval/lapse_benchmark_v1/results_per_split.csv` |
| Student panel identity per dataset | `scripts/eval/lapse_benchmark_v1/method_info.csv` |
| Which students were deferred | `scripts/benchmarks/run_lapse_benchmark.py` |
| Subsample teacher/student pairs, all four | `outputs/finetune/pilot/pilot_metrics.parquet`, `pilot_predictions.parquet` |
| v2-era four-student eudirectlapse panel, 80/20 | `outputs/current/tables/Table1_Model_Performance.csv` |
| Version eras | `docs/MODEL_VERSIONS.md` |
| Metric definitions | `docs/analyses/metrics_explained.md` |
| Full narrative for §14.10 / §14.11 | `docs/analyses/tabpfn_vs_gbdt_baselines_finetuning.md` |
| Pinned student set | `src/baseline_config.py` |
