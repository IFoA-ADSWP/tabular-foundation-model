# Plan — experiment registry (#230)

**Status:** Current — agreed 2026-10-28, implementing.
**Origin:** issue #230, slice 1–2 of `docs/plans/experiment-spec.md` (plus the
`experiment_id` stamping from slice 4).
**Glossary:** `GLOSSARY.md` · **ADR:** `docs/adr/0001-experiment-spec-pins-version-and-guards-reuse.md`

## Scope

#230 is the declaration and its reader. It adds:

1. `scripts/eval/insurance_benchmark_v1/experiments.toml` — every dataset, method and
   experiment the frontier runner uses, generated from the current constants.
2. `src/experiment_spec.py` — frozen dataclasses and a fail-closed `load_registry(path)`.
3. `--experiment <id>` on the frontier runner, and `experiment_id` stamped into the run
   manifest, the capture manifest and every results-CSV row.

It deliberately does **not** do the work of #231 (methods, metrics and folds dispatched
from the experiment), #232 (regression seeds), #233 (reuse provenance) or #235 (the other
producers). The runner still computes exactly what it computed before; only its *input
selection* and its *provenance stamping* move.

`experiment_id` is a new column in the results CSV. "Row-identical to the committed one"
therefore means: every pre-existing column keeps its value and row order. It cannot mean
byte-identical, because the ticket also requires each row to state the id.

## Shape

`[datasets.<name>]` — `file`, `target`, `drop`, `metric`, optional `transform`.
`[methods.classification.<id>]` / `[methods.regression.<id>]` — `n_params`.
`[experiments.<id>]` — `dataset`, `methods`, `n_folds`, `seed`, `model_version`.

Two decisions worth stating:

- **Methods are namespaced by mode.** The runner reports `poissonglm`, `tweedieglm`,
  `rf`, `cat`, `lgbm` and `xgb` in *both* modes, constructed by different functions
  (`make_poissonglm` vs `make_poissonglm_reg`). A flat method table cannot hold both
  without inventing ids, and inventing ids would change the CSVs. Method names resolve
  inside the experiment's own mode.
- **The metric lives on the dataset, not the experiment.** `GLOSSARY.md` defines a
  dataset as "a named table plus its target, its leak-drops and the metric applied to
  it". Declaring it twice would create two sources of truth for one fact. The experiment
  derives its mode from the dataset's metric (`log_loss` → classification,
  `rmse`/`poisson_deviance` → regression), which is already how `metric_fn` dispatches.

### Hyperparameters are not in the file yet

The handoff settled that the file names "an id and hyperparameters". The as-built
decision (#236) keeps hyperparameters in the code-side constructors instead:
`make_logisticglm()` passes `penalty=None` deliberately, TOML has no null, and a declared
value the code cannot honour is worse than no declaration. So this ticket declares which
method, in which mode, counted by which rule; #231 reads that declaration and builds the
method from code.

### What is deliberately not stamped

The append-only `frontier_pr_auc_results.csv` ledger is a cross-run table, not a per-run
artifact: appending a new column to a file that already has rows without it would corrupt
it. The per-run CSV, the run manifest and the capture manifest are stamped.

The pinned `model_version` is **declared, not enforced**. A run still resolves its model
through `TABPFN_MODEL_PATH`, exactly as before; #233 is where reuse becomes conditional on
the pin. Because ADR 0001 promises that each run's manifest records the value actually used,
`write_manifest` now records it — otherwise the pin would be unverifiable and the ADR's
mitigation would not exist. It records `model_version_scope` beside it, because the reuse
path still takes sweep rows whose provenance is unattested: the resolved version is
attested for every fresh fit and merely *assumed* for a reused row. ADR 0001's paired
consequence — "the first post-spec run refits every method once" — is #233's, and the scope
field says so rather than letting the manifest imply a guarantee it lacks.

### The seed and fold count are part of the experiment's identity

`--experiment <id>` refuses a `--seed` that disagrees with the experiment's declared seed,
and refuses an experiment whose declared `n_folds` differs from what this runner folds.
Stamping `coil2000` on a seed-7 run, or on a 10-fold run, would produce an artifact that
contradicts the declaration it cites — precisely the failure class this registry exists to
prevent. Today both checks are vacuous for the committed file (every experiment declares
seed 42 and 5 folds), which is the point: they stop the file and the runner drifting apart
before the drift can be stamped. Seed sweeps remain available ad hoc (positional dataset
filters, no `--experiment`), where they are honestly unstamped.

The seed guard is only as sound as the producer honours the seed. Classification folds do
(`StratifiedKFold(random_state=SEED)`); regression folds still do not (`KFold(...,
random_state=42)`), so a regression experiment declared at a non-42 seed would pass the
guard and then fold at 42. #232 closes that. Declaring one now would be a lie the guard
could not catch, which is why the registry declares seed 42 for all twelve.

## Generation

The TOML is produced once by a throwaway script (kept out of the tree) that imports the
runner and reads `DATASETS`, `REG_DATASETS`, `N_FOLDS`, `SEED` and the `make_*`
constructors' literal keyword arguments via `ast`. `test_experiment_spec.py` then asserts
the committed file agrees with the code constants, so "generated rather than retyped" is
checked on every run rather than asserted in prose. That test is deliberately temporary:
#231 deletes the constants, and the test goes with them.

## Fail-closed rules

Each rejection names the offending entry and the file:

| Input | Error |
|---|---|
| unparseable TOML (incl. a duplicate id) | decode message, which names the duplicated key |
| `schema_version` missing or not `1` | names the version found |
| unknown top-level key / section | names the key |
| unknown or missing key in an entry | names the entry and the key |
| wrong type | names the entry and the key |
| dataset `metric` outside the closed vocabulary | names the metric |
| method `n_params` outside `glm`/`trees`/`tabpfn` | names the rule |
| experiment referencing a missing dataset or method | names the reference and the experiment |
| experiment method whose mode disagrees with the dataset's metric | names both |
| duplicate method in one experiment's list | names it |
| `n_folds < 2`, negative `seed`, empty `model_version` | names the field |
| a section that is not a table | names the section |
| `schema_version = true` (a bool is not version 1) | names the field |

## Verification

- Gate, measured after the change: `ruff` findings **identical** to `origin/main` (64, no new,
  none fixed); `pytest tests/ -q` **238 passed, 2 failed** — the same two pre-existing
  `test_pilot2_mock_run.py` failures, which assert the commit is an ancestor of
  `origin/main` and so cannot pass on an unpushed branch; 48 tests added; shellcheck clean;
  doc links 49 broken over 79 documents (was 78 — the new plan file resolves), doc status
  11 of 38 unchanged.
- Behaviour, the claim that matters: the same command run against the pre-change tree
  (`git archive HEAD`) and against this change produces **bit-identical CSV values** on all
  nine pre-existing columns (`assert_frame_equal(check_exact=True)`), differing only by the
  new `experiment_id` column. That is the ticket's own proof — "this ticket changes no
  computation".
- Behaviour, against the committed evidence: `run_frontier_benchmark.py --experiment
  coil2000 --seed 42` reproduces `frontier_results_coil2000.csv` exactly for the five
  methods that are either reused from the sweep or converge deterministically
  (tabpfn/cat/lgbm/xgb ≤1.1e-16, rf 0), but **not** for the four `max_iter=500` lbfgs
  models (lr 7e-5, logisticglm 1e-4, tweedieglm 9e-4, poissonglm 2.3e-3). This is
  pre-existing and environmental, not caused by the registry: the pre-change tree produces
  the same shifted numbers in this environment. Those four models hit the iteration limit
  (`ConvergenceWarning`), so their result depends on the BLAS/threading of the box that ran
  them, and the committed CSV came from a different one. The acceptance criterion "row-identical
  to the committed one" is therefore met for five of nine methods here and cannot be met for
  the other four without re-running them in the environment that produced the evidence. The
  run is cheap and hosted-free: it reuses all four power methods from the sweep table.
- The committed evidence CSVs are **not** regenerated. They are evidence produced before
  the registry existed, and the code cannot reproduce their `--pr-auc` columns without a
  paid hosted run; rewriting them in non-`--pr-auc` mode would destroy those columns.
  Forward-only, like the pre-spec sweep rows.
- Not verified: a byte-exact reproduction of the *whole* committed CSV including its
  `mean_pr_auc`/`mean_lift10` columns, which requires `--pr-auc` and therefore fresh
  hosted TabPFN fits on 9,822 rows. That is a paid call; it is the user's decision, and
  it is recorded as an open item rather than claimed.

## Gate state at the start of this work

Three of the four checks are already red on `origin/main`, independently of this change:

- `ruff check scripts/ src/ tests/` — 64 errors, no `pyproject.toml`/`ruff.toml` in the
  repo, so ruff's defaults decide. Reproduced on a clean `git archive` of `origin/main`.
- `scripts/check_doc_links.py` — 49 broken references.
- `scripts/check_doc_status.py` — 11 of 38 reports state a status.
- `pytest tests/ -q` — 190 passed, 2 failed in `test_pilot2_mock_run.py`; both assert the
  commit is an ancestor of `origin/main`, which no unpushed branch can satisfy.

This change adds to none of those counts, and the plan does not claim a green gate it
cannot show.
