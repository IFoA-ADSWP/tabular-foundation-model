# Plan — the lease writes its record and reports its release (#325)

**Status:** Current — issue #325, first slice of #324.
**Parent spec:** #324. **Out of scope here:** retry gating (#326), adoption (#327), watchdog (#328).

## Why

`vast_run.sh` has three opinions about teardown: an EXIT trap, a retry path that destroys
with `|| true`, clears the id, and `exec`s, and a watchdog that can only report. A failed
destroy therefore continues on a new instance while the first bills. #325 replaces the
first two with one lease that writes what it did and reports an outcome.

## Interface

`scripts/gpu_helpers/lease.sh`, sourced by the launcher:

- `lease_begin <outdir> <image>` — mint `<utc>-<6 hex>`, write the record in state
  `acquiring` **before** create, set `LEASE_LABEL=tabpfn-pilot-<launch id>`.
- `lease_acquired <instance id>` — state `acquired`, record the id and time.
- `lease_release [reason]` — print and return `released`, `already_gone` or
  `failed:<reason>`. A failure keeps the instance id, writes state `failed`, prints the id
  and a one-line destroy command, and returns 1. A second call may try again; it never
  overwrites the first successful outcome.
- `lease_state` — read the record back for tests and the launcher.

The record is `$OUTDIR/leases/<launch id>.json` (runtime, not committed). Fields: launch
id, instance id, label, image, state, outcome, timestamps, and the run id. Written with
`python3` (already a launcher dependency) via a temp file and atomic rename. `image`, the
timestamps and the run id are written for adoption (#327) and the watchdog (#328), which
are their readers; this slice asserts the state/outcome fields only.

A kill between `create` returning and `lease_acquired` leaves the record in `acquiring`
with no instance id. The label (`tabpfn-pilot-<launch id>`) is the only handle; adoption
(#327) is where that window is closed.

## Launcher wiring

- Mint the launch id before `create instance`; use `LEASE_LABEL` there.
- The leak preflight matches the old exact label **and** the new prefix, so a pre-lease
  instance is still surfaced.
- One EXIT trap calls `lease_release`. A failed release exits non-zero from the trap.
- `retry_or_die` calls `lease_release` first. `failed` refuses the retry; `released`
  clears the id and re-execs as before. `INSTANCE_ID` is cleared only by a confirmed
  release.
- `--keep` does not release; the record stays `acquired` with outcome `kept`, and the
  manual destroy command is printed only when an instance exists. It must not claim
  `released`.
- A successful retry still mints a new launch id: reusing one id across attempts is #326.
  What this slice fixes is that a *failed* release refuses the retry.

## Tests

- **Interface tests** (`tests/test_lease.py`): source `lease.sh` with a mock `vastai` on
  `PATH`; assert record-before-create, released on success, idempotent second call,
  failed-with-reason retaining the id, and failed-then-succeeded on a second call.
- **Guard tests (#256/#271)** stay untouched; the mock-run fixture and teardown test gain
  lease assertions.
- **Mock-driven launch**: the existing `tests/test_pilot2_mock_run.py` path asserts the
  lease record exists before create and ends `released`, and the mock saw one destroy. A
  failed release is tested with **two allowed attempts** so the refusal is what stops the
  retry, not the attempt budget. A fail-once destroy is released by the EXIT trap's second
  attempt, and the record says `released`. The mock gains
  `MOCK_DESTROY_FAIL_ONCE` and records whether the lease file existed at create time.
- **Gate**: `./scripts/check.sh` (now four checks).

## Notes

- No new provider surface: create, list and destroy only.
- No committed evidence changes; lease records are untracked under `outputs/`.
