# Plan — regression runs honour their seed (#232)

**Status:** Current — issue #232; the regression half of slice 4 in
`docs/plans/experiment-spec.md`.
**Glossary:** `GLOSSARY.md` · **Depends on:** #231 (shared fold constructor, merged `e30ddf5`).

## Why

The regression frontier has one self-contradicting artifact. `--seed 7` writes
`frontier_results_<dataset>_seed7.csv`, records `"seed": 7` in the run manifest, and stores
`seed=7` in the capture manifest — but the folds are built with `random_state=42`, and the
capture's `split` string also says 42. Three fields claim one split; the data came from
another. #231 fixed the classification path only.

## What changes

### `run_frontier_benchmark.py`

- `run_dataset_regression(ds, out_csv, out_png, seed=None, n_folds=None)` passes the run's
  seed and fold count to `make_folds("kfold", n_folds, seed)`. The defaults are the
  existing `SEED` / `N_FOLDS`, so an ad-hoc `--data --regression` run is unchanged.
- `main()` forwards the seed and count: `--experiment` uses the declaration's, the
  all-datasets and `--data` paths use the CLI values. The `--experiment` seed guard already
  refuses a CLI seed that disagrees with the declaration.
- `write_predictions_npz` now writes `KFold(..., random_state=<seed>)` in `split`, instead
  of the hardcoded 42. The classification branch already used the passed seed.
- Every remaining `N_FOLDS` use inside the regression path becomes the passed `n_folds`
  (capture, read-back, self-check, plot title).

### Out of scope

- Regression methods still come from the code list, not the experiment (#235), and reuse
  provenance is #233. This ticket changes the split only.

## Verification

1. **Seed-42 does not move.** `make_folds("kfold", 5, 42)` is asserted against a stored
   hash of the pre-change split (captured from the old call site), not re-derived from the
   same constructor. The code path for seed 42 differs from the old one only by passing
   the same value through a parameter.
2. **Seed 7 differs.** The same constructor at seed 7 yields different test indices, and a
   seed-7 run reaches the regression runner with seed 7.
3. **The artifact agrees with itself.** A capture written with `seed=7` has
   `split = "KFold(<n>, shuffle=True, random_state=7)"`; the output filename for a
   `--seed 7` run keeps the `_seed7` suffix.
4. **Gate.** `./scripts/check.sh` (ruff, pytest, shellcheck). Doc checks unchanged.

A full seed-42 regression CSV reproduction is **not** run here: every regression dataset
ends with a hosted TabPFN fit, so the run is a paid call. The committed CSV predates this
change; the equality in (1) is the proof that seed 42 folds identically, and the plan does
not claim a number it did not measure. That reproduction is the user's call, as with #231.
