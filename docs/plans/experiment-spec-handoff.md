# Handoff — experiment spec (architecture candidate 1)

**Status:** Historical — grilling complete (rounds 1–5); the spec it fed is `docs/plans/experiment-spec.md`.
**Subject:** deepen the analysis pipeline so one module owns what an experiment *is*.
**Survey:** issue #227. Visual review was written to the session temp dir and is not durable; #227 is the record.

## Why this candidate

- Already asks for itself: issue **#210** is `priority: now` — "declare experiments in a committed config file, not in five places in code". The review found six.
- Closes a hazard to the *evidence*, not to tidiness: the reuse predicate ignores the seed, so a frontier can be built from two different splits.
- Everything else in the analysis half threads through it — the artifacts module needs a source of truth for `model_version` and seed.

## Settled in round 1

| Decision | Answer |
|---|---|
| What we are sharpening | Candidate 1, the experiment spec — one candidate at a time |
| The live rescore bug | Fix **first, separately**, on the `diagnosing-bugs` on-ramp. Not part of this spec. |
| The six parked candidates | Preserved in issue #227, un-ticketed, so nothing is scheduled prematurely |
| Session | Handoff, then a fresh window for the grilling |

## Evidence to carry into the grilling

An experiment's identity is declared in six code sites:

| Attribute | Declared in |
|---|---|
| dataset + target | `run_frontier_benchmark.py:122-129, 141-148` · `run_home_turf_size_sweep.py:46-51` · `plot_money_chart.py:39-52` · `rescore_altmetrics.py:64-71` · `rescore_focused_imbalance_logloss.py:27` |
| methods | `run_frontier_benchmark.py:159-160, 284-368` · `run_tuned_baselines.py:65-68, 178-278` · `run_reframe_frequency.py:95-102` · `run_tabfm.py:48` · three analysis scripts |
| seed / folds | `run_frontier_benchmark.py:155, 171, 907` · `run_tuned_baselines.py:62-63` · `run_reframe_frequency.py:94, 205` · `run_tabfm.py:43-44` · `rescore_altmetrics.py:47, 329` · `analyze_pr_auc.py:141` |
| model version | `_model_path()` at `:589, 787, 839, 960` — but hardcoded `"v3_default"` at `run_reframe_frequency.py:166`, and **absent from the run manifest** (`:1121-1133`) |
| metrics | five vocabularies across six files |

`src/baseline_config.py` claims to own this ("Centralized configuration…") and is imported by zero *v1 pipeline* modules; its values contradict the pipeline that superseded it. **Corrected:** it is not imported by zero modules — `src/data_loader_class.py:13` imports `DATA_DIR, RANDOM_SEED`, and `tests/test_smoke.py` asserts its constants. It serves the notebook-era loader, not the v1 suite.

**The two live hazards:**

1. `run_frontier_benchmark.py:469-471` — reuse-vs-refit decides from the sweep CSV on `dataset`, `n_rows` and `n_estimators`. **`SEED` is not in the predicate.** `--seed 7` can reuse seed-42 rows while refitting others. The committed `_seed7` CSV escaped only because it ran with `--pr-auc`, which forces fresh.
2. `--regression --seed 7` ignores the seed: `KFold(..., random_state=42)` at `:907`, filename `_seed7` at `:1170`, `"seed": SEED` at `:1125`, `seed=SEED` in the capture at `:1030`. The artifact's own provenance contradicts itself.

## Repo facts that constrain the answer

- **No `GLOSSARY.md`, no `docs/adr/` at survey time.** Both now exist: `GLOSSARY.md` defines
  *method* as canonical, and `docs/adr/0001` records the version-pinning and reuse-guard
  decision. The repo uses *arm*, *method* and *model* interchangeably, and *experiment*, *run*
  and *sweep* without defining the difference — that is now settled.
- **Gate is four checks:** `ruff check scripts/ src/ tests/` · `pytest tests/ -q` · `shellcheck --severity=warning scripts/gpu_helpers/*.sh` · doc link/status checks. Suite is green as of `9758b0c` (185 passed).
- **Tracker is configured** (PR #224): labels are in place, so `/to-tickets` gets native blocking links.
- **Version pinning is load-bearing** — see `docs/MODEL_VERSIONS.md`. A spec that resolves `model_version` must record it, never infer it later.

## Settled in rounds 2–5

| Decision | Answer |
|---|---|
| Unit of the spec | Whole registry — datasets, methods and experiments in one file, experiments referencing the other two by name |
| Format | TOML via stdlib `tomllib`; `schema_version = 1`, refused if unrecognised |
| Location & scope | The v1 suite directory — `experiments.toml`, beside the evidence it governs |
| Model version | A literal in the file (`model_version = "v3_default"`); `TABPFN_MODEL_PATH` still serves ad-hoc runs; the manifest records what was actually used |
| Blast radius | Expand–contract: spec, loader and **the frontier runner only**. Other producers and every analysis/plot/rescore script are follow-up tickets |
| Retrofit | Forward-only. Pre-spec CSVs are untouched; their folds and seeds cannot be validated against any spec |
| Vocabulary | `method` is canonical, `arm` retires from this context (it survives in the fine-tuning pilot with a different meaning); `experiment → run → sweep` defined. See `GLOSSARY.md` |
| Test seam | `load_registry(path) -> Registry` plus a path-free `evaluate(experiment, predictors, folds, metrics)`; frozen dataclasses, no disk in the scoring core |
| Method dispatch | Code-side registry: `register("lr", make_lr)`; the file names ids and hyperparameters; unknown id is a load error |
| Folds | Spec declares `n_folds` and `seed`; one shared `make_folds(kind, n, seed)` used by every producer. This is what kills hazard 2 |
| `src/baseline_config.py` | Leave it; it serves the notebook-era loader. Claim corrected above, retirement is a follow-up ticket |
| Experiment identity | `id` in the file, stamped into `manifest.json`, the capture manifest and an `experiment_id` CSV column. Filenames unchanged, so the four `{dataset}__seed{s}__*` discovery globs keep working |
| Loader strictness | Fail closed: unknown keys, dangling references, duplicate ids and missing fields are load errors |
| Reuse predicate | Guard on recorded provenance — reuse only rows whose `seed` and `model_version` match the experiment. The sweep writer gains both columns; the 220 legacy rows become ineligible, so the first post-spec run refits once |
| Metrics | Closed name→implementation table lives in code; experiments select names; unknown name is a load error |
| Module | `experiment_spec.py` in `src/` — loader, dataclasses, `evaluate`, `make_folds` |
| Authoring the file | Generate once from the current `DATASETS`/`REGR_DATASETS`/method lists with a throwaway script, commit the output, drop the script |
| Hazard 2 timing | Fixed inside this change, as a consequence of `make_folds`; not a separate PR |

## Verification

Re-run `coil2000` at seed 42 through the rewired runner and diff its CSV against the
committed `frontier_results_coil2000.csv`. Identical rows prove the seam; one
classification dataset carries no hosted cost. The loader's own tests cover parsing and
the fail-closed paths.

## Do first, separately — **DONE**

The rescore reader/writer mismatch was fixed by `6f3b412` (#228) and `878dad6` (#229):
`rescore_altmetrics.load_prediction_store()` now discovers the `__{model_version}`
suffix instead of reconstructing it. This blocker no longer gates the spec work.

## Outstanding

- **PR #226** (doc-status pointed at the dissolved `docs/reports/`) is open and unmerged.
- The doc gate is red on `main` independently of this work: `scripts/check_doc_links.py`
  reports 49 broken references and `scripts/check_doc_status.py` reports 11/38 reports
  stating a status. Neither may be attributed to this change, but a landing that claims
  "gate green" cannot be honest until they are addressed or explicitly waived.
