# Plan — the fine-tuning runs ledger

**Status:** Current — issue #665 (map #663; inventory #664).
**Scope:** the generator, its two outputs (CSV + campaign document), and the tests. The
`DOCUMENT_AUTHORITY.md` row and the close-out review are #666.

## Why

The fine-tuning programme's run inventory lives in prose spread over a design, two
pre-registrations, three result documents, a decision log and an inventory note. A reader asking
"what did we run, and what did it score?" has to assemble it from six pages, and the numbers that
are easiest to misread — epochs, seeds, training rows, which rows are still current — are the ones
restated by hand in each of them.

The inventory note (`research/finetuning-runs-inventory`, `e53c452`) settled what the evidence
actually records. This change turns that into one generated table so the inventory is derived, not
remembered.

## What changes

- `scripts/analyses/finetuning_runs_ledger.py` — reads the committed evidence and writes both
  outputs. Follows the neighbours in `scripts/analyses/`: a docstring that states the trap, a
  module-level constant per source, `main(argv)`, no editorialising in code.
- `docs/analyses/data/finetuning_runs_ledger.csv` — the machine form, one row per run × arm × seed.
- `docs/experiments/pilot2-phase2/FINETUNING_RUNS_LEDGER.md` — the campaign document: the ledger
  table, the rows that are not plainly current, and the dataset × arm × training-rows summary. Its
  tables are rendered **from the CSV**, so the two forms cannot disagree.
- `tests/test_finetuning_runs_ledger.py` — determinism, the epoch trap, the `train_rows` key, the
  seed-disjointness assertion, the `coil2000` withdrawal, the Spanish `no-capture` rows, and the
  scope guard.
- Wiring: `docs/REPORT_REGISTRY.md` row, `docs/experiments/pilot2-phase2/README.md` listing and
  document count, `docs/EXPERIMENTS.md` live count, and a section in `docs/analyses/data/README.md`
  for the new table.

## Decisions

1. **The campaign's own run list is the scope guard.** `docs/experiments/pilot2-phase2/README.md`
   has a `## Runs` block naming its 23 committed Runs; the generator reads that, intersects it with
   `results/` and refuses a named run that has no capture. A generator that globbed
   `results/*/capture.json` for "has an `ft` arm" would take the six fair-test directories (#552's
   campaign) whose arms are the same `A_raw` / `B_ft30` labels. `docstatus` already holds that
   block's count to `docs/EXPERIMENTS.md`, so the selector and the campaign index cannot drift.
2. **Epochs from `effective_config.kwargs.epochs`, asserted against the `ftN` label.** `config.epochs`
   and every Run manifest read `3`, including the 30-epoch arm; the anchor's `B_ft10` record is the
   live case. A disagreement fails the generator instead of being smoothed, and an arm with no
   `ftN` label that nonetheless records epochs also fails — there is no label to check it against.
3. **The cell key is `(dataset, arm, seed, train_rows)`.** `uslapseagent` seed 42 exists at 2,000
   rows (R1 pilot) and 10,000 (the `gpu-pilot` launch); a three-part key would mark real evidence
   superseded.
4. **Replacement detection is an assertion, not a diff.** The committed evidence is seed-disjoint by
   construction (three duplicate launches were discarded before commit, so their ids do not exist),
   so mechanical detection returns zero and the generator asserts it. Supersession is curated: the
   four `coil2000` pilot-aggregate rows, withdrawn under D21 and amended by D22.
5. **`no-capture` is a status, not a footnote.** The `outputs/gpu-pilot/` launch records and the
   Spanish breadth cell have no `capture.json`, so they cannot be cited as a Capture. They are
   listed with their real metrics where a record carries them (the launch) and blank where none was
   ever committed (the breadth cell), with the pointer a reader should cite instead.
6. **The summary excludes `superseded` and `no-capture` rows and carries no interval.** It is
   `n`, mean and min–max, computed from the CSV. Its key includes `train_rows` because the ledger's
   key does: a mean over 2,000-row and 10,000-row cells is not a mean of one thing.
7. **`arm_kind` is derived and declared.** `A_raw` → raw; `B_ft*` and `B_in_domain` → fine-tuned;
   `E_glm` / `F_catboost` → comparator, because the glossary's baseline is a Method, not an Arm.
8. **Three metrics, and the model version as recorded.** ROC AUC, Brier, PR-AUC. `log_loss` and
   `ece` are recorded everywhere and deliberately out. `model_version` is `auto` where a record
   says `auto`, with the checkpoint and weights sha beside it; never `v3`.

## What is out of scope

The authority row in `DOCUMENT_AUTHORITY.md` (#666). No re-run, no metric the evidence does not
record, no repair of `results/INDEX.md`, and no change to any committed capture — so
`./scripts/check.sh evidence` must stay green.

## Evidence this works

- `python scripts/analyses/finetuning_runs_ledger.py` twice: byte-identical CSV and document
  (`sha256sum` compared), because rows are sorted on a total key and floats are formatted to fixed
  precision.
- `.venv/bin/pytest tests/test_finetuning_runs_ledger.py -q` — the seven checks above.
- `PATH="$PWD/.venv/bin:$PATH" ./scripts/check.sh` — all eight green.

## Rows this lands

| Source | Rows | Status |
| --- | --- | --- |
| 23 `pilot2-phase2` captures | 580 | current |
| `outputs/finetune/pilot/pilot_metrics.parquet` (2,000 rows, seed 42) | 16 | 12 current, 4 superseded |
| `outputs/gpu-pilot/runs/20260914T010247Z` (10,000 rows, seed 42) | 4 | no-capture |
| `spanish_motor_lapse` breadth cell (curated, no committed record) | 2 | no-capture |

The counts above are the claim; the generator recomputes them from the evidence and the document
under `docs/experiments/pilot2-phase2/` prints what it found.
