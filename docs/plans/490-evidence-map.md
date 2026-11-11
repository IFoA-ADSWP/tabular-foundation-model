# Plan — an evidence map for the run trees

**Status:** Current — delivered 2026-11-08.
**Origin:** #490 on map #484, resolving the fog item "136 files under outputs/gpu-pilot and 27 results
directories are part of the fog". No new evidence, no tree changed.
**Design:** the destination is a reading aid, not an inventory: the same walk from any claim.

## Scope

One page, `docs/EVIDENCE_MAP.md`, explaining where a number ends up and how far a reader has to walk. It is
not a tiered report — it describes trees rather than asserting findings — which is why it sits beside
`MODEL_VERSIONS.md` and `REPORT_REGISTRY.md` rather than inside `docs/current/`.

## Decisions worth arguing with

**No counts.** The request that produced this page described the fog as "136 files" and "27 directories".
Both are true today and both would be false within a month, so neither appears. The page says what a tree
holds and what it is for; a number nobody re-runs is the defect this effort exists to remove.

**The citation rule is written out, not linked.** A reader who has to open a Python file to learn why an id
in a document is or is not a citation has not been helped. The three cases — bare id, suffixed name, legacy
exemption — are stated in the page, with the script named so the statement can be checked.

**The Spanish gap is named as a gap.** Every other cell in Phase 2 has a capture; that one does not. Describing
it neutrally would let a reader assume parity. The page says what was lost and what to do next time.

**"If two documents disagree" is ordered.** Capture, then owning document, then summary. A rule with an order
is actionable; "trust the evidence" is not.

## Shape

```
docs/EVIDENCE_MAP.md   # the page
CHANGELOG.md           # one entry
```

## Verification

```sh
./scripts/check.sh
```

Run on 2026-11-08: green. `doclinks` resolves every reference in the new page (the `<run id>` forms are
placeholders and skipped); `citation` is unaffected because the page names no bare run id.

## What this does not do

It does not move, prune or rename anything under `results/` or `outputs/`, and it does not link a front door
— the front-door ticket links it, which is why that ticket waits on this one.
