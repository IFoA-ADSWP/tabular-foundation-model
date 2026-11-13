# Plan — the actuarial baseline (#597)

**Status:** current — scoped 2026-11-13; build not started.
**Origin:** ticket #597. **Specification:** `docs/analyses/baseline_method_specification.md`.
**Pre-registration:** `docs/current/ACTUARIAL_BASELINE_PREREGISTRATION_2026-11.md`.

## Why this, and why now

The frequency/severity fair test is finished and both of its arms are TabPFN. It therefore answers
*does fine-tuning help* and cannot answer *which model should a pricing team deploy*. Every headline
the programme has published is a comparison between two TabPFN configurations, and the strongest of
them (+11.84% on French frequency) says nothing about the GLM the same team would otherwise build.

The row-scaling arm has just closed the last question about the fair test's internal validity: the
cap was not what produced the frequency Go, and the severity null survives at every claim the data
holds. With that settled, the comparison this work makes is the one that can change the conclusion
rather than defend it.

## What runs

Fine-tuned TabPFN (`B_ft30`, with `A_raw` alongside) against two actuarial baselines — `E_glm` and
`F_catboost` — on all four registered targets, on the fair test's own folds, scored on its own metric.

| Field | Value |
|---|---|
| Targets | `frequency_french`, `frequency_spanish`, `severity_french`, `severity_spanish` |
| Methods | `B_ft30`, `A_raw` (TabPFN); `E_glm`, `F_catboost` (baselines) |
| Rows | full fold pool primary; the fair test's 10,000-row sample as a sensitivity arm |
| Folds / seeds | five policy-grouped folds × three seeds |
| Statistic | `r = (M(baseline) − M(TabPFN)) / M(baseline)`, positive when TabPFN is better |
| Floors | per target as registered: 2% / 4% / 2% / 2% |
| Verdicts | per target, against the **better** of the two baselines |
| Aggregation | task means reported descriptively; no pooled verdict |
| Anchor | intercept-only model per target |
| Compute | local CPU, $0; one fold per target measured before the matrix |

## What changes

1. **A `Method` axis in the runner.** `Arm` keeps its glossary meaning (a TabPFN training
   configuration); the predictor becomes a separate axis threaded through `RunConfig`,
   `src/fair_test_runner.py` and the slot path. Adding `E_glm` to `ARMS` would contradict
   `GLOSSARY.md` and is what the pilot's naming got wrong.
2. **Baseline backends.** `E_glm` is `PoissonRegressor` on rate-with-exposure-weight (algebraically
   the offset model — see the specification's §3.1, measured to 2.8e-14) with the case study's GLM1
   encoding, and OLS on `log(amount)` for severity. `F_catboost` is Poisson and RMSE with raw
   categoricals through `cat_features`.
3. **A capture version for methods without quantiles.** A GLM has no honest predictive distribution
   to record; emitting the mean nine times would assert one. The new version carries `method`,
   `test_index` and predictions, makes quantiles optional, and is taught to `check_citations.py`
   with a test — the same trap that once refused a legitimate v4 capture.
4. **The comparability proof.** For every target, each baseline slot's `test_index` sha256 must equal
   the registered capture's. This is the one check that makes the comparison mean anything, and it
   is an acceptance test rather than a note.
5. **An analysis tool** that prints per-target verdicts against the better baseline, keeps task
   means descriptive, and carries the null anchor.
6. **Documents**: verdict section, registry row, and the pre-registration's outcome row.

## Order of work

1. Method axis + baseline backends behind the existing `Backend` seam — testable without the data.
2. Capture version + citation gate + tests.
3. One fold per target locally: measures the real runtime before the full matrix, and proves the
   `test_index` match on the cheapest possible run.
4. Full matrix; the analysis tool; the write-up.
5. `analysis-review` and `code-review` before merge.

## Verification

```
./scripts/bootstrap_dev.sh && .venv/bin/pytest tests/ -q
.venv/bin/python scripts/analyses/<tool>.py --registered ... --baselines <run id>
EVIDENCE_CHANGE_OK=1 ./scripts/check.sh
```

The registered fair-test rows must reproduce byte-for-byte, and every baseline row's `test_index`
hash must equal its target's registered capture.

## What this does not do

- It does not run the Gamma-log or Tweedie severity families: they cannot be scored on the
  registered metric, so they would produce a ranking the design cannot support.
- It does not claim a task-level verdict. The two-portfolio bootstrap was registered for a different
  claim and is thin; reusing it would widen the claim surface for no evidence.
- It does not touch the fair test's verdict, floors, folds or seeds.
- It spends nothing: this is CPU work on data already in `data/raw`.

## The risk this buys

**The comparison can lose.** If the GLM beats fine-tuned TabPFN on French frequency, the programme's
headline changes from "fine-tuning helps" to "fine-tuning helps TabPFN lose by less". That is the
more useful finding — it is the one a pricing team can act on — but it is not the one the current
write-up implies, and the documents that quote +11.84% would need a dated restatement rather than a
footnote.
