# Row curve, stage 1 — the actuarial baselines at 1k / 2k / 5k rows

> **Status:** current — analysis, 2026-11-21 (#697). Baselines only; no TabPFN, no spend.

**Question:** the adoption rule's first clause is "use default TabPFN when training rows are ≤ ~5K
(won 8/9 size-sweep cells)". That says where TabPFN won; it does not say where a GLM or a GBDT
reaches parity. This is the baseline half of that curve.

## Method

```bash
python scripts/run_fair_test.py --methods E_glm,F_catboost,M_intercept \
    --device cpu --train-rows <1000|2000|5000> --out-root results
```

Four targets, five folds, three seeds (15 observations per cell), `M_intercept` as the null model.
Metric is the target's own verdict metric: Poisson deviance for the frequency targets, RMSE for
French severity, weighted RMSE for Spanish severity.

**MDE** is the 80%-power minimum detectable effect at α=0.05 from the cell's own fold/seed SD:
`(t_0.975 + t_0.80) × SD / √n`. "Resolvable" means the gap between the best and the runner-up mean
exceeds that MDE.

## Results

| target | budget | metric | best | mean | runner-up | Δ | MDE | resolvable? |
|---|---:|---|---|---:|---|---:|---:|---|
| `freMTPL2freq` | 1000 | poisson_deviance | **M_intercept** | 3289.7344 | F_catboost 4339.0567 | 1049.3223 | 107.8453 | yes |
| `freMTPL2freq` | 2000 | poisson_deviance | **M_intercept** | 3281.2875 | F_catboost 3714.4027 | 433.1152 | 99.8134 | yes |
| `freMTPL2freq` | 5000 | poisson_deviance | **M_intercept** | 3279.8541 | F_catboost 3323.3461 | 43.4920 | 99.5176 | **no** |
| `freMTPL2sev` | 1000 | rmse | **M_intercept** | 1.1307 | E_glm 1.1474 | 0.0167 | 0.0125 | yes |
| `freMTPL2sev` | 2000 | rmse | **M_intercept** | 1.1302 | E_glm 1.1332 | 0.0030 | 0.0124 | **no** |
| `freMTPL2sev` | 5000 | rmse | **E_glm** | 1.1258 | F_catboost 1.1291 | 0.0034 | 0.0119 | **no** |
| `spanish_motor_freq` | 1000 | poisson_deviance | **M_intercept** | 10188.5267 | E_glm 10579.8097 | 391.2831 | 275.7286 | yes |
| `spanish_motor_freq` | 2000 | poisson_deviance | **E_glm** | 9467.2980 | M_intercept 10177.5199 | 710.2219 | 335.2570 | yes |
| `spanish_motor_freq` | 5000 | poisson_deviance | **E_glm** | 9072.0082 | F_catboost 9548.7642 | 476.7560 | 179.5142 | yes |
| `spanish_motor_severity` | 1000 | weighted_rmse | **E_glm** | 0.6030 | F_catboost 0.6340 | 0.0310 | 0.0199 | yes |
| `spanish_motor_severity` | 2000 | weighted_rmse | **E_glm** | 0.5990 | F_catboost 0.6101 | 0.0111 | 0.0201 | **no** |
| `spanish_motor_severity` | 4760 | weighted_rmse | **F_catboost** | 0.5807 | E_glm 0.5932 | 0.0124 | 0.0196 | **no** |

## Reading

1. **Seven cells resolve; five do not.** The five that fail are `freMTPL2freq` at 5,000 (Δ 43
   against an MDE of 100) and the French/RMSE cells at 2,000 and 5,000 (Δ 0.003 against 0.012) plus
   the Spanish severity cells at 2,000 and 4,760 (Δ 0.011 and 0.012 against 0.020). Those five are
   **Inconclusive**, not "no difference". The MDE is 3–13% of the mean on the count targets at 1,000
   rows, so the 2% floors #629 warned about are unreachable at that budget.
2. **French frequency has no extractable signal at these budgets.** `M_intercept` — the null model —
   has the lowest mean at 1,000, 2,000 and 5,000 rows, and the fitted GLM is *worse than the null*
   at 1,000 (per-row deviance 0.663 against 0.329). A singular-matrix warning is logged at the two
   smaller budgets, consistent with a ten-parameter fit on ~50 claim events.
3. **Spanish frequency is the opposite once there is enough data.** The null leads at 1,000 (10,188),
   `E_glm` takes over at 2,000 (9,467 against 10,178) and 5,000 (9,072 against 9,549 for CatBoost) —
   and the 5,000 cell is one of the few whose margin clears its MDE.
4. **Severity moves little with budget**, as expected: those targets train on claim rows only, so the
   budget changes less. Only the 1,000-row Spanish severity gap clears its MDE.
5. **One budget could not be met.** `spanish_motor_severity` has 4,760 training rows available, so
   its "5,000" cell is 4,760 — recorded as such rather than rounded up.

## What this means for the adoption rule

The rule's small-data clause is about **where TabPFN wins**, and stage 1 says nothing about TabPFN.
What it does show is that "small data" is not one regime: on French frequency a null model is hard to
beat at 5,000 rows, while on Spanish frequency a GLM extracts signal no tree finds. Stage 2 — a
matched TabPFN capture — is worth its spend only where a gap is plausibly live, and on this evidence
that is Spanish frequency, not French.

## Record

- Twelve run directories committed as `results/<run id>/capture.json`.
- Per-record predictions are **not** committed: the twelve capture manifests are 317 KB, the payload
  is 113 MB. Regenerate with the command above ($0, CPU, ~14 minutes for all three budgets). The
  payload-size question is #584, and this note does not pre-empt it.
- `scripts/analyses/row_curve_stage1.csv` — every cell with its SD, n and MDE.
