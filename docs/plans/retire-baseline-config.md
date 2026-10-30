# Plan — retire `src/baseline_config.py` (#234)

**Status:** Current — issue #234. Follow-up to `docs/plans/experiment-spec.md`.

## Why

`src/baseline_config.py` says it owns experiment configuration, but its values describe
the notebook era (`n_estimators = 8`, a v2-era TabPFN pin) and the pipeline that superseded
it does not read it. Its only code importers are the notebook-era loader and the smoke
tests; four legacy notebooks import three names from it. Keeping it means two answers to
"what seed?" and "where is the data?".

## Accepted source

`src/baseline_utils.py` is the module the notebook-era code already imports for its shared
helpers. It gains:

- `REPO_ROOT = Path(__file__).resolve().parents[1]` — the repo layout, not a hardcoded
  machine path;
- `DATA_DIR = REPO_ROOT / "data" / "raw"` — the same source `scripts/diagnostic_complexity.py`
  and `scripts/run_pilot.py` derive;
- `RANDOM_SEED = 42` — the seed the rest of the suite uses;
- `set_random_seeds()` — the existing helper, unchanged in effect.

The unused `BaselineConfig` wrapper (it required a config module object) is removed with the
module it wrapped.

## What changes

- `src/data_loader_class.py` imports `DATA_DIR` and `RANDOM_SEED` from `baseline_utils`.
- The four notebooks that imported `baseline_config` import the same three names from
  `baseline_utils`; no constant is redefined in a notebook.
- `tests/test_smoke.py` drops `baseline_config` from the import list and deletes the two
  assertions about it. They are removed, not skipped.
- `src/baseline_config.py` is deleted. `README.md`'s layout loses its line.

## Verification

1. `grep -rn "baseline_config" src tests notebooks` returns nothing after the change; the
   only remaining mentions are historical plan/handoff prose.
2. `python -c "from baseline_utils import DATA_DIR, RANDOM_SEED, set_random_seeds"` and
   `DATA_DIR.is_dir()`.
3. `./scripts/check.sh` (ruff, pytest, shellcheck), including the smoke tests.

The notebooks are v2-era and are not executed as part of the gate; the change to their
import line is textual and keeps the same three names available.
