"""The suite must not leave benchmark artifacts in the repository.

Some tests exercise the frontier runner's `main()` to prove a guard fires. When one of
those guards regresses, the test does not fail politely: it fits a real dataset for
minutes and writes `results/<timestamp>/` into the tree, which is only noticed on the
next `git status`. These tests pin the guard that makes it loud instead.
"""

from __future__ import annotations

import pytest

from tests import run_artifact_guard


def test_a_new_run_directory_fails_the_guard(tmp_path):
    before = run_artifact_guard.run_artifact_names((tmp_path,))
    (tmp_path / "20261029-000756").mkdir()

    with pytest.raises(AssertionError, match="20261029-000756"):
        run_artifact_guard.assert_no_new_run_artifacts(before, (tmp_path,))


def test_an_unchanged_tree_passes_the_guard(tmp_path):
    (tmp_path / "20261028-235900").mkdir()
    before = run_artifact_guard.run_artifact_names((tmp_path,))

    run_artifact_guard.assert_no_new_run_artifacts(before, (tmp_path,))  # no raise


def test_the_guard_watches_the_default_run_outputs():
    guarded = {path.name for path in run_artifact_guard.RUN_OUTPUT_ROOTS}

    # a default run writes here; a capture run writes the second
    assert "results" in guarded
    assert "predictions" in guarded
