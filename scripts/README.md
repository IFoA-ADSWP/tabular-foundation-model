# Scripts

One-off experiment scripts, infrastructure and debug tools. Read this before `ls`-ing the directory: the
tree is organised by **what a script is for**, not by when it was written, and two of the directories hold
most of the weight.

**If you are new, start with [`docs/RUNNING.md`](../docs/RUNNING.md)** — it says which environment and which
route. This page is the index of the tree itself.

## Start here by task

| I want to… | Go to |
| --- | --- |
| Run the tests, or the gate | [`../scripts/check.sh`](check.sh), [`bootstrap_dev.sh`](bootstrap_dev.sh) |
| Run the current fine-tuning experiment | [`run_pilot.py`](run_pilot.py) locally, [`gpu_helpers/`](gpu_helpers/) when rented |
| Run the regressor fair test | [`run_fair_test.py`](run_fair_test.py) |
| Run a published benchmark | [`eval/`](eval/) — the frontier, lapse and imbalance suites |
| Run a diagnostic | [`diagnostics/`](diagnostics/) — D1, D2, D3, D5 |
| Build, rescore or check a capture | [`analyses/`](analyses/) |
| Work on a dataset or the wiki | [`infra/`](infra/) |

## The root entry points

| Script | Purpose |
| --- | --- |
| `run_pilot.py` | The fine-tuning pilot: arms, rungs, seeds and folds against the four anchor datasets. Writes a schema-v2 record with dataset and split fingerprints. Runbook §C.2. |
| `run_fair_test.py` | The regressor fair test — four pre-registered frequency/severity targets, policy-grouped folds, capture v4. `--smoke` proves the wiring on CPU and is never a result to quote. Rents nothing by itself. |
| `check.sh` | **The single definition of this repository's checks.** `./scripts/check.sh` runs all eight; `./scripts/check.sh ruff` runs one. CI calls this script per job rather than restating a command. |
| `bootstrap_dev.sh` | Builds `.venv` from `requirements.lock` and asserts the pins (#530). The canonical first command. |
| `new_worktree.sh` | Creates a worktree that actually contains the repository, and removes its own leftovers if the check fails. |
| `check_citations.py` | A bare run id in `docs/` must resolve to `results/<id>/capture.json` with hashes. Run as `./scripts/check.sh citation`. |
| `check_doc_links.py` | Every reference under `docs/` resolves. `plans/` and `archive/` are citations and are skipped. |
| `check_doc_status.py` | Every report in the three tiers states what it is in its first fifteen lines; also enforces the findings registry's shape. |
| `diagnostic_complexity.py`, `analyse_pilot.py` | One-off analysis helpers; see their own docstrings. |

## Subdirectories

| Directory | Files | What lives there |
| --- | --- | --- |
| `eval/` | 106 | The benchmark suites: `insurance_benchmark_v1/` (frontier D1–D5), `lapse_benchmark_v1/`, `insurance_imbalance_pilot/`, `smoke_test/`, `zero_inflation/` (#159, v3.5). Each holds committed result CSVs and logs beside its runners. Hosted client, `tabpfn-client 0.3.3`. |
| `gpu_helpers/` | 18 | **The paid-run path.** `vast_run.sh` rents, bootstraps, polls, pulls and destroys; `bootstrap_pilot.sh` is the on-box installer; `verify_artifacts.py` refuses a run that measured nothing. Shell-checked at `warning` in CI because a syntax error here costs money. |
| `legacy_finetuning/` | 17 | The v2-era fine-tuning line, 2026-04. **Provenance, not canonical**: these do not run on `tabpfn 8.5.0`, whose `finetune_utils` and `get_preprocessed_datasets` were removed. |
| `benchmarks/` | 8 | TabArena-harness runners: the 7-dataset insurance benchmark, the lapse and imbalance pilots, the home-turf size sweep, the regressor-fit measurement. |
| `analyses/` | 7 | Capture and analysis tooling: `make_capture.py`, `rescore.py`, `verdict.py`, `freq_sev_*`, `proxy_resolution.py`. `verdict.py` reproduces the null band the decision log cites (#398). |
| `diagnostics/` | 5 | D1 profiling, D2 importance, D3 reframe, D5 eudirectlapse, and `export_records.py`, which writes the committed table under `docs/analyses/data/`. |
| `infra/` | 11 | Dataset preparation (`prepare_insurance_datasets.py`, `download_datasets.py`), the wiki push, the shared figure style, and the verdict, adoption, diagnostics and baseline figures. |
| `colab_helpers/` | 3 | Superseded R1 launcher path, kept for provenance. |
| `git-hooks/` | 1 | `pre-commit.local`. |

## Benchmarks

| Script | Purpose |
| --- | --- |
| `benchmarks/run_tabarena_insurance_benchmark.py` | Run TabArena benchmark on 7 insurance datasets across foundation / tree / statistical model families |
| `benchmarks/run_smoke_tabarena.py` | Smoke test — single dataset (coil2000), 3 models, validates TabArena setup end-to-end in ~2 min |
| `benchmarks/run_lapse_benchmark.py` | Lapse benchmark — classification (lapse) + regression (premium) on eudirectlapse + spanish_motor_lapse, holdout mode, 3 models |
| `benchmarks/run_tabarena_insurance_imbalance_pilot.py` | Imbalance pilot — `balance_probabilities` vs v1 on coil2000 + uslapseagent (5 folds, reuses v1 splits) |
| `benchmarks/run_home_turf_size_sweep.py` | Home-turf size sweep — 3 datasets × 3 sizes × 5 folds, log loss / Brier / 1−AUC |
| `benchmarks/finish_home_turf_sweep_v2.py` | Revised sweep assembly — drops n_estimators=1, adds n_estimators=8 per cell, retries errored rows, 35-min wall budget (supersedes `finish_home_turf_sweep.py`) |
| `eval/insurance_benchmark_v1/run_frontier_benchmark.py` | Pareto frontier benchmark (power vs parsimony, D1–D5) — log loss / RMSE / Poisson deviance vs n_params, `--regression` mode, 11 datasets; generic CSV mode `--data <csv> --target <col> [--drop a,b]` (issue #46) |
| `eval/insurance_benchmark_v1/rescore_focused_imbalance_logloss.py` | Re-score cached pilot probas on log loss / Brier (post-run only — needs `scripts/experiments/` caches) |

## Zero-inflation study (issue #159)

Synthetic zero-inflated counts, TabPFN `v3.5_default` vs Poisson/ZIP/ZINB GLMs. Report:
[`docs/experiments/zero-inflation/ZERO_INFLATION_TABPFN.md`](../docs/experiments/zero-inflation/ZERO_INFLATION_TABPFN.md).

**Environment.** The sweep was measured with `tabpfn-client 0.5.3` (for `v3.5_default`) and needs `statsmodels`
for the ZIP/ZINB GLMs; `requirements.lock` pins `tabpfn-client 0.3.3` and has no `statsmodels`, so re-running
`run_sweep.py` takes its own venv, as the other v3.5 re-tests did. `analyze.py` and `make_report_charts.py`
read only the committed CSVs and run in `.venv`. Run from the repo root (the API key is read as in the root README).

**Two result files per α.** `results/alpha_<α>/results.csv` holds the five original models and is committed
evidence (its sha256 is in `figures/manifest.json`); the hurdle extension (#159, plan
[`159-zero-inflation-hurdle.md`](../docs/plans/159-zero-inflation-hurdle.md)) writes
`results/alpha_<α>/results_hurdle.csv`, so the original file is never rewritten. Both are read to decide what
is already done: a rerun fills in only missing (arm, π₀, seed, model) cells.

**Models** (`--models`, default all but `tabpfn_recheck`): `poisson_glm`, `zip_glm`, `zinb_glm`, `tabpfn`,
`tabpfn_log1p` → `results.csv`; `hurdle_poisson_glm`, `hurdle_nb_glm` (logit in x + zero-truncated
Poisson / NB2), `tabpfn_hurdle` (TabPFNClassifier on `y > 0` + TabPFNRegressor on the positive rows) and
`tabpfn_recheck` (plain TabPFN refitted, a drift control against the committed `tabpfn` rows) →
`results_hurdle.csv`. The API key is loaded only when a TabPFN model still has a missing cell, so a GLM-only
run needs no key and spends nothing.

**Before adding a model**, run `check_reproducible.py`: the sweep regenerates each cell's data from its seed,
which is only sound if this environment still draws the committed bytes.

```bash
python3 scripts/eval/zero_inflation/check_reproducible.py --alpha 1.0 --seeds 0 5 9
python3 scripts/eval/zero_inflation/run_sweep.py --alpha 1.0 --models hurdle_poisson_glm hurdle_nb_glm
python3 scripts/eval/zero_inflation/run_sweep.py --alpha 1.0 --models tabpfn_recheck --n-seeds 2
python3 scripts/eval/zero_inflation/run_sweep.py --alpha 1.0 --models tabpfn_hurdle
```

| Script | Purpose |
| --- | --- |
| `eval/zero_inflation/run_sweep.py` | Sweep π₀ × 10 seeds for one NB2 dispersion `--alpha`: Poisson/ZIP/ZINB GLMs, the hurdle GLMs, and TabPFN (raw, log1p, two-stage) on mean-matched zero-inflated counts. `--models` picks which to fill in; `--pilot`, `--n-seeds`, `--pi0-grid`, `--n-train`, `--n-test` shrink the grid. Resumable; writes `results.csv` and `results_hurdle.csv` under `results/alpha_<alpha>/` (TabPFN models use API credits) |
| `eval/zero_inflation/check_reproducible.py` | Redraws the cells of `--seeds` (default 0) for `--alpha`, refits `poisson_glm`, and compares with the committed `results.csv`: data-only columns exactly, fit metrics to `--rtol` (default 1e-6). Exit 1 on any mismatch; no API key, no credits |
| `eval/zero_inflation/hurdle.py` | The hurdle arithmetic shared by the GLM and TabPFN hurdles (numpy only; tested by `tests/test_zero_inflation_hurdle.py`) |
| `eval/zero_inflation/hurdle_verdict.py` | The #662 analysis: the drift precondition, the frozen bar (`tabpfn_hurdle` − `tabpfn`, 98.33% t-intervals over 10 seeds) and the verdict it implies, then the contrasts the plan reports alongside. Reads only the committed CSVs; no API key, no credits |
| `eval/zero_inflation/make_hurdle_chart.py` | The #662 result note's chart (NLL gap to ZINB-GLM against π₀, single- and two-stage TabPFN, one panel per α) → `eval/zero_inflation/figures/hurdle_gap_by_alpha.png`, with `hurdle_manifest.json` recording the commit and per-file checksums. The September `manifest.json` is left alone |
| `eval/zero_inflation/analyze.py` | Per-α diagnostic plots into `results/alpha_<alpha>/` (`--alpha`) |
| `eval/zero_inflation/make_report_charts.py` | The report's four charts → `eval/zero_inflation/figures/`, with `manifest.json` recording the producing commit and per-file checksums |

## Infrastructure

| Script | Purpose |
| --- | --- |
| `infra/push_wiki.sh` | Sync `.wiki-content/` to GitHub Wiki |
| `infra/import_backlog_to_github.py` | Import maintenance backlog into GitHub Issues (for when Issues are re-enabled) |
| `infra/download_datasets.py` | Download coil2000, ausprivauto0405, generate freMTPL2freq_binary from freMTPL2freq |
| `infra/prepare_insurance_datasets.py` | Convert CASdatasets `.rda` + raw CSV sources to cleaned CSVs in `data/raw/` (incl. Spanish motor portfolio makers; `--only <stem>` filter) |
| `infra/verdict_figures.py` | The two verdict forest plots, drawn from committed evidence and exported as PDF + 300 dpi PNG (#607) |
| `infra/adoption_figures.py` | The size/drift chart and the method × dataset matrix, drawn from the committed frontier CSVs (#609) |
| `infra/diagnostics_figures.py` | Top-ten overlap and rank agreement across the three families, drawn from the exported D2 table (#610) |
| `infra/baseline_figures.py` | The actuarial baseline verdict as a forest, both budgets, from the v5 captures (#647) |

## Legacy — fine-tuning era (legacy_finetuning/)

These are **provenance, not canonical**: none of them runs on `tabpfn 8.5.0`, whose `finetune_utils` and
`get_preprocessed_datasets` were removed. Most say so in their own docstrings.

| Script | Purpose |
| --- | --- |
| `legacy_finetuning/analyze_round3_results.py` | Analyse Round 3 classifier fine-tuning results |
| `legacy_finetuning/check_saved_finetune_classifier_model.py` | Reload + validate a saved `.tabpfn_fit` artifact |
| `legacy_finetuning/debug_preprocess.py` | Debug TabPFN preprocessing pipeline |
| `legacy_finetuning/diagnose_claimnb_finiteness.py` | Debug tool for TabPFN regressor finiteness issues |
| `legacy_finetuning/evaluate_classifier_homogeneity_proposal.py` | Evaluate homogeneity hypothesis from Stage A results |
| `legacy_finetuning/evaluate_regressor_stability_gate.py` | Evaluate whether regressor config is ready for full rerun |
| `legacy_finetuning/finetune_pilot.py` | Fine-tuning pilot — time per sample under different configs |
| `legacy_finetuning/pilot_timing.py` | Measure per-sample time for TabPFN fine-tuning loop |
| `legacy_finetuning/run_domain_finetune_stage_a.py` | Domain fine-tuning classifier comparison across 4 insurance datasets |
| `legacy_finetuning/run_finetune_crossover_batch_3000.sh` | Crossover batch at 3000 rows |
| `legacy_finetuning/run_finetuned_tabpfn_regression_benchmark.py` | Fine-tuned TabPFN regressor benchmark |
| `legacy_finetuning/run_finetune_first_batch.sh` | First batch of fine-tuning runs |
| `legacy_finetuning/run_finetune_stress_batch_2000.sh` | Stress batch at 2000 rows |
| `legacy_finetuning/run_raw_tabpfn_regression_benchmark.py` | Raw TabPFN regressor benchmark |
| `legacy_finetuning/run_small_finetune_classifier_trial.py` | Local readiness smoke test for classifier fine-tuning |
| `legacy_finetuning/run_small_finetune_regressor_trial.py` | Local readiness smoke test for regressor fine-tuning |
| `legacy_finetuning/summarize_classifier_homogeneity_smoke.py` | Summarise homogeneity smoke-test results |

## Conventions

- A script that writes evidence writes it under `outputs/` (git-ignored, runtime) or `results/<run id>/`
  (committed, and a citation). `./scripts/check.sh evidence` refuses a change to either without the
  `evidence-change` label.
- A new top-level script is a new entry point: add it to the table above in the same change.
- Version era is load-bearing. A number is only meaningful against the environment it was measured in — see
  [`docs/MODEL_VERSIONS.md`](../docs/MODEL_VERSIONS.md).
