# Plan — verdict figures for the two closing results

**Status:** Current — implemented with this change, 2026-11-13.
**Origin:** #607. The gap is recorded in `docs/shared/skill_sets_for_ds_research.md` §4: "Journal-ready
figures: **No**". The style (`scripts/infra/figure_style.py`) and the procedure
(`.opencode/skills/dataviz/SKILL.md`) already exist; no figure for a current verdict does.
**Design:** two static forest plots, one per closing verdict, drawn from committed evidence and embedded
in the report that owns the number.

## Scope

1. `docs/figures/finetuning_phase2_forest.pdf` + `.png` — Δ ROC AUC per dataset with its 95% interval
   against the pre-registered δ = 0.002 band, with `coil2000` shown as a stopped cell rather than a
   fabricated interval.
2. `docs/figures/freq_sev_forest.pdf` + `.png` — per-target and per-task relative improvement on the
   frequency/severity fair test, each row with its own floor and its registered decision.
3. `scripts/infra/verdict_figures.py` — one entry point that regenerates both pairs from the tree.
4. `docs/figures/README.md` — figure → claim → evidence → regenerate command.
5. Embeds and captions in `FINETUNING_PHASE2_OUTCOME.md` and `freq_sev_fair_test_result.md`.

## Decisions worth arguing with

**The numbers are computed, not typed.** The Phase 2 rows come from each run's
`pilot_metrics.parquet`; the fair-test rows come from `freq_sev_fair_test.build_summary()`, the same
function the verdict script calls. A figure that restates a published number in plotting code becomes a
second source of truth, and the first time the analysis is corrected the figure is wrong silently. A test
asserts the plotted values equal the published tables, so drift fails CI rather than a reader.

**`spanish_motor_lapse` is drawn hollow.** It has no committed capture — its evidence is the launch
record under `outputs/gpu-pilot/` — so the figure quotes the owning analysis and marks the row as quoted.
The alternative, dropping the row or drawing it like the others, either loses a measured cell or hides a
provenance difference.

**`coil2000` gets a row with no interval.** The stop is a finding, and an empty row with the reason is
more honest than an omission: it carries the attainable half-width (±0.0149 at 4,000 test rows) against
the design's 0.006 floor, so a reader can see why no seed count closes it.

**The row-scaling arms stay out of the fair-test figure.** They are a robustness check on the registered
verdict, not a second verdict; the caption points at the section that carries them. One figure, one claim.

**Static, not HTML.** Both are cited in markdown reports and read as evidence, which is the skill's test
for the static branch. Interactive HTML would add a file nobody opens from a report.

## Shape

```
scripts/infra/verdict_figures.py                  # builders + drawing + CLI
scripts/infra/figure_style.py                     # NEUTRAL inks; deterministic PDF timestamps
scripts/analyses/freq_sev_fair_test.py            # main() calls the extracted build_summary()
tests/test_verdict_figures.py                     # reproduces the published tables; renders to tmp
docs/figures/finetuning_phase2_forest.{pdf,png}
docs/figures/freq_sev_forest.{pdf,png}
docs/figures/README.md
docs/experiments/pilot2-phase2/FINETUNING_PHASE2_OUTCOME.md
docs/experiments/fair-test-freq-sev/freq_sev_fair_test_result.md
docs/EVIDENCE_MAP.md                              # the docs/figures row
docs/plans/README.md                              # the index row
scripts/README.md                                 # the infra row and count
.opencode/skills/dataviz/SKILL.md                 # non-data ink comes from NEUTRAL
CHANGELOG.md
```

## Verification

```sh
.venv/bin/python scripts/infra/verdict_figures.py     # both pairs regenerate
PATH="$PWD/.venv/bin:$PATH" ./scripts/check.sh        # all eight; ruff lives in .venv, not on PATH
```

The review pass found five things, all fixed: the stopped row's floor was defined and never drawn;
two tests reached into `_draw` instead of the CLI seam; data labels sat below the style's 8 pt floor;
the greys were local hex codes; and the one quoted row was pinned only to itself. The quoted row is
now parsed from the document that owns it, so a correction there fails the test rather than leaving
the figure quietly wrong.

## What this does not do

No adoption-comparison or diagnostics figures (separate batch), no restyling of the eight existing
PNGs, no new evidence and no change to `results/` or `outputs/`.
