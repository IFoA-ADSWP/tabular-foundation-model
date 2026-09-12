# Experiment Design: Insurance-Specialized TabPFN Fine-Tuning (v6)

> Date: 2026-09-11 | Status: **R1 complete — smoke test only; R2, R3 and Q4/Q5 not run** | Related: #22, #129, #156, #159
> Builds on: PRE_FINETUNING_INVESTIGATIONS.md, master report (v3, canonical folds)
>
> **Reconciled 2026-09-12.** R1 has now run. Read the outcome alongside this design:
> - **`SMOKE_TEST_SCOPE.md`** — what R1 proved and, more importantly, what it never exercised
>   (notably **arms C/D, so the transfer question in the Research Question below is still
>   untested**). Also records where R1 deviated from this design.
> - **`FINE_TUNING_PILOT_RESULTS.md`** — the R1 numbers (§5c) and their statistical limits (§5d).
> - **`NEXT_STAGE_PROPOSAL.md`** — the proposed next stage (LODO transfer, audit schema, gates).
>   Note it leads with the fact that the transfer experiment was already run and came out
>   pooled-negative on v2 (`CLASSIFIER_HOMOGENEITY_HYPOTHESIS_METHOD.md`), so the next stage is a
>   **re-test on v3**, not a first look. Nothing in it is approved or funded.
>
> The `R3 Gate` in this document is the pre-specified decision rule for advancing rungs. R1
> evidence (arm B ≈ arm A, both inside the noise floor) points to its "otherwise stop" branch,
> but the gate is specified on R2 and **R2 has not been run** — so it has never been formally
> evaluated. Do not cite R1 as a gate decision.
>
> Deviations of R1 from this design: split was a fixed 2,000/1,000 cap rather than 70/30; the
> 15% validation split was not implemented; `context_samples` was recorded but used by neither
> arm; arms C/D were not run; R1 cost $0.34 on Vast rather than $0 on Colab T4 (T4 was 503).

---

## Research Question

Does fine-tuning TabPFN on insurance data improve performance on **unseen insurance tasks** versus raw TabPFN and actuarial baselines (GLM)?

---

## Available Datasets (15 total, successor repo)

### Classification targets (binary)

| Dataset | File | Rows | Target | Positive Rate | Market | Master report outcome |
|---|---|---|---|---|---|---|
| COIL 2000 | `coil2000.csv` | 9,822 | CARAVAN | 5.97% | NL | WIN (frontier best) |
| US Lapse Agent | `uslapseagent.csv` | 29,317 | surrender | 38% | US | WIN (frontier best) |
| EU Direct Lapse | `eudirectlapse.csv` | 23,060 | lapse | 12.81% | EU | EXCEPTION (GLM wins) |
| freMTPL2 Binary | `freMTPL2freq_binary.csv` | 50,000 | ClaimIndicator | 5.02% | FR | Stage A/B signal |
| Aus. Vehicle | `ausprivauto0405.csv` | 67,856 | ClaimOcc | 6.81% | AU | TIE (linear floor) |
| Spanish Motor Lapse | `spanish_motor_lapse.csv` | ~50,000 | lapse | ~? | ES | New |
| Spanish Motor Freq | `spanish_motor_freq.csv` | ~50,000 | claim_freq | ~? | ES | New |
| bemtl16 | `bemtl16.csv` | 58,723 | liability_claims | 36% | BE | WIN (frontier best) |
| bemtl97 | `bemtl97.csv` | 163,212 | claim | 11.2% | BE | TIE (linear floor) |
| norauto | `norauto.csv` | 184,000 | NbClaim | 4.6% | NO | TIE (linear floor) |
| fretelematic | `fretelematic.csv` | ~2,000 | ? | ~? | FR | New |

### Regression/continuous targets

| Dataset | File | Rows | Targets | Market |
|---|---|---|---|---|
| freMTPL2 (full) | `freMTPL2freq.csv` | 673,383 | ClaimNb, Exposure, ClaimAmount | FR |
| Aus. Auto | `ausautoBI8999.csv` | 22,036 | log AggClaim | AU |
| Aus. Vehicle | `ausprivauto0405.csv` | 67,856 | VehValue | AU |
| Spanish Motor Severity | `spanish_motor_severity.csv` | ~50,000 | severity | ES |

---

## Pilot Dataset Selection (4 datasets)

For the initial pilot, select 4 classification datasets that cover:

1. **Different sizes:** small (9.8K), medium (23K-29K), large (50K+)
2. **Known outcomes:** wins, ties, and the exception
3. **Different markets:** NL, US, EU, ES, FR, BE, AU

| Dataset | Rows | Target | Market | Why include |
|---|---|---|---|---|
| **coil2000** | 9,822 | CARAVAN | NL | Small, known win, frontier best |
| **uslapseagent** | 29,317 | surrender | US | Medium, known win, 38% positive rate |
| **eudirectlapse** | 23,060 | lapse | EU | The exception — TabPFN loses to GLM. Tests if fine-tuning helps where it fails |
| **spanish_motor_lapse** | 53,501 | LapseB | ES | New dataset, 35.4% positive rate, larger scale |

**Deferred for Phase 2:**
- freMTPL2 Binary (Stage A/B signal — replicate first)
- bemtl16/bemtl97 (larger BE datasets)
- norauto (largest, 184K rows)
- ausautoBI8999 (regression target)

---

## Training Splits

### Outer split (experiment level)
- **70/30 train/test**, stratified on target, **seed=42**
- Test set used **exactly once** per arm for final evaluation
- If master report canonical folds are available, reuse them for direct comparability

### Validation split
- **15% of train** held out for config selection (early stopping, hyperparameter choice)
- Not used for final evaluation

### Inner split (TabPFN level)
- `get_preprocessed_dataset_chunks` does its own internal 80/20 for ensemble construction
- Automatic; does not affect outer test set

---

## Config Grid

### Pilot config (limited, for feasibility)
Start with a single config to validate the pipeline:

| Parameter | Value | Rationale |
|---|---|---|
| context_samples | 64 | Faster than 128; expand if signal exists |
| max_finetune_steps | 3 | Middle of Stage A/B grid (1, 3, 5) |
| n_estimators | 2 | Speed; upgrade to 8 if time permits |
| learning_rate | 1e-5 | Default; matches Stage A/B |
| fit_mode | "batched" | Required for fine-tuning |

### Expanded grid (if pilot shows signal)

| Parameter | Values |
|---|---|
| context_samples | 64, 128 |
| max_finetune_steps | 1, 3, 5 |
| n_estimators | 2, 8 |
| learning_rate | 1e-5 |
| fit_mode | "batched" |

---

## Experimental Arms

### Q0: Does fine-tuning help? (pilot arms)

| Arm | Fine-tune data | Eval data | Tests |
|---|---|---|---|
| **A — Raw TabPFN** | none | target dataset | Baseline |
| **B — In-domain** | target dataset (train) | target dataset (test) | Does fine-tuning help this dataset? |
| **E — GLM baseline** | — | target dataset | Linear floor |
| **F — CatBoost baseline** | — | target dataset | Tree floor |

### Q4: Does pool composition matter? (later arms)

| Arm | Fine-tune data | Eval data |
|---|---|---|
| **C — All-other pooled** | all other datasets | target dataset |
| **D — Homogeneous pooled** | datasets passing transfer test | target dataset |

---

## Scale Ladder

| Rung | Target train N | Target test N | Pool N | Device | Purpose |
|---|---|---|---|---|---|
| R1 | 2,000 | 1,000 | 2,000 | Colab T4 | Pilot, validate pipeline |
| R2 | 5,000 | 2,000 | 10,000 | Colab T4 | Medium-scale signal |
| R3 | Full (9K-50K) | 30% of full | Full (~120K) | Vast RTX 4090 | Production scale |

R3 only runs if R1-R2 shows fine-tuning improves over raw.

---

## Factorial Extension: N × Train Ratio (Q5)

To answer Q5, run a factorial design on coil2000 (9.8K rows):

| Factor | Levels |
|---|---|
| Total N | 1K, 2K, 5K |
| Train ratio | 20/80, 50/50, 80/20 |

This gives a 3×3 grid of fine-tuned vs raw comparisons. The outcome is a surface plot of fine-tuning benefit (ΔROC) across N × ratio. If the surface peaks at small N + high ratio, we have a clear use case: thin-segment fine-tuning.

---

## Data Processing Pipeline

### Bottleneck Analysis

| Step | Time per run | Deterministic? | Shared across arms? |
|---|---|---|---|
| Weight download | ~30s | yes | yes (once per session) |
| Weight load | ~5s | yes | yes (once per session) |
| Data loading + encoding | ~500ms | yes | yes |
| **TabPFN preprocessing** | **~15s** | **yes** | **yes** |
| Fine-tuning | ~5-10s | no | no |
| Inference | ~2s | no | no |

**Key insight:** TabPFN preprocessing (`get_preprocessed_dataset_chunks`) is deterministic — same dataset + same config = same output. It's also the bottleneck at ~15s per run. But all arms share the same preprocessed data.

**For the pilot (16 runs):** 16 × 15s = **4 minutes wasted** on redundant preprocessing.
**For R2 (50+ runs):** 50 × 15s = **12+ minutes wasted**.

### Optimal Pipeline: Preprocess Once, Cache, Then Experiment

```
Step 1: PREPROCESS (once per dataset)
   raw data → get_preprocessed_dataset_chunks() → cache to disk
   
Step 2: EXPERIMENT (per arm)
   cached data → arm-specific logic → results
   
Step 3: AGGREGATE (once)
   results/*.parquet → query → report
```

### Cache Structure

```
outputs/finetune/
├── cache/                              # preprocessed data (shared across arms)
│   ├── coil2000/
│   │   ├── preprocessed.ctx64.npz      # preprocessed chunks (context=64)
│   │   ├── preprocessed.ctx128.npz     # preprocessed chunks (context=128)
│   │   ├── ground_truth.npy            # aligned labels
│   │   ├── test_indices.csv            # reproducible splits
│   │   └── meta.json                   # preprocessing config + hashes
│   ├── uslapseagent/
│   ├── eudirectlapse/
│   └── spanish_motor_lapse/
├── results/                            # arm-specific results
│   ├── coil2000/
│   │   ├── arm_A_raw_seed42.parquet    # predictions + metrics
│   │   ├── arm_B_in_domain_seed42.parquet
│   │   ├── arm_E_glm_seed42.parquet
│   │   └── arm_F_catboost_seed42.parquet
│   └── ...
└── pilot_manifest.json                 # run registry
```

### Why This Is Optimal

| Aspect | Naive | Optimal |
|---|---|---|
| Preprocessing runs | 16× per dataset | **1× per dataset** |
| Preprocess time (pilot) | ~4 min | **~1 min** |
| Storage overhead | None | ~50MB/cache (negligible) |
| Result reproducibility | Re-run everything | Cache is deterministic, results are cached |
| Parallelization | Hard | Easy — arms are independent once cached |

### Caching Strategy

| When to invalidate cache | How |
|---|---|
| Dataset changes | Compare SHA256 of raw CSV |
| Config changes | context_samples, max_finetune_steps, seed |
| Preprocessing code changes | Version hash in meta.json |

**Cache lookup logic:**

```python
cache_key = f"{dataset}_ctx{config.context_samples}_s{seed}"
cache_path = f"outputs/finetune/cache/{dataset}/preprocessed.ctx{config.context_samples}.npz"

if cache_exists(cache_path) and cache_is_valid(cache_path, dataset_sha):
    data = load_cache(cache_path)
else:
    data = preprocess(raw_data, config)
    save_cache(cache_path, data, meta)
```

### Storage Budget

| Item | Size | Count | Total |
|---|---|---|---|
| Preprocessed cache (per dataset × context) | ~10MB | 4 datasets × 2 contexts | ~80MB |
| Predictions (per run) | ~1KB | ~200 runs | ~200KB |
| Ground truth (per dataset) | ~10KB | 4 datasets | ~40KB |
| Metrics parquet (per run) | ~500 bytes | ~200 runs | ~100KB |
| **Total** | | | **~80MB** |

### Processing Time Comparison

| Phase | Naive | Optimal |
|---|---|---|
| Preprocess (4 datasets × 2 contexts) | 16 × 15s = 240s | 8 × 15s = 120s |
| Run experiments (16 runs) | 16 × 10s = 160s | 16 × 2s = 32s |
| **Total** | **400s** | **152s** |

**2.6x speedup for pilot, better for larger grids.**

### Software Requirements (updated)

```
pyarrow>=14    # Parquet I/O
joblib         # caching (optional, for memoization)
hashlib        # SHA validation (stdlib)
```

For each target dataset, the pool = all other classification datasets.

**Sampling:** Proportional to dataset row count, 10K cap per source.

**Example:** Target = EU Lapse, Pool = coil2000 + uslapseagent + spanish_motor_lapse + freMTPL2_binary + ...

---

## Metrics

### Primary
- **ROC AUC** (where non-linear structure exists)
- **PR AUC** (imbalanced discrimination)

### Secondary
- **Brier score** (calibration)
- **Log loss** (probabilistic calibration)
- **ECE** (expected calibration error)

### Operational
- **GPU time** (wall clock per run)
- **Peak VRAM** (memory profiling)

---

## R3 Gate (proceed to full scale)

Proceed to R3 if **any** of the following hold in R2 (seed 42):
- Arm B ROC > Arm A ROC (in-domain helps)
- Arm B ROC > Arm E ROC (beats GLM)

Otherwise stop at R2 and report findings.

---

## Budget

| Item | Cost |
|---|---|
| R1 (pilot, 4 datasets × 4 arms, 1 config) | $0 (T4, ~1 hour) |
| R2 (4 datasets × 4 arms, expanded grid) | $0 (T4, ~4 hours) |
| R3 (full scale, paid Vast) | ~$5-10 |
| **Total worst case** | **~$10** |

---

## Hardware Requirements

### Free Tier: Google Colab T4

| Spec | Detail |
|---|---|
| GPU | NVIDIA Tesla T4 (16 GB VRAM) |
| RAM | ~12 GB |
| Session limit | 12 hours, idle disconnect ~90 min |
| GPU hours/week | ~15–30 (dynamic, not guaranteed) |
| Cost | $0 |

**What works on T4:**
- Raw TabPFN inference (all datasets, all sizes)
- Fine-tuning with n_estimators=2, context=64, steps≤3, N≤5K
- Diagnostic scripts (GLM vs RandomForest)

**What doesn't work on T4:**
- n_estimators=8 with N>5K (OOM risk)
- context=128 with N>10K (OOM risk)
- Full-scale grid search (time limit)

**Workaround:** Use `colab-cli` (`colab new --gpu T4`) for headless automation.

### Paid Tier: Vast.ai RTX 4090

| Spec | Detail |
|---|---|
| GPU | NVIDIA RTX 4090 (24 GB VRAM) |
| Cost | ~$0.50/hr (spot) |
| Availability | Market-driven; reliability ≥ 0.90 recommended |

**When Vast is needed:**
- R3 (full-scale, all datasets)
- n_estimators=8 with N>5K
- Factorial extension (9 cells × multiple configs)

**Setup:** SSH in, clone repo, `pip install -r requirements.txt`, run scripts.

### Local M1 Mac (Diagnostic Only)

| Spec | Detail |
|---|---|
| Device | Apple Silicon M1 (8 GB unified memory) |
| Fine-tuning | Not practical (slow, memory-constrained) |
| Use case | Diagnostics, data prep, result analysis |

**Limit:** ~3K rows for local fine-tuning. Beyond that, use Colab.

### Memory Guidelines

| Config | Approximate VRAM | Max N on T4 (16 GB) |
|---|---|---|
| n_estimators=2, context=64 | ~4 GB | ~10K |
| n_estimators=2, context=128 | ~6 GB | ~5K |
| n_estimators=8, context=64 | ~10 GB | ~3K |
| n_estimators=8, context=128 | ~14 GB | ~2K |

**Rule:** Start with n_estimators=2, context=64. Only increase if signal justifies the memory cost.

### Software Requirements

From `requirements.txt`:
- Python 3.12+
- `tabpfn>=6,<7` (local weights, v3 default)
- `torch>=2.0,<3`
- `numpy`, `pandas`, `scikit-learn`
- `pyarrow` (for Parquet I/O)
- `catboost` (optional, for baselines)
- `google-colab-cli` (for headless Colab access)

---

## Pilot Execution

### What We're Running

**Phase 1a — Pilot (R1 only):**

| Parameter | Value |
|---|---|
| Datasets | 4 (coil2000, uslapseagent, eudirectlapse, spanish_motor_lapse) |
| Arms | 4 (Raw TabPFN, In-domain fine-tuned, GLM, CatBoost) |
| Config | context=64, steps=3, n_estimators=2, lr=1e-5 |
| Target N | 2,000 train / 1,000 test |
| Pool N | 2,000 (for pooled arms — deferred to R2) |
| Device | Colab T4 (free) |
| Expected duration | ~1 hour |

**Execution order:**
1. Arm A (raw) on all 4 datasets — establishes baseline
2. Arm E (GLM) on all 4 datasets — establishes linear floor
3. Arm F (CatBoost) on all 4 datasets — establishes tree floor
4. Arm B (in-domain fine-tuned) on all 4 datasets — the test

### Expected Outcomes

| Question | What we'll learn | Possible answers |
|---|---|---|
| Q0: Does fine-tuning help on classification? | Whether fine-tuned TabPFN beats raw TabPFN | Yes (proceed to Q1-Q5) / No (pivot to regression Q3) |
| Q1: Does fine-tuning help EU Lapse? | Whether fine-tuning closes the GLM gap | Yes (headline result: fine-tuning works where TabPFN fails) / No (boundary identified) |
| Does fine-tuning vary by dataset? | Whether the effect is dataset-dependent | Yes (some help, some don't — need to understand why) / No (uniform effect) |
| Does n_estimators=2 limit performance? | Whether we need to upgrade to 8 | Compare VRAM headroom — if T4 has room, upgrade for R2 |

### Measuring Success

**Primary success metric: ROC AUC**

Why ROC, not Brier?
- The diagnostic showed both datasets are linear on Brier — fine-tuning is unlikely to improve calibration
- But freMTPL2 shows ROC signal (RF 0.583 > GLM 0.555) — ranking may improve
- Master report: TabPFN is already AUC rank #1 on most datasets; fine-tuning may push it further

**Success criteria:**

| Outcome | Threshold | Interpretation |
|---|---|---|
| **Fine-tuning helps** | Arm B ROC > Arm A ROC by ≥ 0.005 on any dataset | Fine-tuning adds value over raw TabPFN |
| **Fine-tuning beats GLM** | Arm B ROC > Arm E ROC on EU Lapse | Fine-tuning closes the headline gap |
| **Fine-tuning is dataset-dependent** | Effect varies across datasets | Pool composition and dataset selection matter |
| **Fine-tuning doesn't help** | Arm B ROC ≤ Arm A ROC on all datasets | TabPFN is already at ceiling for classification |

**Secondary metrics (tracked but not gated):**

| Metric | Why track | What it tells us |
|---|---|---|
| PR AUC | Imbalanced discrimination | Does fine-tuning help identify rare events? |
| Brier score | Calibration | Already expected flat; confirms diagnostic |
| Log loss | Probabilistic calibration | More sensitive than Brier |
| ECE | Expected calibration error | Segment-level miscalibration |
| GPU time | Operational cost | Feasibility for production |
| Peak VRAM | Memory profiling | Whether we can upgrade configs |

### Data Storage

**Storage format:**
- **Parquet** for tabular metrics (one row per run) — columnar, typed, compressed, queryable
- **NPZ** for per-sample arrays (predictions, ground truth) — numpy-native, compact
- **JSON** for metadata — human-readable, small

```
outputs/finetune/
├── pilot_metrics.parquet          # tabular: one row per run, all metrics as columns
├── predictions.npz                # dict of {run_id: np.array(n_test)} — compressed
├── ground_truth.npz               # dict of {run_id: np.array(n_test)} — compressed
├── indices.npz                    # dict of {run_id: {"train": [...], "test": [...]}}
├── fold_metrics.parquet           # fold-level metrics (dataset, arm, fold, seed, metrics)
└── pilot_manifest.json            # run registry with configs, SHAs, version info
```

**Why Parquet over CSV:**

| Feature | CSV | Parquet |
|---|---|---|
| Type safety | ❌ strings only | ✅ typed columns (float, int, string) |
| Compression | ❌ none | ✅ snappy/gzip (5-10x smaller) |
| Query speed | ❌ full scan | ✅ column pruning, predicate pushdown |
| Schema enforcement | ❌ none | ✅ explicit schema |
| Cross-platform | ✅ universal | ✅ universal |

**Query example:**

```python
import pandas as pd

df = pd.read_parquet("outputs/finetune/pilot_metrics.parquet")

# Filter and aggregate
eudirectlapse = df[df["dataset"] == "eudirectlapse"]
in_domain = eudirectlapse[eudirectlapse["arm"] == "B"]

# Compare arms
pivot = df.pivot_table(
    index="dataset",
    columns="arm",
    values="roc_auc",
    aggfunc=["mean", "std"]
)

# Standard error across folds
fold_se = df.groupby(["dataset", "arm"])["roc_auc"].sem()
```

**Original repo compatibility:**
The original repo uses CSV (`tabpfn_finetune_trial_results.csv`, `domain_finetune_study_runs.csv`). Parquet is a superset — CSV can be exported via `df.to_csv()` if needed for backward compatibility.

**Per-sample arrays (NPZ):**

```python
import numpy as np

preds = np.load("outputs/finetune/predictions.npz")
truth = np.load("outputs/finetune/ground_truth.npz")
idxs = np.load("outputs/finetune/indices.npz", allow_pickle=True)

# Access by run_id (e.g., "coil2000_B_in_domain_seed42")
run_id = "coil2000_B_in_domain_seed42"
y_prob = preds[run_id]
y_true = truth[run_id]
test_idx = idxs[run_id]["test"]
train_idx = idxs[run_id]["train"]

# Recalculate metrics
from sklearn.metrics import roc_auc_score, brier_score_loss
roc = roc_auc_score(y_true, y_prob)
brier = brier_score_loss(y_true, y_prob)

# Per-sample errors (for conformal intervals)
errors = np.abs(y_true - y_prob)
```

**Metadata schema (pilot_manifest.json):**

```json
{
  "experiment": "pilot_v1",
  "created": "2026-09-11T12:00:00Z",
  "tabpfn_version": "6.x.x",
  "datasets": {
    "coil2000": {"sha256": "abc123", "rows": 9822},
    "uslapseagent": {"sha256": "def456", "rows": 29317},
    "eudirectlapse": {"sha256": "ghi789", "rows": 23060},
    "spanish_motor_lapse": {"sha256": "jkl012", "rows": 53501}
  },
  "config_defaults": {
    "context_samples": 64,
    "max_finetune_steps": 3,
    "n_estimators": 2,
    "learning_rate": 1e-5
  },
  "arms": ["A", "B", "E", "F"],
  "seeds": [42]
}
```

**After pilot:**
- Summary CSV: `outputs/finetune/pilot/results_summary.csv` — one row per arm×dataset
- Push to Git: `git add outputs/finetune/pilot/ && git commit`
- Large files (*.npy, *.tabpfn_fit): store in `outputs/` (gitignored), backed up to S3 if needed

### Pilot Results (R1) — as executed

> Filled in 2026-09-12 from `outputs/gpu-pilot/pilot_metrics.parquet` (16 arm-runs).
> Full analysis, statistical limits and evidence gaps: `FINE_TUNING_PILOT_RESULTS.md` §3 and §5d.
> Scope boundary (what R1 did *not* exercise): `SMOKE_TEST_SCOPE.md`.

**Provenance, because the arms did not all come from one run.** A_raw and B_in_domain were
produced on the **L40S GPU instance** (20:16-20:19, python 3.11.12 / torch 2.7.0+cu128 /
scikit-learn 1.9.1). E_glm and F_catboost were produced **locally on CPU** earlier the same day
(09:20, python 3.13.15 / torch 2.11.0+cpu / scikit-learn 1.6.1). The split is deterministic
(seed 42), so the test rows are identical across arms and the comparison holds — but the
baselines and the TabPFN arms ran in different environments, and CPU-vs-GPU timings are not
comparable.

Reported `config` in the metrics file is the same `PILOT_CONFIG` for every arm, including
`context_samples: 64`, which **neither arm uses**. Treat the config column as nominal; the
effective per-arm settings are in `FINE_TUNING_PILOT_RESULTS.md` §5d.4.

#### coil2000 (9,822 rows, CARAVAN, 5.97% positive)

| Arm | ROC AUC | PR AUC | Brier | Time (s) |
|-----|---------|--------|-------|----------|
| A (raw) | 0.767530 | 0.187545 | 0.050767 | 15.93 |
| B (in-domain) | 0.768962 | 0.193316 | 0.050912 | 35.68 |
| E (GLM) | 0.683029 | 0.130695 | 0.055922 | 0.03 |
| F (CatBoost) | 0.699271 | 0.175306 | 0.051626 | 3.17 |

Delta (B − A): ROC **+0.001432** · PR +0.005771 · Brier +0.000145 (worse)
Delta (B − E): ROC **+0.085933**

#### uslapseagent (29,317 rows, surrender, 37.9% positive)

| Arm | ROC AUC | PR AUC | Brier | Time (s) |
|-----|---------|--------|-------|----------|
| A (raw) | 0.936312 | 0.834384 | 0.087321 | 6.31 |
| B (in-domain) | 0.935505 | 0.837523 | 0.086968 | 26.59 |
| E (GLM) | 0.927057 | 0.817249 | 0.091007 | 0.01 |
| F (CatBoost) | 0.929690 | 0.829297 | 0.093386 | 0.54 |

Delta (B − A): ROC **−0.000807** · PR +0.003139 · Brier −0.000353 (better)
Delta (B − E): ROC **+0.008448**

#### eudirectlapse (23,060 rows, lapse, 12.81% positive) — the design's known exception

| Arm | ROC AUC | PR AUC | Brier | Time (s) |
|-----|---------|--------|-------|----------|
| A (raw) | 0.588090 | 0.194347 | 0.113679 | 12.34 |
| B (in-domain) | 0.597603 | 0.198178 | 0.113328 | 36.36 |
| E (GLM) | 0.574352 | 0.160071 | 0.116278 | 0.02 |
| F (CatBoost) | 0.573768 | 0.183049 | 0.115089 | 0.59 |

Delta (B − A): ROC **+0.009513** · PR +0.003831 · Brier −0.000351 (better)
Delta (B − E): ROC **+0.023251**

#### spanish_motor_lapse (53,502 rows, LapseB, 35.4% positive)

| Arm | ROC AUC | PR AUC | Brier | Time (s) |
|-----|---------|--------|-------|----------|
| A (raw) | 0.723295 | 0.570771 | 0.197776 | 6.49 |
| B (in-domain) | 0.727187 | 0.579063 | 0.196739 | 18.30 |
| E (GLM) | 0.616563 | 0.446904 | 0.222162 | 0.01 |
| F (CatBoost) | 0.711423 | 0.541185 | 0.201455 | 0.73 |

Delta (B − A): ROC **+0.003892** · PR +0.008292 · Brier −0.001037 (better)
Delta (B − E): ROC **+0.110624**

#### Summary across datasets

| Dataset | ΔROC (B−A) | ΔPR (B−A) | ΔBrier (B−A) | ΔROC (B−E) | B beats F? | Cost of B vs A |
|---|---|---|---|---|---|---|
| coil2000 | +0.001432 | +0.005771 | +0.000145 | +0.085933 | yes | 2.2x |
| uslapseagent | −0.000807 | +0.003139 | −0.000353 | +0.008448 | yes | 4.2x |
| eudirectlapse | +0.009513 | +0.003831 | −0.000351 | +0.023251 | yes | 2.9x |
| spanish_motor_lapse | +0.003892 | +0.008292 | −0.001037 | +0.110624 | yes | 2.8x |

**Observations:**

1. **ROC is mixed and tiny** — 3 datasets up, 1 down, |ΔROC| ≤ 0.0096. Against the test-set
   resolution computed in `FINE_TUNING_PILOT_RESULTS.md` §5d.6 (95% CI widths 0.031-0.118),
   **no delta is distinguishable from zero.**
2. **PR AUC improves for B on all four datasets** (+0.0031 to +0.0083), and Brier improves on
   3 of 4. This is the only consistent directional pattern in the data. It is still inside the
   noise floor, so it is recorded as an observation, **not a finding** — but it is the one
   signal a better-powered run should be designed to test.
3. **B beats E (GLM) on all four, and F (CatBoost) on all four.** So the fine-tuned model
   clears both actuarial baselines — but so does the raw model, which is the point of §4 below.
4. **Fine-tuning costs ~2-4x the compute** of raw inference (41.1 s → 116.9 s across the four
   datasets) for a change indistinguishable from noise.

#### Conclusions

- **Does fine-tuning help on classification?** **Not measurably.** Three datasets up, one down,
  every ROC delta ≤ 0.0096 — inside the sampling error of the test sets. The pilot can rule out
  a *large* effect; it cannot demonstrate a small one, and at 2,000 training rows with 3 passes
  it was not powered to.
- **Does it help EU Lapse (eudirectlapse, the known exception)?** Directionally yes, and it is
  the largest ROC gain (+0.0095) — but the CI width on that dataset is 0.108, so **not
  established**. This is the hypothesis most worth re-testing with more power, because it is the
  one case where TabPFN currently loses to GLM.
- **Recommendation for R2:** **do not proceed as designed — pivot.** Reasoning:
  1. The gate's *first* criterion (**B > A**) shows no signal in R1, so it fails.
  2. The gate's *second* criterion (**B > E**) passes on all four datasets — **but so does arm A
     (raw TabPFN beats GLM on all four).** A criterion satisfied by the baseline arm cannot
     discriminate the fine-tuning hypothesis. **The gate needs tightening before it is used to
     authorise spend** — see below.
  3. R1's test sets are too small to resolve the effect size observed, so R2 at 5,000/2,000 would
     still be underpowered for a ≤0.01 effect.

  **Better use of the next spend:** run the arms that answer the design's own research question
  (does fine-tuning help on *unseen* insurance tasks) — **C/D, the transfer arms — which have
  never been run**, at R1 scale. That is cheap, currently untested, and speaks to deployment in a
  way no in-domain rerun can.

#### Gate defect to fix before R2/R3

The `R3 Gate` above admits if `B > A` **or** `B > E`. Since raw TabPFN already beats the GLM on
all four datasets, the second condition is satisfied without any fine-tuning at all. A gate that
admits on a condition the baseline arm also satisfies does not test the hypothesis it was written
for. Recommended replacement: admit only on a **B vs A** criterion, with the threshold set from a
power calculation on the observed test-set variance, and require it on a majority of datasets.

---

## Open Decisions

1. **Canonical folds:** **RESOLVED** — folds saved in `scripts/eval/*/results_per_split.csv`. Reuse lapse benchmark folds for EU Lapse, insurance benchmark folds for others.
2. **Spanish motor positive rate:** **RESOLVED** — 35.4% (18,960 lapse / 34,540 no lapse).
3. **n_estimators:** Start with 2 for speed, upgrade to 8 if time permits.
4. **Pool dry run:** **RESOLVED** — pool fits on T4 at pilot scale.

---

_Next step: Build the runner script or run the pilot on T4._
