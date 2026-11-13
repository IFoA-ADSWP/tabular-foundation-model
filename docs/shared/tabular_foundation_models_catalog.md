# Tabular Foundation Models — Catalog

> **Status:** reference — catalog of the model family.

All known tabular foundation models (pre-trained, zero-shot/in-context learning). Excludes deep learning architectures that require per-dataset training (FT-Transformer, TabNet, SAINT, etc.).

## Quick Access Table

| Model | Creator | Hosted API? | CPU-feasible? | Install | License |
|---|---|---|---|---|---|
| **TabPFN** (v3/v2.6/v2) | Prior Labs | ✅ tabpfn-client | ⚠️ ≤1K rows (v2.5-era; see note) | `pip install tabpfn` | Non-commercial (v3) / Apache 2.0 (v2) |
| **TabFM** | Google | ❌ | ✅ JAX CPU fast | `git clone + pip install` | Apache 2.0 code. Non-commercial weights |
| **TabICL / v2** | Microsoft | ❌ | ⚠️ Slow | Source from GitHub | MIT |
| **TabDPT / Turbo** | Yandex | ❌ | ✅ Efficient | Source from GitHub | Apache 2.0 |
| **TabSwift** | ServiceNow | ❌ | ✅ Designed for CPU | Source from GitHub | Apache 2.0 |
| **TabSTAR** | ServiceNow | ❌ | ⚠️ Small datasets | Source from GitHub | Apache 2.0 |
| **Nori / Nori-30M** | Stanford | ❌ | ✅ Tiny model | Source from GitHub | Non-commercial |
| **TabFlex** | Huawei | ❌ | ✅ Flexible arch | Source from GitHub | Research-only |
| **iLTM** | ServiceNow | ❌ | ❌ Not practical | Source from GitHub | Research-only |
| **OrionMSP** | Orion Research | ❌ | ❌ Not practical | Source from GitHub | Research-only |
| **Mitra** | Microsoft | ❌ | ❌ Not practical | Source from GitHub | Research-only |
| **BetaTabPFN** | Community | ❌ | Same as TabPFN | Fork of tabpfn | Non-commercial |
| **SAP-RPT-OSS** | SAP | ❌ | ✅ | Source from GitHub | Open-source |

## Key Findings

**Only one model has a hosted API:** TabPFN (via `tabpfn-client`). All others require self-hosting.

**Only one model is pip-installable:** TabPFN (`pip install tabpfn`). All others require `git clone` from GitHub and manual setup.

**CPU-feasible** (could run locally without GPU):
- TabPFN — slow, practical only ≤1K rows (Corrected 2026-08: hosted v3 accepts up to 1M training rows — see master report §12.1 model-version correction; the small-window framing was v2.5-era.)
- TabFM — JAX backend is fast on CPU, weights are non-commercial
- TabDPT/Turbo — efficient architecture, Apache 2.0
- TabSwift — designed for CPU from the start, Apache 2.0
- Nori-30M — tiny 30M params, non-commercial
- TabFlex — flexible architecture, research-only
- SAP-RPT-OSS — relative pretraining, open-source

**Non-commercial licenses dominate.** Many models (TabPFN v3, TabFM weights, Nori) restrict commercial use. The most permissively licensed CPU-feasible FMs are TabDPT/Turbo, TabSwift, and SAP-RPT-OSS (all Apache/open-source, all require self-hosting).

## Relevance to Our Project

For our insurance research with no GPU:
- **TabPFN Client** remains the only practical option for hosted inference on full datasets
- **TabDPT or TabSwift** could be added to our local benchmark scripts if we want another FM comparison — both are Apache 2.0, CPU-friendly, and pip-installable from GitHub
- **TabFM** is interesting but non-commercial weights block production use, and no hosted API
- **TabFM on the frontier suite (2026-08-07): assessed but not run** — the full-context in-context-learning fit OOM-killed the process on coil2000 on this 8 GB machine (hard kill, not catchable); a row-capped fallback was scripted (`run_tabfm.py`) but never executed; non-commercial weights block production use regardless. TabFM remains outside the benchmark comparison by assessment, not by measurement (master report §14.13).

## Links

| Resource | URL |
|---|---|
| TabPFN | https://github.com/priorlabs/tabpfn |
| TabFM | https://github.com/google-research/tabfm |
| TabDPT | https://github.com/yandex-research/tab-dpt |
| TabSwift | https://github.com/ServiceNow/TabSwift |
| TabSTAR | https://github.com/ServiceNow/TabSTAR |
| TabICL | https://github.com/microsoft/tabicl |
| Nori | https://github.com/jinghanw/nori |
