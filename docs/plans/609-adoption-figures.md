# Plan — the adoption picture in two figures

**Status:** Current — implemented with this change, 2026-11-13.
**Origin:** #609. Follows the pattern #607 set: a figure is drawn from committed evidence, asserted
against the claim it illustrates, and embedded in the document that owns the claim.
**Design:** two static figures over the committed frontier CSVs — one for the size story, one for the
whole benchmark at a glance.

## Scope

1. `docs/figures/tabpfn_size_drift.{pdf,png}` — TabPFN's metric ÷ the best method's, against training
   rows on log–log, with the 9-cell home-turf sweep. The "parity at small size, drift at scale" claim.
2. `docs/figures/frontier_method_matrix.{pdf,png}` — every dataset × every method that ran, coloured by
   the same ratio, datasets ordered by size, TabPFN's column outlined.
3. `scripts/infra/adoption_figures.py` — both figures, one entry point, values recomputed from the CSVs.
4. Captions and embeds in `regime_characterization.md`, plus the dated correction below.
5. `tests/test_adoption_figures.py`, `docs/figures/README.md` rows, `scripts/README.md`, `CHANGELOG.md`.

## Decisions worth arguing with

**The dataset list comes from the registry, not from a glob.** `experiments.toml` names the twelve
frontier datasets and their raw files; the CSVs also hold per-seed reruns (`*_seed7`, `*_seed123`)
that are not datasets. Reading the registry is the one definition; a glob with a suffix filter would
be a second.

**The sweep is de-duplicated by fold.** At 1K and 5K the CSV records each TabPFN fold twice — once
with a blank `n_estimators` and once with `8` — with identical losses, from the v2 sweep assembly. The
mean is unchanged either way; collapsing to one row per fold makes the cell count mean what it says.

**A missing method is a blank cell, not a zero.** Regression rows have no logistic model and
classification rows have no OLS, so the matrix is the union and the gap is left white. A zero would
read as "infinitely worse".

**Grey is not a category.** Off-frontier points use the palette's vermillion against blue for
on-frontier, with marker shape and legend doing the same work; the matrix is a single-hue ramp derived
from the palette, with the value printed in each cell so colour is never the only encoding.

## The defect this surfaces

`regime_characterization.md` §1 and `plot_money_chart.py`'s docstring both say "every off-frontier point
sits at ≥53.5K training rows with ratio ≥1.03". Recomputed from the CSVs: the size half holds (minimum
53,502 rows), the ratio half does not — `ausprivauto0405` is off-frontier at 67,856 rows with ratio
**1.003**, a tie at seven parameters. The figure's caption states the verified version; the document gets a
dated correction and the script docstring is corrected at source.

## Verification

```sh
.venv/bin/python scripts/infra/adoption_figures.py
PATH="$PWD/.venv/bin:$PATH" ./scripts/check.sh
```

The test asserts the caption's facts from the CSVs: twelve datasets, seven on the parsimony frontier,
the off-frontier minimum of 53,502 rows, the 1.003–1.502 ratio range, and 8 of 9 sweep cells won.
