# Plan — the runs ledger covers regression as well as classification

**Status:** Current — issue #668 (map #663; ledger #665, published #666).
**Scope:** the generator, its two outputs (CSV + campaign document), and the tests. No capture is
touched, no metric is invented, and no verdict moves.

## Why

The ledger answers "what did we run, and what did it score?" for the fine-tuning classification
campaign. The phase's other half — the frequency/severity fair test and the actuarial baselines —
is regression, recorded in a different record schema, scored with a different metric, and one row
per fold rather than one row per seed. A reader who has the CSV cannot tell which task a row serves
or what the dataset is, and the fair test and baseline Runs are absent from it entirely.

This change makes the one document cross-task. It is the decision already taken on #668: one
document, a campaign registry, two metric blocks, and `fold` in the identity key.

## What changes

- `scripts/analyses/finetuning_runs_ledger.py` — reads a registry of campaigns instead of a fixed
  set of loaders, loads regression captures by the same per-record path shape, and renders the
  document from the CSV it has just written.
- `docs/analyses/data/finetuning_runs_ledger.csv` — regenerated: three new identity columns
  (`problem_type`, `task`, `fold`), one era column, and a regression metric block
  (`rmse`, `verdict_metric`, `verdict_metric_value`).
- `docs/experiments/pilot2-phase2/FINETUNING_RUNS_LEDGER.md` — regenerated at the same path. Now
  cross-task: a dataset × task table, the combined ledger, two summary tables, and one era
  statement.
- `tests/test_finetuning_runs_ledger.py` — the fold key, the blank-is-not-zero rule, regression
  rows and their verdict metric, the task-specific summary, and a pinned comparison against the
  classification values `fd3a58f` published.
- Wiring: the `REPORT_REGISTRY.md` row, the campaign README listing, the `DOCUMENT_AUTHORITY.md`
  row, the CSV column table in `docs/analyses/data/README.md`, and the plans index.

## Decisions

1. **The campaign registry is the scope guard, and every entry is explicit.** Each entry carries a
   campaign id, `problem_type`, the dataset → task mapping, the arm labels, the identity key (with
   or without `fold`), the metric block, the era and the record path shape. Runs are selected by
   campaign membership and dataset, never by "has an `ft` arm": six fair-test directories and the
   baseline directories carry the same labels as the pilot, and a label-based selector would merge
   three campaigns into one.

   The regression sources are:
   - `fair-test-freq-sev` — `20261112T164543Z`, `20261112T184155Z`, `20261112T210029Z`,
     `20261112T220641Z` (the four registered targets).
   - `actuarial-baseline-full` — `20261113T223000Z`–`20261113T223003Z` (whole-fold-pool baselines).
   - `actuarial-baseline-matched` — `20261114T003000Z`–`20261114T003003Z` (the 10,000-row
     sensitivity arm).

   The two baseline budgets are separate registry entries for a reason in the evidence, not for
   tidiness: on `spanish_motor_severity` both run ids capture the *same fit* (the fold pool has
   fewer than 10,000 rows), so `(campaign, dataset, arm, seed, fold, train_rows)` would repeat if
   the budgets shared a campaign id. The budget arm is part of the identity.

   Two further captures in the same campaign are deliberately **out** of the ledger:
   `20261113T003320Z` and `20261113T095502Z` are the #572 row-scaling arms, "neither one of the
   four the verdict is registered on" (`freq_sev_fair_test_result.md`), and the fair-test result
   reports them separately. They are not silently missing; the document names them and says why.

2. **One identity key, with `fold` where the evidence has folds.** `(campaign, dataset, arm, seed,
   fold, train_rows)`. Classification rows carry `fold` blank — the records are `seed<N>_foldNone`
   — so a five-fold regression cell stays five rows and no regression cell collapses into one. The
   generator asserts the whole key is unique across both blocks rather than counting rows.

3. **The task and the fold are read from the record, then asserted against the registry.** Every
   regression record names `task`, `fold`, `n_folds`, `train_rows`, `rmse`, `verdict_metric` and
   `verdict_metric_value`. The registry's dataset → task mapping is checked against the record; a
   disagreement fails the ledger. The severity metric is read, never assumed: French severity
   records `rmse` (its weight is exactly 1) and Spanish severity records `weighted_rmse`. `n_folds`
   must be 5.

4. **Two metric blocks, and a blank is "not applicable".** Classification: `roc_auc`, `brier`,
   `pr_auc`. Regression: `rmse` and the record's own verdict metric plus its value. The blocks are
   disjoint per row, and a blank cell is rendered blank — never `0`. The one legitimate numeric
   zero is `epochs = 0` on a regression raw control, which is a recorded epoch count and keeps its
   zero.

5. **`arm_kind` learns the third baseline label.** The ticket names `E_glm` and `F_catboost`; the
   baseline captures also carry `M_intercept`, the intercept-only anchor
   (`actuarial_baseline_result.md`). All three are comparator Methods, `A_raw` is raw, `B_ft30` is
   fine-tuned. `arm_kind` is still derived and declared.

6. **Era is labelled, and nothing is subtracted across it.** Regression Runs are `v3_default`: their
   weights block names `tabpfn-v3-regressor-v3_default.ckpt`. Classification rows keep what the
   record says, `auto`, with the classifier checkpoint beside it; that value names no version and
   the ledger does not re-describe it as v3.5. No row in this ledger is v3.5, and no table compares
   one era or one model family with another.

7. **The summary carries each task's own block.** Grouped by `problem_type`, dataset, arm and
   training rows over current rows only. Classification reports `n`, mean and min–max for ROC AUC,
   Brier and PR-AUC; regression reports them for RMSE and the verdict metric, with the metric named
   per line because it differs by dataset. Still descriptive: no interval, and `n = 1` still says
   `single run`.

8. **The dataset table closes the gap the reader hit.** One row per dataset with its task, problem
   type, what it is and which campaigns ran it. The dataset, task and problem type are read from the
   CSV; the description is curated from the campaigns' own target tables and names the unit and
   target, so a regression row's `rmse` is not read as an AUC.

## What is out of scope

No re-run, no backfilled metric, no repair of `results/INDEX.md`, no new figure, and no change to a
committed capture — so `./scripts/check.sh evidence` stays a no-op. The row-scaling arms (#572) stay
with the fair-test result, as decided above, and the frontier benchmark stays out, as on #663.

## Evidence this works

- `python scripts/analyses/finetuning_runs_ledger.py` twice: byte-identical CSV and document.
- `.venv/bin/pytest tests/test_finetuning_runs_ledger.py -q` — the existing traps plus the fold key,
  the blank-is-not-zero rule, the regression rows and the pinned classification values.
- `PATH="$PWD/.venv/bin:$PATH" ./scripts/check.sh` — all eight green.

## Rows this lands

| Block | Campaigns | Rows | Status |
| --- | --- | --- | --- |
| Classification | `pilot2-phase2`, `r1-pilot`, `gpu-pilot`, `pilot2-breadth-spanish` | 602 | as published in `fd3a58f` |
| Regression | `fair-test-freq-sev` | 120 | current |
| Regression | `actuarial-baseline-full` | 180 | current |
| Regression | `actuarial-baseline-matched` | 180 | current |

The counts above are the claim; the generator recomputes them from the evidence and the document
prints what it found.
