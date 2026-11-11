# Plan — the pilot's disposition, and the pre-run documents

**Status:** Current — delivered 2026-11-09.
**Origin:** #341 on map #484, the last open ticket. Resolved by decision: the pilot is a live candidate,
so the ticket's conditional ("if the pilot is archived") never fired.
**Design:** markers in place, no file moved.

## Scope

Five current-tier documents still read as pre-run. Each gains a dated marker saying what has since
happened and where the outcome lives; none moves tier, and none loses a line.

- `FINETUNING_EXPERIMENT_REFERENCE.md` — "R1 complete — smoke test only", as if the later phases were ahead.
- `FINETUNING_PILOT_DESIGN.md` — "design to be executed", when part of it has executed and part was deferred.
- `FINETUNING_STATISTICAL_ANALYSIS_PLAN.md` — "DRAFT for sign-off", when it has been applied.
- `FINETUNING_PREREGISTRATION_2026-11.md` — authorised one probe and one replication; both ran.
- `FINETUNING_PREREGISTRATION_SPANISH_2026-11.md` — authorised nothing; the cell ran under D19/D20 anyway.

## Decisions worth arguing with

**Markers, not moves.** Moving the pre-run documents to `reference/` would make the tiers match what they
claim, and would break every link from the outcome report, the evidence map and the front door. The map's
standing preference is markers, and the precedent is the status brief: it keeps its history and gains a
dated note. Consistency beats tidiness here.

**The pre-registrations are marked complete, not amended further.** Their bodies stay as written; a
pre-registration is a record of what was fixed in advance, and editing it after the data destroys the only
property that makes it one. The 2026-11 one already carries the pin amendment from #508; this adds the
completion, nothing else.

**One marker declines to repair what it records.** The statistical plan's sign-off is one pass by the owner,
not two independent reviewers. The marker says so rather than letting "applied" imply "independently
reviewed".

**The ticket closes without deciding the pilot's fate.** "Not archived" is not "will not be archived". The
disposition question returns only if someone archives the pilot, and then as a fresh effort — which is what
the map's out-of-scope rule says.

## Shape

```
docs/current/FINETUNING_EXPERIMENT_REFERENCE.md         # + dated marker
docs/current/FINETUNING_PILOT_DESIGN.md                 # + dated marker
docs/current/FINETUNING_STATISTICAL_ANALYSIS_PLAN.md    # + dated marker
docs/current/FINETUNING_PREREGISTRATION_2026-11.md      # + completion
docs/current/FINETUNING_PREREGISTRATION_SPANISH_2026-11.md  # + completion
CHANGELOG.md                                            # one entry
```

## Verification

```sh
./scripts/check.sh
```

Run on 2026-11-09: green. `docstatus` still sees all 42 reports; `doclinks` resolves the new links.

## What this does not do

It does not archive the pilot, move a document, retire a spec, or settle whether Phase 3 is ever run. It does
not touch the nine owning-document contradictions filed as #511 — those need an authority order, not a
marker.
