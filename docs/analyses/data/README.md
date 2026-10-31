# Analysis data tables

The tables in this directory are generated from committed evidence. Each one can be regenerated
from the run it names, and each row says which bytes it rests on. Nothing here is hand-edited.

## `20261031T021845Z-predictions.csv`

One row per prediction from the fine-tuning anchor's run: 4 arms × 2 seeds × 1,000 test rows.

| Column | Meaning |
| --- | --- |
| `run_id` | the run this prediction came from (`results/20261031T021845Z/`) |
| `dataset` | `uslapseagent` |
| `arm` | the training configuration: `A_raw`, `B_ft3`, `B_ft10`, `B_ft30` |
| `seed` | 43 or 44 — each seed is its own split and its own fit |
| `row` | position in the test array, 0-based. **Not** the row in `data/raw/uslapseagent.csv` |
| `y_true` | the true label, 0 or 1 |
| `probability` | the model's positive-class probability for that row |
| `capture_sha` | sha256 of the predictions array this row came from |
| `source` | which artifact verified the array: `capture.json` or the arm's `meta.json` |

Regenerate it with:

```
python scripts/analyses/export_predictions.py --run results/20261031T021845Z
```

The command verifies both array hashes against `results/20261031T021845Z/capture.json` before it
writes. If a hash does not agree it refuses and names both values, so a table here cannot rest on
altered bytes.

**Open it how you like.** It is plain CSV: pandas (`pd.read_csv`), R (`read.csv`), or a
spreadsheet. `y_true` and `probability` are all you need for any metric that scores probabilities
against labels. To check a row against the raw evidence, `capture_sha` matches the entry in
`results/<run_id>/capture.json`.

## What you can and cannot do with it

**You can** compute any scores-only metric yourself, with no code from this repo: a different ECE
binning, cost-weighted thresholds, precision–recall at a chosen operating point, bootstrap
intervals, per-row loss distributions.

**You cannot** attach these rows to customer attributes. The capture stores the two arrays and
their hashes, not the test indices, so `row` identifies a prediction within an arm and seed but
not a row of the source table. Segment, fairness and "error by age band" analyses need the test
indices stored first (out of scope of #387).

## Explore or cite

- **Exploring?** Use the table. Nothing further is required.
- **Citing a number in a document?** The number needs a name and a version in
  `docs/analyses/METRIC_REGISTRY.md`, and a rescore CSV beside this one that carries
  `recorded_value` and `agrees`. The record wins where both can produce a number (#357).

The run id you cite must have a `capture.json`; a cited run without one fails the gate (#364).

## Rescore tables

`rescore` writes `<run_id>-rescore-<metricset>.csv` here, one row per arm × seed × metric, with
the metric version, the capture hash, the tool version, the record's value and whether the two
agree. Regenerate with:

```
python scripts/analyses/rescore.py --run results/20261031T021845Z
```
