# Plan — generate the conclusion's table (#631)

#632 allows the conclusion to restate the headline table only because the conclusion owns it, and
`DOCUMENT_AUTHORITY.md` will say so (#633). Ownership without generation is how a table drifts from
the numbers it reports.

## What

- `scripts/analyses/baseline_conclusion.py` — reads the committed frontier results and today's two
  check CSVs, emits the two tables between markers, and offers `--check` for drift.
- `docs/experiments/baseline-conclusion-2026-11/TABLE.md` — the generated block, committed.
- `tests/test_baseline_conclusion_table.py` — fails when the committed table differs from the
  generator, the same pattern `check.sh verdict` uses for the null band.
- The campaign README and the `EXPERIMENTS.md` row that `docstatus` requires.

## Why

A conclusion that restates 12 values by hand is a transcription exercise with a half-life of one
correction. The generator makes the table reproducible and the drift test makes a stale table a red
gate instead of a review miss.

## A gap this records rather than hides

The frontier results CSVs carry **no run id**, so table 1's `source` column names the CSV, not a
capture. #632 asks for a source run id per row. Producing one needs a dataset-to-run mapping that does
not exist; inventing one in the generator would be exactly the transcription error this ticket
removes. Recorded here, and it belongs in the conclusion's gap register.

## Verification

- `python scripts/analyses/baseline_conclusion.py --check docs/experiments/baseline-conclusion-2026-11/TABLE.md`
- `pytest tests/test_baseline_conclusion_table.py -q`
- `./scripts/check.sh docstatus`

## Out of scope

- The prose (#632) and the registry rows (#633).
- v3.5 frontier verdicts: the committed CSVs are the v3 line. A v3.5 table needs the §16–§24
  artefacts mapped to rows, which is a separate ticket if the conclusion wants both eras in table 1.
