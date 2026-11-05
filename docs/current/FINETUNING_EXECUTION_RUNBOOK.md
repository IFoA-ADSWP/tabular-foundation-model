# Fine-Tuning Execution Runbook — Next-Run Appendix

> **Status:** current as of 2026-11-05.


> **Supporting document.** The canonical funded proposal is `docs/current/FINETUNING_PILOT_DESIGN.md`. This page retains the concrete next-run commands and acceptance procedure; it does not define the overall scope. The funded work is the diagnostics phase followed by the full in-domain pilot.

**Prerequisite 0: satisfied — the seed is reachable (2026-10-30).** The launcher forwards `--seeds` to the runner
(`--seeds LIST`, comma-separated, alongside the existing `--dataset`, `--train-size`, `--test-size`), exporting
`SEEDS` into the onstart payload and the SSH invocation. Note the flag is plural: it takes the runner's list form,
not the singular `--seed` this paragraph used to name. Seeds are passed through rather than defaulted, so the record
states the seed that actually ran.

The anchor's two seeds are pre-registered in `FINETUNING_DECISION_LOG.md` (D9) as **43 and 44**; changing them is a
deviation, not a launch-time choice.

## Stage 1 — replicate the 10,000-row result (2 runs, ~$0.037 each)

```bash
bash scripts/gpu_helpers/vast_run.sh \
  --dataset uslapseagent --arms A_raw,B_ft3,B_ft10,B_ft30 \
  --train-size 10000 --seeds 43,44 --max-dph 0.65
```

**Acceptance, per seed and pre-registered before the run:** each rung's paired interval against the in-run
`A_raw` excludes zero, in the same direction as the first seed, with no `***` marker; Brier and ECE reported
against a tolerance fixed in advance (`docs/current/FINETUNING_DECISION_LOG.md`, D6). **Stop rule:** if a second seed shows the
rungs flat or worse, the line stops here rather than extending to more seeds or more datasets.

## Stage 2 — the same ladder on a second lapse dataset (conditional)

`spanish_motor_lapse`, only if Stage 1 replicates. Same arms, same acceptance, same in-run baseline. Note the
standing caveat: its portfolio-level features against a policy-level target are outside what our split and
context assertions check (FINDINGS L1 and the Spanish leakage note).

## Stage 3 — the adaptation family (conditional, and with a higher bar)

PEFT or meta-learning, only after Stage 2. **The bar is higher than it was:** full SFT now works at scale, so a
parameter-efficient arm must *beat* it, not merely match it. Isolate one factor at a time.

## Watching a launch, and not leaking one

A launch runs unattended for between six minutes and several hours, so the questions are always the
same four: is it alive, is credit moving, is more than one instance billing, and how far through is it.

**The dashboard.** One pane, read-only, redraws every 30 seconds:

```bash
bash scripts/gpu_helpers/watch_run.sh                 # follows the newest /tmp/batch*.log
bash scripts/gpu_helpers/watch_run.sh /tmp/batch3.log --interval 60
bash scripts/gpu_helpers/watch_run.sh --once          # one frame, for a script or a test
```

It shows credit, labelled instances, the arms the launcher was given, the number of result lines, and
— the figure that actually tells you it is alive — **how long ago the log was written**. A count that
stands still is normally the rung, not a hang: a 30-epoch fit at 10,000 rows takes ~155 s, so progress
moves about once every two and a half minutes. Treat a last-write older than ~10 minutes with an
instance still listed as the failure signal.

**The stray-instance killer.** `vast_run.sh` destroys its instance in an `EXIT` trap, and a trap does
not fire on `SIGKILL`, a closed terminal, or a sleeping laptop — and a stopped instance still bills
storage. `vast_watchdog.sh` is the out-of-band control, scoped to the `tabpfn-pilot` label and
refusing to act when it cannot read an instance's age:

```bash
bash scripts/gpu_helpers/vast_watchdog.sh --dry-run     # what it would destroy
bash scripts/gpu_helpers/vast_watchdog.sh               # destroy pilot instances older than 60 min
# from cron, every five minutes:
#   */5 * * * * /bin/bash <repo>/scripts/gpu_helpers/vast_watchdog.sh >> /tmp/vast_watchdog.log 2>&1
```

It prints an unauthenticated warning rather than failing quietly, because a guard you only *believe*
is running is worse than none. If that line appears, the leak protection is off: refresh with
`vast_login.sh`.

**Size a batch to the launcher's own ceiling.** `vast_run.sh` polls for completion for **40 minutes**
(120 polls × 20 s, `vast_run.sh:778`) and then gives up: it exits non-zero, the `EXIT` trap destroys
the instance, and **no artifacts are pulled**. A batch that overruns does not finish late — it loses
everything it computed. Measured 2026-11-04: a thirty-seed batch at 10,000 rows with two arms took
**46.35 min** and cost **$0.2051** for nothing. Size a batch by the per-seed time measured **on the box**, and pin the GPU class while you do it.
Two arms at 10,000 rows on an **RTX PRO 4000**: `A_raw` ~6 s, `B_ft30` ~158 s, so ~164 s per seed.
The same batch on an **RTX 3090** ran `B_ft30` at **753–837 s** per seed — a five-fold difference,
and `--pick value` (dlperf per dollar) does not predict it. Both figures are measured; both losses on
2026-11-04 were batches sized from a figure taken off a truncated run.

Budget the **startup**, not only the fits: image pull, dependency install and the gated weight fetch
take ~3 minutes on a warm host and ~15 on a slow one, and the poll window opens before any of it
begins. Measured across four concurrent launches on 2026-11-04: three at ~3 min, one at ~15.

Keep the compute under ~30 minutes and leave the poll unreachable: at 164 s/seed with a slow
startup allowance, that is about **ten seeds**, not twelve and not twenty.

**The rest of the toolbox**, in the order a run needs them:

| Tool | When |
|---|---|
| `scripts/gpu_helpers/lease.sh` | a launch's identity and release; a failed destroy prints the one-line command to finish it |
| `scripts/gpu_helpers/fetch_weights.py` | the checkpoint and its sha256, into the record |
| `scripts/gpu_helpers/verify_artifacts.py` | after the pull: `predictions verified=N mismatched=0` |
| `scripts/analyses/verdict.py` | per-seed deltas, null band, resolution — `--run` repeats to pool batches |
| `scripts/analyses/rescore.py`, `make_capture.py`, `export_predictions.py` | recompute, manifest, and publish a run's predictions |

**Cancelling.** Find the id, then destroy: `vastai show instances`, then
`vastai destroy instance <id> -y`. The leases under `outputs/gpu-pilot/leases/` name the instance per
launch id, which is the authoritative "is this mine" check.

## Running many launches — the rules this campaign paid for

The section above is watching one launch, and not leaking it. This is the multi-batch half,
for when a campaign is a queue of batches over hours rather than one launch over minutes —
the shape the 2026-11-04/05 D18 campaign took (#414, tracked by #428). Every rule below was
learned by paying for it, none is enforceable by a linter, and where a mechanism exists it
is named rather than restated: `batch_run.sh` is #430's and `watch_run.sh --plan` is #432's.
Neither is built yet, so each rule states the practice and names the ticket that enforces it.

1. **Size a batch from a measured per-seed time and a slow startup allowance.** The launcher
   now budgets 170 s per seed and 900 s to the first arm, and both numbers moved in the same
   direction because both earlier values were optimistic. The first two per-seed defaults,
   90 s and then 110 s, were each derived by dividing the elapsed time of a run the same
   ceiling had cut short, so the division counted work that never ran (#414); 180 s of boot
   was the fast case of four concurrent launches, against a slow one of ~15 minutes. The rule
   is that both inputs come from a run that *completed*, which is why the launcher's guard
   refuses a batch outright instead of warning.

2. **Pin the GPU class to one whose timing has been measured.** `--pick value` optimises
   dlperf/$, which does not predict this workload's per-seed time: the 753–837 s against
   158 s above is a five-fold difference no row count predicts, and the batch that ran on the
   wrong class never finished. Pin `--gpu-allow`; an overrun is a discarded batch, not a late
   one.

3. **Run `batch_run.sh` (#430), not a fixed queue.** A fixed queue skips a dead range and
   moves on, and the missing set is then invisible until someone diffs the run directories
   against the design — on this campaign that was a quarter of the spend buying nothing,
   #430's measurement and the reason its harness removes the failure mode rather than the
   symptom.

4. **Only run concurrently once the smoke test passes (#431).** Two launchers shared one
   fixed output file under `/tmp` — `vast_run_out.txt` — and pulled each other's artifacts;
   both reported success, with
   `verified=24` over a payload that was genuine but belonged to another launch (#426). A
   launch now owns a `mktemp -d` and `tests/test_pilot2_seed_passthrough.py` fails if a fixed
   `/tmp/vast_*` path returns; #431 is the test that two live launchers do not share state.

5. **Never edit a script a process is executing.** Bash reads a script incrementally, so an
   edit lands in the middle of the next command: editing `vast_run.sh` mid-run produced
   `line 863: $'in. >&2…': command not found` in a live launcher. Edit in a separate
   worktree and relaunch.

6. **Pass range lists in a file, never as a shell word.** `for r in $RANGES` does not split
   in zsh, so two launches died on `FATAL: --seeds was given an empty value`. An explicitly
   empty `--seeds` is now a hard error rather than a request for the runner's default, and
   the list belongs in a file that the wrapper reads line by line.

7. **Trust `meta.json` over any log line** — for counting, for progress, and for whether a
   batch is real (#429). A log line is a claim; a `meta.json` is evidence. The
   returned-artifact list itself was once built with `for f in */meta.json`, which matches
   nothing: the runner writes `<dataset>/<arm>/meta.json`. Per-run provenance was never
   returned from the box and nothing failed. `watch_run.sh --plan` (#432) derives banked and
   missing from the run directories for exactly this reason.

8. **`--yes` does not cover the leak preflight (#423).** The prompt that lists still-billing
   `tabpfn-pilot` instances is unconditional, so a second concurrent launcher — which
   correctly sees the first launcher's live instance — aborts there. Pipe a `y` until #423
   fixes it, and do not read that abort as a third failure and retry into it.

9. **When a symptom contradicts the model, reproduce under the mock before blaming an
   external service.** Two symptoms on this campaign — "verified but nothing on disk" and
   "a range ran twice" — were attributed to the provider and to restarts. Both were the
   launcher sharing one fixed `/tmp` output file (`vast_run_out.txt`, #426). Two mock
   launchers would have answered
   it in two minutes; the session put the misdiagnosis at four hours (#434's retro note).
   Corollary: when the numbers disagree with the evidence, suspect our own instrumentation
   first.

10. **Append CHANGELOG entries at the bottom of `## [Unreleased]`, not the top.** Five PRs
    on 2026-11-05 each added a line at the same position, so every squash-merge invalidated
    the next branch and forced a rebase — five mechanical conflicts in one session.
    Disjoint additions at the end merge cleanly far more often.

11. **Evidence is committed before a result ships.** A result cites `results/<run id>/` with
    a `capture.json` per run, and `scripts/check_citations.py` passes before the result is
    published. The check must verify the **arrays** a capture hashes, not only the
    manifest: during #436 it passed in a fresh clone while all 476 prediction arrays were
    absent, because the blanket `*.npy` rule had swallowed them. `results/` is now exempted
    (`!/results/**/*.npy`), but the check still reads only `capture.json`. The extension is
    scoped here and not yet built: for every arm × seed a capture lists, resolve its
    `predictions.npy` and `ground_truth.npy`, hash them, and fail on a missing file or a
    digest that disagrees. Until it exists, a fresh-clone run proves only that the manifest
    is present.

12. **A failure that looks healthy stops the set.** A result that reports success but has no
    artifact — or an artifact that cannot be proven to belong to the launch that asked for
    it — halts the batch. Do not retry into it and do not publish from it. #426 is the case:
    a batch printed `VERIFY predictions verified=24 mismatched=0` while holding another
    launch's seeds, and the payload was genuine, just somebody else's. The identity test is
    the artifact's seeds and hashes against the launch's request, not the verifier's exit
    code. The mechanics are #429 (a batch proves the seeds it wrote), #430 (the missing set
    is the queue), #431 (two launchers at once), #432 (progress, stalls and burn) and #433
    (abort when the box stops progressing); until those land, these rules are checked by
    the person running the batch.

## Evidence obligations, unchanged

Each run writes its own `runs/<run_id>/` directory with per-arm `predictions.npy`, `ground_truth.npy` and
`meta.json` carrying `predictions_sha256`; records, logs and the ledger row follow. A run whose arms did not
produce verifiable artifacts is recorded as incomplete rather than left as an absence.

## What this page deliberately does not do

Name dates. The schedule is the team's, and every number above is measured rather than projected.
