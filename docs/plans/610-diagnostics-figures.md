# Plan — the D2 feature-ranking readings as one panel

**Status:** Current — implemented with this change, 2026-11-13.
**Origin:** #610. The third figure batch, following #607 and #609.
**Design:** one two-panel figure over the committed D2 table, placed beside the prose that defines
what the panels compute.

## Scope

1. `docs/figures/diagnostics_feature_agreement.{pdf,png}` — top-ten Jaccard (bars) and Spearman rank
   correlation (dots) for the three family pairs, per dataset.
2. `scripts/infra/diagnostics_figures.py` — one entry point, values computed from the table.
3. Embed and caption in `docs/analyses/data/README.md`, immediately after the three readings it
   defines.
4. `tests/test_diagnostics_figures.py`, an index row in `docs/figures/README.md`, `CHANGELOG.md`.

## Decisions worth arguing with

**It goes beside the definitions, not in a new report.** The data README already states the three
readings (*same features ranked differently*, *different features*, *interaction only*) and the
at-chance caveat. A figure that computes those readings belongs where they are defined; creating a
fourth diagnostics report to host one picture would add a document whose only content is this one.

**A family at chance is marked, not dropped.** `eudirectlapse`'s LGBM arm scores 0.494 test AUC, so
its ranking is noise. Dropping it would hide a family; drawing it like the others would lend noise the
same authority as signal. It is hatched (bars) and hollow (dots), with the flag in the legend.

**The version caveat is in the caption, not a footnote.** The TabPFN arm here is the local **v2.5**
checkpoint, not `v3_default`. Nothing else in the figure programme uses v2.5, so a reader who assumes
the same model line would be wrong; the caption says so next to the numbers.

**No interaction-candidate panel.** The data README's third reading (an LGBM top-ten feature outside
both other top tens with near-zero univariate AUC) yields two candidates in this table, one of them on
the at-chance arm. Two points do not need a panel; the caption names them.

## Verification

```sh
.venv/bin/python scripts/infra/diagnostics_figures.py
PATH="$PWD/.venv/bin:$PATH" ./scripts/check.sh
```

The test asserts the caption's facts from the table: `uslapseagent` top-ten Jaccard 1.00 on all three
pairs; `eudirectlapse`'s LGBM arm flagged at chance; its GLM–LGBM rank correlation near zero; and
`coil2000`'s TabPFN–GLM overlap at 2 of 18 features.
