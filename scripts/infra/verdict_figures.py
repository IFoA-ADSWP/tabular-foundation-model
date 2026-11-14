#!/usr/bin/env python3
"""The two closing verdicts as forest plots (#607).

    .venv/bin/python scripts/infra/verdict_figures.py            # both pairs, into docs/figures/
    .venv/bin/python scripts/infra/verdict_figures.py --only phase2 --out /tmp/figures

Two figures, each one claim:

- **`finetuning_phase2_forest`** — Δ ROC AUC of in-domain fine-tuning against the in-run raw arm, per
  dataset, with its 95% interval against the pre-registered δ = 0.002. The anchor and `eudirectlapse`
  are recomputed here from each run's committed `pilot_metrics.parquet`; `spanish_motor_lapse` has no
  committed capture, so its published interval is quoted from the owning analysis and the row is drawn
  hollow; `coil2000` is a stopped cell and carries no interval at all.
- **`freq_sev_forest`** — the frequency/severity fair test's relative improvement, per portfolio and
  pooled per task, each against its own registered floor. Every row comes from
  `freq_sev_fair_test.build_summary()`, the same function the verdict script calls, so the figure cannot
  disagree with the published table.

Provenance is part of the picture rather than a footnote: a filled marker was computed here from a
committed artefact, a hollow one is quoted. The test in `tests/test_verdict_figures.py` asserts the
plotted values equal the reports' tables — the figure is not allowed to become the only record of a
number.

The style is `.opencode/skills/dataviz/SKILL.md`'s static branch: `apply_static_style()` before the
figure, `save_publication()` for the PDF + 300 dpi PNG pair.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import NormalDist

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402  (backend must be chosen before pyplot)
import pandas as pd  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from scripts.analyses import freq_sev_fair_test as fair_test  # noqa: E402
from scripts.infra.figure_style import (  # noqa: E402
    NEUTRAL,
    OKABE_ITO,
    apply_static_style,
    figure_parser,
    report_written,
    save_publication,
)

RESULTS = _REPO / "results"
FIGURES = _REPO / "docs" / "figures"

#: Two-sided 95% normal quantile, the interval the verdicts publish. Computed rather than spelled
#: out, so no second copy of the constant can drift.
Z95 = NormalDist().inv_cdf(0.975)
#: The pre-registered practical-effect bar, agreed 2026-11-03 before the replication.
DELTA = 0.002

#: The four registered captures of the fair test, as the verdict document names them.
FAIR_TEST_IDS = {
    "frequency_french": "20261112T164543Z",
    "frequency_spanish": "20261112T184155Z",
    "severity_french": "20261112T210029Z",
    "severity_spanish": "20261112T220641Z",
}
#: Phase 2 cells recomputed from their committed metrics tables.
ANCHOR_RUN = "20261104T123839Z"
EUDIRECTLAPSE_RUNS = (
    "20261104T234013Z", "20261105T001837Z", "20261104T234127Z", "20261104T234132Z",
    "20261105T100533Z", "20261105T005435Z", "20261105T005447Z", "20261105T124200Z",
    "20261105T012925Z", "20261105T013749Z", "20261105T013755Z", "20261105T124205Z",
    "20261105T140236Z", "20261105T103841Z", "20261105T103937Z", "20261105T103853Z",
    "20261105T140242Z", "20261105T111110Z", "20261105T114320Z", "20261105T114647Z",
)
#: `spanish_motor_lapse` is quoted: its 32 records live in the paid-run record, not in a capture.
SPANISH_PUBLISHED = {
    "value": 0.00029,
    "low": -0.00021,
    "high": 0.00078,
    "seeds": 16,
}
#: `coil2000` was stopped on resolution: the best attainable half-width at 4,000 test rows
#: (D21, amended by D22), against the design's 0.006 floor.
COIL2000 = {"half_width": 0.0149, "rows": 4000, "floor": 0.006}

#: Reading and decision colours, from the shared palette only.
DECISION_COLOR = {
    "Go": OKABE_ITO["bluish_green"],
    "gain": OKABE_ITO["bluish_green"],
    "No-go": OKABE_ITO["vermillion"],
    "Inconclusive": OKABE_ITO["blue"],
    "equivalence": OKABE_ITO["sky_blue"],
    "Heterogeneous": OKABE_ITO["orange"],
    "stopped": NEUTRAL["muted"],
}

@dataclass(frozen=True)
class Row:
    """One line of a forest plot. `value is None` means the cell was not measurable."""

    label: str
    value: float | None
    low: float | None
    high: float | None
    decision: str
    group: str
    floor: float | None = None
    computed: bool = True
    detail: str = ""
    emphasis: bool = False


def _delta_series(run_dir: Path) -> pd.Series:
    """Per-seed Δ ROC AUC, `B_ft30` minus `A_raw`, from the run's committed metrics table.

    One row per arm × seed; the pivot refuses nothing and the subtraction is on the seed axis, which
    is the unit the comparison was registered on.
    """
    metrics = pd.read_parquet(run_dir / "pilot_metrics.parquet")
    metrics = metrics[metrics["status"] == "success"]
    wide = metrics.pivot_table(index="seed", columns="arm", values="roc_auc", aggfunc="first")
    missing = {"A_raw", "B_ft30"} - set(wide.columns)
    if missing:
        raise SystemExit(f"{run_dir}: metrics table has no {sorted(missing)} arm")
    return (wide["B_ft30"] - wide["A_raw"]).dropna()


def _interval(values: pd.Series) -> tuple[float, float, float]:
    """Mean and its 95% interval from the between-seed standard error."""
    mean = float(values.mean())
    half = Z95 * float(values.std(ddof=1)) / math.sqrt(len(values))
    return mean, mean - half, mean + half


def phase2_rows() -> list[Row]:
    """The four Phase 2 cells, in the order the outcome report states them."""
    anchor = _delta_series(RESULTS / ANCHOR_RUN)
    eudi = pd.concat([_delta_series(RESULTS / run) for run in EUDIRECTLAPSE_RUNS])

    rows = []
    for dataset, values, reading in (
        ("uslapseagent (anchor)", anchor, "gain"),
        ("eudirectlapse", eudi, "equivalence"),
    ):
        mean, low, high = _interval(values)
        rows.append(
            Row(
                label=f"{dataset} · {len(values)} seeds",
                value=mean,
                low=low,
                high=high,
                decision=reading,
                group="measured",
            )
        )

    rows.append(
        Row(
            label=f"spanish_motor_lapse · {SPANISH_PUBLISHED['seeds']} seeds",
            value=SPANISH_PUBLISHED["value"],
            low=SPANISH_PUBLISHED["low"],
            high=SPANISH_PUBLISHED["high"],
            decision="equivalence",
            group="measured",
            computed=False,
        )
    )
    rows.append(
        Row(
            label="coil2000",
            value=None,
            low=None,
            high=None,
            decision="stopped",
            group="stopped",
            detail=(
                f"not measurable: ±{COIL2000['half_width']:.4f} at {COIL2000['rows']:,} test rows\n"
                f"against the design's {COIL2000['floor']:.3f} floor"
            ),
        )
    )
    return rows


def fair_test_rows() -> list[Row]:
    """The registered fair-test verdict: pooled tasks and the four portfolios under them."""
    # The row-scaling arms are deliberately not requested: #607 keeps one claim a figure, and a
    # figure must not depend on evidence it does not draw.
    summary = fair_test.build_summary(FAIR_TEST_IDS)

    rows: list[Row] = []
    for task in ("frequency", "severity"):
        pooled = summary["tasks"][task]
        rows.append(
            Row(
                label=f"Task: {task} (pooled)",
                value=pooled["mean"],
                low=pooled["ci"][0],
                high=pooled["ci"][1],
                floor=pooled["floor"],
                decision=pooled["decision"],
                group=task,
                emphasis=True,
            )
        )
        for member in pooled["members"]:
            target = summary["targets"][member]
            portfolio = member.split("_")[1].capitalize()
            rows.append(
                Row(
                    label=f"{portfolio} portfolio",
                    value=target["mean"],
                    low=target["ci"][0],
                    high=target["ci"][1],
                    floor=target["floor"],
                    decision=target["decision"],
                    group=task,
                )
            )
    return rows


def _formatter(percent: bool) -> FuncFormatter:
    """Axis ticks: no sign on zero, because `+0.000` reads as a measured increase."""

    def fmt(value: float, _position: int) -> str:
        if abs(value) < 1e-12:
            return "0%" if percent else "0.000"
        return f"{value:+.0%}" if percent else f"{value:+.3f}"

    return FuncFormatter(fmt)


def _draw(
    rows: list[Row],
    *,
    stem: Path,
    xlabel: str,
    percent: bool,
    band: float | None = None,
) -> tuple[Path, Path]:
    """Draw one forest plot and export the PDF + PNG pair."""
    applied = {row.floor for row in rows if row.floor is not None}
    lo = min([row.low for row in rows if row.low is not None] + [0.0])
    hi = max([row.high for row in rows if row.high is not None] + list(applied) + [0.0])
    pad = (hi - lo) * 0.16 or 0.001
    xlim = (lo - pad, hi + pad)

    # Two panels — the forest and its decision column — so the width sits between the single- and
    # double-column sizes: the decision word is part of the claim, not a caption detail.
    fig = plt.figure(figsize=(5.5, 2.7))
    grid = fig.add_gridspec(
        1,
        2,
        width_ratios=(2.7, 1.05),
        left=0.30,
        right=0.995,
        bottom=0.17,
        top=0.84,
        wspace=0.04,
    )
    ax = fig.add_subplot(grid[0, 0])
    decisions = fig.add_subplot(grid[0, 1], sharey=ax)
    ax.set_xlim(*xlim)

    if band is not None:
        ax.axvspan(-band, band, color=NEUTRAL["band"], alpha=0.55, lw=0, zorder=0)
    ax.axvline(0.0, color=NEUTRAL["ink"], lw=0.7, zorder=1)

    positions: list[tuple[Row, float]] = []
    y = 0.0
    previous_group = None
    for row in rows:
        if previous_group is not None and row.group != previous_group:
            y -= 0.5
        positions.append((row, y))
        previous_group = row.group
        y -= 1.0

    for row, at in positions:
        colour = DECISION_COLOR[row.decision]  # a typo must fail, not grey a row

        if row.value is None:
            ax.axhspan(at - 0.34, at + 0.34, color=NEUTRAL["panel"], lw=0, zorder=0)
            ax.text(
                xlim[0] + pad * 0.35,
                at,
                row.detail,
                ha="left",
                va="center",
                fontsize=8,
                style="italic",
                color=NEUTRAL["muted"],
                zorder=3,
            )
        else:
            ax.plot(
                [row.low, row.high],
                [at, at],
                color=colour,
                lw=1.2,
                solid_capstyle="butt",
                zorder=2,
            )
            ax.plot(
                [row.value],
                [at],
                marker="o",
                markersize=4.2,
                color=colour,
                markerfacecolor=colour if row.computed else "white",
                markeredgecolor=colour,
                markeredgewidth=1.0,
                zorder=3,
            )
            ax.annotate(
                f"{row.value:+.2%}" if percent else f"{row.value:+.4f}",
                (row.value, at),
                xytext=(0, 5),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8,
                color=colour,
            )

        if row.floor is not None:
            # Below the row, not through it: the value label sits above the marker.
            ax.plot(
                [row.floor, row.floor],
                [at - 0.42, at - 0.05],
                color=NEUTRAL["muted"],
                lw=1.0,
                ls=(0, (2, 1)),
                zorder=2,
            )

        decisions.text(
            0.0,
            at,
            row.decision,
            ha="left",
            va="center",
            fontsize=8,
            color=colour,
            fontweight="bold" if row.emphasis else "normal",
        )

    ax.set_yticks([at for _, at in positions])
    ax.set_yticklabels([row.label for row, _ in positions])
    for tick_label, (row, _) in zip(ax.get_yticklabels(), positions):
        if row.emphasis:
            tick_label.set_fontweight("bold")

    ax.set_ylim(y + 0.35, 0.8)
    decisions.set_xlim(0.0, 1.0)
    decisions.axis("off")
    ax.set_xlabel(xlabel)
    ax.xaxis.set_major_formatter(_formatter(percent))
    ax.grid(axis="x", color=NEUTRAL["grid"], lw=0.6, zorder=0)
    ax.set_axisbelow(True)

    handles = []
    if band is not None:
        handles.append(
            Patch(facecolor=NEUTRAL["band"], alpha=0.55, edgecolor="none", label=f"δ = {band:.3f} band")
        )
        handles.append(
            Line2D([], [], marker="o", lw=0, color=NEUTRAL["muted"], label="computed from evidence")
        )
        handles.append(
            Line2D(
                [],
                [],
                marker="o",
                lw=0,
                color=NEUTRAL["muted"],
                markerfacecolor="white",
                label="quoted (no capture)",
            )
        )
    else:
        handles.append(
            Line2D(
                [],
                [],
                color=NEUTRAL["muted"],
                lw=1.2,
                marker="o",
                markersize=4,
                label="95% interval",
            )
        )
        if applied:
            handles.append(
                Line2D(
                    [],
                    [],
                    color=NEUTRAL["muted"],
                    lw=1.0,
                    ls=(0, (2, 1)),
                    label="registered floor",
                )
            )
    ax.legend(
        handles=handles,
        loc="lower left",
        bbox_to_anchor=(0.0, 1.0),
        ncol=2,
        fontsize=7,
        handlelength=1.2,
        handletextpad=0.4,
        columnspacing=1.2,
        borderaxespad=0.1,
        frameon=False,
    )

    return save_publication(fig, stem)


def main(argv: list[str] | None = None) -> int:
    parser = figure_parser(FIGURES, description=__doc__.splitlines()[0])
    parser.add_argument("--only", choices=("phase2", "fair-test", "both"), default="both")
    args = parser.parse_args(argv)

    apply_static_style()
    written: list[Path] = []

    if args.only in ("phase2", "both"):
        written += list(
            _draw(
                phase2_rows(),
                stem=args.out / "finetuning_phase2_forest",
                xlabel="Δ ROC AUC vs raw TabPFN (95% interval)",
                percent=False,
                band=DELTA,
            )
        )
    if args.only in ("fair-test", "both"):
        written += list(
            _draw(
                fair_test_rows(),
                stem=args.out / "freq_sev_forest",
                xlabel="Relative improvement vs raw TabPFN (95% interval)",
                percent=True,
            )
        )

    report_written(written)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
