# Plan — cite the external replication in the regime note (#684)

An independent study reproduces this note's frequency result on the same two datasets. The note is
`current`, so the question is not whether to mention it, but how to do so without letting an
external claim move a verdict.

## What

One dated blockquote in `docs/experiments/frontier-benchmark/regime_characterization.md`, after the
"tree-only" count-axis bullet, and a status date bump. It carries:

- the study, its model versions (v2.6 and v3) and its metric (exposure-weighted Poisson deviance);
- its Table 1 figures, quoted, with the explicit statement that our levels differ because our
  deviance is on counts, not rates;
- the sentence that no verdict changes;
- the four mechanisms it names, and the fact that our harness already implements the only exposure
  substitution the model permits.

## Why

The count-axis reading was inferred from our frontier alone. It is now corroborated on the same
data by someone else, which rules out a harness artefact. That is worth one paragraph in the
document whose claim it supports — and worth nothing if it is only in another repository.

## Verification

- `./scripts/check.sh doclinks` and `./scripts/check.sh docstatus`.
- Every figure is from the paper's own table, as recorded in the fm4sd digest, which quotes the
  fetched text; none is restated from memory.

## Out of scope

- Changing the adoption rule. A citation cannot move a bar; only a measurement can.
- Any claim about v3.5, which the paper does not test.
