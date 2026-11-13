# Figures

Committed figures, and the claim each one carries. A figure in this directory is cited evidence: it is
generated from the tree rather than drawn by hand, and where a report publishes the same numbers a test
compares the two so neither can drift.

Style is `scripts/infra/figure_style.py`; the procedure is `.opencode/skills/dataviz/SKILL.md`. New cited
figures join this directory; smoke and throwaway figures go to `outputs/`. Figures committed before the
style module existed are **not** restyled — that would move the visual provenance of numbers already
reported.

## Verdict figures

| Figure | The claim it carries | Evidence | Regenerate |
| --- | --- | --- | --- |
| [`finetuning_phase2_forest.pdf`](finetuning_phase2_forest.pdf) · [`.png`](finetuning_phase2_forest.png) | Fine-tuning produced a gain on one of four datasets and equivalence on two; the fourth could not be measured | `results/20261104T123839Z` (anchor) and the twenty `eudirectlapse` runs, recomputed from each run's `pilot_metrics.parquet`; `spanish_motor_lapse` quoted from its owning analysis, which has no committed capture; `coil2000` stopped on resolution | `.venv/bin/python scripts/infra/verdict_figures.py --only phase2` |
| [`freq_sev_forest.pdf`](freq_sev_forest.pdf) · [`.png`](freq_sev_forest.png) | Fine-tuning helps claim frequency and does not help severity | the four registered captures (`20261112T164543Z`, `20261112T184155Z`, `20261112T210029Z`, `20261112T220641Z`) via `freq_sev_fair_test.build_summary()` | `.venv/bin/python scripts/infra/verdict_figures.py --only fair-test` |

Both are drawn by `scripts/infra/verdict_figures.py` and asserted against their reports by
`tests/test_verdict_figures.py`. A filled marker was computed from committed evidence; a hollow one is
quoted from an analysis with no capture — the distinction is in the figure's legend, not only here.

## Teaching figures (pre-style, 2026-09)

| Figure | The claim it carries | Evidence | Regenerate |
| --- | --- | --- | --- |
| [`lp_discrimination.png`](lp_discrimination.png) | Models are near-equal on `eudirectlapse` discrimination (ROC 0.55–0.60) | `outputs/current/tables/Table1_Model_Performance.csv` | `.venv/bin/python scripts/infra/make_learning_path_charts.py` |
| [`lp_brier.png`](lp_brier.png) | Brier gaps against the constant-predictor floor are below 1% | `outputs/current/tables/Table4_Brier_Scores.csv` | same |
| [`lp_class_balance.png`](lp_class_balance.png) | The full data and the stratified subset carry the same class balance | `outputs/current/tables/Table3_Class_Balance.csv` | same |
| [`lp_reliability_schematic.png`](lp_reliability_schematic.png) | A labelled schematic of a reliability diagram — teaching, not evidence | none (schematic) | same |

These four are embedded by `docs/KNOWLEDGE-PATH-JUNIOR.md` and predate the shared style; they keep their
original rendering and 150 dpi.
