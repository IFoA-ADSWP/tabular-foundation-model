# Frontier AUC/Brier Re-score — Design Spec

Status: implemented 2026-08-06 (commit 9037b26); §14.11 delivered, acceptance criteria
met (see §14.11.5 of the master report). Extends `docs/analyses/insurance_frontier_benchmark_spec.md`
(D1–D5) with AUC and Brier power columns on the same canonical 5-fold protocol. No
existing evidence files are modified — only `frontier_results_*.csv` regenerated with
new columns.

## 1. Motivation

The canonical frontier protocol scores classification datasets on log loss only, so
"how much better is TabPFN than a standard GLM" cannot be answered on it: the only AUC
pairs are the older 80/20 head-to-head (`docs/archive/MULTI_DATASET_GLM_VS_TABPFN_SUMMARY.md`,
4 datasets, GLM `class_weight='balanced'`, TabPFN `random_state=42` — neither matches
the frontier's method configs) and the 2 lapse datasets (§14.10 of
`docs/analyses/tabpfn_vs_gbdt_baselines_finetuning.md`); Brier — named the "secondary"
metric in the frontier spec §5 — was never emitted. This addendum adds mean ± SE AUC
and Brier per method per dataset so the regime rule (GLM gap ≥ ~2.5% log loss or ≥
~0.05 AUC ⇒ thin-signal/TabPFN-win regime, `docs/analyses/regime_characterization.md`)
applies to TabPFN-vs-GLM on the canonical protocol.

## 2. Scope

### Datasets — all 6 classification frontier datasets (`DATASETS` dict, run_frontier_benchmark.py L103–110)

| dataset | target | drop | rows | pos_rate | sweep rows |
|---|---|---|---|---|---|
| bemtl97 | claim | [nclaims, amount] | 163,212 | 11.2% | yes |
| coil2000 | CARAVAN | [] | 9,822 | 6.0% | yes |
| uslapseagent | surrender | [] | 29,317 | 37.9% | yes |
| norauto | NbClaim | [] | 183,999 | 4.6% | no — fresh |
| ausprivauto0405 | ClaimOcc | [] | 67,856 | 6.8% | no — fresh |
| bemtl16 | number_of_liability_claims | [] | 58,723 | 36.0% | no — fresh |

### Methods — all 9, cost unchanged

The script fits every method in one pass per dataset; restricting to GLM+TabPFN would
not skip a single fit, so keep all rows: `lr`, `logisticglm`, `tweedieglm`,
`poissonglm`, `rf`, `cat`, `lgbm`, `xgb`, `tabpfn`. GLM family = `lr`
(LogisticRegression(random_state=0, max_iter=500)) + `logisticglm` (penalty=None,
lbfgs, max_iter=500) + `tweedieglm`/`poissonglm` (regressors on the binary target,
predicted mean clipped to [1e-6, 1-1e-6] as P(y=1) — already in the protocol, L426–431).
No GBDT-only analysis.

### Metrics

| metric | definition | notes |
|---|---|---|
| AUC | `sklearn.metrics.roc_auc_score(y_true, pp[:,1])` | per fold, then mean ± SE |
| Brier | `sklearn.metrics.brier_score_loss(y_true, pp[:,1])` | identical to the sweep's definition (run_home_turf_size_sweep.py L211–212) |
| log loss | existing `mean`/`se` columns | reference, unchanged |

## 3. Protocol

### 3.1 Reuse feasibility — verified by reading code (nothing was run)

`home_turf_sweep_results.csv` header:
`dataset,n_rows,method,fold,n_estimators,trimmed,error,train_s,infer_s,log_loss,brier,roc_auc`.

It stores **per-fold summary brier and roc_auc (not predictions)** for
cat/lgbm/xgb/tabpfn on bemtl97/coil2000/uslapseagent — 0 NaNs, 5 folds each, under the
same `StratifiedKFold(5, shuffle=True, random_state=42)` splits the frontier script
uses (L378). Fold identity verified: sweep per-fold log-loss means reproduce
`frontier_results_*.csv` `mean` to full float precision (e.g., bemtl97 lgbm
0.3417721022279917 both). **The 3 sweep datasets need zero re-runs for reused
methods** — read `brier`/`roc_auc` alongside `log_loss`.

The 3 no-sweep datasets (norauto/ausprivauto0405/bemtl16) cache nothing per fold (run
logs store only the per-fold log-loss scalar; `frontier_results_*.csv` only mean/se) →
they need fresh TabPFN power: **15 hosted API calls total**. GLM/RF are refit fresh on
every run anyway (CPU, cheap).

### 3.2 Code change — implemented (9037b26)

All inside `run_dataset` (L367–534). No new CLI flag: the run is one-pass and
idempotent (all methods fitted regardless), so `--metrics`/`--rescore-only` add
nothing. Smallest change:

1. `reuse_or_fresh` (L390–405): sweep path — read `brier`/`roc_auc` columns; fresh
   path — append per-fold auc/brier from `pp` at L402.
2. D1 loop (L418–435): after `pp`, append per-fold auc/brier (tweedie/poisson use the
   clipped mu as P(y=1), consistent with L426–431).
3. TabPFN path (L457–488): sweep path reads `brier`/`roc_auc`; fresh path appends
   per-fold auc/brier from `pp` (L482–485).
4. Row dicts gain `mean_auc, se_auc, mean_brier, se_brier`; SE = `std(ddof=1)/sqrt(5)`,
   mirroring L394.
5. CSV columns (L506): `method,mean,se,mean_auc,se_auc,mean_brier,se_brier,n_params,on_frontier`
   — `mean`/`se` stay log loss; existing consumers (plots, §14 tables) unaffected.
6. `sanity_check`: assert sweep-reused brier/roc_auc notna; `mean_auc` ∈ [0.5, 1];
   brier ≥ 0. No single-class guard needed: min pos_rate 4.6% with ≥ 9,822 rows
   guarantees both classes per fold (sweep: 0 NaN roc_auc over 220 rows).

## 4. Output artifacts

- 6 regenerated `frontier_results_<dataset>.csv` with `mean_auc,se_auc,mean_brier,se_brier`.
- No plot change (y-axis stays log loss).
- Delivered as §14.11 (commit 9037b26): results table + per-dataset TabPFN-vs-best-GLM
  deltas (Δ log loss, Δ AUC, Δ Brier) + regime verdict added to the master report.

## 5. Cost & runtime estimate (from run logs, 2026-08-05)

| dataset | wall (last run) | of which TabPFN API | API calls |
|---|---|---|---|
| bemtl97 | ~157s | 0 (reuse) | 0 |
| coil2000 | ~35s | 0 | 0 |
| uslapseagent | ~30s | 0 | 0 |
| norauto | ~504s | ~232s (~46s/call) | 5 |
| ausprivauto0405 | ~160s | ~65s (~13s/call) | 5 |
| bemtl16 | ~184s | ~54s (~11s/call) | 5 |
| **total** | **~18 min** | **~5.8 min hosted** | **15** |

Sources: `frontier_benchmark_run.log` (222s, 3 reuse datasets), `frontier_norauto_run.log`
(504s), `frontier_v1suite_run.log` (344s, ausprivauto0405 + bemtl16). Retry loop
(3 attempts, 10/60/300s backoff): 0 activations in the last runs. AUC/Brier compute
cost: negligible (sklearn one-liners on probabilities already in memory). Hosted API
dollar cost: no per-call pricing in the repo — verify billing at implementation.

## 6. Acceptance criteria

1. All 6 `frontier_results_*.csv` contain the 4 new columns, 9 method rows each.
2. `mean_auc` ∈ [0.5, 1] per method; per-fold AUC may legitimately dip below 0.5
   (6/220 sweep rows, min 0.4196) — assert per-fold > 0.4; brier ≥ 0 everywhere.
3. No protocol drift: reused methods' `mean`/`se` (log loss) identical to current CSVs;
   SEs comparable (same ddof=1, 5 folds).
4. Read-back check: sweep-reused AUC/Brier means equal the `home_turf_sweep_results.csv`
   fold means.
5. §14.11 added to master report: TabPFN vs best-GLM deltas + regime verdict per
   dataset under the existing rule (gap ≥ ~2.5% log loss or ≥ ~0.05 AUC ⇒ thin-signal;
   ≤ ~2% ⇒ GLM-captured).

## 7. Open questions

1. **LR vs LogisticGLM**: keep both as separate rows (current behavior); the regime
   rule consumes best-of-GLM-family per dataset (regime_characterization convention).
2. **Lapse datasets**: extend to spanish_motor_lapse/eudirectlapse? They already have
   5-fold AUC under `run_lapse_benchmark.py` (§14.10) — different harness; excluded
   unless requested.
3. **Brier in the rule**: this addendum adds Brier as reference only; a Brier-gap
   threshold (e.g., ≥ ~0.02) would change the regime rule — team decision.
4. **PR AUC**: used in the old 80/20 summary; not in scope unless requested.
