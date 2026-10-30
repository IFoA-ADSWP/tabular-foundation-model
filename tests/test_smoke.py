"""Smoke tests — fail loudly if the package is broken.

These tests assert that the public surface of `src/` imports cleanly
and that critical constants in `baseline_config.py` are present and
of the expected type.
"""

from __future__ import annotations

import pytest


def test_src_imports() -> None:
    """All public modules in src/ must be importable."""
    # These imports are wrapped in try/except so a single missing module
    # doesn't mask other failures. The exact module list mirrors
    # MAINTENANCE_BACKLOG.md Issue 24.
    module_names = [
        "baseline_config",
        "baseline_utils",
        "cleanup_outputs",
        "data_loader",
        "data_loader_class",
        "evaluation_metrics",
        "model_training",
    ]
    failed = []
    for name in module_names:
        try:
            __import__(name)
        except Exception as e:  # noqa: BLE001  (the smoke test reports any import failure)
            failed.append((name, repr(e)))
    assert not failed, f"failed to import: {failed}"


def test_baseline_config_random_seed() -> None:
    """RANDOM_SEED must exist and be an int (Issue 18: standardise seed)."""
    from baseline_config import RANDOM_SEED

    assert isinstance(RANDOM_SEED, int), f"RANDOM_SEED must be int, got {type(RANDOM_SEED)}"


def test_baseline_config_data_dir_exists() -> None:
    """DATA_DIR must point to a real directory in the repo."""
    from baseline_config import DATA_DIR

    assert DATA_DIR.exists(), f"DATA_DIR does not exist: {DATA_DIR}"
    assert DATA_DIR.is_dir(), f"DATA_DIR is not a directory: {DATA_DIR}"


@pytest.mark.parametrize(
    "metric_fn_name",
    ["rmse", "mae", "accuracy"],
)
def test_evaluation_metrics_public_api(metric_fn_name: str) -> None:
    """The simple metric functions must be importable and callable."""
    from evaluation_metrics import accuracy, mae, rmse

    functions = {"rmse": rmse, "mae": mae, "accuracy": accuracy}
    fn = functions[metric_fn_name]
    assert callable(fn), f"{metric_fn_name} must be callable"
