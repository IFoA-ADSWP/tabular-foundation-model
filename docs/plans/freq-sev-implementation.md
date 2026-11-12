# Plan — implementing the frequency/severity fair test

**Issue:** #555 (design #552). **Status:** Proposed.

## What and why

The pre-registration (#552) replaced the 2026-11-08 target set with two actuarial tasks across two
portfolios. The runner (`src/fair_test_runner.py`) and the capture (`src/run_capture.py`) still
implement the old set: annual cost as "severity", `VehValue`, the exposure diagnostic, and capture
v3. They cannot express per-claim severity, grouped folds, or the claim weight, so the design cannot
run until they can.

This is a build, not a decision. It spends nothing.

## Shape

Four stages, each a separate change:

1. **Data layer** — `src/freq_sev_data.py`. One loader per target returning features, target, policy
   groups, weights and cluster ids, with the pre-registered feature treatment. Grouped folds in
   `regression_data.group_fold_splits`. Tests on the committed data.
2. **Runner and capture v4** — the runner's target registry, grouped folds, log-scale severity
   targets, the weight/cluster arrays, and a dataset block that names both files for French
   severity. `capture_reader` stays able to read v1–v3.
3. **Resolution gate** — a mode that runs `A_raw` on the five folds of all four targets and reports
   the fold-level metric SD and MDE. Paid, ~$0.02–0.05, released separately.
4. **Fair test** — 240 fits, ~$0.55, released only after the gate and sign-off.

## Judgement calls

1. **Groups are policies, not rows.** For French severity a policy contributes one to five claims;
   a row-level KFold would leak a policy's claims across folds. Folds are built on unique `IDpol`
   (French) and on the claiming-policy rows (Spanish), then rows follow their group. A test asserts
   no group appears in both sides of a fold.
2. **Severity is modelled on the log scale.** The metric is RMSE of `log(amount)`, so the target
   handed to the trainer is the log and predictions are stored on the log scale. That keeps the
   metric honest: a raw-scale RMSE is dominated by the largest claims.
3. **The Spanish weight is data, not a feature.** `N_claims_year` becomes the weight and is dropped
   from the feature matrix. `Cost_claims_year` is dropped from the frequency target and
   `N_claims_year` from the severity target — the two are exact siblings and would leak each other.
4. **The French severity dataset is two files.** The claim rows are the unit; the policy features
   join on `IDpol`. The dataset block must name both files and both hashes, because a row index in
   the claim file says nothing without the policy file.
5. **Categorical encoding stays global and target-blind**, as in `load_frame`, so the encoding
   cannot leak the target.

## Verification

- `pytest tests/test_freq_sev_data.py tests/test_regression_data.py -q` — row counts, the join, the
  grouped folds (no policy straddles), the weights (Spanish sum 11,167), the sibling drops.
- `./scripts/check.sh` — the eight-check gate.
- No paid run in stages 1–2.
