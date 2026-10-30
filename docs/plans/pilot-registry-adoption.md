# Plan — the pilot takes its experiment from the registry (#238)

**Status:** Current — issue #238, sub-issue of spec #236. **Slices 1–2 built** (loader,
committed declaration, pilot CLI); slice 3 (record + launcher) open.
**Related:** `docs/plans/experiment-registry.md` (#230), `record-contract.md` (#241),
`row-size-axis.md` (#264), `docs/adr/0001-…`, `docs/adr/0003-record-contract-and-model-version.md`.

## Why

The pilot defines one experiment in five places:

| site | holds |
|---|---|
| `DEFAULT_CONFIG` | epochs, early stopping, n_estimators, learning rate, fit mode, `context_samples` |
| `RUNG` | P1a/P1b/P1c train/test sizes |
| `TRAIN_SIZE` / `TEST_SIZE` | the CLI's defaults, duplicating P1a |
| `DEFAULT_SEED` / `SEEDS` | the seed, as a one-element list |
| `ARM_EPOCH_OVERRIDES` / `LADDER_ARMS` | the epoch ladder's per-arm budget |
| argparse defaults | the same values a sixth time |

The paid-run launcher then forwards `DATASET`, `TRAIN_SIZE` and `TEST_SIZE` as shell
defaults and never forwards a seed at all. That is why a replication cannot be launched
through the paid path: the launcher cannot omit an argument it never knew about.

## Shape

A **pilot experiment** is its own kind, in a separate table of the same file:

```toml
[pilot_methods.B_ft10]
epochs = 10

[pilot_experiments.coil2000_p1a]
dataset = "coil2000"
arms = ["A_raw", "E_glm", "F_catboost", "B_in_domain", "B_ft3", "B_ft10", "B_ft30"]
seed = 42
folds = 5
train_size = 2000
test_size = 1000
model_version = "v3_default"

[pilot_experiments.coil2000_p1a.config]
epochs = 3
learning_rate = 1e-5
n_estimators = 2
early_stopping = false
fit_mode = "batched"
context_samples = 64
```

`[pilot_methods.<id>]` carries the arm's epoch budget because that is the arm's
hyperparameter; the constructor stays in code, exactly as `[methods.*]` works for the
frontier (#236's reconciliation: the file names an id and its parameters, the code owns
construction).

## Decisions

- **A separate table, not a `kind` field.** A frontier experiment and a pilot experiment
  share a dataset and a model version and nothing else — one table would force every
  reader to branch on a discriminator, and the frontier's closed key set would grow keys
  it must reject. One file, one loader, two experiment kinds is still one language.
- **One seed per experiment**, per #236's amendment. No seed list; a replication is a
  later axis.
- **Contradiction is detected, not resolved.** With `--experiment`, the registry-owned
  flags (`--seeds`, `--rung`, `--train-size`, `--test-size`, `--epochs`,
  `--learning-rate`, `--n-estimators`, `--folds`) default to `None` instead of their
  module constants. A non-`None` value alongside an id fails, naming the id and the flag.
  Without an id, the same flags fall back to the module constants, so every existing
  invocation behaves exactly as it does today.
- **The launcher passes the id and nothing else.** `EXPERIMENT=<id>` replaces the
  `DATASET`/`TRAIN_SIZE`/`TEST_SIZE` triple. The seed never crosses the wire, which is
  the point of the ticket.
- **Declared and resolved are both recorded, and they are distinguishable.** This needs a
  record-contract decision, not a guess: the arm record's `config` is the *resolved*
  value today, and `provenance` (#241) has fixed sections (dataset/split/model/code). The
  options are (a) a new `provenance.experiment = {id, declared, resolved}` and a schema
  bump to 4 with the reader taught the new section, or (b) a top-level `config_declared`
  beside the existing `config`, which is smaller but sits outside the block the record
  contract says is the only structural difference allowed. **This plan does not decide
  it**; slice 3 opens with that fork named, because whichever way it goes changes what
  every reader sees.

## Slices

1. **Registry** — `[pilot_methods]`, `[pilot_experiments]`, dataclasses
   (`PilotMethod`, `PilotExperiment`, `PilotConfig`), fail-closed parsing (dataset ref,
   arm refs, closed config keys, positive sizes, seed/folds ranges, duplicate ids), and
   the committed declaration that reproduces today's default invocation. No pilot change;
   the loader is additive and the frontier cannot see it.
2. **Pilot CLI** — `--experiment <id>`; `None` sentinels for registry-owned flags;
   contradiction refusals naming both; no-id path unchanged. Tests drive `main()` with a
   stubbed arm runner, never a fit.
3. **Record and launcher** — the declared/resolved decision above, then
   `EXPERIMENT=<id>` through `vast_run.sh` and `bootstrap_pilot.sh`. This is the paid-run
   path: shellcheck, and the mock-launch test, before anything else.

## Acceptance map

| criterion | slice |
|---|---|
| accepts an id and runs without a seed/rung/size/config flag | 2 |
| the launcher passes the id, not a seed | 3 |
| resolved configuration recorded and distinguishable from declared intent | 3 |
| id + contradicting flag fails at load, naming both | 2 |
| invocations without an id behave as before | 2 |
| no experiment setting declared only in the pilot module | 2 (+ `RUNG`/`DEFAULT_CONFIG` reduced to fallbacks) |
| four CI checks | each slice |

## Evidence

- Gate measured on this worktree before any edit, and after each slice.
- Slice 1: `pytest tests/test_experiment_spec.py` — the new refusals are named; the
  frontier's existing tests are untouched and still pass.
- Slices 2–3: a stubbed `main()` proves the contradiction refusals; the mock-launch test
  proves the launcher forwards the id and no seed.
