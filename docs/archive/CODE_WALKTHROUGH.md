# TabPFN Insurance Benchmark — Code Walkthrough

**Purpose:** What the code actually does, step by step, for colleagues who want to understand the implementation.

**Date:** 2026-08-20

---

## The Big Picture: What Are We Running?

We're asking: **"Can a pretrained transformer model (TabPFN) beat traditional actuarial models on real insurance data?"**

To answer this, we run every model on the same data splits and compare. The core metric is **AUC** (how well the model ranks risky vs safe policies) and **Brier score** (how well-calibrated the probabilities are).

---

## The Main Script: `run_frontier_benchmark.py`

**Location:** `scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py`

This is the workhorse. It runs 9 methods on 12 datasets and produces the Pareto frontier plots.

### What It Does, Step by Step

```
For each dataset (12 total):
    1. Load the CSV
    2. Split into 5 folds (same splits every time, seed=42)
    3. For each fold:
        a. Train 8 CPU methods (GLM, LightGBM, CatBoost, XGBoost, RF, etc.)
        b. Train TabPFN via hosted API (runs last, with retry logic)
        c. Count parameters for each method
        d. Compute AUC, Brier score, log loss
    4. Plot Pareto frontier (accuracy vs complexity)
    5. Save results to CSV + plot to PNG
```

### The 9 Methods We Compare

| Method | What It Is | Parameter Count |
|--------|-----------|-----------------|
| `LogisticRegression` | Standard logistic regression | n_cols + 1 |
| `LogisticGLM` | GLM with logistic link | n_cols + 1 |
| `TweedieGLM` | GLM with Tweedie distribution | n_cols + 1 |
| `PoissonGLM` | GLM with Poisson distribution | n_cols + 1 |
| `RandomForest` | Random Forest (100 trees) | n_estimators × mean_leaves |
| `CatBoost` | CatBoost gradient boosting | n_estimators × mean_leaves |
| `LightGBM` | LightGBM gradient boosting | n_estimators × mean_leaves |
| `XGBoost` | XGBoost gradient boosting | n_estimators × mean_leaves |
| **TabPFN** | Tabular foundation model (hosted API) | **10,000,000 (fixed)** |

### The Pareto Frontier Logic

A model is **"on the frontier"** if no other model is both:
- More accurate (lower metric value) by more than 1 standard error, AND
- Simpler (fewer parameters)

This prevents fold noise from deciding the ranking on closely-matched models.

### Key Code Pattern

```python
# For each fold:
for fold, (train_idx, test_idx) in enumerate(kf.split(X, y)):
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
    
    # Fit each method
    for name, model in methods.items():
        model.fit(X_train, y_train)
        y_pred = model.predict_proba(X_test)[:, 1]
        
        # Compute metrics
        auc = roc_auc_score(y_test, y_pred)
        brier = brier_score_loss(y_test, y_pred)
        logloss = log_loss(y_test, y_pred)
```

---

## The Size Sweep: `run_home_turf_size_sweep.py`

**Location:** `scripts/benchmarks/run_home_turf_size_sweep.py`

**Question:** Does TabPFN only work on small data?

**What It Does:**
1. Takes 3 datasets (coil2000, uslapseagent, bemtl97)
2. Slices each to 1K, 5K, and full size
3. Runs 6 methods on each size
4. Records AUC for each

**Result:** TabPFN wins 8/9 cells at ≤5K rows. The "small-data only" story is wrong.

**Code Pattern:**
```python
# Slice dataset to target size
for target_rows in [1000, 5000, len(X)]:
    if target_rows < len(X):
        X_slice = X.sample(n=target_rows, random_state=42)
        y_slice = y.loc[X_slice.index]
    
    # Run 5-fold CV on the slice
    # Record results
```

---

## The Frequency Reframing: `run_reframe_frequency.py`

**Location:** `scripts/eval/insurance_benchmark_v1/run_reframe_frequency.py`

**Question:** TabPFN loses on "how many claims?" (count). Does it win on "claim vs no-claim" (classification)?

**What It Does:**
1. Takes Spanish motor frequency dataset (53K rows, target = claim count)
2. Creates two reframed targets:
   - **Binary:** `(claims > 0)` → claim vs no-claim
   - **Ordinal:** `min(claims, 2)` → 0 / 1 / 2+ claims
3. Runs 9 methods on binary, 6 on ordinal
4. Compares AUC

**Result:** TabPFN moves from weakest to strongest when reframed as classification.

**Code Pattern:**
```python
# Reframe count target as binary
y_binary = (df['N_claims_year'] > 0).astype(int)

# Reframe as ordinal
y_ordinal = df['N_claims_year'].clip(upper=2)

# Run benchmark on reframed targets
```

---

## The Finality Test: `run_tuned_baselines.py`

**Location:** `scripts/eval/insurance_benchmark_v1/run_tuned_baselines.py`

**Question:** Can properly tuned classical models beat zero-tune TabPFN?

**What It Does:**
1. Takes 6 canonical datasets
2. Runs 14 methods (9 defaults + 5 tuned/engineered):
   - `lr_tuned`: LogisticRegression with hyperparameter search
   - `glm_eng`: PolynomialFeatures + LogisticRegression
   - `lgbm_tuned`: LightGBM with early stopping
   - `cat_tuned`: CatBoost with early stopping
   - `rf_tuned`: RandomForest with hyperparameter search
3. All on same 5 folds as the main benchmark

**Result:** TabPFN stays #1 on AUC and PR-AUC for all 6 datasets.

**Code Pattern:**
```python
# Tuned LightGBM with early stopping
param_grid = {
    'learning_rate': [0.05, 0.1],
    'num_leaves': [31, 127]
}

for params in param_grid_product:
    model = LGBMClassifier(**params)
    
    # Early stopping on validation slice
    X_train, X_val = train_test_split(X_fold, test_size=0.1)
    model.fit(X_train, y_train, 
              eval_set=[(X_val, y_val)],
              callbacks=[lgb.early_stopping(10)])
```

---

## The Analysis Scripts

### `analyze_pr_auc.py`
Reads `frontier_pr_auc_results.csv` and computes:
- TabPFN vs best GLM on PR-AUC (unpaired z-test + paired t-test)
- TabPFN rank among all 9 methods
- Seed stability (do results hold across random seeds?)

### `analyze_tuned_baselines.py`
Merges default results with tuned results and answers:
- Does ANY tuned baseline beat TabPFN with p<0.05?
- How much did tuning improve each method?

### `analyze_reframe_frequency.py`
Same paired-test structure for the frequency reframing experiment.

---

## The Visualization: `plot_money_chart.py`

**Location:** `scripts/eval/insurance_benchmark_v1/plot_money_chart.py`

Produces the project's signature figure:
- x-axis: dataset size (log scale)
- y-axis: TabPFN metric / best metric (1.0 = parity)
- Blue points: on frontier
- Red points: off frontier
- Grey diamonds: size sweep cells

Shows the narrative: "parity at small size, drift above 1.0 as datasets grow; all off-frontier points at ≥53.5K rows."

---

## Data Flow Diagram

```
data/raw/*.csv
    │
    ▼
┌─────────────────────────────────────┐
│  run_home_turf_size_sweep.py        │
│  (3 datasets × 3 sizes × 6 methods)│
│  Output: home_turf_sweep_results.csv│
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  run_frontier_benchmark.py          │
│  (12 datasets × 9 methods)         │
│  Reuses home_turf results          │
│  Output: frontier_results_*.csv     │
│           frontier_plot_*.png       │
└─────────────────────────────────────┘
    │
    ├──► run_reframe_frequency.py
    │    Output: reframe_frequency_results.csv
    │
    ├──► run_tuned_baselines.py
    │    Output: frontier_tuned_baseline_results.csv
    │
    └──► run_tabfm.py
         Output: frontier_tuned_baseline_results.csv
              │
              ▼
┌─────────────────────────────────────┐
│  Analysis Scripts                   │
│  analyze_pr_auc.py                  │
│  analyze_tuned_baselines.py         │
│  analyze_reframe_frequency.py       │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  Visualization                      │
│  plot_money_chart.py                │
│  rescore_focused_imbalance_logloss.py│
└─────────────────────────────────────┘
```

---

## Key Design Decisions

1. **All methods run at defaults** (no HPO) — we compare model CLASSES, not tuned winners. The tuned baselines in `run_tuned_baselines.py` are the explicit exception.

2. **Same 5 folds everywhere** (`StratifiedKFold(5, shuffle=True, random_state=42)`) — enables paired statistical tests and result reuse.

3. **TabPFN runs LAST** — the hosted API is flaky; running it after all CPU methods ensures fast results are always available.

4. **Parsimony = parameter count** — GLM = n_cols + 1, GBDT = n_estimators × mean_leaves, TabPFN = 10M constant.

5. **Beyond-SE dominance rule** — Model A is dominated only if some B is strictly better on BOTH axes with gap exceeding 1 SE.

---

## How to Reproduce

```bash
# 1. Run the size sweep (takes ~30 min)
python scripts/benchmarks/run_home_turf_size_sweep.py

# 2. Run the frontier benchmark (takes ~2 hours)
python scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py

# 3. Run the frequency reframing (takes ~45 min)
python scripts/eval/insurance_benchmark_v1/run_reframe_frequency.py

# 4. Run the tuned baselines (takes ~1 hour)
python scripts/eval/insurance_benchmark_v1/run_tuned_baselines.py

# 5. Generate the money chart
python scripts/eval/insurance_benchmark_v1/plot_money_chart.py
```

All results are committed to the repo, so you can also just look at the CSVs in `scripts/eval/insurance_benchmark_v1/`.

---

## File Reference

| Script | Lines | Time | Purpose |
|--------|-------|------|---------|
| `run_frontier_benchmark.py` | 905 | ~2 hrs | Main Pareto frontier benchmark |
| `run_home_turf_size_sweep.py` | 246 | ~30 min | Dataset size ceiling test |
| `run_reframe_frequency.py` | 237 | ~45 min | Count → classification reframing |
| `run_tuned_baselines.py` | 302 | ~1 hr | Finality test against tuned models |
| `run_tabfm.py` | 145 | ~15 min | Google TabFM baseline |
| `analyze_pr_auc.py` | ~200 | seconds | Statistical tests on PR-AUC |
| `analyze_tuned_baselines.py` | ~200 | seconds | Tuned baseline analysis |
| `analyze_reframe_frequency.py` | ~200 | seconds | Reframing analysis |
| `plot_money_chart.py` | 141 | seconds | Signature visualization |
| `rescore_focused_imbalance_logloss.py` | 83 | seconds | Calibration from cached predictions |
