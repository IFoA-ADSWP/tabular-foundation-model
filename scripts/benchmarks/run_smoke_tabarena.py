"""Smoke test for TabArena insurance benchmark.

Validates end-to-end pipeline on a single small dataset with 3 models.
Run this before the full 7-dataset benchmark.

Usage:
    source .venv-ta/bin/activate
    python scripts/benchmarks/run_smoke_tabarena.py
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from autogluon.core.models import AbstractModel
from sklearn.model_selection import StratifiedKFold

from tabarena.benchmark.experiment import TabArenaV0pt1ExperimentBundle
from tabarena.benchmark.task import UserTask
from tabarena.benchmark.task.metadata import TaskMetadataCollection
from tabarena.benchmark.task.user_task import from_sklearn_splits_to_user_task_splits
from tabarena.contexts import AbstractArenaContext

if TYPE_CHECKING:
    from tabarena.utils.config_utils import ConfigGenerator

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
DATA_RAW = REPO / "data" / "raw"

RUN_NAME = "smoke_test"
RESULTS_DIR = str(REPO / "scripts" / "experiments" / RUN_NAME)
EVAL_DIR = REPO / "scripts" / "eval" / RUN_NAME
TASK_CACHE_DIR = REPO / "scripts" / "task_cache" / RUN_NAME

# ---------------------------------------------------------------------------
# Single dataset — coil2000 (smallest, 9.8K rows)
# ---------------------------------------------------------------------------
DATASET = {
    "file": "coil2000.csv",
    "target": "CARAVAN",
    "n_splits": 2,
    "desc": "CoIL 2000 caravan insurance, 9.8K rows, 6.0% positive",
}


def make_smoke_task(task_cache_dir: Path):
    dataset = pd.read_csv(DATA_RAW / DATASET["file"]).dropna(subset=[DATASET["target"]])
    target = DATASET["target"]
    splits = from_sklearn_splits_to_user_task_splits(
        StratifiedKFold(
            n_splits=DATASET["n_splits"], shuffle=True, random_state=42
        ).split(dataset.drop(columns=[target]), dataset[target]),
        n_splits=DATASET["n_splits"],
    )
    task = UserTask(task_name="coil2000_smoke", task_cache_path=task_cache_dir)
    wrapper = task.create_task(
        dataset=dataset,
        target_feature=target,
        problem_type="classification",
        splits=splits,
    )
    task.save_task(wrapper)
    return task, wrapper.metadata


# ---------------------------------------------------------------------------
# TabPFN Client (hosted API)
# ---------------------------------------------------------------------------
class SmokeTabPFNModel(AbstractModel):
    ag_key = "TabPFNSmoke"
    ag_name = "TabPFNSmoke"

    def _fit(self, X, y, **kwargs):
        from tabpfn_client import TabPFNClassifier
        Xp = self.preprocess(X, y=y, is_train=True)
        self.model = TabPFNClassifier(model_path="v3_default", random_state=0)
        self.model.fit(Xp, y)

    def _preprocess(self, X, is_train=False, **kwargs):
        X = super()._preprocess(X, **kwargs)
        return X.fillna(0).to_numpy(dtype=np.float32)

    def _set_default_params(self):
        pass

    def _get_default_auxiliary_params(self) -> dict:
        d = super()._get_default_auxiliary_params()
        d.update({"valid_raw_types": ["int", "float"]})
        return d

    @classmethod
    def supported_problem_types(cls) -> list[str]:
        return ["binary", "multiclass", "regression"]

    @classmethod
    def config_generator(cls) -> ConfigGenerator:
        from tabarena.utils.config_utils import ConfigGenerator
        return ConfigGenerator(search_space={}, model_cls=cls, manual_configs=[{}])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    TASK_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    EVAL_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Build dataset
    print(f"Loading {DATASET['desc']}...")
    task, meta = make_smoke_task(TASK_CACHE_DIR)
    task.with_task_metadata(meta).load().validate_metadata()
    print("  ✓ dataset ready")

    # 2. Build models — one from each family
    experiments = TabArenaV0pt1ExperimentBundle(
        models=[
            (SmokeTabPFNModel.config_generator(), 0),   # foundation (API)
            ("LightGBM", 0),                              # tree-based (registry)
            ("Linear", 0),                                # statistical (registry, sklearn LogisticRegression)
        ],
    ).build_experiments(num_gpus=0)

    # 3. Run
    context = AbstractArenaContext(
        task_metadata=TaskMetadataCollection.from_source([meta]),
        methods=[],
    )
    print(f"\nRunning {len(experiments)} experiments...")
    context.build_and_run_jobs(
        experiments,
        expname=RESULTS_DIR,
        user_tasks=[task],
        new_result_prefix="[Smoke] ",
        debug_mode=True,
    )

    # 4. Leaderboard
    leaderboard = context.compare(output_dir=EVAL_DIR)
    print("\n=== Smoke Test Leaderboard ===")
    print(leaderboard.to_markdown())
    print(f"\nResults saved to {EVAL_DIR}")
    print("\n✓ Smoke test complete.")
