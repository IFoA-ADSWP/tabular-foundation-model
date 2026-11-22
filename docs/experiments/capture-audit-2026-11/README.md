# Capture audit, November 2026

> **Status:** index — this campaign's reading order, not a report of its own.

Where does TabPFN actually lose on captures this repository already owns? This campaign answers that
by re-reading committed captures and published tables — no TabPFN fit, no hosted call, **$0** — rather
than running anything new. It is the evidence-audit half of map
[#716](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/716) and was opened by
[#718](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/718).

## Documents

| Document | Status | What it holds |
| --- | --- | --- |
| [`CAPTURE_AUDIT.md`](CAPTURE_AUDIT.md) | Current — analysis, 2026-11-22 | The cell table by target and fold regime, where the model loses/ties/wins with the gap in the metric's units, whether the `norauto` exposure finding generalises, and the threshold a loss must clear to justify a candidate |

## What this campaign owns

The audit's own comparisons — in particular the per-seed relative gaps recomputed from the fair test's
committed records, and the threshold in its §8. Every underlying number keeps its original owner; the
note restates and links, and `docs/experiments/baseline-conclusion-2026-11/CONCLUSION.md` remains the
owner of the baseline phase's headline table.

## Evidence

Committed captures under `results/`, read by run id in the note; committed CSVs beside the frontier
runner; and the fair test's records under `results/2026111*/

```
20261112T164543Z
20261112T184155Z
20261112T210029Z
20261112T220641Z
20261113T223000Z
20261113T223001Z
20261113T223002Z
20261113T223003Z
20261114T003000Z
20261114T003001Z
20261114T003002Z
20261114T003003Z
```

The twelve runs above are the fair test's four TabPFN captures and its eight baseline captures; the
audit's other evidence is the committed `frontier_results_*.csv`, `version_retest_*.csv`,
`frontier_tuned_baseline_summary.csv`, `exposure_aware_glm_followup.csv` and
`home_turf_sweep_results.csv` files beside `scripts/eval/insurance_benchmark_v1/`.
