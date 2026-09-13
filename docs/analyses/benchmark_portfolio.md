# Benchmark Portfolio — Custom Insurance Benchmarks Index

Status: living index of every benchmark this project has built, current as of 2026-08-07. Colleague-facing reference: what each benchmark is, what question it answers, what it found, and where the evidence lives. All figures below are committed outputs, not recollected numbers.

---

## 1. Purpose

> Companion: `docs/reports/REPORT_REGISTRY.md` indexes the same work from the governance axis (topic → workbooks → evidence); this portfolio indexes the benchmark axis (benchmark → question → finding).

This portfolio is the project's "custom benchmarking to assess insurance performance" mandate in concrete form. Each benchmark is a question, not an event: the smoke test asks whether the harness runs, the default-config baseline asks who wins at default configuration, the hypothesis tests ask why, and the parsimony frontier asks what the accuracy-vs-parsimony trade-off is. Every benchmark is re-runnable with a single command, with outputs committed under `scripts/eval/`, which is what makes them custom benchmarks rather than one-off analyses.

## 2. Benchmark inventory

| # | Preferred name | Files | What it measures | Status |
|---|---|---|---|---|
| 1 | Smoke test | `scripts/benchmarks/run_smoke_tabarena.py` | Pipeline works end-to-end (1 dataset `coil2000`, 3 models, 2 folds, ~2 min) | done |
| 2 | Default-config baseline | `scripts/benchmarks/run_tabarena_insurance_benchmark.py` | Default-config head-to-head: 9 tasks / 7 datasets, 8 models (TabPFN vs GBDTs vs GLMs vs RF), insurance metrics (1−AUC, RMSE) | done |
| 3 | Lapse benchmark | `scripts/benchmarks/run_lapse_benchmark.py` | Lapse classification + premium regression, ELO leaderboard; `eudirectlapse` + `spanish_motor_lapse` | done |
| 4 | Imbalance study | `scripts/benchmarks/run_tabarena_insurance_imbalance_pilot.py` | Does `balance_probabilities` help on imbalanced insurance data? (`coil2000` + `uslapseagent`, 5 folds) | done |
| 5 | Size sweep — small-data regime | `scripts/benchmarks/run_home_turf_size_sweep.py` + `scripts/benchmarks/finish_home_turf_sweep_v2.py` | Size sensitivity: 3 datasets × 1K/5K/full × 5 folds, log loss / Brier / 1−AUC | done |
| 6 | Parsimony frontier | `scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py` | **THE core deliverable (issue #27):** accuracy-vs-complexity Pareto frontiers, 12 datasets (6 class + 6 reg), D1–D5 methodology, `--regression` mode | done |

## 3. Findings by benchmark

1. **Smoke test:** TabPFN ranks #1 (ELO 2190) → harness works, proceed.
2. **Default-config baseline:** TabPFN mostly loses (2 wins, 1 tie, 5 losses), 5–50× slower train; `bemtl97` label leak discovered and excluded (§6).
3. **Lapse benchmark:** TabPFN wins premium regression (RMSE 19.07 vs 81.8); wins Spanish lapse (AUC 0.752 vs LGBM 0.745 vs Linear 0.684); Linear wins `eudirectlapse` classification (0.628). Settled by 5-fold re-run (§14.10): TabPFN 0.7553 vs LGBM 0.7500 on Spanish (wins 5/5 folds); Linear still wins eudirectlapse (0.6260).
4. **Imbalance study:** hypothesis rejected — no 1−AUC gain; `balance_probabilities` hurts calibration (log loss 0.4716 vs 0.2008 on `coil2000`).
5. **Size sweep — small-data regime:** **THE pivot finding** — TabPFN wins 8/9 cells at 1K–5K rows; loses at full size → data efficiency is a secondary strength, not the identity (§13, §14.11).
6. **Parsimony frontier:** quantified verdict — TabPFN on frontier 7/12 datasets at 10M fixed params; off-frontier at scale 5× (`ausprivauto0405`, `bemtl97_amount`, `freMTPL2freq`, `spanish_motor_freq`, `spanish_motor_severity`); 21-param GLMs within noise of it (§14.2–14.11). The count-target story now has a classification leg (issue #67, §14.14): the Spanish motor freq target reframed as binary claim/no-claim or ordinal 0/1/2+ moves TabPFN to AUC rank #1, paired-significant at both seeds — the count model itself stays GBDT/GLM territory.

## 4. Naming canon

Script filenames, eval dirs, and report section numbers are **stable IDs by design** — they are referenced across the master report, `docs/reports/REPORT_REGISTRY.md`, `TASKS.md`, and the merge plan, and are not renamed. Display names may evolve; the canonical names in §2 and the alias map below are the single source of truth.

| Canonical | Aliases | Stable ID (file / dir) |
|---|---|---|
| Smoke test | — | `scripts/benchmarks/run_smoke_tabarena.py` / `scripts/eval/smoke_test` |
| Default-config baseline | v1 baseline | `scripts/benchmarks/run_tabarena_insurance_benchmark.py` / `scripts/eval/insurance_benchmark_v1` |
| Lapse benchmark | — | `scripts/benchmarks/run_lapse_benchmark.py` / `scripts/eval/lapse_benchmark_v1` |
| Imbalance study | imbalance pilot | `scripts/benchmarks/run_tabarena_insurance_imbalance_pilot.py` / `scripts/eval/insurance_imbalance_pilot` |
| Size sweep — small-data regime | home-turf size sweep | `scripts/benchmarks/run_home_turf_size_sweep.py` + `scripts/benchmarks/finish_home_turf_sweep_v2.py` / `scripts/eval/insurance_benchmark_v1` |
| Parsimony frontier | frontier benchmark | `scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py` / `scripts/eval/insurance_benchmark_v1` |

One naming rule: the "imbalance pilot" is a study, not a pilot — the hypothesis was tested to completion (null result), so the word "pilot" in prose should be avoided going forward.

## 5. Research chain

```
smoke (can we run?)
  → default-config baseline (who wins?)
    → hypothesis tests (why? — imbalance study, size sweep)
      → size sweep (the size answer)
        → parsimony frontier (the trade-off answer)
          → Spanish extension (does it hold on new data? — §14.9 + #27a)
```

Each step was gated by the previous one: the smoke test validated the harness, the default-config baseline produced the headline comparison, the hypothesis tests explained the failures, the size sweep located TabPFN's regime, and the parsimony frontier turned that into a deployable trade-off statement.

## 6. Evidence locations

### Source Workbooks

- `scripts/benchmarks/run_smoke_tabarena.py`
- `scripts/benchmarks/run_tabarena_insurance_benchmark.py`
- `scripts/benchmarks/run_lapse_benchmark.py`
- `scripts/benchmarks/run_tabarena_insurance_imbalance_pilot.py`
- `scripts/benchmarks/run_home_turf_size_sweep.py` (+ `scripts/benchmarks/finish_home_turf_sweep_v2.py`)
- `scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py`
- `scripts/eval/insurance_benchmark_v1/run_reframe_frequency.py` (+ `scripts/eval/insurance_benchmark_v1/analyze_reframe_frequency.py`)

### Evidence Files

- `scripts/eval/smoke_test/` — `tabarena_leaderboard.csv`, `results_per_split.csv`, `leaderboard.tex`, Pareto PDFs/HTML
- `scripts/eval/lapse_benchmark_v1/` — `tabarena_leaderboard.csv`, `results_per_split.csv`, `leaderboard.tex`, Pareto PDFs/HTML
- `scripts/eval/insurance_benchmark_v1/` — `results_per_split.csv`, `frontier_results_*.csv` + `frontier_plot_*.png` (one per dataset), `frontier_*_run.log`, `reframe_frequency_results.csv` + `reframe_frequency_summary.csv` (issue #67), Pareto PDFs/HTML
- `scripts/eval/insurance_imbalance_pilot/` — `results_per_split.csv`, `method_info.csv`

### Reports

- Master report: `docs/analyses/tabpfn_vs_gbdt_baselines_finetuning.md` (§1–§14.11)
- Design spec: `docs/analyses/insurance_frontier_benchmark_spec.md` (D1–D5)

## 7. Gaps and natural extensions

- **Other foundation models** — TabFM assessed but **not run** on the frontier suite: the full-context ICL fit OOM-killed the process on this 8 GB machine (a row-capped fallback was scripted but never executed), and its non-commercial weights block production use regardless (master report §14.13; `tabular_foundation_models_catalog.md`). No claim is made about other foundation models.
- **Fine-tuned TabPFN in the frontier** — tested separately, never inside the parsimony framework.
- **"Count/frequency targets are tree territory" — now scoped to the count axis (issue #67, §14.14).** The Spanish motor freq count target reframed as binary claim/no-claim (11.1% positive) or ordinal 0/1/2+ classification moves TabPFN to AUC rank #1, paired-significant at both seeds (p=0.0010/0.0020); the count model itself (Poisson deviance, §14.9) stays GBDT/GLM territory. Not yet extended to freMTPL2freq (678K rows).
- **Ensembling across context windows** — the untested TabPFN lever; the v3 API accepts up to 1M rows — the server handles large contexts internally, but the mechanism is not exposed.
