# Plan — the significance marker agrees with its own bounds (#296)

**Status:** Current — 2026-10-31.
**Ticket:** #296. Reported from the probe results; diagnosed during triage.

## What the ticket asks

The probe write-up says `B_ft3` carries the tool's "interval covers zero" marker while printing
an interval that excludes zero. Which is wrong: the bounds, the marker, or the rounding?

## What the diagnosis found

None of the three. The marker is computed from the same raw percentile pair that is printed,
so the tool cannot produce the reported combination; 25 synthetic bootstraps through the real
function agreed with their bounds every time. What does produce it is the repository's second
convention: the evaluation analysers print `***` when a comparison **is** significant, the
opposite meaning, and the write-up's sentence reads as if it came from that side.

Two defects remain real, and this change fixes them:

1. **The write-up asserts a contradiction that cannot happen**, and tells readers not to quote
   `B_ft3`. That instruction should go: the bounds decide.
2. **A bound that rounds to zero hides its sign.** A raw high bound of `-0.00004` renders as
   `-0.0000`, so an interval that excludes zero reads as if it touched zero — the same
   reader-facing contradiction, in the one place it can genuinely occur.

## Seams under test

1. **The report tool's marker and interval helpers** — pure functions taking the two bounds and
   returning the flag and the bracketed text. Catches marker/bounds drift and the zero-rendering
   edge; misses layout and summary formatting.
2. **`print_report(report, outdir)` rendered output** — catches the reader-visible combination of
   marker and bracket in one line; misses anything not printed. The generated sweep parses the
   printed bracket rather than re-deriving the predicate, so the line is the source of truth.

## Slices

1. Marker derived from the bounds, not from a stored flag: red test over a grid of intervals,
   then the helper. The "covers zero" predicate moves to `interval_covers_zero` in
   `src/paired_analysis.py` so the stored `excludes_zero` fields and the printed marker are one
   fact, not two.
2. A bound that rounds to zero keeps its significance: red test on `-0.00004`, then the
   formatter.
3. The report prints the two together, so the invariant is asserted on rendered output.
4. The write-up no longer asserts the contradiction, the marker legend names its meaning once,
   and `GLOSSARY.md` distinguishes the two conventions so a reader cannot mix them again.

## Gate

`./scripts/check.sh` — ruff, pytest, shellcheck, evidence guard — plus the doc-link checks that
run inside pytest.

## Out of scope

Re-running the probe; re-deriving `B_ft3` from artifacts (the run's records are not in the
repository); the anchor's acceptance rule, which already states that bounds decide.
