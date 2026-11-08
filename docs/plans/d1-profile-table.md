# Plan — D1 runs, and its table lands (#302's diagnostic, #407's readout)

**Status:** Current — delivered 2026-11-07.
**Origin:** chore. D1's tool is #302 (closed) and the exporter is #407 (closed); neither had ever
produced a table. No new capability, so no ticket.
**Design:** `docs/current/FINETUNING_DIAGNOSTICS_DESIGN.md` §D1.

## Scope

D1 had a tool, a table shape and no table: `scripts/diagnostics/d1_profiling.py` was built in #302,
one dated record existed (a single-dataset run kept for D5's citation), and
`docs/analyses/data/README.md` said "not present yet" under that heading. #407 built the D1 export
path and could only test it against a hand-built record, because there was no four-dataset run to
point it at.

Three deliverables:

1. **Run D1 on the four anchor datasets.** `python3 scripts/diagnostics/d1_profiling.py
   --all-anchors`, $0, no model fits. Four records under
   `outputs/diagnostics/d1_profiling/20261107T112100Z-<dataset>/`. `time` on that command measured
   **9.6 s** wall clock on 2026-11-07 (8-core CPU). The four profiles are ~0.5 s of it; ~6 s is
   `runtime_versions()` importing torch, tabpfn and catboost to stamp the record — measured
   separately, because "9.6 s" is not a profile of the profiling.
2. **Commit those records as fixtures** under `tests/fixtures/diagnostics/d1_profiling/`, the same
   way #407 committed D2's, so the table can be regenerated in CI.
3. **`docs/analyses/data/d1_profiling.csv`** — one row per dataset — and the README section that
   names its columns.

## Decisions worth arguing with

**A fresh run rather than the one D1 record that already existed.** `issue-306`'s worktree held a
single `20261106T-d5-cites-d1-eudirectlapse` record, written so D5 could cite D1. It is genuine and
its `dataset_sha256` matches the manifest, but a one-dataset table is not the design's "one row per
dataset", and exporting both would give `eudirectlapse` two rows — which the exporter refuses, on
purpose. So the table is built from one run of all four datasets, and the older record is committed
beside it as `d1_profiling-repro/` evidence rather than exported.

**A second run is a test, not a story.** D1's `--all-anchors` output is a deterministic function of
a committed CSV, and #302's acceptance criteria ask for exactly that: "a second run with the same
inputs produces the same values". The 6 November record is committed under
`tests/fixtures/diagnostics/d1_profiling-repro/` so the comparison is checkable from a clean checkout
rather than made once on the author's machine: identical values for all seventeen measurements and an
identical `dataset_sha256`, with `record_sha` differing because it hashes the record file
(`created_utc`, `git_sha` and all), not the measurement.

**The table is of the CSV, not of the fitted width.** `spanish_motor_lapse` declares two leak-drops
in the pilot's loader (#444), so the model sees 20 features where the file has 22. D1 profiles the
file, as D2 does (it also reports 22), and the README states the gap. Changing D1 to apply loader
declarations is a change to the diagnostic, not to this readout, and is not done here.

The readings themselves — `coil2000`'s near-duplicate pair, the 0.990542 that reproduces D5's figure,
the absence of missingness — are in the README beside the table, written once rather than restated
here.

## Shape

```
tests/fixtures/diagnostics/d1_profiling/<run id>/record.json        # 4 records, byte-for-byte
tests/fixtures/diagnostics/d1_profiling-repro/<run id>/record.json  # the second run, compared not exported
docs/analyses/data/d1_profiling.csv                                 # one row per dataset
docs/analyses/data/README.md                                        # the D1 columns, and the absence note replaced
tests/test_export_records.py                                        # table, hash, recomputation, reproducibility
```

## Verification

```sh
out="$(mktemp -d)"
python3 scripts/diagnostics/export_records.py \
    --run tests/fixtures/diagnostics/d1_profiling --out-dir "$out"
diff "$out/d1_profiling.csv" docs/analyses/data/d1_profiling.csv   # empty
./scripts/check.sh                                                  # all eight green
```

Run on 2026-11-08 (8-core CPU, 689-test suite — the count as it stands, this change's two tests
included): the diff was empty and all eight checks passed, the suite in 347 s.

`tests/test_export_records.py` gains the checks #302's acceptance criteria name rather than only the
ones that are convenient:

* the committed D1 table equals a fresh export of the committed fixtures byte-for-byte;
* every row's `dataset_sha256` matches `data/raw/MANIFEST.sha256` and its `record_sha` matches the
  fixture it came from;
* **the record agrees with the file it names** — `n_rows`, `n_cols`, the missingness totals and the
  target's positive rate are recomputed from `data/raw/<dataset>.csv` and compared, which is #302's
  wrongness check and would fail on a record carrying the right hash and a wrong count;
* the two-run comparison above, and the internal invariants `n_features + 1 == n_cols` and
  `n_numeric + n_categorical == n_features`.

## What this does not do

It does not run D3, D4 or D5, and it does not write the diagnostics report — the report is where a
reading of these numbers belongs, and D3/D4 have not run. It does not re-derive D2's table, which is
the rows of a different run and is unaffected: the two tables are separate files.
