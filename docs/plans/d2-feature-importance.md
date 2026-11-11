# Plan — D2 feature importance across TabPFN, GLM and LGBM (#303)

**Status:** Current — delivered 2026-11-04.
**Origin:** ticket #303 under the campaign spec #300.
**Design:** `docs/current/FINETUNING_DIAGNOSTICS_DESIGN.md` §D2 · **Record shape:** ADR 0003.

## Scope

D2 asks what each model family uses, and where they disagree. The design assumed the benchmark's
fitted models could be re-opened; they are not committed — only prediction arrays are — so this
ticket refits all three families locally on a fixed 2,000-row subsample and records that cap.

Three deliverables:

1. **`scripts/diagnostics/d2_importance.py`** — profiles the four anchor datasets through the
   pilot's own registry (`src/anchor_datasets.py`, now shared with D1), fits TabPFN / GLM / LGBM on
   one seeded subsample, and measures permutation importance on held-out rows. One record per
   dataset, through `provenance.write_diagnostic_record`, under
   `outputs/diagnostics/d2_importance/<run id>-<dataset>/`.
2. **The three readings the design names, computed rather than left to the reader.** Each record
   carries enough to answer, per dataset: same features ranked differently (Spearman over the whole
   ranking plus the largest top-10 rank moves), different features entirely (top-10 set differences
   with their Jaccard overlap), and interactions visible only to the tree model (LGBM top-10
   features outside **both** other families' top-10 whose univariate AUC is within 0.02 of a coin
   flip). TabPFN is excluded as well as GLM, because it is itself an interaction learner — a
   feature it ranks first is not "visible only to the tree model".
3. **The wrongness check.** The whole pipeline is repeated on a label-permuted copy of one dataset.
   If a feature dominates there, the measurement is picking up leakage or an artefact.

**The records are git-ignored** (`outputs/diagnostics/`), as D1's and D3's were: they are runtime
evidence, produced by running the script, not committed artefacts. The `--run-id` names the
directory, so a record is reproducible from the command and the seed rather than from a diff.

## Decisions worth arguing with

**The cap is 2,000 rows for the whole working set, not 2,000 training rows.** The ticket asks for
"a fixed 2,000-row subsample" and the record must say the cap. Splitting the cap 1,500 train / 500
test keeps that number literally true and keeps the words in the record unambiguous. Importance on
500 rows is noisier than on more; the record states the test-row count so a reader can discount it.

**Permutation importance on held-out rows, not refits.** The column of the evaluation set is
shuffled and the model re-scored; the drop in ROC AUC is that feature's importance for that repeat.
The fitted context stays intact, which is the only affordable form for TabPFN (a refit per feature
would be `features × repeats` context preparations) and the honest one for GLM/LGBM too: the
question is how much the fitted model's prediction depends on the column.

**TabPFN is the local open checkpoint, and the record says so.** `tabpfn` 6.4.1 resolves `auto` to
a **v2.5** classifier checkpoint; there is no local v3. The record carries `model_version: auto`
(the #285 convention: a label is not a filename) and, beside it, the version and checkpoint the
package actually resolved. The resolution mirrors `tabpfn.base`, which normalises `"auto"` to
`None` *before* resolving — `resolve_model_version("auto")` answers `v2` while
`resolve_model_version(None)` answers `v2.5`, so the obvious call would record a version no
checkpoint matched. The design's frontier numbers are v3-era and are **not** comparable with this
arm; nothing in the record claims they are.

**The families are the benchmark's canonical method ids, not a search for the best.** Reading
`frontier_results_*.csv` to pick the strongest GLM would be model selection on test rows, which the
decision log's leakage rule forbids. `logisticglm` and `lgbm` are taken from the benchmark's own
`CLASSIFICATION_METHODS`, so the code and the comparison cannot drift.

**The GLM's iteration budget is raised; its estimator is not changed.** `logisticglm` is
`penalty=None, max_iter=500`, and on a 1,500-row subsample with 85 near-collinear dummies that
budget runs out with the coefficients still moving (measurement C below). An unconverged fit's
importance describes the iteration limit, not the data, so `max_iter` is raised to 20,000 — enough
for every anchor to converge, including `spanish_motor_lapse`, which needs 12,481 — and the solver
block records the iteration count and whether it converged. The estimator stays the
benchmark's: swapping to the penalised `lr` — the other canonical linear id — would have been a
modelling choice taken after seeing scores. Nothing acts on the `converged` flag, and that is
deliberate: a non-converged unpenalised logistic still yields a fit, and refusing would discard the
dataset's whole linear arm; the field is there so a reader of an unconverged record is told.

**A family with no signal says so in the record.** Each family carries `no_better_than_chance`
(test AUC below 0.52), and a limitation line names it, because a ranking of noise is still a
ranking and would otherwise pass for a reading. The bound is one-sided: a family at 0.35 is not "at
chance", but it is just as unreadable, and the note says which it is.

**Preprocessing is the R1 default, on purpose.** Categoricals become per-column codes and missing
values become 0 — the benchmark's `load_Xy` convention. Whether that encoding is the reason TabPFN
struggles is D4's question; D2 must not improve the inputs and then report importance as if the
regimes were the same.

**One estimator, the library's fit mode, and batched prediction.** A permutation run makes
`features × repeats` predictions against one fitted context on a CPU-only box; `coil2000` alone has
85 features. Two throughput choices keep it runnable, both recorded: `n_estimators=1` (the pilot
uses 2) and up to ten permuted copies per prediction call (measurement A). Batching is throughput
and not method — the permutations drawn are identical, and a test pins that.

**`fit_with_cache` was tried and rejected.** It is the obvious accelerator and it is *wrong* here
(measurement B). Had the run used it, every importance in the record would describe a broken model
— the sort of thing the label-permutation control would not have caught, because a broken model's
importances are still self-consistent.

## What is deliberately not done

- **No SHAP.** The design allows "permutation importance (or SHAP where feasible)"; SHAP over three
  families is a second method with its own artefacts, and permutation already answers the three
  readings.
- **No interaction test beyond the univariate screen.** A real interaction measure (H-statistic,
  two-way ablation) multiplies the prediction budget by the feature count. The record's
  `interaction_candidates` list is a *screen* with its rule stated, not a proof of interaction.
- **No re-run on other classification datasets.** The design extends "only if the pilot needs a
  broader explanation"; the ticket names the four anchors.
- **No paid call anywhere.** The four anchor CSVs are already committed.

## Seam

One seam, as the campaign spec agrees: **the record on disk**, read back by the test through
`provenance.read_diagnostic_record`. The script's model builders are injectable
(`main(..., families=...)`) and so is the dataset registry (`main(..., datasets=...)`), so tests
assert the record's shape and the three readings from a synthetic table without fitting TabPFN —
the same seam D1 uses. A record produced through that seam states `model_version:
injected-families` rather than borrowing a label for a checkpoint nothing loaded.

## A control that cannot write its own failure is decoration

D3 refuses to write when its control fails. D2 does the opposite and writes anyway, then exits
non-zero: the control's numbers *are* the evidence of what went wrong, and refusing to write would
destroy the only record of a failure that took most of an hour of CPU to produce.

## Measurements

Each figure this plan and the script lean on, and how it was established. All were taken on
2026-11-04 on the development box (8 cores, CPU only, `torch` 2.7.1, `tabpfn` 6.4.1), and all are
reproducible with the command beside them.

- **A — batching.** `coil2000`, 1,500-row context, `n_estimators=1`: one prediction call for 500
  rows took 27.7s; for 5,000 rows (ten permuted copies stacked) 84.6s. Ten separate 500-row calls
  would be ~277s. Command: a TabPFN fit on `data/raw/coil2000.csv` with repeated `predict_proba`
  over `np.tile`-stacked copies.
- **B — `fit_with_cache` is broken.** `uslapseagent`, same split, `roc_auc_score` on the held-out
  500 rows: `fit_with_cache` 0.631 (2 estimators) and 0.333 (8); `fit_preprocessors` 0.937 (8) and
  `batched` 0.936 (2). The comparison holds in float32 and float64.
- **C — the GLM's iteration budget.** `logisticglm` at `max_iter=500` reaches the limit unconverged
  on every anchor carrying a wide, near-collinear design (`coil2000` AUC 0.636 against 0.667 on a
  converged fit). The converged iteration counts, read from the records' solver blocks:
  `coil2000` 1,262; `eudirectlapse` 3,423; `spanish_motor_lapse` 12,481 (so 5,000 is still short —
  the first delivery of this diagnostic ran at 5,000 and its `spanish_motor_lapse` record says
  `converged: false`); `uslapseagent` 145.
- **D — LGBM at chance on `eudirectlapse`.** Same split, test AUC 0.4942 at 100 trees and 0.4930 at
  400; and no categorical column has more than 2% of its test values unseen in training, so the
  coding is not the explanation.
- **E — wall clock.** The four-dataset run plus the control on one anchor took about 45 minutes,
  of which `coil2000` (85 features) was about 40.

## Verification

- `./scripts/check.sh` green (ruff, pytest, shellcheck, evidence, doclinks, docstatus, citation,
  verdict).
- Four records, one per anchor, each carrying the 2,000-row cap, the approximation note, three
  top-tens, the three readings and — on the designated dataset — the permutation control.
- The control passes: its top feature is not as important as the real run's top feature in any
  family. A failing control still writes its records and exits non-zero, which the tests exercise.
- Two invocations with the same seed produce identical numbers; batching does not change them.
- `git diff` over `outputs/` and `results/` is empty — the records land in the git-ignored
  diagnostics tree.
