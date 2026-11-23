# Plan — the paper-facing fine-tuning results matrix (#739)

**Status:** current — implemented and checked, 2026-11-23.

Parent: #44 (the paper deliverable). The paper needs one table that lines up the in-domain
fine-tuning results across lapse, frequency and severity. The pieces exist — the runs ledger, three
result notes and two designs — but no single artifact presents them, and the ledger deliberately
excludes the epoch ladder and has no verdict column.

## What

- `docs/shared/FINETUNING_RESULTS_MATRIX.md` — the paper-facing tables and the caveats: one model
  line, in-domain only, both arms TabPFN, eligible versus training rows, lapse is not folded, the
  unreported log-loss estimand, `coil2000` is not a lapse target, the two severity units, the
  exploratory status of the ladder, and the Spanish frequency power gap.
- `docs/analyses/data/finetuning_results_matrix.csv` — the same rows, machine-readable.
- `scripts/analyses/finetuning_results_matrix.py` — recomputes fair-test and row-scaling cells
  through `freq_sev_fair_test.build_summary()`, quotes the lapse and ladder result tables, and
  renders both files. `--check` fails on drift.
- `tests/test_finetuning_results_matrix.py` — checks that every quoted number appears in its owner,
  that fair-test cells reproduce the analysis, that design axes agree with the ledger where the
  ledger covers the family, and that the ladder's absence from the ledger is deliberate.
- `REPORT_REGISTRY.md`, `DOCUMENT_AUTHORITY.md`, `CHANGELOG.md`, this plan and its index row.

## Verification

- `pytest tests/test_finetuning_results_matrix.py` — 7 passed.
- `python scripts/analyses/finetuning_results_matrix.py --check` — matrix and CSV match.
- `check.sh doclinks`, `docstatus`, `citation`, `evidence`, `ruff` — pass; full `pytest` in CI.

## Out of scope

- Any new run or capture.
- The missing Phase 2 log-loss estimand (stated as a gap, not computed here).
- The ladder itself, already owned by `EPOCH_LADDER_RESULT.md`.
