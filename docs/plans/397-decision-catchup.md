# Plan — the repository states the decision it has made (#397)

**Status:** current — 2026-11-03. **Origin:** #397, under spec #395.

## Why

The decision log ends at **D11 — the fine-tuning line stops**, and the status brief says the same.
Both were written on 2026-10-31, before the null control showed that the anchor's design could not
resolve the effect it was asked about. Everything decided afterwards — the threshold, the replication
design, the destination — exists only as issue resolutions, so a colleague reading the repo today
would conclude the lever is closed and nothing is planned.

## The finding this ticket must record

D11's own log contains a **pre-registered outcome mapping** (§3) whose last row reads: *"Test-set
power unreachable within the envelope → report the power limit, not a null → revisit scale or accept
the limit."*

D11 recorded the anchor as *"a fair negative, not the historic one"* — the row above it. That reading
was taken without a power measurement. The null control (#338) then measured it: the design resolves
**±0.010** at 1,000 test rows against an effect of **0.002–0.003**, and under 5,000 label permutations
the observed deltas sit inside the null band (p 0.29–0.84).

So the stop was a correct *stop* under D9 and a wrong *reading* under §3. The restatement is not
"we were wrong to stop"; it is "the stop's stated meaning was not the one the log had pre-registered
for this case". That distinction is the whole value of pre-registering the mapping.

## What changes

1. **`docs/current/FINETUNING_DECISION_LOG.md`**
   - A **restatement block under D11**, leaving the original text visible as history, naming the §3
     row the evidence actually selects.
   - **D12** — the continuation threshold (δ=0.002 AUC, Brier guard, one probe-selected rung, v3.5
     pinned, $0.15 per launch).
   - **D13** — the replication design (probe shape, rung rule with budget fallback, resolution gate,
     fresh null, pre-registration as dated amendment).
   - **D14** — the destination (continue once, no expansion, three outcome branches, reopening
     conditions).
2. **`docs/current/FINETUNING_STATUS_BRIEF.md`** — the "What we're doing next" section stops saying
   "stopped" and states the authorised replication; the staged-scale list is marked as superseded by
   D14's no-expansion decision.
3. **`docs/analyses/`** — two research documents promoted from their throwaway branches
   (`research/replication-sizing`, `research/spanish-lapse-stage2`), and one new document for the
   null control with its method, RNG seed, replicate count and measured figures.
4. **`docs/MODEL_VERSIONS.md`** — a scoped note: v3.5 is pinned for the replication's classification
   task by D12, which steps outside the table's "still v3" line; #186 owns closing the gap. Without
   this the doc forbids what the plan does.

## What this deliberately does not do

- **No new numbers.** The null control's figures are copied with their provenance; the reseeding
  arithmetic belongs to #398's tool, and the pre-registration to #396.
- **No archival of code or evidence** — D14 keeps both; #340/#341 stay dormant.
- **No rewrite of D11's original text.** The log is a record; restating is appending.

## Verification

`./scripts/check.sh` green: `doclinks` (every reference resolves), `docstatus` (every document states
what it is), `citation` (no uncaptured run id is introduced), plus ruff/pytest/shellcheck/evidence.
The two promoted documents already carry status lines and were written against `main`.
