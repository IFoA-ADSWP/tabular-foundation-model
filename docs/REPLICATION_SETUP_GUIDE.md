# Replication Setup Guide

> ⚠️ **Version notice:** this replication is **TabPFN v2 era (v2.0 via API), Apr 2026** (seed 45, 70:30 split; weights ID unrecorded). Re-running on v3 **will** give different numbers — see [MODEL_VERSIONS.md](MODEL_VERSIONS.md) and the v3 benchmark summary before citing.

## "There's Life in the Old GLM Yet!" - Paper Replication Notebook

This document provides step-by-step instructions to replicate the experiments from the paper.

---

## 1. Overview

**Notebook**: `notebooks/adswp_project/REPLICATION_There_Is_Life_in_the_Old_GLM_Yet.ipynb`

**What the Notebook Does**:
- Loads the eudirectlapse motor insurance lapse prediction dataset (23,060 policies, 13% lapse rate)
- Implements 70:30 stratified train/test split (seed=45) as in the paper
- Trains and evaluates:
  - **TabPFN** (pretrained foundation model)
  - **GLM** (traditional logistic regression)
  - **Baseline models** (CatBoost, XGBoost, RandomForest for context)
- Applies post-hoc isotonic calibration to improve TabPFN probability accuracy
- Regenerates all paper figures and tables

**Key Metrics**:
- ROC AUC (discrimination/ranking ability)
- Brier Score (probability calibration)
- F1 Score (threshold-based balance)

---

## 2. Dataset Setup (REQUIRED)

The notebook uses the **eudirectlapse dataset** from the public **CASdatasets R package** (CRAN).

### Option 0: Bundled CSV (Easiest — No R Required)

A copy of the dataset ships in the repo at `data/raw/eudirectlapse.csv`. The notebook's
data-loading cell checks this file first, so if you cloned the repo you can skip R
entirely — just run the notebook.

### Option A: Automatic Load via R + pyreadr (Recommended if you have R)

If you have R installed:

```bash
# 1. Install required Python package
pip install pyreadr

# 2. Install R package
# In R console:
install.packages('CASdatasets')

# 3. Re-run the data loading cell in the notebook
```

The notebook will automatically detect and load the dataset.

### Option B: Manual Download via R

If you prefer to download the CSV manually:

```r
# In R:
install.packages('CASdatasets')
data(eudirectlapse)
write.csv(eudirectlapse, '~/eudirectlapse.csv')
```

Then upload the CSV to your workspace and modify the data loading cell:

```python
df = pd.read_csv('path/to/eudirectlapse.csv')
```

### Option C: Check Dataset Availability

Run this Python snippet to verify the dataset can be accessed:

```python
import pyreadr
import pandas as pd

try:
    result = pyreadr.read_r('/usr/local/lib/R/site-library/CASdatasets/data/eudirectlapse.RData')
    df = result[None]
    print(f"✓ Dataset loaded: {df.shape}")
except Exception as e:
    print(f"✗ Dataset not found: {e}")
    print("Install CASdatasets R package and try again")
```

---

## 3. Python Environment Setup

### Install Dependencies

```bash
# Core ML packages
pip install pandas numpy scikit-learn torch matplotlib seaborn

# Tree-based models
pip install catboost xgboost

# Dataset loading
pip install pyreadr

# TabPFN (if available)
pip install tabpfn  # or: pip install tabpfn-client for API access
```

### Verify Installation

```python
import pandas as pd
import numpy as np
import sklearn
import torch
import catboost
import xgboost
import pyreadr

print("✓ All packages imported successfully")
```

---

## 4. Running the Notebook

### Step 1: Open the Notebook

```bash
cd notebooks/adswp_project
jupyter notebook REPLICATION_There_Is_Life_in_the_Old_GLM_Yet.ipynb
```

### Step 2: Run Cells in Order

The notebook is designed to run sequentially:

1. **Cell 1**: Title and overview
2. **Cell 2**: Install dependencies (run if needed)
3. **Cell 3**: Import libraries
4. **Cell 4**: Set random seed (SEED=45)
5. **Cell 5**: Configure output directories
6. **Cell 6**: Load dataset (see "Dataset Setup" above)
7. **Cell 7**: Preprocess data (encode categoricals)
8. **Cell 8**: Create train/test splits
9. **Cell 9**: Define evaluation metrics
10. **Cell 10**: Run TabPFN evaluation
11. **Cell 11**: Apply isotonic calibration
12. **Cell 12-15**: Train baseline models (GLM, CatBoost, XGBoost, RandomForest)
13. **Cell 16**: Aggregate results
14. **Cell 17**: Generate paper comparison table
15. **Cell 18-20**: Create figures (ROC AUC, Brier, heatmap)
16. **Cell 21**: Export predictions and artifacts

### Step 3: Review Outputs

All outputs will be saved to:
```
outputs/replication/
├── tables/
│   ├── paper_comparison_table.csv
│   └── model_metrics.csv
├── figures/
│   ├── fig_roc_auc_comparison.png
│   ├── fig_brier_score_comparison.png
│   └── fig_all_metrics_heatmap.png
└── predictions/
    └── all_model_predictions.csv
```

---

## 5. Expected Results

Your results should closely match these from the paper:

| Model | ROC AUC | Brier | Notes |
|-------|---------|-------|-------|
| GLM | ~0.599 | ~0.1098 | Traditional logistic regression |
| TabPFN (Raw) | ~0.593 | ~0.1108 | Pretrained, no tuning |
| TabPFN (Calibrated) | ~0.593 | ~0.1080 ✓ | +0.87% Brier improvement |
| CatBoost | ~0.591 | - | For comparison |
| XGBoost | ~0.551 | - | For comparison |
| RandomForest | ~0.578 | - | For comparison |

**Interpretation**:
- GLM and TabPFN are competitive on raw discrimination (ROC AUC)
- Post-hoc calibration gives TabPFN an edge on probability accuracy (Brier)
- Tree-based models underperform because this dataset has simple, additive structure

---

## 6. Troubleshooting

### Dataset Loading Fails

```
FileNotFoundError: eudirectlapse dataset not available
```

**Solution**: Follow "Dataset Setup" section above. Ensure either:
- R + CASdatasets is installed and pyreadr can access it, OR
- You manually download and upload the CSV

### Module Import Errors

```
ModuleNotFoundError: No module named 'tabpfn'
```

**Solution**: Install missing package:
```bash
pip install tabpfn
```

Or if using API access:
```bash
pip install tabpfn-client
```

### Seed Reproducibility

The notebook uses **SEED=45** (as in the paper). If you get slightly different metrics:
- Verify seed is set before running models
- Some randomness in tree-based models is inherent
- Differences <0.1% are typically acceptable

### Device Issues

If you have CUDA available but want to use CPU:

```python
DEVICE = 'cpu'  # Change in reproducibility cell
```

---

## 7. Paper Reference

**Title**: There's Life in the Old GLM Yet! When a modern foundation model meets decades of actuarial tradition

**Authors**: Cillian Williamson, Scott Hawes, Jin Cui, Karol Gawłowski

**Dataset**: eudirectlapse (CASdatasets R package)
- 23,060 UK motor insurance policies
- 13% lapse rate
- 18 heterogeneous features

**Reproducibility**:
- Stratified 70:30 train/test
- Seed: 45
- Metrics: ROC AUC, Brier Score, F1
- Calibration: Post-hoc isotonic regression

---

## 8. Citation

If you use this replication notebook, please cite:

```bibtex
@article{williamson2026glm,
  title={There's Life in the Old GLM Yet! When a modern foundation model meets decades of actuarial tradition},
  authors={Williamson, Cillian and Hawes, Scott and Cui, Jin and Gaw{\l}owski, Karol},
  year={2026}
}
```

---

## 9. Questions or Issues?

Refer to the embedded notebook documentation for detailed explanations of each cell. The notebook includes:
- Clear comments explaining each step
- References to paper methodology
- Validation checks at each stage
- Export options for further analysis

Happy replicating!
