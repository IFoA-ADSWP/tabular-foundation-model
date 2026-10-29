"""The suite must not leave benchmark artifacts in the repository.

See `docs/plans/suite-hygiene.md` for the incident and the chosen limits.
"""

from __future__ import annotations

import importlib.util

import pytest

from tests import run_artifact_guard


def _runner():
    """The frontier runner, imported the way its own CLI tests import it."""
    script = (run_artifact_guard.REPO
              / "scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py")
    spec = importlib.util.spec_from_file_location("runner_for_guard_test", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_guard_watches_the_roots_the_runner_writes():
    # Pinned against the runner, not against the guard's own constant — otherwise the
    # assertion passes even if both drift somewhere useless.
    runner = _runner()
    assert runner.PREDICTIONS_DIR in run_artifact_guard.RUN_OUTPUT_ROOTS
    assert runner.REPO / "results" in run_artifact_guard.RUN_OUTPUT_ROOTS
    assert runner.REPO / "catboost_info" in run_artifact_guard.RUN_OUTPUT_ROOTS


@pytest.mark.parametrize("mutation, expected", [
    (lambda root: (root / "20261029-000756").mkdir(), "added: .*20261029-000756"),
    (lambda root: (root / "capture.npz").write_text("x" * 10), "added: .*capture.npz"),
])
def test_a_new_artifact_fails_the_guard(tmp_path, mutation, expected):
    before = run_artifact_guard.run_artifacts((tmp_path,))
    mutation(tmp_path)

    with pytest.raises(AssertionError, match=expected):
        run_artifact_guard.assert_no_new_run_artifacts(before, (tmp_path,))


def test_an_overwritten_artifact_fails_the_guard(tmp_path):
    # The names are unchanged; only the bytes moved. A capture re-written by a misfired
    # --save-predictions run is exactly this, and it must not pass silently.
    capture = tmp_path / "coil2000__seed42__v3_default.npz"
    capture.write_text("original")
    before = run_artifact_guard.run_artifacts((tmp_path,))

    capture.write_text("a longer replacement payload")

    with pytest.raises(AssertionError, match="overwritten: .*coil2000__seed42__v3_default"):
        run_artifact_guard.assert_no_new_run_artifacts(before, (tmp_path,))


def test_an_unchanged_tree_passes_the_guard(tmp_path):
    (tmp_path / "20261028-235900").mkdir()
    before = run_artifact_guard.run_artifacts((tmp_path,))

    run_artifact_guard.assert_no_new_run_artifacts(before, (tmp_path,))  # no raise
