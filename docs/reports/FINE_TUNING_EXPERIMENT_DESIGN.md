# Experiment Design: Insurance-Specialized TabPFN Fine-Tuning (v6)

> Date: 2026-09-11 | Status: draft | Related: #22, #129, #156, #159
> Builds on: PRE_FINETUNING_INVESTIGATIONS.md, master report (v3, canonical folds)

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

## Pool Composition Strategy

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

### Pilot Report Template

After R1 completes, fill in:

```
## Pilot Results (R1)

### Dataset: coil2000 (9,822 rows, CARAVAN)
| Arm | ROC AUC | PR AUC | Brier | Time (s) |
|-----|---------|--------|-------|----------|
| A (raw) | ? | ? | ? | ? |
| B (in-domain) | ? | ? | ? | ? |
| E (GLM) | ? | ? | ? | ? |
| F (CatBoost) | ? | ? | ? | ? |

Delta (B - A): ? (positive = fine-tuning helps)
Delta (B - E): ? (positive = beats GLM)

### Dataset: eudirectlapse (23,060 rows, lapse)
...

### Conclusions
- Does fine-tuning help on classification? [Yes/No/Depends]
- Does it help EU Lapse? [Yes/No]
- Recommendation for R2: [proceed / pivot / stop]
```

---

## Open Decisions

1. **Canonical folds:** **RESOLVED** — folds saved in `scripts/eval/*/results_per_split.csv`. Reuse lapse benchmark folds for EU Lapse, insurance benchmark folds for others.
2. **Spanish motor positive rate:** **RESOLVED** — 35.4% (18,960 lapse / 34,540 no lapse).
3. **n_estimators:** Start with 2 for speed, upgrade to 8 if time permits.
4. **Pool dry run:** **RESOLVED** — pool fits on T4 at pilot scale.

---

_Next step: Build the runner script or run the pilot on T4._
