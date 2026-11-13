#!/usr/bin/env python3
"""The D2 feature-ranking readings, drawn (#610).

    .venv/bin/python scripts/infra/diagnostics_figures.py
    .venv/bin/python scripts/infra/diagnostics_figures.py --out /tmp/figures

One figure, two panels, over `docs/analyses/data/d2_importance.csv`:

- **Top-ten overlap** — the Jaccard index of two families' top-ten feature sets, per dataset. This is
  the data README's *same features* reading.
- **Rank agreement** — Spearman correlation of the two families' full rankings, per dataset. This is
  *same features, ranked differently*.

A family whose own `test_auc` is at chance carries `no_better_than_chance`; its ranking is noise, so
its bars are hatched and its dots hollow rather than removed. `eudirectlapse`'s LGBM arm is the case
that matters (0.494).

Provenance, and the limits a reader needs: the table is an export of the committed D2 records, hashed
row by row (`docs/analyses/data/README.md`); importance is a shuffle-drop ROC AUC on a 2,000-row
subsample (1,500 train / 500 test), so it is an approximation of the full table; and the TabPFN arm is
the local **v2.5** checkpoint, not the `v3_default` line the frontier and fine-tuning figures use.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402  (backend must be chosen before pyplot)
import pandas as pd  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from scripts.infra.figure_style import (  # noqa: E402
    NEUTRAL,
    OKABE_ITO,
    apply_static_style,
    save_publication,
)

TABLE = _REPO / "docs" / "analyses" / "data" / "d2_importance.csv"
FIGURES = _REPO / "docs" / "figures"

FAMILIES = ("tabpfn", "glm", "lgbm")
LABELS = {"tabpfn": "TabPFN", "glm": "GLM", "lgbm": "LGBM"}
PAIRS = tuple(combinations(FAMILIES, 2))
PAIR_COLOUR = {
    ("tabpfn", "glm"): OKABE_ITO["blue"],
    ("tabpfn", "lgbm"): OKABE_ITO["bluish_green"],
    ("glm", "lgbm"): OKABE_ITO["orange"],
}


@dataclass(frozen=True)
class Agreement:
    """One dataset's three readings, plus which of its families are at chance."""

    dataset: str
    overlap: dict[tuple[str, str], float]
    correlation: dict[tuple[str, str], float]
    at_chance: frozenset[str]


def load_table() -> pd.DataFrame:
    """The committed D2 export. It is the record; no diagnostic is re-run here."""
    table = pd.read_csv(TABLE)
    missing = {"dataset", "family", "rank", "feature", "test_auc", "no_better_than_chance"} - set(
        table.columns
    )
    if missing:
        raise SystemExit(f"{TABLE} no longer carries {sorted(missing)}")
    return table


def _rows(table: pd.DataFrame, dataset: str, family: str) -> pd.DataFrame:
    """One dataset's rows for one family — the only place the two-column filter is written."""
    return table[(table["dataset"] == dataset) & (table["family"] == family)]


def _top_ten(table: pd.DataFrame, dataset: str, family: str) -> set[str]:
    rows = _rows(table, dataset, family)
    return set(rows.loc[rows["rank"] <= 10, "feature"])


def _ranks(table: pd.DataFrame, dataset: str, family: str) -> pd.Series:
    return _rows(table, dataset, family).set_index("feature")["rank"]


def agreements() -> list[Agreement]:
    """Every dataset's readings, in alphabetical order so the axis cannot shuffle between runs."""
    table = load_table()
    out = []
    for dataset in sorted(table["dataset"].unique()):
        overlap = {}
        correlation = {}
        for first, second in PAIRS:
            left, right = _top_ten(table, dataset, first), _top_ten(table, dataset, second)
            overlap[(first, second)] = len(left & right) / len(left | right)
            ranks_left, ranks_right = _ranks(table, dataset, first), _ranks(table, dataset, second)
            common = ranks_left.index.intersection(ranks_right.index)
            correlation[(first, second)] = float(
                ranks_left.loc[common].corr(ranks_right.loc[common], method="spearman")
            )
        chance = frozenset(
            family
            for family in FAMILIES
            if bool(_rows(table, dataset, family)["no_better_than_chance"].iloc[0])
        )
        out.append(Agreement(dataset, overlap, correlation, chance))
    return out


def draw(readings: list[Agreement], stem: Path) -> tuple[Path, Path]:
    """Two panels sharing the dataset axis: what is picked, then how similarly it is ordered."""
    positions = list(range(len(readings)))
    width = 0.26

    # Two stacked panels with long dataset labels beneath; the width is the labels', as in #609.
    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(5.8, 4.0), sharex=True, gridspec_kw={"height_ratios": (1.0, 1.0)}
    )

    for index, reading in enumerate(readings):
        for offset, (first, second) in enumerate(PAIRS):
            # Centre the group whatever the number of pairs, so a fourth family cannot skew it.
            x = index + (offset - (len(PAIRS) - 1) / 2) * width
            colour = PAIR_COLOUR[(first, second)]
            noise = first in reading.at_chance or second in reading.at_chance
            top.bar(
                x,
                reading.overlap[(first, second)],
                width,
                color=colour,
                edgecolor=NEUTRAL["ink"] if noise else "none",
                hatch="///" if noise else None,
                linewidth=0.6 if noise else 0,
                alpha=0.55 if noise else None,
                zorder=2,
            )
            bottom.plot(
                [x],
                [reading.correlation[(first, second)]],
                marker="o",
                linestyle="",
                markersize=4.4,
                color=colour,
                markerfacecolor=NEUTRAL["surface"] if noise else colour,
                markeredgecolor=colour,
                markeredgewidth=0.9,
                zorder=3,
            )

    top.set_ylabel("Top-ten overlap\n(Jaccard, 1.0 = same ten)")
    top.set_ylim(0, 1.1)
    top.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    bottom.set_ylabel("Rank agreement\n(Spearman, 0 = unrelated)")
    bottom.set_ylim(-0.15, 0.85)
    bottom.set_yticks([0, 0.2, 0.4, 0.6, 0.8])
    bottom.axhline(0.0, color=NEUTRAL["ink"], lw=0.7, zorder=1)

    bottom.set_xticks(positions)
    bottom.set_xticklabels([reading.dataset for reading in readings], rotation=18, ha="right")
    bottom.set_xlim(-0.55, len(readings) - 0.45)

    for panel in (top, bottom):
        panel.grid(axis="y", color=NEUTRAL["grid"], lw=0.6)
        panel.set_axisbelow(True)
        panel.tick_params(axis="x", length=0)

    handles = [
        Patch(facecolor=PAIR_COLOUR[pair], label=f"{LABELS[pair[0]]} – {LABELS[pair[1]]}")
        for pair in PAIRS
    ]
    handles.append(
        Patch(
            facecolor=NEUTRAL["band"],
            edgecolor=NEUTRAL["ink"],
            hatch="///",
            label="at chance: hatched bar, hollow dot — its ranking is noise",
        )
    )
    top.legend(
        handles=handles,
        loc="lower left",
        bbox_to_anchor=(0.0, 1.0),
        ncol=2,
        fontsize=7,
        handlelength=1.3,
        handletextpad=0.5,
        columnspacing=1.2,
        borderaxespad=0.2,
        frameon=False,
    )

    fig.tight_layout()
    return save_publication(fig, stem)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=FIGURES, help="directory for the PDF/PNG pair")
    args = parser.parse_args(argv)

    apply_static_style()
    pdf, png = draw(agreements(), args.out / "diagnostics_feature_agreement")
    for path in (pdf, png):
        print(path.relative_to(_REPO) if path.is_relative_to(_REPO) else path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
