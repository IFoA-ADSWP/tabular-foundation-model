# Plan — the exposure-aware rate target (#742)

**Status:** Current — implementation in progress, 2026-11-23.
**Origin:** protocol ticket #742, from candidate #719, map #716.
**Bar:** French frequency must fall from a 15.5% offset-GLM gap to **≤ 7.75%**.

## The design decision that matters

Predicting a rate (`ClaimNb / Exposure`) and scoring it directly would change the metric as well
as the target — `METRIC_REGISTRY.md:45` says a rate-scale variant is "a different name and
version" of `poisson_deviance`, and two arms scored on two metrics are not comparable.

So: **the model predicts a rate, and scoring multiplies back by exposure before computing
`poisson_deviance` on counts.** One metric, version 1, unchanged; only the target and the
transform differ. That is what makes "does the rate target close the gap?" a like-for-like
question rather than a comparison of two estimands.

## What changes

| Site | Change |
|---|---|
| `src/freq_sev_data.py` — `TargetSpec` | one field naming the exposure column, empty for every existing target |
| `src/freq_sev_data.py` — `TARGETS` | `frequency_french_rate`: same file, same `ClaimNb`, same drop, plus the exposure column |
| `src/freq_sev_data.py` — `load_target` | a branch dividing the target by exposure and carrying the exposure vector on `LoadedTarget` |
| `src/fair_test_runner.py` | multiply the held-out predictions back by exposure before scoring; record the transform in `meta.json` (the field already exists and currently records `native`/`log`) |

## Constraints carried from the protocol

- `v3_default` pinned by checkpoint path; no era mixing.
- 5 policy-grouped folds (`random_state=42`) × 3 seeds; identical test rows across arms.
- French only. Spanish waits on #737; severity is out of scope.

## Verification before any spend

A **5,000-row CPU smoke run** first. Below the CPU cap, so it needs no override, and it proves
the transform, the multiply-back and the metric path before a single rented minute. A GPU run
that fails on a shape error is $0.16 spent on a stack trace.

## Out of scope

- The Spanish half (#737 blocks it).
- Any weight-based variant: `sample_weight = Exposure` reweights the count target and does not
  fix the elasticity at 1 (`baseline_method_specification.md` §3). That is a different model
  and would need its own bar.
