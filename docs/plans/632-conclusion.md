# Plan — the technical conclusion and its companion (#632)

The phase's closing statement. Shape settled on #630 through two rounds of questions; the table is
generated (#631); this ticket writes the prose around it.

## What

- `docs/experiments/baseline-conclusion-2026-11/CONCLUSION.md` — nine sections: status and version
  rule, the answer, the generated tables, the gap register, four ways to misread it, the direction,
  what would change our mind, how to check us, reproduce with costs.
- `.../COMPANION.md` — the same story for an actuary deciding adoption, no method detail, no number
  of its own, ending on the one-sentence advice.
- The campaign README updated; `TABLE.md` retired because the conclusion now owns the block.

## Why

Every other document owns one claim. This one restates them for a reader who will not read twelve
notes, and the generated block keeps it honest.

## Verification

- `python scripts/analyses/baseline_conclusion.py --check .../CONCLUSION.md`
- `pytest tests/test_baseline_conclusion_table.py -q`
- `./scripts/check.sh doclinks docstatus`
- Every figure in the companion appears in the conclusion; the companion adds none.

## Out of scope

- Registry rows, the authority row, the changelog and the fresh-context review: #633.
- Any new measurement. A conclusion that needs a new run is a new ticket.
