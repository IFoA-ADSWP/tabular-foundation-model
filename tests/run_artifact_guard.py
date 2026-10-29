"""Guard against the test suite leaving benchmark artifacts in the repository.

A few tests drive the frontier runner's `main()` to prove that its guards fire. When one
of those guards regresses, the test does not fail politely: it fits a real dataset for
minutes and writes `results/<timestamp>/` into the tree, which nobody notices until the
next `git status`. This module turns that into an immediate, named failure.

The guard watches the *default* output roots. A test that passes `--out-dir legacy` writes
beside the script instead, and is deliberately out of scope: it is also a test asking for
trouble in a way this file cannot see.
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

RUN_OUTPUT_ROOTS = (
    REPO / "results",
    REPO / "scripts/eval/insurance_benchmark_v1/predictions",
)


def run_artifact_names(roots: tuple[Path, ...] = RUN_OUTPUT_ROOTS) -> set[str]:
    """One entry per run directory or capture beside each root, namespaced by the root."""
    names: set[str] = set()
    for root in roots:
        if not root.exists():
            continue
        names.update(f"{root.name}/{child.name}" for child in root.iterdir())
    return names


def assert_no_new_run_artifacts(
    before: set[str], roots: tuple[Path, ...] = RUN_OUTPUT_ROOTS
) -> None:
    """Fail, naming the artifacts, if anything new appeared under the run-output roots."""
    new = sorted(run_artifact_names(roots) - before)
    if new:
        raise AssertionError(
            "the test suite wrote run artifacts into the repo: "
            + ", ".join(new)
            + " — a test reached the dataset runner instead of a stub, so it would have "
            "fitted a dataset for minutes; stub the runner or pass --out-dir under tmp_path"
        )
