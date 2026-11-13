# The regressor positive control: result

> **Status:** current — control result, 2026-11-10. **Ticket:** #516. **Decision:** #498.
> **Spec:** `REGRESSOR_FINETUNING_PREREGISTRATION_2026-11.md` §"The positive control".
> **Verdict:** **passed** — all three evidence items held on the run recorded in
> `docs/analyses/data/regressor_positive_control.json`.

This is the instrument check that gates the fair test. A null from a pipeline that cannot learn is
uninterpretable, so the control must show evidence that learning happened, not merely that a metric
was produced: the historic AUS Auto arm executed zero steps, left the weights unchanged, and still
"lost" 0.049 R² (#496).

## What the control requires

All three evidence items must hold, from #498:

1. **Parameter delta** — the weights moved between the initial and final model state.
2. **Loss fall** — the training loss fell.
3. **Paired gain** — the fine-tuned arm beats the raw arm on a synthetic target with a known
   low-noise function, on identical rows, with a 95% CI excluding zero.

A failure stops the fair test and reopens the trainer ticket; it does not authorise retuning the
control.

## How it was measured

`src/positive_control.py` drives the shipped `FinetunedTabPFNRegressor` on the pinned v3 line
(`tabpfn==8.5.0`, Python 3.12, `ModelVersion.V3` — resolved by `create_default_for_version`, not
`auto`). Raw and fine-tuned arms see the same training rows and the same test rows.

| Stage | Frame | Epochs | What is asserted |
|---|---|---|---|
| Overfit sanity | `x0*x1 + 0.1·noise`, 256 train / 64 test | 30 (fixed, no early stopping) | `max·|Δw|` over the state dict, and a fall in mean loss (first fifth of steps vs last fifth) |
| Known signal | `sin(6·x0) + 0.5·x1·x2 + 0.02·noise`, 96 train / 256 test | 30 | Paired relative gain `(MSE_raw − MSE_ft)/MSE_raw`, 5 replicates, paired t interval |

The "before" weights come from a zero-epoch fit at the same seed: the trainer creates and
initialises the estimator before the epoch loop, so a zero-epoch run exposes the initial state
without patching the library. The loss trace is the trainer's own `FinetuningLogger` stream — one
`log_step` per executed optimiser step — so the check reads what the trainer did, not a number the
control recomputed.

## Choosing the synthetic target

The target was sized by two free probes, recorded here because the second one changed the design
and nothing else did. The pass rule was fixed before both.

| Probe | Target | Context rows | Raw MSE | Fine-tuned MSE | Relative gain |
|---|---|---|---|---|---|
| 1, seed 0 | `x0*x1 + sin(2π·x2) + 0.1·noise` | 512 | 0.0090 | 0.0101 | −12.0% |
| 1, seed 1 | same | 512 | 0.0098 | 0.0106 | −8.3% |
| 2, seed 0 | `sin(6·x0) + 0.5·x1·x2 + 0.02·noise` | 96 | 0.0028 | 0.0025 | +11.1% |
| 2, seed 1 | same | 96 | 0.0038 | 0.0025 | +33.3% |

**Probe 1 was a broken instrument, not a learning failure.** Raw TabPFN reached MSE 0.009 against a
noise variance of 0.010: it had already solved the task, so no fine-tune could gain, and the only
possible movement was degradation. Probe 2 keeps the noise low but makes raw inference underfit
(high-frequency signal, 96 context rows), which is the regime where a gain is possible at all. The
registered target is probe 2; probe 1 is kept here so the choice is auditable.

## Result

Run of 2026-11-10, CPU, `tabpfn==8.5.0` on Python 3.12.11, **575 s** wall time. The complete record
is `docs/analyses/data/regressor_positive_control.json`.

| Check | Required | Measured | Verdict |
|---|---|---|---|
| Parameter delta | `max·|Δw| > 0` and at least one tensor moved | **1.44e-4**, 502 of 504 tensors moved | pass |
| Loss fall | mean of the last fifth of steps below the first fifth | **0.2452 → 0.2421** (−0.0031) over 30 steps | pass |
| Paired gain | 95% CI lower bound > 0 | **+26.12%**, CI **[+14.11%, +38.12%]**, 5 replicates, df = 4 | pass |

All five replicate gains were positive:

| Replicate seed | Raw MSE | Fine-tuned MSE | Relative gain |
|---|---|---|---|
| 1000 | 0.002602 | 0.002219 | +14.75% |
| 1001 | 0.002069 | 0.001650 | +20.25% |
| 1002 | 0.002800 | 0.001674 | +40.22% |
| 1003 | 0.001800 | 0.001334 | +25.90% |
| 1004 | 0.003729 | 0.002630 | +29.47% |

**Reading the magnitude honestly.** +26% is the gain on a target chosen so that raw inference
underfits; it is not a prediction of the fair test's effect on insurance targets, where the 2% floor
is the question. What the control establishes is narrower and sufficient for its purpose: the
trainer executes steps, those steps move the weights, the training loss falls, and the movement
generalises to held-out rows. A zero-step arm cannot produce this table — which is exactly the
failure the control was built to catch.

**The loss fall is small and should not be overstated.** The per-step loss is noisy because each
epoch re-splits the frame into context and query; the check compares fifths of the trace for that
reason, and the first-to-last single-step pair does not fall monotonically. The parameter delta and
the paired gain are the strong evidence; the loss check is the directional one.

**Limitations.** One machine, CPU only, one target family, five replicates, one model version
(`v3_default`, tabpfn 8.5.0). The control shares the fair test's dose (30 epochs = 30 optimiser
steps at these sizes), which is why a pass here speaks to the dose the fair test will use. It does
not bound GPU behaviour, and it does not test any insurance target.

## What this does and does not authorise

A pass authorises the **benchmark fit** — the first spend — and nothing else. It does not authorise
the fair test: the spec still requires the benchmark estimate to sit inside the \$50 ceiling and a
team decision to release the run. A failure authorises nothing: the fair test does not run, no
verdict is written, and the trainer ticket reopens with this note.

The control says the instrument can learn at 96 rows × 30 epochs. It does not say the effect at
10,000 rows will be the same size, and it does not replace the power argument in the spec.

## Reproduce

Python 3.12 with `tabpfn==8.5.0`:

```
python src/positive_control.py --out docs/analyses/data/regressor_positive_control.json
```

It exits 0 on a pass and 1 on a failure, and writes every parameter it used, the per-step losses,
the per-replicate MSEs and the interval. Unit tests at the library seam:

```
pytest tests/test_positive_control.py -q
```

## Source workbooks

— (a script, not a notebook).

## Evidence files

- `docs/analyses/data/regressor_positive_control.json` — the run's own record.
- `src/positive_control.py` — the runner; `tests/test_positive_control.py` — the pass-rule tests.
- `REGRESSOR_FINETUNING_PREREGISTRATION_2026-11.md` — the rule this checks.
