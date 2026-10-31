# Plan — experiment spec

**Status:** Current — agreed 2026-10-28. Slices 1–2 and the `experiment_id` stamping of
slice 4 are implemented in #230 (`docs/plans/experiment-registry.md`); slice 3 and the
classification half of slice 4 are implemented in #231
(`docs/plans/frontier-registry-adoption.md`); the regression half of slice 4 is implemented
in #232 (`docs/plans/regression-seed.md`); slice 5 is implemented in #233
(`docs/plans/reuse-provenance.md`); slice 6, the verification record, remains open.
**Origin:** issue #227 (survey) · issue #210 (the ask) · `docs/plans/experiment-spec-handoff.md` (grilling record)
**Glossary:** `GLOSSARY.md` · **ADR:** `docs/adr/0001-experiment-spec-pins-version-and-guards-reuse.md`

## Why

An experiment is declared in six places in code, and the reuse predicate at
`run_frontier_benchmark.py:469-471` decides from `dataset`, `n_rows` and `n_estimators`
alone — no seed. `--seed 7` can therefore reuse seed-42 rows while refitting others. The
regression path pins folds to `random_state=42` at `:907` while the filename and manifest
both claim the run's seed. Both are hazards to the *evidence*, not to tidiness.

The fix is one committed file that says what an experiment is, and one module that owns
reading it.

## Shape

`experiments.toml` lives in the v1 suite directory, beside the evidence: `schema_version = 1`,
then `[datasets.<name>]`, `[methods.<name>]`, `[experiments.<id>]` tables. Experiments reference
datasets and methods by name. `model_version` is a literal.

`experiment_spec.py` in `src/` — frozen dataclasses, a fail-closed `load_registry(path)`, a shared
`make_folds(kind, n, seed)`, code-side method and metric registries, and a path-free
`evaluate(experiment, predictors, folds, metrics)`.

`run_frontier_benchmark.py` — reads the registry, stamps `experiment_id` into the run
manifest, the capture manifest and the per-row CSV. Output filenames are unchanged, so the
`{dataset}__seed{s}__*` discovery globs in `rescore_altmetrics` and `plot_money_chart` keep
working.

## Slices

Ordered; each is a ticket. `/to-tickets` should encode the blocking links.

1. **Spec file** — generate once from the current `DATASETS` / `REGR_DATASETS` / method
   lists with a throwaway script, hand-commit the TOML, delete the script. Acceptance: the
   file parses and every entry in the generated version is present.
2. **Loader** — dataclasses, fail-closed parsing, `schema_version` refusal, duplicate-id and
   dangling-reference errors. Acceptance: tests cover each rejection path and a valid file.
3. **Registries** — code-side method dispatch (`register("lr", make_lr)`) and the closed
   metric vocabulary. Acceptance: unknown method and unknown metric both raise on load.
4. **Wire the frontier runner** — read the spec, use `make_folds`, stamp `experiment_id`.
   This is where hazard 2 dies: `KFold(random_state=42)` at `:907` becomes `SEED`, and the
   `split_desc` in the capture manifest stops lying.
5. **Reuse guard** — sweep writer gains `seed` and `model_version` columns; the predicate
   requires them to match. The 220 legacy rows become ineligible.
6. **Verification** — re-run `coil2000` at seed 42, diff against the committed
   `frontier_results_coil2000.csv`. Identical rows, recorded in this file.

## Verification

- Gate: the three CI checks (`ruff`, `pytest tests/ -q`, `shellcheck`); the doc link/status checks are not in `ci.yml` yet.
- Behaviour: the `coil2000` diff above. Slice 4 without it is unproven.
- Note: the doc gate is currently red on `main` (49 broken references, 27 unlabelled
  reports). This change must not add to either count, and a "gate green" claim needs those
  numbers addressed or explicitly waived first.

## Out of scope — follow-up tickets

- Migrating the other four producers (`run_tuned_baselines`, `run_reframe_frequency`,
  `run_tabfm`, and the analysis/rescore/plot scripts) — implemented in #235
  (`docs/plans/registry-producers.md`).
- Retiring `src/baseline_config.py`, which serves the notebook-era `data_loader_class` —
  filed as #234.
- Re-stamping or attributing the 220 legacy sweep rows, and the pre-spec CSVs generally.
- The tabarena runners under `scripts/benchmarks/`, which are a different suite.

## Divergence from #210

#210 is `priority: now` and asks for the same pattern **for the fine-tuning pilot**: YAML
under `configs/`, loaded by `run_pilot.py`, with the resolved config recorded in every
record. Its body is pilot-scoped; it is not the parent of these tickets and nothing here
closes it. This suite uses TOML beside its own evidence because it is a different consumer
with a different record shape. Two loaders in one repo is a real cost — revisit if the pilot
loader lands and the duplication looks worth merging.

## Tickets

| Issue | Ticket |
|---|---|
| #230 | Registry, fail-closed loader, experiment id stamped into every artifact |
| #231 | Dataset, methods, metrics and folds read from the registry (classification) |
| #232 | Regression runs honour their seed |
| #233 | Reuse sweep rows only when provenance matches |
| #234 | Retire the notebook-era configuration module (follow-up) |
| #235 | Migrate remaining producers and analysis scripts (follow-up) |
