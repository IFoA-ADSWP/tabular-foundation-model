# Plan — a diagnostics record becomes a table a reviewer can open (#407)

**Status:** Current — delivered 2026-11-07.
**Origin:** ticket #407, which came out of D2 (#303).
**Design:** `docs/current/FINETUNING_DIAGNOSTICS_DESIGN.md` §D1, §D2 · **Record shape:** `src/provenance.py`.

## Scope

Every diagnostic writes its record to `outputs/diagnostics/`, which `.gitignore` excludes. That is
deliberate — records are runtime evidence — but it makes the campaign unreadable: an acceptance
criterion of the form "one record per dataset" cannot be checked from a diff, and D2 shipped its
result as prose in a pull request because there was nowhere else for it to live.

Three deliverables:

1. **`scripts/diagnostics/export_records.py`** (logic in `src/diagnostics_export.py`, following the
   `scripts/analyses/export_predictions.py` → `src/predictions_export.py` split) writes one committed
   table per diagnostic into `docs/analyses/data/`:
   * `d2_importance.csv` — one row per dataset × family × feature.
   * `d1_profiling.csv` — one row per dataset.
2. **The D2 table, committed.** Four `d2_importance` records exist on disk (from #303). They are
   copied byte-for-byte into `tests/fixtures/diagnostics/d2_importance/` and the table is exported
   from them, so the table can be regenerated in CI.
3. **A section in `docs/analyses/data/README.md`** naming each table's columns and the bytes each
   row rests on, and stating which tables are **absent** and why.

## Decisions worth arguing with

**The four D2 records are committed, as fixtures.** The acceptance criterion is "reproduces a
committed table byte-for-byte from a fixture record", and that is untestable in CI unless the input
bytes are in the tree: `outputs/diagnostics/` is git-ignored, so a test that re-exported from there
would skip or fail on every clean checkout. `.gitignore` already permits this — *"commit a record
deliberately if it becomes evidence"* — and here it is evidence: it is the input the committed table
rests on. Total cost: 96 KB across four records. The alternative (commit the table, leave the input
unreachable) makes the table a claim nothing can re-derive.

**The dataset hash is checked against `data/raw/MANIFEST.sha256`, not just copied.** `export_predictions`
refuses unless the arrays match `capture.json`; the equivalent here is that the record's
`dataset_sha256` must equal the manifest entry for that dataset's committed CSV. This is the part a
reviewer can actually check from the tree: `dataset_sha256` in the table → `grep` it in
`data/raw/MANIFEST.sha256` → the raw bytes the run read. A mismatch refuses and names both values.

**A record for a dataset outside the manifest is refused, not exported with a blank hash.** An
ad-hoc `--csv` run has no committed bytes to rest on, so its table could not be verified — and a
table whose whole purpose is being checkable should not quietly ship an uncheckable row. The refusal
names the dataset and the manifest, so the next person knows what to fix.

**One table per diagnostic, rebuilt from every record named.** `--run` is repeatable and accepts
either a record directory (holds `record.json`) or a directory of them. The file written is exactly
the rows of the runs named, sorted by `(dataset, family, rank)` — so passing the same input twice, in
any argument order, produces the same bytes. Passing the diagnostic directory
(`outputs/diagnostics/d2_importance/`) is how all four datasets land in one table **while it holds
one run per dataset**, which it does today. Two consequences worth stating: exporting one dataset on
its own **replaces** the table with that dataset's rows, and **a second run of a dataset already
named is refused**, because the table's key is `(dataset, family, feature)` — two runs would put two
`rank` 1 rows in one family, and "top ten" would stop meaning ten features. Records accumulate (the
writer never overwrites one), so after the next D2 run the command names record directories per run
rather than the diagnostic directory; the refusal says so. Both consequences are in the README.

**The rows carry the model version, because the numbers are meaningless without it.** `AGENTS.md`
makes version pinning load-bearing, and a D2 table whose reader cannot see that the TabPFN arm was
v2.5 would invite exactly the comparison across eras the repo forbids. Two columns, not one:
`model_version_requested` is what the diagnostic *asked* for (`auto` — a request, not a version, per
#285) and `model_resolved_version` is what the library resolved (`v2.5`). The first is named
`…_requested` because plain `model_version` means the resolved label everywhere else in this repo,
and a column that quietly redefined it would be the D20 defect in a header.

**No wall-clock columns.** An `exported_at` column would make every re-export a diff and break
byte-for-byte reproduction; `run_id` already names the run, and the sort order does not need it
because `(dataset, family, rank)` cannot tie. `created_utc`, `git_sha` and `runtime` stay in the
record — they describe the run, not the table.

**D1's nested blocks are JSON-encoded, using `provenance.csv_cell`.** `missing_by_column` and
`target` are mappings and the ticket asks for one row per dataset, so the two blocks become compact
sorted-JSON columns. Reusing `csv_cell` means the table and `record.csv` cannot disagree about how a
bool or a null is spelled.

**D3 and D5 are not supported yet, and the exporter says so.** The ticket names D1 and D2; a D3 or
D5 record is refused with the supported list rather than exported as an empty table. Those tables
land when each diagnostic is next run, which is also why D1's table is absent (no D1 record exists on
disk) — the README states the absence instead of implying all five diagnostics are present.

## Shape

```
src/diagnostics_export.py          # rows, ordering, verification, writer
scripts/diagnostics/export_records.py   # thin CLI shim
tests/test_export_records.py       # seam: the bytes on disk
tests/fixtures/diagnostics/d2_importance/<run id>/record.json   # 4 records, byte-for-byte
docs/analyses/data/d2_importance.csv
docs/analyses/data/README.md       # new section
```

`d2_importance.csv` columns: `run_id, dataset, family, rank, feature, importance, std,
univariate_auc, test_auc, no_better_than_chance, model_version_requested, model_resolved_version,
dataset_sha256, record_sha`.

That column set is the ticket's "enough to reconstruct a top-ten and the three readings without the
JSON": `rank <= 10` is the top ten per family; Spearman over the rankings, top-k set differences and
their Jaccard, and the tree-only screen (`rank <= 10` outside the other families' top ten with
`|univariate_auc - 0.5| < 0.02`) are all functions of `rank` and `univariate_auc` alone. The README
spells the three computations out.

`d1_profiling.csv` columns: `run_id, dataset, n_rows, n_cols, n_features, n_numeric_features,
n_categorical_features, numeric_to_categorical_ratio, n_features_after_one_hot, feature_row_ratio,
missing_rate, n_cols_with_missing, max_col_missing_rate, n_high_cardinality_features, max_vif,
vif_reason, max_abs_feature_correlation, target, missing_by_column, dataset_sha256, record_sha`.

## Verification

```sh
out="$(mktemp -d)"
python3 scripts/diagnostics/export_records.py \
    --run tests/fixtures/diagnostics/d2_importance --out-dir "$out"
diff "$out/d2_importance.csv" docs/analyses/data/d2_importance.csv   # empty
./scripts/check.sh                                                    # all eight green
```

Run on 2026-11-07, in the commit that carries this plan: the diff was empty and `./scripts/check.sh`
passed all eight checks (685 tests, 344 s). The four committed records measure 96 KB.

`tests/test_export_records.py` asserts: the committed table equals a fresh export byte-for-byte; two
exports of the same fixtures are identical; argument order does not change the bytes; each row's
`dataset_sha256` matches `data/raw/MANIFEST.sha256`; a tampered hash refuses and writes nothing; an
unsupported diagnostic refuses; a missing measurement key refuses and names the key; a second run of
a dataset already in the table refuses; every row names the model version it was measured with and
the chance flag agrees with the test AUC it summarises; D1's nested columns round-trip through
`json.loads`; and the three readings can be reconstructed from the CSV alone.

## What this does not do

It does not run any diagnostic, does not export D3 or D5, and does not commit an `outputs/` tree. It
does not add a CI `--check` mode: the test already compares the committed table to a fresh export,
which is the same guarantee with one fewer flag to document.
