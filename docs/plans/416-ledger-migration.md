# Plan — the cost ledger migrates instead of quarantining

**Status:** Proposed — awaiting sign-off.
**Origin:** #416, and the second occurrence recorded there on 2026-11-13.
**Design:** a schema change should rewrite the ledger under the new header, not replace it. Quarantining
was correct when the file was thought to be unreadable; it is a valid CSV with a different column set.

## What happens today

`scripts/gpu_helpers/vast_run.sh` builds a record dict and writes it both as `run_<stamp>.json` and as a row
in `run_ledger.csv`. Before appending, it compares the ledger's header with the record's fields. On a
mismatch it **renames the whole ledger** to `run_ledger.csv.stale-<stamp>` and starts a new file with one row.

That fired again on 2026-11-12 when `credit_before_usd` was added: seven `.stale-*` files now sit in the
directory, the live ledger holds a single row, and **12 runs are missing from it** (#416 records the ids).

The comment in the script says "quarantining loses nothing", because the per-run JSONs are the source of
truth. That is true of the *data* and false of the *file*: a rebuild from JSON cannot restore
`20261104T122235Z`, which is in the ledger and has no record. Quarantining also loses the ordering and any
row whose record was written elsewhere.

## The change

**On header mismatch, migrate.** Read the old rows against the old header, map them by column name into the
new field set, write the union with the new header, then append the new record. A column that did not exist
before becomes empty; a column that no longer exists is dropped and the drop is printed, because a silent
drop is how the columns shifted the first time.

**Fall back to quarantine only when the old file cannot be read** — a truncated or non-CSV file. That keeps
the one case where starting fresh is genuinely the only option, and it prints which case fired.

**Extract it, so it can be tested.** The logic moves out of the unquoted heredoc into
`scripts/gpu_helpers/ledger.py`, and the heredoc keeps only `rec` construction and one call. The heredoc is
unquoted — `$` interpolates — so nothing that needs a literal dollar sign can live there, and the current
code works around that with an escaped `\$` in a comment. A module has no such constraint and can be
imported by a test.

## Shape

```
scripts/gpu_helpers/ledger.py          # new: append(), migrate(), quarantine()
scripts/gpu_helpers/vast_run.sh        # heredoc shrinks to build rec + one call
tests/test_gpu_ledger.py               # new
outputs/gpu-pilot/README.md            # header block matches the writer again
CHANGELOG.md
```

`outputs/gpu-pilot/README.md` is an evidence tree: its "Rebuilding the ledger" section prescribes a header
without `credit_before_usd`, so following it would re-fragment the file on the next launch. The pull request
carries the `evidence-change` label for that one file and nothing else.

## Verification

```sh
./scripts/check.sh shellcheck     # the paid path is shellchecked before it is trusted
.venv/bin/pytest tests/test_gpu_ledger.py -q
./scripts/check.sh                # all eight, with the evidence-change label in CI
```

Plus a direct exercise of the module against the real directory shape: a two-column ledger, a record with
three fields, and the assertion that both old rows survive with the new column empty.

## What this does not do

- Does not rebuild the current ledger or restore the 12 unrecorded runs. That is a separate, deliberate
  evidence change, and it needs the runs' records to be committed first.
- Does not change what a record contains.
- Does not touch `run_<stamp>.json`, which stays the source of truth.
