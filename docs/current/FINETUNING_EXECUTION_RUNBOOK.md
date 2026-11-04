# Fine-Tuning Execution Runbook — Next-Run Appendix

> **Status:** current as of 2026-10-31.


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
**46.35 min** and cost **$0.2051** for nothing. Size a batch by the per-seed time measured **on the box**
(~108 s/seed at two arms: `A_raw` ~6 s, `B_ft30` ~102 s at 10,000 rows), keep the compute under
~30 minutes, and leave the ceiling unreachable.

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

## Evidence obligations, unchanged

Each run writes its own `runs/<run_id>/` directory with per-arm `predictions.npy`, `ground_truth.npy` and
`meta.json` carrying `predictions_sha256`; records, logs and the ledger row follow. A run whose arms did not
produce verifiable artifacts is recorded as incomplete rather than left as an absence.

## What this page deliberately does not do

Name dates. The schedule is the team's, and every number above is measured rather than projected.
