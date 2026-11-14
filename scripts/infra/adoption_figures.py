#!/usr/bin/env python3
"""The adoption picture in two figures (#609).

    .venv/bin/python scripts/infra/adoption_figures.py             # both, into docs/figures/
    .venv/bin/python scripts/infra/adoption_figures.py --only size --out /tmp/figures

- **`tabpfn_size_drift`** — TabPFN's metric divided by the best method's, against training rows on
  log–log axes, with the nine home-turf size-sweep cells (the six 1K/5K cells all tie at 1.00 and
  overlap). It answers "when is default TabPFN the
  right default?" in one picture: parity on small data, drift as the table grows.
- **`frontier_method_matrix`** — every frontier dataset against every method that ran, the same ratio
  as a colour and a number, datasets ordered by size and TabPFN's column outlined. It answers "what
  should I have used here?" without reading twelve tables.

Both are computed from committed evidence only — `scripts/eval/insurance_benchmark_v1/frontier_results_*.csv`,
`home_turf_sweep_results.csv`, the dataset registry that names them, and the committed raw CSVs those
registry entries point at for a row count. No ratio is typed; `tests/test_adoption_figures.py` asserts
the claims the captions make.

A note on what the ratio is not: the frontier metric differs by task (log loss for classification,
Poisson deviance or RMSE for regression), so a ratio is comparable within a dataset and not across
datasets. The figures say so rather than inviting the mistake.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402  (backend must be chosen before pyplot)
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import Normalize  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from src.experiment_spec import load_registry  # noqa: E402
from scripts.infra.figure_style import (  # noqa: E402
    NEUTRAL,
    OKABE_ITO,
    SEQUENTIAL_CMAP,
    apply_static_style,
    figure_parser,
    report_written,
    save_publication,
)

BENCHMARK = _REPO / "scripts" / "eval" / "insurance_benchmark_v1"
REGISTRY = BENCHMARK / "experiments.toml"
SWEEP = BENCHMARK / "home_turf_sweep_results.csv"
RAW = _REPO / "data" / "raw"
FIGURES = _REPO / "docs" / "figures"

#: Matrix columns: TabPFN first (it is the default under comparison), then trees, then statistical
#: models. A dataset that did not run a method gets a blank cell, never a zero.
METHOD_ORDER = (
    "tabpfn",
    "cat",
    "lgbm",
    "xgb",
    "rf",
    "logisticglm",
    "lr",
    "poissonglm",
    "ols",
    "tweedieglm",
)

#: Label offsets in points, for the five off-frontier points — the ones that carry the claim.
#: The seven on-frontier points sit on the 1.00 line and are named by the matrix figure and the
#: caption; labelling twelve in a 0.9-decade band collides at any legible size.
LABEL_OFFSETS = {
    "spanish_motor_freq": (-8, 10),
    "spanish_motor_severity": (7, -14),
    "ausprivauto0405": (8, -15),
    "bemtl97_amount": (-18, 10),
    "freMTPL2freq": (-14, 10),
}


@dataclass(frozen=True)
class FrontierDataset:
    """One frontier dataset's default-config comparison."""

    dataset: str
    n_rows: int
    ratio: float
    best_method: str
    on_frontier: bool


def _n_rows(path: Path) -> int:
    """Rows in the committed CSV, before any split — what the frontier harness fitted on."""
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return sum(1 for _ in handle) - 1


def _dataset_files() -> dict[str, str]:
    """The registry's datasets and the raw file each is read from, in registry order."""
    return {name: spec.file for name, spec in load_registry(REGISTRY).datasets.items()}


#: The plotted set. A private list would drift from `experiments.toml`; #235's rule is that a
#: producer selects its datasets from the registry, and this is the one selection both figures use.
DATASETS: dict[str, str] = _dataset_files()


@lru_cache(maxsize=None)
def _results(dataset: str) -> pd.DataFrame:
    """One dataset's frontier table, read once per process rather than once per figure."""
    return pd.read_csv(BENCHMARK / f"frontier_results_{dataset}.csv")


def _ratio_to_best(means: pd.Series) -> pd.Series:
    """Each method's metric divided by the best on that row, so the best is always 1.0."""
    return means / means.min()


def frontier_points() -> list[FrontierDataset]:
    """The twelve registry datasets, with TabPFN over the best method for each.

    The dataset list comes from `experiments.toml` rather than from the CSV filenames: the directory
    also holds per-seed reruns (`*_seed7`, `*_seed123`) that are stability checks, not datasets.
    """
    rows = {}
    points = []
    for name, raw_file in DATASETS.items():
        if not (BENCHMARK / f"frontier_results_{name}.csv").exists():
            continue
        table = _results(name)
        tabpfn = table[table["method"] == "tabpfn"]
        if tabpfn.empty:
            continue
        relative = _ratio_to_best(table.set_index("method")["mean"])
        if raw_file not in rows:
            rows[raw_file] = _n_rows(RAW / raw_file)
        points.append(
            FrontierDataset(
                dataset=name,
                n_rows=rows[raw_file],
                ratio=float(relative["tabpfn"]),
                best_method=str(relative.idxmin()),
                on_frontier=str(tabpfn.iloc[0]["on_frontier"]) == "yes",
            )
        )
    if not points:
        raise SystemExit(f"no frontier results under {BENCHMARK}")
    return sorted(points, key=lambda point: (point.n_rows, point.dataset))


def sweep_cells() -> pd.DataFrame:
    """The nine home-turf cells: TabPFN over the best method, per dataset × row count.

    The CSV records each TabPFN fold twice at 1K and 5K — once with a blank `n_estimators` and once
    with `8`, identical losses, an artefact of the v2 sweep assembly. Collapsing to one row per fold
    leaves the cell mean unchanged and makes the fold count mean what it says.
    """
    sweep = pd.read_csv(SWEEP)
    sweep = sweep[sweep["error"].isna()]
    sweep = sweep.drop_duplicates(subset=["dataset", "n_rows", "method", "fold"])
    means = (
        sweep.groupby(["dataset", "n_rows", "method"], as_index=False)["log_loss"]
        .mean()
        .rename(columns={"log_loss": "mean_log_loss"})
    )
    cells = []
    for (dataset, n_rows), per_method in means.groupby(["dataset", "n_rows"]):
        losses = per_method.set_index("method")["mean_log_loss"]
        cells.append(
            {
                "dataset": dataset,
                "n_rows": int(n_rows),
                "ratio": float(_ratio_to_best(losses)["tabpfn"]),
            }
        )
    return pd.DataFrame(cells).sort_values(["n_rows", "dataset"]).reset_index(drop=True)


def method_matrix(points: list[FrontierDataset]) -> np.ndarray:
    """Rows in `points` order, columns in `METHOD_ORDER`; each cell is the metric ÷ that row's best."""
    matrix = np.full((len(points), len(METHOD_ORDER)), np.nan)
    for row, point in enumerate(points):
        relative = _ratio_to_best(_results(point.dataset).set_index("method")["mean"])
        for column, method in enumerate(METHOD_ORDER):
            if method in relative.index:
                matrix[row, column] = float(relative[method])
    return matrix


def _size_drift(points: list[FrontierDataset], sweep: pd.DataFrame, stem: Path) -> tuple[Path, Path]:
    """Parity at small size, drift at scale — one point per dataset, plus the sweep cells."""
    # Single panel, but five dataset names have to sit beside their points at 8 pt; 3.5 in forces
    # them over the data. The width is the labels', not the panel's.
    fig, ax = plt.subplots(figsize=(5.8, 3.4))

    ax.scatter(
        sweep["n_rows"],
        sweep["ratio"],
        s=26,
        facecolors="none",
        edgecolors=NEUTRAL["muted"],
        linewidths=0.9,
        marker="D",
        zorder=2,
        label="size sweep 1K / 5K / full",
    )

    for point in points:
        colour = OKABE_ITO["blue"] if point.on_frontier else OKABE_ITO["vermillion"]
        ax.scatter(
            [point.n_rows],
            [point.ratio],
            s=34,
            color=colour,
            edgecolors=NEUTRAL["surface"],
            linewidths=0.7,
            zorder=3,
        )
        if point.dataset in LABEL_OFFSETS:
            dx, dy = LABEL_OFFSETS[point.dataset]
            ax.annotate(
                point.dataset,
                (point.n_rows, point.ratio),
                textcoords="offset points",
                xytext=(dx, dy),
                fontsize=8,
                color=colour,
                zorder=4,
            )

    ax.axhline(1.0, color=NEUTRAL["ink"], ls=(0, (4, 2)), lw=0.8, zorder=1)
    ax.set_xscale("log")
    ax.set_yscale("log")
    # From 700 rows: the sweep's 1K and 5K cells are the small-data half of the claim and must be
    # inside the axes, not clipped off the left edge.
    ax.set_xlim(7e2, 1.3e6)
    ax.set_ylim(0.97, 1.75)
    ax.set_yticks([1.0, 1.1, 1.25, 1.5])
    ax.set_yticklabels(["1.00", "1.10", "1.25", "1.50"], fontsize=7)
    ax.minorticks_off()
    ax.set_xlabel("Training rows (log scale)")
    ax.set_ylabel("TabPFN metric ÷ best method\n(log scale, 1.0 = ties the best)")
    ax.grid(which="major", color=NEUTRAL["grid"], lw=0.6)
    ax.set_axisbelow(True)

    handles = [
        Line2D([], [], marker="o", ls="", color=OKABE_ITO["blue"], markersize=5, label="on the parsimony frontier"),
        Line2D([], [], marker="o", ls="", color=OKABE_ITO["vermillion"], markersize=5, label="off the frontier"),
        Line2D(
            [],
            [],
            marker="D",
            ls="",
            markerfacecolor="none",
            markeredgecolor=NEUTRAL["muted"],
            markersize=5,
            label="size sweep 1K / 5K / full",
        ),
    ]
    ax.legend(
        handles=handles,
        loc="upper left",
        fontsize=7,
        handletextpad=0.4,
        borderaxespad=0.3,
        frameon=False,
    )

    return save_publication(fig, stem)


def _method_matrix(points: list[FrontierDataset], stem: Path) -> tuple[Path, Path]:
    """The whole benchmark as a grid: metric ÷ the dataset's best, per method."""
    matrix = method_matrix(points)
    masked = np.ma.masked_invalid(matrix)
    cmap = SEQUENTIAL_CMAP.with_extremes(bad=NEUTRAL["band"])

    # A 12-row x 10-column matrix: each cell must hold an 8 pt number, so the width is set by
    # ten legible columns plus the row labels, not by a single-panel rule.
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    image = ax.imshow(
        masked,
        cmap=cmap,
        norm=Normalize(vmin=1.0, vmax=1.5),
        aspect="auto",
        interpolation="nearest",
    )

    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            value = matrix[row, column]
            if np.isnan(value):
                continue
            ax.text(
                column,
                row,
                f"{value:.2f}",
                ha="center",
                va="center",
                fontsize=8,
                color=NEUTRAL["surface"] if value > 1.25 else NEUTRAL["ink"],
            )

    ax.set_xticks(range(len(METHOD_ORDER)))
    # Vertical, not slanted: the method ids are long enough that any slant overlaps its neighbour
    # at a legible size, and shortening them would introduce names the registry does not use.
    ax.set_xticklabels(METHOD_ORDER, rotation=90, ha="center", va="top", fontsize=8)
    ax.set_yticks(range(len(points)))
    ax.set_yticklabels([point.dataset for point in points], fontsize=8)
    ax.tick_params(length=0)

    ax.add_patch(
        Rectangle(
            (-0.5, -0.5),
            1.0,
            len(points),
            fill=False,
            edgecolor=NEUTRAL["ink"],
            lw=1.0,
            zorder=5,
        )
    )
    ax.get_xticklabels()[METHOD_ORDER.index("tabpfn")].set_fontweight("bold")

    colourbar = fig.colorbar(image, ax=ax, fraction=0.025, pad=0.02)
    colourbar.set_label("metric ÷ this dataset's best (1.00 = best)", fontsize=8)
    colourbar.ax.tick_params(labelsize=7)
    colourbar.outline.set_visible(False)

    ax.set_xticks(np.arange(-0.5, len(METHOD_ORDER), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(points), 1), minor=True)
    ax.grid(which="minor", color=NEUTRAL["surface"], lw=0.8)
    ax.tick_params(which="minor", length=0)

    fig.tight_layout()
    return save_publication(fig, stem)


def main(argv: list[str] | None = None) -> int:
    parser = figure_parser(FIGURES, description=__doc__.splitlines()[0])
    parser.add_argument("--only", choices=("size", "matrix", "both"), default="both")
    args = parser.parse_args(argv)

    apply_static_style()
    written: list[Path] = []

    points = frontier_points()
    if args.only in ("size", "both"):
        written += list(_size_drift(points, sweep_cells(), args.out / "tabpfn_size_drift"))
    if args.only in ("matrix", "both"):
        written += list(_method_matrix(points, args.out / "frontier_method_matrix"))

    report_written(written)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
