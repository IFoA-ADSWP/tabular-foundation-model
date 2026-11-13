# Plan — the row-scaling arm on `frequency_french` (#572)

**Status:** implemented 2026-11-13 — the arm ran and the verdict document carries it.
**Origin:** ticket #572. **Pre-registration:** the dated amendment in
`docs/current/REGRESSOR_FINETUNING_PREREGISTRATION_FREQ_SEV_2026-11.md`.
**Sibling plan (already done):** `docs/plans/572-row-scale-outcome.md` — the `severity_french` half.
**Evidence:** `results/20261113T095502Z/` (30 entries, schema v3, 29.8 MB of arrays, 17.8 MB on the
wire). Paid run:
`est_cost_usd` 0.5705 and `wall_minutes` 115.82 in `outputs/gpu-pilot/run_20261113T095502Z.json`.
**Outcome:** r = **+11.84%**, CI [+8.93%, +14.76%], MDE 2.94%, **Go** — against **+9.69%** at
10,000 rows, on identical test rows. The gain did not shrink, so the frequency Go was not a
small-data artefact; the intervals overlap, so no increase is claimed.

## What this runs, and why

The amendment raises the per-fold training budget from 10,000 to 40,000 rows for a row-scaling arm,
applied to **both** arms, and names `frequency_french` as its second target. The severity half ran
on 2026-11-13 and returned **No-go** at 2.1× (the budget clamped to each fold's whole claim pool):
the null survived. This plan covers the frequency half, which ran the same day.

It matters more than the severity half did, on the amendment's own numbers: the published **+9.69%**
is measured on **10,000 of ~542,000** available French policies — **1.8%**. That is the starved end
of the cap, and it is the only target where the registered 4× budget is actually reachable.

One launch, same machinery as the severity arm:

| Field | Value |
|---|---|
| targets | `frequency_french` only, via `TFM_FAIRTEST_TARGETS` |
| arms | `A_raw` vs `B_ft30` — the primary pair, unchanged |
| rows | `TFM_TRAIN_ROWS=40000`, both arms, so the inference context stays matched |
| folds / seeds | five policy-grouped folds × three seeds = 30 fits |
| mode | `--fairtest primary`, so the capture is emitted as the target completes |

## The reading this arm is allowed to make

The registered decision rule does not move: the `frequency_french` target row gets its own
**2% floor** and the existing `decide()` — Go when the interval excludes zero and the point estimate
clears the floor, No-go when the interval's upper bound is below it, Inconclusive otherwise.

Mirroring the severity arm, this row is reported **beside** the registered targets and **not** folded
into the frequency task mean. The registered verdict is the 10,000-row pair; this arm asks whether a
larger budget changes it rather than replacing it. So the two readings are separate and both stay:

- **target-level**: whether `frequency_french`'s gain survives at 4× rows, and in which direction;
- **task-level**: unchanged — still **Go** on the 10,000-row pair until a separate registration
  says otherwise.

Three outcomes, each publishable:

1. **The gain holds or grows** — +9.69% was a floor, not a midpoint, and the cap was not what
   produced the win. This is the classifier lane's finding repeating.
2. **The gain shrinks but still clears 2%** — the win is real and smaller at scale; the write-up
   must then quote the smaller number wherever it currently quotes 9.69%.
3. **The gain collapses or reverses** — the frequency **Go** was a small-data artefact, exactly the
   possibility the amendment was written to test, and the verdict document would need a dated
   supersession rather than a caveat.

## Cost

Ceiling: `--poll-minutes 180` at `--max-dph 0.60`, so **≤ $1.80** for the slot, and the launcher's
pre-flight refuses anything below the 105 min this configuration needs.

Measured basis, not a guess: the severity arm ran 30 fits at 21,177 rows in **50.7 min for $0.2149**
(`outputs/gpu-pilot/run_20261113T003320Z.json`). Frequency at 40,000 rows is ~1.9× the context on the
same 30-fit shape, so **~2–3 h and roughly $0.6–1.0** expected, dominated by paced transfer of a
larger capture. The ticket's own `$1.50–2.50` estimate was written before any measurement in this
arm and overshot the severity launch ~7×; it is kept here only as the upper bound it now is.

**Measured:** 115.82 min at the $0.2956/hr effective rate the record reports = **$0.5705**, just under
the estimated range and a third of the ceiling. Transfer was the slow half, as predicted: the fits finished
well before the poll window filled.

## Risks measured on the last two launches

- **A suspended laptop loses the capture.** The 2026-11-12 failure was the poller asleep while the
  box emitted (`docs/plans/chunk-transport-under-stalls.md`). This launch runs under
  `caffeinate -dimsu`, and a launch that starts without one is warned by the launcher's own check.
- **The 40,000-row capture is bigger than the severity one**, and transfer is the failure mode, not
  the fits. The poll ceiling is set from the launcher's arithmetic rather than from the fits alone.
- **The rollup lies about completion.** Status is confirmed from `gh run`-style per-job conclusions
  where it applies, and here from the launcher's own exit plus a capture on disk, never from a
  progress line.

## What changes when it lands

1. **Commit the capture** under `results/<run id>/` (schema v3, 30 entries), with the PR labelled
   `evidence-change` so the evidence gate accepts the addition.
2. **`scripts/analyses/freq_sev_fair_test.py` gains `--row-scale-frequency`**, symmetrical to
   `--row-scale-french`: printed beside the target table, excluded from the frequency task mean,
   with a test pinning that exclusion. Result figures must come from one run of the tool
   (`CODING_STANDARDS.md`), so the tool has to be able to print this row.
3. **The verdict document gains a section** and, if the review says so, a dated supersession in the
   frequency row; the amendment table gains its outcome row naming the run id and figures.
4. **`docs/REPORT_REGISTRY.md`** picks up the new capture on the verdict document's row.

## Verification

```
./scripts/bootstrap_dev.sh && .venv/bin/pytest tests/ -q
python scripts/analyses/freq_sev_fair_test.py \
  --frequency-french 20261112T164543Z --frequency-spanish 20261112T184155Z \
  --severity-french 20261112T210029Z --severity-spanish 20261112T220641Z \
  --row-scale-french 20261113T003320Z --row-scale-frequency 20261113T095502Z
EVIDENCE_CHANGE_OK=1 ./scripts/check.sh
```

The registered target and task rows must be byte-identical to the verdict document as recorded on
2026-11-12, and the severity row-scaling line must still read −0.79%.

## What this does not do

- It does not re-open the floors, folds, seeds, arms or the registered verdict.
- It does not test the epoch ladder (`B_ft10` / `B_ft3`), which has no registered floor.
- It does not rescue `frequency_spanish`: at ~42,800 policies its 4% floor is a separate
  registration, and more rows there is a different experiment.
- It does not close #572 on its own; the write-up and the amendment row do that.
