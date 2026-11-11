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

### Amendment 2026-11-10 — the capture carries row identity, exposure and quantiles

> Added after a grilling with the owner; ticket #538. The decision rule, the 2% floor and the power
> analysis are unchanged.

The capture above was written for evidence: two arrays and their hashes prove that a prediction
existed. It is not enough for a reader who wants a metric other than the pre-registered one.
Poisson deviance was named, and others will follow: a metric that needs a source column or a
predictive distribution cannot be computed from `y` and `ŷ` alone. Exposure is stored as a
convenience — with `test_index` it is joinable from the pinned CSV — so scoring needs no join.

**Schema v3, and when it applies.** A run *declares* v3 by writing `test_index.npy` in its first
slot. From that declaration every slot must carry `test_index.npy` and `quantiles.npy`;
`exposure.npy` is required when and only when the dataset is `freMTPL2freq`, and its absence on
severity and VehValue is neither a null hash nor a refusal. A partial run is **refused**, not
demoted to v2 — otherwise one missing array turns fourteen faithful slots into an unhashed capture
that passes the older gate — and a foldless run may not write the arrays at all, because a v1
manifest has no place to hash them. A folded run that never declares v3 stays v2.

| Array | Shape, dtype | What it is |
|---|---|---|
| `test_index.npy` | `(n,)`, int64 | 0-based positions in `data/raw/<dataset>.csv` **as read, before any `dropna` or `reset_index`**. The record's `provenance.dataset.sha256` is what makes the join checkable. It is the fold's index, so every slot of one fold carries identical values. |
| `exposure.npy` | `(n,)`, float64 | the raw `Exposure` column for the same rows; `freMTPL2freq` only |
| `quantiles.npy` | `(9, n)`, float64 | nine rows in ascending level order `0.1…0.9`, one column per test row. Values are on the scale the Arm trained on (for `X_log1p`, `log1p` of the target) and are stored before any clip. `meta.json` records `quantile_levels`. |

**The manifest and the gate.** v3 keeps every v2 requirement — `versions.tabpfn`, `versions.python`
and `weights.path`/`weights.sha256` — and adds `test_index_sha256` and `quantiles_sha256` to every
entry, plus `exposure_sha256` for `freMTPL2freq`. The citation gate applies the environment check to
v2 and v3 alike and requires the array hashes for v3.

**The reader and rescore.** `src/capture_reader.py` becomes version-aware and keys slots by
`(arm, seed, fold)`; `VerifiedSlot` gains `fold` and `src/rescore.py` gains a `fold` column. This is
not optional: today the reader accepts only schema 1 and keys by `(arm, seed)`, so a folded capture
collapses fifteen entries per arm into three and refuses honest runs. The v2 folded capture shipped
in #501 is already unreadable, and #538 fixes it before v3 exists.

**The record.** Every slot's `meta.json` gains `verdict_metric` (the name: `poisson_deviance` for
`freMTPL2freq`, `rmse` for the other two), `verdict_metric_value`, `rmse` and `quantile_levels`.
The v3 gate requires all four keys. `rescore` compares a metric only when its name equals
`verdict_metric`; `rmse` duplicates `verdict_metric_value` on severity and VehValue by design, so a
rescorer that reads `verdict_metric_value` as a deviance would be reading RMSE.

**The metrics.** Six registry rows, each with its definition and the finding that put it there:

| Metric | Definition |
|---|---|
| `rmse/1`, `mae/1`, `medae/1` | over all rows, on the stored target scale |
| `rmsle/1` | `log1p` applied to both sides, with `ŷ` clipped below at 0; rows with `y < 0` are excluded, and none of the three targets has one |
| `poisson_deviance/1` | deviance of **counts**: `2·Σ[y·log(y/ŷ) − (y − ŷ)]`, with `ŷ` clipped below at `1e-12` (the capture spec's scoring convention) and `y = 0` handled by the limit: the bracket is `ŷ`, so that row contributes `2ŷ`. Exposure is a *feature*, not an offset; a rate-scale variant is a different name and version. |
| `gini/1` | the normalised Gini, `2·AUC − 1`, where AUC is the concordance of `ŷ` against `y` over all row pairs with `y_i ≠ y_j` (pairs tied on `y` are excluded), a pair tied on `ŷ` scores one half, and a constant `ŷ` scores 0 |

`tests/test_metric_registry.py` asserts today that the table holds exactly the metrics `rescore`
computes; #538 redefines that assertion to cover both the classifier set and the regression set
rather than weakening it. Further rows — pinball, Tweedie — are added when a document first needs
their definition.

Storing more is not scoring more. The verdict still uses Poisson deviance for `ClaimNb` and RMSE for
the other two targets, and the trainer still minimises MSE, so a deviance null remains inconclusive
unless `X_log1p` also nulls.

The writer, the manifest's hashes and the gate's v3 requirement land with #538, and the capture is
large: `quantiles.npy` is 720 kB per slot under the stated float64, which is about 76 MB for
freMTPL2freq's seven Arms and 54 MB for each of the other two targets — roughly 185 MB of quantiles
across the fair test, plus about 20 MB of index and exposure. That PR needs the `evidence-change`
label if anything lands under `results/`. Until #538 lands, no run may claim this schema: the
contract is stated here so the runner is built against it, not so a record can cite it early.

## Environment and implementation preconditions

- `tabpfn==8.5.0` on Python 3.12, exact pin plus lock; a legacy requirements file keeps the v2
  scripts runnable; CI stays on 3.12.
- The pin bump, the legacy file, the capture fields and the positive control are implementation
  preconditions, not part of this design map.
- One benchmark fine-tune at 10,000 rows × 30 epochs on the target GPU measures wall time. The
  estimate is extrapolated over Arms × folds × seeds × epochs and the 50k sensitivity. The
  benchmark sits inside the ceiling.

Measured rate, cold-start overhead and the cost controls are owned by
`docs/current/FINETUNING_COST_AND_CONTROLS.md`; this section states the ceiling, not the rate.

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
| 2026-11-10 | Capture v3: `test_index`, `exposure` and nine quantiles per slot, all hashed; six regression metrics registered. The decision rule and the 2% floor are unchanged (#538). |
