# TabPFN for Actuarial Tasks — Research Repository

> ⚠️ **Version notice:** legacy reports/tables in this repo were tested **Mar–Apr 2026 against TabPFN v2 era (v2.0 via API; weights ID unrecorded)**; current benchmark verdicts are pinned to **v3_default (tabpfn-client 0.3.3)**. See [docs/MODEL_VERSIONS.md](docs/MODEL_VERSIONS.md) for the timeline and what flipped.

**Can a transformer-based foundation model (TabPFN) compete with traditional actuarial models (GLM, CatBoost, XGBoost) on insurance tasks like lapse prediction and claim frequency modeling?**

This repo contains experiments by the **IFoA Actuarial Data Science Working Party (ADSWP)** comparing [TabPFN](https://github.com/PriorLabs/TabPFN) — a pretrained in-context learning model for tabular data — against industry-standard baselines. The primary result is the paper **"There's Life in the Old GLM Yet!"**.

## Quick Start

Build the environment from the lock, and prove it before anything else:

```bash
./scripts/bootstrap_dev.sh          # creates .venv from requirements.lock and asserts the pins
.venv/bin/pytest tests/ -q          # the canonical test command
```

`requirements.txt` is the loose floor that `requirements.lock` is compiled from — do not install it directly.
`requirements-legacy.txt` is the v2-era path for `scripts/legacy_finetuning/` only.

**To run something rather than test it, read [`docs/RUNNING.md`](docs/RUNNING.md).** It names the environment,
the command, the output tree and the runbook section for each route. Note that the benchmark line
(`scripts/eval/`, `scripts/benchmarks/`) runs against a *different* environment — the TabArena venv with
`tabpfn-client 0.3.3` — because the published verdicts were measured against the hosted client.

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
├── docs/                           # Start at docs/README.md
│   ├── RUNNING.md                  #   the route in, if you are running the code
│   ├── EVIDENCE_MAP.md             #   which tree holds which number
│   ├── current/                    #   reports describing the design as built
│   ├── reference/                  #   historical, still cited for provenance
│   ├── archive/                    #   kept for the record, not cited
│   ├── plans/                      #   one plan per task, written before the work
│   ├── adr/                        #   accepted decisions that constrain the code
│   └── analyses/                   #   methodology, diagnostics, result notes
│
├── scripts/                        # Indexed in scripts/README.md
├── results/                        # Committed run captures (see docs/EVIDENCE_MAP.md)
├── legacy/                         # Deprecated R analysis scripts
├── tests/                          # The test suite
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

**Current verdict (2026-08-06):** TabPFN is the best risk-ranking model in the suite — AUC #1 over GLMs, LightGBM, CatBoost, XGBoost and RF on all six canonical classification datasets (deltas +0.006 to +0.033 over the best GLM, five ≥2.5 SE (four >2.5); calibration never significantly worse, log loss better or tied vs the best GLM), holding #1 at production scale up to 184K rows (master report §14.11; [`docs/archive/TABPFN_BENCHMARK_SUMMARY.md`](docs/archive/TABPFN_BENCHMARK_SUMMARY.md)). It wins the business case where the question is which policies are risky — underwriting triage, lapse/surrender propensity, claim/no-claim targeting — and stays on the bench for pricing/regression targets where GBDTs win. The eudirectlapse loss below is the known exception.

On the eudirectlapse lapse-prediction task (13% lapse rate):

| Aspect | Result |
|--------|--------|
| **Discrimination (ROC AUC)** | GLM 0.599, TabPFN 0.593 — near tie |
| **Calibration (Brier)** | TabPFN after isotonic calibration **0.1080** vs GLM 0.1098 |
| **Bottom line** | TabPFN matches a tuned GLM out-of-the-box with no traditional training. Post-hoc calibration gives it a small edge on probability accuracy — relevant for pricing and reserving. |

See [`docs/archive/TECHNICAL_COMPANION.md`](docs/archive/TECHNICAL_COMPANION.md) for a walkthrough of every metric.

## Documentation Index

The full index is **[`docs/README.md`](docs/README.md)** — start there. Two pages answer most questions:

- **[`docs/RUNNING.md`](docs/RUNNING.md)** — which environment, which command, where the output lands.
- **[`docs/EVIDENCE_MAP.md`](docs/EVIDENCE_MAP.md)** — which tree holds the evidence behind a number, and what
  a citation must have.

The report-level registry is [`docs/REPORT_REGISTRY.md`](docs/REPORT_REGISTRY.md), and
[`docs/DOCUMENT_AUTHORITY.md`](docs/DOCUMENT_AUTHORITY.md) says which document wins when two disagree.

## Dependencies

Python 3.12. `scripts/bootstrap_dev.sh` builds `.venv` from `requirements.lock` and refuses an interpreter that
is not 3.12, because the lock's `numpy<2` pin has no wheel for 3.13. Core stack: numpy, pandas, scikit-learn,
torch, TabPFN, matplotlib, seaborn. Optional: XGBoost, LightGBM, CatBoost.

## References

- [TabPFN upstream](https://github.com/PriorLabs/TabPFN) — the foundation model
- [Molnar, *Tabular Foundation Models*](https://tabularfoundationmodels.com/) — external research context; see [`docs/reference/TABULAR_FOUNDATION_MODELS_MOLNAR.md`](docs/reference/TABULAR_FOUNDATION_MODELS_MOLNAR.md)
- [CASdatasets](https://CRAN.R-project.org/package=CASdatasets) — R package supplying the datasets
- `legacy/adswp_project_scripts/` — original R analysis scripts

## License

MIT — see [`LICENSE`](LICENSE).
