# Plan — the runs ledger reads both launch-record layouts

**Status:** Current — issue #678 (ladder evidence #672, #674; ledger #668, #671).
**Scope:** the launch loader, the `gpu-pilot` registry entry, the two generated ledger outputs and
the tests. No record is moved, no metric is invented, and no verdict moves. **Depends on #679**,
which widens the citation rule; without it `check citation` is red on this branch alone.

## Why

The ledger's `gpu-pilot` source globbed `outputs/gpu-pilot/runs/<run>/<dataset>/<arm>/meta.json`.
That is the 2026-09-14 launch's layout. The 2026-11-21 ladder runs write one level deeper —
`<run>/<dataset>/<arm>/seed<N>_foldNone/meta.json` — because the launcher now names the seed in a
directory as well as in the record. The loader matched nothing under those Runs, so the 192
records the ladder banked in #677 (112 `uslapseagent` at 2,000 and 5,000 rows, 80 `eudirectlapse`
at 10,000) were invisible: the ledger showed `gpu-pilot` 4 rows and claimed to be the complete
record of committed Runs.

The fix is a second path shape, not a second source. Both layouts are one campaign's launch
records, with the same status, the same metric extraction and the same arm-kind derivation.

## What changes

- `scripts/analyses/finetuning_runs_ledger.py` — `launch_rows` reads both layouts; a layout helper
  derives `dataset` and `arm` from the path, reads `seed` from the record, and refuses a seed
  directory that disagrees with it. The `gpu-pilot` registry entry gains `eudirectlapse` and names
  both record paths in the source table.
- `docs/analyses/data/finetuning_runs_ledger.csv` — regenerated: 192 new `no-capture` rows.
- `docs/experiments/pilot2-phase2/FINETUNING_RUNS_LEDGER.md` — regenerated from the CSV. The
  `gpu-pilot` source row names both layouts, and the `gpu-pilot` count moves from 4 to 196.
- `tests/test_finetuning_runs_ledger.py` — a fixture for each layout, one for a seed directory that
  disagrees with its record, one for a record with no `arm`, the live-tree counts, and a check
  that the pointer rows stay out of the summary.
- `docs/plans/README.md` — this plan listed in the index.

The citation gate is **not** touched here. These are the first post-rule citations of a run with
no Capture, and changing what the gate accepts is a rule change a human should review on its own:
it ships as #679 (plan `docs/plans/679-launch-citation.md`), and this branch depends on it.

## Decisions

1. **The path selects the record; the record supplies the numbers.** Dataset and arm are path
   parts, because the path is what places a record in a cell. The seed is the record's own field,
   because the record is the claim about what ran. Where the path also names a seed, the two must
   agree: a directory saying `seed56` around a record saying `seed55` is two claims about one
   file, and the loader exits rather than choosing one. The record's `dataset` and `arm` are
   asserted against the path for the same reason, and a record with no `arm` still raises — a
   `continue` would make the document's "nothing was dropped" false while still printing a total.

2. **Both layouts yield `no-capture` rows.** The ladder records carry metrics and weights bytes but
   no `capture.json`, exactly as the 2026-09-14 launch does, so they are cited by description and
   excluded from the summary. `summarise` already filters on `status == "current"`; the change adds
   no exception, and a test pins that no `gpu-pilot` line appears in the summary tables.

3. **`eudirectlapse` joins the campaign's datasets, not a new campaign.** The ladder's EU cell is
   the same campaign, same arms and same record schema as its US cell; a separate campaign id would
   repeat the identity key's role for no reason in the evidence. The arm labels already cover it:
   `A_raw`, `B_ft3`, `B_ft10`, `B_ft30`.

4. **Epochs still come from the record, and the ladder records one.** The 2026-11-21 fine-tuned
   arms carry `effective_config.kwargs.epochs` (3, 10 and 30), so a `B_ft30` ladder row reads 30 and
   is asserted against its label exactly as the 2026-09-14 rows are. The ladder's `A_raw` records
   no epoch count, which is a raw control doing no training, and the row's `epochs` stays blank —
   never inferred from the arm label.

5. **The citation rule is #679's, not this change's.** These are the first post-rule citations of
   a run with no Capture: the citation gate knows only `results/<id>/capture.json`, and
   `legacy_citations.txt` is closed to ids after 2026-10-31 on purpose. Adding the ids there
   would be the grandfathering the rule exists to prevent, and teaching the gate a new evidence
   form is a policy change that should not ride in on a loader fix. It ships separately as #679,
   which accepts `outputs/gpu-pilot/runs/<id>/` when the tree exists and every record names its
   seed. **Until #679 lands, `check citation` fails on this branch alone** — that is the
   dependency, not a workaround to be found here.

## Verification

Before: `gpu-pilot` 4 rows, ledger 1082 rows.

```
./scripts/bootstrap_dev.sh
.venv/bin/python scripts/analyses/finetuning_runs_ledger.py
PATH="$PWD/.venv/bin:$PATH" ./scripts/check.sh
```

Seven of the eight checks are green on this branch; `check citation` is red until #679 merges,
because the regenerated CSV and Markdown cite the 15 ladder run ids and the current gate knows only
`results/<id>/capture.json`. Nothing here works around that: the failure is the dependency, and
the PR says so.

After: `gpu-pilot` 196 rows (192 ladder + the unchanged 4), ledger 1274 rows. The generator's
output is checked against the committed CSV and Markdown by
`test_the_committed_artefacts_are_byte_identical_to_a_fresh_render`, so regenerating twice and
diffing is the same assertion.

The only prose that moves besides the counts: the pin sentence's denominator becomes 794
classification rows (the count recording no version stays 22 — the old flat launch's 4 plus the 16
pilot rows and the 2 curated cells), the `eudirectlapse` dataset row's campaign list gains
`gpu-pilot`, and the flagged-row count becomes 198. The summary tables do not move, because every
new row is `no-capture`.
