# Alternative-Metrics Re-score for Regression Benchmarks — Design Spec

Status: proposed 2026-08-20 (issue #123). Consumer of the prediction-capture artefact
(`docs/analyses/prediction_capture_rescore_spec.md`, issue #122): computes additional
insurance-native metrics **from stored per-fold predictions** — no refits, no hosted-API
calls. Extends the metric layer of `insurance_frontier_benchmark_spec.md` (D4) and the
statistics conventions of `frontier_auc_brier_rescore_spec.md` (§14.11 pattern).

## 1. Motivation

Regression/severity datasets are currently scored on a single metric each — RMSE for
the four continuous targets, Poisson deviance for the two count targets
(`run_frontier_benchmark.py`, `DATASETS` dict L129–134). Three problems:

1. **Tail geometry**: squared error on heavy-tailed severity is dominated by large
   claims. Log-scale storage mitigates but does not eliminate the concern, and
   `ausprivauto0405_vehvalue` is scored on the raw scale.
2. **Zero-inflation contamination**: `bemtl97_amount` is ~89% zero mass (regime
   characterization §2); RMSE-on-log1p there partly measures the zero/non-zero split,
   not severity-given-a-claim.
3. **GLM-family inconsistency**: the suite contains Tweedie/Poisson GLMs as *models*
   but never scores with the GLM-family *deviances* (Gamma, Tweedie p∈(1,2)).

Decisive open question: `spanish_motor_severity` — TabPFN trails LGBM by only
~2.2–2.7% RMSE (master report §14.10) — is the one severity verdict a metric swap could
plausibly flip. The +46–48% gaps elsewhere are not.

## 2. Relationship to #122

Hard dependency: this spec consumes `predictions/<dataset>__seed<seed>.npz` artefacts.
Until a dataset is captured, its alternative metrics require one capture run (bounded
API cost per #122 §6). Once captured, any future metric is a seconds-long local
computation — that is the point of the split: #122 is the storage layer, this is the
metric layer.

## 3. Metric additions

All via `sklearn.metrics` (zero new dependencies):
`mean_gamma_deviance`, `mean_tweedie_deviance`, `mean_absolute_error`.

| metric | definition | applies to | notes |
|---|---|---|---|
| Gamma deviance | `mean_gamma_deviance(y_true, y_pred)` | severity, positive targets only | relative-error geometry; severity-given-a-claim native |
| Tweedie deviance p=1.5 | `mean_tweedie_deviance(y_true, y_pred, power=1.5)` | zero-inflated severity / pure premium | valid for y_true ≥ 0 when 1 < p < 2 |
| MAE | `mean_absolute_error(y_true, y_pred)` | all 6 regression datasets | median-consistent; robust tail contrast to RMSE |
| Poisson deviance | existing primary | frequency datasets | unchanged |

### Scale and zero-handling rules (per dataset)

Deviances are **not transform-invariant**, and stored targets are log/log1p — so
alternative deviances are computed on the **euro scale** after inverse-transforming
both `y_true` and `y_pred` with the dataset's stored-scale inverse:

| dataset | stored scale | inverse fn | zero mass | gamma dev | tweedie 1.5 | MAE |
|---|---|---|---|---|---|---|
| ausautoBI8999 | log `AggClaim` | `exp` | verify at impl. | full (if y>0) else positive-subset | full | euro scale |
| bemtl97_amount | log1p `amount` | `expm1` | ~89% | **positive subset only** | full | euro scale |
| spanish_motor_severity | log1p cost | `expm1` | verify at impl. | full if claims-only, else positive-subset | full | euro scale |
| ausprivauto0405_vehvalue | raw `VehValue` | identity | none expected | full | full | raw scale |
| freMTPL2freq / spanish_motor_freq | counts | identity | n/a | n/a | optional | count scale |

Implementation guards: clip inverse-transformed predictions to ≥ 1e-9 before `exp`/
`expm1` (overflow/negative guard); assert `y_true > 0` on gamma-deviance subsets;
record per-dataset zero mass in the output header row.

### Known limitation (documented, accepted)

Models were trained to predict the stored scale; inverse-transformed predictions are
median-biased on the euro scale (Jensen). This bias applies **uniformly to every
method**, so metric-sensitivity *rankings* remain valid; absolute euro-scale levels are
not interpretable without a smearing correction (Duan 1983) — out of scope, §8 Q3.

## 4. Variability and statistics

House conventions, identical to the AUC/Brier rescore (§14.11):

- Per-fold metric values → **mean ± SE** with `SE = std(ddof=1)/sqrt(n_folds)`.
- **Paired t-test** on per-fold deltas: TabPFN vs best GLM family member, and TabPFN vs
  best GBDT, per metric per dataset (mirrors `analyze_pr_auc.py`).
- Rank of every method per metric (min-rank ties).
- Seed stability table wherever multi-seed runs exist (reframe pattern).

## 5. Deliverables

1. `scripts/eval/insurance_benchmark_v1/rescore_altmetrics.py` — reads
   `predictions/*.npz` (+ manifests), emits:
   - `alt_metrics_per_fold.csv` — dataset, seed, method, fold, metric, value, scale-handling flags
   - `alt_metrics_summary.csv` — per dataset × method × metric: mean, SE, rank, paired-test p-values
2. Master-report addendum (**§14.15-style**): per-dataset verdict table under each
   metric; explicit answer to "does the spanish_motor_severity ranking flip?".
3. Frontier membership is **not** recomputed (see §8 Q1) — alternative metrics are
   reported alongside; the canonical frontier stays defined on the primary metric.

## 6. Cost & runtime

| item | estimate |
|---|---|
| rescoring compute | seconds–minutes, CPU-only, from stored arrays |
| hosted-API calls | **0** for captured datasets; one capture run per uncaptured dataset (per #122 §6) |
| new dependencies | none |

## 7. Acceptance criteria

1. All 6 regression datasets have per-fold + summary rows for every applicable metric
   in §3, with SEs matching the ddof=1/sqrt(5) convention.
2. Read-back sanity: RMSE recomputed from stored pairs matches committed
   `frontier_results_*.csv` means within tolerance (validates the #122 artefact end-to-end).
3. Zero-mass and transform handling per §3 recorded in outputs; gamma-deviance subsets
   asserted positive.
4. Paired tests delivered for TabPFN vs best GLM and vs best GBDT on every new metric.
5. Master-report addendum answers the motivating question explicitly:
   spanish_motor_severity verdict under Gamma deviance and Tweedie(1.5) vs RMSE —
   flipped or stable, stated with fold-level evidence.

## 8. Open questions

1. **Frontier recomputation under alternative metrics** — off-frontier verdicts are
   currently primary-metric-only. Recomputing membership per metric changes headline
   claims and should be a deliberate follow-up, not a side effect.
2. **Classification side** — already rich (log loss/AUC/Brier/PR-AUC/lift10); no
   additions proposed. Revisit only if a reviewer asks.
3. **Smearing correction** for euro-scale debiasing — noted, out of scope.
4. **Frequency targets** — keep Poisson deviance primary; Tweedie(1.5) on counts is
   optional (pure-premium framing needs exposure/premium data not in the benchmark).
