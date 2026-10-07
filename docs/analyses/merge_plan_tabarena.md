# TabArena Benchmark Branch — Staged Merge Plan

> **STATUS: MERGED 2026-08-04** — PR #51 merged to `main` (merge commit `31d40a5`; final branch tip `f7790ce`, 44 commits). All 5 stages and all pre-merge fixes complete; registry path check post-merge clean. Follow-ups tracked as issues #52–#57.

Coordination/ops document — not a research report; no `docs/REPORT_REGISTRY.md` row is added for this file.
Branch: `feat/tabarena-benchmark` vs `origin/main` — 44 commits, ~86 files. Diff was additive + script reorg moves (7 committed CSVs in `data/raw/`, ~510K rows total). Two merge commits had already reconciled the branch with `origin/main`; final pre-merge `git merge origin/main` resolved cleanly (`ed6de3a`).

## 1. What this branch contains

All research work for issue #27 (TabArena insurance frontier benchmark).

- **Data** — `data/raw/` 7 benchmark CSVs:

  | Dataset | Rows | Notes |
  |---|---|---|
  | `uslapseagent` | 29K | |
  | `bemtl97` | 163K | carries known label leak (`nclaims`/`amount`) — excluded from conclusions |
  | `bemtl16` | 59K | |
  | `ausautoBI8999` | 22K | |
  | `norauto` | 184K | |
  | `spanish_motor_freq.csv` | 53,502 × 21 | target `N_claims_year`, 11.1% claims > 0; leak exclusions: `N_claims_history` / `R_Claims_history` (current-year leak, AUC 0.76/0.92), `Cost_claims_year` is the sibling target |
  | `spanish_motor_lapse.csv` | 53,502 × 23 | target `LapseB`, 35.4% positive; `Date_lapse` excluded (AUC 0.85) |

  Plus the raw source dir `data/raw/Spanish motor portfolio/` (Segura-Gisbert et al. 2024, "Dataset of an actual motor vehicle insurance portfolio": `Motor vehicle insurance data.csv`, `Descriptive of the variables.xlsx`, `sample type claim.csv`).

  `scripts/infra/prepare_insurance_datasets.py` regenerates the CASdatasets-derived CSVs from `.rda` files, and now also carries two additional makers (`make_spanish_motor_freq`, `make_spanish_motor_lapse`) with a CSV-source branch — the worktree has no `.rda` sources for the Spanish data — plus an `--only` CLI filter.

- **Benchmark scripts** (`scripts/`):

  | Script | Purpose |
  |---|---|
  | `run_smoke_tabarena.py` | pipeline validation (coil2000) |
  | `run_lapse_benchmark.py` | lapse classification + regression |
  | `run_tabarena_insurance_benchmark.py` | v1 baseline: 9 tasks, 8 models (TabPFN / GBDTs / GLMs / RF) |
  | `run_tabarena_insurance_imbalance_pilot.py` | imbalance hypothesis; reuses v1 splits |
  | `run_home_turf_size_sweep.py` + `finish_home_turf_sweep_v2.py` | 3 datasets × 3 sizes × 5 folds |
  | `scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py` | issue #27 deliverable — Pareto frontiers, `--regression` flag, D1–D5; now also registers `spanish_motor_freq` (target `N_claims_year`, metric `poisson_deviance`, no `log_exposure` — uniform ~1yr exposure) |
  | `scripts/eval/insurance_benchmark_v1/rescore_focused_imbalance_logloss.py` | log-loss / Brier re-score of the pilot; post-run only — needs uncommitted `scripts/experiments/` caches |

- **Evidence** — `scripts/eval/{smoke_test, lapse_benchmark_v1, insurance_benchmark_v1, insurance_imbalance_pilot}/`: ~60 files — leaderboards, `results_per_split.csv`, 11 `frontier_results_<dataset>.csv` + PNG plots (10 → 11 with `frontier_results_spanish_motor_freq.csv` + `frontier_plot_spanish_motor_freq.png`), Pareto PDFs/HTML explorers. `insurance_benchmark_v1` covers 9 task ids / 7 datasets; the frontier covers 11 datasets (6 classification + 5 regression — `spanish_motor_freq` is counted with the regression family, metric `poisson_deviance`), 9 methods for classification / 8 regressors.

- **Docs** — `docs/analyses/insurance_frontier_benchmark_spec.md` (D1–D5 design), `docs/analyses/tabpfn_vs_gbdt_baselines_finetuning.md` (master report, §1–§14.9), `docs/analyses/benchmark_portfolio.md` (benchmark portfolio + naming canon, `58dde49`), `docs/archive/sessions/2026-07-28-tabarena-benchmark-setup.md`, a `docs/REPORT_REGISTRY.md` row, and the `TASKS.md` #27 / #27a rows.

## 2. Staged implementation plan (5 stages, in merge order)

Status legend: all five stages are DONE — the work exists committed on the branch; nothing is merged to `origin/main` yet.

| Stage | Contents | Status | Rationale |
|---|---|---|---|
| 1 — Data + prep | 7 CSVs, prep script, `data/README.md` update | DONE (see 2.1) | nothing runs without data |
| 2 — Core harness (v1) | smoke + lapse + insurance benchmark scripts, eval outputs, API-key docs | DONE | v1 is imported by the pilot |
| 3 — Hypothesis work | imbalance pilot + size sweep + results | DONE | sweep feeds Stage 4 |
| 4 — Frontier (issue #27 deliverable) | frontier script, results + plots, rescore script | DONE (see 2.4) | depends on sweep results |
| 5 — Docs umbrella | spec, master report, portfolio + canon, registry row, `TASKS.md` | DONE (see 2.5) | merge last so references don't dangle |

### 2.1 Stage 1 — Data + prep

- 7 CSVs in `data/raw/`, `scripts/infra/prepare_insurance_datasets.py`, and a `data/README.md` update.
- Status: DONE — data CSVs + prep script in commit `4b6be6f`; `data/README.md` update in `58dde49`.
- The prep commit also brings the Spanish motor makers (CSV-source branch, `--only` filter) and the `Spanish motor portfolio/` raw source dir.
- The `data/README.md` gap originally flagged here (5 datasets undocumented, beMTPL16-vs-`bemtl16` naming collision) is addressed; see fix #4 in §3.

### 2.2 Stage 2 — Core harness (v1)

- `run_smoke_tabarena.py` (pipeline validation, coil2000), `run_lapse_benchmark.py` (lapse class+reg), `run_tabarena_insurance_benchmark.py` (v1 baseline: 9 tasks, 8 models — TabPFN/GBDTs/GLMs/RF), plus their eval outputs.
- README API-key section: `TABPFN_API_KEY` env / repo `.env` / `TABPFN_ENV_FILE`; scripts fail with a clear error if absent.
- Rationale: v1 is imported by the pilot (Stage 3).
- Status: DONE (committed on branch).
- v1 verdict: 2 wins / 1 tie / 5 losses vs GBDT baselines; TabPFN 5–50× train, 100–1000×+ inference; `bemtl97` label leak identified here (§6).

### 2.3 Stage 3 — Hypothesis work

- Imbalance pilot (`run_tabarena_insurance_imbalance_pilot.py`) + results; size sweep (`run_home_turf_size_sweep.py` + `finish_home_turf_sweep_v2.py`) + finishers + `home_turf_sweep_results.csv`.
- Pilot reuses v1 splits; sweep feeds Stage 4.
- Status: DONE (committed on branch).
- Findings: imbalance null on 1−AUC; `balance_probabilities` hurts calibration (log loss 0.4716 vs 0.2008 on coil2000); sweep TabPFN wins 8/9 cells at ≤5K rows.

### 2.4 Stage 4 — Frontier (issue #27 deliverable)

- `scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py` (Pareto frontiers, `--regression` flag, D1–D5), 11 `frontier_results_*.csv` + plots, `rescore_focused_imbalance_logloss.py` + `focused_imbalance_logloss.csv`.
- Depends on sweep results: reuses power for cat/lgbm/xgb/tabpfn on bemtl97/coil2000/uslapseagent; fresh fits for the rest.
- Status: DONE — Spanish motor frequency extension in `87844a4` (with `model_path=v3_default` pin), Spanish motor lapse benchmark in `58dde49`.
- Headlines: lead erodes at scale (norauto LGBM wins; ausprivauto0405 7-param GLMs beat 10M-param TabPFN — since retracted to calibration-tie + TabPFN best-AUC, §14.11.3).
- Regression Phase 2 (§14.8): wins ausautoBI8999, vehvalue within SE (v1's +67.2% not reproduced — protocol-specific), dominated at scale on bemtl97_amount + freMTPL2freq.
- Spanish motor frequency result (53,502 policies, `N_claims_year`, Poisson deviance, ~453s run): LGBM wins (0.8916 ± 0.0124); TabPFN off-frontier (0.9876 ± 0.0162, dominated beyond SE); ols/poissonglm/tweedieglm (21 params) anchor the frontier within noise of TabPFN; null deviance 1.0123. Fourth at-scale dataset (after norauto, bemtl97_amount, freMTPL2freq) where TabPFN falls off the frontier.
- Spanish motor lapse benchmark (`spanish_motor_lapse` vs `eudirectlapse`, `58dde49`): TabPFN AUC 0.752 vs LGBM 0.745 vs LR 0.684, elo 1128 (#1); caveat: 2-fold holdout panel. Tracks `TASKS.md` #27a (closed).

### 2.5 Stage 5 — Docs umbrella

- Spec, master report, benchmark portfolio + naming canon, session notes, registry row, `TASKS.md`.
- Status: DONE — all in `58dde49`: `benchmark_portfolio.md` + naming canon, registry evidence row, `TASKS.md` #27a row, §14.9 lapse takeaway, and §12.1 v3-context correction in the master report.
- Merge last so references don't dangle.

## 3. Pre-merge fixes (colleagues would trip on these)

Open action items: **none** — #2 and #3 were resolved in `f72c57f`; all others resolved or informational.

1. **RESOLVED** (`58dde49`) — `scripts/README.md` now lists all 8 benchmark scripts.
2. **RESOLVED** (`f72c57f`) — 5 run logs (`frontier_benchmark_run.log`, `frontier_norauto_run.log`, `frontier_regression_run.log`, `frontier_v1suite_run.log`, `home_turf_sweep_run.log`) were gitignored (`*.log`) but cited as evidence → force-added (`git add -f`), tracked in repo.
3. **RESOLVED** (`f72c57f`) — `rescore_focused_imbalance_logloss.py` needs uncommitted `scripts/experiments/` caches → "post-run only" docstring note added.
4. **RESOLVED** — `data/README.md` gap (Stage 1): the section now exists (committed in `58dde49`). Caveat remains: the beMTPL16-vs-`bemtl16` naming collision is documented but the names themselves are unchanged.
5. Vehvalue discrepancy (§4 +67.2% vs §14.8 within SE) — flag as protocol-specific, not a contradiction.
6. `TABPFN_API_KEY` required on fresh checkout for all TabPFN runs (documented in README; no secrets in repo — the only API-key string in history is a redacted placeholder).
7. Auth is now unblocked in practice: a cached client token is persisted to the repo `.env` as `TABPFN_API_KEY` (gitignored), so full runs no longer fail on fresh checkout. The merge itself ships no secrets — `.env` is not committed.

## 4. What to communicate to colleagues (science summary)

- **11-dataset frontier** (6 classification + 5 regression), 9/8 methods; actuary takeaways in §14.4.
- **Home-turf sweep:** TabPFN wins 8/9 cells at ≤5K rows; the single loss is bemtl97@full (LGBM 0.3418 vs 0.3428); 3,045 s cold fit at 163K rows.
- **At-scale erosion:** norauto (LGBM wins), ausprivauto0405 (GLMs dominate — since retracted to calibration-tie + TabPFN best-AUC, §14.11.3), regression frontier (lead does not survive except ausautoBI8999).
- **Spanish motor frequency frontier** (53,502 policies): LGBM 0.8916 vs TabPFN 0.9876 — TabPFN off-frontier, GLM anchors (21 params) within noise of it; 4th at-scale confirmation that the lead does not survive.
- **Spanish motor lapse** (53,502 rows): TabPFN AUC 0.752 edges LGBM 0.745, LR 0.684 (elo 1128, #1) — a lapse flip vs the frequency result at the same row count; 2-fold holdout caveat.
- **bemtl97 label leak excluded;** imbalance null + calibration harm; fine-tuning degrades 3/4 targets (§5).
- **Overall verdict (§8):** do not adopt default TabPFN as a general insurance engine; fix the protocol before re-testing.
- **Operations:** `TABPFN_API_KEY` env setup; CPU runs; macOS libomp `DYLD_LIBRARY_PATH` workaround.

## 5. Merge mechanics

**EXECUTED 2026-08-04**: `git merge origin/main` clean (`ed6de3a`) → pushed → PR #51 marked ready (was draft) → merged (`31d40a5`). Post-merge checks: registry paths all resolve on `origin/main`; branch kept; follow-ups #52/#53/#55 landed (PRs #61/#62), #54 assessed (PR #63).

```bash
git fetch origin
git merge origin/main     # resolved cleanly
# PR / merge to main
```

- Merge `origin/main` into the branch first, resolve any conflicts (currently none), then PR to `main`.
- Pushes from git 2.39.3 need the HTTP/2 workaround (empty 400 on larger packs): repo config `http.version=HTTP/1.1` + `http.postBuffer=524288000`. Documented, applied; branch push of 2026-08-04 used it.
- `TASKS.md` #27/#27a rows were closed in TASKS.md during post-merge wrap-up (PR #60).
- `origin/main` carries 2 cosmetic junk commits from a diagnostic (`f0bf230` test + `5264ec1` revert, content-neutral) — cleanup decision pending.
- Low risk: additive-only diff, no existing source files modified.
