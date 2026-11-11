# Plan — remaining producers read the registry (#235)

**Status:** Current — issue #235; the last slice of `docs/plans/experiment-spec.md`.
**Glossary:** `GLOSSARY.md` · **Depends on:** #230–#234.

## Why

The frontier reads the registry (#231–#233), but the scripts around it still declare
datasets privately: the tuned-baseline, TabFM and reframe producers, the home-turf sweep,
and the analysis/plot/rescore scripts. Each private list is a second answer to "what is
this dataset" — the exact drift the registry exists to remove.

## Scope

### Registry helper

`src/experiment_spec.py` gains `datasets_by_mode(registry, mode)`,
`load_dataset_entries(path, mode)`, `dataset_entry(dataset)` and
`mode_methods(registry, mode)`. The last refuses two experiments of one mode declaring
different method lists, so a producer that is not itself an experiment cannot pick an
arbitrary anchor and drift from the run it analyses. Ordering is the registry's declared
order, so filenames and loops keep their current order.

### Producers

| Script | Change |
|---|---|
| `run_tuned_baselines.py` | Dataset entries from the registry's classification Datasets, not `DATASETS` from the frontier. |
| `run_tabfm.py` | Same; its `ALLOWED` set stays a selection of registry names. |
| `run_reframe_frequency.py` | The `spanish_motor_freq` entry comes from the registry, not `REG_DATASETS`. Its binary method list is derived from a classification experiment's methods; the ordinal list is a recorded subset. |
| `scripts/benchmarks/run_home_turf_size_sweep.py` | The three datasets are selected by name from the registry; their target/drop/file no longer live here. |
| `scripts/benchmarks/finish_home_turf_sweep_v2.py` | Shares the sweep's dataset entries and its declared size axis; the duplicated `SIZES` list is gone. |

### Analysis, plot and rescore

| Script | Change |
|---|---|
| `analyze_pr_auc.py` | Classification dataset names from the registry; `SEED_DATASETS` stays a study selection. |
| `analyze_tuned_baselines.py` | Classification dataset names from the registry. |
| `plot_money_chart.py` | The dataset → file map comes from registry Datasets; label offsets stay presentation. |
| `rescore_altmetrics.py` | The regression dataset set comes from the registry; the scale/metric config stays keyed by name and must cover exactly that set. `METHODS` is derived from a regression experiment's methods. |

### Frontier cleanup

`run_frontier_benchmark.py` loses `DATASETS` and `REG_DATASETS`; both modes select from the
registry. `tests/test_experiment_spec.py` loses the temporary constants-comparison test that
#230 added as a bridge.

### Deliberately out of scope

- **Method studies that are not experiments.** The tuned variants (`lr_tuned`, `glm_eng`,
  `lgbm_tuned`, `cat_tuned`, `rf_tuned`), `tabfm`, and the ordinal reframe subset are not
  methods an Experiment compares; declaring them in the registry would add ids that no
  experiment references and no code-side constructor builds. Their method lists stay local
  and are recorded here.
- `rescore_focused_imbalance_logloss.py` reads pilot/v1 **cache ids** (`coil2000-<hash>`),
  not Datasets.
- The tabarena runners under `scripts/benchmarks/`, as #230's plan already recorded.

## Verification

1. **Metadata equivalence.** A stored `EXPECTED` map pins every registry Dataset's
   file/target/drop/metric/transform to the values the scripts used before this change,
   and the tests pin each script's dataset and method selection (not re-derived from the
   registry). Coverage also asserts one experiment per Dataset, one method list per mode,
   and the runner's 5-fold / seed-42 defaults.
2. **No private lists.** `grep` for the removed constants and for `target=`/`"drop"` literals
   in the migrated scripts returns nothing.
3. **Seed-42 outputs unchanged.** No computation changes: the entries are the same values,
   in the same order. The paid producers are not re-run; the equivalence test is the proof.
4. **Gate.** `./scripts/check.sh`.
