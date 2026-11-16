# Plan — the diagnostics figure shows what overlap to expect

**Status:** Current — implemented with this change, 2026-11-16.
**Origin:** #651, from the figure-honesty audit.
**Design:** a chance model computed from each dataset's feature count, drawn as a dashed reference in
the overlap panel, with the caption quoting the multiples.

## Scope

1. `chance_overlap(features)` in the diagnostics module: the expected Jaccard of two random top-ten
   sets, `(k²/N) / (2k − k²/N)`, which is 1.0 when the dataset has only ten features.
2. A dashed line per dataset group in the overlap panel, plus a legend entry.
3. A caption sentence naming the two ends of the range and the multiples: `eudirectlapse` 0.54 is
   1.4× chance, `coil2000` 0.11 is 1.8× and 0.33 is 5.3×.
4. Tests pinning the chance values, the feature counts, and the caption's multiples.

## Decisions worth arguing with

**A chance line, not a second bar.** A bar per pair would double the ink and read as another result;
a dashed reference is a scale, and scales belong as lines.

**The model is computed, not tabulated.** A hard-coded expectation table would drift the moment a
dataset's feature set changed; the number comes from the same table the bars do.

**The caption keeps the `uslapseagent` artefact.** Its chance value is 1.0, so the line sits on the
top of the axis — which is the honest picture of "the top ten is the whole set".

## Verification

```sh
.venv/bin/python scripts/infra/diagnostics_figures.py
.venv/bin/python -m pytest tests/test_diagnostics_figures.py -q
PATH="$PWD/.venv/bin:$PATH" ./scripts/check.sh
```
