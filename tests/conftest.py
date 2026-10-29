"""Pytest configuration: make `src/` importable, and refuse to leave run artifacts behind.

This file is loaded by pytest before any tests run. It adds the repo root and the `src/`
directory to `sys.path` so that `import src.data_loader` works without needing to install
the package as editable, and the repo root so the test modules can import shared helpers.

The session fixture below is a guard, not decoration: see `tests/run_artifact_guard.py`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SRC = _REPO / "src"
for _path in (_REPO, _SRC):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from tests.run_artifact_guard import (  # noqa: E402  (path set up immediately above)
    assert_no_new_run_artifacts,
    run_artifact_names,
)


@pytest.fixture(scope="session", autouse=True)
def _no_run_artifacts_left_behind():
    """Fail the session if a test wrote a run directory into the repo.

    Cheaper to discover here than from `git status` after a two-minute benchmark.
    """
    before = run_artifact_names()
    yield
    assert_no_new_run_artifacts(before)
