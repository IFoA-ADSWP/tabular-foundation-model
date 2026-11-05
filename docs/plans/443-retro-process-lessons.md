# Plan — the 2026-11-05 paid-run retro's process lessons (#443)

**Status:** Current — 2026-11-05. **Issue:** #443. **Branch:** `docs/443-retro-lessons` from `main`.
**Scope:** one coding standard and two rules deferred to #434. No code, no launch, no spend.

## What and why

The 2026-11-05 campaign's engineering failures are ticketed under #428. What no ticket captures is
the process mistake that let a signed result disagree with its own evidence: D18 quoted the 228-seed
pool's mean, SD and seed requirement beside a 238-seed count, and the committed capture was what
finally exposed it (#436). The retro (#443) turns that into prose, because no checker can read a
result document's arithmetic in general.

## What lands

1. **`CODING_STANDARDS.md`** gains "A result quotes the analysing tool, not a hand-assembled summary":
   one run of the tool over the final evidence, the command in the document, and *unmeasured* for a
   figure copied from an earlier pool. It cites the D18 finding and names the one mechanical
   enforcement that exists (`tests/test_d18_evidence.py` parses the document).
2. **A comment on #434** carrying the two rules that belong in the paid-run rules document rather
   than here:
   - evidence is committed before a result ships, and the citation check should verify the arrays it
     hashes — it passed while every `.npy` was absent during #436;
   - a failure that looks healthy stops the set: no retry and no publication until the artifact's
     identity is proven against the launch that asked for it (#426's `verified=24 mismatched=0` while
     holding another launch's seeds).
3. **`CHANGELOG.md`** entry for the standards change.

## What does not land

The #434 document itself (it is an open ticket with its own scope), any new check or code, and a
second retro document. The campaign's engineering actions are #428's children.

## Verification

- `./scripts/check.sh doclinks`, `docstatus`, `citation`, `evidence` (no evidence change)
- No test is added: the rule is prose, and the only mechanical enforcement is the D18 test it names.
  `pytest tests/ -q` stays green as the regression guard.
