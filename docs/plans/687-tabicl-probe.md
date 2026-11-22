# Plan — TabICL v2 CPU timing probe (#687)

The access re-check (#685) established that three models install with pip. Installability is not
practicality, and no project publishes a CPU fit or predict time at our row counts.

## What

One measured block in `docs/experiments/tabarena/cpu_model_feasibility.md`: one fold of
`bemtl97_amount`, five context sizes, fit and predict timed separately, peak RSS recorded, and the
three SIGKILLs recorded as outcomes rather than omissions.

## Why

The "one model, many baselines" shape was partly a constraint of access. That constraint is gone but
unmeasured, and an unmeasured constraint becomes an assumption in the next decision. #629 needs a
number, not an adjective.

## Verification

- `./scripts/check.sh doclinks` and `./scripts/check.sh docstatus`.
- Every figure is a console reading from `tabicl` 2.2.0 / `torch` 2.15.0, `device="cpu"`, on this
  8.0 GB machine, with the dataset and drop list named in the note.
- Accuracy is not reported, because no accuracy was measured.

## Out of scope

- TabDPT and TabSTAR timings: the same in-context shape, and the constraint is CPU inference.
- Any comparison of loss.
- Changing the pinned environment; the probe ran in a scratch venv.
