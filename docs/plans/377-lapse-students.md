# Plan — measure the lapse GBDTs instead of estimating them

**Issue:** #377 (wayfinder:task under map #368). Feeds #373.
**Status:** Current.

## What and why

#370 could only quote **estimates** for the two lapse Datasets: CatBoost/XGBoost/RandomForest
were never fitted at full size, so the Spanish Motor Lapse headroom (`~0.005–0.012 AUC`) came
from a 2,000-row pilot subsample, and EU Direct Lapse's negative sign rested on a `LinearModel`
proxy. Both CatBoost, XGBoost and RandomForest exist in `scripts/benchmarks/run_lapse_benchmark.py`
only as comments under `# --- Deferred to the GPU run ---`.

This ticket turns those cells into measurements on the teacher's own five folds, reusing the
committed teacher scores. No spend, no GPU, no hosted call, no protocol change.

## The two findings that shape the implementation

### 1. `LinearModel` is **not** the pinned `logistic_regression`

`scripts/eval/lapse_benchmark_v1/method_info.csv` records the committed LR row as
`ta_name = [Lapse] LinearModel`, `ta_suite = [Lapse] LinearModel`,
`config_default = LinearModel_c1_default_HOLDOUT`. That is **TabArena's** `LinearModel`, not
`src/baseline_config.py`'s `logistic_regression: {"max_iter": 1000}`. #370 could not settle this
because TabArena is not vendored; the committed `method_info.csv` does settle it, because it is
the harness's own description of what it ran.

So the existing `[Lapse] LR (default)` row stays named `LinearModel` and is **not** renamed, and
it does not count as a pinned student. This ticket fits `logistic_regression` proper as a
separate student and reports both, so the difference is visible instead of assumed.

### 2. `run_lapse_benchmark.py` cannot run in this environment — and must not

The script imports `tabarena` (`TabArenaV0pt1ExperimentBundle`, `UserTask`), which is not
installed here and is not in `requirements.txt`/`requirements.lock`; its documented venv
(`/tmp/tabarena/.venv-ta`) no longer exists. Installing a fresh `tabarena` would fit students
under a harness generation nobody can tie to the Aug-2026 rows the teacher came from, i.e. a new
era, not a reproduction. Running it would also call the hosted teacher (`TabPFNClientModel`),
which this ticket forbids.

The students are therefore **enabled in the script** (the ticket's literal ask, so the next
TabArena-box run has the full panel) and **not executed**. The measurement is made by a new
CPU-only script that touches no TabArena code and imports no `tabpfn_client`.

## What changes

| File | Change | Why |
| --- | --- | --- |
| `scripts/benchmarks/run_lapse_benchmark.py` | uncomment `XGBoost`, `CatBoost`, `RandomForest` under the deferred marker; keep `LogisticGlmModel` deferred and say why | the ticket's ask; the panel is recorded for the next TabArena run |
| `scripts/benchmarks/measure_lapse_students.py` | **new**: rebuild the 5 folds, fit the four pinned students, reuse the teacher's committed per-fold scores, write the Record | the measurement, without TabArena and without the teacher |
| `results/20261031-lapse-students/` | **new**: `per_fold.csv`, `record.json`, `predictions/*.npz` | the committed output #370 lost to `/tmp/opencode` |
| `tests/test_lapse_students_record.py` | **new**: the committed Record parses and is `comparable`; teacher rows reproduce the committed v3 numbers; every student has 5 folds × 2 Datasets; no teacher Brier is invented | the omission that caused this ticket becomes a failing test |
| `docs/plans/377-lapse-students.md` | this plan | AGENTS.md |

No file under `data/` is read differently, no committed result is rewritten, and the existing
`results_per_split.csv` is read only.

## Method — the measurement, precisely

**Folds.** `StratifiedKFold(5, shuffle=True, random_state=42)` over `data/raw/<file>` after
`dropna(target)`, exactly the rule the lapse benchmark constructs. The fold construction is
recorded as a rule (`src/provenance.split_rule`), not prose.

**Teacher (reuse, never refit).** Per-fold AUC read from the committed
`scripts/eval/lapse_benchmark_v1/results_per_split.csv`, rows `method == "[Lapse] TabPFNClient
(default)"`, `auc = 1 − metric_error`. The file's sha256 is recorded so the reused rows are
pinned.

**Teacher Brier — not measurable, and said so.** The committed lapse record carries `roc_auc`
and `rmse` only. Teacher Brier on the canonical folds cannot be produced without a hosted call,
so it is recorded as `null` with a reason, not estimated, not back-filled from the 2,000-row
pilot.

**Students (fit here, CPU).** The four pinned in `src/baseline_config.py`:
`catboost {iterations:100, verbose:0}`, `xgboost {n_estimators:100, random_state:42}`,
`random_forest {n_estimators:100, random_state:42}`, `logistic_regression {max_iter:1000}`.
Parameters come from `BASELINE_MODELS` rather than being retyped. Brier and AUC are computed per
fold from `predict_proba[:, 1]`.

The pinned `logistic_regression` carries no scaler, and lbfgs reports non-convergence on raw
category codes, so a **sensitivity** arm (`logistic_regression_scaled`: the same pinned model
behind a `StandardScaler`) is fitted too. It is labelled a sensitivity arm, never a pinned
student, and exists so the headline assumes neither that the pinned config is broken nor that it
is fine.

**Preprocessing, and the asymmetry it creates.** The teacher rows were produced by TabArena's
pipeline, which is not in the tree; the students are fitted under the repo's own home-harness
convention (`object`/`category` → `.cat.codes`, `fillna(0)`, `float32`) — the same convention
that produced the **measured** coil2000/uslapseagent student rows in #370. The pipeline is
therefore asymmetric against the reused teacher, which is a named limitation of the gap, not a
hidden one. It is quantified with a **LightGBM control**: `LGBMClassifier(random_state=0,
device_type="cpu", verbose=-1)` is fitted on the same folds and diffed against the committed
`[Lapse] GBM (default)` row that TabArena produced. Agreement there is the evidence that the
home pipeline and the folds land where the committed teacher rows landed; disagreement is
reported, not smoothed.

**Version-era guard.** Re-scored teacher means must reproduce the committed `v3_default` values —
0.610066 (`eudirectlapse`) and 0.755255 (`spanish_motor_lapse`) to 1e-6 — or the script exits
non-zero and writes nothing. A mismatch means the reused rows are a different generation, and
mixing eras is forbidden by `docs/MODEL_VERSIONS.md`.

**Cost guard.** The script imports no host, reads no API key, and has no teacher code path at
all; `TABPFN_MODEL_PATH` is irrelevant to it. The record states the teacher was reused, with the
source file named and hashed.

## The committed Record

`results/20261031-lapse-students/`:

* `per_fold.csv` — `dataset, dataset_id, fold, method, role, auc, brier, source`.
  `method` is the student's pinned name (`catboost`, `xgboost`, `random_forest`,
  `logistic_regression`); `role` separates `teacher`, `student`, the `LinearModel` and LightGBM
  `committed-proxy` rows, `sensitivity` and `control`. `source` names where each row came from, so
  a reused row can never be mistaken for a fit. The version pin lives once, in `record.json`.
* `predictions/<dataset>__seed42__students.npz` — per-fold `y_true`, `y_pred` and `test_idx` per
  student, so a future rescore does not need a refit (the #370 failure).
* `record.json` — the record contract's one top-level `provenance` block (dataset / split /
  model / code), `schema_version: 2` for the capture kind, and the run-level dataset **list**,
  since two Datasets were measured. A `Verdict` is computed with
  `src.provenance.verdict(record, kind="capture")` and printed; it is never written into the
  record.

## Verification

* `python scripts/benchmarks/measure_lapse_students.py` — teacher means reproduce; LightGBM
  control diff printed; record written once, refusing to overwrite.
* `pytest tests/test_lapse_students_record.py` — the committed record is `comparable`, has five
  folds × five methods × two Datasets, no fabricated teacher Brier, and the teacher rows equal an
  independent re-read of `results_per_split.csv`.
* `ruff check scripts/ src/ tests/`, `pytest tests/ -q`.

## Out of scope

Refitting or re-calling the teacher; tuning any student (the pinned configs are the students);
any change to the 5-fold protocol, the seed, the metrics or the Datasets; installing TabArena;
touching #373's threshold or the map's body; rewriting any existing result.
