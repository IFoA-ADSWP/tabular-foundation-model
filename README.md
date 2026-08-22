# TabPFN for Actuarial Tasks — Research Repository

**Can a transformer-based foundation model (TabPFN) compete with traditional actuarial models (GLM, CatBoost, XGBoost) on insurance tasks like lapse prediction and claim frequency modeling?**

This repo contains experiments by the **IFoA Actuarial Data Science Working Party (ADSWP)** comparing [TabPFN](https://github.com/PriorLabs/TabPFN) — a pretrained in-context learning model for tabular data — against industry-standard baselines. The primary result is the paper **"There's Life in the Old GLM Yet!"**.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# reproducible exact-match env (recommended for replication):
uv pip sync requirements.lock
jupyter notebook notebooks/adswp_project/01_TabPFN_classifier_eudirectlapse.ipynb
```

### API key setup

Scripts using the hosted TabPFN client need an API key. Set the `TABPFN_API_KEY` environment variable, or place a `.env` file containing `TABPFN_API_KEY=...` in the repo root, or point `TABPFN_ENV_FILE` at a `.env` file elsewhere. Scripts fail with a clear error if none is found.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for detailed setup and contribution guide.

## Directory Structure

```
├── data/                           # Datasets
│   ├── raw/                        #   eudirectlapse.csv, freMTPL2freq.csv, ...
│   └── processed/                  #   Intermediate benchmark results (CSV)
│
├── src/                            # Shared Python modules
│   ├── data_loader.py              #   Load CSVs, train/test split
│   ├── data_loader_class.py        #   OOP wrapper for notebook use
│   ├── evaluation_metrics.py       #   AUC, accuracy, F1, RMSE, MAE
│   ├── model_training.py           #   Baseline models + train/predict pipeline
│   ├── baseline_config.py          #   Centralised config (seeds, paths, params)
│   ├── baseline_utils.py           #   Preprocessing, metrics, scaling helpers
│   └── cleanup_outputs.py          #   Output directory maintenance
│
├── notebooks/
│   ├── adswp_project/              # Domain-specific TabPFN applications
│   │   ├── 01_TabPFN_classifier_eudirectlapse.ipynb
│   │   ├── 02_TabPFN_freMTPL.ipynb
│   │   ├── 03_usautoBI_fit.ipynb
│   │   ├── 04_tabpfn_embedding_workflow.ipynb
│   │   └── REPLICATION_There_Is_Life_in_the_Old_GLM_Yet.ipynb
│   │
│   └── baseline_experiments/       # Head-to-head model comparisons
│       ├── 01_claims_classification_baseline.ipynb
│       ├── 02_tabpfn_vs_glm_lapse.ipynb
│       ├── 03_tabpfn_vs_glm_summary.ipynb
│       ├── 04_probability_calibration.ipynb
│       ├── 05_regression_finetuning.ipynb
│       ├── 06_synthetic_data_exploration.ipynb
│       ├── 07_multi_dataset_benchmark.ipynb
│       └── 08_multi_dataset_regression_benchmark.ipynb
│
├── outputs/
│   ├── current/                    # Latest figures + tables
│   │   ├── figures/                #   Figure1–Figure6 PNGs
│   │   ├── tables/                 #   Table1–Table4 CSVs
│   │   └── logs/                   #   Finetuning logbooks
│   ├── archive/                    # Historical experiment outputs (gitignored)
│   └── replication/                # Paper replication outputs (config, tables, figures)
│
├── docs/
│   ├── reports/                    # Analysis reports (see REGISTRY.md)
│   ├── analyses/                   # Methodology docs and analysis summaries
│   ├── papers/                     # Paper content + LaTeX style files
│   ├── status/                     # Project status and security record
│   └── REPLICATION_SETUP_GUIDE.md  # Step-by-step replication instructions
│
├── scripts/                        # One-off experiment scripts
├── legacy/                         # Deprecated R analysis scripts
├── tests/                          # Smoke tests
├── requirements.txt
├── CONTRIBUTING.md
└── CHANGELOG.md
```

## Notebooks at a Glance

| Notebook | What it does |
|----------|-------------|
| `adswp_project/01` | TabPFN classifier on eudirectlapse (lapse prediction) |
| `adswp_project/02` | TabPFN on freMTPL (claim frequency regression) |
| `adswp_project/03` | US Auto BI fitting |
| `adswp_project/04` | TabPFN embedding workflow |
| `adswp_project/REPLICATION` | Full paper replication — TabPFN vs GLM |
| `baseline_experiments/01` | Claim classification baseline |
| `baseline_experiments/02` | TabPFN vs GLM lapse prediction |
| `baseline_experiments/03` | TabPFN vs GLM summary comparison |
| `baseline_experiments/04` | Probability calibration analysis |
| `baseline_experiments/05` | Regression finetuning |
| `baseline_experiments/06` | Synthetic data exploration |
| `baseline_experiments/07` | Multi-dataset benchmark (classification) |
| `baseline_experiments/08` | Multi-dataset benchmark (regression) |

## Key Findings

**Current verdict (2026-08-06):** TabPFN is the best risk-ranking model in the suite — AUC #1 over GLMs, LightGBM, CatBoost, XGBoost and RF on all six canonical classification datasets (deltas +0.006 to +0.033 over the best GLM, five ≥2.5 SE (four >2.5); calibration never significantly worse, log loss better or tied vs the best GLM), holding #1 at production scale up to 184K rows (master report §14.11; [`TABPFN_BENCHMARK_SUMMARY.md`](docs/reports/TABPFN_BENCHMARK_SUMMARY.md)). It wins the business case where the question is which policies are risky — underwriting triage, lapse/surrender propensity, claim/no-claim targeting — and stays on the bench for pricing/regression targets where GBDTs win. The eudirectlapse loss below is the known exception.

On the eudirectlapse lapse-prediction task (13% lapse rate):

| Aspect | Result |
|--------|--------|
| **Discrimination (ROC AUC)** | GLM 0.599, TabPFN 0.593 — near tie |
| **Calibration (Brier)** | TabPFN after isotonic calibration **0.1080** vs GLM 0.1098 |
| **Bottom line** | TabPFN matches a tuned GLM out-of-the-box with no traditional training. Post-hoc calibration gives it a small edge on probability accuracy — relevant for pricing and reserving. |

See [`docs/reports/TECHNICAL_COMPANION.md`](docs/reports/TECHNICAL_COMPANION.md) for a walkthrough of every metric.

## Documentation Index

The docs are extensive. Start here:

- **`docs/reports/REPORT_REGISTRY.md`** — maps every report to its source notebook and evidence files
- **`docs/reports/TECHNICAL_COMPANION.md`** — explains all metrics in actuarial context (best first read)
- **`docs/REPLICATION_SETUP_GUIDE.md`** — step-by-step to reproduce the paper results
- **`docs/status/STATUS_REPORT_FINAL.md`** — summary of validated findings and recommendations

## Dependencies

Python 3.10+. Core stack: numpy, pandas, scikit-learn, torch, TabPFN, matplotlib, seaborn. Optional: XGBoost, LightGBM, CatBoost.

## References

- [TabPFN upstream](https://github.com/PriorLabs/TabPFN) — the foundation model
- [CASdatasets](https://CRAN.R-project.org/package=CASdatasets) — R package supplying the datasets
- `legacy/adswp_project_scripts/` — original R analysis scripts

## License

MIT — see [`LICENSE`](LICENSE).
