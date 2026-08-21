# Prediction Capture for Retrospective Re-scoring — Design Spec

Status: proposed 2026-08-20 (issue #122). Extends
`docs/analyses/insurance_frontier_benchmark_spec.md` (D1–D5) and the AUC/Brier rescope
(`docs/analyses/frontier_auc_brier_rescore_spec.md`) with persisted per-fold test
predictions. No existing evidence files are modified; existing CLI behaviour is
byte-identical unless the new flag is passed.

## 1. Motivation

The canonical frontier protocol commits **aggregates only**: `frontier_results_*.csv`
stores `mean/se/n_params/on_frontier` per method, and the per-fold artefacts that do
exist (`frontier_pr_auc_results.csv`, `results_per_split.csv`) store computed metric
values, never raw predictions. The only prediction cache the project ever had
(`scripts/experiments/*/data/**/results.pkl`, TabArena harness) was explicitly
local-only ("not committed", see the docstring of
`rescore_focused_imbalance_logloss.py`) and no longer exists on any machine.

Consequence: **every new metric question forces a full refit**, including paid hosted
TabPFN API calls. The live example: scoring severity under Gamma/Tweedie deviance
instead of RMSE cannot be done from stored RMSE values — it needs `(y_true, y_pred)`
pairs. The project has already been hit by this class of problem twice: the v1 metric
blindness (corrected by the §14.11 AUC/Brier rescore) and the imbalance-pilot rescore,
which worked only because caches happened to exist at the time.

This spec makes prediction capture a first-class, permanent capability so retrospective
metrics become seconds-long local computations.

## 2. Scope

### In scope

- `scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py`: capture and persist
  per-fold **test-split** predictions for all 9 methods, both classification and
  regression modes, behind an explicit `--save-predictions` flag.
- One `.npz` + one manifest JSON per dataset under
  `scripts/eval/insurance_benchmark_v1/predictions/`.
- Read-back verification and a rescoring demo (Gamma deviance / Tweedie p=1.5 / MAE on
  `spanish_motor_severity` — the motivating use case).

### Out of scope (phase 2 candidates, §7)

- `run_reframe_frequency.py` and `run_tuned_baselines.py` capture.
- Train-split predictions (rejected: ×5 storage for no metric benefit).
- Any change to committed result CSVs, plots, or the reuse protocol's default economics.

## 3. What to store

Per dataset, per seed:

| array | key | dtype | notes |
|---|---|---|---|
| true target | `y_true__fold{k}` | float32 | once per fold (aligned with every method's rows) |
| prediction | `{method}__fold{k}` | float32 | classification: positive-class probability `pp[:,1]`; regression: model output on the stored scale |
| test indices | `test_idx__fold{k}` | int32 | enables fold-integrity checks and feature rejoin; trivial cost |

**Store raw model output, pre-clipping.** The Poisson-deviance clip (`y_pred >= 1e-12`)
and the classifier-style clip (`mu ∈ [1e-6, 1-1e-6]` for tweedieglm/poissonglm on
binary targets, run_frontier_benchmark.py L519–524) are *scoring conventions* applied
inside `metric_fn`. Captured arrays must be the model's actual output; the clipping
conventions are documented in the manifest so a future Gamma/Tweedie rescoring chooses
its own treatment instead of inheriting today's.

## 4. Format and layout

```
scripts/eval/insurance_benchmark_v1/predictions/
  spanish_motor_severity__seed42.npz
  spanish_motor_severity__seed42.manifest.json
  ...
```

`.npz` chosen over parquet/CSV: zero new dependencies (numpy only), compact, and the
analysis surface (`np.load(...)["lgbm__fold0"]`) is one line. Long-format parquet is a
viable alternative if pandas ergonomics are preferred (§7 Q1b).

Manifest JSON (schema v1):

```json
{
  "schema_version": 1,
  "dataset": "spanish_motor_severity",
  "data_file": "spanish_motor_severity.csv",
  "target": "Cost_claims_year",
  "drop": [],
  "problem_type": "regression",
  "primary_metric": "rmse",
  "stored_scale_note": "target stored log1p; scored on stored scale",
  "clip_convention": "poisson_deviance: y_pred clipped >= 1e-12 at scoring time; stored arrays are raw",
  "n_folds": 5,
  "seed": 42,
  "split": "StratifiedKFold(5, shuffle=True, random_state=42)",
  "methods": ["lr", "logisticglm", "tweedieglm", "poissonglm", "rf", "cat", "lgbm", "xgb", "tabpfn"],
  "model_version": "v3_default",
  "tabpfn_client_version": "0.3.3",
  "script_git_sha": "<git rev-parse HEAD at run time>",
  "created_at": "<ISO-8601 UTC>"
}
```

The version block is mandatory: without it, retrospective metrics inherit exactly the
ambiguity the §15 version-drift policy exists to prevent. Stored predictions also
*freeze* the artifact behind published numbers, protecting against future hosted-API
drift.

## 5. Code change sketch

All inside `run_frontier_benchmark.py`; no changes to other scripts.

1. New flag: `--save-predictions` (opt-in, see cost note below). Implies fresh fits for
   every method — same mechanism `--pr-auc` already uses to defeat sweep reuse
   (L462–466) — because reused sweep rows carry no predictions.
2. Capture seam: the existing `record_fold` hook (L453) gains the fold's `y_true`,
   `y_pred`, and `te` indices. Call sites: GBDT fresh path (after `pp` at L493), D1 GLM
   loop (store raw `mu` pre-clip, L519–524), TabPFN fresh path (§4a, L548+), and the
   regression branch of `run_dataset` (same pattern, `model.predict(Xte)`).
3. Writer: end of `run_dataset()` — `np.savez_compressed` + manifest; assert before
   writing: per-fold lengths equal `len(te)`, no NaN/Inf in any array, all 9 methods ×
   5 folds present.
4. Read-back check (same run): reload the `.npz`, recompute the primary metric per fold
   from stored pairs, compare to the recorded fold scores (tolerance 1e-9 CPU;
   documented tolerance for tabpfn if the API is non-bitwise-deterministic).
5. Without the flag: behaviour byte-identical to today (reuse economics untouched).

**Why opt-in, not default-on:** forcing fresh fits defeats sweep reuse, and reuse exists
precisely to avoid repeat hosted-API calls (bemtl97/coil2000/uslapseagent tabpfn arms).
Default-on would silently convert every routine rerun into an API-spending run. An
explicit flag keeps the cost decision visible at the CLI. (This corrects an earlier
informal suggestion of default-on.)

## 6. Cost & runtime estimate

| item | estimate | basis |
|---|---|---|
| capture + write overhead | negligible | arrays already in memory; one compressed write per dataset |
| storage, all 12 datasets | ~50 MB uncompressed / ~20–30 MB npz | Σ rows ≈ 1.39M × 9 methods × 4 B; largest single file freMTPL2freq ≈ 24 MB |
| extra API calls when capturing on the 3 sweep datasets | ≤ 15 hosted calls (~5.8 min) | identical to the AUC/Brier rescore's forced-fresh accounting (that spec §5, 2026-08-05 logs) |
| regression + no-sweep datasets | 0 extra calls | they fit fresh on every run regardless |

## 7. Acceptance criteria

1. `--save-predictions` on one classification and one regression dataset produces
   `.npz` + complete manifest: 9 methods × 5 folds, dtypes per §3.
2. Read-back: primary metric recomputed from stored pairs matches
   `frontier_results_<dataset>.csv` means within tolerance; fold sizes match
   `StratifiedKFold(5, shuffle=True, random_state=42)` partition sizes.
3. No-flag runs produce byte-identical stdout/artifacts to current behaviour.
4. Manifest records model version, client version, script SHA, seed, clip conventions.
5. Rescoring demo delivered: Gamma deviance, Tweedie(p=1.5), MAE computed from stored
   `spanish_motor_severity` pairs, alongside the RMSE baseline — closing the open
   severity metric-sensitivity question (TabPFN trails LGBM by only ~2.2–2.7% RMSE
   there; the other severity gaps, +46–48%, are not expected to flip).

## 8. Open questions

1. **Binary artifacts in git** — commit `.npz` directly (<100 MB total, consistent with
   "results committed alongside the code"), or route through git-lfs / release assets?
   Org-norms decision.
2. **Parquet alternative** — switch format if pandas ergonomics beat npz compactness
   for the analysis workflow.
3. **Phase-2 capture targets** — `run_reframe_frequency.py` (per-fold CSV already
   exists; predictions don't) and `run_tuned_baselines.py` (append-mode CSV; cheap win).
4. **Backfill strategy** — opportunistic (capture piggybacks on the next needed rerun,
   e.g., the severity sensitivity check) vs a dedicated full-suite pass (bounded API
   spend, ~15 extra calls). Recommendation: opportunistic; the demo in AC5 already
   backfills the highest-value dataset.
