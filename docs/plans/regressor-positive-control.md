# Plan — the regressor positive control

**Issue:** #516 (precondition of the fair test; decision in #498, spec #501).
**Status:** Current — implemented and run; result in `docs/analyses/regressor_positive_control.md`.

## What and why

The pre-registration gates the fair test on a positive control: a pipeline that cannot be shown to
learn cannot produce an interpretable null. The control has to catch the exact failure the historic
record contained — a "fine-tuned" arm that executed zero steps, left the weights untouched, and
still reported a number (#496).

So the control asserts evidence, not a metric: the weights moved, the training loss fell, and a
fine-tuned arm beats the raw arm on a synthetic target with a known low-noise function, paired on
identical rows, with a 95% confidence interval that excludes zero.

This plan covers the runner, its tests and one local execution. It authorises no fair-test run and
no spend.

## Shape

One module, `src/positive_control.py`, with the library behind a small seam so the tests do not
need `tabpfn`:

- `backend` — the only code that imports `tabpfn`. It exposes `fit_raw(...)` and
  `run_finetune(...)`, the second returning predictions, a per-step loss trace and the parameter
  delta between the initial and final model state.
- `run_control(backend, config)` — pure orchestration over the two stages.
- `evaluate(result, config)` — the pass rule, three named checks, each reported separately.
- `main()` — CLI; writes `result.json`, prints the checks, exits 1 when any check fails.

### Stage 1 — overfit sanity

Fine-tune a small synthetic frame (`epochs=30`, one optimiser step per epoch at this size).

- **Parameter delta** — `max |w_after - w_before|` over the model state dict. The "before" state
  comes from a second fit with `epochs=0`; the trainer creates and initialises the estimator
  before the epoch loop, so a zero-epoch run exposes the initial weights at the same seed. This is
  the check that would have caught the AUS Auto arm.
- **Loss fall** — the loss trace comes from the trainer's own `FinetuningLogger` seam (the library
  emits one `log_step` per executed optimiser step). The check compares the mean of the first fifth
  of the steps against the mean of the last fifth; a single step pair is too noisy to pre-register.

### Stage 2 — known-signal target

A low-noise synthetic regression target, replicated `R` times. Each replicate draws its own frame
and seeds both arms identically. For replicate `r`:

```
g_r = (MSE_raw - MSE_ft30) / MSE_raw      # same train rows, same test rows
```

The 95% CI is the paired t interval over the `R` gains with `R-1` degrees of freedom; the check
requires the lower bound to exceed zero. The realised gains, their mean and both bounds are written
to the result.

**The target must leave headroom.** Two free probes sized this stage before the control was
registered. With 512 context rows and `y = x0*x1 + sin(2*pi*x2)`, raw TabPFN reached MSE 0.009
against a noise variance of 0.010 — it had already solved the task, so no fine-tuned arm could
gain, and it lost 8–12%. That is a broken instrument, not a learning failure. The registered
target is high-frequency and low-noise (`sin(6*x0) + 0.5*x1*x2`, noise SD 0.02) at 96 context rows,
where raw underfits: the same probe measured gains of +11% and +33% on two seeds. Both probes are
recorded in the analysis note; the pass rule did not change between them.

`R` is fixed by the budget, not by the outcome: five replicates at `epochs=30`, `n_train=96`,
`n_test=256` measured about 55 s per replicate on CPU, which fits inside 15 minutes.

Everything the run used — sizes, epochs, replicates, seeds, thresholds, device, `tabpfn` version
and wall time — goes in the result JSON, so the record cannot claim a budget it did not run.

## Judgement calls

1. **The unit of pairing is the replicate, not the row.** Per-row squared errors on the same test
   set are not independent, so a t interval over them understates the variance. Resampling the whole
   frame per replicate keeps the interval honest; it is the same choice the fair test makes at fold
   level.
2. **`epochs=0` is the "before" snapshot, not a copy of a fresh estimator.** The trainer seeds
   initialisation from `random_state`, so a zero-epoch fit at the same seed is the same starting
   point, and it costs one model initialisation rather than a library patch.
3. **The trainer's loss trace is read through `FinetuningLogger`, not recomputed.** Recomputing it
   would assert a value the control code itself produced; the seam is a public library protocol.
4. **A control target with no headroom is an invalid instrument, not a failing one.** Raw TabPFN
   already at the noise floor cannot be improved by any fine-tune; the first probe's −8% measured
   the absence of headroom, not the absence of learning. The registered target is chosen for
   headroom, before the control ran, and the probe that rejected the first target is recorded.
5. **A failure is a result.** The runner exits non-zero and writes the evidence; the spec says stop,
   do not run the fair test, and reopen the trainer ticket. It does not say retune the control.

## Verification

- `pytest tests/test_positive_control.py -q` — stubbed backend: zero steps, unmoved weights, a
  rising loss, a CI that includes zero, and the clean pass. **Ran: 10 passed.**
- One real execution in the Python 3.12 / `tabpfn==8.5.0` environment; result committed under
  `docs/analyses/` with wall time. **Ran 2026-11-10: passed in 575 s.**
- `./scripts/check.sh` — the eight-check gate, unchanged by this work.
