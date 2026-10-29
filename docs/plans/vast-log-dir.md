# Plan — the mock run's log goes beside its records (#280)

**Status:** Current — issue #280, found while measuring the gate on #239.
**Scope:** one path in `scripts/gpu_helpers/vast_run.sh` (the paid-run path) and one test.

## Why

`vast_run.sh` honours `VAST_OUTDIR` for the run record, the ledger and the returned
artifacts, and its own comment states the purpose: *"so a mock/dry run can be isolated
from a real one instead of writing into the working tree (PR-8)"*. `cleanup()` was the
one path that escaped it, fetching the container log into a hardcoded
`$REPO_DIR/outputs/gpu-pilot/logs`.

The consequence is visible on a clean checkout: `pytest tests/ -q` leaves three logs
(the three cases that invoke the launcher), because `tests/test_pilot2_mock_run.py`
sets `VAST_OUTDIR` to a tmp dir for everything *except* this. `outputs/gpu-pilot/logs/**`
is un-ignored on purpose — run logs are kept — so they are indistinguishable from a
real run's narrative. That is a provenance defect, not clutter: the runbook reads that
directory as the record of what a rented box did.

## What changes

- `cleanup()` uses `LOG_DIR="$OUTDIR/logs"`. The default is unchanged (a real run has
  no `VAST_OUTDIR`, so it still writes `outputs/gpu-pilot/logs`), and the log stays
  beside `run_<stamp>.json` under the same `RUN_STAMP` name.
- `tests/test_pilot2_mock_run.py` gains one test: after a mock run, exactly one log
  exists under the run's `$OUTDIR/logs`, the launcher names that path, and the real
  `outputs/gpu-pilot/logs` is unchanged. It pins both halves of the contract, so a
  future change that moves the log back into the tree fails here.

## Decisions

- **Fix the path, not the test.** Deleting the stray logs or ignoring the directory
  would hide the defect and contradict the deliberate "logs ARE kept" rule.
- **Do not widen `RUN_OUTPUT_ROOTS`.** `tests/run_artifact_guard.py` watches `results/`,
  `predictions/` and `catboost_info/` because nothing legitimate may appear there
  during a test session. A real run *does* write `outputs/gpu-pilot/logs`, so the guard
  belongs in the mock test's own assertion, where the mock's isolation is the property
  under test.

## Evidence

- Before: a clean worktree plus one `./scripts/check.sh` leaves three untracked
  `outputs/gpu-pilot/logs/<stamp>.log` files.
- After: the same run leaves `outputs/` clean (`git status --porcelain outputs/` empty).
- Gate: `./scripts/check.sh` measured on this worktree before the change (exit 0, 270
  passed, ruff and shellcheck clean) and after.
