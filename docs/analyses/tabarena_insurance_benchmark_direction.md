# TabArena — Insurance Benchmark Direction

## What we learned about TabArena

TabArena is the leading living benchmark for tabular ML (NeurIPS 2025 spotlight). It benchmarks 38 method families across 51 IID datasets + 142 BeyondArena datasets. Results are published at https://tabarena.ai/ and the framework is open-source at github.com/autogluon/tabarena.

The leaderboard on Hugging Face is **read-only** — a display of pre-computed results. There is no automated "submit your CSV" pipeline.

To join the ecosystem, the "➕ Your Benchmark?" tab invites you to contact the TabArena team for a human-curated review process.

## Our constraint — private data

Real insurance data is proprietary. A public benchmark (Option A below) can use CASdatasets, but the real value for insurers is a private evaluation framework (Option B).

## Two paths

### Option A — Open insurance benchmark (for TabArena submission)

- Uses public CASdatasets (eudirectlapse, freMTPL, etc.)
- Anyone can reproduce
- TabArena team reviews and potentially features it
- Good for conference credibility

### Option B — Private evaluation framework (for real insurers)

- Code is open, data stays in-house
- Standardised protocol: same splits, same metrics, same preprocessing every time
- Insurance company runs it on their own book of business
- Transparency is in the methodology, not the data

The two are compatible — Option A is for conferences, Option B is what gets used.

## Models we can access (no GPU required)

| Via hosted API | Via pip + CPU |
|---|---|
| TabPFN (tabpfn-client) | CatBoost, XGBoost, LightGBM |
| | RF, GLM, EBM, PerpetualBooster |
| | TorchMLP, FastaiMLP |

TabFM, TabICL, TabDPT, and most other foundation models require GPU. TabPFN Client is the only tabular FM with a hosted API.

## What we'd need to build for either path

- Standardised k-fold CV splits
- Consistent model wrappers with fixed configs
- Single evaluation script running all models on all datasets
- Clean code repo with README

Most of this already exists in our notebooks and src/ — it's a packaging job, not new research.

## Reference docs created this session

- `docs/analyses/tabarena_reference.md` — overview of TabArena
- `docs/analyses/cpu_model_feasibility.md` — which models we can run
- `docs/REPORT_REGISTRY.md` — entry for this doc

## Key links

| Resource | URL |
|---|---|
| TabArena leaderboard | https://tabarena.ai/ |
| TabArena code | https://github.com/autogluon/tabarena |
| TabArena paper | https://arxiv.org/abs/2506.16791 |
| TabPFN Client | `pip install tabpfn-client` |
| Our repo | IFoA-ADSWP/TabPFN |
