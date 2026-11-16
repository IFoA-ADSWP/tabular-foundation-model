#!/usr/bin/env python3
"""The actuarial baseline verdict as a forest (#647).

    .venv/bin/python scripts/infra/baseline_figures.py
    .venv/bin/python scripts/infra/baseline_figures.py --out /tmp/figures

One figure, one claim: **at the registered budget, fine-tuned TabPFN does not beat the better of a
GLM and CatBoost on any of the four targets**, and matching the baselines' training rows moves only
French frequency, into Inconclusive.

Two rows per target — the registered primary (baselines on the whole fold pool) and the matched
10,000-row sensitivity — except `severity_spanish`, whose fold holds fewer than 10,000 rows, so both
arms are the same fit and it is drawn once.

The values come from `scripts/analyses/actuarial_baseline.py`'s `analyse()` over the committed v5
captures, for both budget sets: the same function the verdict document uses, so the figure cannot
disagree with the table it illustrates.

Read the sign carefully: `r = (M(baseline) − M(B_ft30)) / M(baseline)`, so a **positive** `r` means
TabPFN has the lower metric. Almost every point in this figure is negative.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402  (backend must be chosen before pyplot)
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from scripts.analyses import actuarial_baseline as baseline  # noqa: E402
from scripts.infra.figure_style import (  # noqa: E402
    NEUTRAL,
    OKABE_ITO,
    apply_static_style,
    figure_parser,
    report_written,
    save_publication,
)

FIGURES = _REPO / "docs" / "figures"
RESULTS = _REPO / "results"

#: The TabPFN side of every comparison: the fair test's registered captures.
TABPFN_RUNS = {
    "frequency_french": RESULTS / "20261112T164543Z",
    "frequency_spanish": RESULTS / "20261112T184155Z",
    "severity_french": RESULTS / "20261112T210029Z",
    "severity_spanish": RESULTS / "20261112T220641Z",
}
#: Baselines on the whole fold pool — the registered primary.
PRIMARY_RUNS = {
    "frequency_french": RESULTS / "20261113T223000Z",
    "frequency_spanish": RESULTS / "20261113T223001Z",
    "severity_french": RESULTS / "20261113T223002Z",
    "severity_spanish": RESULTS / "20261113T223003Z",
}
#: Baselines capped at the fair test's 10,000 rows — the registered sensitivity.
MATCHED_RUNS = {
    "frequency_french": RESULTS / "20261114T003000Z",
    "frequency_spanish": RESULTS / "20261114T003001Z",
    "severity_french": RESULTS / "20261114T003002Z",
    "severity_spanish": RESULTS / "20261114T003003Z",
}

TARGET_ORDER = ("frequency_french", "frequency_spanish", "severity_french", "severity_spanish")
TARGET_LABEL = {
    "frequency_french": "French frequency",
    "frequency_spanish": "Spanish frequency",
    "severity_french": "French severity",
    "severity_spanish": "Spanish severity",
}
#: `severity_spanish`'s fold is smaller than the matched budget, so its two arms are one fit.
SAME_FIT_AT_BOTH_BUDGETS = "severity_spanish"

DECISION_COLOR = {
    "Go": OKABE_ITO["bluish_green"],
    "No-go": OKABE_ITO["vermillion"],
    "Inconclusive": OKABE_ITO["blue"],
}


@dataclass(frozen=True)
class Row:
    """One line of the forest: a target at one budget, and what the rule made of it."""

    label: str
    value: float
    low: float
    high: float
    floor: float
    decision: str
    group: str


@lru_cache(maxsize=1)
def verdicts() -> tuple[dict, dict]:
    """Both budget arms' summaries, computed once per process."""
    primary = baseline.analyse(TABPFN_RUNS, PRIMARY_RUNS)
    matched = baseline.analyse(TABPFN_RUNS, MATCHED_RUNS)
    return primary, matched


def rows() -> list[Row]:
    """The forest's rows, in target order, primary above matched."""
    primary, matched = verdicts()
    out: list[Row] = []
    for target in TARGET_ORDER:
        for budget, summary in (("full pool", primary), ("10k rows", matched)):
            if target == SAME_FIT_AT_BOTH_BUDGETS and budget != "full pool":
                continue
            verdict = summary["targets"][target]["verdict"]
            label = f"{TARGET_LABEL[target]} · {budget}"
            if target == SAME_FIT_AT_BOTH_BUDGETS:
                label = f"{TARGET_LABEL[target]} · one fit"
            out.append(
                Row(
                    label=label,
                    value=float(verdict["mean"]),
                    low=float(verdict["ci"][0]),
                    high=float(verdict["ci"][1]),
                    floor=float(verdict["floor"]),
                    decision=str(verdict["decision"]),
                    group=target,
                )
            )
    return out


def _formatter() -> FuncFormatter:
    def fmt(value: float, _position: int) -> str:
        if abs(value) < 1e-12:
            return "0%"
        return f"{value:+.0%}"

    return FuncFormatter(fmt)


def draw(readings: list[Row], stem: Path) -> tuple[Path, Path]:
    """Draw the forest and export the PDF + PNG pair."""
    lo = min([row.low for row in readings] + [0.0])
    hi = max([row.high for row in readings] + [row.floor for row in readings] + [0.0])
    pad = (hi - lo) * 0.10
    xlim = (lo - pad, hi + pad)

    # Single panel, but the labels carry the target and the budget, and the floor ticks sit on the
    # positive side of a mostly-negative axis; that needs the width.
    fig, ax = plt.subplots(figsize=(5.8, 3.6))
    ax.set_xlim(*xlim)

    ax.axvline(0.0, color=NEUTRAL["ink"], lw=0.7, zorder=1)

    positions: list[tuple[Row, float]] = []
    y = 0.0
    previous_group = None
    for row in readings:
        if previous_group is not None and row.group != previous_group:
            y -= 0.55
        positions.append((row, y))
        previous_group = row.group
        y -= 1.0

    for row, at in positions:
        colour = DECISION_COLOR[row.decision]
        ax.plot([row.low, row.high], [at, at], color=colour, lw=1.2, solid_capstyle="butt", zorder=2)
        ax.plot(
            [row.value], [at], marker="o", markersize=4.4, color=colour,
            markeredgecolor=colour, zorder=3,
        )
        ax.annotate(
            f"{row.value:+.2%}",
            (row.value, at),
            xytext=(0, 5),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
            color=colour,
        )
        # Below the row, so the value label above the marker is never struck through.
        ax.plot(
            [row.floor, row.floor],
            [at - 0.40, at - 0.06],
            color=NEUTRAL["muted"],
            lw=1.0,
            ls=(0, (2, 1)),
            zorder=2,
        )
        ax.text(
            1.015,
            at,
            row.decision,
            transform=ax.get_yaxis_transform(),
            ha="left",
            va="center",
            fontsize=8,
            color=colour,
        )

    ax.set_yticks([at for _, at in positions])
    ax.set_yticklabels([row.label for row, _ in positions])
    ax.set_ylim(y + 0.35, 0.8)
    ax.set_xlabel("Δ metric vs the better baseline (positive = TabPFN is better)")
    ax.xaxis.set_major_formatter(_formatter())
    ax.grid(axis="x", color=NEUTRAL["grid"], lw=0.6)
    ax.set_axisbelow(True)

    handles = [
        Line2D([], [], color=NEUTRAL["muted"], lw=1.2, marker="o", markersize=4, label="95% interval"),
        Line2D([], [], color=NEUTRAL["muted"], lw=1.0, ls=(0, (2, 1)), label="registered floor"),
    ]
    ax.legend(
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
    parser = figure_parser(FIGURES, description=__doc__.splitlines()[0])
    args = parser.parse_args(argv)

    apply_static_style()
    pdf, png = draw(rows(), args.out / "actuarial_baseline_forest")
    report_written((pdf, png))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
