# Frequency/severity power — what the new targets can resolve, and what must be measured

> **Status:** proposed — power analysis for #552, 2026-11-11. **No run, no spend.** The one measured
> figure is #499's ClaimNb result, cited from the superseded pre-registration, not re-derived here.
> **Question:** at the real sample sizes, what relative improvement can each frequency and severity
> target resolve at 80% power, and which figures are bounds rather than measurements?

## Answer in one paragraph

**The 2% floor is supported for French frequency by a measurement, and for both severity targets by a
conservative bound; Spanish frequency is the one figure that needs a probe.** French severity's bound
is 1.95% and Spanish severity's 1.83% (claim-weighted) — inside 2%, but only just, and both bounds
ignore the pairing benefit that the actual design has. French frequency's 0.48% was measured in #499.
Spanish frequency has no defensible number until the raw arm is run on its five folds. A pre-spend
resolution gate does that for all four targets, and the severity floor is registered from its result,
not from these bounds.

## Inputs

| Target | Unit | n | What the metric is computed on | SD of the metric input |
|---|---|---:|---|---:|
| French frequency (`ClaimNb`) | policy | 678,013 | Poisson deviance, 10,000-row test cap | measured in #499: MDE 0.0048 |
| Spanish frequency (`N_claims_year`) | policy | 53,502 | Poisson deviance, 10,000-row test cap | not measured |
| French severity (`ClaimAmount`) | claim | 26,444 (24,944 policies) | RMSE of `log(amount)` | 1.13 |
| Spanish severity (`Cost/N`) | claim-equivalent, weighted by N | 11,167 (5,950 policies) | RMSE of `log(Cost/N)`, policy-clustered | 0.691 weighted / 0.538 unweighted |

The French severity file is new (`freMTPL2sev.csv`). The Spanish severity unit is the claiming policy;
each contributes `N_claims_year` claim-equivalents at its mean `Cost_claims_year / N_claims_year`.
All 26,444 French claims join to `freMTPL2freq` on `IDpol`.

## Method

For target `t`, fold `f` and model seed `s`, the test computes the relative improvement

```
r_{t,f,s} = (M(A_raw) - M(B_ft30)) / M(A_raw)
```

and averages the three seeds. The per-target interval is a paired t over the five fold values
(4 df). The minimum detectable relative effect at 80% power is

```
MDE = 2.8016 * SD_fold(r) / sqrt(5)
```

where `2.8016 = z(0.975) + z(0.80)`, the same constant D13 used. `SD_fold(r)` — the spread of the
relative improvement across folds — is **not** the SD of the target. The bound below substitutes the
target's own SD divided by `sqrt(n)`. That ignores both the fold structure's correlation and the
pairing between the two Arms, so it is **conservative**: the real MDE is at or below it.

| Target | Bound (conservative) | Is it inside 2%? |
|---|---:|---|
| French frequency | 0.48% (measured, #499) | yes, with room |
| Spanish frequency | not derived | unknown — needs the gate |
| French severity | 1.95% | yes, at the edge |
| Spanish severity | 1.83% weighted / 1.4% unweighted | yes, at the edge |

The Spanish severity interval must be **clustered by policy**; treating 11,167 claim-equivalents as
independent rows would understate the variance by the intra-policy correlation.

## The resolution gate (pre-spend)

Before the fair test, run `A_raw` — in-context, no fine-tuning — on the five folds of all four
targets. That is twenty in-context fits; on the measured card they are seconds each, and the launch
overhead dominates. From each target's five fold-level metric values, take `SD_fold(metric)`. Two
Arms on the same rows have positively correlated errors (same context, and the fine-tune starts from
the raw model), so this SD bounds the paired difference SD from above. Then

```
MDE_gate = 2.8016 * SD_fold(metric_A_raw) / sqrt(5)
```

If `MDE_gate` exceeds the registered floor for a target, the fair test **stops for that target** (or
the floor is raised in a dated amendment before the fair test launches). This is D13's resolution
gate applied to the new targets, and it is the only place a spend decision is made before the matrix.

Cost of the gate: four targets × five folds of in-context fits. On the measured RTX PRO 4000
(41.7 s for a 10,000-row 30-epoch fine-tune), in-context fits are far cheaper; the launch overhead
dominates at roughly $0.02–$0.05. It is released separately, like the benchmark fit was.

## What would change the answer

- A paired difference SD much larger than the bound's assumption would move the severity MDE above
  2%; the gate measures it, the bound does not.
- The Spanish frequency target has no number here. Its MDE could be better or worse than the French
  one; the two are different portfolios, targets and exposure treatments.
- More folds would shrink the fold-level SE, but the pre-registration fixes five and a larger fold
  count is a new registration.
