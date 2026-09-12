# Fine-Tuning Methodology — Technical Description

> Date: 2026-09-12 | Status: current | Related: #22
> Describes the method used in **R1** (the smoke test). The results are in
> `FINE_TUNING_PILOT_RESULTS.md`; what R1 did and did not exercise is in `SMOKE_TEST_SCOPE.md`.
> The wider study this belongs to is `FINE_TUNING_EXPERIMENT_DESIGN.md`.
>
> Written so a statistician can assess the method without reading the code. Every parameter
> named below was verified against the installed package (`tabpfn==8.5.0`) and against our
> runner (`scripts/run_pilot.py`).

---

## 1. The quantity being estimated

For each dataset independently, the target of estimation is

```
Δ = ROC AUC(arm B) − ROC AUC(arm A)
```

where **A** and **B** are scored on the **same held-out test rows**, with identical features
and an identical split. The design is therefore **paired by construction** — every test
observation has a prediction under both arms. Δ is the "effect of fine-tuning" for that dataset.

Secondary quantities: Δ PR AUC and Δ Brier score, same structure.

This is an estimation problem, not a hypothesis test as executed: R1 produced a single point
estimate of Δ per dataset, with no repeated sampling. Any inference about Δ requires the
variance machinery discussed in §10.

---

## 2. The estimator being fine-tuned

The model is **TabPFN** (v3 default classifier checkpoint, `tabpfn-v3-classifier-v3_default.ckpt`,
from the `Prior-Labs/tabpfn_3` weights repository), via the Python package `tabpfn==8.5.0`.

TabPFN is a **pretrained transformer that performs in-context learning**. Its defining property,
and the reason the raw/instrumented distinction in §3 matters, is this:

> A raw TabPFN prediction involves **no gradient descent on the target data**. The training rows
> are presented to the network as *context* — they condition a forward pass — and the test rows
> are *queries* to be predicted. Nothing in the model is updated.

Statistically: arm A is not "a model fitted to the training set". It is a **fixed, pretrained
mapping** evaluated with the training set as conditioning evidence. There is no optimisation, no
convergence, no local minimum, and no fitting variance in the usual sense — though the ensemble
mean in §5 is a source of Monte-Carlo variation.

---

## 3. What "fine-tuning" means here, precisely

Arm B keeps the pretrained parameters as a **starting point** and then performs **gradient
descent on the model's own parameters using only the target dataset's training split**.

Two facts that determine how this should be interpreted:

1. **It is full-parameter fine-tuning, not a classification head.** Verified: the optimiser is
   constructed over `model.parameters()` with nothing frozen and no layer selection
   (`finetuning/finetuned_base.py`). Every weight in the network is in scope.
2. **The objective is cross-entropy on the query rows**, not on the context
   (`finetuning/finetuned_classifier.py`, `_compute_classification_loss`). The model is trained
   on the *same task shape* it is used for: condition on context, predict query.

So arm B is the pretrained prior **modified by a short, low-learning-rate optimisation on the
target**, and arm A is the prior **unmodified**. Δ measures the effect of that modification.

---

## 4. The data pipeline — identical for every arm

Per dataset, in order:

1. **Load** the CSV; `y` = the named target column as integers; `X` = **all other columns**,
   one-hot encoded (`pandas.get_dummies`), missing values filled with 0, cast to float64.
   The target is dropped from the features by construction.
2. **Row cap.** If the CSV exceeds 3,500 rows, take a **uniform (unstratified) random sample** of
   3,500 with seed 42. *This is a design limitation: the sampled class balance need not match the
   full population (e.g. coil2000 5.97% → 5.74%).*
3. **Outer split.** `train_test_split(test_size=1000, random_state=42, stratify=y)` on those
   3,500 rows → 2,500 candidate training rows and a **1,000-row test set**.
4. **Training cap.** From the 2,500, a **stratified** subsample of 2,000 is taken as the training
   set; the remaining ~500 rows are **discarded unused**.
5. **Scaling.** `StandardScaler` **fit on the training set only**, then applied to the test set.
   No test statistics enter the transform.
6. Both arms receive these same objects: the same `X_train` (2,000 × p), the same `y_train`, and
   the same `X_test` (1,000 × p). The test set is touched once per arm, for scoring only, and is
   never used to make any modelling decision.

**Effective sample sizes per dataset:** 2,000 training rows, 1,000 test rows, ~500 discarded.
Test-set positive counts are small on some datasets (coil2000: 57 positives), which dominates
the achievable precision — see `FINE_TUNING_PILOT_RESULTS.md` §5d.6.

---

## 5. Arm A — raw TabPFN (the comparator)

```python
TabPFNClassifier(
    ignore_pretraining_limits=True,          # allow the full 2,000-row context
    n_estimators=2,                          # 2 forward-pass ensemble members
    fit_mode="batched",
    inference_precision=torch.float32,
    random_state=42,
    device="cuda",
).fit(X_train, y_train)                      # conditioning only; no gradient steps
probs = clf.predict_proba(X_test)[:, 1]
```

`fit` here performs **preprocessing and caching, not optimisation**. Prediction averages the
`n_estimators=2` ensemble members.

Note what this means for the comparison: the 2,000 training rows are **in-context evidence** for
arm A. It is a legitimate and strong baseline, but it is not a "trained model" in the classical
sense, and Δ should not be read as "adding training to a trained model".

---

## 6. Arm B — in-domain fine-tuning (the intervention)

```python
FinetunedTabPFNClassifier(                   # shipped by tabpfn 8.5.0
    device="cuda",
    epochs=3,                                # from our config's max_finetune_steps
    learning_rate=1e-5,
    n_estimators_finetune=2,                 # from our config's n_estimators
    random_state=42,
).fit(X_train, y_train)                      # fine-tuning happens here
probs = clf.predict_proba(X_test)[:, 1]
```

**We use the library's own trainer rather than a hand-rolled loop.** This is a methodological
decision, not a convenience. An earlier hand-written version of this arm (a) left the model in a
batched-executor state that could not serve a standard prediction, and (b) wrapped the optimiser
construction and the loss/backward/step in bare exception handlers, so a failure inside could
leave the optimiser unset — the loop would run, take **no gradient step**, and still report
metrics. Both defects produced output that looked plausible. Using the shipped trainer removes
that whole class of silent failure.

---

## 7. What happens inside arm B — step by step

1. **Validation holdout.** `validation_split_ratio=0.1` (library default): **10% of the 2,000
   training rows (~200) are set aside as a validation set**; ~1,800 rows are optimised on. The
   validation set is carved out of the *training* split — the test set is untouched.
2. **Optimiser.** AdamW over **all** model parameters, learning rate 1e-5, weight decay 0.01
   (default), with a **linear-warmup learning-rate schedule** (enabled by default). Mixed
   precision (GradScaler) is active on CUDA.
3. **Each epoch.** The training rows are preprocessed into chunks; a chunk is split into
   **context** and **query** portions using a query ratio of 0.2 (20% of the chunk), stratified
   where the chunk permits, with the query size bounded below by the number of classes. The model
   conditions on the context portion, and the **cross-entropy loss is computed on the query
   portion only**. With two estimators the loss is the estimator-mean over the batch dim.
   A 50,000-sample chunk cap exists but **does not bind at ~1,800 rows**.
4. **Validation and checkpointing.** The primary metric — **ROC AUC** — is evaluated on the
   ~200-row validation set **before training and after each epoch**. An improvement must exceed
   the best value by `min_delta=1e-4`. The **best checkpoint is retained**, and early stopping
   restores the best state rather than the final epoch.
5. **Early stopping is inert here.** It is enabled by default with `early_stopping_patience=8`,
   and the patience counts *validation checks*, not epochs. With `epochs=3` there are three
   checks, so patience can never be reached. In practice the arm selects the best of three
   checkpoints on 200 rows.
6. **Prediction.** After training, the fine-tuned estimator is cloned into a standard
   `TabPFNClassifier` carrying the **fine-tuned weights**, preprocessors are refit on the training
   data, and `predict_proba` runs the ordinary in-context inference path over the test rows.

**Summary of what differs between the arms:** the only intended difference is that B's weights
were optimised on ~1,800 rows of the target's training data for 3 epochs. Everything downstream —
features, split, scaling, test rows, inference path — is held fixed.

---

## 8. Hyperparameters were not tuned on the target

A single pre-specified configuration was used for all four datasets:

| Parameter | Value | Source |
|---|---|---|
| `epochs` | 3 | our config (`max_finetune_steps`), mapped to the trainer's `epochs` |
| `learning_rate` | 1e-5 | our config |
| `n_estimators_finetune` | 2 | our config (`n_estimators`) |
| `random_state` | 42 | our config |
| `validation_split_ratio` | 0.1 | library default |
| `early_stopping` / `patience` | True / 8 | library defaults (inert at 3 epochs) |
| `weight_decay` | 0.01 | library default |
| `min_delta` | 1e-4 | library default |
| `n_finetune_ctx_query_samples` | 50,000 | library default (inert at this size) |
| `finetune_ctx_query_split_ratio` | 0.2 | library default |
| `use_lr_scheduler` | True (linear warmup) | library default |

**Consequences for inference.** No hyperparameter was selected using the target's test set, so
there is **no selection bias from tuning**. Equally, there is **no per-dataset adaptation of the
lever**: the same 3-epoch, 1e-5 configuration was applied to a 6%-positive and a 38%-positive
dataset alike. A null result is therefore a statement about *this* configuration, which was
deliberately small, and it **biases toward finding no effect**.

The recorded `config` field in the metrics file is not reliable: it stores the same
`PILOT_CONFIG` for every arm, including `context_samples: 64`, which **neither arm uses**. The
table above is the effective configuration.

---

## 9. Leakage and validity controls

| Control | Status |
|---|---|
| Target excluded from features | yes — dropped before encoding |
| Scaler fit on training data only | yes |
| Test rows never seen during fit | yes |
| Stratified splitting on the target | yes (both the outer split and the training cap) |
| Identical test rows across arms | yes |
| Validation holdout drawn from training, not test | yes (10% of the 2,000) |
| Test set used only for final scoring | yes — one use per arm |
| Hyperparameters selected on the test set | no — not used for selection at all |
| **In-domain evaluation** (fit and score on the same dataset) | **by design — see §10** |
| Row subsample unstratified (step 2 of §4) | **no — a real limitation** |

There is no test-set leakage. The threats in §10 are of validity and power, not of contamination.

---

## 10. Threats to validity, and what a statistician should require next

1. **In-domain only.** B is fine-tuned on, and scored on, the same dataset. Δ is therefore an
   *upper bound* on what deployment would deliver, and is only available at all if labelled data
   from the target is already in hand. The transfer question — fine-tune on some datasets,
   evaluate on an unseen one — is **untested**: arms C/D exist in the design and have never run.
2. **One seed, one split.** Δ is a single draw. There is **no variance estimate**, so no interval,
   no p-value, and no way to separate the effect from split-to-split variation.
3. **Underpowered test sets.** For A_raw, bootstrap 95% CI widths on ROC AUC are 0.031-0.118
   (coil2000: 0.118 on 57 positives). Observed |ΔROC| ≤ 0.0096 is far inside that. **The design
   cannot resolve the effect size it observed.**
4. **The lever was deliberately small** — 3 epochs at 1e-5 — which biases toward a null result.
5. **Model selection on 200 rows.** Checkpoint choice uses ~200 validation rows; with 3 epochs it
   is a best-of-three selection, which is high-variance but limited in scope.
6. **The arms do not use identical data**: A conditions on 2,000 rows, B optimises on ~1,800
   (the rest is its validation set).
7. **Environments differed across arms.** A and B ran on the GPU instance; E and F ran locally on
   CPU with different Python/torch/scikit-learn versions. The split is deterministic so the test
   rows match, but this is not one controlled run.
8. **Determinism is approximate on GPU.** Two runs of the *same* raw arm on different cards
   differed by ~2e-4 in ROC AUC, which is an estimate of the run-to-run floor.
9. **No calibration assessment** on the fine-tuned model, though fine-tuning is precisely the
   operation that can distort probabilities.
10. **PR AUC is the more sensitive instrument** on imbalanced targets and improved under B on all
    four datasets (+0.003 to +0.008) while ROC was mixed — the one directional signal, and the
    natural hypothesis for a better-powered test.

**Minimum design for a defensible claim:** multiple seeds and/or repeated stratified folds (so Δ
has a distribution); the paired test on the shared test rows (the structure already supports it);
a pre-specified decision rule with a power calculation, replacing the current R3 gate, whose
second criterion raw TabPFN satisfies on its own; and arms C/D for any transfer claim.

---

## 11. Reproducing this

| Item | Value |
|---|---|
| Runner | `scripts/run_pilot.py`, arm `B_in_domain` |
| On the GPU box | `scripts/gpu_helpers/bootstrap_pilot.sh` (installs `tabpfn==8.5.0`) |
| Metrics / artifacts | `outputs/gpu-pilot/pilot_metrics.parquet` (16 arm-runs) |
| Predictions | `outputs/finetune/pilot/<dataset>/<arm>/predictions.npy` — **absent for arm B** (see `SMOKE_TEST_SCOPE.md` §6.4) |
| Split seed | 42 (outer split, training cap, and the fine-tuner's `random_state`) |
| Package versions | box: python 3.11.12, torch 2.7.0+cu128, numpy 2.2.5, tabpfn 8.5.0, scikit-learn 1.9.1 |
| Hardware | NVIDIA L40S (A and B); local CPU (E and F) |
| Cost | $0.0482 for the run that produced A and B |

**Reproducibility caveat:** identical seeds reproduce the *split* exactly, but not necessarily
bit-identical GPU numerics. Treat a repeat as a new draw, not a re-run — which is precisely why
the single-seed design is the binding limitation, not a detail.
