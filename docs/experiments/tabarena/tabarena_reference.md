# TabArena Reference

> **Status:** reference — background on the harness.

## What it is

[TabArena](https://tabarena.ai/) is the leading living benchmark for tabular ML — a curated suite of 51 IID datasets (plus 142 BeyondArena datasets testing temporal/grouped shifts) with standardised evaluation across 27+ methods. Accepted as a NeurIPS 2025 spotlight paper.

Measures ROC AUC, RMSE, R², Elo ratings. Run by the AutoGluon team (AWS, University of Freiburg).

## Where TabPFN ranks

TabPFN v3 pareto-dominates the speed/performance frontier on TabArena — a single forward pass outperforms all other models at equivalent inference cost. Earlier versions (v2.0, v2.5) were also top-ranked.

## Why it matters for this project

TabArena validates TabPFN's general tabular capability on a rigorous, independent benchmark. Our repo tests the **insurance-specific question**: does that capability translate to actuarial tasks (lapse, claim frequency) against domain-standard baselines (GLM, CatBoost)?

The answer from our work is nuanced — it translates but doesn't dominate — and TabArena gives us the external context to explain why: TabPFN excels on smaller datasets with interactions, while our eudirectlapse problem has simple additive structure where GLM holds its own. TabArena's BeyondArena suite (temporal generalisation) is directly relevant to actuarial forecasting use cases we haven't tested yet.

## Links

| Resource | URL |
|---|---|
| Leaderboard | https://tabarena.ai/ |
| Paper (NeurIPS 2025) | https://arxiv.org/abs/2506.16791 |
| GitHub | https://github.com/autogluon/tabarena |
