# Plan — frontier classification reads the registry (#231)

**Status:** Current — issue #231; slices 3–4 of `docs/plans/experiment-spec.md`, scoped to
the classification path.
**Glossary:** `GLOSSARY.md` · **ADR:** `docs/adr/0001-experiment-spec-pins-version-and-guards-reuse.md`
**Depends on:** #230 (registry and loader, merged as `f8a5e8c`…`3050792`).

## Why

#230 made the registry the declaration site, but the classification frontier still
decides four things in code:

- the dataset list (`DATASETS`),
- the compared methods (`REUSED_METHODS`, `FAST_METHODS`, and three hand-written loops),
- the metric vocabulary (`metric_fn` silently falls back to log loss), and
- the folds (`StratifiedKFold(..., random_state=SEED)` built inside `run_dataset`).

A registry that the runner does not read is a document beside the code, not a source of
truth. This slice makes the loaded `Experiment` decide all four, so the file and the
evidence cannot disagree about what a dataset or an experiment is.

## What changes

### `src/experiment_spec.py`

- `make_folds(kind, n_folds, seed)` returns one configured splitter. `kind` is
  `"stratified"` or `"kfold"`; an unknown kind raises. The classification frontier and the
  regression frontier both call it, so the same dataset and seed cannot yield two splits
  because two scripts built them.
- The loader is unchanged. Hyperparameters stay in the code-side constructors, per the
  as-built decision in #236: the file names a method id and its parameter-counting rule
  (`n_params`), and the code owns construction.

### `scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py`

- **Method registry.** One ordered table maps each classification method id to its
  constructor, how it produces a probability (direct `predict_proba`, or a regressor's
  mean mapped to a probability), whether its power may be reused from the sweep table, and
  how its parameters are counted. The experiment's `methods` list decides what runs and in
  what order; `tabpfn` is still deferred to last. A method named by the registry but absent
  from the code table fails at selection, naming the method.
- **Metric registry.** A closed `log_loss` / `rmse` / `poisson_deviance` table. A present
  but unknown name raises; an absent name still means log loss for the ad-hoc `--data`
  path that has no experiment.
- **Dataset selection.** A classification run with no `--experiment` and no `--data` builds
  its dataset list from the registry's classification experiments. `--experiment <id>`
  already selected one; it now also supplies the methods and folds. Filenames stay keyed to
  the dataset name, so `{dataset}__seed{s}__*` discovery is unchanged.
- **Folds.** `run_dataset` calls `make_folds("stratified", experiment.n_folds,
  experiment.seed)`. The `experiment.n_folds != N_FOLDS` refusal is removed because the
  count is now honoured. The seed guard stays.
- **Regression path.** It keeps its own dataset list and methods until #232/#235, but its
  inline `KFold(..., random_state=42)` becomes `make_folds("kfold", N_FOLDS, 42)` — the
  same splitter, at the same seed, so behaviour does not move. #232 replaces `42` with the
  experiment's seed and fixes `split_desc`.
- **Compatibility.** `DATASETS` stays as a deprecated constant because
  `run_tuned_baselines.py` imports it until #235. The classification frontier no longer
  reads it.

## Out of scope

- #232 (regression seed), #233 (reuse provenance), #235 (other producers and analysis
  scripts). The regression path keeps its hardcoded 42 and its static method list.
- Re-stamping committed evidence. Only `experiment_id` was added in #230; this slice writes
  the same columns as #230 plus nothing new.

## Verification

1. **Gate.** `./scripts/check.sh` (ruff, pytest, shellcheck). The doc checks are red on
   `main` against a pre-existing backlog; this change must not add to either count.
2. **Row identity.** Run
   `python scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py --experiment coil2000 --out-dir /tmp/issue-231`
   at seed 42 and compare the output with the committed
   `frontier_results_coil2000.csv` on every pre-existing column and row order. The
   `experiment_id` column is new since #230 and is excluded from the comparison.
3. **Adding a method.** A test drives the method planner with an experiment whose list
   differs from the canonical one and asserts the compared set changes without touching
   code. A second test removes one id from the code table and asserts selection fails,
   naming it.
4. **Unknown metric.** A test calls `metric_fn({"metric": "nope"})` and asserts the error
   names the metric. The loader's own rejection is already covered by
   `tests/test_experiment_spec.py`.
5. **Fold identity.** `make_folds` tests assert that two calls with the same kind, count and
   seed produce identical indices, and a different seed produces different indices.

## Evidence

**The refactor changes no computation.** The same command was run against `origin/main`
(the pre-change runner) and against this branch, both in this environment, into separate
output directories. Every shared column is bit-identical: `mean`, `se`, `mean_auc`,
`se_auc`, `mean_brier`, `se_brier`, `n_params`, and `on_frontier` all have
`max|delta| = 0.000e+00`; the column list is unchanged.

**Against the committed evidence.** `--experiment coil2000` at seed 42 reproduces
`frontier_results_coil2000.csv` exactly for five methods — `tabpfn` (−1.1e-16), `cat`,
`lgbm` (−1.1e-16), `xgb`, `rf` — and not for the four `max_iter=500` lbfgs models:
`lr` +1.6e-5, `logisticglm` +9.0e-5, `tweedieglm` −1.9e-4, `poissonglm` +2.3e-3.

That split is the one #230 recorded, with the same order of magnitude: those four hit the
iteration limit, so their result depends on the BLAS/threading of the box that produced the
committed file. The pre-change runner produces the same shifted numbers here, which is why
the bit-identical comparison above, not the committed CSV, is the proof that this slice
moved nothing. The acceptance criterion "reproduces its committed results CSV exactly" is
therefore met for five of nine methods in this environment and cannot be met for the other
four without re-running them where the evidence was produced.

