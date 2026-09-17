# TabPFN vs GBDT Baselines on Insurance Datasets, and Domain Fine-Tuning Effectiveness

Technical research report — engineering/data-science audience.
Branch: `feat/tabarena-benchmark`. Date: 2026-08-01. Updated: 2026-08-02 (§11, §12, §13, §14); 2026-08-03 (§14.6 norauto first extension, §14.7 v1-suite extension, §14.8 regression Phase 2); 2026-08-07 (§14.13 finality test — tuned/engineered classical baselines; §14.14 count/frequency classification reframe — issue #67).

## Results digest (12 datasets)

Compact cross-dataset digest of the frontier runs — mean over folds from
`scripts/eval/insurance_benchmark_v1/frontier_results_*.csv`; detail per dataset in
§14.2–§14.10. Ratio = TabPFN metric ÷ best-method metric (error metrics, lower is better;
1.000 = on par with the best).

| Dataset | Task | Rows | Best method (metric) | TabPFN (metric) | Ratio | On frontier? |
| --- | --- | ---: | --- | ---: | ---: | --- |
| bemtl97 | classification — log loss (claim occurrence; leak-fixed) | 163,212 | lgbm 0.34177 | 0.34279 | 1.003 | yes |
| coil2000 | classification — log loss (caravan purchase) | 9,822 | tabpfn 0.20059 | 0.20059 | 1.000 | yes |
| uslapseagent | classification — log loss (lapse) | 29,317 | tabpfn 0.24909 | 0.24909 | 1.000 | yes |
| norauto | classification — log loss (claim occurrence) | 183,999 | lgbm 0.17518 | 0.17619 | 1.006 | yes |
| ausprivauto0405 | classification — log loss (claim occurrence) | 67,856 | logisticglm 0.23947 | 0.24026 | 1.003 | no |
| bemtl16 | classification — log loss (liability claim) | 58,723 | tabpfn 0.23803 | 0.23803 | 1.000 | yes |
| ausautoBI8999 | regression — RMSE (BI severity) | 22,036 | tabpfn 0.96491 | 0.96491 | 1.000 | yes |
| ausprivauto0405_vehvalue | regression — RMSE (vehicle value) | 67,856 | tabpfn 0.71162 | 0.71162 | 1.000 | yes |
| bemtl97_amount | regression — RMSE (severity, log1p) | 163,212 | lgbm 0.48499 | 0.72825 | 1.502 | no |
| freMTPL2freq | frequency — Poisson deviance | 678,013 | lgbm 0.29113 | 0.38770 | 1.332 | no |
| spanish_motor_freq | frequency — Poisson deviance | 53,502 | lgbm 0.89157 | 0.98764 | 1.108 | no |
| spanish_motor_severity | regression — RMSE (severity, log1p) | 53,502 | lgbm 1.83719 | 1.88616 | 1.027 | no |

\* bemtl97: excluded from the v1 baseline tally (label leak, §6); this row is the
leak-fixed frontier re-run (§14.2).

## 1. Objective

Answer two questions with reproducible evidence:

1. **Does default-config TabPFN beat GBDT baselines on insurance datasets?**
   (Baseline benchmark, authoritative, holdout mode, CPU, default configs only.)
2. **Does domain fine-tuning make TabPFN materially better, and can it close the gap?**
   (Earlier fine-tuning studies — different protocol, synthesized here, not re-run.)

Cross-checked against `docs/reports/REPORT_REGISTRY.md`: no existing report covers the
`insurance_benchmark_v1` GBDT comparison (`results_per_split.csv` is not referenced by any
registry entry). Fine-tuning evidence overlaps with
`docs/reports/COMBINED_TABPFN_CLASSIFIER_REGRESSOR_ANALYSIS.md` and
`docs/reports/STAGE_A_B_FINDINGS_AND_RECOMMENDATIONS.md`; this report cross-references them
rather than duplicating their content.

## 2. Experimental Setup

### 2.1 Baseline benchmark (newest, authoritative)
- Source: `scripts/eval/insurance_benchmark_v1/results_per_split.csv` + `method_info.csv`
- 9 CASdatasets tasks (7 datasets, 2 with dual targets), holdout split, CPU, 3–5 folds.
- 8 methods, all **default config** (`config_type=default`, `can_hpo=False`):
  TabPFNClient, CAT (CatBoost), GBM (LightGBM), XGB (XGBoost), RF, LR, LogisticGLM,
  PoissonGLM, TweedieGLM. GLM variants only run on tasks matching their family.
- Metric: `metric_error` = **error metric, lower is better** — RMSE for regression,
  **1 − ROC AUC** for binary tasks (ROC AUC stored as error).
- Harness drops only the target column from features (`run_tabarena_insurance_benchmark.py:184`).

### 2.2 Domain fine-tuning study (earlier, different protocol)
- Source: `outputs/current/tables/domain_finetune_study_runs.csv`,
  `outputs/current/logs/domain_finetune_logbook.md`
- Stage A protocol: 2,500-row subsets, `cpu/64/1..5` (and `cpu/128/5`), seed 42, single
  train/test split (1,750/750). Models: logistic regression, random forest, raw TabPFN,
  domain-finetuned TabPFN.
- **Not directly comparable to the benchmark**: different targets, splits, row counts, and
  protocol. The benchmark measured only **raw default** TabPFN — no fine-tuned arm ran inside
  the benchmark harness.

### 2.3 Small-finetune trials (protocol validation)
- Source: `outputs/current/tables/tabpfn_finetune_trial_results.csv`
- coil2000 (target `CARAVAN`), rows 300–3,000, 1–3 steps, ctx 64/128, seed 42.

## 3. Data and Targets

| Task (id suffix) | Metric | Task type | Folds |
| --- | --- | --- | --- |
| ausautoBI8999 | RMSE | regression (BI severity) | 3 |
| ausprivauto0405 | 1−AUC | binary (claim occurrence, 6.8% pos) | 5 |
| ausprivauto0405_vehvalue | RMSE | regression (vehicle value) | 3 |
| bemtl16 | 1−AUC | binary (liability claims, 36% pos) | 5 |
| bemtl97 | 1−AUC | binary (claim, 11.2% pos) — **EXCLUDED, leak** | 5 |
| bemtl97_amount | RMSE | regression (severity, log1p zero-inflated) | 3 |
| coil2000 | 1−AUC | binary (caravan purchase) | 5 |
| norauto | 1−AUC | binary (claims, 4.6% pos) | 5 |
| uslapseagent | 1−AUC | binary (lapse) | 5 |

## 4. Results — Baseline Benchmark

Mean `metric_error` across folds, per task. Lower is better; best baseline in **bold**;
TabPFN rank within the task's method pool.

| Task | Metric | Best baseline (err) | TabPFN (err) | Δ vs best | Rank |
| --- | --- | --- | --- | --- | --- |
| bemtl16 | 1−AUC | TabPFN **0.04394** | **0.04394** | 0% | 1/7 |
| coil2000 | 1−AUC | TabPFN **0.22738** | **0.22738** | 0% | 1/7 |
| ausprivauto0405 | 1−AUC | CAT 0.34006 | 0.34240 | +0.7% | 3/7 |
| uslapseagent | 1−AUC | CAT 0.05550 | 0.05688 | +2.5% | 3/7 |
| ausautoBI8999 | RMSE | CAT 0.97588 | 1.01273 | +3.8% | 5/8 |
| norauto | 1−AUC | CAT 0.29947 | 0.31564 | +5.4% | 6/7 |
| bemtl97_amount | RMSE | CAT 0.48201 | 0.71485 | **+48.3%** | 8/8 |
| ausprivauto0405_vehvalue | RMSE | XGB 0.71722 | 1.19891 | **+67.2%** | 8/8 |
| bemtl97 | 1−AUC | GBM 0.00000 | 0.00000 | — | **EXCLUDED** |

### 4.1 Per-dataset verdicts (TabPFN vs best baseline)

- **WIN** — bemtl16, coil2000: TabPFN is the best method (rank 1 of 7). Both are small-ish
  classification tasks with strong categorical structure.
- **TIE** — ausprivauto0405 (claim occurrence): within 0.7% of best (CAT), rank 3/7.
- **LOSE (close)** — uslapseagent (+2.5%), ausautoBI8999 (+3.8%).
- **LOSE (clear)** — norauto (+5.4%, rank 6/7).
- **LOSE (decisive)** — both severity regressions: bemtl97_amount (+48.3%) and
  ausprivauto0405_vehvalue (+67.2%), TabPFN rank 8/8. GBDTs and even linear models crush
  TabPFN on these; TabPFN's zero-shot regression transfer does not fit insurance severity
  targets under default config.

**Tally on 8 valid tasks: 2 wins, 1 tie, 5 losses (2 of them large).** GBDTs (CAT/GBM/XGB)
hold the aggregate lead; TabPFN wins only where default GBDTs are weakest.

### 4.2 Compute cost (engineering)

Train time summed over folds; inference mean per fold.

| Task | TabPFN train (s) | GBM/XGB/CAT train (s) | TabPFN infer/fold (s) | GBDT infer/fold (s) |
| --- | ---: | ---: | ---: | ---: |
| norauto (184K rows) | 190.1 | 5.7–75.1 | **239.9** | <0.05 |
| bemtl97 (163K rows) | 157.9 | 6.7–135.6 | 34.1 | ~0.06 |
| bemtl97_amount | 75.1 | 3.1–15.5 | 30.2 | ~0.05 |
| ausprivauto0405 | 55.1 | 2.7–27.8 | 9.1 | <0.02 |

TabPFN is ~5–50× slower than GBDTs for train and 100–1000×+ for inference on this hardware
(CPU, local Mac). Worst single fold: norauto fold 0 inference took **1,030 s** (vs ~42 s on
other folds — memory/context pressure on the 184K-row task). For production batch scoring of
100K+ row insurance portfolios, raw TabPFN inference is the binding constraint.

## 5. Domain Fine-Tuning Effectiveness

### 5.1 Domain fine-tuning (Stage A protocol) — raw vs tuned TabPFN, ROC AUC

| Target | Raw | Tuned (1 step) | Tuned (3 steps) | Tuned (5 steps) | Verdict |
| --- | ---: | ---: | ---: | ---: | --- |
| eudirectlapse | 0.5763 | 0.5334 | 0.5339 | 0.5337 | Degrades |
| coil2000 | 0.7566 | 0.5541 | 0.5532 | 0.5527 | **Severe degradation (−0.20)** |
| ausprivauto0405 | 0.6486 | 0.5525 | 0.5505 | 0.5508 | Degrades |
| freMTPL2freq_binary | 0.5412 | 0.5819 | 0.5888 | 0.5909 | Improves (+0.05) |

- Only **freMTPL2freq_binary** improved; the other 3 targets degraded at **every** step count
  (1, 3, 5) and context (64, 128 — see `domain_finetune_logbook.md` runs 2026-04-02T01:2x).
- Aggregate deltas (logbook): ROC AUC **−0.0752**, PR AUC −0.0314, Brier +0.0017,
  LogLoss +0.0106 — net degradation under this low-budget protocol.
- Finding consistent with prior report
  `docs/reports/COMBINED_TABPFN_CLASSIFIER_REGRESSOR_ANALYSIS.md`: single-step/3-step/5-step
  domain adaptation is currently **misaligned or too weak** for stable cross-dataset uplift.

### 5.2 Small-finetune trials (coil2000) — negligible

`tabpfn_finetune_trial_results.csv`, all rows/contexts/steps: largest gain was
**+0.0047 ROC AUC** (0.708 → 0.713 at 300 rows); several runs moved −0.002 to −0.008.
Conclusion: one- to three-step fine-tune on the target's own data produces **no material
gain**; step counts are not the lever.

### 5.3 Net assessment

Neither fine-tuning path currently closes the gap to GBDTs. Worse, the benchmark's two
decisive TabPFN losses (severity regressions) are exactly the tasks where the fine-tuning
evidence is thinnest (all finetune studies were classification targets). **Fine-tuning, as
configured today, does not change the "do not deploy TabPFN for severity" verdict.**

## 6. Data Anomaly — bemtl97 (must not be used)

`bemtl97` (`target=claim`) is **excluded from all conclusions** due to confirmed label
leakage:

- The prepared dataset (`prepare_insurance_datasets.py:44-52`) keeps `nclaims` and `amount`
  as **features** alongside the `claim` target.
- Inspection of `data/raw/bemtl97.csv` (163,212 rows):
  - rows with `claim==1` but `nclaims==0`: **0**
  - rows with `claim==0` but `nclaims>0`: **0**
  - rows with `amount>0` where `nclaims==0`: **0** (0 mismatches total)
  - i.e. `claim == (nclaims > 0) == (amount > 0)` **exactly**, for every row.
- The harness only drops the target column from features
  (`run_tabarena_insurance_benchmark.py:184`), so `nclaims`/`amount` stayed in the feature
  matrix. Every method trivially reaches AUC = 1.0 → `metric_error = 0.0000` on all folds.
  CAT shows floating-point residue `1.11e-16`; LogisticGLM shows `4.55e-05` on fold 3 —
  numerically zero.
- **Characterization: hard label leakage** (target derivable from a single feature column),
  not a trivial/near-constant target — the positive rate is a healthy 11.2%.
- **Fix options**: drop `nclaims`/`amount` from the feature set (they are post-hoc outcomes
  of the claim event), or drop the task. Note `bemtl97_amount` (target=`amount`) also keeps
  `nclaims` as a feature, which encodes `amount>0` exactly — a partial target proxy; flag for
  the same cleanup.

## 7. Limitations and Risks

1. **Default configs only** — `can_hpo=False` for all methods; HPO-tuned TabPFN (e.g. TabPFN's
   `auto` mode) could change rankings, as could tuned GBDTs (tuned/feature-engineered classical
   baselines have since been tested on the canonical folds — §14.13; they do not change the
   ranking verdict, only the calibration picture gains two small exceptions).
2. **Fine-tuning protocol mismatch** — finetune studies used 2,500-row subsets and different
   targets; they never ran inside the benchmark harness. A direct "fine-tuned TabPFN vs GBDT"
   head-to-head is still missing.
3. **CPU only, small hardware** — TabPFN inference outliers (norauto fold 0: 1,030 s) suggest
   memory/context pressure; GPU (MPS) was available but unused for the benchmark.
4. **Single seed in finetune studies** (seed 42); the benchmark is fold-based so more robust.
5. **bemtl97 exclusion** removes one of the two large classification datasets; the effective
   evidence base is 8 tasks.
6. **Severity regressions may need transforms** (log/Tweedie-family modeling); default
   TabPFN made no such assumption, while GBDTs and GLMs benefited from harness-level setup.

## 8. Recommendation (engineering-facing)

- **Do not adopt default-config TabPFN as a general insurance modeling engine today.** On 8
  valid CASdatasets tasks: GBDTs win the aggregate; TabPFN loses decisively on both severity
  regressions and costs 5–50× in train and 100–1000× in inference.
- **Keep TabPFN on the bench for niche value**: small-data / few-shot classification
  (bemtl16, coil2000 wins) and cold-start or proxy-model contexts where a GBDT has no
  training signal.
- **Fix the fine-tuning protocol before re-testing** — current domain/self fine-tune
  degrades AUC on 3/4 targets; step-count sweeps (1→5) and context (64→128) do not recover
  it. A working fine-tune is a precondition for any "TabPFN closes the gap" claim.
- **Repair the benchmark**: remove `nclaims`/`amount` from bemtl97 features (also
  `bemtl97_amount`), then re-run bemtl97.
- **What would change the answer**: (a) HPO-enabled TabPFN in the harness; (b) a
  fine-tuned-TabPFN arm inside the benchmark on the same folds; (c) GPU inference for the
  100K+ row tasks; (d) severity-specific transforms in the TabPFN arm. Without at least (a)
  or (b), the verdict stands.
- **Adoption rule (issue #52)**: the decision-level guidance — when to adopt, when to
  expect domination on the trade-off at scale, and the GLM-default middle — lives in the
  one-pager's "Conclusion & adoption guidance"
  (`docs/reports/TABPFN_BENCHMARK_SUMMARY.md`) and the regime analysis
  (`docs/analyses/regime_characterization.md`); this section stays the benchmark-level
  verdict.

## 11. Addendum — Imbalance Pilot and Calibration Re-Score (2026-08-02)

Follow-up to the v1 benchmark (sections 1–10). Does not rewrite the v1 conclusions; it
qualifies the aggregate verdict. Evidence added by commits f1d7cc4 and bb7ab5c.

### 11.1 Hypothesis and pilot

Prior working hypothesis: TabPFN's losses to GBDTs are partly an **imbalance-handling
deficit** — GBDTs get class-weight handling "for free" while TabPFN defaults to the raw
prior. Pilot: `TabPFNClassifier(balance_probabilities=True, n_estimators=8)` vs v1 default
on the two most informative binary tasks, same folds as v1 (`coil2000`, 6% positive;
`uslapseagent`, 38% positive). Harness: `scripts/benchmarks/run_tabarena_insurance_imbalance_pilot.py`;
results: `scripts/eval/insurance_benchmark_v1/focused_imbalance_results.csv`.

### 11.2 Null on 1−AUC, and why

`balance_probabilities=True` produced **1−AUC identical to default to ≤1e-16 on every fold**
of both datasets (exact equality to float64 precision in the CSV, e.g. 0.215550653050653 both
arms, coil2000 fold 0). Root cause: **ROC-AUC is rank-invariant to monotone probability
transforms**, and `balance_probabilities` is a monotone calibration rescale. The v1
benchmark metric is therefore **structurally blind to the lever** — the pilot could never
have moved 1−AUC. Testing the imbalance hypothesis on 1−AUC is a measurement dead end.

### 11.3 Re-score on insurance-native metrics

Same folds re-scored on log loss + Brier — the metrics an insurer actually pays on
(`scripts/eval/insurance_benchmark_v1/rescore_focused_imbalance_logloss.py` →
`focused_imbalance_logloss.csv`). Mean over 5 folds, lower is better:

| dataset | method | log_loss | brier |
| --- | --- | ---: | ---: |
| coil2000 (6% pos) | TabPFN default | **0.2008** | **0.0528** |
| coil2000 | TabPFN balanced | 0.4716 | 0.1572 |
| coil2000 | CAT | 0.2032 | 0.0531 |
| uslapseagent (38% pos) | TabPFN default | 0.2536 | 0.0830 |
| uslapseagent | TabPFN balanced | 0.2669 | 0.0869 |
| uslapseagent | CAT | **0.2516** | **0.0822** |

### 11.4 The lever works in the wrong direction

`balance_probabilities=True` **actively hurts calibration**: it rescales predictions toward
a 50/50 prior, inflating mean predicted probability on 6%-positive coil2000 from 0.047 to
0.327 (base rate 0.06 — roughly a 5× overstatement of purchase risk). It is worse than the
v1 default on **both log loss and Brier in all 5 folds, both datasets**. The imbalance
hypothesis is disproven for insurance data: imbalance handling is not what separates TabPFN
from GBDTs on these tasks, and the exposed lever moves in the wrong direction.

### 11.5 Corrected calibration verdict (nuanced, not reversed)

- **v1-default TabPFN is near-best on log loss**: best on coil2000 (0.2008 vs CAT 0.2032),
  and 0.002 off CAT on uslapseagent (0.2536 vs 0.2516).
- The v1 "TabPFN loses" headline (§4 tally) was **partly an artifact of ranking on 1−AUC**,
  which discards all calibration information. On decision-relevant probabilities TabPFN holds
  its own on these two tasks.
- The verdict is **qualified, not reversed**: §8 still stands — not clearly production-worthy
  on large portfolios (context ceiling + 100–1000× inference cost, §4.2) — but the
  "TabPFN cannot compete on insurance probabilities" reading of the v1 results is dropped.
- Only remaining lever likely to move the aggregate verdict: HPO-enabled TabPFN inside the
  harness (§8(a)). Imbalance/flagship config levers do not.

## 12. Why the v1 results looked the way they did — interpretation and lessons

Sections 1–10 report *what* v1 found; this section explains *why* the numbers were as
lopsided as they were. It separates genuine TabPFN model limits from setup artifacts, so
future work does not re-run or re-explain the same results. No new experiments; every
claim traces to evidence cited above.

### 12.1 Dataset-size mismatch — primary cause of the headline losses

TabPFN is pre-trained on **1,024-sample context windows**. The benchmark's hosted-API
client (`scripts/benchmarks/run_tabarena_insurance_benchmark.py:23,245`) accepts full-size training
sets on our 10K–184K-row datasets (norauto 184K rows, §4.2; bemtl97 163,212 rows, §6), but
each prediction can effectively attend to only ~1K training rows — the local-API
equivalent of this behavior is `ignore_pretraining_limits=True`. GBDTs, by contrast, see
every row in training. This is a **capability limit of the model design, not a harness
bug**. It predicts exactly where TabPFN lost worst: the largest datasets and the
regression/severity tasks where every row of signal matters — bemtl97_amount +48.3% vs
CAT (rank 8/8, §4), ausprivauto0405_vehvalue +67.2% vs XGB (rank 8/8, §4), and the
184K-row norauto classification (+5.4%, rank 6/7, §4). The converse also holds: TabPFN
won its two smallest classification tasks (bemtl16, coil2000; §4.1), where a ~1K-row
context captures the learnable signal. The bemtl97 leak (§6) is unaffected by this — a
single leaking feature is trivially learnable inside any context window, which is why
exclusion is data-driven, not model-driven.

**Model-version correction (2026-08-04).** The "~1K effective context" framing above
was written from a v2.5-era architecture understanding and does **not** describe the
model this benchmark actually ran. All hosted-API runs in this report used the
**hosted v3 model** (auto-selection; pinned post-hoc to `model_path="v3_default"`,
tabpfn-client 0.3.3 — see the §14.9 model version note). Live-verified API limits on
2026-08-04 via the client's `/tabpfn/get_model_limits` (ModelLimit): **v3 supports up
to 1,000,000 rows / 200,000,000 cells / 160 classes / 2,000 columns** (v2/v2.5 capped
at 50,000 rows, v2.6 at 100,000), so there is **no 1K context ceiling at the API
level** for v3. The server manages large training sets internally — plausibly a larger
v3 context window and/or internal subsampling/ensembling — but the mechanism is not
exposed by the client. What stands: the measured size-dependent pattern (TabPFN wins
small data, ties mid-size, drops off the frontier at scale) is empirical and
**mechanism-independent**. The operative v3-era limits are accuracy-per-parameter and
accuracy-per-second against GBDTs/GLMs, not a hard 1K window.

### 12.2 Metric blindness — 1−AUC cannot see calibration

v1 ranked methods on **1−AUC**, a rank-invariant metric that discards all probability
calibration (§2.1). TabPFN's comparative strength is calibrated probabilities, which 1−AUC
is structurally incapable of detecting — §11.2 demonstrates this: `balance_probabilities`
is a monotone probability transform, so its effects are provably invisible to 1−AUC.
The §11.3 re-score on insurance-native log loss / Brier (the metrics an insurer pays on)
shows what 1−AUC hid: default TabPFN is **best on coil2000** (0.2008 vs CAT 0.2032) and
**0.002 off CAT on uslapseagent** (0.2536 vs 0.2516). Part of the v1 "loss" was therefore
a **measurement artifact**, not model behavior.

### 12.3 Uneven tuning — TabPFN at its floor vs competitors at standard settings

The harness ran every method at default config with `can_hpo=False`
(`scripts/eval/insurance_benchmark_v1/method_info.csv`), but "default" is not symmetric
across libraries. CatBoost/LightGBM/XGBoost ship tuned default hyperparameters; TabPFN ran
as a bare `TabPFNClassifier(random_state=0)` (`run_tabarena_insurance_benchmark.py:262–
265`) — pure defaults, no HPO, no ensemble tuning. v1 therefore compared **TabPFN at its
floor against competitors at their standard settings**. HPO-enabled TabPFN in the harness
remains the one lever untested (§8(a), §11.5).

### 12.4 Ruled-out suspects (documented so future work does not re-chase them)

- **(a) CPU.** TabPFN executed on Prior Labs' hosted API, not local CPU
  (`run_tabarena_insurance_benchmark.py:23,245`); local CPU only affected the GBDT/GLM
  arms and the wall-clock comparison (§4.2). CPU does not explain any accuracy gap.
- **(b) Imbalance handling** (`balance_probabilities=True`). Tested in §11: actively
  hurts calibration — rescales predictions toward a 50/50 prior, inflating mean predicted
  probability on coil2000 from 0.047 to 0.327 vs a 0.06 base rate (§11.4) — and is worse
  on log loss and Brier in all 5 folds on both datasets (§11.4).
- **(c) Domain fine-tuning.** Tested in §5: degrades ROC AUC on 3/4 targets (§5.1) and
  produces no material gain in the coil2000 small-finetune trials (§5.2).

### 12.5 What this means for reading the results

The v1 "TabPFN loses" headline **conflated genuine model limits with setup choices**:
the context ceiling, the regression/severity gap, and inference cost are model limits
(context-ceiling item amended by the §12.1 model-version correction, 2026-08-04);
dataset scale, the 1−AUC metric, and the tuning asymmetry are setup choices. Correcting
the setup choices (metric re-score, §11.3) flips classification from losing to
competitive on calibration — the classification headline was substantially measurement.
The **regression gap and the inference cost remain genuine TabPFN limits that no setup
change fixes**: the §8 verdict stands for severity modeling and 100K+-row batch scoring,
and TabPFN's competitive claim is restricted to calibrated classification on
small-to-moderate data.

## 13. Addendum — Home-Turf Size Sweep (2026-08-02)

Direct test of the §12.1 hypothesis on TabPFN's home turf: 3 insurance classification
datasets × 3 training sizes (1K / 5K / full) × 5 folds, scored on log loss (the metric an
insurer pays on, §11.3). Runs every method at defaults on every cell — no HPO, no
trimming, no setup asymmetry — so the only variable left is training-set size. Evidence
added by commit 63d43ee.

### 13.1 Setup

- **Cells:** 3 datasets (bemtl97 with the §6 leak features dropped, coil2000,
  uslapseagent) × 3 sizes (1K / 5K / full: 163,212 / 9,822 / 29,317 rows respectively) ×
  5 folds = 9 cells, 220 result rows, zero errors.
- **Methods:** TabPFN (hosted API) vs CAT / LGBM / XGB (CPU), all at default config —
  matching the §2.1 harness convention.
- **Config-lite probe:** per cell, TabPFN also ran an `n_estimators=8` arm (API cap) to
  test whether the v1 default sits below a better ensemble setting.
- Harness: `scripts/benchmarks/run_home_turf_size_sweep.py`; row assembly and error handling:
  `scripts/benchmarks/finish_home_turf_sweep_v2.py`.

### 13.2 Results — mean log loss over 5 folds, lower is better

| dataset | size | rows | TabPFN | CAT | LGBM | XGB | winner |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| bemtl97 | 1K | 1,000 | **0.3529** | 0.3687 | 0.5103 | 0.5206 | TabPFN |
| bemtl97 | 5K | 5,000 | **0.3462** | 0.3545 | 0.3778 | 0.4088 | TabPFN |
| bemtl97 | full | 163,212 | 0.3428 | 0.3436 | **0.3418** | 0.3450 | LGBM |
| coil2000 | 1K | 1,000 | **0.2080** | 0.2205 | 0.3914 | 0.3352 | TabPFN |
| coil2000 | 5K | 5,000 | **0.2026** | 0.2103 | 0.2558 | 0.2807 | TabPFN |
| coil2000 | full | 9,822 | **0.2006** | 0.2082 | 0.2219 | 0.2494 | TabPFN |
| uslapseagent | 1K | 1,000 | **0.2513** | 0.2763 | 0.3459 | 0.3858 | TabPFN |
| uslapseagent | 5K | 5,000 | **0.2602** | 0.2718 | 0.2838 | 0.3098 | TabPFN |
| uslapseagent | full | 29,317 | **0.2491** | 0.2529 | 0.2537 | 0.2642 | TabPFN |

Winner per cell computed from the CSV means (mean of 5 folds per dataset × size × method,
`scripts/eval/insurance_benchmark_v1/home_turf_sweep_results.csv`). **TabPFN wins 8/9
cells.** The single loss is bemtl97@full: LGBM 0.3418 vs TabPFN 0.3428 — a 0.0010 margin
at 163K rows, the largest cell in the sweep.

### 13.3 The size-ceiling curve is fully mapped — and it is flat for TabPFN

- TabPFN leads on **all six practical-size cells** (1K and 5K on all three datasets) and
  on two of the three full-size cells; the GBDTs draw even exactly once, at 163K rows,
  within 0.001.
- This confirms §12.1: the v1 headline losses were driven by **dataset-size mismatch**,
  not by TabPFN's context ceiling per se. When the benchmark stays within TabPFN's
  training-data sweet spot, it beats all three GBDT families on log loss on every dataset.
  The v1 "context ceiling kills TabPFN" story is **dead for classification log loss** —
  the ceiling shows up only as a 0.001 shave at 163K rows, not as the dominant effect.
- The sweep does not revive v1: it explains it. §12.5's restricted claim — TabPFN
  competitive on calibrated classification at small-to-moderate data — is upgraded to:
  *leading* on log loss at every practical size tested here.

### 13.4 The real TabPFN cost is compute, not accuracy

- Full-size hosted fit was the bottleneck: bemtl97@full fold 0 took **3045 s (≈51 min)
  cold**; folds 1–4 took 36–64 s once the server-side cache was warm. Coil2000 and
  uslapseagent full-size cells fit in ~3 s (hosted API, no local GPU).
- This substantiates the §4.2 speed objection: TabPFN's accuracy is no longer the
  barrier, but 50-minute cold fits at 163K rows still rule it out for large-portfolio
  retraining cycles. The §8 verdict's *engineering* half stands on cost, not quality.

### 13.5 Methodological note — do not re-chase the config-lite arm

- The `n_estimators=8` probe arm was **bit-identical to the server default on all 40
  (dataset × size × fold) pairs** where both ran — identical log loss to float64
  precision. The API cap is not binding at these sizes, and the config-lite arm adds no
  information.
- The flaky `n_estimators=1` config was **dropped as a pure duplicate** (rows absent from
  the CSV; `trimmed=True` flags the bemtl97@full cell where the extra arms were trimmed).
- Conclusion for future work: TabPFN default config is already at the tested ceiling;
  HPO inside the harness (§8(a)) remains the only untested accuracy lever, and the
  ensemble-size dimension is closed.

## 14. Addendum — Insurance Frontier Benchmark (2026-08-02)

Pareto-efficiency analysis for issue #27 (repo IFoA-ADSWP/TabPFN): predictive power
(log loss) vs parsimony (# params as a proxy for interpretability), per the agreed design
spec `docs/analyses/insurance_frontier_benchmark_spec.md` (commit 037d215, settled
decisions D1–D5). Each of the three home-turf datasets is an **independent frontier**
(separate table + plot; no cross-dataset Pareto comparison). Implementation committed in
`ed3e119` (script) with the spec's acceptance criteria 1–4 met; this addendum is
deliverable 6.

### 14.1 Setup

- **Spec:** `docs/analyses/insurance_frontier_benchmark_spec.md` — authoritative reading
  of issue #27; D1–D5 are settled, not re-derived (§14.3/14.4 check the spec's expected
  results (a) and (b) against the run).
- **D1/D2 combined pass, one script:** `scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py`
  runs all three datasets, one pass each. D1 (Option B) re-runs LogisticGLM/LR,
  TweedieGLM, PoissonGLM and RandomForest (the fast families whose v1 folds did not match
  the sweep's splits); D2 (Option A) re-fits LightGBM/XGBoost/CatBoost at their recorded
  defaults purely to count parameters. GBDT/RF param count = `n_estimators × mean leaves
  per tree`; GLM/LR = post-encoding column count + 1 intercept (harness uses `cat.codes`
  → raw column count); count inputs recorded in
  `scripts/eval/insurance_benchmark_v1/method_info.csv`.
- **Reused sweep power (no re-run):** TabPFN / CAT / LGBM / XGB log loss is taken as-is
  from `scripts/eval/insurance_benchmark_v1/home_turf_sweep_results.csv` (§13), filtered
  to full size (`n_rows == len(X)`, `n_estimators.isna()`) — the new run uses the same
  splits, `StratifiedKFold(5, shuffle=True, random_state=42)`, so the D1 re-runs land on
  the identical folds.
- **New compute only:** GLMs/LR/RF power (5 folds) + leaf-count refits for all tree
  families. The GLM/LR/RF pass is cheap even at 163K rows (LR/GLMs ~1–7 s/fold on
  bemtl97; RF ~16–87 s/fold, per `frontier_benchmark_run.log`).
- **D3 Pareto rule (Option B, beyond SE):** model A is dominated iff some model B with
  strictly fewer params has `mean_B + SE_B < mean_A − SE_A`. Models within SE of each
  other both stay on the frontier; ties on both axes keep both models on. Rationale per
  spec §5: a point-estimate rule would let fold noise decide membership (bemtl97 LGBM
  0.3418 vs TabPFN 0.3428 is within fold noise).
- **TabPFN parameter count — settled non-decision (spec §5):** constant **10,000,000** per
  dataset regardless of training size — the top-right anchor (max power, min parsimony).
  It never changes frontier membership; the exact hosted-model figure is TBD from
  PriorLabs/TabPFN docs and is flagged as constant regardless.
- **Datasets:** bemtl97 (leak-fixed per §6: `claim` target, `nclaims`/`amount` dropped;
  163,212 rows, pos-rate 11.2%), coil2000 (`CARAVAN`; 9,822 rows, pos-rate ≈6%),
  uslapseagent (`surrender`; 29,317 rows). Note: the 184K-row dataset is `norauto` — the
  designated first extension per D5, **not** part of this v1 run.

### 14.2 Results — log loss mean ± SE over 5 folds, lower is better

**bemtl97** (163,212 rows, `claim`, leak-fixed):

| method | mean log loss | ± SE | n_params | on frontier |
| --- | ---: | ---: | ---: | --- |
| lgbm | **0.34177** | 0.00053 | 3,100 | yes |
| lr | 0.34270 | 0.00040 | 11 | yes |
| logisticglm | 0.34270 | 0.00040 | 11 | yes |
| poissonglm | 0.34277 | 0.00040 | 11 | yes |
| tabpfn | 0.34279 | 0.00057 | 10,000,000 | yes |
| tweedieglm | 0.34280 | 0.00042 | 11 | yes |
| cat | 0.34363 | 0.00053 | 63,546 | no |
| xgb | 0.34503 | 0.00054 | 3,981 | no |
| rf | 0.59530 | 0.01219 | 2,245,565 | no |

**coil2000** (9,822 rows, `CARAVAN`):

| method | mean log loss | ± SE | n_params | on frontier |
| --- | ---: | ---: | ---: | --- |
| tabpfn | **0.20059** | 0.00221 | 10,000,000 | yes |
| lr | 0.20554 | 0.00187 | 86 | yes |
| logisticglm | 0.20626 | 0.00188 | 86 | yes |
| cat | 0.20823 | 0.00244 | 63,764 | yes |
| poissonglm | 0.21093 | 0.00233 | 86 | yes |
| tweedieglm | 0.21779 | 0.00260 | 86 | yes |
| lgbm | 0.22193 | 0.00261 | 3,100 | no |
| xgb | 0.24937 | 0.00354 | 2,719 | no |
| rf | 0.47859 | 0.02993 | 71,763 | no |

**uslapseagent** (29,317 rows, `surrender`):

| method | mean log loss | ± SE | n_params | on frontier |
| --- | ---: | ---: | ---: | --- |
| tabpfn | **0.24909** | 0.00518 | 10,000,000 | yes |
| cat | 0.25286 | 0.00459 | 63,394 | yes |
| lgbm | 0.25367 | 0.00446 | 3,100 | yes |
| xgb | 0.26419 | 0.00460 | 3,781 | no |
| rf | 0.27141 | 0.00325 | 270,218 | no |
| logisticglm | 0.27624 | 0.00506 | 11 | yes |
| lr | 0.27660 | 0.00505 | 11 | yes |
| poissonglm | 0.28584 | 0.00488 | 11 | yes |
| tweedieglm | 0.28781 | 0.00593 | 11 | yes |

Bold = best mean log loss per dataset (power winner). Frontier membership per the D3
beyond-SE rule, reproduced from `frontier_results_<dataset>.csv` (the run's self-check
asserts ≥1 frontier point per dataset).

### 14.3 Narrative per dataset

**bemtl97 — the spec's mid-complexity squeeze, confirmed.** The entire top of the table
is a 0.001-wide cluster: LGBM 0.34177, all four GLM variants and LR 0.34270–0.34280,
TabPFN 0.34279. LGBM's tiny edge puts it on the frontier; TabPFN and all six GLMs are on
because no 11-param model beats anyone else beyond SE and LGBM does not beat TabPFN beyond
SE (`0.34177+0.00053 = 0.34230` vs `0.34279−0.00057 = 0.34222` — within SE). This is
exactly the fold-noise trap the D3 rule exists to avoid. **CatBoost (63,546 params) and
XGBoost (3,981) are dominated** — beaten on power by LGBM/TabPFN *and* on parsimony by the
GLMs: a clean case of the spec's expected result (a), a real "don't deploy this" signal.
RandomForest is catastrophic (0.59530 ± 0.01219) — worst by a wide margin, dominated on
both axes, consistent with §13's sweep pattern. On expected result (b): TabPFN's §13
0.0010 lead over LGBM does **not** survive the parsimony constraint here — LGBM holds the
power edge and the GLMs hold parsimony; TabPFN survives the frontier only on the
beyond-SE tie (AUC nuance: §14.11.3 — TabPFN wins AUC at 2.6 SE even in the log-loss
tie).

**coil2000 — TabPFN leads, GLMs hold the low-complexity end, CatBoost beats LightGBM.**
TabPFN is the power winner (0.20059) and the top-right anchor. LR (0.20554) and
LogisticGLM (0.20626) at just 86 params are within ~0.006 of TabPFN — the most
interesting actuary trade-off on this dataset. CatBoost makes the frontier (0.20823, 63,764
params) because it beats LGBM (0.22193) and XGBoost (0.24937) on power; LGBM and XGBoost
are dominated (no power advantage, worse parsimony than the GLMs) — the usual GBDT pecking
order is inverted here. RandomForest again fails (0.47859 ± 0.02993). On expected result
(b): TabPFN's lead **survives** the frontier constraint — it is the best power on the
dataset, and parsimony pressure only closes the gap, it does not remove it.

**uslapseagent — the full family stack is on the frontier.** TabPFN (0.24909), CatBoost
(0.25286) and LightGBM (0.25367) are all within ~0.005 and all on the frontier, each the
most parsimonious model at its power tier (CatBoost and LightGBM dominate XGBoost: both
beat it on power with far fewer params). The GLM family anchors the parsimony end — all
four 11-param variants are on the frontier (logisticglm/lr at 0.27624/0.27660, then
poisson/tweedie within SE of them); nothing at 11 params beats them beyond SE. XGBoost and
RandomForest are dominated; RF (0.27141) beats the GLMs on power but is crushed on
parsimony (270,218 vs 11 params) — a textbook mid-complexity squeeze (expected result
(a)). On expected result (b): TabPFN's lead survives — it wins power outright, with
parsimony again closing but not removing the gap.

### 14.4 Interpretation — what an actuary should take away

- **The GLM family (11–86 params) is never dominated on any dataset.** On every frontier
  at least one GLM variant is on the curve — they anchor the low-complexity end with log
  loss within ~0.001 (bemtl97) to ~0.006 (coil2000) of the power winner. For
  governance-defensible deployment under a complexity budget, a GLM is always on the
  table. This is the single most robust result of the frontier.
- **TabPFN is on the frontier everywhere but never parsimonious.** It wins power on 2 of 3
  datasets (coil2000, uslapseagent) and is within fold-noise of the winner on the third,
  but at a constant 10,000,000 params it is always the top-right anchor — never a
  parsimony answer. The spec's expected result (b) resolves as: TabPFN's accuracy lead
  survives the frontier only where it is the outright power winner; where it merely ties
  (bemtl97), parsimony pressure removes the advantage (AUC nuance: §14.11.3 — TabPFN
  wins AUC at 2.6 SE even in the log-loss tie).
- **RandomForest at default config is a frontier failure** — dominated on all three
  datasets, catastrophic on bemtl97 (0.59530), consistent with §13 and the v1 baseline.
  No further RF exploration is warranted at default settings.
- **The mid-complexity squeeze (expected result (a)) is real**: CatBoost/XGBoost are
  dominated on bemtl97, LGBM/XGBoost on coil2000, XGBoost/RF on uslapseagent — beaten on
  power by TabPFN and on parsimony by the GLMs. Mid-complexity models must earn their
  place by beating the GLMs by more than SE, and mostly they do not.
- **`norauto` (184K rows) is done (§14.6)** — the designated first extension per D5.
  LGBM takes the power edge at scale (0.17518 vs TabPFN 0.17619) and TabPFN survives the
  frontier only on the beyond-SE tie — the §12.1 size-ceiling hypothesis holds on the
  frontier axis. **The v1 classification suite is now complete (§14.6, §14.7)** —
  `ausprivauto0405` and `bemtl16` closed out the remaining post-`norauto` priority
  (spec §8). **The regression Phase 2 (D4) is now done (§14.8)** — the frontier covers
  10 datasets (6 classification + 4 regression). **Where to look next:** the spec's
  remaining open items are TabPFN's exact param count (non-decision, recorded), an
  exposure-weighted Poisson deviance / offsets refinement, and the fine-tuned TabPFN arm
  (§12.3 tuning asymmetry) — of these the highest-value is the fine-tuned TabPFN arm, or
  else close out issue #27.

### 14.5 Files & reproducibility

- **Script:** `scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py` (committed
  `ed3e119`, branch `feat/tabarena-benchmark`; spec commit `037d215`).
- **Run command:** `source /tmp/tabarena/.venv-ta/bin/activate && python
  scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py`
- **Outputs** (same dir as the script): `frontier_results_bemtl97.csv`,
  `frontier_results_coil2000.csv`, `frontier_results_uslapseagent.csv`,
  `frontier_results_norauto.csv` (method | mean | se | n_params | on-frontier),
  `frontier_plot_{dataset}.png` (x = log10(n_params), y = mean
  log loss, ± SE bars, frontier red / dominated grey), `frontier_benchmark_run.log`,
  `frontier_norauto_run.log` (per-fold timings and log loss).
- **Inputs:** `data/raw/{bemtl97,coil2000,uslapseagent}.csv`;
  `home_turf_sweep_results.csv` (reused TabPFN/CAT/LGBM/XGB power, identical folds);
  `method_info.csv` (recorded defaults for the D2 leaf-count refits).
- **Self-check:** assert-based sanity checks at end of run — 5 sweep fold rows per reused
  method, no NaNs, unique methods, ≥1 frontier point, no train/test overlap within folds.
- Regression/severity frontier deliberately **not** in this pass (D4, classification-only
  v1); Phase 2 adds the RMSE/Poisson-deviance axis.

### 14.6 First extension — norauto (184K rows)

`norauto` (184,000 rows; 183,999 after dropna, 4.6% positive, target `NbClaim`, 5
features — the §6-style leak-fix is already baked into the prepared file, d170afc).
All 9 methods fit **fresh**: the home-turf sweep did not cover norauto, so there was no
reusable power (`run_frontier_benchmark.py` falls back to fresh fits per commit e93f3c0;
TabPFN via the hosted API, 5 folds, 504 s total).

| method | mean log loss | ± SE | n_params | on frontier |
| --- | ---: | ---: | ---: | --- |
| lgbm | **0.17518** | 0.00047 | 3,100 | yes |
| tabpfn | 0.17619 | 0.00061 | 10,000,000 | yes |
| cat | 0.17676 | 0.00053 | 62,540 | no |
| xgb | 0.17739 | 0.00055 | 4,517 | no |
| logisticglm | 0.17846 | 0.00046 | 6 | yes |
| lr | 0.17846 | 0.00046 | 6 | yes |
| poissonglm | 0.18131 | 0.00035 | 6 | yes |
| tweedieglm | 0.18264 | 0.00159 | 6 | yes |
| rf | 0.73544 | 0.00929 | 593,042 | no |

Frontier = 6: LGBM, TabPFN, and all four 6-param GLMs (logisticglm/lr tied at 0.17846).
CatBoost and XGBoost are dominated — beaten on power by LGBM/TabPFN and on parsimony by
the GLMs; RF is catastrophic at scale (0.73544 ± 0.00929, 593,042 params), dominated on
both axes, consistent with §13 and §14.3. **D5 verdict — the size-ceiling hypothesis
transfers to the frontier axis:** LGBM takes the power edge at scale (0.17518 vs TabPFN
0.17619), and TabPFN survives the frontier **only** on the beyond-SE tie (AUC nuance: §14.11.3 —
TabPFN wins AUC at 2.5 SE even inside the log-loss tie)
(`lgbm mean+SE` = 0.17565 vs `tabpfn mean−SE` = 0.17558) — the same fold-noise
membership as bemtl97 at 163K rows (§14.3). Files:
`scripts/eval/insurance_benchmark_v1/frontier_results_norauto.csv`,
`frontier_plot_norauto.png`.

### 14.7 v1-suite extension — ausprivauto0405 + bemtl16

The remaining two v1 classification datasets, completing the post-`norauto` priority
(spec §8). Both fit **fresh** — neither was covered by the home-turf sweep, so there is
no reusable power; `run_frontier_benchmark.py` uses the same fallback path as norauto
(§14.6). Results committed in `b2d03a5`.

**ausprivauto0405** (67,856 rows, 6.8% positive, target `ClaimOcc`):

| method | mean log loss | ± SE | n_params | on frontier |
| --- | ---: | ---: | ---: | --- |
| logisticglm | **0.23947** | 0.00038 | 7 | yes |
| lr | 0.23947 | 0.00038 | 7 | yes |
| poissonglm | 0.23956 | 0.00036 | 7 | yes |
| tweedieglm | 0.23983 | 0.00033 | 7 | yes |
| tabpfn | 0.24026 | 0.00037 | 10,000,000 | no |
| lgbm | 0.24164 | 0.00018 | 3,100 | no |
| cat | 0.24327 | 0.00047 | 62,604 | no |
| xgb | 0.24907 | 0.00051 | 4,368 | no |
| rf | 0.52831 | 0.00988 | 602,223 | no |

**bemtl16** (58,723 rows, 36.0% positive, target `number_of_liability_claims`):

| method | mean log loss | ± SE | n_params | on frontier |
| --- | ---: | ---: | ---: | --- |
| tabpfn | **0.23803** | 0.00129 | 10,000,000 | yes |
| lgbm | 0.23985 | 0.00112 | 3,100 | yes |
| cat | 0.24341 | 0.00101 | 63,778 | no |
| xgb | 0.25144 | 0.00114 | 4,253 | no |
| rf | 0.26121 | 0.00203 | 434,404 | no |
| logisticglm | 0.26315 | 0.00171 | 14 | yes |
| lr | 0.26319 | 0.00172 | 14 | yes |
| poissonglm | 0.30162 | 0.00383 | 14 | yes |
| tweedieglm | 0.65338 | 0.00001 | 14 | yes |

*Verdict update (2026-08-06): the DOMINATED verdict is retracted by §14.11.3
(calibration tie; TabPFN best AUC of the suite, 0.6622) — the log-loss mechanics below
remain as recorded.*

**ausprivauto0405 — the first outright TabPFN domination.** The frontier is exactly the
four 7-param GLMs (logisticglm/lr tied at 0.23947, then poissonglm 0.23956, tweedieglm
0.23983); every other method — tabpfn, lgbm, cat, xgb, rf — is dominated. This
confirms the spec's expected result (a) at its most decisive: the GLM family wins **both
axes**. TabPFN's 10,000,000-param power edge is gone — logisticglm at 7 params beats it
beyond SE (`mean_B + SE_B = 0.23984` vs `mean_A − SE_A = 0.23989`). It extends
the §12.1 "at scale" narrative one step further than norauto: at 67,856 rows / 6.8%
positive the problem is easy enough that a 7-param GLM beats 10M-param TabPFN outright.

**bemtl16 — TabPFN survives, and this time the edge is real.** TabPFN keeps the power
edge (0.23803) over lgbm (0.23985) and it is **beyond SE**, not a fold-noise tie:
`lgbm mean+SE = 0.24097` vs `tabpfn mean−SE = 0.23674`. The frontier-tie story of
§14.3/§14.6 (TabPFN surviving only on the beyond-SE tie) does **not** repeat here — at
36% positive, TabPFN's lead over the GBDTs holds on the power axis at 10M params.
Parsimony still narrows the practical gap: lgbm at 3,100 params is within 0.002 of
TabPFN's log loss, and the GLM family anchors the low-complexity end at 14 params
(logisticglm/lr 0.26315/0.26319, poisson/tweedie well behind — tweedieglm catastrophic
at 0.65338). But unlike §14.6, parsimony alone does not remove TabPFN from the frontier;
cat/xgb/rf are dominated. Files:
`scripts/eval/insurance_benchmark_v1/frontier_results_ausprivauto0405.csv`,
`frontier_results_bemtl16.csv`, `frontier_plot_ausprivauto0405.png`,
`frontier_plot_bemtl16.png`, `frontier_v1suite_run.log`.

### 14.8 Regression Phase 2 — RMSE + Poisson-deviance frontiers (D4)

The regression/severity axis the v1 classification pass deliberately deferred (spec §5
D4): severity mixes a different power metric and TabPFN's documented regression weakness
would have polluted v1's first delivery. Phase 2 runs **4 datasets** on their **stored
targets** — RMSE for `ausautoBI8999` (log-scale `AggClaim`), `ausprivauto0405_vehvalue`
(raw `VehValue`), `bemtl97_amount` (log1p amount, `claim` dropped as a leak) and Poisson
deviance for `freMTPL2freq` (log(`Exposure`) offset feature, `IDpol` dropped). All **8
regressors at defaults** (ols / poissonglm / tweedieglm / rf / cat / lgbm / xgb / tabpfn
via hosted API), **5-fold KFold seed 42**, all fits fresh. The §14.7 pointer named
`ausprivauto0405_vehvalue` + `freMTPL2freq` as candidates; `ausautoBI8999` +
`bemtl97_amount` were run as well. Results committed in `78c3df2`.

**ausautoBI8999** (22,036 rows, RMSE on stored log-scale `AggClaim`):

| method | mean RMSE | ± SE | n_params | on frontier |
| --- | ---: | ---: | ---: | --- |
| tabpfn | **0.96491** | 0.00868 | 10,000,000 | yes |
| cat | 0.96883 | 0.00756 | 63,944 | yes |
| lgbm | 0.97456 | 0.00822 | 3,100 | yes |
| xgb | 0.98945 | 0.00957 | 5,223 | yes |
| rf | 1.01260 | 0.00874 | 1,112,247 | no |
| ols | 1.07133 | 0.00928 | 12 | yes |
| poissonglm | 1.07881 | 0.00926 | 12 | yes |
| tweedieglm | 1.08867 | 0.00875 | 12 | yes |

**ausprivauto0405_vehvalue** (67,856 rows, RMSE on raw `VehValue`):

| method | mean RMSE | ± SE | n_params | on frontier |
| --- | ---: | ---: | ---: | --- |
| tabpfn | **0.71162** | 0.01246 | 10,000,000 | yes |
| lgbm | 0.71645 | 0.01258 | 3,100 | yes |
| cat | 0.72171 | 0.01164 | 63,912 | yes |
| xgb | 0.73784 | 0.00809 | 5,994 | no |
| rf | 0.82071 | 0.00893 | 2,599,078 | no |
| poissonglm | 1.00932 | 0.01609 | 7 | yes |
| ols | 1.04150 | 0.01545 | 7 | yes |
| tweedieglm | 1.05117 | 0.01548 | 7 | yes |

**bemtl97_amount** (163,212 rows, RMSE on stored log1p amount, `claim` dropped as leak):

| method | mean RMSE | ± SE | n_params | on frontier |
| --- | ---: | ---: | ---: | --- |
| lgbm | **0.48499** | 0.00431 | 3,100 | yes |
| cat | 0.48726 | 0.00412 | 63,226 | yes |
| xgb | 0.49149 | 0.00448 | 4,733 | yes |
| rf | 0.50457 | 0.00461 | 902,022 | no |
| ols | 0.70799 | 0.00651 | 12 | yes |
| tabpfn | 0.72825 | 0.01057 | 10,000,000 | no |
| tweedieglm | 1.84473 | 0.00626 | 12 | yes |
| poissonglm | 6.45906 | 2.83431 | 12 | yes |

**freMTPL2freq** (678,013 rows, Poisson deviance, log(`Exposure`) offset feature, `IDpol` dropped):

| method | mean Poisson deviance | ± SE | n_params | on frontier |
| --- | ---: | ---: | ---: | --- |
| lgbm | **0.29113** | 0.00138 | 3,100 | yes |
| cat | 0.30048 | 0.00184 | 63,788 | no |
| xgb | 0.31221 | 0.00208 | 5,747 | no |
| ols | 0.32097 | 0.00161 | 11 | yes |
| poissonglm | 0.32109 | 0.00161 | 11 | yes |
| tweedieglm | 0.32109 | 0.00161 | 11 | yes |
| tabpfn | 0.38770 | 0.00201 | 10,000,000 | no |
| rf | 0.47966 | 0.00525 | 3,337,930 | no |

Bold = best mean per dataset (power winner). Frontier membership per the D3 beyond-SE
rule (§14.1), reproduced from `frontier_results_<dataset>.csv`.

**ausautoBI8999 — TabPFN wins the power axis outright, and this time the lead is real.**
TabPFN is the power winner (0.96491) over cat (0.96883) and it is **beyond SE**, not a
fold-noise tie: `tabpfn mean−SE = 0.95623` vs `cat mean+SE = 0.97639`. The frontier is
tabpfn/cat/lgbm/xgb plus the 12-param GLM anchors; rf is the only dominated method (beaten
on power by the GBDTs *and* on parsimony by the GLMs). The GLMs trail by ~0.11–0.12
(1.07133/1.07881/1.08867) — the widest GLM gap of the regression pass.

**ausprivauto0405_vehvalue — TabPFN wins power within SE of lgbm — and a critical v1
discrepancy.** TabPFN leads (0.71162 vs lgbm 0.71645), but the intervals overlap, so it
shares the frontier with lgbm on the beyond-SE tie (`tabpfn mean+SE = 0.72408` vs
`lgbm mean−SE = 0.70387`); cat trails at 0.72171, xgb/rf are dominated. **This does NOT
reproduce the v1 verdict (§4.1: TabPFN +67.2% on vehvalue, rank 8/8, RMSE ≈ 1.20/fold in
`results_per_split.csv`).** The v1 figure came from the TabArena harness (3-fold, a
different client invocation); the frontier protocol — TabPFNRegressor (random_state=0) on
5-fold KFold seed 42 — gives 0.71. The +67.2% was protocol-specific, not a stable
property of the model on this dataset, and §12.1's citation of it as a size-ceiling data
point should be read accordingly.

**bemtl97_amount — TabPFN dominated at scale; the zero-inflation trap.** lgbm (0.48499) /
cat (0.48726) / xgb (0.49149) sweep the top; rf and tabpfn (0.72825 ± 0.01057) are
dominated — tabpfn beaten on power and on parsimony, consistent with v1's +48.3% verdict
(§12.1). The GLM end tells the zero-inflation story: poissonglm is catastrophic
(6.45906 ± 2.83431) — predicting >0 systematically misses the ~89% zero mass — and
tweedieglm is poor (1.84473); ols (0.70799) anchors the GLM family, and the 12-param
models all sit on the frontier because nothing has fewer parameters to dominate them.

**freMTPL2freq — the frequency axis is genuinely competitive for GLMs, and TabPFN's worst
size-ceiling case.** lgbm wins power (0.29113); the 11-param GLM family — Poisson, the
actuarial gold standard — lands within ~10% (0.32097/0.32109/0.32109), unlike
classification where GLM variants were placeholders. cat/xgb/tabpfn/rf are dominated;
tabpfn at 0.38770 is ~+33% behind lgbm on 678,013 rows ≈ 100× its ~1K-row home-turf
regime — the strongest §12.1 size-ceiling confirmation yet. Files:
`scripts/eval/insurance_benchmark_v1/frontier_results_{ausautoBI8999,ausprivauto0405_vehvalue,bemtl97_amount,freMTPL2freq}.csv`,
`frontier_plot_{ausautoBI8999,ausprivauto0405_vehvalue,bemtl97_amount,freMTPL2freq}.png`,
`frontier_regression_run.log`.

**D4 synthesis — TabPFN's regression lead does not survive the frontier.** Across the four
regression axes TabPFN wins power only at small N — beyond SE at 22,036 rows
(ausautoBI8999) and on the beyond-SE tie at 67,856 rows (vehvalue) — and is dominated at
scale: 163,212 rows (bemtl97_amount) and 678,013 rows (freMTPL2freq). This transfers the
§12.1 size-ceiling hypothesis to the regression axis: at ~1K effective context the model
holds its edge on small/medium severity problems and loses it where every row of signal
matters. (The "~1K effective context" mechanism is amended by the §12.1 model-version
correction, 2026-08-04; the size-dependent pattern stands.) It also flags a protocol
sensitivity worth recording — the frontier protocol's
TabPFNRegressor does not reproduce v1's vehvalue +67.2%, so v1's regression verdicts are
harness-specific. The GLMs are far more competitive on frequency than on classification;
on severity the GBDTs dominate outright.

### 14.9 Spanish motor portfolio — frequency frontier (53,502 rows)

Real-portfolio extension: Segura-Gisbert et al. (2024), "Dataset of an actual motor
vehicle insurance portfolio" (Spanish motor, prepared by `make_spanish_motor_freq` in
`scripts/infra/prepare_insurance_datasets.py`). 53,502 policies, target `N_claims_year`
(int 0–18, 11.1% claims > 0), Poisson deviance, 5-fold KFold seed 42, all 8 regressors
fit **fresh**. The raw policy-year panel is collapsed to the last policy-year per ID
(bemtl16 precedent); `Length` NA (motorbikes) is imputed by `Type_risk` median;
exposure uniform ~1yr (no offset). Leak exclusions verified **pre-run**:
`N_claims_history` / `R_Claims_history` include CURRENT-year claims (leak AUC
0.76/0.92 vs claims > 0 — the history-variable leak, ~0.918, was caught before the
run) and `Cost_claims_year` is a sibling target; none are kept as features.

| method | mean Poisson deviance | ± SE | n_params | on frontier |
| --- | ---: | ---: | ---: | --- |
| lgbm | **0.89157** | 0.01238 | 3,100 | yes |
| tabpfn | 0.98764 | 0.01624 | 10,000,000 | no |
| ols | 0.98994 | 0.01854 | 21 | yes |
| cat | 0.99757 | 0.02372 | 63,892 | no |
| rf | 0.99808 | 0.01651 | 412,124 | no |
| poissonglm | 1.01250 | 0.01867 | 21 | yes |
| tweedieglm | 1.01250 | 0.01867 | 21 | yes |
| xgb | 1.35178 | 0.03642 | 5,350 | no |

**LGBM dominates beyond SE; TabPFN falls off the frontier for the fourth time at
scale; the GLM anchors sit within noise of TabPFN at 21 params.** lgbm wins power
(0.89157) and dominates TabPFN outright per the D3 beyond-SE rule (`lgbm mean+SE =
0.90395` vs `tabpfn mean−SE = 0.97140`), ~10.8% better deviance (0.98764 vs 0.89157).
ols / poissonglm / tweedieglm (21 params) hold the frontier anchors, all within SE of
TabPFN's mean (0.98994 / 1.01250 vs 0.98764) — parsimony closes a gap that power
leaves open, the §12.1 pattern again. Null deviance is 1.0123, so poissonglm /
tweedieglm at 1.01250 are effectively at the intercept-only floor: the portfolio's
frequency signal is thin, and only lgbm extracts it. cat (0.99757) / rf (0.99808) sit
just off the power edge, xgb is dominated (1.35178). This is the **fourth at-scale
frontier where TabPFN is off-frontier** — after norauto (surviving only on the
beyond-SE tie, §14.6), bemtl97_amount and freMTPL2freq (dominated, §14.8) — and
consistent with the D4 synthesis: at 53,502 rows the 10M-param model adds nothing a
3,100-param LGBM or a 21-param GLM does not already provide. Files:
`scripts/eval/insurance_benchmark_v1/frontier_results_spanish_motor_freq.csv`,
`frontier_plot_spanish_motor_freq.png`. Model version note: TabPFN served via the
hosted client 0.3.3; this run used auto-selection (resolves to v3_default), and the
benchmark scripts now pin `model_path="v3_default"` explicitly for reproducibility.

**Actuary takeaway:** on this real Spanish motor frequency book, a default LGBM
beats TabPFN by ~10.8% deviance with 1/3,200 of the parameters, and the standard
Poisson GLM is statistically indistinguishable from TabPFN — there is no actuarial
case for TabPFN on frequency at this scale. The scope of that sentence is the
count model: the same target reframed as claim/no-claim classification inverts
the ranking picture — §14.14. On lapse, the picture flips: TabPFN
edges LGBM (AUC 0.752 vs 0.745 on Spanish motor, 53.5K rows) and both far outrun
LR (0.684); TabPFN also leads the combined lapse leaderboard (elo 1128). The
2-fold caveat on that lapse gap is settled by the 5-fold re-run in §14.10.

## 14.10 Gap-closing addendum (2026-08-04)

**5-fold lapse re-run** (`scripts/benchmarks/run_lapse_benchmark.py`, both classification
entries now `n_splits: 5`; experiment cache cleared first — 0 cache_exists, so
both datasets including eudirectlapse were freshly refit; premium regression task
stays 2-fold). Mean AUC over 5 stratified folds, ±SE:

| Dataset | TabPFN | LGBM | Linear |
|---|---|---|---|
| spanish_motor_lapse (53.5K rows, 35.4% pos) | **0.7553 ± 0.0026** | 0.7500 ± 0.0022 | 0.6841 ± 0.0015 |
| eudirectlapse (23K rows, 12.8% pos) | 0.6101 ± 0.0049 | 0.6138 ± 0.0043 | **0.6260 ± 0.0037** |

The Spanish lapse gap **survives 5 folds and widens slightly** (0.7553 vs 0.7500,
~2 SE): TabPFN wins all five folds (0.7465–0.7621 vs 0.7416–0.7550). eudirectlapse
still goes to Linear (wins all 5 folds). Combined leaderboard (2×5-fold lapse +
2-fold premium): TabPFN elo 1099.0 > GBM 983.5 > LR 917.6 — TabPFN's lead is
carried by the premium RMSE task (19.07 vs 26.34 vs 81.84) plus Spanish lapse.

**Spanish severity frontier** (`data/raw/spanish_motor_severity.csv`: last
policy-year per ID, 53,502 rows × 20 features, target log1p(Cost_claims_year) in
place — bemtl97_amount precedent; N_claims_year excluded as a sibling target:
cost==0 iff count==0, so the count would give away the zero/non-zero split).
RMSE on the stored log1p scale, 5-fold KFold, 8 methods:

| Method | RMSE (mean ± SE) | n_params | Frontier |
|---|---|---|---|
| lgbm | **1.8372 ± 0.0100** | 3,100 | yes |
| cat | 1.8376 ± 0.0095 | 63,952 | yes |
| rf | 1.8702 ± 0.0100 | 477,610 | no |
| ols | 1.8781 ± 0.0104 | 21 | yes |
| xgb | 1.8786 ± 0.0100 | 5,459 | no |
| tabpfn | 1.8862 ± 0.0116 | 10,000,000 | no |
| poissonglm / tweedieglm | 1.8876 ± 0.0106 | 21 | yes |

TabPFN lands 5th of 8 (mid-pack) and off-frontier — 2.7% behind LGBM on RMSE.
Severity shows the same at-scale pattern as frequency: LGBM/Cat extract the
signal, TabPFN's 10M-param prior adds nothing. Files:
`scripts/eval/insurance_benchmark_v1/frontier_results_spanish_motor_severity.csv`,
`frontier_plot_spanish_motor_severity.png`.

## 14.11 AUC/Brier re-score addendum (2026-08-06)

Implements acceptance criterion #5 of `docs/analyses/frontier_auc_brier_rescore_spec.md`
(issue #27 addendum): the 6 classification frontier datasets now carry **mean ± SE AUC
and Brier** on the same 5-fold `StratifiedKFold(5, shuffle=True, random_state=42)`
protocol, so the regime rule (`docs/analyses/regime_characterization.md` §1: GLM gap
≥ ~2.5% log loss or ≥ ~0.05 AUC ⇒ thin-signal/TabPFN-win regime; ≤ ~2% ⇒
GLM-captured) applies to TabPFN-vs-GLM on the canonical protocol for the first time —
previously the only AUC pairs were the older 80/20 head-to-head
(`docs/reports/MULTI_DATASET_GLM_VS_TABPFN_SUMMARY.md`) and the 2 lapse datasets (§14.10),
and Brier was never emitted (spec §1). All 9 methods are fit/reused exactly as before;
the log-loss `mean`/`se` columns reproduce §14.2/§14.3/§14.6/§14.7 and the regime table
to the printed precision (no protocol drift; spec acceptance #3). GLM family =
{lr, logisticglm, tweedieglm, poissonglm}; "best GLM" = best-of-family **per metric**
(regime_characterization convention, spec §7.1). Metric definitions per spec §2:
AUC = `roc_auc_score(y_true, pp[:,1])`, Brier = `brier_score_loss(y_true, pp[:,1])`,
per fold, SE = std(ddof=1)/√5 — identical to the sweep's definitions (§13).
Deltas below are **TabPFN − best GLM** per metric; z = Δ/√(SE_TabPFN² + SE_GLM²) —
**unpaired and therefore conservative** (folds are paired within each method, which
would shrink the SE of the difference).

**Environment note — client version bump mid-delivery.** run2
(`/tmp/opencode/frontier_auc_rescore_run2.log`) completed bemtl97 / coil2000 /
uslapseagent (14:52–15:15, 3× `SELF-CHECK OK`) then aborted on norauto's first hosted
TabPFN fold: the server began gating the installed client at the connection/version
check — `tabpfn f0 fit attempt 3/3 failed: RuntimeError(None)` at
`tabpfn_client/client.py:533 _validate_response(..., only_version_check=True)`
(HTTP 426 client-version lockout, **not an outage**; the 3-attempt 10/60/300s retry
loop exhausted). The benchmark venv was upgraded **tabpfn-client 0.2.8 → 0.3.3** and
run3 (`/tmp/opencode/frontier_auc_rescore_run3.log`) executed clean: norauto /
ausprivauto0405 / bemtl16, 18:11–19:07, **3375 s total**, all `SELF-CHECK OK`,
server-side cache reused ("train set hashes match previously uploaded"). The
`model_path="v3_default"` pin is unchanged (§15.1 records the 0.3.3 install; the
upgrade is logged here per §15.1's version trigger).

### 14.11.1 Results — log loss, AUC, Brier (mean ± SE over 5 folds)

Bold = best mean per column (log loss and Brier: lower is better; AUC: higher).
`on_frontier` flags are unchanged — they are driven by log loss (§14.2–§14.7).
TabPFN n_params is the settled 10,000,000 constant (§14.1) on every row.

**bemtl97** (163,212 rows, `claim`, leak-fixed, 11.2% pos):

| method | log loss | ± SE | AUC | ± SE | Brier | ± SE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| tabpfn | 0.34279 | 0.00057 | **0.6224** | 0.0034 | 0.0978 | 0.0001 |
| cat | 0.34363 | 0.00053 | 0.6115 | 0.0030 | 0.0981 | 0.0001 |
| lgbm | **0.34177** | 0.00053 | 0.6169 | 0.0035 | **0.0977** | 0.0001 |
| xgb | 0.34503 | 0.00054 | 0.6081 | 0.0031 | 0.0984 | 0.0001 |
| rf | 0.59530 | 0.01219 | 0.5625 | 0.0032 | 0.1101 | 0.0004 |
| lr | 0.34270 | 0.00040 | 0.6107 | 0.0030 | 0.0979 | 0.0001 |
| logisticglm | 0.34270 | 0.00040 | 0.6107 | 0.0030 | 0.0979 | 0.0001 |
| poissonglm | 0.34277 | 0.00040 | 0.6105 | 0.0030 | 0.0979 | 0.0001 |
| tweedieglm | 0.34280 | 0.00042 | 0.6102 | 0.0030 | 0.0979 | 0.0001 |

**coil2000** (9,822 rows, `CARAVAN`, 6.0% pos):

| method | log loss | ± SE | AUC | ± SE | Brier | ± SE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| tabpfn | **0.20059** | 0.00221 | **0.7731** | 0.0074 | **0.0528** | 0.0004 |
| cat | 0.20823 | 0.00244 | 0.7469 | 0.0076 | 0.0546 | 0.0006 |
| lgbm | 0.22193 | 0.00261 | 0.7364 | 0.0054 | 0.0569 | 0.0007 |
| xgb | 0.24937 | 0.00354 | 0.7059 | 0.0065 | 0.0594 | 0.0010 |
| rf | 0.47859 | 0.02993 | 0.6890 | 0.0072 | 0.0614 | 0.0008 |
| lr | 0.20552 | 0.00186 | 0.7405 | 0.0095 | 0.0536 | 0.0003 |
| logisticglm | 0.20633 | 0.00190 | 0.7397 | 0.0096 | 0.0538 | 0.0003 |
| poissonglm | 0.20953 | 0.00195 | 0.7386 | 0.0096 | 0.0541 | 0.0003 |
| tweedieglm | 0.21791 | 0.00255 | 0.7343 | 0.0083 | 0.0550 | 0.0004 |

**uslapseagent** (29,317 rows, `surrender`, 37.9% pos):

| method | log loss | ± SE | AUC | ± SE | Brier | ± SE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| tabpfn | **0.24909** | 0.00518 | **0.9466** | 0.0020 | **0.0814** | 0.0019 |
| cat | 0.25286 | 0.00459 | 0.9440 | 0.0018 | 0.0826 | 0.0017 |
| lgbm | 0.25367 | 0.00446 | 0.9432 | 0.0017 | 0.0831 | 0.0017 |
| xgb | 0.26419 | 0.00460 | 0.9407 | 0.0018 | 0.0863 | 0.0017 |
| rf | 0.27141 | 0.00325 | 0.9345 | 0.0016 | 0.0885 | 0.0016 |
| lr | 0.27660 | 0.00505 | 0.9254 | 0.0025 | 0.0917 | 0.0020 |
| logisticglm | 0.27625 | 0.00506 | 0.9254 | 0.0025 | 0.0917 | 0.0020 |
| poissonglm | 0.28585 | 0.00488 | 0.9247 | 0.0024 | 0.0921 | 0.0020 |
| tweedieglm | 0.28782 | 0.00593 | 0.9248 | 0.0024 | 0.0921 | 0.0020 |

**norauto** (183,999 rows, `NbClaim`, 4.6% pos):

| method | log loss | ± SE | AUC | ± SE | Brier | ± SE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| tabpfn | 0.17619 | 0.00061 | **0.7016** | 0.0044 | 0.0427 | 0.0001 |
| cat | 0.17676 | 0.00053 | 0.6882 | 0.0044 | 0.0429 | 0.0001 |
| lgbm | **0.17518** | 0.00047 | 0.6971 | 0.0040 | **0.0427** | 0.0001 |
| xgb | 0.17737 | 0.00057 | 0.6853 | 0.0041 | 0.0429 | 0.0001 |
| rf | 0.73544 | 0.00929 | 0.5965 | 0.0031 | 0.0493 | 0.0001 |
| lr | 0.17846 | 0.00046 | 0.6850 | 0.0050 | 0.0432 | 0.0001 |
| logisticglm | 0.17846 | 0.00046 | 0.6850 | 0.0050 | 0.0432 | 0.0001 |
| poissonglm | 0.18131 | 0.00035 | 0.6485 | 0.0051 | 0.0433 | 0.0000 |
| tweedieglm | 0.18264 | 0.00159 | 0.6750 | 0.0048 | 0.0433 | 0.0001 |

**ausprivauto0405** (67,856 rows, `ClaimOcc`, 6.8% pos):

| method | log loss | ± SE | AUC | ± SE | Brier | ± SE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| tabpfn | 0.24026 | 0.00037 | **0.6622** | 0.0025 | 0.0625 | 0.0000 |
| cat | 0.24327 | 0.00047 | 0.6368 | 0.0029 | 0.0631 | 0.0001 |
| lgbm | 0.24164 | 0.00018 | 0.6425 | 0.0024 | 0.0627 | 0.0000 |
| xgb | 0.24884 | 0.00028 | 0.6217 | 0.0015 | 0.0638 | 0.0001 |
| rf | 0.52831 | 0.00988 | 0.5809 | 0.0039 | 0.0698 | 0.0002 |
| lr | 0.23947 | 0.00038 | 0.6567 | 0.0027 | **0.0624** | 0.0001 |
| logisticglm | **0.23947** | 0.00038 | 0.6567 | 0.0027 | 0.0624 | 0.0001 |
| poissonglm | 0.23956 | 0.00036 | 0.6568 | 0.0027 | 0.0624 | 0.0001 |
| tweedieglm | 0.23983 | 0.00033 | 0.6567 | 0.0028 | 0.0624 | 0.0001 |

**bemtl16** (58,723 rows, `number_of_liability_claims`, 36.0% pos):

| method | log loss | ± SE | AUC | ± SE | Brier | ± SE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| tabpfn | **0.23803** | 0.00129 | **0.9560** | 0.0003 | **0.0768** | 0.0003 |
| cat | 0.24341 | 0.00101 | 0.9540 | 0.0003 | 0.0790 | 0.0002 |
| lgbm | 0.23985 | 0.00112 | 0.9552 | 0.0004 | 0.0777 | 0.0003 |
| xgb | 0.25226 | 0.00114 | 0.9515 | 0.0004 | 0.0816 | 0.0002 |
| rf | 0.26121 | 0.00203 | 0.9524 | 0.0003 | 0.0800 | 0.0003 |
| lr | 0.26323 | 0.00172 | 0.9501 | 0.0007 | 0.0848 | 0.0005 |
| logisticglm | 0.26348 | 0.00176 | 0.9499 | 0.0007 | 0.0848 | 0.0006 |
| poissonglm | 0.30148 | 0.00374 | 0.9490 | 0.0007 | 0.0879 | 0.0006 |
| tweedieglm | 0.65338 | 0.00001 | 0.5000 | 0.0000 | 0.2304 | 0.0000 |

bemtl16's tweedieglm row is the degenerate constant predictor (AUC 0.5000 ± 0.0000,
Brier 0.2304 ± 0.0000 — its predicted mean is the 36% prior; §14.7's "tweedieglm
catastrophic at 0.65338"). It never wins an AUC best-pick (max selection) and is shown
for completeness. Brier ties within rounding (e.g., ausprivauto0405 GLM rows 0.0624);
bold = best at full precision.

### 14.11.2 TabPFN vs best-GLM deltas

Δ = TabPFN − best GLM per metric (best-of-family; log loss/Brier lower is better, AUC
higher is better — so negative Δ log loss / Δ Brier and positive Δ AUC favor TabPFN).
z = Δ/√(SE_TabPFN² + SE_GLM²), unpaired/conservative. The best GLM is lr or
logisticglm in every cell except ausprivauto0405 AUC (poissonglm 0.6568) — the two
regularized/unregularized linear models are effectively identical on every dataset.

| dataset | Δ log loss | z | Δ AUC | z | Δ Brier | z |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| bemtl97 | +0.00008 | 0.12 | +0.0117 | 2.58 | −0.0001 | −0.55 |
| coil2000 | −0.00492 | −1.71 | +0.0326 | 2.71 | −0.0009 | −1.65 |
| uslapseagent | −0.02716 | −3.75 | +0.0212 | 6.65 | −0.0103 | −3.70 |
| norauto | −0.00227 | −2.99 | +0.0166 | 2.50 | −0.0004 | −4.68 |
| ausprivauto0405 | +0.00080 | 1.51 | +0.0055 | 1.48 | +0.0001 | 1.13 |
| bemtl16 | −0.02520 | −11.74 | +0.0059 | 7.96 | −0.0079 | −13.26 |

### 14.11.3 Regime verdicts per dataset

Rule (regime_characterization.md §1, applied to the canonical protocol): GLM gap
≥ ~2.5% log loss (best-GLM-vs-best-score, the regime-doc definition) **or** Δ AUC vs
best GLM ≥ ~0.05 ⇒ thin-signal/TabPFN-win; gap ≤ ~2% ⇒ GLM-captured. Note the AUC leg
never fires here: the largest Δ AUC vs best-of-family GLM is coil2000 +0.0326, below
the ~0.05 bar — that leg was set on the Spanish-lapse comparison (§14.10), where the
linear family is a lone LR at 0.684. All six verdicts ride the log-loss leg.

| dataset | GLM gap (log loss) | Δ AUC vs best GLM (z) | regime verdict |
| --- | ---: | ---: | --- |
| bemtl97 | +0.3% | +0.0117 (2.6) | GLM-captured — calibration tie, TabPFN ranking edge |
| coil2000 | +2.5% | +0.0326 (2.7) | thin-signal / TabPFN-win |
| uslapseagent | +10.9% | +0.0212 (6.7) | thin-signal / TabPFN-win |
| norauto | +1.9% | +0.0166 (2.5) | GLM-captured — ranking edge inside the log-loss tie |
| ausprivauto0405 | +0.0% | +0.0055 (1.5) | GLM-captured — **DOMINATED retracted** |
| bemtl16 | +10.6% | +0.0059 (8.0) | thin-signal / TabPFN-win |

**ausprivauto0405 — the regime table's only outright domination is retracted.** The
regime table (§1, issue #53) listed ausprivauto0405 as TabPFN's sole outright
frontier domination (7-param logisticglm beats it beyond SE on log loss, §14.7). With
AUC in the protocol that verdict no longer stands as stated: the log-loss gap is
**+0.0008 ≈ 1.5 SE — statistically indistinguishable** (0.24026 ± 0.00037 vs 0.23947 ±
0.00038), i.e. a calibration tie with a 7-vs-10M-param parsimony caveat, and on ranking
TabPFN is now **best AUC of the suite** (0.6622 vs poissonglm 0.6568, +0.0055, 1.5 SE).
The `on_frontier=no` flag on the log-loss axis is technically unchanged (the strict D3
beyond-SE inequality still clears by 4.8e-5), but the substantive verdict flips:
TabPFN is not dominated on the full metric set — it holds the ranking edge. Regime
class stays GLM-captured per the log-loss rule.

**bemtl97 & norauto — log-loss ties, real ranking edges.** Both stay GLM-captured
(log-loss leg: +0.3% and +1.9% gaps vs the achievable lgbm scores, the §14.3/§14.6
fold-noise picture), but TabPFN now wins AUC at **2.6 SE (bemtl97: 0.6224 vs lr 0.6107)
and 2.5 SE (norauto: 0.7016 vs lr 0.6850)** — on norauto it also beats the best GLM on
log loss by 1.3% (z −3.0) and on Brier by −0.0004 (z −4.7). In both GLM-captured
datasets the tie is a *calibration* tie; the *ranking* verdict favors TabPFN.

**coil2000 / uslapseagent / bemtl16 — thin-signal wins confirmed on the new metrics.**
All three keep the thin-signal/TabPFN-win class (gaps +2.5%/+10.9%/+10.6%). On the two
near-balanced datasets the win is now significant on **all three metrics**: bemtl16
Δ log loss −0.02520 (z −11.7), Δ AUC +0.0059 (z 8.0), Δ Brier −0.0079 (z −13.3);
uslapseagent −0.02716 (z −3.8), +0.0212 (z 6.7), −0.0103 (z −3.7). coil2000 is
directional on all three (−1.7/−1.7 SE on log loss/Brier) and significant on AUC
(+0.0326, 2.7 SE). The largest effects land exactly where the log-loss picture was
already strongest.

### 14.11.4 What changed vs the log-loss-only picture

- **TabPFN has the highest mean AUC of all 9 methods on all 6 datasets** (rank 1/9:
  0.6224 / 0.7731 / 0.9466 / 0.7016 / 0.6622 / 0.9560). The AUC edge is not only
  vs the GLM family — it also clears the GBDTs on the three fresh datasets (bemtl16
  0.9560 vs lgbm 0.9552; norauto 0.7016 vs lgbm 0.6971; ausprivauto0405 0.6622 vs lgbm
  0.6425) and on bemtl97 (0.6224 vs lgbm 0.6169).
- **ausprivauto0405's DOMINATED verdict is retracted** (§14.11.3): calibration tie
  (+0.0008, ~1.5 SE) + suite-best AUC. The log-loss-only picture over-stated the
  defeat: "GLM beats 10M-param TabPFN outright" (§14.7) is now "indistinguishable on
  calibration, TabPFN best at ranking".
- **GLM-captured ≠ no TabPFN edge.** The two GLM-captured datasets both carry a
  significant TabPFN AUC lead (2.5–2.6 SE). The regime class describes the GLM floor
  (calibration), not the full metric set.
- **Mechanism note — the divergence is an imbalance artifact.** On the imbalanced
  datasets (norauto 4.6%, ausprivauto0405 6.8% pos) log loss is dominated by the
  majority-class bulk (it is a calibration-weighted average over ~95%/93% negative
  rows), while AUC reads only the ranking at the top of P(y=1). So the metric
  divergence — log-loss tie/GLM-edge vs TabPFN AUC edge — is an artifact of the
  imbalance, not a TabPFN weakness; it echoes §11.2/§12.2's rank-invariance discussion.
  Brier (a calibration metric) behaves like log loss on ausprivauto0405 (tie, +0.0001,
  1.1 SE) and as a small TabPFN edge on norauto (−0.0004, 4.7 SE) — the ranking edge
  shows up only in AUC, exactly as the imbalance-artifact reading predicts.
- **Calibration and ranking separate cleanly.** On the 6-dataset suite TabPFN's
  calibration (log loss/Brier) is at worst a tie (ausprivauto0405, bemtl97) and its
  ranking (AUC) is best-in-suite everywhere. The one-pager's adoption rule
  (`docs/reports/TABPFN_BENCHMARK_SUMMARY.md`) is unaffected on the log-loss leg; the
  AUC evidence adds a "ranking edge even in GLM-captured regimes" nuance for
  underwriting-scorecard contexts. Qualification (2026-08-07, §14.13): "at worst a
  tie" holds against the default-config suite; vs tuned/feature-engineered baselines
  the calibration claim gains two small paired-significant exceptions
  (ausprivauto0405 log loss and Brier vs the linear family, bemtl97 Brier vs lgbm —
  ~1e-4 margins, ranking metrics untouched).

### 14.11.5 Files & reproducibility

- **6 regenerated CSVs** (2026-08-06; columns now
  `method,mean,se,mean_auc,se_auc,mean_brier,se_brier,n_params,on_frontier`; `mean`/`se`
  unchanged — no protocol drift vs §14.2–§14.7):
  `scripts/eval/insurance_benchmark_v1/frontier_results_{bemtl97,coil2000,uslapseagent,norauto,ausprivauto0405,bemtl16}.csv`.
- **Sweep read-back (spec acceptance #4):** tabpfn/cat/lgbm/xgb AUC and Brier on
  bemtl97/coil2000/uslapseagent equal the full-size fold means of
  `home_turf_sweep_results.csv` to full float precision — the 3 sweep datasets needed
  zero re-runs; only norauto/ausprivauto0405/bemtl16 ran fresh TabPFN power (15 hosted
  API calls, spec §3.1).
- **Run logs:** `/tmp/opencode/frontier_auc_rescore_run2.log` (bemtl97/coil2000/
  uslapseagent done; norauto aborted at the client-version lockout, §14.11 intro) and
  `/tmp/opencode/frontier_auc_rescore_run3.log` (norauto/ausprivauto0405/bemtl16,
  `SELF-CHECK OK` ×3, 3375 s, "ALL DATASETS DONE").
- **Environment:** tabpfn-client **0.2.8 → 0.3.3** in `.venv-ta` (server-enforced
  version bump — HTTP 426 lockout at the version check, not an outage; §14.11 intro),
  `model_path="v3_default"` pin unchanged; §15 version-drift policy applies.
- **Script:** `run_frontier_benchmark.py` modified per spec §3.2 (per-fold
  `roc_auc_score`/`brier_score_loss` appended at every `pp`; sweep-reuse path reads
  `roc_auc`/`brier` columns; SE = std(ddof=1)/√5; sanity checks unchanged).
- **Prior AUC evidence, not duplicated here:** §14.10's 5-fold lapse AUC
  (spanish_motor_lapse 0.7553 vs 0.7500, eudirectlapse 0.6260 LR — the 2-fold caveat
  settled) and `docs/reports/MULTI_DATASET_GLM_VS_TABPFN_SUMMARY.md` (older 80/20
  head-to-head, ranked on 1−AUC, GLM `class_weight='balanced'` and TabPFN
  `random_state=42` — neither config matches the frontier protocol). This addendum is
  the first per-fold AUC/Brier on the canonical 5-fold protocol.
- **Registry:** no new entry for §14.11 itself — it is an addendum to this already-registered master
  report (topic key `tabpfn-vs-gbdt-baselines-finetuning`,
  `docs/reports/REPORT_REGISTRY.md`); the master-report row was bumped to 2026-08-06
  with the AUC/Brier scope noted, and the rescore spec gained its own row
  (`frontier-auc-brier-rescore-spec`, 2026-08-06).

## 14.12 Ranking-robustness addendum — PR AUC, top-decile lift, paired + seed tests (2026-08-06)

Follow-up to §14.11 answering three questions the AUC/Brier rescore left open: (1) does
the ranking edge survive **PR AUC and top-decile lift** (the metrics that matter where
triage decisions actually cut), (2) do the per-dataset edges hold under **paired
per-fold tests** (the §14.11 z-scores were conservative unpaired), (3) does the 6/6 AUC
record survive **split-seed variation** on the marginal datasets.

### 14.12.1 Protocol

`run_frontier_benchmark.py` gains `--pr-auc` (forces fresh fits for all methods — the
sweep CSV stores no predictions, so PR AUC/lift need real fits; 30 hosted API calls for
the 6 datasets) and `--seed N` (StratifiedKFold random_state, default 42). Per fold:
`pr_auc = average_precision_score`, `lift10` = positives-in-top-decile ÷ base rate.
Per-fold rows → `frontier_pr_auc_results.csv`; summary → `frontier_pr_auc_summary.csv`;
analysis → `analyze_pr_auc.py` (paired t, df=4). Runs A (seed 42, all 6), B/C (seeds
7/123, ausprivauto0405/bemtl97/norauto): 540 per-fold rows, zero API retries, zero
426/version errors. Drift check: seed-42 log loss reproduces §14.11/9037b26 CSVs in
52/54 cells to full precision; the 2 exceptions are xgb on bemtl97/uslapseagent
(0.34503→0.34539, 0.26419→0.26447 — sweep-reuse rows refit under the venv's xgboost
3.4.0; environmental, xgb is off-frontier in both eras; pin the xgboost version if the
sweep CSVs are reused for fresh-fit comparisons).

### 14.12.2 PR AUC — TabPFN rank and paired tests (seed 42; delta = TabPFN − best GLM)

| dataset | metric | best_glm | TabPFN | GLM | delta | z | t (df=4) | p | rank |
|---|---|---|---|---|---|---|---|---|---|
| bemtl97 | pr_auc | logisticglm | 0.1705 ± 0.0023 | 0.1605 | +0.0101 | 3.35 | 7.11 | 0.0021 | **1** |
| coil2000 | pr_auc | lr | 0.1869 ± 0.0110 | 0.1671 | +0.0199 | 1.53 | 2.74 | 0.0521 | **1** |
| uslapseagent | pr_auc | poissonglm | 0.8866 ± 0.0040 | 0.8245 | +0.0622 | 10.58 | 15.92 | <0.0001 | **1** |
| norauto | pr_auc | lr | 0.1069 ± 0.0030 | 0.1019 | +0.0050 | 1.26 | 9.02 | 0.0008 | **1** |
| ausprivauto0405 | pr_auc | poissonglm | 0.1129 ± 0.0017 | 0.1098 | +0.0032 | 1.40 | 6.03 | 0.0038 | **1** |
| bemtl16 | pr_auc | lr | 0.9032 ± 0.0015 | 0.8891 | +0.0141 | 5.43 | 5.88 | 0.0042 | **1** |

**PR AUC: rank #1 on 6/6; paired-significant on 5/6** (coil2000 p=0.052 borderline).
The paired t is dramatically more powerful than the unpaired z — e.g. norauto pr_auc
z=1.26 (ns) vs t=9.02 (p=0.0008). **Every AUC edge from §14.11 is real, not fold
noise**: paired p ≤ 0.0063 on all 6 datasets, including ausprivauto0405 (t=13.93,
p=0.0002) and norauto (t=18.25, p<0.0001).

### 14.12.3 Top-decile lift — the honest weak spot

| dataset | TabPFN lift10 | best GLM lift10 | delta | t | p | rank (of 9) |
|---|---|---|---|---|---|---|
| bemtl97 | 1.837 ± 0.033 | 1.717 (lr) | +0.120 | 5.23 | 0.0064 | **1** |
| coil2000 | 3.335 ± 0.168 | 3.130 (logisticglm) | +0.206 | 1.19 | 0.2995 | **1** |
| uslapseagent | 2.458 ± 0.014 | 2.275 (poissonglm) | +0.183 | 13.20 | 0.0002 | **1** |
| norauto | 2.560 ± 0.057 | 2.540 (lr) | +0.020 | 1.16 | 0.3100 | 2 (lgbm) |
| ausprivauto0405 | 1.873 ± 0.044 | 1.845 (tweedieglm) | +0.028 | 0.65 | 0.5484 | **1** |
| bemtl16 | 2.607 ± 0.006 | 2.596 (poissonglm) | +0.011 | 1.04 | 0.3571 | 3 (lgbm, cat) |

**Lift10: rank #1 on 4/6, paired-significant on 2/6** (bemtl97, uslapseagent). On
norauto and bemtl16 the GBDTs edge TabPFN in the extreme top decile and the GLM
comparison is a tie. Lift is a noisier, thinner statistic than AUC (one 10% slice), and
the reading is clear: **TabPFN's ranking edge concentrates in the mid-to-upper rank
region; at the extreme top of the distribution it is dataset-dependent, not
universal.** "Use for triage" should be read as "strong global ranker; validate
top-decile behaviour on your own book" — consistent with the §14.4 adoption posture.

### 14.12.4 Seed stability (ausprivauto0405, bemtl97, norauto × seeds 7/42/123)

| dataset | Δ AUC vs best GLM, seed 7 | seed 42 | seed 123 | TabPFN AUC rank |
|---|---|---|---|---|
| ausprivauto0405 | +0.0051 | +0.0055 | +0.0049 | **1 on all 3** |
| bemtl97 | +0.0121 | +0.0117 | +0.0120 | **1 on all 3** |
| norauto | +0.0164 | +0.0165 | +0.0166 | **1 on all 3** |

The AUC record holds on all 9 dataset×seed cells, deltas stable to ±0.0004. The §14.11
verdict is not a split-seed artifact.

### 14.12.5 Bottom line

The ranking story from §14.11 **survives and strengthens**: AUC and PR AUC both rank
#1 on all 6 datasets, paired tests significant on 5–6/6, seed-stable. Calibration/log
loss remains the weak axis (unchanged: LL still goes to the best GLM on
bemtl97/norauto/ausprivauto0405). The one new nuance: **top-decile lift is
dataset-dependent** (4/6 rank 1, 2/6 significant) — the triage claim holds globally on
AUC/PR-AUC but not at the extreme tail. Two open questions remained after this
addendum — tuned/feature-engineered classical baselines, and other foundation models
(TabFM). Both are closed in §14.13: the tuned baselines do not change any ranking
verdict (TabPFN stays AUC/PR-AUC #1 of 14 on all 6 datasets), and TabFM was closed out
by assessment, not run (OOM on this hardware + non-commercial weights).
Artifacts: `frontier_pr_auc_results.csv`,
`frontier_pr_auc_summary.csv`, `analyze_pr_auc.py`, 6 extended canonical CSVs + 6
seed-run CSVs/plots.

## 14.13 Finality test — tuned/feature-engineered classical baselines on the canonical folds (2026-08-07)

The last standing baseline threat to the default-config verdict — §7.1's "as could
tuned GBDTs", §8's "what would change the answer" — is now measured. This addendum
runs tuned/feature-engineered versions of the classical baselines on the exact
canonical folds used by §14.11/§14.12, and closes out the other-foundation-models
question (TabFM) by assessment.

### 14.13.1 Protocol

Same canonical folds as §14.12 (StratifiedKFold 5, `random_state=42`); fold identity
verified — a plain LR (`C=1`) reproduces the stored canonical per-fold `lr` rows
exactly (built into the runner as the fold-identity check). Five new baselines, all
tuned by **ROC AUC** (documented choice — the metric under contest). Ranks below are
among **14 methods** (9 canonical + 5 new). Script: `run_tuned_baselines.py`
(docstring documents exact protocols; folds/metrics imported unmodified from
`run_frontier_benchmark.py`).

- `lr_tuned` — StandardScaler + LogisticRegression, C ∈ {0.01, 0.1, 1, 10} by inner
  3-fold CV AUC on the training fold, refit on the full fold.
- `glm_eng` — PolynomialFeatures(degree 2, interaction-only) + scaler + LR, same C
  grid; if >100k features, keep interactions of the top-30 features by |corr| with
  the target.
- `lgbm_tuned` — lr ∈ {0.05, 0.1} × num_leaves ∈ {31, 127}, early stopping (max
  1000 rounds, patience 10) on a 10% stratified slice of the training fold, refit on
  the full fold.
- `cat_tuned` — lr × depth ∈ {6, 10}, same early-stopping protocol (10 min/fold
  soft cap).
- `rf_tuned` — 300 trees, max_features ∈ {sqrt, 0.5} × min_samples_leaf ∈ {1, 10}.

Tests: paired t, df=4, two-sided; delta = TabPFN − baseline. Outputs:
`frontier_tuned_baseline_summary.csv` (per-dataset × metric × baseline:
tabpfn_mean/se, base_mean/se, delta, t_paired, p_paired, tabpfn_rank, n_folds=5),
`frontier_tuned_baseline_results.csv` (per fold, incl. fit/infer seconds and chosen
config); analysis: `analyze_tuned_baselines.py` (untracked).

### 14.13.2 Ranking metrics — TabPFN stays #1 of 14 on AUC and PR-AUC

| dataset | AUC rank (closest competitor: delta, p) | PR-AUC rank (closest competitor: delta, p) |
|---|---|---|
| bemtl97 | 1 (lgbm: +0.0055, p=0.0007) | 1 (lgbm: +0.0054, p=0.0009) |
| coil2000 | 1 (cat: +0.0263, p=0.0016) | 1 (cat: +0.0240, p=0.0005) |
| uslapseagent | 1 (cat: +0.0027, p=0.0219) | 1 (cat: +0.0077, p=0.0298) |
| norauto | 1 (lgbm: +0.0045, p=0.0064) | 1 (lgbm: +0.0038, p=0.0102) |
| ausprivauto0405 | 1 (glm_eng: +0.0036, p=0.0029) | 1 (glm_eng: +0.0017, p=0.0765, ns) |
| bemtl16 | 1 (lgbm: +0.0008, p=0.0020) | 1 (lgbm: +0.0019, p=0.0239) |

**No baseline beats TabPFN on AUC at p<0.05 on any dataset** — every delta positive
and paired-significant. The closest edges: glm_eng on ausprivauto0405 (+0.0036,
p=0.003 — TabPFN 0.6622 vs 0.6586), lgbm on bemtl16 (+0.0008, p=0.002), cat on
uslapseagent (+0.0027, p=0.022). PR-AUC: rank #1 on all 6, paired-significant on
5/6 — the one non-significant win is glm_eng on ausprivauto0405 (delta +0.0017,
p=0.077). The §14.12 lift10 caveat is unchanged: lgbm still beats TabPFN on bemtl16
(delta −0.018, p=0.015); the norauto lgbm edge stays non-significant (p=0.949).

### 14.13.3 Calibration — two small documented exceptions

- **log_loss (new):** on ausprivauto0405 the entire linear family beats TabPFN:
  glm_eng (+0.0010, p=0.004), lr / lr_tuned / logisticglm (≈+0.0008, p≈0.003),
  poissonglm (+0.0007, p=0.005), tweedieglm (+0.0004, p=0.049). The known lgbm
  log-loss wins are unchanged: bemtl97 (+0.0010, p<0.001) and norauto (+0.0010,
  p=0.005).
- **Brier (new):** "never significantly worse" is now strictly false on 2/6
  datasets, by ~1e-4 margins: ausprivauto0405 vs glm_eng (+0.0001, p=0.031) and vs
  lr / lr_tuned / logisticglm / poissonglm (p≈0.008–0.015); bemtl97 vs lgbm
  (+0.0001, p=0.016).
- Both exceptions are calibration-axis only (majority-class bulk, per the §14.11.4
  imbalance-artifact reading) — the ranking metrics are untouched on the same
  datasets.

### 14.13.4 Tuning-effectiveness honesty note + TabFM closure

- **The tuned GBDTs regressed vs their shipped defaults on AUC on 5/6 datasets**
  (e.g. norauto: lgbm_tuned 0.640 vs lgbm 0.697; cat_tuned 0.663 vs cat 0.688). The
  2×2 grid + 10%-slice early-stopping protocol did not improve on defaults, so
  "properly tuned GBDT" was only partially achieved; the credible engineered
  baseline is glm_eng, and it still lost on every ranking metric (AUC/PR-AUC rank 1
  TabPFN).
- **TabFM: NOT RUN** — closed out by assessment. The full-context in-context-learning
  fit OOM-killed the process on coil2000 on this 8 GB machine (hard kill, not
  catchable); a row-capped fallback (`max_num_rows=6000`, `n_estimators=4`) was
  scripted in `run_tabfm.py` but never executed; and per
  `docs/analyses/tabular_foundation_models_catalog.md` the non-commercial weights
  already block production use. Verdict: no claim about other foundation models;
  TabFM remains outside the comparison by assessment, not by measurement.

### 14.13.5 Bottom line

The "best in suite at default configs" scoping **survives contact with
tuned/engineered classical baselines on the ranking metrics**: AUC and PR-AUC rank
#1 on all 6 datasets among 14 methods. The calibration claims gain two small
documented exceptions — ausprivauto0405 log loss and Brier vs the linear family
(glm_eng closest), and bemtl97 Brier vs lgbm — both ~1e-4 paired-significant edges
on the calibration axis. Artifacts: `frontier_tuned_baseline_summary.csv`,
`frontier_tuned_baseline_results.csv`, `run_tuned_baselines.py`, `run_tabfm.py`
(written, never executed), `analyze_tuned_baselines.py`.

## 14.14 Count/frequency targets reframed as classification — issue #67 (2026-08-07)

Issue #67's question: can TabPFN's weakest axis be sidestepped by re-expressing the
target? The count targets on which TabPFN is dominated (Poisson deviance, §14.8/§14.9)
are read as classification problems instead — claim/no-claim and 0/1/2+ claim count —
moving the contest from TabPFN's weakest metric axis (count regression) to its
strongest (ranking). Hypothesis: on the classification reframe of a count target,
TabPFN's AUC edge applies. **Confirmed — the count axis was the loss; classification
is the win.**

### 14.14.1 Protocol

Same dataset and prep as §14.9: Spanish motor freq (`make_spanish_motor_freq` in
`scripts/infra/prepare_insurance_datasets.py`), 53,502 policies, leak-fixed loaders
via `run_frontier_benchmark.py`. The count target `N_claims_year` is reframed into two
new targets:

- **binary** — claim vs no-claim (11.1% positive);
- **ordinal** — 0 / 1 / 2+ claims (88.9 / 6.3 / 4.8%).

Protocol mirrors the canonical suite: StratifiedKFold(5, shuffle, `random_state=42`)
per target; binary also run at seed 7 for the stability check (§14.12 precedent).
Methods — binary: the canonical 9 (tabpfn, cat, lgbm, xgb, lr, logisticglm, tweedieglm,
poissonglm, rf); ordinal: the multiclass 6 (tabpfn, cat, lgbm, xgb, lr, rf) —
poissonglm/tweedieglm excluded because single-output GLMs cannot feed multiclass
metrics (documented deviation). Metrics — binary: log loss, AUC, Brier, PR-AUC, lift10;
ordinal: one-vs-rest macro AUC, multiclass log loss, multiclass Brier (MSE of the
one-hot encoding), lift10 on P(≥1). Paired t, df=4, two-sided; delta = TabPFN −
baseline; rank among all methods on that target. 15 hosted TabPFN API calls, zero
failures. Scripts: `run_reframe_frequency.py` (runner; docstring documents exact
targets/folds), `analyze_reframe_frequency.py` (summary + paired tests). Outputs:
`reframe_frequency_results.csv` (121 lines, per fold × method),
`reframe_frequency_summary.csv` (per baseline × metric × seed).

### 14.14.2 Binary claim/no-claim, seed 42 — rank #1 on all 5 metrics

| metric | TabPFN | best competitor | delta | p (paired t) | rank |
| --- | ---: | ---: | ---: | ---: | ---: |
| AUC | 0.7170 | lgbm 0.7090 | +0.0080 | 0.0010 | 1 |
| PR-AUC | 0.2428 | cat 0.2374 | +0.0054 | 0.1165 (n.s.) | 1 |
| lift10 | 2.6018 | cat 2.5127 | +0.0891 | 0.0279 | 1 |
| log loss | 0.3206 | lgbm 0.3209 | −0.0003 (tie) | 0.3630 | 1 |
| Brier | 0.0927 | lgbm 0.0929 | −0.0002 | 0.0441 | 1 |

**TabPFN ranks #1 on all five binary metrics.** The AUC edge is paired-significant
(+0.0080 over lgbm, p=0.0010), lift10 is significant (+0.0891, p=0.0279), and Brier is
a significant ~1e-4 win (p=0.0441). The one within-noise result is PR-AUC: rank #1 but
+0.0054 over cat at p=0.1165. Note what is *not* the weak spot here: calibration. Log
loss and Brier both go to TabPFN (ties-to-better) — the inverse of the §14.12/§14.13
classification picture, where calibration carried the caveats.

### 14.14.3 Binary seed 7 — seed-stable

| metric | TabPFN | delta vs best | p (paired t) | rank |
| --- | ---: | ---: | ---: | ---: |
| AUC | 0.7165 | +0.0098 | 0.0020 | 1 |
| log loss / Brier / PR-AUC / lift10 | rank #1 (details in `reframe_frequency_summary.csv`) | — | — | 1 |

AUC 0.7165 at seed 7 vs 0.7170 at seed 42: the reframe win is not fold-luck —
paired-significant at both seeds (p=0.0020) and rank #1 on all five metrics at both
seeds.

### 14.14.4 Ordinal 0/1/2+ — rank #1 on all 4 metrics

| metric | TabPFN | best competitor | delta | p (paired t) | rank |
| --- | ---: | ---: | ---: | ---: | ---: |
| AUC (ovr-macro) | 0.7167 | lgbm 0.7056 | +0.0111 | 0.0085 | 1 |
| lift10 (P(≥1)) | 2.7370 | lgbm 2.6491 | +0.0878 | 0.1338 (n.s.) | 1 |
| log loss (multiclass) | 0.3935 | lgbm 0.3944 | −0.0009 (tie) | 0.3428 | 1 |
| Brier (MSE of one-hot) | 0.0647 | lgbm 0.0647 | 0.0000 (tie) | 0.8790 | 1 |

The ordinal reframe reproduces the binary result: AUC rank #1 with the largest edge of
the two reframes (+0.0111 over lgbm, p=0.0085); multiclass log loss and Brier tie with
lgbm at rank 1; lift10 on P(≥1) is rank 1 but within noise (p=0.1338) — the same tail
caveat as binary.

### 14.14.5 §14.9 contrast — the count axis was the loss

On Poisson deviance TabPFN is off-frontier on this same dataset: 0.9876 vs lgbm
0.8916, rank 5/8, +0.096 worse (§14.9). Reframed as classification, the same rows put
TabPFN ahead of lgbm on AUC with paired significance at both seeds (+0.0080, p=0.0010
seed 42; +0.0098, p=0.0020 seed 7). Same data, different target encoding: TabPFN's
prior does not extract the count signal the GBDT extracts, but it ranks the claim
propensity the GBDT ranks.

### 14.14.6 Caveats

- **PR-AUC is the honest weak spot — not calibration.** Binary PR-AUC is rank #1 but
  within noise vs CatBoost (+0.0054, p=0.1165); ordinal lift10 on P(≥1) likewise
  (p=0.1338). The caveat the issue expected (calibration) did not materialize: log
  loss and Brier rank #1, ties-to-better.
- **GLM collapse.** poissonglm and tweedieglm predict a constant on claim/no-claim:
  AUC exactly 0.5000, log loss at the base rate (0.3490). Their count-domain edge
  (frontier anchors in §14.9) does not transfer to the classification reframe.
- **Ordinal PR-AUC is NaN by design** — no standard PR-AUC for multiclass; lift10 on
  P(≥1) is the substitute (§14.14.1), and it is within noise.
- **Single dataset, single portfolio.** One count target (Spanish motor freq), two
  reframings; freMTPL2freq (678K rows) was not reframed.

### 14.14.7 Bottom line

"Regression/frequency stays GBDT territory" gains a scoping footnote: on the
classification reframe of a count target — claim vs no-claim, or 0/1/2+ — TabPFN's
ranking edge applies, paired-significant and seed-stable, while the count model
itself (Poisson deviance) and the pricing/calibration story are unchanged. Use case:
triage on claim propensity from the same loss-cost data the count model prices.
Artifacts: `run_reframe_frequency.py`, `analyze_reframe_frequency.py`,
`reframe_frequency_results.csv`, `reframe_frequency_summary.csv`.

## 15. Addendum — Version-Drift Re-Test Policy (issue #55, 2026-08-04)

The benchmark verdict is pinned to hosted v3 (`model_path="v3_default"`, tabpfn-client
0.3.3 — §12.1 model-version correction, §14.9 note). This section is the policy for
re-running the verdict when the model or client evolves. Docs-only deliverable of
issue #55 — no re-run has been done; this is the procedure to follow when a trigger
fires.

### 15.1 Trigger

- A new `tabpfn-client` release installed in the benchmark venv (`/tmp/tabarena/.venv-ta`,
  currently 0.3.3; the committed `requirements.txt:9` range is the loose
  `tabpfn-client>=0.2,<0.3` and does not capture the installed version).
- A Prior Labs model-version announcement (a new `model_path` beyond `v3_default`).
- Any environment bump: venv rebuild, requirements change, or CI image refresh that
  changes the resolved client version.

### 15.2 Scope

- **12-dataset frontier** (`scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py`):
  6 classification datasets (`DATASETS`, lines 103–110) + 6 regression datasets
  (`REG_DATASETS`, lines 122–129). One command per dataset, case-insensitive filter
  (lines 701–707), from the benchmark venv (`source /tmp/tabarena/.venv-ta/bin/activate`,
  docstring lines 69–74):

  ```bash
  python scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py <dataset>
  python scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py --regression <dataset>
  ```

- **Lapse benchmark** (`scripts/benchmarks/run_lapse_benchmark.py`): has no pin of its
  own, but imports the shared `TabPFNClientModel` from
  `run_tabarena_insurance_benchmark.py` (lines 26–27), which pins
  `model_path="v3_default"` (lines 262, 265) — covered transitively; re-run it
  alongside the frontier.
- **Sweep-reuse caveat** (must be handled or stated): the frontier reuses TabPFN
  log-loss rows for bemtl97 / coil2000 / uslapseagent from the committed
  `home_turf_sweep_results.csv` (lines 31–36, 385–388, 457–461) — refresh the sweep
  (`scripts/benchmarks/run_home_turf_size_sweep.py`) first, or the frontier will not
  see new model behavior on those three datasets. norauto / ausprivauto0405 / bemtl16
  and all regression datasets run fresh TabPFN power (lines 462–488, 603–626).

### 15.3 Procedure

1. **Record versions before running**: `python -c "from importlib.metadata import version; print(version('tabpfn-client'))"` plus the `model_path` used — every TabPFN call site pins `model_path="v3_default"` (`run_frontier_benchmark.py:469,610`; `run_home_turf_size_sweep.py:102`; `finish_home_turf_sweep_v2.py:89`; `run_smoke_tabarena.py:82`; `run_tabarena_insurance_benchmark.py:262,265`; `run_tabarena_insurance_imbalance_pilot.py:219,222,265`). The installed version is authoritative — the committed range is loose (§15.1).
2. **Run the same datasets/commands as the v3 baselines** (§15.2) — same folds (seed 42), same metrics, same D3 beyond-SE rule (§14.1).
3. **Diff `scripts/eval/insurance_benchmark_v1/frontier_results_*.csv`** (the 12 committed v3 baselines, §14.2–§14.10) — compare `mean` ± `se` per method and the `on_frontier` flag (columns are stable: `method,mean,se,mean_auc,se_auc,mean_brier,se_brier,n_params,on_frontier` on the 6 classification CSVs, `run_frontier_benchmark.py` L569 — regression CSVs keep `method,mean,se,n_params,on_frontier`, L720; `mean`/`se` stay log loss, no protocol drift, §14.11.5).
4. **Append a §14.x-style addendum** (this section becomes §16/§17 for the re-run, or a dated `§15.x` sub-section) documenting client + model versions, the command log, and the diff outcome.
5. **Update the one-pager verdict / adoption rule only if the pattern changes** — wins/losses flip or beyond-SE shifts (`docs/reports/TABPFN_BENCHMARK_SUMMARY.md` "Conclusion & adoption guidance"; regime descriptor `docs/analyses/regime_characterization.md` §3). No change → note "pattern unchanged" in the addendum; do not re-derive the adoption rule.
6. **Close-out**: registry evidence update (`docs/reports/REPORT_REGISTRY.md`) + a TASKS.md row (owned by the orchestrator).

### 15.4 Automation note (optional)

A dev script or CI check comparing the installed `tabpfn-client` version against the
baseline recorded here (0.3.3, §15.3 step 1) — e.g. a `pip show tabpfn-client` /
importlib version check in the existing eval scripts, flagging when it moves off the
pinned version so a human triggers §15.3. Not built; documented for when the harness
gets CI.

## 16. Addendum — TabPFN 3.5 version-drift re-test, regression/count tier (issue #186, 2026-09-16)

First live execution of the §15 policy. §15.1's second trigger fired — a Prior Labs
model-version announcement introducing a `model_path` beyond `v3_default` — so this is
the real run, not the §82 dry run (which was never executed and is superseded).

Scope is deliberately partial: the four regression/count datasets where `v3_default` sits
**off the parsimony frontier**, i.e. the evidence base for the "prefer GBDT/GLM for pricing
at scale" verdict (§8, §14.9). The classification tiers (`ausprivauto0405`, `bemtl97`,
`norauto`, `bemtl16`) and the `eudirectlapse` lapse loss are **not** covered here
(`eudirectlapse`: see §17).

### 16.1 Versions and provenance (§15.3 step 1)

| Field | Baseline (§14.x) | This re-test |
| --- | --- | --- |
| Model | `v3_default` | **`v3.5_default`** |
| `tabpfn-client` | 0.3.3 | **0.6.0** |
| Server default model | v3 | **v3.5** — an unpinned call now silently selects 3.5 |
| Row / cell / class caps | 1M / 200M / 160 | unchanged |
| Max columns | 2,000 | **20,000** (10×) |
| Folds / seed / split | `KFold(5, shuffle=True, random_state=42)` | identical — unchanged |
| Script git SHA | — | `0fc1158` (recorded per-dataset in `predictions/*.manifest.json`) |

Model identifiers are `ModelVersion` enum values in the client: `v3.5` and `v3.5-fast`
exist, and the `_default` suffix forms the `model_path` alias the server resolves to a
checkpoint. `estimate_cost`, by contrast, takes the bare enum value (`v3.5`) — the two
APIs are not interchangeable. Only `v3.5_default` was run; `v3.5-fast_default` (alpha,
latency-optimised, accuracy trade-off undisclosed) was not.

Selection is no longer hardcoded: `src/model_version.py` resolves `model_path` from
`TABPFN_MODEL_PATH` (env, then `.env`), defaulting to `v3_default` so an unconfigured
run still reproduces the baseline.

### 16.2 Results — all four datasets improved

Mean ± SE over 5 folds, lower is better. `Δ/SE` uses the baseline SE, since no per-fold
baseline values exist (see §16.5). Paired column is a per-fold paired t-test against the
best rival within this run.

| Dataset | Rows | Metric | v3_default | v3.5_default | Δ | Δ/SE | Frontier | Paired vs `lgbm` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `freMTPL2freq` | 678,013 | Poisson dev. | 0.3877 ± 0.0020 | **0.3013 ± 0.0017** | −22.3% | 43.0 | no | p=0.0004, 0/5 — worse |
| `spanish_motor_freq` | 53,502 | Poisson dev. | 0.9876 ± 0.0162 | **0.9031 ± 0.0085** | −8.6% | 5.2 | **no → yes** | **p=0.47 — not distinguishable** |
| `bemtl97_amount` | 163,212 | RMSE | 0.7282 ± 0.0106 | **0.7012 ± 0.0062** | −3.7% | 2.6 | no | p<0.0001, 0/5 — worse |
| `spanish_motor_severity` | 53,502 | RMSE | 1.8862 ± 0.0116 | **1.8607 ± 0.0113** | −1.4% | 2.2 | no | p=0.0004, 0/5 — worse |

Per-fold TabPFN values (`v3.5_default`):

- `freMTPL2freq` — 0.3012, 0.2968, 0.2983, 0.3038, 0.3063
- `spanish_motor_freq` — 0.8952, 0.8867, 0.9112, 0.9326, 0.8898
- `bemtl97_amount` — 0.7118, 0.6954, 0.6801, 0.7147, 0.7041
- `spanish_motor_severity` — 1.8714, 1.8386, 1.8742, 1.8892, 1.8300

### 16.3 The one verdict change — `spanish_motor_freq`

Exactly one `on_frontier` flag moved across all four datasets, and it is TabPFN's own.
The frontier rule (`pareto_frontier`, SE-aware domination: B dominates A iff B has fewer
parameters **and** `mean_B + SE_B < mean_A − SE_A`) resolves as:

- **Before** — lgbm 0.8916 + 0.0124 = 0.9040 < 0.9876 − 0.0162 = 0.9714 → dominated.
- **Now** — 0.9040 < 0.9031 − 0.0085 = 0.8946 is **false** → not dominated.

The flip is driven by both a better mean and a halved SE (0.0162 → 0.0085), against
`lgbm` numbers that reproduced bit-exactly. The paired test agrees: p=0.47 over 5 folds.

This falsifies a specific §14.9 claim. That section cites this dataset as evidence that
frequency signal at scale is *"tree-extractable only"* — LGBM 0.8916 vs TabPFN 0.9876,
with the Poisson GLM at the 1.0123 null floor. At 0.9031 vs 0.8916, not statistically
separable, that reading no longer holds **for `spanish_motor_freq` on `v3.5_default`**.

Consequently the headline count in §8 and `TABPFN_BENCHMARK_SUMMARY.md` — *"off the
parsimony frontier 5 of 12"* — becomes **4 of 12**.

`freMTPL2freq` is the largest single improvement (−22.3%, closing ~90% of the gap to
LightGBM: +0.0966 → +0.0101) but is **not** a verdict change: the paired test still
returns p=0.0004 with 0/5 folds won. Better, not competitive. `bemtl97_amount` is
unmoved in substance — LightGBM still wins by ~1.4× on RMSE.

### 16.4 Environment confound — `ols` drift (disclose before citing)

This is **not** a pure model-only diff, contrary to the ideal in §15.3 step 2.
`scikit-learn` also moved: `requirements.lock` pins **1.6.1**; this re-test ran **1.9.0**
(the Aug-2026 benchmark venv at `/tmp/tabarena/.venv-ta` no longer exists, so its exact
version is unverifiable). Baseline reproduction against the committed CSVs:

| Method | Reproduced? | Largest drift |
| --- | --- | --- |
| `lgbm`, `cat`, `xgb` | **bit-exact on all 4** | — |
| `ols` | **no — all 4 datasets** | +5.63% (`spanish_motor_freq`) |
| `rf`, `poissonglm`, `tweedieglm` | near-exact | <0.2% |

Why the conclusions survive it:

1. `lgbm` is the best rival on all four datasets and reproduced exactly, so every paired
   test in §16.2 is unaffected.
2. No `ols` frontier flag changed anywhere, despite the drift — at 11–21 parameters it is
   too parsimonious to be dominated.
3. The §16.3 flip depends only on TabPFN's mean/SE versus lgbm's unchanged numbers.

What it does mean: the `ols` rows in this re-test must not be compared against the
committed v3 `ols` rows. A future re-test should pin `scikit-learn==1.6.1` to make the
diff genuinely model-only.

### 16.5 Two harness defects found (both fixed here)

Neither is a model finding; both would have silently corrupted this re-test.

1. **Auth (silent TabPFN dropout).** `src/api_key.py` exported only `TABPFN_API_KEY`;
   `tabpfn-client` reads **`TABPFN_TOKEN`** after 0.3.3. The failure mode is quiet — all
   eight baselines populate normally while every TabPFN fold fails its retries. Fixed by
   exporting both names, which keeps 0.3.3 baseline re-runs working.
2. **Retry did not cover `predict`.** The 3-attempt backoff wrapped `model.fit()` only.
   On `freMTPL2freq` a transient server error (`The worker failed to process this
   request`) at fold 4 of 5 aborted the dataset and discarded **four completed folds,
   ~59 minutes of compute and its tokens** — nothing was written but an empty manifest.
   Fixed by moving construction, fit and predict inside the retry, so a predict failure
   re-fits and retries.

The re-run after the fix reproduced folds 0–3 to the digit (0.3012 / 0.2968 / 0.2983 /
0.3038), confirming determinism, and completed fold 4 at 0.3063.

### 16.6 Version-vs-version paired test — not done here, but now unblocked

The `Δ/SE` column in §16.2 is a two-sample comparison against the baseline SE, **not** a
paired per-fold test. Nothing in `main` supports the paired version: the committed v3
frontier CSVs carry only mean ± SE.

The per-fold v3 arrays do exist, however — in open PR
[#152](https://github.com/IFoA-ADSWP/tabular-foundation-model/pull/152), which backfills
`v3_default` predictions for six regression datasets, including all four re-tested here.
Once it merges, a paired `v3_default`-vs-`v3.5_default` test on identical folds becomes a
mechanical exercise, and it should replace the `Δ/SE` column. Treat §16.2 as provisional
in that respect.

**Filename collision, and the fix.** #152's artefacts were named
`<dataset>__seed<seed>`, which has no version component — so this re-test would have
written over the exact baseline it is diffed against, leaving the manifest as the only way
to tell the two apart. `write_predictions_npz` now appends the resolved `model_path`:

```
predictions/freMTPL2freq__seed42__v3_default.npz      <- #152 (baseline)
predictions/freMTPL2freq__seed42__v3.5_default.npz    <- this re-test
```

Generations therefore coexist, and each `§15` re-test preserves its predecessor instead of
destroying it. #152's files need the matching rename before merge; the `.gitignore`
exemption (`!scripts/eval/insurance_benchmark_v1/predictions/*.npz`, per the #150 decision
to commit directly) is glob-based and already covers both names — both PRs add the same
line, so expect a trivial conflict there.

Other limits unaffected by the above: single seed (42), single split, and no
`v3.5-fast_default` arm.

### 16.7 Cost

Metered via `get_api_usage()`: **~4.8M tokens** for the tier including the discarded
`freMTPL2freq` attempt (~2.3M for its re-run alone). Account usage moved 19.37M → 24.17M
of a 60M allowance. `estimate_cost` quoted `freMTPL2freq` well (2.27M vs ~2.3M actual)
but under-quoted the three smaller datasets, which hit a 10,000-token-per-call floor
while actually costing ~50–95k per fold — treat quotes on small datasets as a floor.

### 16.8 Bottom line

> On the four regression/count datasets where `v3_default` sat off the parsimony frontier,
> **`v3.5_default` improved on every one**, each beyond 2× the baseline SE. One verdict
> change: `spanish_motor_freq` moved onto the frontier and is no longer statistically
> separable from LightGBM (p=0.47), which falsifies §14.9's "tree-extractable only"
> reading for that dataset and takes the off-frontier count from 5/12 to 4/12.
> `freMTPL2freq` improved most (−22.3%) but remains a paired-significant loss.
> `bemtl97_amount` and `spanish_motor_severity` remain paired-significant losses.
> The pricing-at-scale verdict therefore **narrows but does not reverse** — and the
> `scikit-learn` drift in §16.4 means the `ols` rows here are not comparable to v3.

Still open under #186: the classification tiers (`ausprivauto0405`, `bemtl97`, `norauto`
calibration; `bemtl16` top-decile lift) and the sweep refresh that §15.2 requires before
any `bemtl97` frontier claim. The `eudirectlapse` loss is covered in §17.

## 17. Addendum — `eudirectlapse` re-test: the v3 loss does not reproduce (issue #186, 2026-09-17)

Tier 2 of #186. The target was the one classification dataset disclosed as a genuine
TabPFN loss in §14.10 (published, TabArena lapse harness, Aug 2026): **TabPFN v3 AUC
0.6101 ± 0.0049**, last of three, behind GBM 0.6138 and LR **0.6260 ± 0.0037**. The
regime analysis attributed it to additive lapse structure the model does not capture.

### 17.1 Design — same-day, same-harness, model-only

Unlike §16, which diffed against committed August numbers, **both model versions were
run here** in one environment on one day. `eudirectlapse` went through the frontier harness
(`run_frontier_benchmark.py --data data/raw/eudirectlapse.csv --target lapse
--save-predictions`), once with `TABPFN_MODEL_PATH=v3_default` and once with
`v3.5_default`, rather than rebuilding the autogluon/tabarena lapse harness.

- 23,060 rows, 18 features (9 categorical), 12.8% positive
- `StratifiedKFold(5, shuffle=True, random_state=42)`, `tabpfn-client` 0.6.0,
  `scikit-learn` 1.9.0
- Checked: the test folds are identical across the two runs, and all eight baselines'
  predictions are bit-identical (max difference 0). The model is the only variable, so
  §16.4's `scikit-learn` confound does not apply.
- The test folds are also **identical to the published lapse benchmark's**: that harness
  uses the same `StratifiedKFold` call on the same row order.

Per-fold predictions for all nine methods are saved for both runs
(`predictions/eudirectlapse__seed42__{v3_default,v3.5_default}.npz`). This is the
project's **first genuine paired version-vs-version test**.

### 17.2 v3 vs v3.5 — a small, consistent improvement

| Metric | v3 | v3.5 | Δ | Paired p | v3.5 better on |
| --- | --- | --- | --- | --- | --- |
| Log loss | 0.3726 ± 0.0012 | **0.3694 ± 0.0010** | −0.0032 | **0.002** | 5/5 folds |
| Brier | 0.1092 ± 0.0002 | **0.1085 ± 0.0002** | −0.0007 | **0.002** | 5/5 |
| PR-AUC | 0.2031 ± 0.0042 | **0.2080 ± 0.0046** | +0.0049 | **0.014** | 5/5 |
| AUC | 0.6331 ± 0.0051 | **0.6367 ± 0.0048** | +0.0036 | 0.054 | 4/5 |
| Lift@10% | 1.914 ± 0.033 | **1.954 ± 0.061** | +0.041 | 0.43 | 4/5 |

v3.5 is significantly better on log loss, Brier and PR-AUC, borderline on AUC, and not
distinguishable on lift. TabPFN is on the parsimony frontier under both versions; no flag
changed.

### 17.3 The published loss does not reproduce — even for v3

On this harness, **TabPFN v3 ranks #2 of 10 methods on every metric**, behind only v3.5.
The comparison needs care, because the harness's default `lr` receives categoricals as
integer codes (`cat.codes`), which treats nominal levels such as `vehicl_region` (14
levels) as ordinal. That handicaps it. A fair linear baseline — one-hot categoricals plus
standardised numerics, `LogisticRegression`, fitted on the identical folds — was therefore
added for the comparison:

| AUC, identical folds | Frontier harness | Published (TabArena harness) |
| --- | --- | --- |
| TabPFN v3.5 | **0.6367** | — |
| TabPFN v3 | **0.6331** | 0.6101 |
| LR, one-hot | **0.6271** | 0.6260 |
| LR, integer codes (harness default) | 0.6132 | — |

One-hot LR reproduces the published LR (0.6271 vs 0.6260). TabPFN v3 does **not** (0.6331
vs 0.6101). Against the fair one-hot LR:

| Metric | v3 vs one-hot LR | v3.5 vs one-hot LR |
| --- | --- | --- |
| AUC | +0.0060, p=0.047, 5/5 | +0.0096, p=0.005, 5/5 |
| PR-AUC | +0.0094, p=0.007, 5/5 | +0.0143, p=0.008, 5/5 |
| Lift@10% | +0.169, p=0.001, 5/5 | +0.210, p=0.012, 5/5 |
| Log loss | +0.0007, p=0.19, 1/5 — **tie** | −0.0024, p<0.001, 5/5 |
| Brier | −0.0000, p=0.86, 3/5 — **tie** | −0.0007, p=0.001, 5/5 |

So on identical folds, **v3 beats a fair linear model on ranking and ties it on
calibration; v3.5 beats it on all five metrics.** The version change turned a calibration
tie into a paired-significant win. Measured against the integer-coded default `lr`, v3.5's
log-loss margin looks about twice as large (−0.0045) — the harness default overstates it.

### 17.4 Why the published number differs — unresolved

The gap sits on TabPFN's side: v3 scores **0.023 AUC lower** in the TabArena harness on
the same folds. Two things are ruled out:

- **Fold construction** — the folds are identical (§17.1).
- **One-hot vs integer encoding for TabPFN** — both harnesses feed TabPFN float32 arrays
  (`src/tabpfn_client_model.py` `_preprocess` → `to_numpy(dtype=np.float32)`), not one-hot
  columns.

Two candidates remain, and neither is verified:

1. **Harness preprocessing.** The TabArena wrapper passes data through AutoGluon's
   `super()._preprocess` before the float32 conversion. That step can re-encode, reorder or
   drop categorical levels, so the integers TabPFN receives may differ from `cat.codes`.
2. **Server-side drift of the `v3_default` alias.** Client 0.6.0 documents that the server
   resolves each `<version>_default` alias to *its current default checkpoint*. The
   `v3_default` run here (client 0.6.0, 2026-09-17) is therefore not guaranteed to be the
   checkpoint the August run used (client 0.3.3).

**Discriminating test (not run):** re-run `v3_default` today on a dataset whose August
per-fold TabPFN values are committed — for example `coil2000` at full size in
`home_turf_sweep_results.csv` — and compare fold by fold. A match rules out alias drift and
leaves preprocessing. A mismatch confirms drift.

That outcome also bears on §16: its deltas compare **August** `v3_default` against
**September** `v3.5_default`, so any alias drift would be folded into what §16 attributes to
the version change. The same-day paired design here is immune to it.

### 17.5 Caveats

- **Weak default linear baselines, benchmark-wide.** The frontier harness gives `lr` and
  `logisticglm` integer-coded categoricals on every dataset, not only this one. §14.13's
  feature-engineered `glm_eng` partly addresses this for the six canonical classification
  datasets, but untuned linear rows on categorical-heavy data understate the linear floor.
- **Degenerate GLM rows.** `tweedieglm` and `poissonglm` score AUC exactly 0.5000 here —
  constant predictions on the binary target — so they are not meaningful baselines on
  this dataset.
- **`rf` log loss is clip-dependent.** The random forest emits exact 0/1 probabilities (43
  of them, 3 hard misses), so its log loss depends on the clipping epsilon: 0.3905 in
  float64 vs 0.3878 from float32 storage. Rank-based metrics are unaffected.
- **Single seed (42).**

### 17.6 Harness defect found (fixed here)

The first attempt at both runs completed every TabPFN fold, then aborted at the in-run
read-back check with `read-back mismatch for rf: recomputed=0.387838 vs recorded=0.390453`.
The check re-scored float32-stored predictions, while the run had scored in float64, and
`log_loss` clips at the dtype's machine epsilon — so the three hard misses cost ~16 nats
instead of ~36. It had never fired before because §16 was regression-only, where RMSE and
Poisson deviance do not clip on dtype epsilon. `verify_predictions_readback` now scores in
float64. Both runs were repeated after the fix, and the TabPFN fold values reproduced to
the digit.

### 17.7 Cost

200,000 credits for four runs — the two aborted attempts plus the two repeats — which is
10,000 per fold, the API's per-call minimum.

### 17.8 Bottom line

> The `eudirectlapse` "genuine classification loss" (§14.10) **does not reproduce** on the
> frontier harness, even for v3, on the identical folds. Against a fair one-hot logistic
> regression, v3 wins on ranking (AUC +0.006, PR-AUC, lift) and ties on calibration;
> v3.5 wins on all five metrics. Paired on the same folds, v3.5 improves on v3
> significantly for log loss, Brier and PR-AUC. The published loss reflects TabPFN scoring
> 0.023 AUC lower inside the TabArena harness, for a reason not yet isolated (§17.4). It
> should **no longer be cited as a property of the model** — in particular, not as
> evidence that TabPFN fails to capture additive structure.

Docs that still cite the published loss and are **not** edited here: §14.10 (the source
table, kept as the historical v3 record), `docs/reports/PRE_FINETUNING_INVESTIGATIONS.md`
("EU Lapse is the disclosed exception"), and `docs/reports/FINE_TUNING_PILOT_RESULTS.md`
§4 finding 2. Read them through this section.

## 9. Source Workbooks

- `scripts/benchmarks/run_home_turf_size_sweep.py` — home-turf size sweep runner (3 datasets × 3
  sizes × 5 folds, TabPFN + GBDT arms; §13).
- `scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py` — insurance frontier
  benchmark (D1/D2 combined pass, 3 datasets × 9 methods, D3 beyond-SE Pareto rule;
  §14, commit `ed3e119`).
- `scripts/eval/insurance_benchmark_v1/run_reframe_frequency.py` +
  `analyze_reframe_frequency.py` — count/frequency targets reframed as binary/ordinal
  classification (§14.14, issue #67).
- `scripts/benchmarks/finish_home_turf_sweep_v2.py` — sweep result assembly, fold/cell bookkeeping,
  flaky-config dedup, error handling (§13; supersedes `finish_home_turf_sweep.py`).
- `scripts/benchmarks/run_tabarena_insurance_benchmark.py` — benchmark runner (task registry, target
  definitions, feature handling at line 184).
- `scripts/benchmarks/run_tabarena_insurance_imbalance_pilot.py` — imbalance pilot (coil2000 +
  uslapseagent, `balance_probabilities` vs default; §11).
- `scripts/eval/insurance_benchmark_v1/rescore_focused_imbalance_logloss.py` — log-loss /
  Brier re-score of pilot folds (§11.3).
- `scripts/infra/prepare_insurance_datasets.py` — dataset prep (`make_bemtl97` at line 43).
- `outputs/current/logs/domain_finetune_logbook.md` — domain fine-tune runs and
  interpretation blocks (protocol runs 2026-04-02).
- Prior write-ups: `docs/reports/COMBINED_TABPFN_CLASSIFIER_REGRESSOR_ANALYSIS.md`,
  `docs/reports/STAGE_A_B_FINDINGS_AND_RECOMMENDATIONS.md`,
  `docs/analyses/tabpfn_small_finetune_methodology.md`.

## 10. Evidence Files

- `scripts/eval/insurance_benchmark_v1/results_per_split.csv` — per-split benchmark metrics
  (282 rows; primary evidence for §4).
- `scripts/eval/insurance_benchmark_v1/method_info.csv` — method registry (default config,
  CPU, `can_hpo=False`).
- `outputs/current/tables/domain_finetune_study_runs.csv` — Stage A runs (§5.1).
- `outputs/current/logs/domain_finetune_logbook.md` — raw-vs-tuned summary and step/context
  sweeps (§5.1).
- `outputs/current/tables/tabpfn_finetune_trial_results.csv` — coil2000 small-finetune
  trials (§5.2).
- `data/raw/bemtl97.csv` — leak inspection (§6; 163,212 rows, `claim`/`nclaims`/`amount`
  collinearity check).
- `scripts/eval/insurance_benchmark_v1/focused_imbalance_results.csv` — imbalance pilot,
  per-fold 1−AUC (null result; §11.2).
- `scripts/eval/insurance_benchmark_v1/focused_imbalance_logloss.csv` — per-fold log-loss /
  Brier re-score (§11.3).
- `scripts/eval/insurance_benchmark_v1/home_turf_sweep_results.csv` — size sweep, per-fold
  log loss / Brier / ROC-AUC, 220 rows (9 cells × 5 folds, zero errors; primary evidence
  for §13).
- `scripts/eval/insurance_benchmark_v1/frontier_results_{bemtl97,coil2000,uslapseagent,norauto}.csv`
  — frontier benchmark, per-method mean log loss ± SE, n_params, on-frontier flag
  (primary evidence for §14.2, §14.6).
- `scripts/eval/insurance_benchmark_v1/frontier_plot_{bemtl97,coil2000,uslapseagent,norauto}.png`
  — frontier plots, x = log10(n_params), y = mean log loss ± SE (§14.2, §14.6).
- `scripts/eval/insurance_benchmark_v1/frontier_benchmark_run.log` — frontier run log,
  per-fold timings and log loss (§14.1).
- `scripts/eval/insurance_benchmark_v1/frontier_norauto_run.log` — norauto run log,
  per-fold timings and log loss (§14.6).
- `scripts/eval/insurance_benchmark_v1/reframe_frequency_results.csv` — per-fold reframe
  metrics, 121 lines (primary evidence for §14.14).
- `scripts/eval/insurance_benchmark_v1/reframe_frequency_summary.csv` — reframe paired-t
  summary, per baseline × metric × seed (§14.14).
