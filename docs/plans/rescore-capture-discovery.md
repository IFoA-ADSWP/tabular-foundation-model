# Plan — restore capture discovery in the alt-metrics rescore

**Issue:** #123 (metric layer), independent of the architecture work.
**Status:** Proposed.

## What and why

`rescore_altmetrics.load_prediction_store` builds the capture name as
`{dataset}__seed{seed}.npz`, but `run_frontier_benchmark.write_predictions_npz` has written
`{dataset}__seed{seed}__{model_version}.npz` since #186. All four committed captures are therefore
skipped and the script exits 1 with "no datasets captured". #123's rescore has been reading nothing.

The suffix is deliberate — the writer's docstring says it keeps generations side by side so a
version re-test cannot overwrite the baseline it is being diffed against. The reader is the side
that is wrong.

## Decision: discover, do not reconstruct

Rebuilding the name from `_model_path()` would tie the reader to *today's* version, which is
exactly backwards: the rescore exists to score captures produced earlier. So the reader discovers.

- Glob `{dataset}__seed{seed}__*.npz`, read each sibling manifest, filter on the manifest's
  `model_version` (the manifest is the record; the filename is a label derived from it).
- No filter and exactly one capture → use it. This keeps every current call site working.
- No filter and more than one capture → stop with the versions listed and ask for
  `--model-version`. A silent pick among generations is the same class of failure being fixed.
- Capture with no sibling manifest → raise rather than skip; a capture without provenance was
  already a latent hazard.

## Verification

The committed `alt_metrics_per_fold.csv` and `alt_metrics_summary.csv` (2026-09-17) predate the
suffix and are the output of a working reader. Re-running to `--out-dir` in the temp directory and
diffing against them proves the fix restores the previous behaviour exactly, rather than merely
producing rows.

## Out of scope

The `artifacts` module (architecture candidate 2) absorbs this seam properly — one owner for
layout and names, shared by writer, readers and tests. This plan is the bug fix, not that refactor.
