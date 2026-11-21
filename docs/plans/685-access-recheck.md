# Plan — refresh the model-access scoping note (#685)

`docs/experiments/tabarena/cpu_model_feasibility.md` is a reference note from 2026-08 whose table
and closing sentence decide whether this programme can compare against any foundation model but
TabPFN. Three of its "GPU required" rows are now false: the packages exist on PyPI.

## What

- Correct the four foundation-model rows the registry evidence covers (`tabicl`, `tabdpt`,
  `tabstar`, `tabfm`), leaving `limix`, `tabswift`, `norp`-family and the rest as they are.
- Add a dated **Access re-check (2026-11-21)** section with the registry versions, dates and the
  projects' own CPU statements, so the correction is auditable rather than asserted.
- Qualify the closing sentence: the hosted-API claim was not re-checked, so it stands as written
  but says so.

## Why

The note's conclusion — TabPFN is the only accessible foundation model — was the premise that made
"one model, many baselines" a choice rather than a constraint. It is still true for hosted APIs and
no longer true for local installation. Leaving it unqualified means the next reader repeats a
2026-08 fact in a 2026-11 decision.

## Verification

- `./scripts/check.sh doclinks` and `./scripts/check.sh docstatus` for the document checks.
- Every version and date in the new table is from the PyPI JSON API read on 2026-11-21; every CPU
  statement is quoted from the project's own README, not inferred.

## Out of scope

- Fit times. Installability is not practicality, and the timing probe is #687.
- Re-checking hosted APIs for the other models.
- Any accuracy claim about any model.
