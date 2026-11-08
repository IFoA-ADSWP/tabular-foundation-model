# Can the v3 regressor be fine-tuned?

> **Status:** current as of 2026-11-08. Research for wayfinder ticket #495 (map: fine-tuning).
> **Question:** is there a working fine-tuning path for `TabPFNRegressor` on `v3_default`, or does
> one have to be built? **Answer:** the pinned library ships one and it runs — on CPU, on the three
> historic targets, at probe size. **Cost of this work:** £0 (CPU only; the only download is the
> public 233 MB checkpoint).

## Bottom line

`tabpfn==8.5.0` ships `tabpfn.finetuning.finetuned_regressor.FinetunedTabPFNRegressor`, a
scikit-learn-shaped trainer that fine-tunes the whole model on one dataset. It supports a full-context
run, an epoch budget, validation with early stopping, per-row predictions and checkpointing, and it
executed gradient steps with finite losses on all three historic targets — `ClaimNb`, `prem_pure`,
`VehValue` — and on the `log1p(claim frequency)` transform that produced **zero executed steps** in
the v2 hand-rolled loop.

The v2 loop cannot be repaired on 8.5.0, because the API it calls was removed: it imports
`tabpfn.finetune_utils` and calls `TabPFNRegressor.get_preprocessed_datasets`, neither of which
exists in 8.5.0 (probe: `grep` over the 8.5.0 wheel; `tabpfn/finetuning` is a new package and
`RegressorBatch` replaces the manual batch tuple). The library trainer is therefore not an
alternative to the hand-rolled loop — it is the replacement for it.

Two things are still missing before a real run, neither of them research: an interpreter that can
install 8.5.0 (it requires Python ≥ 3.10; the local `.venv` is 3.9 and carries 7.0.1, whose
`ModelVersion` has no `V3`), and a runner that turns the trainer's per-row predictions into the
repository's `capture.json`. The trainer itself emits no capture.

## The class and its API

| | |
|---|---|
| Class | `FinetunedTabPFNRegressor` — `tabpfn/finetuning/finetuned_regressor.py:140` |
| Import | `from tabpfn.finetuning.finetuned_regressor import FinetunedTabPFNRegressor` (also re-exported from `tabpfn.finetuning`) |
| Constructor | keyword-only; the regressor-specific parameters are docstringed at `finetuned_regressor.py:244-320`, the shared ones at `finetuned_base.py:421-499` |
| `fit` | `fit(X, y, X_val=None, y_val=None, output_dir=None) -> FinetunedTabPFNRegressor` (`finetuned_regressor.py:491`, base at `finetuned_base.py:701`) |
| `predict` | `predict(X, **kwargs) -> ndarray`, shape `(n,)`, `**kwargs` forwarded to the inference regressor (e.g. `output_type`) (`finetuned_regressor.py:520`) |
| Model selection | `model_version=ModelVersion.V3`; the package enumerates `V2, V2_5, V2_6, V3` (`tabpfn/constants.py:31-37`) and the v3 regressor checkpoint is `tabpfn-v3-regressor-v3_default.ckpt` (`tabpfn/model_loading.py:185-195`) |
| Weight pin | `extra_regressor_kwargs={"model_path": "<path>"}` — the finetuner has no `model_path` of its own; it forwards regressor kwargs (`finetuned_base.py:815-838`) |

The pin matters: `model_version` unset falls back to `settings.tabpfn.model_version`, the same
`auto` default a plain `TabPFNRegressor` uses (`finetuned_base.py:499-509`), so a record that says
`v3_default` must pass either `model_version=ModelVersion.V3` or an explicit checkpoint path.

## Capability checklist

| Requirement | Supported | Where / how |
|---|---|---|
| Full-context training | **Yes.** `n_finetune_ctx_plus_query_samples` defaults to 50,000 and is capped at the training set size, so at insurance scale the whole training frame is one meta-dataset per epoch (`finetuned_base.py:430`, `917-919`). The final inference regressor is refitted on **all** training rows (`finetuned_regressor.py:477-489` → `fit_mode="fit_preprocessors"`), so fine-tuned and raw arms see the same inference context by construction. |
| Epoch budget | **Yes.** `epochs` (default 30) and a wall-clock `time_limit` (seconds) (`finetuned_base.py:421-499`). One epoch = `ceil(n_samples / n_finetune_ctx_plus_query_samples)` optimiser steps (`finetuned_base.py:1032-1066`), i.e. **one step per epoch** at our sizes. |
| Validation | **Yes.** `validation_split_ratio` (default 0.1, 0/None disables), or an explicit `X_val`/`y_val` to `fit`. Validation metric is MSE only for the regressor (`eval_metric: Literal["mse"]`). |
| Early stopping | **Yes.** `early_stopping` (default True), `early_stopping_patience` (8), `validation_frequency` (1), `min_delta` (`finetuned_base.py:1327-1362`). Note the repository's classifier pilot deliberately pins `early_stopping=False` to keep the epoch budget honest; the same choice is available here. |
| Per-row predictions | **Yes.** `predict` returns one value per row. Probe: 80 test rows → shape `(80,)`, all finite. |
| Stability aids | `grad_clip_value=1.0`, AdamW, linear-warmup/cosine LR by default (`finetuned_base.py:1130-1190`), NaN-masked loss (`_compute_regression_loss`, `finetuned_regressor.py:39-138`). |

## The numerical instability does not reproduce

### Why the v2 loop executed zero steps

The legacy runner is `scripts/legacy_finetuning/run_small_finetune_regressor_trial.py`; its
companion is `run_finetuned_tabpfn_regression_benchmark.py`. Both drive the model by hand:
`get_preprocessed_datasets` → `meta_dataset_collator` → `optimizer.step()`, guarded by
`if not torch.isfinite(y_test_standardized).all(): continue` and a second `isfinite` guard on the
loss. On `ClaimNb` every batch tripped a guard: `finetune_steps_executed=0` with
`skipped_nonfinite_loss=14`, and restricting the pool to positive claims still gave 0 steps
(`docs/archive/STAGE_A_B_FINDINGS_AND_RECOMMENDATIONS.md:117-121`).

That code targets a pre-8.0 API. In 8.5.0:

- `tabpfn.finetune_utils` does not exist (the helper is now `tabpfn.finetuning.train_util`);
- `TabPFNRegressor.get_preprocessed_datasets` does not exist — only `fit_from_preprocessed`
  (`tabpfn/regressor.py:963`) survives, and the docstring that mentions the old method
  (`regressor.py:401-426`) describes a flow the class no longer exposes;
- `meta_dataset_collator` moved to `tabpfn.finetuning.data_util`.

So the hand-rolled loop fails at import/call time on 8.5.0, before it can reach the guard that
produced the zero.

### Why the shipped trainer does step

`FinetunedRegressor._should_skip_batch` returns `False` unconditionally — "Never skip a batch for
regression" (`finetuned_regressor.py:353-357`) — and the loss masks non-finite **targets** out of the
mean rather than abandoning the batch (`_compute_regression_loss`, `finetuned_regressor.py:100-138`).
The batch loop has no `isfinite` escape hatch, clips gradients at norm 1.0, and the LR warms up from
zero. The structural cause of the v2 failure — a guard that silently converts a numerical wobble into
"no training happened" — is absent.

### Probe result (free, CPU, this ticket)

CPU-only run in a throwaway Python 3.12 venv with `tabpfn==8.5.0`, `FinetunedTabPFNRegressor`,
`model_version=ModelVersion.V3`, 320 training rows / 80 test rows, 2 epochs, `n_estimators_finetune=1`,
validation split 0.1, early stopping off.

| Target | Zero mass | Steps logged | Step losses | Val MSE | Predictions |
|---|---|---|---|---|---|
| freMTPL2 `ClaimNb` | 94.5% | **2/2** | 1.7072 → 0.5082 | 0.0305 → 0.0308 | 80 rows, finite |
| EU Direct `prem_pure` | — | **2/2** | 0.0714 → 0.0670 | 253.48 | 80 rows, finite |
| AUS Auto `VehValue` | 0% | **2/2** | 0.8995 → 0.6063 | 0.3764 → 0.3681 | 80 rows, finite |
| `log1p(ClaimNb/Exposure)` (the v2 failing transform) | 94.5% | **2/2** | 1.0381 → 0.2881 | — | finite |

`skipped_*` counters do not exist in the new trainer; the equivalent evidence is the step log — one
`log_step` per executed optimiser step, all finite. Fit time on an M-series CPU: 9.6–9.7 s per target
after the model load, 41 s including the first load.

**What this does not prove.** 320 rows is a smoke test, not the pilot's 10,000. It establishes that
the path executes and returns finite predictions on these targets; it says nothing about whether
fine-tuning improves MSE at pilot scale, and it is one seed, one split, CPU only. A GPU run at
10,000 rows is still the measurement that answers the pilot's question.

## What it emits, and whether that passes the gate

`fit(..., output_dir=...)` writes full-weight checkpoints named
`checkpoint_<train_size>_<epoch>.pth` — 699,937,189 bytes each in the probe (2 epochs → 1.4 GB).
The "best" checkpoint is written **only** when early stopping is enabled; with early stopping off the
last epoch is the result and only interval checkpoints are saved (`finetuned_base.py:1273-1303`).
Per-step and per-epoch metrics go to a `FinetuningLogger` (`tabpfn.finetuning.logging`:
`NullLogger` by default, `WandbLogger` optional) — nothing is written to disk unless a logger is
supplied.

Persistence of the *predictor* is not turnkey:

- `save_fitted_tabpfn_model(model.finetuned_inference_regressor_, path)` **raises**. Probe:
  `TypeError: Object of type device is not JSON serializable` (the inference regressor's `device`
  param is a tuple of `torch.device`); after normalising that to `"cpu"`, it raises again on
  `RegressorModelSpecs` (the resolved `model_path`). The helper serialises `get_params()` to JSON
  (`tabpfn/model_loading.py:1161-1200`) and is written for a plain estimator, not for the
  fine-tuner's inference wrapper.
- `joblib.dump(finetuned_regressor)` **works**: 467 MB file, reload reproduced the probe's
  predictions byte-for-byte (`max_abs_diff = 0.0`).

The repository's evidence gate is a `results/<run_id>/capture.json` with an entry per arm × seed
carrying `predictions.npy` / `ground_truth.npy` hashes and a `meta.json` pointer
(`src/run_capture.py:1-60`; enforced by `scripts/check_citations.py`). **The trainer emits nothing of
that shape** — no predictions, no ground truth, no record. The gate is satisfied by the runner, not
by the library: call `predict` once per arm × seed, retain the arrays, and run the capture generator.
Library checkpoints are provenance, not evidence.

## Environment reality (the actual blocker)

Three pins disagree, and the local box cannot run the one the pilot uses:

| Where | Says | Consequence |
|---|---|---|
| `requirements.txt:11` | `tabpfn>=6,<7` | the declared repo pin |
| `requirements.lock:475` | `tabpfn==6.4.1` | what a lock install gives you |
| `docs/REPRODUCIBILITY_RUNBOOK.md:126,571` | `tabpfn==8.5.0` on the GPU box | the version the anchor and the pilot run |
| local `.venv` | `tabpfn 7.0.1`, Python 3.9.6 | `ModelVersion` exposes only `V2, V2_5, V2_6` (`tabpfn/constants.py:31-37`) — **no v3 at all**, and 8.5.0 cannot be installed (`Requires-Python: >=3.10`) |

So: the trainer exists and works, but the machine the repo's own `.venv` describes cannot run it on
`v3_default`. The path that does work is a Python ≥ 3.10 environment with `tabpfn==8.5.0` — which is
what the GPU bootstrap already installs, and what the probe used. No auth is needed for the
checkpoint: `Prior-Labs/tabpfn_3` is public (`gated: false`), the 233,289,807-byte
`tabpfn-v3-regressor-v3_default.ckpt` downloaded without a token, sha256
`311ce18d97e9533d8585eaadafe040fbdd8070533209ed8696641dadc97a7301`.

## If it could not be used: the smallest addition to the hand-rolled loop

Recorded because the ticket asks, though the evidence says it is not the route to take.

The v2 loop is not one patch away from working on 8.5.0 — its three entry points are gone, so
"smallest addition" means porting it back onto `get_preprocessed_dataset_chunks` +
`meta_dataset_collator` + `fit_from_preprocessed`, i.e. re-implementing the shipped trainer. If a
future package change forced a hand-rolled loop again, the four changes that would have prevented the
v2 failure are:

1. **No silent skip.** Replace `continue` on non-finite loss with a recorded, bounded clamp of the
   standardised target and a `nan_to_num` on the loss; a batch that cannot produce a finite loss must
   fail the run, not decrement a counter nobody reads.
2. **`AdamW` + `clip_grad_norm_(1.0)` + LR warmup**, which is what the shipped trainer uses
   (`finetuned_base.py:1130-1190`); the v2 loop used bare `Adam(lr=1e-5)`.
3. **A parameter-delta assertion.** Snapshot `model_.parameters()` before and after and refuse to
   report a run whose weights did not move — the classifier track already learned this the hard way
   (`docs/reference/FINE_TUNING_PILOT_RESULTS.md:240-260`).
4. **Refit inference on the full training frame** before evaluating, instead of evaluating with the
   64-row `context_samples` the v2 loop passed around.

## Method and reproducibility

- Library: `tabpfn==8.5.0` wheel from PyPI (`tabpfn-8.5.0-py3-none-any.whl`, `Requires-Python >=3.10`),
  read directly as source and also executed.
- Probe environment: throwaway `uv venv --python 3.12` with `tabpfn==8.5.0` (CPU, M-series macOS).
  The repo was not modified; probe scripts live outside the tree
  (`regressor_smoke.py`, `regressor_artefacts.py`, `regressor_reload.py` under the session's
  temporary directory; they are probe scripts, not deliverables).
- Data: `data/raw/freMTPL2freq.csv`, `data/raw/eudirectlapse.csv`, `data/raw/ausprivauto0405.csv` —
  the repository's own copies, 400 rows sampled per target, 80/20 train/test.
- Model: `ModelVersion.V3` → `tabpfn-v3-regressor-v3_default.ckpt`, downloaded from
  `Prior-Labs/tabpfn_3` (public) into `~/Library/Caches/tabpfn/`.
- No paid compute, no GPU, no hosted inference, no repository code changed.

## Sources

- `tabpfn` 8.5.0 wheel: modules `tabpfn.finetuning.finetuned_regressor`,
  `tabpfn.finetuning.finetuned_base`, `tabpfn.finetuning.train_util`, `tabpfn.finetuning.data_util`,
  `tabpfn.finetuning.logging`, plus `tabpfn.model_loading` (`model_loading.py`), `tabpfn.constants`
  (`constants.py`) and `tabpfn.regressor` (`regressor.py`).
- Repository: `requirements.txt:11`, `requirements.lock:475`, `docs/REPRODUCIBILITY_RUNBOOK.md:126,571,616`,
  `docs/reference/FINE_TUNING_PILOT_RESULTS.md:240-260`, `docs/archive/STAGE_A_B_FINDINGS_AND_RECOMMENDATIONS.md:117-121`,
  `scripts/legacy_finetuning/run_small_finetune_regressor_trial.py`,
  `scripts/legacy_finetuning/run_finetuned_tabpfn_regression_benchmark.py`, `src/run_capture.py`,
  `scripts/check_citations.py`.
- Local install: `TabPFN-work-scott/.venv` → `tabpfn 7.0.1`, Python 3.9.6.
