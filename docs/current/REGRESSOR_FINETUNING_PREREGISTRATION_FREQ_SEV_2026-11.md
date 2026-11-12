# Pre-registration — the frequency/severity fair test (2026-11)

> **Status:** proposed — pre-registration, 2026-11-11. **Authorises:** no run. **Supersedes:** the
> 2026-11-08 regressor pre-registration, whose target set did not match the project's frequency and
> severity aim. **Scores:** relative improvement per task; 2% floor. **Model:** `v3_default`, pinned
> by checkpoint path. **Cost:** provisional \$0.55; ceiling \$50. **Ticket:** #552 (this document).

This document fixes a design before the data exists for it. A launch record must name it. It does not
authorise spend. The resolution gate and the implementation preconditions are named below and are
released separately.

## What is being tested

**Claim.** Fine-tuning the TabPFN regressor improves on raw TabPFN, under matched inference context
and on identical test rows, for **claim frequency** and **claim severity**, in a French and a Spanish
portfolio.

This replaces the 2026-11-08 design. That document tested a method-level claim over three regression
targets: annual cost per policy-year labelled "severity", no Spanish frequency, and vehicle value as
a third target. None of those three is the actuarial task the project is about. The old document is
retained unchanged, marked superseded, because the record of what was filed and why it changed is
part of the design history.

## Targets

Two tasks, two portfolios. Severity is **per-claim amount**; frequency is **claims per policy**.

| Task | Portfolio | Dataset | Target | Unit | Rows | Metric |
|---|---|---|---|---|---:|---|
| Frequency | French | `freMTPL2freq` | `ClaimNb` | policy | 678,013 | Poisson deviance |
| Frequency | Spanish | `spanish_motor_freq` | `N_claims_year` | policy | 53,502 | Poisson deviance |
| Severity | French | `freMTPL2sev` joined to `freMTPL2freq` | `ClaimAmount` | claim | 26,444 claims, 24,944 policies | RMSE of `log(amount)` |
| Severity | Spanish | `spanish_motor_severity` with `spanish_motor_freq` for the count | `Cost_claims_year / N_claims_year` | claiming policy, weighted by `N` | 5,950 policies, 11,167 claim-equivalents | RMSE of `log(Cost/N)` |

**Feature treatment, fixed now.**

- French frequency: all `freMTPL2freq` columns except `IDpol` and the target; `log(Exposure)` is a
  feature, per the registry's `log_exposure` transform.
- Spanish frequency: all `spanish_motor_freq` columns except the target, `Cost_claims_year`
  (sibling target), and the documented leaks `N_claims_history` and `R_Claims_history`. No exposure
  offset: the registry treats exposure as uniform, and adding one changes the estimand.
- French severity: the claim rows carry the policy's features from `freMTPL2freq` joined on `IDpol`,
  excluding `IDpol`, `ClaimNb` (sibling frequency target) and `Exposure` (a frequency channel).
  Every amount is at least 1, so `log(amount)` is defined.
- Spanish severity: the severity view's columns except its target and `Policies_in_force` (the
  frequency channel); `N_claims_year` from the frequency view is the weight, never a feature.
- The two Spanish views are **row-aligned**: their 20 shared columns are identical row for row. A
  test asserts the alignment rather than trusting equal row counts.

**Datasets not in the design.** `ausprivauto0405` `VehValue` is not an actuarial claim task and is
removed. The `Exposure` target of `freMTPL2freq` is not used: the synthetic positive control already
gates the instrument, and the exposure diagnostic belonged to the method-level design.

## Arms

| Arm | Meaning |
|---|---|
| `A_raw` | raw TabPFN regressor, in-context, no training — the comparator |
| `B_ft30` | full-parameter fine-tune, 30 epochs — the treatment |
| `B_ft10`, `B_ft3` | the same at 10 and 3 epochs — sensitivity |

`X_log1p` is removed: it was a ClaimNb-only transform. `S_50k` is removed: no severity target has
50,000 rows to scale to, and a row-scaling arm on frequency alone would not be comparable across
targets. Both removals are design decisions made before any data, not after a result.

## Folds and seeds

- **Five folds**, `KFold(5, shuffle=True, random_state=42)`, fixed.
- **Three model seeds** inside each fold — 0, 1 and 2 — as repeated measures, never three
  independent samples.
- Folds are built on **policies**, not rows. For French severity, a policy's claims all follow the
  policy into the same fold, so no claim of a policy is ever in the training and the test fold at
  once. Spanish severity folds are built on the claiming policies.
- Training is capped at 10,000 rows per fold. Test rows: the fold's policies for frequency (capped at
  10,000), and **all** claims of the fold's test policies for severity. Every Arm and seed in a
  target sees the same test rows.
- The matrix is 4 targets × 4 Arms × 5 folds × 3 seeds = **240 fits**.

## Statistical plan

For target `t`, fold `f` and model seed `s`:

```
r_{t,f,s} = (M(A_raw) - M(B_ft30)) / M(A_raw)
```

A positive value means fine-tuning improved the target. Average over the three seeds to get `r_{t,f}`.

- **Per target.** Mean of the five `r_{t,f}`; 95% CI from a paired t with 4 degrees of freedom.
- **Per task.** Mean of the two portfolio means. The interval comes from a two-way bootstrap that
  resamples portfolios and folds (10,000 resamples). Two portfolios is a thin resample, so the
  interval is reported as indicative and the per-target intervals are always shown. If the two
  portfolios disagree in sign, the task result is **heterogeneous** and no task-level gain is
  claimed.
- **Severity clustering.** The Spanish severity metric is computed per fold with the claim weight,
  and the interval over folds is clustered by policy. Treating the 11,167 claim-equivalents as
  independent would understate the variance.

## Decision rule, fixed now

| State | Condition |
|---|---|
| **Go** | Task relative improvement: 95% CI excludes zero **and** the point estimate is at or above the floor |
| **No-go** | Task CI upper bound is below the floor — a meaningful gain is excluded |
| **Inconclusive** | CI covers both zero and the floor, or a target is untrainable or underpowered |

Per-target decisions use the same rule on that target's interval. Floors:

- **Frequency: 2%.** The French target's MDE was measured at 0.48% in #499; the Spanish target is
  confirmed by the resolution gate.
- **Severity: 2%, conditional on the resolution gate.** The conservative bounds are 1.95% (French)
  and 1.83% weighted (Spanish) — inside the floor, but only just. If the gate's measured MDE exceeds
  2% for a severity target, the floor for that target is raised in a **dated amendment before the
  fair test launches**, or the target is dropped from the task. It is not decided after seeing the
  effect.

## Power and the resolution gate

The full derivation is in `docs/analyses/freq_sev_power.md`. Measured or bounded MDEs:

| Target | MDE | Basis |
|---|---:|---|
| French frequency | 0.48% | measured in #499 |
| Spanish frequency | — | not measured; the gate decides |
| French severity | 1.95% | conservative bound from `log(amount)` SD 1.13 at 26,444 claims |
| Spanish severity | 1.83% | conservative bound from weighted SD 0.69 at 11,167 claim-equivalents |

The gate, run before any fair-test spend: `A_raw` **and** `B_ft30` on the five folds of all four
targets (forty in-context fits), the fold-level paired improvement per target, and

```
MDE_gate = 2.8016 * SD_fold(r) / sqrt(5)
```

> **2026-11-12 — amendment after the first gate run.** The gate originally measured
> `SD_fold(M_A_raw)` and called it an upper bound on the paired difference. It is not: fold
> difficulty is a shared component that moves both Arms together and cancels in `r`, so the
> A_raw-only SD overstated the MDE by an order of magnitude on the frequency targets — 10.05% and
> 7.36% relative against a 2% floor, where the paired quantity is what the decision uses. The gate
> now runs both Arms and measures `r_f = (M_A_raw − M_B_ft30) / M_A_raw` per fold; the severity and
> frequency floors are fixed from the paired MDE. The first run's summary is retained locally; it
> took 2.88 min and cost \$0.0129. The gate costs roughly \$0.02–\$0.05 and is released separately.

A **positive control** still gates the trainer before the gate: weights moved, training loss fell,
and a paired held-out gain on a synthetic known-signal target. It is the existing control (#498,
#516); this document does not change it.

## Capture contract

One capture per target. The v3 contract is insufficient for severity, so this pre-registers **v4**:

- `test_index.npy` indexes the target's source file: `freMTPL2freq.csv`, `spanish_motor_freq.csv`,
  `freMTPL2sev.csv` (claim rows) or the claiming-policy rows of the Spanish severity view.
- `exposure.npy` stays required for `freMTPL2freq` only. Spanish frequency's `Policies_in_force` is
  recorded in provenance and is not an offset.
- `weights.npy` is required for severity: all ones for French claims, `N_claims_year` for Spanish
  claiming policies.
- `cluster_id.npy` is required for severity: `IDpol` for French claims, the policy index for Spanish.
- The dataset block names **both** files and both sha256 for French severity, with `IDpol` as the
  join key; for Spanish severity it names both views and asserts the row alignment.
- A partial run is refused, as in v3. The schema version is 4; v1–v3 stay readable.

## Cost

The measured unit is 41.706 s for a 10,000-row, 30-epoch fine-tune on the RTX PRO 4000 Blackwell
(`benchmark_fit`, 2026-11-11, \$0.2678/hr effective). Scaling that over 240 fits with the epoch
assumption gives roughly **2 GPU-hours and \$0.55**, plus the ~\$0.05 cold start. The ceiling stays
\$50. The exact estimate must be produced by the harness against the new matrix before any launch,
as it was for the benchmark fit; a provisional figure is not a release.

## Order of work

1. **Data.** `data/raw/freMTPL2sev.csv` added from CASdatasets with source and both hashes; the two
   Spanish views' alignment asserted by a test. (This document's PR.)
2. **Resolution gate.** Paid, ~\$0.02–0.05, released separately. Its result fixes the severity floor
   by dated amendment.
3. **Implementation.** Capture v4, the target registry in the fair-test runner, and the grouped folds
   for severity. A ticket, no spend.
4. **Fair test.** 240 fits, unauthorised until the gate is inside the floors and the team signs off.

## What this does not do

- Authorise any run, including the gate.
- Change the positive control, the trainer, or the model version.
- Re-open the classifier pilot or the breadth cells.
- Claim anything about vehicle value, annual pure premium, or the exposure diagnostic.

## Sign-off

Proposed 2026-11-11. The owner and the team sign the document before step 2 is released; a change to
a target, an Arm, a fold or a floor after that is an amendment with a date, not an edit.

| Date | Change | By |
|---|---|---|
| 2026-11-11 | Filed: replaces the 2026-11-08 target set with frequency and per-claim severity across two portfolios. | agent, for owner review |
| 2026-11-12 | The resolution gate runs `A_raw` and `B_ft30` and fixes the floors from `SD_fold(r)`; the A_raw-only gate measured fold difficulty and overstated the MDE (10.05% / 7.36% on frequency). Owner released the correction before any fair-test data. | agent, owner approved |
