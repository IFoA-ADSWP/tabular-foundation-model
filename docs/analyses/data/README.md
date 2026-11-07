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

## Diagnostic record tables

A diagnostic writes its record under `outputs/diagnostics/`, which is git-ignored: a record is
runtime evidence, produced by running the diagnostic. That leaves the campaign unreadable from a
clean checkout, so each record is also exported here as a table. One table per diagnostic, one row
per thing the diagnostic measured. Regenerate with:

```
python3 scripts/diagnostics/export_records.py --run tests/fixtures/diagnostics/d2_importance
```

**What the table is the rows of.** Exactly the records you name, sorted by dataset then family then
rank, with no timestamp column — so the same records produce the same bytes in any argument order,
and a diff means the records changed. Two consequences. Exporting one dataset on its own
**replaces** the table with that dataset's rows, so pass every record that should appear. And
**one run per dataset** is enforced: the table's key is `(dataset, family, feature)`, so two runs of
one dataset would put two `rank` 1 rows in one family and "top ten" would stop meaning ten features.
Records accumulate — a record is never overwritten, each run gets its own directory — so
`--run outputs/diagnostics/d2_importance/` names one run per dataset today and will name two once D2
is run again. At that point name the record directories of the run you mean (`--run` once per
dataset) rather than the diagnostic directory.

**What each row rests on.** `dataset_sha256` is the hash of the CSV the diagnostic read, and the
exporter refuses to write a row unless it equals the entry in `data/raw/MANIFEST.sha256` — so a
reviewer can confirm it from the tree: search the value in the manifest and it names the committed
bytes. `record_sha` is the sha256 of the `record.json` the row came from. Where that record is
committed it is checkable with `shasum -a 256`; where it is not, it identifies a record that lives
only on the machine that ran the diagnostic, and the table does not claim otherwise.

### `d2_importance.csv`

D2 (#303), one row per dataset × model family × feature: 4 datasets, 3 families, and the features
each family ranked. The record is `outputs/diagnostics/d2_importance/<run id>-<dataset>/record.json`;
the four records this table was built from are committed under
`tests/fixtures/diagnostics/d2_importance/` so it can be regenerated in CI. They are the four #303
wrote:

| Record committed | Dataset | `record_sha` in the table |
| --- | --- | --- |
| `20261104T1725Z-coil2000` | `coil2000` | starts `c764057e…` |
| `20261104T1725Z-eudirectlapse` | `eudirectlapse` | starts `c48200c9…` |
| `20261104T1725Z-spanish_motor_lapse` | `spanish_motor_lapse` | starts `accbc0b7…` |
| `20261104T1725Z-uslapseagent` | `uslapseagent` | starts `c074479c…` |

`record_sha` is the sha256 of those committed files, so the panel above is checkable with
`shasum -a 256` rather than asserted. What the tree cannot re-derive is that those bytes are what the
diagnostic wrote: nothing external hashes an uncommitted record, so the record's own `created_utc`
and `git_sha` are the run's claim about itself, and this table repeats it rather than proving it.

*Family* here is the glossary's **Method** — one predictor under comparison — because the D2 record
keys its blocks `families`; the table keeps the record's word rather than inventing a third one.

| Column | Meaning |
| --- | --- |
| `run_id` | the diagnostic run the row came from (`<timestamp>-<dataset>`) |
| `dataset` | `coil2000`, `eudirectlapse`, `spanish_motor_lapse` or `uslapseagent` |
| `family` | `tabpfn`, `glm` or `lgbm` — the benchmark's `logisticglm` and `lgbm` ids, refitted locally |
| `rank` | 1 is the most important feature **within that family**; ties are broken by name, so the order is total |
| `feature` | the encoded feature's name, as the model saw it |
| `importance` | mean drop in ROC AUC when that column is shuffled on the held-out rows, over the record's repeats |
| `std` | the standard deviation of that drop across the repeats — the noise of the measurement, not a confidence interval |
| `univariate_auc` | ROC AUC of the feature used alone as a score, from the training rows of the 2,000-row subsample |
| `test_auc` | the family's ROC AUC on the held-out 500 rows; repeated on every row of that family |
| `no_better_than_chance` | `true` when `test_auc` is below 0.52, i.e. the ranking is a ranking of noise |
| `model_version_requested` | what the diagnostic **asked** the library for — `auto`, which is a request, not a version (#285). Named `…_requested` because `model_version` alone means the resolved label everywhere else in this repo |
| `model_resolved_version` | the era the library actually resolved: `v2.5`. The checkpoint filename is in the record. Empty when the record resolved none, and its `resolution_reason` says why |
| `dataset_sha256` | sha256 of the raw CSV the run read — the checkable anchor above |
| `record_sha` | sha256 of the `record.json` this row came from |

**Reading a dataset's top ten:** the rows with `rank <= 10` for that family.

**The D2 record's three readings, from this table alone.** They are computed in the record too;
these are the definitions, so a reviewer can reproduce them without the JSON:

- *same features, ranked differently* — Spearman correlation between two families' `rank` columns,
  over every feature both rank. `rank` is already the rank, so this is Pearson correlation of the
  two columns.
- *different features* — the top-ten sets (`rank <= 10`) of two families: their symmetric
  difference, and their Jaccard overlap (shared ÷ union).
- *interaction only* — an `lgbm` top-ten feature outside **both** `tabpfn`'s and `glm`'s top ten
  whose `|univariate_auc - 0.5| < 0.02`. A screen with its threshold recorded, not a proof of
  interaction. TabPFN is excluded as well as GLM because it is itself an interaction learner.

**Check `no_better_than_chance` before quoting any of the three.** A family whose `test_auc` is at
chance still has a ranking, and that ranking is noise; `eudirectlapse`'s `lgbm` arm is at 0.494, so
its top ten — and any interaction candidate read off it — describes the measurement's error rather
than the dataset. The column travels with every row so that check needs no second lookup.

The 2,000-row subsample (1,500 train / 500 test) is a property of the run, not of a column: it is in
the record and in the regenerate command, and `importance` from it is an approximation rather than a
whole-table measurement. The TabPFN arm is the local v2.5 checkpoint, not the v3 the frontier
numbers used — that is why `model_resolved_version` is a column.

### `d1_profiling.csv` — not present yet

D1's profile table lands the first time D1 is run after #407. No D1 record exists on disk: the D1
runs predate the exporter and `outputs/diagnostics/` is git-ignored, so there are no bytes to
export. It will have one row per dataset and carry `n_rows`, the feature counts, the missingness
and correlation summaries, `max_vif` with the reason it could not be computed, and the target's
shape. `target` and `missing_by_column` are compact JSON in their columns rather than flattened,
because the table is one row per dataset.

### D3 and D5

Their records have no table yet. `export_records.py` **refuses** a diagnostic it has no table for and
names the ones it supports, rather than writing an empty file under a name a reader would trust.
