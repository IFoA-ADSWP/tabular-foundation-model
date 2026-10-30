# Plan — a mock launch's log goes beside its records (#280)

**Status:** Current — issue #280, found while measuring the gate on #239.
**Scope:** one path in `scripts/gpu_helpers/vast_run.sh` (the paid-run path) and its test.

## Why

`vast_run.sh` honours `VAST_OUTDIR` for the launch's record, the ledger and the
returned artifacts, and its own comment states the purpose: *"so a mock/dry run can be
isolated from a real one instead of writing into the working tree (PR-8)"*. `cleanup()`
was the one path that escaped it, fetching the container log into a hardcoded
`$REPO_DIR/outputs/gpu-pilot/logs`.

The consequence is visible on a clean checkout: `pytest tests/ -q` leaves three logs
(the cases that invoke the launcher), because `tests/test_pilot2_mock_run.py` sets
`VAST_OUTDIR` to a tmp dir for everything *except* this. `outputs/gpu-pilot/logs/**`
is un-ignored on purpose — launch logs are kept — so they are indistinguishable from a
real launch's narrative. That is a provenance defect, not clutter: the runbook reads
that directory as the record of what a rented box did.

## What changes

- `cleanup()` uses `LOG_DIR="$OUTDIR/logs"`. The default is unchanged — a real launch
  has no `VAST_OUTDIR`, so it still writes `outputs/gpu-pilot/logs` — and the log stays
  beside `run_<stamp>.json` under the same `RUN_STAMP` name (identifiers ADR 0002
  grandfathers).
- The full-path mock test gains two assertions instead of a third launch: exactly one
  log under the launch's `$OUTDIR/logs`, and the real `outputs/gpu-pilot/logs`
  fingerprinted before and after (path + mtime + size, via `run_artifact_guard`) so a
  same-named rewrite fails too.
- A second test evaluates the launcher's own `OUTDIR` and `LOG_DIR` lines in a subshell:
  with `VAST_OUTDIR` unset the log resolves to `outputs/gpu-pilot/logs`, and with it set
  the override wins. That is the acceptance criterion nothing else would pin.

## Decisions

- **Fix the path, not the test.** Deleting the stray logs or ignoring the directory
  would hide the defect and contradict the deliberate "logs ARE kept" rule.
- **Do not widen `RUN_OUTPUT_ROOTS`.** `tests/run_artifact_guard.py` watches `results/`,
  `predictions/` and `catboost_info/` because nothing legitimate may appear there
  during a test session. A real launch *does* write `outputs/gpu-pilot/logs`, so the
  guard belongs in the mock test's own assertion, where isolation is the property under
  test.
- **No assertion on the `[log] saved …` line.** `len(saved) == 1` proves where the log
  is; matching the human-readable message would only fail on a reword.
- **No third launcher run.** The new assertions join the existing full-path launch,
  which already runs the whole provision-to-destroy cycle.
- **Leave `mkdir -p "$LOG_DIR" 2>/dev/null` alone.** It can blame the box for a local
  permission error, but that shape predates this change, and moving the error path on
  the paid-run side wants its own ticket and a test. This change only changes which
  directory is passed to it.

## Evidence

- Before, on a clean checkout: one `./scripts/check.sh` left three untracked
  `outputs/gpu-pilot/logs/<stamp>.log` files.
- After: the same run leaves `outputs/` clean (`git status --porcelain outputs/` empty).
- Gate, measured on this worktree: **before** the change, exit 0 and 270 passed; **after**
  the change and the merge of `main` (which landed #241), exit 0 and 311 passed. Ruff and
  shellcheck clean in both. `scripts/check.sh` runs three commands; the fourth CI check —
  doc links and doc status — runs inside pytest (`tests/test_check_doc_*.py`), so green
  pytest covers it.
