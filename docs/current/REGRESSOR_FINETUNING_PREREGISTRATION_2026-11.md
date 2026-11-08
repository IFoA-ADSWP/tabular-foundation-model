# Pre-registration — the regressor fair test (2026-11)

> **Status:** current — pre-registration, 2026-11-08. **Authorises:** no run. One implementation
> follows sign-off. **Scores:** relative improvement per target; 2% floor. **Model:** `v3_default`,
> pinned by checkpoint path. **Cost:** provisional \$15–\$40; ceiling \$50. **Decision it applies:**
> the map *is fine-tuning effective for the v3 regressor?* (#494) and tickets #495–#509.
> **Ticket:** #501 (this document).

This document fixes the design before any regressor run exists. A launch record must name it. It
does not authorise spend. The benchmark fit, the pin bump and the positive control are
implementation preconditions; each is named below.

## What is being tested

**Claim.** Fine-tuning improves the TabPFN regressor over raw TabPFN, under a matched inference
context, on identical test rows.

**Datasets.** Three targets plus one diagnostic. The treatment is the one settled in #507.

| Dataset | Rows | Target | Drop | Feature treatment | Metric | Folds |
|---|---|---|---|---|---|---|
| freMTPL2freq | 678,013 | `ClaimNb` | `IDpol` | `log(Exposure)` | Poisson deviance | KFold(5, seed 42) |
| spanish_motor_severity | 53,502 | `Cost_claims_year` | — | — | RMSE | KFold(5, seed 42) |
| ausprivauto0405 | 67,856 | `VehValue` | `ClaimOcc`, `Exposure` | — | RMSE | KFold(5, seed 42) |
| freMTPL2freq (diagnostic) | 678,013 | `Exposure` | `IDpol` | — | RMSE | outside the decision |

`prem_pure` is not a target. It carries leakage through `prem_final`, `prem_last` and
`prem_market`, and it has no registry entry.

**Model.** `v3_default` via `tabpfn==8.5.0` on Python 3.12. Pinned by checkpoint path
`tabpfn-v3-regressor-v3_default.ckpt`, sha256
`311ce18d97e9533d8585eaadafe040fbdd8070533209ed8696641dadc97a7301`. `v3.5` is not used. `auto` is
not accepted: an unpinned call can resolve to a different line.

**Comparator.** `A_raw` and `B_ft30` of the same fold and model seed, on the same rows. The shipped
`FinetunedTabPFNRegressor` refits inference on all training rows, so both Arms see the same context
by construction. The historic 64-row context cut is forbidden.

## Design

**Rows.** Training cap 10,000 per fold for the primary. The 50,000-row arm is a sensitivity.
Test is a fixed 10,000-row subsample of each fold (seed 42), or the whole fold when it is smaller.
The same test rows are used by every Arm and model seed. 5,000 test rows is rejected: ClaimNb and
VehValue fall below 80% power at 2%.

**Folds and seeds.** Canonical `KFold(5, shuffle=True, random_state=42)`, fixed. Three model seeds
inside each fold — 0, 1 and 2 — recorded in the Capture. The fold is the sampling unit; the three
seeds are repeated measures, never three independent samples.

**Epochs.** 30 primary. 3 and 10 are sensitivity Arms. Early stopping is off, so the epoch budget is
the budget that was run.

**Arms.**

| Arm | Meaning |
|---|---|
| `A_raw` | raw TabPFN regressor, in-context, no training |
| `B_ft30` | full-parameter fine-tune, 30 epochs, MSE loss |
| `B_ft10`, `B_ft3` | the same at 10 and 3 epochs |
| `X_log1p` | `log1p(ClaimNb)` target, 30 epochs, ClaimNb only; co-primary/sensitivity |
| `S_50k` | 50,000 training rows, 30 epochs, sensitivity |
| `D_exposure` | diagnostic only; never in the decision |

The primary comparison is `A_raw` against `B_ft30`, per target. The other Arms are pre-registered
sensitivities, not alternatives chosen after seeing the result.

## The positive control (instrument check)

The control runs before the fair test, on local CPU or MPS, for no more than 15 minutes, at \$0.

1. **Overfit sanity.** Fine-tune a small synthetic frame. Assert that the parameters moved and that
   training loss fell.
2. **Known-signal target.** Fine-tune a synthetic regression target with a known low-noise function.
   Require a paired held-out gain over raw TabPFN with a 95% CI excluding zero.

All three must hold: parameter delta, loss fall, paired gain. A metric alone is not enough. The
historic AUS Auto arm executed zero steps, weights unchanged, and still "lost" 0.049 R²; a control
must catch that class of failure.

**On failure: stop.** Do not run the fair test, do not write a verdict, and reopen the trainer
ticket with the failure evidence.

## The statistical plan

For target `t`, fold `f` and model seed `s`, compute the metric for both Arms. Define the relative
improvement

```
r_{t,f,s} = (M(A_raw) - M(B_ft30)) / M(A_raw)
```

A positive value means fine-tuning improved the target. Average over the three seeds to get `r_{t,f}`.

- **Per target.** Mean of the five `r_{t,f}`; 95% CI from a paired t with 4 degrees of freedom.
- **Pooled.** Mean of the three target means. The 95% CI comes from a two-way bootstrap that
  resamples targets and folds (10,000 resamples), because three target means are too few for a t
  interval. The per-target intervals are always shown.
- **Heterogeneity.** If the target intervals disagree in sign, the pooled result is described as
  heterogeneous and no method-level gain is claimed.

**Power, fixed in advance.** From #499, at 10,000 test rows per fold: the 80%-power MDE is about
0.0048 for ClaimNb (2% delta 0.0061), 0.0142 for severity (delta 0.0367), and 0.0266 for VehValue
(delta 0.0144) under the worst variance proxy. ClaimNb and severity are powered; VehValue is
conditional.

**VehValue gate.** Before the verdict, compute the observed fold-level SD of the `A_raw` to
`B_ft30` difference. If it exceeds **0.0087**, keep VehValue as a reported target, exclude it from
the pooled estimate, and show its CI and MDE. Do not add folds after seeing the effect; a larger
fold count is a new registration.

## The decision rule, fixed now

| State | Condition |
|---|---|
| **Go** | Pooled relative improvement: 95% CI excludes zero **and** point estimate ≥ 2% |
| **No-go** | Pooled CI upper bound < 2% — a meaningful gain is excluded |
| **Inconclusive** | CI covers both zero and 2%, or a target is untrainable or underpowered |

Per-target decisions use the same rule on that target's interval. VehValue can be no-go or
inconclusive on its own without moving the pooled state.

**ClaimNb objective mismatch.** The trainer minimises MSE; the decision scores Poisson deviance. A
deviance null on `B_ft30` is **inconclusive, not a null**, unless `X_log1p` also nulls. The spec
records the mismatch as a limitation of the test.

**Untrainable target.** Mark it not trainable, stop only that target, continue the others, and
exclude it from the pool. A zero-step arm is never reported as a null. A retry is a new Run.

## Capture and record

For every Arm × fold × model seed: per-row predictions, ground truth, `predictions.npy`,
`ground_truth.npy`, `capture.json` with hashes, and `meta.json`. No library checkpoints are kept; if
one is written, its SHA-256 goes in `meta.json`.

`meta.json` records: dataset, target, transform, drop list, fold seed, model seed, Arm, epochs,
training rows, test rows, `tabpfn_version`, `python_version`, `model_path` and checkpoint sha256.
The evidence gate **fails** a run with a missing field. The runner produces the Capture through
`src/run_capture.py`; the library is not patched.

## Environment and implementation preconditions

- `tabpfn==8.5.0` on Python 3.12, exact pin plus lock; a legacy requirements file keeps the v2
  scripts runnable; CI stays on 3.12.
- The pin bump, the legacy file, the capture fields and the positive control are implementation
  preconditions, not part of this design map.
- One benchmark fine-tune at 10,000 rows × 30 epochs on the target GPU measures wall time. The
  estimate is extrapolated over Arms × folds × seeds × epochs and the 50k sensitivity. The
  benchmark sits inside the ceiling.

**Cost.** Provisional \$15–\$40 at the measured step time; **ceiling \$50**. The estimate includes
the benchmark, the control, both Arms, the 3/10/30 epoch ladder and the 50k sensitivity.

## What is out of scope

- Classifier fine-tuning; it has its own evidence and pilot.
- v2 weights and the v2 hand-rolled loop; its APIs were removed in 8.5.0.
- Transfer and pooled Arms; they graduate only if A/B is ambiguous.
- New datasets beyond the three targets; `prem_pure` is retired.
- Executing the fair test or any paid Run. This document authorises no spend.
- Recovering deleted historic artefacts by re-running.

## Registry entry (proposed, implementation)

Three pilot experiments, one per target, sharing the config:

```toml
[pilot_experiments.regressor_fair_test_claimnb]
dataset = "freMTPL2freq"
arms = ["A_raw", "B_ft30", "B_ft3", "B_ft10", "X_log1p", "S_50k"]
seed = 42
folds = 5
train_size = 10000
test_size = 10000
model_version = "v3_default"

[pilot_experiments.regressor_fair_test_claimnb.config]
epochs = 30
early_stopping = false
learning_rate = "library default"
fit_mode = "full-context"
```

The same block with `regressor_fair_test_severity` and `regressor_fair_test_vehvalue` for the other
two targets. The schema must carry the drop list, the transform and the three model seeds; if it
cannot, the implementation extends it rather than putting the treatment only in prose.

## Amendments

| Date | Change |
|---|---|
| 2026-11-08 | Filed. VehValue's pooled membership is conditional on the fold-SD gate; `X_log1p` is co-primary for ClaimNb. |
