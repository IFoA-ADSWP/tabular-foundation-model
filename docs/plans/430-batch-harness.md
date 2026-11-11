# Plan — a self-healing batch harness: the missing set is the queue (#430)

**Status:** Current — 2026-11-06. **Issue:** #430 (a child of the paid-run hardening tracking
issue #428). **Branch:** `feat/430-batch-harness` from `origin/main` @ `f6bd471`. **Scope:**
one new launcher wrapper, one new banked-set reader, one shared fit guard (extracted from
`vast_run.sh`, not rewritten), one test module, one runbook/CHANGELOG update. No launch, no
spend.

## What happened

The 2026-11-04/05 campaign drove a **fixed queue**: batch 1..16 in order. When a batch died the
queue moved on, so the range was never measured; when a batch wrote another range's seeds the
queue also moved on, and the range it *thought* it had covered stayed missing. Both were
invisible until someone diffed the run directories against the design. A quarter of the spend
bought nothing, and the last stretch only converged because of an ad-hoc `/tmp` loop that
recomputed the missing set each pass.

## What changes

`scripts/gpu_helpers/batch_run.sh START END BATCH_SIZE --dataset NAME[,NAME] --arms LIST
[--max-passes N] [--poll-minutes M] [--estimate-sec-per-seed S] [--train-size N] [--test-size N]
[--launcher PATH] [--runs-dir DIR] [--parallel N] [--notify CMD] [--notify-macos]
[--notify-log FILE] [-- LAUNCHER_ARGS...]`

```text
for pass in 1..max-passes:
  missing := seeds in [start,end] not banked for EVERY (dataset, arm) pair
  if missing = ∅                       → announce COMPLETE, exit 0
  for each dataset: split its missing seeds into batches of BATCH_SIZE, launch them
  if the pass banked nothing twice running → announce STALL, exit 4
print missing                          → announce STOP, exit 3
```

**The missing set is the queue.** There is no plan to drift from: a range a dead batch failed
to produce is still missing on the next pass and comes back automatically, and a duplicated
range cannot happen because "already on disk" is the exit condition.

## The decisions worth arguing

### 1. The design is passed in, not guessed

`--dataset` and `--arms` are required. Completeness per arm is the issue's own wording ("which
seeds lack both arms"), and a harness that infers the pair set from what is already on disk
would report `COMPLETE` over a range it has never launched — the exact failure this ticket
exists to remove. A missing `--dataset` on an empty tree has no honest default: the launcher's
default is "every registered dataset", which lives in `run_pilot.py`, not in a place a bash
wrapper should reach for.

Both values are **passed verbatim to every launch**, so the harness's notion of a complete
seed and the launcher's notion of what it will write are the same list by construction.

### 2. One launch per dataset

`--dataset a,b` means one launch per dataset, not one launch with a comma list. `vast_run.sh`
runs **one** dataset; handing it `a,b` makes `run_pilot.py` print `Unknown dataset 'a,b'` and
return nothing *after the box is paid for*, and because an absent payload is only a warning the
launch still exits 0. A queue that quietly bought boots which measured nothing would be this
ticket's failure wearing a disguise, so the split happens here.

### 3. Banked means a `meta.json` says so, read by #429's own reader

`banked_seeds.py` imports `written_seeds`, `parse_seeds` and `seed_ranges` from
`verify_artifacts.py` rather than re-walking `runs/`. The verifier already defines what
"written" means per `(dataset, arm)` and already treats a string seed as that seed; a second
implementation would be a second definition, and #429 exists because the count and the range
are different questions. The reader is a CLI so #432 (`watch_run.sh --plan`) can report the
same numbers instead of inventing them again.

**Which launches count is decided by the launch, not the file.** Each run directory holds the
manifest the box wrote (`manifest_<run_id>.json`, returned by `emit_artifacts.sh`), and:

- `dry_run: true` → skipped. A mock costs nothing, so it measured nothing; counting it would
  let a smoke test report COMPLETE over a range nobody ran. (`meta.json` carries no such field,
  and neither does the launcher's own cost record — the manifest is the only place it is
  written.)
- `--train-size` / `--test-size`, when given, must match the manifest. The campaign scans
  2,000 → 10,000 rows by design, and a seed measured at one size must not retire the other.
- A launch with no manifest is counted when no size was asked for (every run from before the
  manifest was returned) and skipped when one was (nothing to attest).

**The limit, stated.** The model line, the commit and the config are not compared. So
`--runs-dir` must point at the campaign's own tree: the reader answers "what have I banked
here", not "is this evidence commensurable with today's run". The docstring says so too.

### 4. The size guard is extracted, not duplicated

Rule 1 of the runbook says a batch is sized from a measured per-seed time and a startup
allowance, and `vast_run.sh` refuses a batch that does not fit its poll window. The harness
needs the same arithmetic *before* it spends, so `fit_guard.sh` carries the sum, the capacity
and the refusal text; `vast_run.sh` sources it (its output is unchanged) and `batch_run.sh`
refuses a `BATCH_SIZE` above capacity with the same message. One definition, two callers.
`batch_run.sh` passes `--poll-minutes` and `--estimate-sec-per-seed` explicitly on every
launch, so the guard it applied is exactly the guard the launcher applies. A zero estimate is
refused in both, because `0` silently disables the guard while looking applied.

### 5. Announcements are one line to a log, and optionally a human

The ticket's second acceptance box asked for a harness that interrupts a human on completion,
failure and stall instead of needing to be polled. Every terminal event writes one line to
`$VAST_OUTDIR/batch_notifications.log` (always) and, when `--notify CMD` or `--notify-macos`
is given, to that too. A file is the default because it is the only sink that works on any
host and in CI; `--notify-macos` exists because the harness runs on the operator's laptop, and
`--notify CMD` covers a webhook without a config format. It cannot announce its *own* death
(SIGKILL, a sleeping laptop) — that is #433's box-side guard.

## Failure taxonomy — which failure stops the set, and which is just missing

| Event | Launcher rc | Harness behaviour |
| --- | --- | --- |
| Batch banks its seeds | 0 | continue |
| Batch dies (provider, OOM, poll overrun, seeds refused, no payload, all arms dead) | 0 or non-zero ≠2 | that range is still missing; the next pass retries it. rc 0 is why the harness recomputes instead of trusting it |
| Launcher exits 2 | 2 | **stop the queue**: either a free pre-flight refusal (poll window, dirty tree, no offer, #423's leak prompt) or a release/retry failure that may still be billing. Both repeat identically and both want a human; the launcher's output says which |
| Two passes in a row bank nothing | — | **stop** (STALL): the harness will not keep renting for a set that is not moving. One empty pass is not a stall — it is the retry the issue asks for |
| `--parallel` > 1 | — | **refuse** before anything is launched: #431 is the test that two launchers do not collide, and it does not exist yet (runbook rule 4) |
| A `--` argument tries to replace the batch | — | the harness's own `--seeds`/`--dataset`/window are last on the command line, and the launcher is last-wins |

Rule 12's "a failure that looks healthy stops the set" is met two ways: #429 turns the
healthy-looking seed mismatch into a non-zero exit, and the recompute means a launch that exits
0 without banking anything is not mistaken for success.

## Exit codes

```
0  COMPLETE — every seed in [start,end] banked for every (dataset, arm)
2  usage error, or a refusal (parallel > 1, batch larger than the poll window admits, or the
   launcher exiting 2 — a free refusal or an unconfirmed release)
3  the pass limit was reached with seeds still missing — they are printed
4  stopped: two consecutive passes banked nothing (STALL)
```

## Seams (named before the tests)

1. **`banked_seeds.py` over a runs tree** — the missing set, per `(dataset, arm)`, with
   dry-run and wrong-size launches excluded. Catches a seed banked on one arm and absent on
   the other, and a mock or differently-sized tree standing in for the design; misses whether
   the metas came from the launch that was asked for (that is #429's, and the recompute).
2. **`batch_run.sh` with a recording test-double launcher** — the batch plan, the retry of a
   dead range, one launch per dataset, the refusal paths, the sequencing at the default
   `--parallel 1`, the announcements. Catches a harness that relaunches a complete range or
   skips a dead one; misses anything about Vast.
3. **`fit_guard.sh` against `vast_run.sh`** — the same seed count is admitted or refused by
   both. Catches a harness that sizes batches by its own arithmetic.

## Tests (`tests/test_batch_run.py`)

- 40 seeds at a batch size of 12 → 4 launches, `COMPLETE`, exit 0, every seed launched once
- a batch killed mid-run comes back on the next pass, and only that range
- a range already banked is never launched (pre-seeded tree, partial coverage)
- a seed banked on one arm but not the other is still missing
- `--parallel 2` refuses, names #431, launches nothing; the default runs one launch at a time
  (a directory lock in the double fails the test if two are ever alive)
- two empty passes stall (exit 4); one empty pass alone does not
- the pass limit with a launcher that banks one seed per launch exits 3 and prints the missing
  range
- launcher rc 2 stops immediately
- a comma dataset list launches once per dataset, and the comma list never reaches the launcher
- `BATCH_SIZE` above the poll window is refused before any launch, with the shared message
- a dry-run manifest does not bank; a real one does; a 2,000-row launch does not bank a
  10,000-row design
- announcements reach the log, `--notify CMD` and a stubbed `osascript`
- operator arguments after `--` reach the launcher and cannot replace the batch
- usage errors: `END` before `START`, batch size 0, a non-numeric argument, `--parallel 0`, a
  missing `--dataset`/`--arms`
- `fit_guard.sh` and `vast_run.sh` agree at the boundary for the same seed count

## Docs

- `docs/current/FINETUNING_EXECUTION_RUNBOOK.md`: rule 3 stops saying `batch_run.sh` is not
  built, gains the invocation (including the poll window a 12-seed batch needs), the one
  launcher per dataset rule, and the two-empty-pass stop. The section's opening sentence
  ("Neither is built yet") becomes true of `watch_run.sh` only.
- `CHANGELOG.md`: one line at the bottom of `## [Unreleased]` (rule 10).

## Out of scope

`--parallel > 1` (#431), progress/stall/burn reporting (#432), the abort-on-no-progress guard
(#433), the citation-array extension (#434 rule 11), and model-line/commit comparison in the
banked set (stated as the limit above). The harness reserves `--parallel` so #431 can fill it
in without changing the CLI.
