# Plan — row curve, stage 1 (#697)

#629's second direction: find the row count where the cheap model stops being worse, before
spending on a matched TabPFN capture.

## What

- `docs/experiments/frontier-benchmark/row_curve_stage1.md` — the analysis, with a table generated
  from the CSV and a resolvability column.
- `scripts/analyses/row_curve_stage1.csv` — 36 cells: target × budget × method, with SD, n and MDE.
- Twelve `results/<run id>/capture.json` manifests, one per budget × target, plus their index rows.

## Why

The adoption rule says TabPFN wins at ≤5K rows; it never said where the baselines are competitive.
Without this, stage 2 could spend a rented run comparing against a baseline that cannot be separated
from a null model at the same budget.

## Verification

- Runs came from `scripts/run_fair_test.py --methods E_glm,F_catboost,M_intercept --device cpu`,
  the command #629 specified; $0, no rented machine.
- MDE is computed from each cell's own fold/seed SD at 80% power, and the table marks the five cells
  whose margin does not clear it.
- `./scripts/check.sh doclinks`, `docstatus`; the PR carries `evidence-change` because `results/`
  gains twelve directories.

## Out of scope

- Any TabPFN number. Stage 2 is a separate ticket, gated on a cell where the gap is plausibly live.
- The 113 MB prediction payload: only the capture manifests are committed, and #584 owns the
  payload-size question.
