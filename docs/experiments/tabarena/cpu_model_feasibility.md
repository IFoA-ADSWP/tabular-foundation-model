# Model Feasibility — TabArena Methods We Can Access

> **Status:** reference — 2026-08 scoping note on what runs without a GPU.

Constraint: no GPU, but hosted API inference is fine.

TabArena benchmarks 38 method families. Here's what we can practically use.

## Foundation Models (20 families on TabArena)

| Model | Access | Notes |
|---|---|---|
| **TabPFN-3** | ✅ pip + hosted API | `tabpfn-client` — Prior Labs cloud. 50M tokens/day. Only FM with a real API. |
| **TabPFN-2.6 / v2** | ✅ pip + hosted API | Same client, older versions. |
| **TabFM** | ✅ pip, self-host only | `pip install tabfm[pytorch]`. No API. Non-commercial license. Needs GPU for practical use. |
| **TabICL / TabICLv2** | ❌ | No pip package, no API. GPU required. |
| **TabDPT / TabDPT-Turbo** | ❌ | GPU required. |
| **iLTM, LimiX, TabSwift, TabSTAR** | ❌ | GPU required. |
| **SAP-RPT-OSS, Mitra, BetaTabPFN** | ❌ | GPU required. |
| **Nori, OrionMSP, TabFlex** | ❌ | GPU required. |

**TabPFN Client is the only FM with a hosted API.**

## GBDTs (6 families — all CPU-friendly, all pip installable)

| Model | Pip | TabArena Elo (default) | Notes |
|---|---|---|---|
| **CatBoost** | `pip install catboost` | 1378 (default) / 1408 (tuned) | Best categorical support. Already in our stack. |
| **XGBoost** | `pip install xgboost` | 1317 (default) / 1350 (tuned) | Already in our stack. |
| **LightGBM** | `pip install lightgbm` | 1277 (default) / 1386 (tuned) | Fastest GBDT. Already in our stack. |
| **ChimeraBoost** | `pip install chimeraboost` | — | Newer GBDT variant. Worth a look? |
| **EBM (InterpretML)** | `pip install interpret` | ~1235 | Fully interpretable. Good for regulatory contexts. |
| **PerpetualBooster** | `pip install perpetual` | — | "Never needs tuning" claim. |

## Neural Nets (5 families — some CPU-friendly)

| Model | Access | Notes |
|---|---|---|
| **TorchMLP** | ✅ CPU, via AutoGluon | All variants run on CPU. ~2.5s/1K rows. |
| **FastaiMLP** | ✅ CPU, `pip install fastai` | All variants CPU. ~2.9s/1K rows. |
| **RealMLP** | ⚠️ Default on CPU, tuned needs GPU | Default ~10s/1K. Tuned+ensembled 2040s/1K on GPU. |
| **TabM** | ⚠️ Default on CPU, tuned needs GPU | Default ~7.5s/1K. |
| **ModernNCA** | ❌ | GPU required. |

## Tree Ensembles + Baselines (all CPU, all sklearn)

RandomForest, ExtraTrees, KNN, Linear (Ridge/Logistic) — all via `pip install scikit-learn`.

## AutoGluon (reference pipeline)

`pip install autogluon` — best-quality preset runs on CPU (1735s/1K rows). Could be worth running as a "best-effort ensemble" baseline.

## New models to consider adding to our stack

| Model | Why |
|---|---|
| **EBM** (InterpretML) | Fully interpretable. Good for "we care about explainability" narrative in conference talks. |
| **ChimeraBoost** | Newer GBDT, possible edge over XGBoost. |
| **PerpetualBooster** | No tuning needed — matches "zero-config" narrative alongside TabPFN. |
| **AutoGluon** | Ensemble of all the above — could be the "best possible" ceiling. |

## Bottom line

Only **TabPFN** has a hosted API. But we can pip install and run most of TabArena's top methods locally on CPU — CatBoost, XGBoost, LightGBM, EBM, TorchMLP, FastaiMLP, and sklearn baselines. That's already most of the leaderboard.
