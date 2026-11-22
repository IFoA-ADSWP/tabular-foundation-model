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
| **TabICL / TabICLv2** | ✅ pip, `tabicl` | CPU supported: `device=None` "auto-selects CUDA → XPU → MPS → CPU", with CPU and disk offloading for large sets. "For larger datasets, we recommend a GPU." Corrected 2026-11-21 — see the re-check below. |
| **TabDPT / TabDPT-Turbo** | ✅ pip, `tabdpt` | README states no device; neither a CPU claim nor a GPU requirement. Corrected 2026-11-21. |
| **iLTM, LimiX, TabSwift** | ❌ | GPU required. LimiX v2 is source-only and wants a CUDA-matched `torch` plus a `flash-attn` wheel. |
| **TabSTAR** | ✅ pip, `tabstar` | README states no device; the 2026-08 "GPU required" is unverified either way. Corrected 2026-11-21. |
| **SAP-RPT-OSS, Mitra, BetaTabPFN** | ❌ | GPU required. |
| **Nori, OrionMSP, TabFlex** | ❌ | GPU required. |

**TabPFN Client is the only FM with a hosted API.**

### Access re-check (2026-11-21)

Read from the PyPI JSON API and each project's README on 2026-11-21. Installability changed; fit
time at our sizes did not become known, and that is the number that matters here.

| package | latest | released | CPU, as stated by the project |
|---|---:|---|---|
| `tabicl` (TabICL v2) | 2.2.0 | 2026-09-02 | `device=None` auto-selects CUDA → XPU → MPS → CPU; CPU and disk offloading; GPU "recommended" for large datasets |
| `tabdpt` (TabDPT) | 1.3.2 | 2026-11-02 | not stated |
| `tabstar` (TabSTAR) | 1.2.2 | 2026-10-16 | not stated |
| `tabfm` | 1.0.1 | 2026-07-21 | unchanged: self-host, needs GPU for practical use |
| LimiX v2 | not on PyPI | — | source install; CUDA-matched `torch` + `flash-attn`; `--device cpu` exists, "cuda recommended" |

The package versions of TabPFN itself have also moved well past this repository's pin: `tabpfn`
is at 10.2.0 (2026-11-17) and `tabpfn-client` at 0.10.1 (2026-11-20), against `tabpfn==8.5.0` and
`tabpfn-client==0.3.3` here.

**Installable is not practical.** No project states a CPU fit time at 163k–678k rows; TabICL
quotes only an H100 figure. The probe in #687 measures one fold on CPU and reports nothing about
accuracy. Until it lands, the "wide model line" option is available in principle and unmeasured in
practice.

#### Measured on this machine (2026-11-21, #687)

One fold of `bemtl97_amount` (163,212 rows, 10 features, 88.8% zeros), `device="cpu"`,
`tabicl` 2.2.0 with `torch` 2.15.0, 8.0 GB RAM. No accuracy claim — timing and memory only.

| context (train) rows | queries (test) | fit | predict | peak RSS |
|---:|---:|---:|---:|---:|
| 1,000 | 32,643 | 0.6 s | **862.1 s** | 4.44 GB |
| 5,000 | 1,000 | 0.4 s | 48.2 s | 2.00 GB |
| 25,000 | 32,643 | — | **SIGKILL** | — |
| 50,000 | 32,643 | — | **SIGKILL** | — |
| 163,212 | 32,643 | — | **SIGKILL** (after 98 s) | — |

**Prediction is the whole cost, and fitting is free.** There is no training: `fit` is 0.4–0.6 s
because it only holds the context. The forward pass over the test rows is what costs, at
**26 ms per query row** (1k context) and **48 ms per query row** (5k context). Those two points do
*not* define a single law — per-pair cost falls from 26 µs to 10 µs — so do not extrapolate a
context size from them; measure it.

**What the numbers mean for a comparison here.** A five-fold run predicts 5 × 32,643 rows. At the
measured 26 ms/row that is ~72 minutes per dataset, and at 48 ms/row ~2.2 hours, using a context
that is 0.6–3% of the training fold. The model can be *run*; it cannot be *compared* on a schedule,
and a context that small is not the model being measured. Context of 25,000 rows or more does not
survive memory on this machine.

**This is a property of the family and of CPU inference, not of TabICL alone.** TabDPT and TabSTAR
are the same shape of in-context model, so the constraint transfers; testing them here would
reproduce the timing, not resolve it. A GPU or a hosted endpoint is the way past it.

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

Only **TabPFN** has a hosted API (not re-checked on 2026-11-21; the other rows were). But we can pip install and run most of TabArena's top methods locally on CPU — CatBoost, XGBoost, LightGBM, EBM, TorchMLP, FastaiMLP, and sklearn baselines. That's already most of the leaderboard.
