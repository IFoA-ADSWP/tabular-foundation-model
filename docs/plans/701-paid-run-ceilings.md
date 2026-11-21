# Plan — #701: the paid-run path measures its own ceilings

**Status:** Current — issue #701, with #433 (a stall releases the box).
**Scope:** the launcher's poll window, the fair-test frame estimate, and the re-emit's ceiling.

## Why

A launch on 2026-11-21 spent **$1.86** billing past its own poll window, and every completion
estimate made from the launcher was wrong by a large margin. Three independent measurements:

| Claim the launcher made | What was true |
| --- | --- |
| `--poll-minutes 210` | 630 polls × ~13.5 s = **142 min** |
| the frame is `arms × seeds` | `folds × seeds × arms` = **5 × 20 × 4 = 400 fits**, each with three estimator passes |
| a capture transfers in ~18 min | **182 chunks**, 20 s apart, two copies, two passes ≈ **2 h** for one pass |

A fourth failure was operational: a `git clone` hung for **28 minutes**, and the launch's own
checkout was pruned mid-run so every merge failed with `No such file` for ten minutes while the box
billed.

## What changes

- **The ceiling is a duration.** The poll loop ends on elapsed seconds (`TFM_POLL_DEADLINE_SECS`
  overrides it for tests and canaries) and prints the deadline it will honour.
- **The spend gate counts the fits.** For `--fairtest primary` it prints
  `targets × arms × seeds × folds = N fits`, projects `N × 45 s` of fits and a transfer term, and
  refuses a ceiling below the total. Folds default to the runner's 5 because the bootstrap never
  passes `--folds`. The 45 s constant is measured: 400 fits in 4 h 26 m.
- **#433: a box that stops advancing is released.** Two bounds, because the failures differ: the
  bootstrap bound (no marker within `BOOT_MINUTES`, default 30) covers a hung clone, and the stall
  bound (no new log bytes for `STALL_MINUTES`, default 15, measured from the first marker) covers a
  run that stops. Both release rather than keep, because there is no capture to keep; the log and
  reason are recorded.
- **A vanished checkout refuses.** Before each merge the launcher checks that its own helper
  scripts still exist. A launch whose checkout is pruned now stops loudly instead of polling on.
- **The re-emit sizes its own ceiling** from `chunks=N` in the box's `__ARTIFACTS_INFO__` line,
  through `transfer_minutes.py`, instead of from the target count.

## Decisions

- **Release, do not keep, an aborted launch.** A stalled or hung box has no capture; keeping it
  bills for nothing. This is the opposite of the verification-failure path, which keeps the box
  because the fits are on it.
- **The bootstrap bound exists because #433 excludes bootstrapping.** #433 measures idleness from
  the first arm marker so a slow image pull is not a stall. That leaves a clone that hangs with no
  marker at all — the failure measured here — so a separate bound covers the window before the
  first marker.
- **A measured constant, not a guess.** 45 s per fit comes from 400 fits in 4 h 26 m on an A100 at
  10,000 rows. It is a starting point for the gate, not a promise; `TFM_SEC_PER_FIT` overrides it.
- **The transfer is paced, so it is counted in chunks.** `transfer_minutes.py` is the single
  definition, used by the re-emit driver and tested directly.

## Not in scope

- The emitter still prints `__ARTIFACTS_INFO__` once, at the head of the payload. A poller that
  attaches after the head has scrolled cannot reconstruct the declaration. That is a transport
  change for its own ticket.
- The launcher still polls the container log; #432's progress tool may absorb the reporting.

## Verification

```bash
.venv/bin/pytest tests/test_launch_ceilings.py -q
.venv/bin/pytest tests/test_fairtest_capture_launch.py tests/test_pilot2_seed_passthrough.py -q
./scripts/check.sh
```
