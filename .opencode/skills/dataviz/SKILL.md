---
name: dataviz
description: 'Make figures with the repo''s shared figure style — static matplotlib/seaborn charts for docs and papers (Okabe-Ito palette, vector PDF + 300 dpi PNG, caption draft) and self-contained plotly HTML figures for interactive inspection. Use when creating, styling, exporting or captioning any chart, plot or figure, when choosing chart type, or when deciding between a static figure and an interactive one.'
---

# Dataviz

One style, two renderers. [`scripts/infra/figure_style.py`](../../../scripts/infra/figure_style.py)
is the single source of truth for the look; this skill is the procedure around it.

## 1. Choose the mode

| The figure will… | Mode |
| --- | --- |
| be cited in a markdown doc, report or paper | **static** — matplotlib/seaborn |
| be opened, poked at, or handed to a human or agent to inspect | **HTML** — plotly |

Done when: the mode is chosen and stated in one line before any plotting code is written.

## 2. Static procedure

1. From the repo root:

   ```python
   import matplotlib
   matplotlib.use("Agg")  # headless export
   from scripts.infra.figure_style import apply_static_style, save_publication

   apply_static_style()  # before creating the figure
   ```

2. Build the figure. Series colours come from the `axes.prop_cycle` (Okabe-Ito) — the
   palette is already the default, no hex codes needed. Non-data ink (rules, bands, grid
   lines, de-emphasised text) comes from `NEUTRAL`; a grey must never encode a category. A
   matrix or heatmap uses `SEQUENTIAL_CMAP` and prints its value in each cell, so colour is
   never the only encoding.
   Override `figsize` only for multi-panel layouts.
3. Draft the caption: what it shows, on what data, the key comparison.
4. Export with `save_publication(fig, "path/to/stem")` — vector PDF **and** 300 dpi PNG, both.
5. Run every item in `EXPORT_CHECKLIST` (same module).

Done when: both files exist, every checklist item passes, the caption is drafted.

## 3. HTML procedure

1. Build the plotly figure, then:

   ```python
   from scripts.infra.figure_style import apply_html_theme, write_html

   apply_html_theme(fig)
   write_html(fig, "path/to/stem")  # self-contained .html, plotly.js embedded
   ```

2. Confirm the `.html` exists, has no empty traces, and opens without network access.

Done when: the file stands alone — no CDN, no sidecar assets.

## New figures only

Figures already committed under `docs/figures/` are cited evidence: re-rendering one would
move the visual provenance of numbers already reported. New cited figures join
`docs/figures/`; smoke and throwaway figures go to `outputs/`.
