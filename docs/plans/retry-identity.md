# Plan — a retry is a new attempt under one launch id (#326)

**Status:** Current — issue #326, slice 2 of #324.
**Depends on:** #325 (`docs/plans/lease.md`).

## Why

#325 made a failed release refuse the retry. A successful release still re-execs into a
fresh process that minted a **new** launch id, so two attempts of one launch looked like
two unrelated launches and the record could not show both.

## What changes

- `lease.sh` preserves `LEASE_LAUNCH_ID` and `LEASE_ATTEMPT` from the environment; the
  previous `=""` initialisation wiped them when the retry re-exec sourced the file.
- `lease_begin` reuses the id and record when `LEASE_LAUNCH_ID` names an existing file,
  appending an attempt instead of minting. A new run with no environment value mints as
  before.
- `lease_write` maintains an `attempts` array: each attempt records its number, instance
  id, state, outcome, reason and timestamps. The top-level fields describe the current
  attempt.
- `retry_or_die` exports the same launch id and `LEASE_ATTEMPT+1` before the `exec`.
  `ATTEMPT` still counts total attempts against `--max-attempts`; a release never
  increments either counter.

## Tests

- `tests/test_lease.py`: two `lease_begin` calls under one id produce one record with two
  attempts, ids 111/222, both released.
- `tests/test_pilot2_mock_run.py`: the mock returns a different instance id and a
  per-attempt status; a first attempt that stops is released and re-execs, and the second
  completes. One lease file, one launch id, two attempts and two destroys.
- The failed-release no-retry test still runs with two allowed attempts.

## Out of scope

Adoption (#327), watchdog (#328), and any change to the default attempt count or
exclude-machine behaviour.
