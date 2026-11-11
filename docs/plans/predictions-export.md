# Plan — the anchor's predictions as a table a colleague can open

**Issue:** #387.
**Status:** Current.

## What and why

The anchor's evidence is committed, verifiable and discoverable since #362/#361. But reading it
needs `np.load`, a directory layout, and the knowledge that row *i* pairs with row *i* of
`ground_truth.npy`. `rescore` reads a capture, but only emits metrics from a fixed registry — so a
colleague who wants their own metric cannot get at the numbers without our code.

This writes the same evidence as one long-format CSV, a row per prediction, and commits the
anchor's copy:

```
python scripts/analyses/export_predictions.py --run results/20261031T021845Z
→ docs/analyses/data/20261031T021845Z-predictions.csv
```

Columns: `run_id, dataset, arm, seed, row, y_true, probability, capture_sha, source`. 8,000 rows,
sorted by arm then seed then row, so a diff means the inputs changed.

## Judgement calls

1. **It verifies before it writes.** Both the export and `rescore` now read through
   `capture_reader.read_run`, which owns the manifest/record/hash rules. One reader means the two
   tools cannot disagree about what "verified" means, and the export cannot produce a table from
   bytes `rescore` would refuse.
2. **`capture_sha` is repeated on every row.** It costs file size — the committed CSV is about
   1.1 MB, not the ~150 KB I first estimated — and buys a row that is self-describing: filter one
   arm in a spreadsheet and you still know which bytes it rests on, with no join.
3. **`row` is the position in the test array, not the dataset row.** That is all the capture
   encodes. Segment analysis stays blocked until the test indices are stored, which changes the
   #355 shape and needs its own decision — stated in the issue, the README and the module
   docstring rather than left to be discovered.
4. **The anchor's table is committed** so a colleague with no Python and no checkout can open it.
   It sits under `docs/`, not `results/`, because it is derived analysis output, not run evidence.
5. **`csv_cell` moved to `provenance`.** `rescore` and the export needed the same float/bool/None
   spelling; two copies is how two tables start disagreeing about how `1.0` is written. The
   diagnostic writer already had this helper privately, so it is now public and shared.

## Seams under test

The CSV on disk. Expectations come from the arrays and the manifest, never from the exporter's
helpers; the committed table is checked against the anchor's arrays, so it cannot drift.

## Verification

- `pytest tests/test_predictions_export.py -q` — 8,000 rows, nine columns, every value equal to
  the array it came from, every hash equal to the manifest's, a mutated truth refusing before a
  file is written, byte-identical reruns, and the committed table matching the arrays.
- `./scripts/check.sh` — all six checks; the doc-link check must resolve
  `scripts/analyses/export_predictions.py` from the new README.

## Out of scope

- **Test indices / dataset row ids** — the capture shape, decided in #355.
- New registry rows (`lift/1`, `calibration_slope/1`) and rescore behaviour.
- Parquet, or one file per arm.
