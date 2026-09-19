# Master Report Digest — the addendum arc (§4 → §14.15)

Companion to `docs/KNOWLEDGE-PATH.md` Stage 4.5. The master report (`docs/analyses/tabpfn_vs_gbdt_baselines_finetuning.md`) is an *evolution*, not a static study: nine addenda, each answering one question, several reversing or qualifying prior verdicts. This digest gives one paragraph per addendum — question, result, verdict change, key numbers. Read it alongside the report, or instead of it when you need the story fast.

**The one-line story:** v1 looked like a loss → §11 showed the metric was blind → §12 separated artifacts from real limits → §13 killed the size story → §14 built the frontier → §14.11 retracted a verdict and found TabPFN AUC #1 on 6/6 → §14.13 confirmed it against tuned baselines → §14.14 showed the frequency verdict was a framing artifact → §14.15 tested the severity verdict against three insurance-native metrics and it held.

---

## §4 v1 — the baseline that started it (2026-08-01)

9 tasks (7 datasets, 2 dual targets), all-default configs, scored on `1 − ROC AUC` / RMSE. Verdict: **2W / 1T / 5L** — wins on the two smallest classification tasks (bemtl16, coil2000), decisive losses on severity (vehvalue +67.2%, bemtl97_amount +48.3%). Compute cost objection: TabPFN 5–50× slower train, 100–1000×+ inference. **This verdict is the one the whole report exists to correct.**

## §11 Imbalance pilot & calibration re-score (08-02)

Question: *is the loss an imbalance-handling deficit?* Tested `balance_probabilities=True` — and found the metric was blind to it: ROC AUC is rank-invariant to monotone transforms, so 1−AUC was identical to ≤1e-16 with or without the lever. Re-scored on **log loss + Brier** ("insurance-native metrics — what an insurer pays on"): the lever **actively hurts** calibration (coil2000 log loss 0.4716 vs 0.2008 default; mean predicted probability inflated 0.047 → 0.327 on a 6% base rate). Headline qualified, not reversed. **New concept: 1−AUC metric blindness.**

## §12 Why v1 looked lopsided (08-02, corrected 08-04)

Question: *which v1 losses are real?* Separated genuine limits (regression gap, inference cost) from setup artifacts (scale, metric, tuning asymmetry — TabPFN ran bare while GBDTs ship tuned defaults). **Ruled out for good:** CPU, imbalance handling, fine-tuning. Correction embedded: the "~1K context ceiling" framing was superseded — hosted v3 accepts 1M rows; the size-dependent pattern is empirical and mechanism-independent. **Do not re-chase: CPU, imbalance, fine-tuning.**

## §13 Home-turf size sweep (08-02)

Question: *is TabPFN just a small-data model?* 3 datasets × 1K/5K/full × 5 folds on log loss, defaults. Result: **8/9 wins** — only loss bemtl97@full at 163K rows by 0.0010 (fold noise). The "context ceiling kills TabPFN" story died for classification log loss. Real cost is compute: 3,045 s cold fit at 163K rows. Closed: the `n_estimators=8` config-lite arm was bit-identical to the server default on all 40 cells. **Do not re-chase: the ensemble-size dimension.**

## §14 Frontier benchmark — efficiency, not just power (08-02)

Question: *where does TabPFN sit on quality-per-parameter?* Pareto frontiers per dataset: log loss vs parameter count, under the **D3 beyond-SE rule** (A dominated iff some B with strictly fewer params has `mean_B + SE_B < mean_A − SE_A`). TabPFN = fixed **10M-param top-right anchor** (never parsimonious, often powerful: power-best 2/3 initial datasets). **Most robust result of the entire report: the 11–86-param GLM family is never dominated on any dataset.** RF at defaults is a frontier failure — do not re-chase.

## §14.6–§14.10 The extensions (08-03 → 08-04)

- **§14.6 norauto (184K rows):** LGBM takes power at scale; TabPFN survives the frontier only on a beyond-SE tie — the size ceiling transfers to the frontier axis.
- **§14.7 ausprivauto0405 + bemtl16:** first outright TabPFN domination (ausprivauto0405 — *later retracted*) and first real beyond-SE win (bemtl16).
- **§14.8 Regression Phase 2 (D4):** TabPFN wins power at small N only (beyond-SE at 22K rows, tie at 68K), dominated at scale (163K, 678K). v1's vehvalue +67.2% shown to be a harness-specific artifact. Zero-inflation trap identified (poissonglm catastrophic on log1p amount).
- **§14.9 Spanish motor frequency (real portfolio):** LGBM dominates beyond SE; TabPFN off-frontier a 4th time at scale; GLMs sit at the null-deviance floor — thin signal only trees extract. History-variable leak caught pre-run.
- **§14.10 Gap-closing:** Spanish lapse 5-fold re-run — TabPFN 0.7553 > LGBM 0.7500, all 5 folds, the 2-fold caveat settled. eudirectlapse still Linear. Spanish severity: TabPFN mid-pack, off-frontier.

## §14.11 AUC/Brier re-score — the retraction (08-06)

Question: *does the ranking edge survive proper metrics on the canonical protocol?* Emitted per-fold AUC + Brier for the first time. Result: **TabPFN highest mean AUC of 9 methods on all 6 classification datasets** (deltas +0.006 to +0.033 over best GLM; five ≥2.5 SE); Brier never loses significantly; log loss better-or-tied vs best GLM. **Retraction:** ausprivauto0405 "DOMINATED" reversed — log-loss gap +0.0008 ≈ 1.5 SE, calibration tie, and TabPFN holds the suite-best AUC (0.6622). New concepts: the **regime rule** (GLM gap ≥ ~2.5% or ΔAUC ≥ ~0.05 ⇒ TabPFN-win regime; ≤ ~2% ⇒ GLM-captured), imbalance artifact (log loss is majority-bulk dominated), unpaired z convention. Verdict: "calibration at worst a tie, ranking best-in-suite."

## §14.12 Ranking-robustness (08-06)

Question: *does the edge survive the metrics where triage actually cuts?* PR AUC + top-decile lift + paired tests + seed variation. Results: **PR AUC rank #1 6/6 (paired-significant 5/6)**; every §14.11 AUC edge real (paired p ≤ 0.0063); seed-stable 9/9 (seeds 7/42/123). **Honest weak spot: top-decile lift** — rank #1 on only 4/6, paired-significant 2/6. Lesson in statistical power: norauto PR-AUC unpaired z=1.26 (ns) vs paired t=9.02 (p=0.0008) — same folds make comparisons paired.

## §14.13 Finality test (08-07)

Question: *does the last standing threat — tuned classical baselines — dethrone it?* Five tuned/feature-engineered baselines (LR tuned, GLM-engineered with degree-2 interactions, tuned LGBM/CatBoost/RF — all tuned by ROC AUC) on the exact canonical folds. Result: **TabPFN stays #1 of 14 on AUC and PR-AUC on all 6 datasets**; two small ~1e-4 calibration exceptions. Honesty notes: tuned GBDTs *regressed* vs their own shipped defaults on 5/6 (norauto: lgbm_tuned 0.640 vs lgbm 0.697) — the credible engineered baseline was glm_eng, and it still lost every ranking metric. TabFM closed by assessment (OOM-killed at 8GB, non-commercial weights), not by measurement. Fold-identity check: plain LR reproduces canonical rows exactly.

## §14.14 Count/frequency reframed as classification (08-07, issue #67)

Question: *can the weakest axis be sidestepped by reframing the target?* Spanish motor `N_claims_year` → binary claim/no-claim (11.1% pos) and ordinal 0/1/2+. Result: **rank #1 on every metric, but several margins are within noise** (binary PR-AUC p=0.12, ordinal Brier p=0.88 — the report's own §14.14.6 honest weak spot); **significant margins are seed-stable** (binary AUC 0.7170, +0.0080 vs LGBM, p=0.0010; ordinal one-vs-rest AUC 0.7167, +0.0111, p=0.0085). §14.9 contrast: the same rows scored by Poisson deviance had TabPFN +10.8% *behind* LGBM — **the count axis was the loss; classification is the win.** Caveats: single dataset, GLMs collapse on the binary task (constant prediction, AUC exactly 0.5000), ordinal PR-AUC is NaN by design (lift10 on P(≥1) is the substitute).

## §14.15 Insurance-native alternative metrics (08-27, issue #123)

Question: *does the severity verdict flip under Gamma/Tweedie deviance or MAE?* Re-scored all 6 regression datasets from #122's persisted predictions. Result: **stable — the one apparent flip is an artifact.** `spanish_motor_severity` (RMSE rank 6/8, §14.10) jumps to **MAE rank 1/8** (paired-significant vs best GBDT, p=1.1e-05) — but 117.45 is *worse* than predicting €0 for every policy (117.24). Same trap on both count targets: at ~89–95% zero mass the MAE-minimizing constant (the median) *is* zero, so every method loses to a constant and the ranking is meaningless. Where zero mass is absent the result holds and strengthens: `ausautoBI8999` (0% zeros) and `ausprivauto0405_vehvalue` (0.1%) are TabPFN rank 1 on all four metrics, paired-significant throughout on the former (p=0.0094/0.0036/0.0012). `bemtl97_amount` stays put (LGBM #1 on all three) and clears its own baseline. On `spanish_motor_severity` itself, TabPFN's own Gamma/Tweedie verdict is **rank 4/8, improved from RMSE's 6/8 but not flipped** — the uncorrupted GLM family (0% floor-clip) legitimately outranks it (best=ols, p=0.0009/0.0009). **Second artifact: the floor-clip blowup** — GBDT Gamma/Tweedie means on `spanish_motor_severity` reach 1e8–1e11, driven by near-zero predictions on real claims (xgb 8.5% of predictions floor-clipped vs tabpfn 0.065%), which is also why those deltas aren't significant (p=0.37–0.42). Net: §14.8's small-N regression picture confirmed on three metrics; no verdict reverses.

## §14.16 Fine-tuning pilot — negligible gain extends to the GPU regime (09-12)

Question: *does in-domain fine-tuning beat raw TabPFN when it is actually trained, on a GPU,
rather than in the earlier small-step CPU trials?*

**Scope note, because it is easy to overstate.** §12's "do not re-chase: fine-tuning" was
about which setup artifacts explain **v1's losses**, and the fine-tuning evidence behind it
was the CPU small-step work (§2.3, §5.2 — 1-3 steps, context 64/128, coil2000 only). This
run does **not** re-test that ruling. It extends the question to a regime the earlier work
could not reach: GPU, the shipped trainer, four datasets. Treat the two as separate.

Result: **no reliable gain, now at GPU scale.** Four insurance classification datasets, each
fine-tuned on its own training split (TabPFN 8.5.0, `v3_default`). `A_raw` and `B_in_domain`
ran on the **same device in the same run at the same seed**, so this is like-for-like:

| dataset | A_raw | B_in_domain | delta |
| --- | --- | --- | --- |
| coil2000 | 0.7675 | **0.7690** | +0.0014 |
| eudirectlapse | 0.5881 | **0.5976** | +0.0095 |
| spanish_motor_lapse | 0.7233 | **0.7272** | +0.0039 |
| uslapseagent | **0.9363** | 0.9355 | −0.0008 |

**Two design facts that must travel with those numbers.** First, this produced **four separate
fine-tuned models — one per dataset — and none were saved**; there is no single fine-tuned TabPFN
evaluated across datasets. Second, each model was **fine-tuned on the same dataset it was then
tested on** (a held-out split, so there is no leakage, but in-domain by construction). That is
the weakest form of the claim and the one reviewers flag first: it can say a small in-domain
fine-tune changed nothing measurable, and **cannot** say anything about a fine-tuned model that
transfers to an unseen portfolio. The arms that would test that — C/D, one model fine-tuned on
other datasets and evaluated on a target it never saw — have never been run.

Three wins, one loss, every delta ≤0.010 — inside the split-to-split movement the pilot
report's §6.4 already flags, at a single seed with no paired testing. Fine-tuning also costs
~3x the compute (117 s vs 41 s of GPU across the four datasets). Meanwhile raw TabPFN's
margin over the *best actuarial baseline* is an order of magnitude larger: **+0.068** on
coil2000 against **+0.001** from fine-tuning.

**Scope limits that bound this claim:** 3 fine-tune passes (`max_finetune_steps=3` mapped to
the trainer's `epochs`), the shipped trainer's default subsampling, one seed, four
classification datasets, ROC AUC. It shows that a *small* GPU fine-tune buys nothing
measurable — not that no fine-tuning configuration could ever help. Anyone proposing a
larger or differently-tuned run should say which of those limits they are testing.

**Verdict change: none.** This corroborates the earlier "negligible" finding in a stronger
regime, and leaves the standing adoption rule untouched: the value is in *using* the
foundation model, not in adapting it.

Method note worth carrying: arm B had never completed a run anywhere and was believed to be
memory-bound. That diagnosis was wrong — it failed in 2-5 s with 50.8 GB of VRAM free, on a
call-sequence defect — and the fix was to use the trainer TabPFN already ships rather than
driving the model by hand. Details in `FINE_TUNING_PILOT_RESULTS.md` §5b-§5c.

## §15 Version-drift re-test policy (08-04, docs-only)

The verdicts are **version-stamped**: `model_path="v3_default"`, tabpfn-client 0.3.3. Triggers: client upgrade, new model_path, any environment bump. Procedure: record versions → rerun same commands/folds/metrics/D3 rule → diff the 12 committed frontier CSVs → append a §14.x addendum → update the adoption rule *only if the pattern changes*. Sweep-reuse caveat: the frontier reuses home-turf sweep rows on 3 datasets — refresh the sweep first or the frontier won't see new model behavior.

---

## The verdict chain, one line per era

| Era | Verdict |
|---|---|
| §4 v1 | TabPFN loses aggregate, decisive on severity |
| §11–§12 | Loss partly a metric artifact; calibration story opens |
| §13 | Size story dead for classification log loss (8/9) |
| §14 | Frontier: GLM never dominated; TabPFN top-right anchor |
| §14.11 | **AUC #1 on 6/6; ausprivauto0405 retraction** |
| §14.12–§14.13 | Ranking edge survives PR AUC, paired tests, seeds, tuned baselines (#1 of 14) |
| §14.14 | Frequency verdict was a framing artifact — reframe wins |
| §14.15 | Severity verdict stable under Gamma/Tweedie/MAE; the one apparent flip fails a trivial baseline |
| §14.16 | GPU fine-tuning measured: no reliable gain for a 3-pass fine-tune (≤0.010, one negative) — extends, does not re-test, §12's CPU-scoped ruling |
| Standing | Adopt for risk-ranking (underwriting triage, propensity); keep GLM for pricing/coefficient stories; regression stays GBDT territory except clean positive-severity targets at small N (§14.8, confirmed §14.15) |
