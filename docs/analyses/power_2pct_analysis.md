# Power for a 2% relative effect: does 5 folds × 3 model seeds suffice?

> **Status:** task analysis, 2026-11-08, for #499. **Question:** how many rows, folds and seeds are
> needed to detect a 2% relative improvement with a paired 95% CI on each target? **Answer: yes for
> ClaimNb and spanish_motor_severity; conditional for VehValue.** No paid compute was used.

## Bottom line

Canonical **5 folds × 3 model seeds is sufficient** for freMTPL2 `ClaimNb` (Poisson deviance) and
`spanish_motor_severity` (RMSE) under every variance proxy measured here. For `ausprivauto0405`
`VehValue` (RMSE) it is sufficient if the fine-tuned-vs-raw fold-level standard deviation is at or
below the competent-model proxy (0.0014); it is **underpowered** if the true fold-level SD is as
large as the most dissimilar-model proxy (0.0136). The three model seeds do not repair that: seeds
reduce training noise, not fold-sampling variance.

The binding unit is the **fold**, not the row. Treating 5 folds × 3 seeds as 15 independent samples
would overstate power by roughly √3 and is rejected.

## Method

- Canonical `KFold(5, shuffle=True, random_state=42)` on each target under the #507 treatment.
- Cheap CPU baselines only: training mean, OLS / Poisson GLM, and two histogram gradient-boosting
  fits. No TabPFN, no GPU, no hosted calls.
- For every pair of arms, the per-fold metric difference and its standard deviation across the five
  folds. The fold is the replicate; the test statistic is a paired t over five fold differences
  (df = 4, two-sided α = 0.05).
- The 2% effect is relative to the competent baseline (`hgb0`), so the target delta is 0.02 × its
  mean fold metric.
- The fine-tuned-vs-raw variance is **not measured**; it is proxied by the closest and the most
  dissimilar cheap-model pairs. The closest pair bounds the optimistic case, the most dissimilar
  pair the pessimistic one.
- The minimum detectable effect (MDE) is the non-central-t solution at 80% power.

## Results

| target | metric | n | test rows/fold | reference | 2% delta | tight pair SD | power @2% | MDE 80% | worst pair SD | power @2% | MDE 80% |
|---|---|---|---|---|---|---|---|---|---|---|---|
| freMTPL2 `ClaimNb` | Poisson deviance | 678,013 | 135,602 | 0.3069 | 0.0061 | 0.0003 | 1.000 | 0.0005 | 0.0007 | 1.000 | 0.0013 |
| spanish_motor_severity | RMSE | 53,502 | 10,700 | 1.8339 | 0.0367 | 0.0020 | 1.000 | 0.0033 | 0.0085 | 1.000 | 0.0142 |
| ausprivauto0405 `VehValue` | RMSE | 67,856 | 13,571 | 0.7223 | 0.0144 | 0.0014 | 1.000 | 0.0023 | 0.0136 | **0.443** | 0.0228 |

The variance ceiling for 5 folds at 80% power is `delta / 3.717`: **0.0037** for ClaimNb,
**0.0221** for severity, **0.0087** for VehValue. A larger fold-level SD than that needs more folds.

If VehValue's true SD sits at the pessimistic proxy (0.0136), reaching 80% power needs about
**12 folds**, not 5. If it sits near the competent-model proxy, 5 is ample.

## Recommendation

1. **Keep canonical 5 folds × 3 model seeds** for the main design. It clears 2% comfortably for
   ClaimNb and severity.
2. **Pre-register a VehValue power check.** Before the verdict, compute the observed fold-level SD
   of the paired FT-vs-raw difference. If it exceeds 0.0087, either raise the fold count (towards 12)
   or report VehValue as a per-target result without letting it carry the pooled verdict.
3. **Never treat 15 runs as n = 15.** The 5 fold differences are the sample; the 3 seeds are
   repeated measures inside a fold. Report the paired CI at the fold level, with the seed
   variability shown separately.
4. If the observed fold SD is dominated by training stochasticity rather than fold composition,
   the 3-seed average will shrink it and the VehValue risk falls. Check that before adding folds.

## What this does not prove

- The proxy variance is not the fine-tuned-vs-raw variance. It is a bound from cheap models; the
  fine-tuner may be more or less variable.
- Only one fold seed (the canonical 42) was examined. Fold composition is fixed by the registry.
- A 2% relative change in Poisson deviance and a 2% relative change in RMSE are not equally hard;
  the table reports each on its own metric, and the verdict pools relative improvements.
- No TabPFN fit was run. This is a design calculation, not a measurement of the effect.

## Sources

- `data/raw/freMTPL2freq.csv`, `data/raw/spanish_motor_severity.csv`,
  `data/raw/ausprivauto0405.csv` under the #507 treatments.
- Probe scripts and raw per-fold outputs: `power2pct/probe.py`, `power_out_0/1/2.json` in the
  session's temporary directory (not repository files).
