"""Guard against the test suite leaving benchmark artifacts in the repository.

A few tests drive the frontier runner's `main()` to prove that its guards fire. When one
of those guards regresses, the test does not fail politely: it fits a real dataset for
minutes and writes into the tree, which nobody notices until the next `git status`.

This module fingerprints the output roots a run writes to and reports what appeared or
was overwritten. See `docs/plans/suite-hygiene.md` for why it exists and what it does not
cover.
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# The roots a real run writes by default. `catboost_info/` is CatBoost's own dump during
# a GBDT fit, which AGENTS.md lists as an experiment output and .gitignore hides.
RUN_OUTPUT_ROOTS = (
    REPO / "results",
    REPO / "scripts/eval/insurance_benchmark_v1/predictions",
    REPO / "catboost_info",
)

# path -> (mtime_ns, size). Content is not hashed: an overwrite rewrites the file, so the
# fingerprint moves, and hashing tens of megabytes per session is not worth it.
Artifacts = set[tuple[Path, int, int]]


def run_artifacts(roots: tuple[Path, ...] = RUN_OUTPUT_ROOTS) -> Artifacts:
    """Fingerprint every immediate child of each output root."""
    found: Artifacts = set()
    for root in roots:
        if not root.exists():
            continue
        for child in root.iterdir():
            try:
                stat = child.stat()
            except OSError:  # a broken symlink is not an artifact
                continue
            found.add((child, stat.st_mtime_ns, stat.st_size))
    return found


def assert_no_new_run_artifacts(
    before: Artifacts, roots: tuple[Path, ...] = RUN_OUTPUT_ROOTS
) -> None:
    """Fail, naming them, if anything appeared or changed under the output roots."""
    old = {path: (mtime, size) for path, mtime, size in before}
    new = {path: (mtime, size) for path, mtime, size in run_artifacts(roots)}

    added = sorted(set(new) - set(old))
    overwritten = sorted(path for path in set(new) & set(old) if new[path] != old[path])
    if not (added or overwritten):
        return

    found = []
    if added:
        found.append("added: " + ", ".join(_label(path) for path in added))
    if overwritten:
        found.append("overwritten: " + ", ".join(_label(path) for path in overwritten))
    raise AssertionError(
        "the test suite wrote run artifacts into the repo ("
        + "; ".join(found)
        + ") — a test reached the dataset runner instead of a stub, so it would have "
        "fitted a dataset for minutes; stub the runner or pass --out-dir under tmp_path"
    )


def _label(path: Path) -> str:
    """Repo-relative when possible, so the message reads like the path you would open."""
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)
