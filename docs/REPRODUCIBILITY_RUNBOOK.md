# Reproducibility Runbook — rerunning experiments in this repo

**Purpose.** One place to look up any completed experiment in this repo and find the exact
command (or notebook + cells), the inputs it needs, the outputs it writes, and the environment
it runs in. If a result is committed, the command below reproduces it.

**Promise.** Every committed result CSV / table / plot in `scripts/eval/`, `outputs/current/`
and `docs/` maps to exactly one command or notebook in this runbook. Commands are copied from
the scripts' own argparse/usage text — nothing here is guessed. Where a script cannot run
as-is (missing data, needs a sibling checkout, needs hosted-API credits, needs uncommitted
caches), that is stated in its section rather than hidden.

Three eras, documented separately:

- **A. Frontier era (2026-07→08)** — hosted-API TabPFN (`tabpfn-client` 0.3.3) + local GBDT/GLM
  baselines, the evidence behind master report §14.11–§14.14. Already partially documented in
  `notebooks/reproducibility/README.md`; sections A.7–A.9 **reference** those notebooks instead
  of duplicating them.
- **B. Legacy finetuning era (2026-04)** — local TabPFN v6 fine-tuning on CPU/MPS. No prior
  documentation existed; the runbook fills that hole. ⚠ **These are provenance, not canonical
  verdicts**: 2026-04 era, `tabpfn>=6,<7` loose pins, superseded on the AUC axis by §14.11.
- **C. GPU execution era (2026-09→)** — the fine-tuning pilot on a rented GPU (Vast.ai), which
  is the only way arm B (actual fine-tuning) can run. ⚠ Partially verified: no run has yet
  completed end-to-end. See §C before invoking it.

## Registry → runbook section map

| Report registry topic key | Runbook section |
| --- | --- |
| `tabpfn-vs-gbdt-baselines-finetuning` (master report) | §A (whole frontier era; §A.7–A.9 per addendum) |
| `insurance-frontier-benchmark-spec` | §A.7 |
| `frontier-auc-brier-rescore-spec` (§14.11) | §A.7 (`--pr-auc`, `--seed`) |
| `class-imbalance-analysis-summary` | §A.6 |
| `tabarena-insurance-benchmark-direction` | §A.3 |
| `benchmark-portfolio` | §A.2–§A.9 |
| `tabpfn-benchmark-summary` | §A (non-technical layer) |
| `insurance-finetuning-method-protocol` | §B.1 |
| `stage-a-b-findings-recommendations` | §B.1 |
| `combined-classifier-regressor-analysis` | §B.2, §B.3 |
| `insurance-finetuning-evidence` | §B.3 |
| `finetuning-limit-study` | §B.7 (shell batches) |
| `technical-companion-reference` | §B.2, §B.4 |
| `classifier-homogeneity-hypothesis-method` | §B.5 |
| `glm-vs-tabpfn-summary` (GLM paper) | §0 / pointer to `docs/REPLICATION_SETUP_GUIDE.md` |
| `post-hoc-optimisation` | notebook `notebooks/baseline_experiments/04_probability_calibration.ipynb` (not covered here) |
| `fine-tuning-pilot-results` | §C (GPU execution era) |

## ⏱ Time & cost budget — read before you start

A full run of **everything** below takes roughly **1.5–2 working days of wall time**, mostly
hosted-API spend and CPU-bound baselines. Per-section estimates:

| Section | Wall time | Cost driver |
| --- | --- | --- |
| §0 Setup (once) | ~10 min | — |
| §A.1 Data prep | minutes | — |
| §A.2 Smoke | ~2 min | — |
| §A.3 TabArena 7-dataset | hours-ish | hosted API (TabPFN folds) |
| §A.4 Lapse benchmark | minutes | — |
| §A.5 Home-turf sweep | ~1–1.5 h | hosted API |
| §A.6 Imbalance pilot | minutes–1 h | hosted API |
| §A.7 Frontier §14.11 | **hours** (6 datasets × 5 folds) | hosted API |
| §A.8 Tuned baselines | **hours** (tens of min/dataset, 60-min cap each) | local CPU |
| §A.9 Reframe §14.14 | 20–60 min | hosted API |
| §A.10 Money chart | minutes | — |
| §B.1–B.9 Legacy finetuning | **the long tail — most of a day** | local CPU/MPS (v6 era, provenance only) |
| §C GPU pilot (Vast.ai) | ~10–30 min per run | rented GPU, ~$0.25/run; **arm B unmeasured** |

**Two faster paths:**

- **Verify the published numbers (recommended first):** repro notebooks
  `notebooks/reproducibility/01–03` re-run their evidence cells in **minutes each** — they read
  committed CSVs and display the canonical results. Start here; only expand to the full
  sections below if you need to regenerate from scratch.
- **Frontier era only (A.1–A.10):** ~1 working day, dominated by A.3/A.7/A.8 + API credits.
- **Everything (A + B):** ~1.5–2 days; B-era runs are provenance (2026-04, loose pins) and
  will **not** byte-match committed artifacts — they validate the method, not the numbers.

## 0. One-time setup

### Frontier era (A)

```bash
# TabArena harness + benchmark venv (one-time, ~10 min):
git clone https://github.com/autogluon/tabarena.git /tmp/tabarena
uv venv --seed --python 3.12 /tmp/tabarena/.venv-ta
source /tmp/tabarena/.venv-ta/bin/activate
uv pip install --prerelease=allow -e "/tmp/tabarena/packages/tabarena[benchmark,tabfm]"
uv pip install "tabpfn-client==0.3.3"   # EVERY verdict is stamped to 0.3.3 — do not drift
```

- The repo-local `.venv-ta/` is the venv that produced the committed outputs and is already
  set up (incl. Jupyter kernel for the repro notebooks, name `tabarena-ta`).
- **API auth:** `TABPFN_API_KEY` env var, or a `TABPFN_API_KEY=...` line in the repo-root
  `.env` (gitignored), or `TABPFN_ENV_FILE` pointing at a file. Every script raises a clear
  error if none exists. The repro notebooks' preflight cell can also do a browser login and
  write `.env` for you. Hosted inference **costs credits** — see per-section cost notes.
- **Data:** §A.1.
- **Jupyter repro:** `notebooks/reproducibility/README.md` (setup cells, kernels, ground rules).

### Legacy finetuning era (B)

```bash
python -m venv .venv312 && source .venv312/bin/activate
pip install -r requirements.txt          # tabpfn>=6,<7 · tabpfn-client>=0.2,<0.3 · torch · sklearn
```

- **Requires a sibling checkout** `../TabPFN-upstream/` (repo-root parent) — most legacy
  scripts insert `TabPFN-upstream/src` at the head of `sys.path` so the 2026-04-era finetune
  APIs resolve even if the installed package differs. Without it they fall back to the
  installed `tabpfn` (use `--no-prefer-upstream-src` where the flag exists).
- CatBoost was **not installed** in the legacy env — every legacy run logs
  `catboost_not_available`; that is expected, not an error.
- Gated-model downloads may need `HF_TOKEN` (see `finetune_pilot.py --hf_token`).

### GPU execution era (C)

```bash
uv tool install vastai
export PATH="$HOME/.local/share/uv/tools/vastai/bin:$PATH"
vastai set api-key <KEY>               # → ~/.config/vastai/vast_api_key
export TABPFN_TOKEN="pk_..."           # Prior Labs licence token (TabPFN weight downloads)
```

- **No local install of the pilot deps is needed** — the run happens on the rented box, and the
  bootstrap installs `tabpfn==8.5.0` + `scikit-learn`/`pandas`/`pyarrow`/`catboost` there.
  Deliberately **not** `requirements.txt` (see §C.3).
- **2FA is required on this account** — run `scripts/gpu_helpers/vast_login.sh` once per session
  before anything else.
- Details, constraints and failure modes: **§C**.

### GLM paper (not a script — a notebook)

`notebooks/adswp_project/REPLICATION_There_Is_Life_in_the_Old_GLM_Yet.ipynb` — step-by-step
replication in `docs/REPLICATION_SETUP_GUIDE.md` (dataset bundled at `data/raw/eudirectlapse.csv`,
no R needed; paper split seed = 45).

## A. Frontier era (2026-07→08)

### A.1 Data preparation (runs first, once)

```bash
python scripts/infra/download_datasets.py
python scripts/infra/prepare_insurance_datasets.py /tmp/opencode/datasets
```

| Script | Generates (in `data/raw/`) | Inputs it needs | Flags |
| --- | --- | --- | --- |
| `scripts/infra/download_datasets.py` | `coil2000.csv` (OpenML ID 298, 9,822×86); `ausprivauto0405.csv` (CASdatasets GitHub mirror, `.rda` → CSV via `pyreadr`); `freMTPL2freq_binary.csv` (50,000-row stratified sample of `freMTPL2freq.csv`, seed 42) | `pyreadr` installed; **`freMTPL2freq.csv` already present in `data/raw/`** (not downloaded by this script); network | none; skips files that already exist |
| `scripts/infra/prepare_insurance_datasets.py [SRC_DIR] [--only STEM]` | `uslapseagent.csv`, `bemtl97.csv` (amount = log1p), `bemtl16.csv` (last policy-year per contract), `ausautoBI8999.csv` (AggClaim = log), `norauto.csv` (NbClaim binarised), `spanish_motor_freq.csv`, `spanish_motor_lapse.csv`, `spanish_motor_severity.csv` | `.rda` files in `SRC_DIR` (default `/tmp/opencode/datasets`, e.g. `uslapseagent.rda`, `beMTPL97.rda`, …); Spanish-motor variants read `data/raw/Spanish motor portfolio/Motor vehicle insurance data.csv` | `--only uslapseagent\|beMTPL97\|beMTPL16\|ausautoBI8999\|norauto\|spanish_motor` |

Example single-dataset rerun: `python scripts/infra/prepare_insurance_datasets.py /tmp/opencode/datasets --only spanish_motor`.

⚠ `download_datasets.py` **skips** files that already exist — deleting a CSV first is the way
to force a re-download.

### A.2 Smoke test (pipeline sanity, ~minutes)

```bash
source /tmp/tabarena/.venv-ta/bin/activate
python scripts/benchmarks/run_smoke_tabarena.py
```

- Inputs: `data/raw/coil2000.csv`; `TABPFN_API_KEY` (TabPFN arm is hosted).
- What: 2-fold classification task on coil2000, 3 models (TabPFN / LightGBM / Linear).
- Outputs: **committed at `scripts/eval/smoke_test/`** (`tabarena_leaderboard.csv`,
  `results_per_split.csv`, `method_info.csv`, Pareto charts) — a fresh run writes to
  `scripts/benchmarks/eval/smoke_test/` (see ⚠ note in §A.3).
- Non-destructive; costs a couple of hosted calls.

### A.3 TabArena insurance benchmark — the v1 suite (7 datasets)

```bash
source /tmp/tabarena/.venv-ta/bin/activate
python scripts/benchmarks/run_tabarena_insurance_benchmark.py
```

- Inputs: 6 classification CSVs (`uslapseagent`, `coil2000`, `ausprivauto0405`, `bemtl97`,
  `bemtl16`, `norauto`) + 3 regression (`ausautoBI8999`, `ausprivauto0405`→`VehValue`,
  `bemtl97`→`amount`) from `data/raw/`; `TABPFN_API_KEY`.
- What: StratifiedKFold(5, seed 42) classification / KFold(3, seed 42) regression; 7–9 models
  per panel (TabPFN hosted + LightGBM/XGBoost/CatBoost/RandomForest + LogisticGLM/PoissonGLM/
  TweedieGLM/Linear); `holdout_experiments=True` (no bagging). TabFM arms are **dropped**
  (6.1 GB checkpoint OOMs on the 8 GB Mac — see `ponytail:` comment at line 422).
- Outputs: leaderboard → `scripts/eval/insurance_benchmark_v1/` (`tabarena_leaderboard.csv`,
  `results_per_split.csv`, `method_info.csv`); task caches → `scripts/experiments/insurance_benchmark_v1/` (gitignored).
- ⚠ **Output-path drift:** the script computes `scripts/benchmarks/eval/<RUN_NAME>` and
  `scripts/benchmarks/experiments/<RUN_NAME>`, but committed outputs live under
  `scripts/eval/<RUN_NAME>` / `scripts/experiments/<RUN_NAME>` (moved during a repo reorg).
  Re-runs write to the new paths; don't be surprised when both exist.
- Cost: hosted-API fits for TabPFN across 9 tasks; hours-ish wall time on CPU.

### A.4 Lapse benchmark (eudirectlapse + spanish_motor_lapse)

```bash
source /tmp/tabarena/.venv-ta/bin/activate
python scripts/benchmarks/run_lapse_benchmark.py
```

- Inputs: `data/raw/eudirectlapse.csv`, `data/raw/spanish_motor_lapse.csv`; `TABPFN_API_KEY`.
- What: 2 classification tasks (5-fold, seed 42) + 1 regression (`prem_pure`, 2-fold); models
  trimmed to TabPFN / LightGBM / Linear (full panel deferred to GPU).
- Outputs: committed at `scripts/eval/lapse_benchmark_v1/` (`tabarena_leaderboard.csv`,
  `results_per_split.csv`); caches → `scripts/experiments/lapse_benchmark_v1/` (gitignored).
- Non-destructive; hosted cost moderate.

### A.5 Home-turf size sweep (3 datasets × 1K/5K/full)

```bash
source /tmp/tabarena/.venv-ta/bin/activate
python scripts/benchmarks/run_home_turf_size_sweep.py          # initial sweep
python scripts/benchmarks/finish_home_turf_sweep_v2.py         # finisher v2: fills gaps, drops n_estimators=1 arm
```

- Inputs: `coil2000`, `uslapseagent`, `bemtl97` (leak-fixed: drops `nclaims`,`amount`) from
  `data/raw/`; `TABPFN_API_KEY`.
- What: per cell × 5 folds (StratifiedKFold seed 42): TabPFN default / n_estimators=8 /
  n_estimators=1 (v1 arm; **dropped by finisher v2**) + CAT/XGB/LGBM. Full-size bemtl97 is
  trimmed to TabPFN-default only (`trimmed` column). `TABPFN_CLIENT_TIMEOUT` defaults 240 s;
  finisher uses 300 s per fit, 35-min wall budget, retries errored rows once.
- Outputs: `scripts/eval/insurance_benchmark_v1/home_turf_sweep_results.csv` + `home_turf_sweep_run.log`.
- ⚠ Destructive in-place: finisher **deletes** the n_estimators=1 rows from the CSV. Rerunning
  the sweep + finisher re-creates the canonical matrix but spends hosted credits (~30–40 min budget).
- Downstream: `run_frontier_benchmark.py` **reuses** this CSV's 5-fold log-loss rows (§A.7) —
  re-running the sweep changes frontier inputs.

### A.6 Imbalance pilot + log-loss rescore

```bash
source /tmp/tabarena/.venv-ta/bin/activate
python scripts/benchmarks/run_tabarena_insurance_imbalance_pilot.py

# Post-run analysis — rescues log loss / Brier from cached fold predictions (NO refits):
/tmp/tabarena/.venv-ta/bin/python scripts/eval/insurance_benchmark_v1/rescore_focused_imbalance_logloss.py
```

- Inputs (pilot): `uslapseagent`, `coil2000` only; reuses the v1 task-cache splits
  (`scripts/task_cache/insurance_benchmark_v1/`); `TABPFN_API_KEY`. Runs ONLY the
  `TabPFNClient-balanced` variant (balance_probabilities=True, n_estimators=8 — the API caps
  ensembles at 8, so the tested change is balancing alone); GBDT rows are reused from v1.
- Outputs: leaderboard → `scripts/eval/insurance_imbalance_pilot/` (`results_per_split.csv`,
  `method_info.csv`).
- ⚠ **Rescore is un-runnable as-is after a fresh clone**: it reads per-fold `results.pkl`
  prediction caches under `scripts/experiments/insurance_benchmark_v1/data/` and
  `scripts/experiments/insurance_imbalance_pilot/data/` — **task caches are gitignored**.
  Regenerate them by running §A.3 + the pilot first (hosted credits required).
- Outputs (rescore): `scripts/eval/insurance_benchmark_v1/focused_imbalance_logloss.csv`
  (+ printed mean summary).

### A.7 Frontier benchmark — §14.11 coil2000 + AUC/Brier rescore (master report core)

```bash
source /tmp/tabarena/.venv-ta/bin/activate

# canonical: all 6 classification datasets, seed 42 — DESTRUCTIVE (overwrites committed CSVs)
python scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py
python scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py coil2000            # single dataset (case-insensitive)
python scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py --seed 7 ausprivauto0405   # split-seed stability: writes _seed7 files, non-destructive
python scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py --pr-auc            # PR-AUC/lift10 robustness: fresh-fit ALL methods, APPENDS per-fold rows
python scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py --regression        # 4+2 regression frontiers (fresh power, KFold seed 42)
python scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py --regression ausautoBI8999
python scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py --data data/raw/some.csv --target TARGET [--drop a,b]   # arbitrary CSV (issue #46)
```

Flags (from argparse, `run_frontier_benchmark.py:832`): positional `filters` (dataset names),
`--regression`, `--pr-auc`, `--seed N` (default 42), `--data CSV`, `--target COL` (required
with `--data`), `--drop COLS` (comma-separated). Verify with `python run_frontier_benchmark.py --help`.

- Inputs: 6 classification CSVs (`bemtl97` drops `nclaims`,`amount`; targets/drops table at
  `run_frontier_benchmark.py:109`) or 6 regression CSVs (incl. `spanish_motor_freq`,
  `spanish_motor_severity`; `freMTPL2freq` applies log-Exposure offset); **reuses**
  `home_turf_sweep_results.csv` log-loss rows for cat/lgbm/xgb/tabpfn when present
  (norauto/ausprivauto0405/bemtl16 have no sweep rows → fresh power); `TABPFN_API_KEY`.
- Outputs (in `scripts/eval/insurance_benchmark_v1/`): `frontier_results_<dataset>.csv`
  (method | mean | se | mean_auc/se_auc | mean_brier/se_brier [+mean_pr_auc/se_pr_auc +
  mean_lift10/se_lift10 in `--pr-auc`] | n_params | on_frontier), `frontier_plot_<dataset>.png`,
  per-fold append file `frontier_pr_auc_results.csv` (`--pr-auc` only), run logs
  `frontier_benchmark_run.log` / `frontier_v1suite_run.log` / `frontier_regression_run.log`.
  Seed ≠ 42 → suffixed `_seed<N>.csv/.png` (canonical seed-42 files untouched).
- Notes: hosted TabPFN last per dataset with 3-attempt retry/backoff (10/60/300 s);
  assert-based self-check at the end (`SELF-CHECK OK`). Seed 42 runs **overwrite** committed
  evidence — prefer `--seed 7` or copy CSVs aside (§14.12 protocol: seeds 7/42/123).
- Cost: minutes per dataset CPU; hosted API per TabPFN fold (6 datasets × 5 folds for full run).
- Analysis: `python scripts/eval/insurance_benchmark_v1/analyze_pr_auc.py [results_csv]` →
  `frontier_pr_auc_summary.csv` (paired t-tests, seed-stability table).
- **Repro notebook:** `notebooks/reproducibility/01_frontier_classification_repro.ipynb`
  (§14.11 on coil2000 only; evidence cells pre-executed, free to re-run; the one `optional`
  cell costs minutes and overwrites `frontier_results_coil2000.csv` — use `--seed 7`).

### A.8 Tuned baselines + TabFM — §14.13 "finality" test

```bash
source /tmp/tabarena/.venv-ta/bin/activate
python scripts/eval/insurance_benchmark_v1/run_tuned_baselines.py [ds ...]   # default: all 6 datasets; APPENDS rows
python scripts/eval/insurance_benchmark_v1/run_tuned_baselines.py coil2000
python scripts/eval/insurance_benchmark_v1/run_tabfm.py [ds ...]            # default: coil2000 uslapseagent bemtl16; APPENDS rows
```

- What: 5 tuned/engineered baselines (lr identity-check, lr_tuned, glm_eng, lgbm_tuned,
  cat_tuned, rf_tuned) on the exact §14.12 folds; tuning by inner-CV AUC with 10-min/fold soft
  caps. `run_tabfm.py` = TabFM v1.0.0 (JAX, HF `google/tabfm-1.0.0-jax`, non-commercial
  license), n_estimators=8, `max_num_rows=6000` ICL cap (full-context OOMs on 8 GB), 60-min
  wall cap per dataset.
- Inputs: same datasets as §A.7; **no** API key (CPU-only); TabFM weights download
  (~20 min restore on CPU) on first run.
- Outputs: `frontier_tuned_baseline_results.csv` (append mode — **duplicates accumulate** on
  reruns); analysis `python analyze_tuned_baselines.py [results_csv]` →
  `frontier_tuned_baseline_summary.csv`.
- Cost: **tens of minutes per dataset**; full suite = hours of CPU.
- Repro notebook: `notebooks/reproducibility/03_tuned_baselines_repro.ipynb`.

### A.9 Reframe frequency — §14.14, issue #67

```bash
source /tmp/tabarena/.venv-ta/bin/activate
python scripts/eval/insurance_benchmark_v1/run_reframe_frequency.py
python scripts/eval/insurance_benchmark_v1/analyze_reframe_frequency.py
```

- What: spanish_motor_freq counts reframed as binary (seed 42 + 7, canonical 9 methods) and
  ordinal 0/1/2+ (seed 42, 6 multiclass methods). Hosted TabPFN last per task, same retry loop.
- Inputs: `data/raw/spanish_motor_freq.csv` (leak columns dropped at prep time); `TABPFN_API_KEY`.
- Outputs: `reframe_frequency_results.csv` (120 fold rows, asserted) →
  `analyze_reframe_frequency.py` writes `reframe_frequency_summary.csv` (paired t, rank).
- ⚠ Seed-42 binary/ordinal rows **overwrite** the committed CSV; seed-7 rows append in the same
  file. Cost: 20–60 min hosted API.
- Repro notebook: `notebooks/reproducibility/02_reframe_frequency_repro.ipynb`.

### A.10 Money chart (visual summary of the whole frontier era)

```bash
/tmp/tabarena/.venv-ta/bin/python scripts/eval/insurance_benchmark_v1/plot_money_chart.py
```

- Reads all `frontier_results_*.csv` + `home_turf_sweep_results.csv`; writes
  `money_chart_tabpfn_relative.png`. Read-only, no API.

## B. Legacy finetuning era (2026-04) — provenance, not canonical

> ⚠ Caveat: these scripts ran against TabPFN **v6** (loose `tabpfn>=6,<7` pin) in April 2026,
> on CPU/MPS, with catboost missing. The AUC-axis verdicts were superseded by §14.11 (2026-08).
> Treat these sections as a record of what ran (batch names, row counts, seeds below are the
> **actual** runs from `outputs/current/logs/domain_finetune_logbook.md` and
> `outputs/current/tables/domain_finetune_study_runs.csv`), not as current method guidance.
> All legacy scripts also require the sibling `../TabPFN-upstream/src` checkout (§0).

### B.1 Stage A domain finetune (the main legacy experiment)

```bash
source .venv312/bin/activate
# the exact config of the 2026-04-02 batch (eudirectlapse target, context 64, 1 step):
python scripts/legacy_finetuning/run_domain_finetune_stage_a.py \
  --target-dataset eudirectlapse --seed 42 --target-rows 2500 --pool-rows-per-dataset 1000 \
  --tabpfn-device cpu --tabpfn-context-samples 64 --tabpfn-n-estimators 2 --tabpfn-max-finetune-steps 1 \
  --observations "..." --comments "..."
```

- Full argparse (`run_domain_finetune_stage_a.py:81`): `--target-dataset`
  {eudirectlapse,coil2000,ausprivauto0405,freMTPL2freq_binary}, `--seed`, `--target-rows`,
  `--pool-rows-per-dataset`, `--pool-policy`
  {all,homogeneous,heterogeneous,similarity_topk,mixed_baseline}, `--pool-k`,
  `--sim-weight-{feature,target,context}`, `--test-size`, `--tabpfn-device`,
  `--tabpfn-context-samples`, `--tabpfn-n-estimators`, `--tabpfn-max-finetune-steps`,
  `--log-path` (default `outputs/current/tables/domain_finetune_study_runs.csv`),
  `--logbook-path` (default `outputs/current/logs/domain_finetune_logbook.md`),
  `--observations`, `--comments`, `--[no-]prefer-upstream-src`.
- **What actually ran** (85 rows in `domain_finetune_study_runs.csv`, all seed 42):
  - Batch `2026-04-02T00:30:53Z`: 4 targets × context 64 × steps 1, target_rows 2500,
    pool_rows_per_dataset 1000 (pool_rows=3000 = 3 non-target datasets × 1000).
  - Smoke-check run: eudirectlapse, target_rows 800, pool 400 (00:37:03).
  - Steps sweep: 4 targets × steps {3, 5} × context 64 (00:41→01:12).
  - Context sweep: 4 targets × context 128 × steps 5 (01:20→01:37).
  - Models per run: logistic_regression, random_forest, catboost (logged
    `catboost_not_available`), raw TabPFN, domain_finetuned TabPFN.
- Inputs: `data/raw/{eudirectlapse,coil2000,ausprivauto0405,freMTPL2freq_binary}.csv`; local
  TabPFN v6 (no API key).
- Outputs (append-only, **non-destructive**): `outputs/current/tables/domain_finetune_study_runs.csv`,
  `outputs/current/logs/domain_finetune_logbook.md` (one section per run with auto-generated
  raw-vs-finetuned delta interpretation).
- Verdict recorded: single-step/low-budget domain finetune did not beat raw TabPFN on
  aggregate; freMTPL2freq_binary was the only consistent improver.

### B.2 Raw & fine-tuned regressor benchmarks (3 datasets, no argparse)

```bash
source .venv312/bin/activate
python scripts/legacy_finetuning/run_raw_tabpfn_regression_benchmark.py      # MUST run first
python scripts/legacy_finetuning/run_finetuned_tabpfn_regression_benchmark.py  # reads raw's output
```

- **No argparse** — edit constants at the top of each file. Shared (both scripts):
  `RANDOM_SEED=42`, `TEST_SIZE=0.20`, `GLOBAL_MAX_TRAIN=300`, `GLOBAL_MAX_TEST=2000`,
  `N_ESTIMATORS=4`, `DEVICE="cpu"`, and the `DATASETS` list (both: `freMTPL2freq.csv`/`ClaimNb`,
  `eudirectlapse.csv`/`prem_pure`, `ausprivauto0405.csv`/`VehValue`). Finetuned script only:
  `CONTEXT_SAMPLES=64`, `MAX_FINETUNE_STEPS=1`, `FINETUNE_LR=1e-5`.
- Inputs: the 3 raw CSVs; `data/processed/multi_dataset_regression_benchmark_results.csv`
  (baseline table, read by both — **must exist**); finetuned script also reads
  `outputs/current/tables/raw_tabpfn_regression_revalidation.csv`.
- Outputs: raw → `outputs/current/tables/raw_tabpfn_regression_revalidation.csv` +
  `multi_dataset_regression_benchmark_with_tabpfn_revalidated.csv` +
  `raw_tabpfn_regression_revalidation_run_meta.json` + `outputs/current/logs/raw_tabpfn_regression_revalidation.md`;
  finetuned → `tabpfn_regression_finetune_vs_raw.csv` + `multi_dataset_regression_benchmark_with_tabpfn_finetuned.csv`
  + `_run_meta.json` + `outputs/current/logs/tabpfn_regression_finetune_vs_raw.md`. All writes
  are **overwrites** (safe to rerun; deterministic seed 42).
- Note: the finetuned script also skips non-finite target/loss batches and logs the skip counts.

### B.3 Small classifier / regressor finetune trials (argparse)

```bash
source .venv312/bin/activate
# classifier smoke (defaults: coil2000, CARAVAN, 300 rows, cpu, context 64, 1 step, seed 42):
python scripts/legacy_finetuning/run_small_finetune_classifier_trial.py \
  --data-path data/raw/coil2000.csv --target-col CARAVAN --rows 300 \
  --device cpu --context-samples 64 --n-estimators 2 --max-finetune-steps 1 --seed 42

# regressor smoke (defaults: freMTPL2freq, ClaimNb, 1000 rows):
python scripts/legacy_finetuning/run_small_finetune_regressor_trial.py \
  --data-path data/raw/freMTPL2freq.csv --target-col ClaimNb --rows 1000 \
  --device cpu --context-samples 64 --n-estimators 2 --max-finetune-steps 1 --seed 42
```

- Classifier flags (`run_small_finetune_classifier_trial.py:39`): `--data-path`, `--target-col`,
  `--rows`, `--device`, `--context-samples`, `--n-estimators`, `--max-finetune-steps`,
  `--seed`, `--save-path` (default `outputs/current/models/<ts>_tabpfn_finetune_<target>_<device>_<rows>.tabpfn_fit`),
  `--log-path`, `--[no-]prefer-upstream-src`.
- Regressor adds `--target-transform {none,log1p,claimfreq_raw,claimfreq_log1p}`,
  `--logbook-path` (default `outputs/current/logs/tabpfn_finetune_regressor_logbook.md`),
  `--positive-claims-pool` (Stage R2 ablation: pool restricted to ClaimNb>0 rows).
- Outputs: append rows to `outputs/current/tables/tabpfn_finetune_trial_results.csv` /
  `tabpfn_finetune_regressor_trial_results.csv`; classifier saves a `.tabpfn_fit` model
  artifact (needed by §B.4). Non-destructive (append), deterministic seed 42.
- Fits batched-mode TabPFN v6 with Adam(1e-5), CrossEntropyLoss; evaluates pre/post-step.

### B.4 Saved-model reload check

```bash
python scripts/legacy_finetuning/check_saved_finetune_classifier_model.py              # latest saved trial
python scripts/legacy_finetuning/check_saved_finetune_classifier_model.py --model-path outputs/current/models/<file>.tabpfn_fit
```

- Flags: `--results-log-path` (default `outputs/current/tables/tabpfn_finetune_trial_results.csv`),
  `--check-log-path` (default `outputs/current/tables/tabpfn_finetune_reload_checks.csv`),
  `--model-path`, `--device`. Reconstructs the same stratified sample/split (seed from the
  trial row), reloads the artifact, re-evaluates; appends a row comparing reload vs logged metrics.

### B.5 Homogeneity evaluation (classifier pool selection; no argparse)

```bash
python scripts/legacy_finetuning/evaluate_classifier_homogeneity_proposal.py
python scripts/legacy_finetuning/summarize_classifier_homogeneity_smoke.py --seeds 42 44 --target-rows 800 --context 32 --max-finetune-steps 1 --policies homogeneous heterogeneous all
```

- `evaluate_classifier_homogeneity_proposal.py`: **no argparse**; reads
  `outputs/current/tables/domain_finetune_study_runs.csv` + the 4 raw CSVs, computes per-target
  finetune deltas vs a prevalence-distance homogeneity proxy. Read-only.
- `summarize_classifier_homogeneity_smoke.py`: argparse as shown (plus `--compare-a/-b`,
  `--out`); writes `outputs/current/tables/classifier_homogeneity_smoke_seed42_summary.csv`.
- Method, not verdict: homogeneous-pool gain was inconclusive (registry:
  `classifier-homogeneity-hypothesis-method`).

### B.6 ClaimNb finiteness diagnosis

```bash
python scripts/legacy_finetuning/diagnose_claimnb_finiteness.py \
  --data-path data/raw/freMTPL2freq.csv --rows 500 --context-samples 64 --seed 42 --device cpu --max-batches 20
```

- Flags: `--data-path`, `--rows`, `--context-samples`, `--seed`, `--device`, `--max-batches`,
  `--log-path` (default `outputs/current/logs/claimnb_finiteness_checkpoints.csv`).
  Runs transforms `none` and `claimfreq_log1p`, logs finite/non-finite batches. Appends to CSV.

### B.7 Round-3 analysis & stability gate

```bash
python scripts/legacy_finetuning/analyze_round3_results.py        # no argparse; MUST run from repo root (relative CSV path)
python scripts/legacy_finetuning/evaluate_regressor_stability_gate.py \
  --target-col ClaimNb --target-transform none --rows 1000 --context-samples 64 \
  --seeds 42 1337 2025 --min-steps-executed 1 --max-abs-loss 1e6 --max-loss-range 100.0 [--strict-exit]
```

- `analyze_round3_results.py`: **no argparse, cwd-sensitive** (`pd.read_csv("outputs/current/tables/domain_finetune_study_runs.csv")`);
  filters context=128/steps=5 tabpfn rows, prints delta tables + a PASS/FAIL decision, writes
  `outputs/current/tables/classifier_round3_seed42_44_deltas.csv` and
  `classifier_round3_policy_pooled.csv`. Read-only on inputs, overwrites the two outputs.
- Stability gate: `--target-col` and `--rows`/`--context-samples` are **required**; reads the
  regressor trial ledger (`--log-path`), checks every seed executed ≥ min steps with finite,
  bounded last-step losses. `--strict-exit` → non-zero exit on failure.

### B.8 Timing pilots (argparse; no persisted outputs beyond stdout)

```bash
python scripts/legacy_finetuning/finetune_pilot.py --n_pilot 2000 --device cpu          # synthetic data
python scripts/legacy_finetuning/pilot_timing.py --n_pilot 1000 --device cpu
python scripts/legacy_finetuning/pilot_timing.py --csv data/processed/my_features.csv --target target_col --n_pilot 500
```

- `finetune_pilot.py` flags: `--n_pilot`, `--n_features`, `--n_classes`, `--device`,
  `--batch_size`, `--epochs`, `--n_estimators`, `--hf_token`. Synthetic `make_classification`
  data; prints per-sample finetune time + extrapolated GPU-hours/cost.
- `pilot_timing.py` flags: `--csv`, `--target`, `--n_pilot`, `--device`, `--n_estimators`,
  `--hf_token`. Prints fit timing; HF-gated-model troubleshooting hints built in.
- `debug_preprocess.py`: **no argparse**, inline synthetic smoke of the
  `get_preprocessed_dataset_chunks` batch structure; prints batch shapes, writes nothing.

### B.9 Shell batch scripts (the limit study)

```bash
bash scripts/legacy_finetuning/run_finetune_first_batch.sh          # A2(500/64/1) A3(1000/64/1) B2(1000/128/1) C2(1000/128/3) D1(mps,1000/64/1)
bash scripts/legacy_finetuning/run_finetune_crossover_batch_3000.sh # X1,X2 cpu+mps @3000 rows (64/128 context, 1 step)
bash scripts/legacy_finetuning/run_finetune_stress_batch_2000.sh    # S1-S4 @2000 rows (64/128 context, 1-3 steps, cpu+mps)
```

- Each trial = `run_small_finetune_classifier_trial.py` (rows/context/steps as shown) then a
  reload check on CPU. Inputs: `data/raw/coil2000.csv` (trial defaults), local TabPFN v6.
- Outputs: append to `outputs/current/tables/tabpfn_finetune_trial_results.csv` +
  `tabpfn_finetune_reload_checks.csv`; artifacts in `outputs/current/models/`.
- Evidence for `TABPFN_FINE_TUNING_LIMIT_STUDY.md` (registry: `finetuning-limit-study`).

## C. GPU execution era (2026-09 →) — fine-tuning pilot on a rented GPU

**Purpose.** Run the fine-tuning pilot's four arms (`A_raw`, `B_in_domain`, `E_glm`,
`F_catboost`) on a cloud GPU. §B is the 2026-04 CPU/MPS era with loose pins; this section is
the 2026-09 GPU path that arm B (actual fine-tuning) requires.

**Status: partially verified — read this before trusting it.** Offer selection, image
tiering and the login flow are exercised against live marketplace data. The end-to-end
`vastai execute` transport has **not** been confirmed by a completed run, and arm B has
**never completed anywhere** (see "arm B memory" below). Treat the first real run as the test.

### C.1 One-time setup

```bash
uv tool install vastai
export PATH="$HOME/.local/share/uv/tools/vastai/bin:$PATH"

vastai set api-key <KEY>     # writes ~/.config/vastai/vast_api_key -- NOT ~/.vast_api_key
```

That path detail matters: hunting `~/.vast_api_key` produces a misleading 403 as if the key
were wrong.

### C.2 Running the pilot

```bash
bash scripts/gpu_helpers/vast_login.sh          # once per session; opens the 2FA session
unset TABPFN_TOKEN                              # do NOT export it -- see below
bash scripts/gpu_helpers/vast_run.sh --min-vram 40 --max-dph 0.75 \
     --arms A_raw,B_in_domain --max-attempts 2
```

**Never `export TABPFN_TOKEN`.** The token is read from `~/.config/tfm/keys.env`
(mode 600) and that file is authoritative. An exported variable used to silently
win, which is a specific and invisible failure: a stale token gets embedded into
the onstart script, the API rejects it on the box (**401**, reported as
`verify_token: False`), and nothing looks wrong locally because a stale key has
the same length and the same `tabpfn_sk_` prefix. The runner now warns loudly when
the two disagree and prints the token's sha on every run, so the value that
reached the box can be compared against the local one.

`vast_run.sh` steps: select offer → match image to host CUDA → create → wait for
`running` (aborting within ~30 s if `intended_status` is `stopped`) → bootstrap runs
at container boot via `--onstart` → watch the log → pull artifacts from the log
stream → **destroy**. The `trap` destroys on any exit (success, failure, Ctrl-C)
unless `--keep`, which is the entire cost model — a forgotten instance bills
indefinitely.

The bootstrap then runs its own gates before any arm: GPU check → clone → install
`tabpfn==8.5.0` → **torch/CUDA check** → **TabPFN auth preflight** (forces the gated
weight download and prints the licence decision inputs). A failure there costs ~2
minutes and ~$0.02 instead of a doomed 16-arm batch, and the bootstrap emits
`BOOTSTRAP FINISHED` on every exit path so the runner never polls out its ceiling.

Artifacts land in `outputs/gpu-pilot/`: `pilot_metrics.parquet`,
`pilot_predictions.parquet`, plus a per-run JSON and `run_ledger.csv`. They are
returned through the container log, folded into 440-char `__ART__` lines because
the log truncates any line at 500 characters (see C.3).

### C.3 Hard constraints — each of these cost real time to find

**Team context blocks SSH keys.** On a team account every account-level SSH key operation
fails:

```
Failed with error 400: Team SSH keys are not supported.
SSH keys can only be created in personal context.
```

Worse, `vastai create ssh-key` **exits 0 on that failure**, so `cmd || exit 1` does not fire and
a naive script reports success. Hence the default `--transport execute`, which runs commands
over the API and needs no key at all. SSH remains available via `--transport ssh` once a
personal-scope key exists. Note `show api-keys` distinguishes keys by `key_type`
(`primary`/`api`/`team`/`session`) and `team_id` — a personal `api` key (`team_id: null`) is
what unblocks SSH.

**Every CLI call is 2FA-gated on this account.** `show user`, `tfa status` and `tfa totp-setup`
all return 401 *"requires you to have logged in using Two Factor Authentication"*. `search
offers` is the exception — it works unauthenticated, so you can price a job before logging in.

**Email 2FA is the bootstrap path, and it has a pairing trap.** `totp-setup` cannot be reached
before a session exists (chicken-and-egg), and with no phone on the account `send-sms` fails.
`vastai tfa send-email` works pre-session and mints a one-time secret; the emailed code is
bound to **that** challenge. Reusing an older secret with a newer code yields:

```
❌ Error: No 2FA challenge found. Please try again.
```

because each `send-email` invalidates the previous secret. `vast_login.sh` mints and consumes
the secret in one shot to make that impossible.

**Do not use `requirements.txt` on the GPU box.** It pins `numpy>=1.24,<2`; numpy 1.x has no
cp313 wheels, so pip compiles numpy from source via meson/gcc (~20 min) and the run looks
hung. It also pins `tabpfn>=6,<7` while the pilot runs `tabpfn==8.5.0` — record that
deviation. The bootstrap installs named packages and lets pip resolve wheels.

**Restrict the architecture.** Ranking by `dlperf/$` selects ancient hardware; `--pick
cheapest` chose a **Tesla V100**, and recent PyTorch builds have dropped Volta/sm_70, so the
run would fail *after* the instance was paid for. `vast_run.sh` whitelists Ampere/Ada/Hopper
and hard-excludes Volta/Pascal/Turing. It also excludes RTX 5090 (Blackwell), which needs
CUDA 12.8+ and over-constrains the image choice. Be suspicious of mismatched specs in offers:
an "RTX 4090" advertising 49 GB VRAM is a modded card or a misreport.

**Match the image to the host's CUDA ceiling**, and keep torch ≥ 2.5 — `tabpfn 8.5.0` requires
it, so a 2.4.0 image lets pip pull a CUDA 12.4 wheel onto a 12.2-capped host (mid-run failure).
Verified tier matrix:

| host `cuda_max_good` | image | torch |
| --- | --- | --- |
| ≥ 12.8 | `pytorch/pytorch:2.7.0-cuda12.8-cudnn9-runtime` | 2.7.0 |
| ≥ 12.6 | `pytorch/pytorch:2.6.0-cuda12.6-cudnn9-runtime` | 2.6.0 |
| ≥ 12.4 | `pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime` | 2.5.1 |
| ≥ 12.1 | `pytorch/pytorch:2.5.1-cuda12.1-cudnn9-runtime` | 2.5.1 |

**Never hardcode an offer ID.** The marketplace turns over within minutes — an offer
recommended half an hour earlier had already vanished, and prices for the same card class span
$0.15–2.14/hr in a single session. Pass `--query` and let it select at run time.

**Offer IDs are not searchable.** `id == <n>` returns zero rows; re-running the original query
and matching on `id` is the only way to check whether an offer still exists.

**Keep Python out of shell heredocs nested in substitutions.** macOS ships **bash 3.2.57**
(`/bin/bash`) and it precedes Homebrew's bash on PATH. In 3.2, a heredoc inside a process
substitution mis-parses at *runtime*:

```bash
read -r A B < <(python3 - "$x" <<'PY' ... PY)   # -> "0: ambiguous redirect"
```

and `bash -n` does **not** catch it — the file passes a syntax check and fails when executed.
Offer selection and image tiering therefore live in `select_offer.py` / `pick_image.py`, called
as ordinary commands. The same class of bug bit the Colab launcher (stdin is Python, not shell);
treat the shell/Python boundary as the primary hazard in this tooling.

**`vastai execute` is NOT a remote shell — it runs only `ls`, `rm`, `du`.** This supersedes
the earlier advice to use `--transport execute` for running commands. Passing anything else
returns:

```
Failed with error 400: Invalid command given.
```

so `echo <b64> | base64 -d | bash` and `tar czf - | base64` can never work through it, and a
mock that accepts arbitrary shell will happily validate a transport that does not exist. The
working transport is `--onstart <file>` (runs at container boot, takes a *filename* so the
~4048-char `--onstart-cmd` argument limit does not apply) plus `vastai logs` to read results.
`--transport ssh` remains available only with a personal-scope key.

**Never pass `--ssh --direct` when you do not need SSH.** Those flags set
`image_runtype: ssh_direc ssh_proxy`, and instances created with them came up with:

```
intended_status: stopped      <- Vast has decided this instance should not run
cur_state:       stopped
```

The container is then never started, so `actual_status` sits at `loading` **forever** — which
looks exactly like a very slow image pull. Three attempts were misdiagnosed as Docker
slowness before this was spotted. One earlier instance did reach `running` with the old flags,
so this is intermittent, which is all the more reason not to request a capability the pilot
never uses. `vast_run.sh` no longer passes either flag, and the wait loop aborts within ~30s
if `intended_status` is `stopped`.

**The container log caps every LINE at 500 characters, and truncates silently.** Measured: a
base64 artifact payload came back at exactly 500 chars while the next-longest line in the
whole log was 363. The payload decoded to a 375-byte gzip that `tar` rejected as *"truncated
gzip input"* — while every log message indicated the transfer had succeeded. Artifacts are
therefore folded into `__ART__`-tagged lines of 440 chars and reassembled client-side
(verified by round trip: 63 lines, longest 447, restored parquet sha256-identical).

**The TabPFN licence check is separate from token validity, and easy to test wrongly.**

| Endpoint | Proves |
| --- | --- |
| `GET {api}/protected/` | the token is valid (and which account it belongs to) |
| `GET {api}/account/license/?version=<licence-name>` | that account ACCEPTED the licence |

A token can pass the first and fail the second, and **only the second gates the weight
download**.

**What the gate actually gates — and what it does not.** The check is *not* an inference or
fine-tuning credential. It sits inside the weight-download path and fires only on a **cache
miss**:

```
model_loading.py
  if to.exists(): return ...          # weights already on disk -> NO licence check at all
  return _download_model(...)         # cache miss only

  _download_model(...):
      _HF_REPOS = {V2_5: "tabpfn_2_5", V2_6: "tabpfn_2_6", V3: "tabpfn_3"}
      if version in _HF_REPOS:        # every current version is gated
          ensure_license_accepted(hf_repo_id=...)   # -> then hf_hub_download
```

Three consequences that matter operationally:

- **No token is needed for local inference or fine-tuning once the weights are cached.** On a
  machine with the `.ckpt` already in `~/.cache/tabpfn/`, the cache check short-circuits and the
  gate never runs. Fine-tuning itself is entirely local — no cloud compute, no API call.
- **Our ephemeral Vast containers take the cache-miss path on every run**, so the gate fires
  every time and `TABPFN_TOKEN` is required every time. That is why the bootstrap enforces it.
- **The token is *how* licence acceptance is verified — it is not an alternative to accepting
  the licence.** "You need a licence, not a key" is a distinction without a difference here:
  `TABPFN_TOKEN` is the mechanism by which Prior Labs records acceptance. In a non-interactive
  container it is the only supported path, which is why the failure reads as a licence error.

Baking the checkpoint into the image would move the gate from every run to once per image
build. Not implemented; recorded as the obvious optimisation.

Two traps:

- `version` is a **LICENCE NAME read from the HuggingFace model card**, not a package version:
  `_get_license_name(hf_repo_id)` → for `Prior-Labs/tabpfn_3` that is `tabpfn-3-license-v1.0`.
  Querying with `8.5.0` returns `{"accepted":false}` for *every* value, including ones that do
  not exist, which reads exactly like an unaccepted licence. Use `bash scripts/gpu_helpers/keys.sh
  licence`, which derives the name the same way the library does.
- A locally-installed `tabpfn` may be a different version with **no licence gate at all**, in
  which case a local fit succeeds regardless and proves nothing. Check for
  `tabpfn/browser_auth.py` before trusting a local pass. 8.5.0's real auth modules can be
  exercised without torch by copying `errors.py`/`settings.py`/`constants.py`/`browser_auth.py`
  out of the sdist and stubbing `torch`.

The bootstrap preflights this before running any arm and prints the decision inputs
(`api_url`, proxy env, `verify_token`, resolved licence name, `check_license_accepted`), so a
failure names the branch instead of repeating a generic licence error. It costs ~2 min and
~$0.02 to fail there rather than across a 16-arm batch.

**Do not pin `--image` by hand unless you must.** Hosts differ far more in whether they have a
tag cached than in which tag is "safer". A `2.5.1-cuda12.1` pin both succeeded and stalled on
different hosts, while the auto-picked image worked for the runs that completed. Leave the
tier choice to `pick_image.py`.

### C.4 Arm B memory — the central unknown

Arm B has **never completed a run**. On the Colab free CPU runtime (12 GB, **no swap**) the
kernel OOM-killed it:

```
Memory cgroup out of memory: Killed process (python3)  anon-rss:11824532kB
```

Two consequences worth internalising:

1. **A kernel SIGKILL cannot be caught by `try/except`.** The interpreter dies mid-statement,
   so the per-arm handler never runs: no traceback, no `ERROR:` line, and the remaining arms
   never execute. `vast_run.sh` therefore runs **one arm per subprocess** so an OOM costs one
   arm rather than the batch, and reports `rc=137` explicitly (128+9 = SIGKILL).
2. **11.8 GB was SYSTEM RAM, not VRAM.** On a CPU-only box every tensor lives in RAM; on a GPU
   they move to VRAM with a different allocation pattern. **24 GB VRAM is an extrapolation, not
   a measurement** — which is why the recommended first arm-B run buys headroom with
   `--min-vram 40` rather than optimising `dlperf/$`. For a ~20-minute job the price difference
   is ~$0.10, while a failed measurement costs a whole retry cycle.

### C.5 Cost — measured, not estimated

**The ledger is derived; the per-run JSONs are the source of truth.** `run_ledger.csv` is
appended to, so adding a field to the run record silently misaligned every later row
(`csv.DictWriter` only writes a header when the file is missing): the ledger reported
`$1789231403` for a five-minute run. It now compares the header against the record's fields
and quarantines a mismatch as `run_ledger.csv.stale-<stamp>` instead of appending garbage.
If a figure looks absurd, rebuild from `run_*.json` — the ledger can be wrong, the JSONs
were not.

**Every run records its own cost.** `vast_run.sh` writes `outputs/gpu-pilot/run_<stamp>.json`
plus an appended `outputs/gpu-pilot/run_ledger.csv` with 19 columns:

```
run_id, instance_id, gpu_name, dph_total, gpu_ram_gb, cpu_ram_gb, reliability,
cuda_max_good, image, transport, arms, disk_requested_gb,
t_create, t_running, t_end, wall_seconds, wall_minutes, est_cost_usd, bootstrap_rc
```

`t_create` → `t_end` is the billable window (billing starts at create, not at `running`).
Records are written in the `trap` **before** the instance is destroyed, so a failed run still
records — and a failed *destroy* still leaves the record behind. Aggregate the ledger to
replace the estimates below with measurements:

```bash
python3 - <<'PY'
import csv
rows = list(csv.DictReader(open('outputs/gpu-pilot/run_ledger.csv')))
print(f'{len(rows)} runs, total ${sum(float(r["est_cost_usd"]) for r in rows):.4f}')
for r in rows:
    print(f"  {r['gpu_name']:<14} {r['wall_minutes']:>5}min  rc={r['bootstrap_rc']:<4} ${r['est_cost_usd']}")
PY
```

Arm-level timing is recorded separately by the pilot itself: every arm writes
`run_time_seconds` into its own `meta.json`. On the CPU box, arm A was essentially the whole
compute cost (34–83 s per dataset) with E and F sub-second.

**The model, as it stands (unmeasured — no run has completed).** Fixed setup is ~2 min
(clone + pip install) regardless of card. Compute scales roughly inversely with `dlperf`, which
is Vast's *generic* DL benchmark — a proxy, not a predictor of TabPFN's in-context workload:

| gpu | $/hr | VRAM | 5 min | 15 min | 30 min | 60 min |
| --- | --- | --- | --- | --- | --- | --- |
| A100 PCIE | 0.6014 | 41.0 | $0.073 | $0.179 | $0.339 | $0.657 |
| RTX 6000Ada | 0.6614 | 49.1 | $0.071 | $0.168 | $0.314 | $0.607 |
| A100 SXM4 | 0.7343 | 41.0 | $0.089 | $0.217 | $0.410 | $0.796 |
| RTX PRO 5000 | 0.9352 | 48.9 | $0.078 | $0.173 | $0.314 | $0.597 |

**Two conclusions that reframe the question:**

1. **The hourly rate is a rounding error; arm B's runtime is the entire cost.** Going 5 → 60 min
   of compute multiplies cost ~9×, while switching between these cards changes it by under 10%.
   Optimising the rate optimises the wrong variable.
2. **Compare cards on throughput-adjusted cost, not headline rate.** A cheaper $/hr card can
   lose if it is slower. Worked example at prices observed 2026-09-12:

   | card | $/hr | dlperf | 5 min compute | verdict |
   | --- | --- | --- | --- | --- |
   | RTX PRO 5000 | 0.6681 | 165.5 | $0.078 | wins |
   | RTX 6000Ada | 0.6614 | 113.1 | $0.103 | 46% slower for 1% less money |

   ⚠ **Prices move within minutes** — re-derive this rather than trusting either figure. An
   earlier version of this section claimed the RTX 6000Ada "dominated" the PRO 5000; that was
   an artefact of comparing against the PRO 5000's briefly-higher $0.9352 listing, and is
   wrong at $0.6681.

3. **`--pick` now breaks ties on reliability.** Two offers at identical `dlperf/$` used to be
   separated by API return order, which could select a `rel 0.978` host over a `rel 0.998` one
   at the same price. Reliability is now the secondary sort key for all three `--pick` modes.
   It does not override price or throughput: paying 46% more (+$0.31/hr) for `rel 0.9876` →
   `0.9983` is not worth it for a minutes-long job, where the expected saving is ~$0.001.

**The dominant unknown is arm B's runtime**, and it is unmeasured because arm B has never
completed anywhere (§C.4). Buy the answer cheaply before committing to a full run:

```bash
# one dataset, arm B only: ~2 min setup + ~5 min compute ≈ $0.08
bash scripts/gpu_helpers/vast_run.sh --arms B_in_domain --max-dph 0.70
```

Then the full four-arm × four-dataset run is a known quantity instead of a gamble.

**Practical notes:**

- Credit-only accounts work (`has_billing: false`, `billing_creditonly: 1`).
- Check state with `vastai show instances` (**must be empty between runs**) and
  `vastai show user --raw` (`credit` / `balance` / `total_spend`).
- **`--max-dph` must be set deliberately:** the default `0.60` *excludes* the larger-VRAM cards
  that `--min-vram 40` needs. The two recommendations conflict unless both are given.
- An RTX 4090 at ~$1.00/hr was never the cheapest option — that recommendation came from a
  too-narrow first search. One cheap 4090 offer (`id 25814730`) persistently reports
  `dlperf 3.0` against ~97 for a healthy 4090: treat it as a broken listing.
- Colab's free T4 is $0 but cannot host arm B (OOM at 11.8 GB of 12 GB, §C.4) and was
  returning HTTP 503. The spend buys capability, not convenience.

### C.6 Cost safety — the failure mode that actually happened

A real leak occurred twice during development (**~$0.13 total**, credit-only, no card charged). Both times a *test* reached the real CLI. The traps did not save it, for two independent reasons:

**1. `vastai destroy instance` prompts for confirmation.** It has a `-y, --yes  Skip confirmation prompt` flag. The `trap cleanup EXIT` called it without `-y`, so in a non-interactive context it read EOF, printed `Aborted.`, and **left the instance running and billing**. A cost-safety trap that itself blocks on stdin is not a cost-safety trap. Now passed `-y`, with a loud warning on failure.

**2. `vast_run.sh` shadowed its own test double.** The script began with an unconditional `export PATH="$HOME/.local/share/uv/tools/vastai/bin:$PATH"`, which put the **real** CLI ahead of any mock. A "dry run" therefore created three real instances. PATH is now extended only when `vastai` is not already resolvable.

Two further safeguards:

**Preflight leak check.** Step 1 lists any existing `tabpfn-pilot` instances and requires confirmation before starting, so a leak cannot accumulate unnoticed across runs.

**Dry-run fixture.** `scripts/gpu_helpers/mock_vastai.sh` answers every call the runner makes. It refuses to run (exit 99) unless it *is* the resolved `vastai`, compared by realpath:

```bash
mkdir -p /tmp/mockbin
cp scripts/gpu_helpers/mock_vastai.sh /tmp/mockbin/vastai
chmod +x /tmp/mockbin/vastai
cp <offers.json> /tmp/mock_offers.json

# NOTE: /tmp/mockbin MUST be first, and the real CLI dir must NOT be ahead of it.
PATH="/tmp/mockbin:$PATH" TABPFN_TOKEN=pk_dummy \
    bash scripts/gpu_helpers/vast_run.sh --yes --arms B_in_domain
```

**Verify no leak at any time, and always after a run:**

```bash
vastai show instances          # must reach "Total: 0 instances"
vastai show invoices --raw     # line items; GPU vs storage charges
vastai show user --raw         # credit / total_spend
```

Note that **credit keeps dropping after a destroy** — Vast posts GPU charges into a daily invoice bucket in arrears, so the number moves for minutes afterwards. To distinguish arrears from live burn, sample the credit twice a minute apart with zero instances: if it is flat, nothing is billing. (Measured flat at `9.8693473543` across two minutes with 0 instances.)

Storage is billed separately from GPU time, and an instance still `loading` incurs storage charges without ever taking a GPU charge — so a short-lived mistake shows up as cents, not dollars, but it is still real.

### C.7 macOS portability

BSD `base64` (macOS) rejects a positional filename — `base64 -d file` fails with
`invalid argument`, where GNU `base64` accepts it. Scripts must use stdin redirection
(`base64 -d < file`). Artifact transfer wraps the base64 payload in
`__VAST_B64_BEGIN__`/`__VAST_B64_END__` markers and extracts between them, so CLI decoration
around the output cannot corrupt the stream.

## 5. Getting help / common failures

| Symptom | Fix |
| --- | --- |
| `TABPFN_API_KEY not set: export TABPFN_API_KEY=... or add a TABPFN_API_KEY=... line to a .env file` | §0 auth. Check `TABPFN_ENV_FILE` if `.env` is not at repo root. |
| `ModuleNotFoundError: tabarena` / autogluon import errors | TabArena not installed → §0 frontier setup (`/tmp/tabarena` clone + editable install). |
| `tabpfn_client` version mismatch / results don't match committed CSVs | Pin `tabpfn-client==0.3.3` (§0). Verdicts are version-stamped (`v3_default`); re-read master report §15 before trusting comparisons. |
| `FileNotFoundError: data/raw/<ds>.csv` | Run §A.1. `spanish_motor_*` → `prepare_insurance_datasets.py --only spanish_motor`; `freMTPL2freq_binary` needs `freMTPL2freq.csv` present first. |
| `KeyError: Target column ... not found` | §A.1 table lists the exact target per dataset — usually a dataset was hand-edited; re-download. |
| `No rows with save_path found` (reload check) | Run a classifier trial first (§B.3) — the check reads its log CSV. |
| Rescore script prints `MISSING ... results.pkl` | Task caches are gitignored → rerun §A.3 + §A.6 pilot first (hosted credits). |
| `multi_dataset_regression_benchmark_results.csv` missing (legacy) | It lives at `data/processed/`; regenerate from `notebooks/baseline_experiments/08_multi_dataset_regression_benchmark.ipynb` (GLM-era). |
| Legacy: `ModuleNotFoundError: tabpfn.finetune_utils` / import mismatch | Need sibling `../TabPFN-upstream/src` checkout (2026-04 era, v6) — §0 legacy setup. |
| Legacy: catboost rows empty / `catboost_not_available` | Expected — catboost was not installed in the 2026-04 env; rows are logged, not errors. |
| `beMTPL16.csv` vs `bemtl16.csv` both in `data/raw/` | Only `bemtl16.csv` is used by every script/registry; `beMTPL16.csv` is a stale duplicate artifact — ignore (don't delete without checking git history). |
| Outputs land in `scripts/benchmarks/eval/` but docs point at `scripts/eval/` | Scripts compute the former, committed outputs live in the latter (repo reorg) — see §A.3 ⚠. |
| Seed-42 rerun clobbers committed CSVs | Prefer `--seed 7` (suffixed files) or copy CSVs aside first. §A.5 finisher deletes n_estimators=1 rows in place — back up `home_turf_sweep_results.csv` before re-running. |
| Vast: `This action requires login` / 403 on a key you just set | The CLI reads `~/.config/vastai/vast_api_key`, not `~/.vast_api_key` — §C.1. If the key IS set, the account has 2FA and needs a session: `bash scripts/gpu_helpers/vast_login.sh` (§C.3). |
| Vast: `No 2FA challenge found` | Stale secret — each `tfa send-email` invalidates the previous one. Re-run `vast_login.sh` rather than pairing an old secret with a new code (§C.3). |
| Vast: `Team SSH keys are not supported` | Expected on a team account; SSH is unavailable. Use the default `--transport execute`. The CLI exits 0 on this failure, so check output, not exit codes (§C.3). |
| Vast: run silently stops mid-way, no traceback | Kernel OOM SIGKILL — uncatchable by `try/except`. Look for `rc=137` per arm (§C.4). Give it `--min-vram 40`. |
| Vast: `cheapest` picked a Tesla V100 / ancient GPU | `dlperf/$` favours old hardware whose kernels recent PyTorch dropped. Use `--pick value` with the default architecture whitelist (§C.3). |
| Vast: nothing matched / no offer within ceiling | `--min-vram 40` needs `--max-dph` above 0.60 — the defaults conflict (§C.5). |
| Vast: pip appears hung for ~20 min | Something is compiling numpy from source — you used `requirements.txt` (pins `numpy<2`, no cp313 wheel). Use the bootstrap's package list (§C.3). |
| macOS: `base64: invalid argument <file>` | BSD `base64` rejects a positional filename. Use `base64 -d < file` (§C.7). |
| Vast: `Aborted.` after a run, instance still listed | `vastai destroy instance` **prompts**; it needs `-y`. The EXIT trap used to omit it, leaking a billing instance (§C.6). |
| Vast: `0: ambiguous redirect` at runtime although `bash -n` passed | macOS ships bash **3.2.57** and it precedes Homebrew bash on PATH; 3.2 mis-parses a heredoc nested inside a process substitution. Keep Python in real files, not heredocs-in-substitutions (§C.3). |
| Vast: a "dry run" created real instances | The runner prepended the real CLI's dir to PATH, shadowing the test double. Use `scripts/gpu_helpers/mock_vastai.sh` with the mock dir *first* on PATH; it refuses (exit 99) if it is not the resolved `vastai` (§C.6). |
| Vast: credit keeps falling after destroying everything | Billing posts to a daily invoice bucket in arrears. Sample `credit` twice a minute apart with 0 instances — flat means nothing is live (§C.6). |
