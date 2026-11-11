"""Shared figure style for new figures — static (matplotlib/seaborn) and HTML (plotly).

Single source of truth for the look of every figure this repo produces from now on.
`.opencode/skills/dataviz/SKILL.md` is the procedure; this module is the style.
Figures already committed under docs/figures/ are cited evidence and are not restyled.
"""
from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go
from cycler import cycler
from matplotlib.figure import Figure as MplFigure

# Okabe-Ito colour-blind-safe palette (Okabe & Ito, 2008).
OKABE_ITO: dict[str, str] = {
    "black": "#000000",
    "orange": "#E69F00",
    "sky_blue": "#56B4E9",
    "bluish_green": "#009E73",
    "yellow": "#F0E442",
    "blue": "#0072B2",
    "vermillion": "#D55E00",
    "reddish_purple": "#CC79A7",
}

#: Series colours in cycle order — what an axes' colour cycle draws from.
SERIES_COLORS: list[str] = [
    OKABE_ITO[name]
    for name in (
        "orange",
        "sky_blue",
        "bluish_green",
        "vermillion",
        "blue",
        "reddish_purple",
        "yellow",
    )
]

#: Publication rcParams: single-column width, >=8 pt text, 300 dpi, embedded fonts.
STATIC_RC: dict[str, object] = {
    "figure.figsize": (3.5, 2.625),
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "font.size": 8,
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans"],
    "axes.titlesize": 9,
    "axes.labelsize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "legend.frameon": False,
    "axes.prop_cycle": cycler(color=SERIES_COLORS),
    "axes.spines.top": False,
    "axes.spines.right": False,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "svg.fonttype": "path",
}

#: Export checklist the dataviz skill runs before a static figure is called done.
EXPORT_CHECKLIST: tuple[str, ...] = (
    "width 3.5 in single column (7 in double) — override figsize only for multi-panel",
    "fonts >= 8 pt (ticks 7 pt), embedded: pdf.fonttype 42, svg text as paths",
    "palette from SERIES_COLORS only (Okabe-Ito)",
    "saved as vector PDF and 300 dpi PNG",
    "caption drafted: what it shows, on what data, the key comparison",
)


def apply_static_style() -> None:
    """Apply the publication rcParams. Call before creating any matplotlib figure."""
    import matplotlib

    matplotlib.rcParams.update(STATIC_RC)


def save_publication(fig: MplFigure, stem: str | Path) -> tuple[Path, Path]:
    """Save `fig` as vector PDF + 300 dpi PNG at `stem` (no suffix). Returns (pdf, png)."""
    path = Path(stem)
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf = path.with_suffix(".pdf")
    png = path.with_suffix(".png")
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(png, bbox_inches="tight")
    return pdf, png


def apply_html_theme(fig: go.Figure) -> None:
    """Apply the repo palette and fonts to a plotly figure, in place."""
    fig.update_layout(
        template="plotly_white",
        colorway=SERIES_COLORS,
        font={"family": "DejaVu Sans, Helvetica, Arial, sans-serif", "size": 12},
    )


def write_html(fig: go.Figure, stem: str | Path) -> Path:
    """Write a self-contained HTML file (plotly.js embedded) at `stem`.html. Returns it."""
    path = Path(stem).with_suffix(".html")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(path, include_plotlyjs=True)
    return path
