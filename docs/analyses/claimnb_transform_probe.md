# ClaimNb target treatment probe: what runs, and what the trainer actually optimises

> **Status:** task probe, 2026-11-08, for #497. **Question:** which target treatment and loss let the
> v3 regressor fine-tuner execute steps and produce finite, sane predictions on ClaimNb under the
> canonical protocol? **Answer: the canonical raw-count + `log(Exposure)` treatment runs cleanly; but
> the trainer optimises MSE, not Poisson deviance, which is the metric the verdict scores.** CPU only,
> no paid compute.

## Bottom line

All four treatments executed **2/2** fine-tuning steps with finite losses and finite, non-negative
predictions. The v2 zero-step failure does **not** reproduce on `tabpfn==8.5.0` — including the
historic `log1p(claim frequency)` transform that produced zero steps before.

The canonical treatment (raw count, `log(Exposure)` feature) is safe to run. It is **not** a clean
test of the verdict metric: `FinetunedTabPFNRegressor` minimises MSE, and the verdict scores Poisson
deviance. A null on deviance could therefore mean "MSE fine-tuning does not help a zero-inflated
count", not "fine-tuning does not help". The spec must say which claim it is making.

## Probe result

400 sampled rows, 320 train / 80 test, one split (seed 42), 2 epochs, one estimator per arm, CPU.

| treatment | arm | steps | finite | negative preds | last val MSE | Poisson deviance |
|---|---|---|---|---|---|---|
| raw count + `log(Exposure)` **(canonical)** | raw | 0 | yes | 0 | — | 0.5422 |
| raw count + `log(Exposure)` **(canonical)** | fine-tuned | **2/2** | yes | 0 | 0.004031 | **0.4919** |
| raw count + raw `Exposure` | raw | 0 | yes | 0 | — | 0.5271 |
| raw count + raw `Exposure` | fine-tuned | **2/2** | yes | 0 | 0.001822 | 0.4655 |
| `log1p(ClaimNb)` | raw | 0 | yes | 0 | — | 0.5973 |
| `log1p(ClaimNb)` | fine-tuned | **2/2** | yes | 0 | 0.003393 | 0.5087 |
| `log1p(ClaimNb / Exposure)` (historic failing transform) | raw | 0 | yes | 0 | — | 0.5189 |
| `log1p(ClaimNb / Exposure)` (historic failing transform) | fine-tuned | **2/2** | yes | 0 | 0.002683 | 0.4279 |

Every arm produced 80 finite predictions with no negative counts after the inverse transform.

**Do not read the deviance column as an effect.** It is one split of 80 rows, one seed, two epochs.
The canonical arm's training loss rose between epochs (0.7236 → 1.1657) and its validation MSE rose
(0.00203 → 0.00403). The apparent deviance gain is not evidence of learning.

## The loss fact

The shipped regressor trains on **MSE** (`eval_metric: Literal["mse"]`; `_compute_regression_loss`
masks non-finite targets and returns a mean squared error). It exposes no Poisson, Tweedie or
deviance loss. So on the canonical treatment:

- the model fits raw `ClaimNb` by least squares, on a target that is 95% zeros;
- the verdict scores Poisson deviance, which weights small counts differently;
- a null on deviance is therefore ambiguous between "fine-tuning does not generalise" and "the
  training objective is misaligned with the scoring rule".

This is a design constraint, not a probe failure. The spec must state it and choose one of:

1. **Accept the mismatch** and report it: the claim becomes "MSE fine-tuning, scored on deviance".
   Cheapest and closest to what the library actually does.
2. **Align the target to MSE** by using `log1p` or the frequency transform, where squared error is a
   more sensible objective for a zero-heavy count. The historic `log1p(freq)` arm runs on 8.5.0,
   but it is not the canonical registry treatment.
3. **Train on a transformed target and score the canonical deviance**, treating the transform as an
   explicit arm rather than the default.

## Recommendation for the spec

- Use **raw count + `log(Exposure)`** as the canonical treatment; it is the registry protocol and it
  runs.
- Record the **MSE-versus-deviance mismatch** as a limitation of the test, not as a neutral detail.
- Add `log1p` (or `log1p` frequency) as a **pre-registered sensitivity arm**, so a null on the
  canonical arm can be separated from an objective mismatch.
- Do not use the probe's deviance numbers as an effect estimate.

## What this does not prove

- 400 rows, one split, one seed, two epochs, CPU. It establishes that the path executes and returns
  sane predictions; it says nothing about efficacy at pilot scale.
- The 8.5.0 trainer was not compared against a raw arm under a full context. That is the fair test.
- The checkpoint and capture contract are handled in #506; this probe wrote no checkpoints.

## Method and sources

- `tabpfn==8.5.0` in a Python 3.12 venv, CPU, `ModelVersion.V3`, the public
  `tabpfn-v3-regressor-v3_default.ckpt` cached under `~/Library/Caches/tabpfn/`.
- Data: `data/raw/freMTPL2freq.csv`, 400-row sample, seed 42, 80/20 split.
- Probe script and raw `results.json` live in the session's temporary directory
  (`claimnb-probe/probe_small.py`), not in the repository.
- Trainer API and loss: `tabpfn/finetuning/finetuned_regressor.py` (`_compute_regression_loss`,
  `eval_metric`), confirmed in #495.
