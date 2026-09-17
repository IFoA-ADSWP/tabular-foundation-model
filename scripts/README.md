# Scripts

One-off experiment scripts, infrastructure, and debug tools. Ordered by purpose. Scripts tagged (Legacy — fine-tuning era, provenance) live in `legacy_finetuning/`. Active benchmark runners live in `benchmarks/`; shared tooling in `infra/`.

## Benchmarks

| Script | Purpose |
|--------|---------|
| `benchmarks/run_tabarena_insurance_benchmark.py` | Run TabArena benchmark on 7 insurance datasets across foundation / tree / statistical model families |
| `benchmarks/run_smoke_tabarena.py` | Smoke test — single dataset (coil2000), 3 models, validates TabArena setup end-to-end in ~2 min |
| `benchmarks/run_lapse_benchmark.py` | Lapse benchmark — classification (lapse) + regression (premium) on eudirectlapse + spanish_motor_lapse, holdout mode, 3 models |
| `benchmarks/run_tabarena_insurance_imbalance_pilot.py` | Imbalance pilot — `balance_probabilities` vs v1 on coil2000 + uslapseagent (5 folds, reuses v1 splits) |
| `benchmarks/run_home_turf_size_sweep.py` | Home-turf size sweep — 3 datasets × 3 sizes × 5 folds, log loss / Brier / 1−AUC |
| `benchmarks/finish_home_turf_sweep_v2.py` | Revised sweep assembly — drops n_estimators=1, adds n_estimators=8 per cell, retries errored rows, 35-min wall budget (supersedes `finish_home_turf_sweep.py`) |
| `eval/insurance_benchmark_v1/run_frontier_benchmark.py` | Pareto frontier benchmark (power vs parsimony, D1–D5) — log loss / RMSE / Poisson deviance vs n_params, `--regression` mode, 11 datasets; generic CSV mode `--data <csv> --target <col> [--drop a,b]` (issue #46) |
| `eval/insurance_benchmark_v1/rescore_focused_imbalance_logloss.py` | Re-score cached pilot probas on log loss / Brier (post-run only — needs `scripts/experiments/` caches) |

## Zero-inflation study (issue #159)

Run from the repo root (the API key is read from the root `.env`). Report: `docs/reports/ZERO_INFLATION_TABPFN.md`.

| Script | Purpose |
|--------|---------|
| `eval/zero_inflation/run_sweep.py` | Sweep π₀ × 10 seeds for one NB2 dispersion `--alpha`: Poisson/ZIP/ZINB GLMs vs TabPFN (raw and log1p) on mean-matched zero-inflated counts; resumable, writes `results/alpha_<alpha>/results.csv` (uses API credits) |
| `eval/zero_inflation/analyze.py` | Per-α diagnostic plots into `results/alpha_<alpha>/` (`--alpha`) |
| `eval/zero_inflation/make_report_charts.py` | The report's four charts → `outputs/current/figures/zero_inflation_*.png` |

## Infrastructure

| Script | Purpose |
|--------|---------|
| `infra/push_wiki.sh` | Sync `.wiki-content/` to GitHub Wiki |
| `infra/import_backlog_to_github.py` | Import maintenance backlog into GitHub Issues (for when Issues are re-enabled) |
| `infra/download_datasets.py` | Download coil2000, ausprivauto0405, generate freMTPL2freq_binary from freMTPL2freq |
| `infra/prepare_insurance_datasets.py` | Convert CASdatasets `.rda` + raw CSV sources to cleaned CSVs in `data/raw/` (incl. Spanish motor portfolio makers; `--only <stem>` filter) |

## Legacy — Fine-tuning Era (legacy_finetuning/)

| Script | Purpose |
|--------|---------|
| `legacy_finetuning/analyze_round3_results.py` | Analyse Round 3 classifier fine-tuning results (Legacy — fine-tuning era, provenance) |
| `legacy_finetuning/check_saved_finetune_classifier_model.py` | Reload + validate a saved `.tabpfn_fit` artifact (Legacy — fine-tuning era, provenance) |
| `legacy_finetuning/debug_preprocess.py` | Debug TabPFN preprocessing pipeline (Legacy — fine-tuning era, provenance) |
| `legacy_finetuning/diagnose_claimnb_finiteness.py` | Debug tool for TabPFN regressor finiteness issues (Legacy — fine-tuning era, provenance) |
| `legacy_finetuning/evaluate_classifier_homogeneity_proposal.py` | Evaluate homogeneity hypothesis from Stage A results (Legacy — fine-tuning era, provenance) |
| `legacy_finetuning/evaluate_regressor_stability_gate.py` | Evaluate whether regressor config is ready for full rerun (Legacy — fine-tuning era, provenance) |
| `legacy_finetuning/finetune_pilot.py` | Fine-tuning pilot — time per sample under different configs (Legacy — fine-tuning era, provenance) |
| `legacy_finetuning/pilot_timing.py` | Measure per-sample time for TabPFN fine-tuning loop (Legacy — fine-tuning era, provenance) |
| `legacy_finetuning/run_domain_finetune_stage_a.py` | Domain fine-tuning classifier comparison across 4 insurance datasets (Legacy — fine-tuning era, provenance) |
| `legacy_finetuning/run_finetune_crossover_batch_3000.sh` | Crossover batch at 3000 rows (Legacy — fine-tuning era, provenance) |
| `legacy_finetuning/run_finetuned_tabpfn_regression_benchmark.py` | Fine-tuned TabPFN regressor benchmark (Legacy — fine-tuning era, provenance) |
| `legacy_finetuning/run_finetune_first_batch.sh` | First batch of fine-tuning runs (Legacy — fine-tuning era, provenance) |
| `legacy_finetuning/run_finetune_stress_batch_2000.sh` | Stress batch at 2000 rows (Legacy — fine-tuning era, provenance) |
| `legacy_finetuning/run_raw_tabpfn_regression_benchmark.py` | Raw TabPFN regressor benchmark (Legacy — fine-tuning era, provenance) |
| `legacy_finetuning/run_small_finetune_classifier_trial.py` | Local readiness smoke test for classifier fine-tuning (Legacy — fine-tuning era, provenance) |
| `legacy_finetuning/run_small_finetune_regressor_trial.py` | Local readiness smoke test for regressor fine-tuning (Legacy — fine-tuning era, provenance) |
| `legacy_finetuning/summarize_classifier_homogeneity_smoke.py` | Summarise homogeneity smoke-test results (Legacy — fine-tuning era, provenance) |
