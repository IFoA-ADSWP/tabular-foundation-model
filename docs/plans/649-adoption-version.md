# Plan — the adoption figures declare their model version

**Status:** Current — implemented with this change, 2026-11-16.
**Origin:** #649, from the figure-honesty audit. Settled by grilling: one `v3_default` panel, era
disclosed in-figure, re-tested cells marked, no mixing of values.
**Design:** a version note inside each figure, a dagger on the four re-tested cells, and captions that
state what moved on the current line.

## Scope

1. Both adoption figures carry `model v3_default` as figure-level text, so a screenshot keeps it.
2. A dagger marks `spanish_motor_freq`, `spanish_motor_severity`, `bemtl97_amount`, `freMTPL2freq` —
   the four datasets §16 re-tested at `v3.5` — in the size chart's labels and the matrix's row labels,
   keyed in the legend and under the matrix.
3. The size chart's headline is scoped to the panel; both captions name the two material moves and the
   off-frontier count on each line (5 in the panel, 4 current).
4. §1 carries both counts; the figures index rows carry the era.
5. `tests/test_adoption_figures.py` pins the four datasets, the version string, and the document's
   two counts.

## Decisions worth arguing with

**The panel is not re-rendered at v3.5.** A mixed matrix would rest its cross-dataset comparison on
different model versions, which `MODEL_VERSIONS.md` and `GLOSSARY.md` forbid in one claim. The
coherent panel plus an explicit era statement is the honest cheaper option; the re-run is #654's
decision.

**The dagger is per-cell, not a blanket sentence.** A reader scanning the image needs to know *which*
numbers have a newer line; a caption alone is lost the moment the image is copied.

**The claim is scoped, not withdrawn.** "In the `v3_default` panel, parity at small size and drift at
scale" is true of the data drawn. Withdrawing it would hide a real result; stating it unqualified
would present a superseded one.

## Verification

```sh
.venv/bin/python scripts/infra/adoption_figures.py
.venv/bin/python -m pytest tests/test_adoption_figures.py -q
PATH="$PWD/.venv/bin:$PATH" ./scripts/check.sh
```

Figure bytes change (the version note and daggers are new); no plotted value changes.
