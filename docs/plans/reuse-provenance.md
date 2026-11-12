# Plan — reuse a sweep row only when its provenance matches (#233)

**Status:** Current — issue #233; slice 5 of `docs/plans/experiment-spec.md`.
**Glossary:** `GLOSSARY.md` (*Reuse*, *Provenance*) · **ADR:** `docs/adr/0001-experiment-spec-pins-version-and-guards-reuse.md`
**Depends on:** #231 and #232 (the registry now supplies the run's split).

## Why

The classification frontier builds its "reused" power rows from
`home_turf_sweep_results.csv` by selecting on dataset, row count and an empty
`n_estimators`. Seed and model version are not in that predicate — and until now they were
not in the table either. So a `--seed 7` frontier can take a seed-42 fold row, and a run
under a different TabPFN version can take a row produced under another. The artifact's
provenance then contradicts the number, which `GLOSSARY.md` calls a bug in the artifact.

## What changes

### `scripts/benchmarks/run_home_turf_size_sweep.py`

- A `SPLIT_SEED = 42` constant beside `N_FOLDS`, used for the sweep's `StratifiedKFold`.
- Every row carries `seed = SPLIT_SEED` and `model_version = _model_path()`, the version
  actually used for that row. The row builder is a small `sweep_row(...)` function so a
  test can call it without fitting anything.

### `run_frontier_benchmark.py`

- `reusable_sweep_rows(sweep, dataset, n_rows, n_folds, seed, model_version)` is the one
  predicate. It requires the provenance columns to exist and to equal the run's seed and
  resolved model version. A table without those columns — the committed 220 rows — yields
  no rows and is therefore never reused.
- `run_dataset` uses it instead of the ad-hoc filter. A row is reused only when the
  predicate returned it **and** the method has `n_folds` rows.
- The run manifest records the power source per dataset:
  `"power": {"<dataset>": {"reused": [...], "fresh": [...]}}`. Regression records all
  methods as fresh (it never reuses the classification sweep).

### Behaviour change to expect

The committed sweep table has no provenance columns, and the frontier only **reads** it:
fresh fits go to `frontier_results_*.csv`, never back into the sweep table. So until
`run_home_turf_size_sweep.py` is re-run — a paid hosted sweep over 3 datasets × 3 sizes ×
5 folds — every frontier run refits everything, including the hosted TabPFN rows. Reuse
resumes only after that sweep writes attributable rows. The first frontier run does not
create them, and this plan does not claim otherwise.

The version check uses the **experiment's declared** `model_version`, not the value the
environment resolved, and requires the two to agree: #239 records `model_version_mismatch`,
and #233 refuses reuse unless it is exactly false. A run whose resolved version drifts from
the declaration refits and records both values; an ad-hoc run declares nothing, so it
reuses nothing — absence is not a pass. CPU rows carry
the same version stamp, so a TabPFN bump also invalidates them; that is strict on purpose,
and the cost is a refit.

## Verification

1. **Predicate tests, no fitting:** a table with the columns and a matching seed/version
   returns rows; a seed mismatch, a version mismatch, or a table missing the columns
   returns none.
2. **Writer test:** `sweep_row(...)` carries the seed and the resolved model version.
3. **Manifest test:** `write_manifest` writes `power: null` first and the per-dataset
   `reused`/`fresh` split after it is populated, so the after-each-dataset rewrite is
   exercised rather than assumed.
4. **Gate:** `./scripts/check.sh`.

The "second run reuses rows" criterion is proved at the predicate and manifest seams. A
real second run is not performed here: with the committed table unprovenanced the first run
is a paid TabPFN refit, and that spend is the user's decision. The plan records the
limitation rather than claiming a run that did not happen.

## Out of scope

- #235 migrates the other producers. This ticket changes the sweep writer and the frontier
  reuse path only.
- Re-stamping the 220 legacy rows: forward-only, as ADR 0001 says.
