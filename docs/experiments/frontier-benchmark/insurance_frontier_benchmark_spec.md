# Insurance Frontier Benchmark — Design Spec

Status: agreed spec for issue #27 (repo IFoA-ADSWP/TabPFN). This document was written as the self-contained implementation spec for the frontier benchmark; it was pasted into the issue body and executed (PR #51). It encodes approved design decisions D1–D5 (see §5); those are settled choices, not open options.

---

## 1. Origin — issue #27 and the ticket text

GitHub issue #27 ("Review TabArena", repo IFoA-ADSWP/TabPFN) asks for a benchmark framed as:

> "an efficient frontier in insurance/finance applications being predictive power vs parsimony. Parsimony could be measured in # of parameters and serve as a proxy for interpretability"

This spec captures the agreed interpretation of that request and the design of the benchmark that satisfies it. It is the authoritative reading — do not re-derive.

## 2. Interpretation of the goal

1. **It is a FRONTIER, not a ranking.** The output is not "model X wins." It is a two-axis trade-off space in which multiple models can be simultaneously efficient. The benchmark's job: identify which models are Pareto-efficient — i.e., no other model is both more predictive AND more parsimonious.
2. **Parsimony = # of parameters of the FITTED model, used as a PROXY for interpretability.** The underlying goal is interpretability-aware model selection: actuaries must defend models to regulators and governance (IFoA context: model governance, auditability). A high-accuracy but huge model is often indefensible regardless of its score. Parameter count is the chosen measurable stand-in for "can I explain this to a regulator."
3. **Scope is insurance/finance applications** — a decision aid for actuaries: "on this insurance problem, what is the most predictive model within a complexity budget I can govern?"

## 3. Benchmark definition

> Build the ADSWP insurance benchmark that answers: given an insurance task, which model classes are worth deploying once you trade predictive power against parameter-count parsimony (interpretability)?

## 4. Boundaries (what it is NOT)

- **Not a TabArena submission.** That was Path A of the earlier review. This is our own framework with our own axis.
- **Not a speed frontier.** TabArena already produces ELO-vs-time frontiers; the ticket explicitly picks parsimony as the second axis instead.
- **Not an HPO study.** All methods run at default configuration, matching the existing v1 harness convention, so the frontier compares model CLASSES, not tuned winners.
- **Not a simple leaderboard / ranking.** The deliverable is a Pareto set, not a #1.

## 5. Design decisions

### Datasets — D5: Option A (three sweep datasets) + `norauto` as designated first extension
- **v1:** the three home-turf sweep datasets — `bemtl97` (leak-fixed), `coil2000`, `uslapseagent` — because predictive-power evidence already exists for them. Each dataset is an **independent frontier** (separate table and plot; no cross-dataset Pareto comparison).
- **First extension:** `norauto` (the only other 184K-row dataset) — the strongest second test of "TabPFN drops off the frontier at scale". Priority beyond `norauto` remains open (see §8).
- **Regression — D4: Option A (classification-only v1).** Deferred to a Phase 2 with its own power axis (RMSE / Poisson deviance). Severity (bemtl97_amount, vehvalue) mixes a different power metric, and TabPFN's documented regression weakness would pollute the frontier's first delivery.

### Methods by family (all at defaults)
- Statistical: LogisticGLM / LR, TweedieGLM, PoissonGLM
- Tree-based: LightGBM, XGBoost, CatBoost, RandomForest
- Foundation: TabPFN

### Predictive-power axis
- Classification (v1): **log loss** as the primary metric (the insurance-native metric, per §11.3 of `tabpfn_vs_gbdt_baselines_finetuning.md`); Brier as secondary. Reported as **mean ± SE over the 5 folds** (see D3). AUC/Brier per-fold columns added 2026-08-06 (frontier_auc_brier_rescore_spec.md; master report §14.11).
- Regression (Phase 2 only, per D4): RMSE / Poisson deviance.

### Parsimony axis — parameter-count rule table (critical consistency decision)

| Method family | Counted as | Rationale |
|---|---|---|
| GLM / LR | Count as fitted — post-encoding column count + 1 intercept. The harness uses `cat.codes`, so that is the raw column count (settled non-decision) | Interpretability gold standard: every parameter is a named coefficient with a sign and magnitude |
| GBDTs | `n_estimators × average leaves per tree` (effective decision rules, not raw nodes) | A leaf is the smallest unit of decision logic a practitioner reads; node counts overstate readable structure |
| TabPFN | Fixed architecture parameter count — CONSTANT per dataset regardless of training size | Proxy's honest weakness: TabPFN anchors the top-right (max power, min parsimony) and can never be parsimonious |

Rationale: the counting rules must be (a) reproducible from a fitted model object without HPO, (b) comparable across families, and (c) truthful about what an actuary would actually read. GLM coefficients and GBDT leaves are defensible, auditable quantities; a TabPFN model has no such per-dataset reduction, so its architecture count is used as-is and flagged as constant.

**D2 — GBDT parameter counts (Option A):** LightGBM / XGBoost / CatBoost are re-fit at their recorded defaults (configs in `scripts/eval/insurance_benchmark_v1/method_info.csv`) purely to count parameters — `n_estimators × average leaves per tree`. Tree structure is seed-insensitive for counting. This re-fit is bundled into D1's single run (§6).

**TabPFN parameter count — settled non-decision:** constant per dataset regardless of training size, and orders of magnitude above the GBDTs, so its precise value never changes frontier membership (TabPFN is always the top-right anchor, or dominated at scale). Use the documented architecture figure and do not block on it; confirm the exact hosted-model count from PriorLabs/TabPFN docs at implementation time, not before.

### Pareto-efficiency — D3: Option B (mean ± SE over folds)

Power is compared as **mean ± SE over the 5 folds** (fold rows already exist in the sweep CSV; SE is free). Model A is dominated if there exists model B with power better than A's **beyond SE** — `mean_B + SE_B < mean_A - SE_A` — and strictly fewer params (or vice versa). Models within SE of each other both stay on the frontier; ties on both axes keep both models on. The frontier is the set of models not dominated by any other model in the same dataset's run. Rationale: bemtl97@full gives LGBM 0.3418 vs TabPFN 0.3428 — a point-estimate rule would let fold noise decide frontier membership.

### Expected results to look for
- (a) Which mid-complexity models are **DOMINATED** — beaten on power by TabPFN AND on parsimony by GLM. That is a real "don't deploy this" signal.
- (b) Whether TabPFN's accuracy lead **survives the frontier** once parsimony is a hard constraint.

## 6. What already exists vs what is new

### Already measured (reused as-is, identical folds)
- Home-turf size sweep power for TabPFN, CatBoost, LightGBM, XGBoost: `scripts/eval/insurance_benchmark_v1/home_turf_sweep_results.csv` (§13 of the analysis doc, committed in `63d43ee`). Reused without re-running — the new run uses the same splits.
- v1 benchmark: `scripts/eval/insurance_benchmark_v1/results_per_split.csv` (context only; its folds differ from the sweep's).

### The gap (the new work)
1. **The D1/D2 combined frontier-run script** — one script, one pass per dataset (fit → predict log loss → count params, for every family):
   - **D1 (Option B):** re-run LogisticGLM/LR, TweedieGLM, PoissonGLM + RandomForest on the three starting datasets, log loss, 5 folds, matching the home-turf sweep's splits. The earlier "no re-runs needed" claim was wrong: v1 folds ≠ sweep folds, and only TabPFN+CAT probabilities were rescored, so fast-family power was not transferable. GLMs/RF are cheap even at 163K rows.
   - **D2 (Option A):** in the same pass, re-fit the GBDTs at recorded defaults purely to count parameters; count params for every family.
2. **Frontier plot + Pareto-efficient set table with ± SE** (D3), one independent frontier per dataset.

The sweep's existing TabPFN/CAT/LGBM/XGB log loss is reused as-is (identical folds) — only GLM/LR/RF power + param counting is new compute.

## 7. Deliverables and acceptance criteria

1. **Frontier-run script** (the D1/D2 combined pass) with dual output per family: power (mean ± SE log loss over 5 folds) for GLM/LR/RF, and `n_params` for all families — counting rule recorded (reproducible, documented).
2. **Frontier table** per dataset: `method | log loss (mean ± SE) | # params | on-frontier (yes/no)`, dominance decided under D3's beyond-SE rule.
3. **Frontier plot**: x = log(# params), y = log loss, Pareto points highlighted, SE error bars included.
4. **Narrative per dataset**: which models are on the frontier, which are dominated.
5. **v1 is classification-only** (D4): no regression/severity frontier in this pass; Phase 2 adds an RMSE / Poisson-deviance axis.
6. **Results documented** as an addendum to `tabpfn_vs_gbdt_baselines_finetuning.md` (§14) + registry row updated, per repo reporting conventions.

## 8. Open items (settled decisions are recorded in §5, not repeated here)

- **Dataset extension priority beyond `norauto`** (D5): which dataset comes after `norauto`, and on what cadence. The full v1 suite (`ausprivauto0405`, `bemtl16`) is the natural candidate but is not scheduled.
- **TabPFN exact parameter count** (non-decision, recorded): constant per dataset, never changes frontier membership; confirm the exact hosted-model figure from PriorLabs/TabPFN docs at implementation time, not before.
