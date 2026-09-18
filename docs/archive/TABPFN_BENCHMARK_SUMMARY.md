# TabPFN for Insurance — Benchmark Summary

One-page answer to the question: **Is TabPFN worth adopting for insurance modeling?** Written for actuarial colleagues — the full evidence and methods live in the technical report (references at the end).

**Verdict: TabPFN is the best risk-ranking model in the suite — AUC and PR AUC #1 over GLMs, LightGBM, CatBoost, XGBoost and RF on all six canonical classification datasets (AUC deltas +0.006 to +0.033 over the best GLM, five ≥2.5 SE; paired per-fold tests significant on all six; stable across split seeds), with calibration (Brier) never significantly worse at default settings — two ~1e-4 paired-significant exceptions appear once tuned/feature-engineered baselines enter (ausprivauto0405 log loss/Brier vs the linear family, bemtl97 Brier vs lgbm; §14.13) — and log loss better or tied vs the best GLM. It holds #1 at production scale (up to 184K rows), not just on small data. Data efficiency is a secondary strength, not its identity. Caveat: at the extreme top decile the ranking edge is dataset-dependent (rank 1 on 4/6 by lift) — validate triage cutoffs on your own book.**

## Where TabPFN fits — at a glance

| Scenario | What we measured | Call |
|---|---|---|
| Small data (≤5K rows) | Wins 8/9 size-sweep cells | Use it |
| Risk-ranking — which policies are risky (underwriting triage, lapse/surrender, claim/no-claim) | Best AUC of all 9 methods on all 6 canonical classification datasets, up to 184K rows | Use it |
| Lapse classification and premium regression | Spanish lapse AUC 0.7553 vs 0.7500 (5/5 folds); premium RMSE 19.07 vs 81.8 | Use it, validated on your own book |
| Large regression/frequency datasets (50K+ rows) | Off the parsimony frontier 5 of 12 — all at scale | Prefer GBDT/GLM for the count model; its claim/no-claim reframe is TabPFN triage territory (§14.14) |
| Regulator-facing simplicity | 21-param GLMs within noise of the 10M-param model | Prefer the simple model |

## How we tested it

We built a custom benchmark on real insurance datasets — claims, lapse, frequency and severity — with fair same-fold comparisons and insurance-native metrics (log loss, RMSE, Poisson deviance). Every model ran at default settings with no tuning, so the differences are the models', not the setup's. Tuned/feature-engineered classical baselines were later run on the same canonical folds and do not change the ranking verdict (master report §14.13). The core question is "best accuracy per unit of model complexity" — the parsimony frontier — because regulators and governance care about models an actuary can explain. Everything is re-runnable with one command, with results committed alongside the code.

## The evidence

- **Size sweep** — TabPFN wins 8/9 cells at ≤5K rows; the small-data regime is real.
- **Parsimony frontier** — on the frontier for 7 of 12 datasets (log-loss axis), but off it 5× at scale; 21-param GLMs sit within noise of the 10M-param model.
- **Regression** — the lead does not survive at scale: wins `ausautoBI8999`, ties `vehvalue`, loses the rest.
- **Lapse** — a real win at 5-fold: AUC 0.7553 vs 0.7500 on Spanish motor (wins all 5 folds), plus the premium-regression win.

## Why TabPFN trails on accuracy-per-complexity at scale

Earlier generations could effectively attend to only ~1K training rows, a context-window design limit. The v3 model's API now accepts up to 1M rows and still loses on accuracy-per-complexity and speed — so the measured pattern holds regardless of mechanism (see the §12.1 model-version correction in the master report).

## Caveats

- The `bemtl97` label-leak dataset is excluded; all frontier results use the leak-fixed version (§6 of the master report).
- The `vehvalue` discrepancy between the v1 baseline and the frontier run is protocol-specific, not a stable property of the model.
- The lapse leaderboard's ELO lead is partly carried by the premium-regression task — an artifact of the task mix, not pure lapse skill.
- The `eudirectlapse` lapse task is the disclosed exception to the risk-ranking story: a genuine classification loss (TabPFN AUC 0.6101 vs best GLM 0.6260 — an additive-lapse structure the model doesn't capture), reported in full alongside the AUC #1 results.

## Conclusion & adoption guidance

**Decision rule** (regime analysis `docs/analyses/regime_characterization.md` §3; evidence in master report §8, §14.9, §14.10):

> **Adopt default TabPFN (v3)** when data is scarce — ≤ ~5K training rows (8/9 size-sweep cells won, §13.2) — **or** on classification/lapse-style tasks where the linear floor is far from achievable: best LR/GLM ≥ ~3% behind the best model, or ≥ ~0.05 AUC gap. Every TabPFN win satisfies this — coil2000, bemtl16, uslapseagent, ausautoBI8999, vehvalue, and Spanish lapse (LR 0.684 vs TabPFN 0.7553, 5/5 folds, §14.10, §14.11). The classification case is not small-data-limited: TabPFN posts the best AUC of all 9 methods on all 6 canonical classification datasets, including at production scale (163K–184K rows) — AUC #1 over GLMs, LightGBM, CatBoost, XGBoost and RF (deltas +0.006 to +0.033 over the best GLM, five ≥2.5 SE), with calibration (Brier) never significantly worse and log loss better or tied vs the best GLM (§14.11; two ~1e-4 paired-significant calibration exceptions vs tuned/engineered baselines — §14.13). Where the question is which policies are risky — underwriting triage, lapse/surrender propensity, claim/no-claim targeting — TabPFN wins the business case.
>
> **On regression/frequency targets at scale (≥ ~50K rows), expect TabPFN to be dominated on the accuracy-per-complexity trade-off**: every off-frontier point sits at ≥53.5K rows (money chart); no edge when the GLM floor is within ~2% of achievable (ausprivauto0405, eudirectlapse, norauto, bemtl97 — GLM gap ≈ 0, 0/4 wins); and no edge on frequency targets at scale even with a weak GLM floor, because the signal there is tree-extractable only (Spanish freq: LGBM 0.8916 vs TabPFN 0.9876, Poisson GLM at the 1.0123 null floor, §14.9; freMTPL2freq at 678K rows, §14.8). The "no edge" reading is calibration-only — §14.11.4 shows TabPFN holds a significant AUC ranking edge even in GLM-captured regimes (norauto, bemtl97, ausprivauto0405). Scoping footnote (issue #67, §14.14): the tree-only reading holds on the **count axis** — the same count target reframed as claim/no-claim classification (binary or ordinal) moves TabPFN to AUC rank #1, paired-significant at both seeds (0.7170 vs lgbm 0.7090, p=0.0010; 0.7165, p=0.0020) — so count targets do have a TabPFN pathway, as triage ranking, while the count model itself stays GBDT/GLM territory.
>
> **Between the regimes — and on pricing/regression targets (severity, claim frequency, amount) where GBDTs win — prefer the GLM**: the 11–86-param GLM family is never dominated on any dataset (§14.4), it is statistically indistinguishable from TabPFN on frequency at 21 params (§14.9), and where a fitted-coefficient story is required (a handful of interpretable GLM parameters vs TabPFN's 10M), the GLM is the defensible default. One qualification (issue #67, §14.14): claim-frequency *classification* (claim vs no-claim, 0/1/2+) is a TabPFN ranking win — price with the GLM/GBDT, triage with TabPFN.

- The rule is predictive, not descriptive: it explains the Spanish motor flip at the same 53,502 rows — lapse wins (linear floor far, §14.10), frequency loses on the count axis (tree-only signal, §14.9; its claim/no-claim reframe is a TabPFN ranking win, §14.14) — where a "small data only" rule would not (regime analysis §2).
- Re-test on model-version change: every number here is pinned to `v3_default` (tabpfn-client 0.3.3); re-run before trusting the rule on a new model version. The procedure — trigger, scope, diff, and addendum steps — is master report §15 ("Version-Drift Re-Test Policy", issue #55).

## What's next

The two open questions are settled: the 5-fold lapse re-run confirms the Spanish win, and the Spanish severity frontier is done. Tuned/feature-engineered classical baselines (lr_tuned, glm_eng, lgbm_tuned, cat_tuned, rf_tuned) are now tested on the same canonical folds: TabPFN stays AUC/PR-AUC #1 of 14 methods on all 6 datasets, with glm_eng the closest competitor (ausprivauto0405, +0.0036 AUC, p=0.003); the calibration caveat is two ~1e-4 paired-significant exceptions (ausprivauto0405 log loss/Brier vs the linear family; bemtl97 Brier vs lgbm — master report §14.13). TabFM is closed out, not deferred: it was never run (full-context fit OOM-killed this 8 GB machine; row-capped fallback scripted but never executed; non-commercial weights block production use). Issue #67 is done: count/frequency targets reframed as classification (binary claim/no-claim and ordinal 0/1/2+) put TabPFN at AUC rank #1, paired-significant at both seeds (+0.0080/+0.0098 over lgbm, p=0.0010/0.0020), with log loss/Brier ties-to-better and PR-AUC the only within-noise result — the count model itself is unchanged (Poisson deviance stays GBDT/GLM territory; master report §14.14). Remaining future work: fine-tuned TabPFN inside the parsimony frontier; and version re-runs — the model is pinned to `v3_default`, so re-runs are reproducible.

## References

- Master report: `docs/analyses/tabpfn_vs_gbdt_baselines_finetuning.md` (§1–§14.14; verdict §8)
- Regime analysis: `docs/analyses/regime_characterization.md` (decision rule §3, hypothesis test §2)
- Benchmark portfolio: `docs/analyses/benchmark_portfolio.md`
- Merge plan: `docs/analyses/merge_plan_tabarena.md`

### Source Workbooks

`scripts/benchmarks/run_smoke_tabarena.py`; `scripts/benchmarks/run_tabarena_insurance_benchmark.py`; `scripts/benchmarks/run_lapse_benchmark.py`; `scripts/benchmarks/run_tabarena_insurance_imbalance_pilot.py`; `scripts/benchmarks/run_home_turf_size_sweep.py`; `scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py`; `scripts/eval/insurance_benchmark_v1/run_reframe_frequency.py`; `scripts/eval/insurance_benchmark_v1/analyze_reframe_frequency.py`

### Evidence Files

`scripts/eval/insurance_benchmark_v1/frontier_results_*.csv`; `scripts/eval/insurance_benchmark_v1/money_chart_tabpfn_relative.png`; `scripts/eval/lapse_benchmark_v1/results_per_split.csv`; `scripts/eval/insurance_benchmark_v1/reframe_frequency_results.csv`; `scripts/eval/insurance_benchmark_v1/reframe_frequency_summary.csv`
