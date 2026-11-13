# Plan — the row-scaling arm's outcome (#572)

**Status:** Current — implemented 2026-11-13.
**Origin:** ticket #572. **Pre-registration:** the dated amendment in
`docs/current/REGRESSOR_FINETUNING_PREREGISTRATION_FREQ_SEV_2026-11.md`.
**Evidence:** `results/20261113T003320Z/` (paid run, `est_cost_usd` 0.2149 and `wall_minutes`
50.68 in `outputs/gpu-pilot/run_20261113T003320Z.json`, completed 2026-11-13 00:33 UTC).

## What was run, and what it returned

The amendment raises the per-fold training budget from 10,000 to 40,000 rows for a row-scaling arm,
applied to both arms. On `severity_french` the budget clamped to the fold's whole claim pool, so each
fold trained on **21,131–21,177 rows** — 2.1× the cap and every claim the fold had — for 5 folds × 3
seeds × 2 arms = **30 entries**.

The arm returned **r = −0.79%, 95% CI [−1.55%, −0.03%], MDE 0.77%, No-go**. The severity null
survives at full scale: the interval still excludes zero on the negative side, and its upper bound
stays far below the 2% severity floor. The point estimate is 0.13 points smaller than the 10,000-row
arm's −0.92%, and the interval is about three times wider.

## What changes

1. **Commit the capture.** `results/20261113T003320Z/` (30 entries, schema v4, ~18 MB) is
   evidence and goes in under the #436 rule, with the `evidence-change` label on the pull request.
2. **The amendment table records the outcome.** A dated row in the pre-registration's sign-off
   table, naming the run id, the figures and the No-go.
3. **The verdict document gains a section**, because it is the document a reader consults to learn
   what the fair test says: the arm, the comparison against the registered severity target, the
   per-fold pattern, and the limit the result does and does not remove.
4. **The analysis tool can recompute it.** `scripts/analyses/freq_sev_fair_test.py` gains an optional
   `--row-scale-french <run id>`: the row-scaling arm is printed beside the registered targets and
   recorded separately, and it does **not** enter the severity task mean. `CODING_STANDARDS.md`
   requires a result's figures to come from one run of the tool, so the document's reproduce command
   has to produce this row.

## What this does not do

- It does not re-open the floors, folds, seeds, arms or the registered verdict. The task tables in
  `docs/analyses/freq_sev_fair_test_result.md` stay exactly as recorded on 2026-11-12.
- It does not run the **frequency** mirror (`frequency_french`), which is the more starved target at
  1.8% of the available policies. The amendment authorises it after the severity arm; it is a
  separate launch, and its cost is **unmeasured** — the severity arm's own `est_cost_usd` (0.2149)
  does not transfer to a target four times its row pool.
- It does not analyse the row-scaling capture's quantiles. `docs/analyses/freq_sev_quantiles.md`
  stays as measured on the four registered captures.
- It does not close #572: the frequency arm of the amendment is still open.

## Verification

```
./scripts/bootstrap_dev.sh && .venv/bin/pytest tests/ -q
python scripts/analyses/freq_sev_fair_test.py \
  --frequency-french 20261112T164543Z --frequency-spanish 20261112T184155Z \
  --severity-french 20261112T210029Z --severity-spanish 20261112T220641Z \
  --row-scale-french 20261113T003320Z
EVIDENCE_CHANGE_OK=1 ./scripts/check.sh
```

The tool's severity task row must be unchanged from the verdict document, and the row-scaling line
must read −0.79% with the interval above.
