# Pre-registration — the actuarial baseline (2026-11)

> **Status:** proposed 2026-11-13 — no run has been made under this document. It is released for
> sign-off, not executed.
> **Ticket:** #597. **Plan:** `docs/plans/597-actuarial-baseline.md`.
> **Specification:** `docs/experiments/fair-test-freq-sev/baseline_method_specification.md` (the configuration, sourced).
> **Relationship to the fair test:** independent of
> `REGRESSOR_FINETUNING_PREREGISTRATION_FREQ_SEV_2026-11.md`, and deliberately so. That document
> asks whether fine-tuning a TabPFN beats using it untouched. This one asks whether either beats a
> GLM or a CatBoost model built the way an actuary would build one. Neither verdict can be derived
> from the other, and neither amends the other.

## The question

On the four targets of the frequency/severity fair test, does fine-tuned TabPFN (`B_ft30`) beat the
**better** of two actuarial baselines — a GLM (`E_glm`) and CatBoost (`F_catboost`) — on the fair
test's own metric?

## Why the better of two

If TabPFN beats a GLM but loses to CatBoost, it is not the best available choice, and a verdict
against the weaker baseline would be true and useless. The claim on offer is *TabPFN is the better
model*, so the bar is the stronger competitor.

## Design

| Field | Value |
|---|---|
| Targets | `frequency_french`, `frequency_spanish`, `severity_french`, `severity_spanish` |
| Methods | `B_ft30` (contender), `A_raw` (reported alongside), `E_glm`, `F_catboost` |
| Folds | five policy-grouped folds, `random_state=42` — the fair test's, unchanged |
| Seeds | three per fold, uniformly |
| Test rows | the registered capture's `test_index`, unchanged and hash-verified |
| Rows trained | **full fold pool** (primary); the fair test's **10,000 rows** (sensitivity) |
| Frequency metric | `src/metrics.poisson_deviance` — the total, not the mean |
| Severity metric | weighted RMSE on `log(amount)`, as registered |
| Anchor | intercept-only model per target |
| Spend | none; CPU on data already in `data/raw` |

### The statistic

```
r_{t,f} = ( M_{t,f}(baseline) − M_{t,f}(B_ft30) ) / M_{t,f}(baseline)
```

averaged over the three seeds inside each fold, with the target's interval a paired t over five folds
(4 df) — the fair test's shape. A **positive** `r` means TabPFN has the lower metric, so the
statistic names the contender rather than the control, and `Go` keeps its meaning: an improvement,
not a gap.

### The decision rule

Unchanged from the fair test, applied per target:

```
Go            CI excludes zero AND the point estimate is at or above the target's floor
No-go         CI upper bound is below the floor — a meaningful gain is excluded
Inconclusive  CI covers both zero and the floor
```

**Floors carry over per target**: `frequency_french` 2%, `frequency_spanish` 4%, both severity
targets 2%. They were sized from the fair test's measured fold-level variance, and keeping them is
what makes a baseline verdict readable on the same scale as the fine-tuning result for that target.

### The three readings

1. **`Go` against the better baseline** — TabPFN is the better model on that target, and the
   programme's claim survives contact with practice.
2. **`No-go`** — the baseline is better by at least the floor. This is a real result and must be
   published as one: the fine-tuning gain is then a gain inside a losing class.
3. **`Inconclusive`** — the interval covers zero and the floor. Reported as such, with the MDE, and
   not narrated.

Per-target verdicts only. The frequency and severity task means are reported descriptively; no
pooled or task-level verdict is claimed, because the two-portfolio bootstrap was registered for a
different claim.

## What is fixed, and what may move

**Fixed — changing any of these is an amendment with a date:**

1. The targets, folds, seeds, test rows and metrics above.
2. The family and link per target: Poisson-log for frequency; Gaussian identity on `log(amount)` for
   severity. The Gamma family is **not** run (it cannot be scored on the registered metric).
3. The GLM encoding — the case study's GLM1 bins, merges, reference levels and `Area` as continuous.
4. Hyperparameters of record: `alpha=0`, `max_iter=500`; CatBoost `iterations=1000`, `depth=6`,
   `learning_rate=0.03`, `l2_leaf_reg=3.0`, shipped defaults pinned explicitly.
5. No capping of `ClaimNb` or `Exposure`. The captures' ground truth is uncapped; capping would give
   the baseline a different target from the one TabPFN was scored on.
6. The row budgets: full fold pool primary, 10,000-row sensitivity.
7. The statistic, the floors and the decision rule.

**Free — engineering, recorded in the run manifest:** the solver and its tolerances, whether exposure
enters as rate-plus-weight or through another exact realisation, column order and dtype handling,
CatBoost's threading and file-writing flags.

## What this cannot settle

- It compares TabPFN against **these two specifications**, not against "an actuary". The GLM has no
  interactions or splines, so a GLM loss is a loss for a main-effects GLM.
- It says nothing about calibration, lift, pure premium, or the frequency × severity product.
- It does not test the exposure specification: offset is fixed, the robustness arm is a separate
  registration.
- It cannot show how a Gamma or Tweedie severity model would rank on its own deviance.
- Spanish frequency is underpowered at its 4% floor, so an Inconclusive there may reflect power
  rather than parity.

## Sign-off

Proposed 2026-11-13. The run is released only when the owner signs this document; a change to a
target, method, fold, metric, floor or row budget after that is a dated amendment, not an edit.

| Date | Change | By |
|---|---|---|
| 2026-11-13 | Filed. Scope, method set, statistic, per-target floors, row budgets and feature policy settled with the owner in #597. | agent, for owner review |
| 2026-11-13 | **Released for execution by the owner**, immediately after #608 merged: the method axis, both baselines, capture v5, the analysis tool and the one-fold timing are on `main`. No target, method, fold, seed, metric, floor or row budget changed. | owner, via session instruction |
