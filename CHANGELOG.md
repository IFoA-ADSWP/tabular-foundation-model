# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- feat: a run records its declared and resolved model version — issue #239: the run manifest and the capture manifest now carry `model_version_declared` (the registry's literal) beside `model_version` (what execution resolved) and `model_version_mismatch` (`true`/`false`/`null`), computed by one function (`version_mismatch`) so the two artifacts cannot disagree. A mismatch is **recorded, not enforced**: #233 owns the reuse predicate and needs exactly `false` to reuse a row, while `null` (an ad-hoc `--data`/filtered run, which declares nothing) is an absence and never a pass. `--experiment` sets the declared value from `experiments.toml`; the resolver's env-first order and the registry's literal-only load are unchanged
- fix: a mock launch's log stays out of the working tree — issue #280: `vast_run.sh`'s `cleanup()` fetched the container log into a hardcoded `$REPO_DIR/outputs/gpu-pilot/logs`, so every mock launch in `pytest tests/ -q` left logs in the directory the runbook treats as the record of paid launches (`outputs/gpu-pilot/logs/**` is deliberately kept by `.gitignore`). The log now lands under `$OUTDIR/logs`, beside the launch's record and ledger, so `VAST_OUTDIR` isolates a mock launch completely; a real launch's default path is unchanged, and the suite pins both halves — the mock's placement behaviourally, in the existing full-path launch, and the default by evaluating the launcher's own `OUTDIR`/`LOG_DIR` lines
- feat: frontier classification reads its experiment — issue #231: the classification frontier stops reading its dataset list, method lists, metric fallback and fold constructor from code. `experiments.toml` decides the dataset, the compared methods (in declared order, hosted TabPFN last), the metric and the folds; `src/experiment_spec.make_folds(kind, n_folds, seed)` is the one splitter for both modes. Methods dispatch through a code-side table keyed by the declared id — a method the file names but the code cannot build fails at selection, and an unknown metric name raises instead of falling back to log loss. The all-datasets path keeps the CLI `--seed` so split-stability runs still fold at that seed; `--experiment` uses the declaration's seed and fold count. No computation changes: the same `coil2000` command on the pre-change tree is bit-identical on every shared column. Output filenames and capture stems are unchanged. The `DATASETS` constant stays only for `run_tuned_baselines` until #235
- feat: record contract — issue #241: a pilot arm record now declares `schema_version` 3 and carries a `provenance` block with one vocabulary defined in `src/provenance.py`: **dataset** (name, file, target, drop columns, sha256 over the bytes on disk, shape, source pinning), **split** (fold count, seed, train-index sha256, and the fold construction as a `{constructor, params}` rule rather than a description string), **model** (version resolved from `src/model_version.py`, weights sha256, client version) and **code** (git sha, dirty flag, runtime versions, container image). No pilot record has ever carried a model version before, so two pilot numbers from different model eras could not be compared; `weights_sha256` corroborates the version and never substitutes for it. `read_record`/`verdict` turn any record into `comparable`, `partial` or `unusable` and name the missing keys by index (`provenance.model.version`), dispatching on a `schema_version` per record kind and failing closed on an unknown version, an explicit null or a bool rather than guessing; the eight v2 arm records and the four v1 capture manifests are read through their documented pre-block keys and come out `partial` (missing their model version and git sha; missing the dataset and split fingerprints), the records that identify neither come out `unusable`, and none is rewritten. `model.version_source` records that the pilot's version is the resolver's declaration, not a pinned estimator (follow-up #285). `dataset_fingerprint` now takes the frame plus target and drop columns instead of resolving a dataset name, so a second runner can call it, and the pilot adapter records its dataset declaration's drop columns; `analyse_pilot.py` reads schema-3 records unchanged and no committed record under `outputs/` or `results/` is modified. Vocabulary and the version-not-hash decision: `docs/adr/0003-record-contract-and-model-version.md`; *record* and *verdict* added to `GLOSSARY.md`
- feat: one diagnostic record writer — issue #211: the pilot's provenance helpers (`dataset_fingerprint`, `inference_context_rows`, `assert_matched_context`) move into `src/provenance.py` and are imported back by `scripts/run_pilot.py` with identical results; `write_diagnostic_record` is the one writer D1–D5 emit through, with a single field definition (`DiagnosticRecord`), a `schema_version`, one `<diagnostic>/<run_id>/` directory per record holding `record.json` (source of truth) plus `record.csv`, and a **refusal** to replace an existing record, so a stale `csv.DictWriter` header, a split record and a re-stamped old record are structurally impossible. Records carry the resolved model version, seed, dataset fingerprint, runtime versions and the matched-context assertion's evidence, ready for #241's `provenance` block. `scripts/diagnostics/d1_profiling.py` is the first consumer; `outputs/diagnostics/` is git-ignored and D1 exposes no flag that could write elsewhere. Pilot schema stays 2 and no committed record changes
- docs: the paid-run path gets its vocabulary and its spine — ADR `docs/adr/0002-launch-identity-and-the-spend-gate.md` records the three contracts settled on issue #245: a launch id minted before any spend with each run's id derived from it, a spend gate that decides over four pre-spend checks and records a refusal, and the provider CLI as the seam with the mock as its second implementation. `GLOSSARY.md` gains *launch*, *launch id*, *arrival* and *spend gate*; *run* is unchanged. No code changes
- feat: experiment registry — issue #230: the frontier suite's datasets, methods and experiments are declared once in `scripts/eval/insurance_benchmark_v1/experiments.toml`, read by a fail-closed loader (`src/experiment_spec.py`) that refuses unknown keys, an unrecognised schema version, duplicate ids, dangling references and missing fields by name; `run_frontier_benchmark.py --experiment <id>` selects a registered experiment and stamps its id into the run manifest, the capture manifest and every results-CSV row, records the resolved model version, and refuses a `--seed` that contradicts the experiment's declaration. No computation changes: the same command on the pre-change tree gives bit-identical values
- docs: count/frequency targets reframed as classification — §14.14 (2026-08-07, issue #67): Spanish motor freq (53,502 rows) re-expressed as binary claim/no-claim (11.1% positive) and ordinal 0/1/2+ (88.9/6.3/4.8%); TabPFN ranks #1 on all 5 binary and all 4 ordinal metrics — AUC 0.7170 vs lgbm 0.7090 (p=0.0010, seed 42) and 0.7165 (p=0.0020, seed 7); PR-AUC rank 1 but within noise (p=0.1165); poissonglm/tweedieglm collapse on the reframe (constant prediction, AUC 0.5000); count axis unchanged (Poisson deviance stays GBDT/GLM territory, §14.9); new scripts run_reframe_frequency.py/analyze_reframe_frequency.py + reframe_frequency_results.csv/reframe_frequency_summary.csv; PR not yet merged (no commit ref)
- docs: finality test — §14.13 (2026-08-07): tuned/feature-engineered classical baselines (lr_tuned, glm_eng, lgbm_tuned, cat_tuned, rf_tuned) on the canonical folds; TabPFN stays AUC/PR-AUC #1 of 14 methods on all 6 datasets, no baseline beats it at p<0.05; calibration gains two small documented exceptions (ausprivauto0405 log loss/Brier vs the linear family, bemtl97 Brier vs lgbm, ~1e-4); tuned GBDTs regressed vs defaults (5/6 datasets); TabFM closed out by assessment (not run — OOM on 8 GB + non-commercial weights); one-pager + report registry updated
- docs: human-voice cleanup pass — removed AI-assistant framing and phantom file references (papers/status/analyses/notebooks/data)
- docs: frontier AUC/Brier rescore — §14.11 addendum (2026-08-06): per-fold AUC/Brier in `frontier_results_*.csv`; ausprivauto0405 "DOMINATED" retracted to calibration tie + ranking edge; verdict reframed to best risk-ranking model (TabPFN AUC #1 of 9 methods on all 6 classification datasets); stale-verdict reconciliation across regime/portfolio/papers + wiki reframe (commits 4e7912c, 9037b26, cea967d, ced3ac9)
- docs: ranking-robustness addendum — §14.12 (2026-08-06): PR AUC #1 on all 6 (paired-significant 5/6), all AUC edges significant under paired fold tests, seed-stable across 3 seeds; top-decile lift dataset-dependent (4/6 rank 1) — triage claim scoped accordingly
### Added
- Metrics explainer — log loss vs AUC vs Brier, imbalance mechanism, insurance reading guide — `docs/analyses/metrics_explained.md` (wiki: Metrics-Explained)

## [v8.2.0] — 2026-08-06

Benchmark suite release: TabArena harness, parsimony frontier, lapse settlement, Spanish motor portfolio, regression Phase 2, adoption regime.

### Added
- TabArena benchmark harness + v1 suite: 6 classification + 3 regression insurance datasets, 10 models, 5-fold CV (seed 42), same-fold comparisons — `scripts/eval/insurance_benchmark_v1/`
- Parsimony frontier analysis: accuracy-per-complexity across 12 datasets, per-dataset verdicts — `scripts/eval/` frontier outputs
- Lapse settlement benchmark: eudirectlapse class + regression via TabArena bundle — `scripts/eval/lapse_benchmark_v1/`
- Spanish motor portfolio: frequency, lapse, severity variants + benchmark naming canon (issue #27a)
- Regression Phase 2: RMSE + Poisson-deviance frontiers, 4 datasets (issue #27 D4)
- Home-turf size sweep: 3 datasets × 3 sizes × TabPFN (n8/n1/default) + GBDT baselines — `home_turf_sweep_results.csv`
- Imbalance pilot — `scripts/eval/insurance_imbalance_pilot/`
- Benchmark summary one-pager for actuarial colleagues — `docs/archive/TABPFN_BENCHMARK_SUMMARY.md`
- Regime characterization + adoption guidance (issues #52/#53) — `docs/analyses/regime_characterization.md`
- TabPFN levers assessment: fine-tuning / HPO / ensembling (issue #54)
- Version-drift re-test policy (issue #55)
- `scripts/infra/make_notebook.py` — clone template notebooks (strips outputs) for new experiments
- (earlier, previously unversioned) `LICENSE` (MIT), `CHANGELOG.md`, `tests/` smoke test, wiki + backlog sync tooling

### Changed
- Scripts reorg: active benchmarks → `scripts/benchmarks/`, shared tooling → `scripts/infra/`, legacy fine-tuning → `scripts/legacy_finetuning/` (issue #27)
- Benchmark protocol: single 80/20 split → 5-fold CV; TabPFN `model_path` pinned to `v3_default`
- Replication notebook loads bundled `data/raw/eudirectlapse.csv` first — R/CASdatasets no longer required (fallback retained)
- API key removed from code; `TABPFN_API_KEY` env var with documented setup

### Removed
- Superseded `finish_home_turf_sweep.py` and `STATUS_REPORT_FINAL.md` (superseded by the report registry); `.venv/` artifacts untracked

### Fixed
- `bemtl97` label-leak dataset excluded from frontier results (leak-fixed version used, §6 master report)
- Stale and phantom file references removed across docs (human-voice cleanup, PR #64)
- Colab widget metadata stripped from notebooks

### Headline verdict
TabPFN is a small-data specialist, not a general engine: wins 8/9 size-sweep cells at ≤5K rows and the Spanish lapse + premium-regression cases, but sits off the parsimony frontier 5 of 12 times at scale. Adoption decision rule: `docs/analyses/regime_characterization.md`. One-page summary: `docs/archive/TABPFN_BENCHMARK_SUMMARY.md`.

## [0.0.0] — pre-release

Initial state. No versioned release. Pre-licence, pre-changelog, pre-tests.
