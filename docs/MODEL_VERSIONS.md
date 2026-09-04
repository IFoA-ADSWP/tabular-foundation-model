# Model Versions & Validity Timeline

> Read this before citing any number in this repo. Every finding is pinned to the TabPFN version that produced it — versions change behaviour, so findings do not automatically carry forward.
> Current pinned version here is **v3_default (tabpfn-client 0.3.3)** — see `docs/reports/TABPFN_BENCHMARK_SUMMARY.md`, master report §12.1 (version correction) and §15 (re-test policy). Legacy v2.6 rows below are frozen and must not be cited as current.

## The rule

> **Do not trust a metric on a new TabPFN version until it is re-run.** Note the `Tested:` line on every report/table, and check this timeline for what changed.

New runs must record: model version (`tabpfn` / `tabpfn-client` + weights ID e.g. `v2.6` / `v3_default`), date, seed, dataset SHA. Pattern to copy: successor's `results/<run-dir>/manifest.json` + Version-Drift Re-Test Policy (trigger → scope → diff → addendum, master report §15, issue #55).

## Timeline

| Period | TabPFN version | Package | Context / notes | Status |
|---|---|---|---|---|
| **Apr 2026 — this repo** | **v2.6** | `tabpfn>=7` local (`n_estimators`, not `n_ensemble`); `tabpfn-client 0.2.8` for hosted finetune | Effective context ~1k rows (hence 10k-row caps + batching in `scripts/`); CPU inference, GPU finetune | **Frozen. Numbers below are v2.6-only.** |
| **Aug 2026 — successor** | **v3_default** | `tabpfn-client 0.3.3` | API accepts up to 1M rows; still loses on accuracy-per-complexity at scale, so the *mechanism* changed but the *pattern* mostly held (§12.1 correction) | **Current. Cite this for new work.** |

Tags: `paper-snapshot-2026-08-22` (pre-hygiene baseline backing §14.x verdicts), `v8.2.0` (benchmark suite + version-drift policy).

## What flipped between v2.6 and v3 (so you are not confused)

| Finding (v2.6, this repo, Apr 2026) | v3 re-test (successor, Aug 2026) |
|---|---|
| "TabPFN is a small-data specialist" (wins ≤10k rows) | Refined: best risk-ranker on 6/6 classification sets **including 163–184k rows** (AUC deltas +0.006–+0.033 over best GLM); small-data is a secondary strength, not its identity |
| Lapse tie: GLM 0.599 vs TabPFN raw 0.593, calibrated Brier 0.1080 best | `eudirectlapse` disclosed as **genuine classification loss** (TabPFN 0.6101 vs best GLM 0.6260, additive structure); Spanish lapse is the real win (0.7553 vs 0.7500, 5/5 folds) |
| Regression: mixed, needs finetune | Confirmed at scale: off parsimony frontier 5/12, all at ≥53.5k rows — prefer GBDT/GLM for count model; claim/no-claim *reframe* is TabPFN triage territory (AUC #1, p≈0.001) |
| Calibration: +0.87% Brier via isotonic | Holds, with two ~1e-4 paired-significant exceptions vs tuned baselines (see §14.13) |

## Per-artifact validity (this repo)

| Artifact | Tested | TabPFN | Verdict |
|---|---|---|---|
| `docs/reports/*.md` (8 reports, registry `last_updated` 2026-04-04 → 2026-04-07) | Apr 2026 | v2.6 / client 0.2.8 | v2.6-only; see banner on each report |
| `notebooks/adswp_project/REPLICATION_*` (seed 45, 70:30) | Apr 2026 | v2.6 | Re-run on v3 before citing |
| `outputs/current/tables/*revalidation*.csv` (2026-04-05) | 2026-04-05 | v2.6 | Superseded by successor frontier runs |
| `notebooks/baseline_experiments/01–08`, `scripts/*finetune*`, `scripts/run_*benchmark*` | Mar–Apr 2026 | v2.6 | Methods reusable; numbers not portable |

## What to do

1. **Citing old numbers?** Quote with version: "TabPFN v2.6 (Apr 2026): lapse AUC 0.593 vs GLM 0.599".
2. **Running today?** Install, run, and write a `manifest.json` (model, package, date, seed, dataset SHA). If on v3, compare against the successor's `TABPFN_BENCHMARK_SUMMARY.md`, not this repo's tables.
3. **Bumping versions?** Follow the re-test policy: trigger (new weights/client) → scope (canonical folds) → diff (paired per-fold tests) → addendum (append here + report header, never silently overwrite).
