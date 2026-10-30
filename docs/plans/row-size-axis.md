# Plan — the row-size axis is declared in the registry (#264)

**Status:** Current — issue #264, a sub-issue of spec #236.
**Related:** `docs/plans/experiment-spec.md` (slice 5), `docs/adr/0001-...`,
`docs/plans/experiment-registry.md` (#230).

## Why

The size sweep's axis — 1 000 rows, 5 000 rows, the full table — lives as a
constant (`SIZES = [1000, 5000, None]`) inside `scripts/benchmarks/run_home_turf_size_sweep.py`.
That is the last axis of an experiment still declared in code: the dataset, methods,
metric, seed and folds moved to `experiments.toml` in #230–#232, and #233 gave the
result rows provenance. A reader can now see what was compared, but not *at which
size*, and a second producer cannot ask "what sizes does this experiment declare?"
without importing a benchmark script.

The registry is where an experiment's identity lives. The axis belongs there too, so a
run states which point it measured and a size that the declaration does not contain is
refused at load, naming the entry — the same fail-closed rule the rest of the schema uses.

## What changes

- `experiments.toml` — `[experiments.<id>]` gains an optional `row_sizes = [...]`.
  Declared for the three datasets the sweep actually varies (`bemtl97`, `coil2000`,
  `uslapseagent`) as `[1000, 5000]`. Every other experiment declares none and is measured
  only at the full dataset.
- `src/experiment_spec.py`
  - parses `row_sizes` (positive integers, no duplicates, refused by name like every other
    field) onto `Experiment.row_sizes`;
  - `Experiment.row_size_points` — the declared sizes plus **full**, or `(None,)` when
    none are declared. Full is always a point: an experiment quoted at its full table is
    not an exception to the axis, and the committed sweep already contains those rows.
  - `resolve_row_size(experiment, requested)` — the `None | int` a run asked for, or a
    `RegistryError` naming the experiment and listing what it declares.
- `src/row_sizes.py` — `slice_data()` moves here from the sweep script, unchanged
  (`train_test_split(train_size=n, stratify=y, random_state=42)`), so the frontier and the
  sweep choose the same rows for the same size. A size that two scripts resolve
  differently is two experiments with one name.
- `run_frontier_benchmark.py` — `--size <full|N>`, validated against the experiment it
  runs (refused with `--data`, which declares nothing). The slice is applied after
  `load_Xy` and before the folds. The point is stamped in the run manifest (`row_size`),
  in every results-CSV row (`n_rows`), and in the capture manifest.
- `run_home_turf_size_sweep.py` — `SIZES` is replaced by each dataset's declared points.
  The script keeps its own dataset list until #235.
- `CHANGELOG.md`, `TASKS.md`, plan.

## Decisions

- **Full is implicit, not declared.** TOML arrays are single-typed, so `"full"` cannot sit
  beside `1000` and `5000`. Treating full as the absence of a cap matches the existing
  `slice_data(None)` and keeps `row_sizes = [1000, 5000]` readable. A declaration of none
  therefore means `(full,)`, not "no sizes".
- **One slicer, imported.** `slice_data` moves to `src/` rather than being copied. The
  sweep and the frontier must agree on which rows `n` means, or the same declared size
  produces two different measurements.
- **`--size` is refused for `--data`.** An ad-hoc CSV has no declaration, so it has no
  axis. Default is `full`, which is what every existing invocation means.
- **The results CSV gains `n_rows`.** #230 already added `experiment_id` to every row for
  the same reason: an artifact that does not state the point it measured cannot be joined
  back to its declaration. Existing columns and row order do not move.
- **The committed sweep table does not change.** Its distinct `(dataset, n_rows)` pairs are
  exactly `1000 / 5000 / <full>` for the three declared experiments, which is what the
  declaration now says.

## Evidence this works

- The gate, measured on this worktree before any edit: `./scripts/check.sh`.
- `pytest tests/test_experiment_spec.py tests/test_frontier_cli.py` — a size outside the
  declaration is refused by name; a declared size reaches the manifest, the CSV and the
  capture; an undeclared `--size` on `--data` is refused.
- The sweep's sizes, read from the registry, equal the committed table's distinct sizes.
