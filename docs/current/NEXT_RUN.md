# The next round — execution appendix

> **Supporting document.** The canonical funded proposal is `docs/current/FULL_FINE_TUNING_PILOT_DESIGN.md`. This page retains the concrete next-run commands and acceptance procedure; it does not define the overall scope. The funded work is the diagnostics phase followed by the full in-domain pilot.

**Prerequisite 0: the seed is not reachable.** The loader and the split both hard-code seed 42, and the launcher
exposes no flag for it. Replication therefore needs a small pass-through first (`--seed`, alongside the existing
`--dataset`, `--train-size`, `--test-size`). Until that exists, "run it again" runs the same split, not an
independent replication, and would look like a result while measuring nothing new.

## Stage 1 — replicate the 10,000-row result (2 runs, ~$0.037 each)

```bash
bash scripts/gpu_helpers/vast_run.sh \
  --dataset uslapseagent --arms A_raw,B_ft3,B_ft10,B_ft30 \
  --train-size 10000 --max-dph 0.65
```

**Acceptance, per seed and pre-registered before the run:** each rung's paired interval against the in-run
`A_raw` excludes zero, in the same direction as the first seed, with no `***` marker; Brier and ECE reported
against a tolerance fixed in advance (`docs/current/PILOT_2_DECISION_LOG.md`, D6). **Stop rule:** if a second seed shows the
rungs flat or worse, the line stops here rather than extending to more seeds or more datasets.

## Stage 2 — the same ladder on a second lapse dataset (conditional)

`spanish_motor_lapse`, only if Stage 1 replicates. Same arms, same acceptance, same in-run baseline. Note the
standing caveat: its portfolio-level features against a policy-level target are outside what our split and
context assertions check (FINDINGS L1 and the Spanish leakage note).

## Stage 3 — the adaptation family (conditional, and with a higher bar)

PEFT or meta-learning, only after Stage 2. **The bar is higher than it was:** full SFT now works at scale, so a
parameter-efficient arm must *beat* it, not merely match it. Isolate one factor at a time.

## Evidence obligations, unchanged

Each run writes its own `runs/<run_id>/` directory with per-arm `predictions.npy`, `ground_truth.npy` and
`meta.json` carrying `predictions_sha256`; records, logs and the ledger row follow. A run whose arms did not
produce verifiable artifacts is recorded as incomplete rather than left as an absence.

## What this page deliberately does not do

Name dates. The schedule is the team's, and every number above is measured rather than projected.
