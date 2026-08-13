"""Lapse benchmark — classification + regression on eudirectlapse.

Usage:
    source /tmp/tabarena/.venv-ta/bin/activate
    python scripts/benchmarks/run_lapse_benchmark.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold, KFold

from tabarena.benchmark.experiment import TabArenaV0pt1ExperimentBundle
from tabarena.benchmark.task import UserTask
from tabarena.benchmark.task.metadata import (
    TabArenaTaskMetadata,
    TaskMetadataCollection,
)
from tabarena.benchmark.task.user_task import from_sklearn_splits_to_user_task_splits
from tabarena.contexts import AbstractArenaContext

# Reuse model classes from the full benchmark script
from run_tabarena_insurance_benchmark import (
    TabPFNClientModel,
    LogisticGlmModel,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
DATA_RAW = REPO / "data" / "raw"

RUN_NAME = "lapse_benchmark_v1"
RESULTS_DIR = str(REPO / "scripts" / "experiments" / RUN_NAME)
EVAL_DIR = REPO / "scripts" / "eval" / RUN_NAME
TASK_CACHE_DIR = REPO / "scripts" / "task_cache" / RUN_NAME


def _load_raw(info: dict) -> pd.DataFrame:
    df = pd.read_csv(DATA_RAW / info["file"])
    target = info["target"]
    if target not in df.columns:
        raise KeyError(f"Target column '{target}' not found in {DATA_RAW / info['file']}")
    # Convert object columns to categorical (TabArena requires non-object dtypes)
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].astype("category")
    return df.dropna(subset=[target])


def make_classification_task(
    name: str, info: dict, task_cache_dir: Path
) -> tuple[UserTask, TabArenaTaskMetadata]:
    dataset = _load_raw(info)
    target = info["target"]
    splits = from_sklearn_splits_to_user_task_splits(
        StratifiedKFold(
            n_splits=info["n_splits"], shuffle=True, random_state=42
        ).split(dataset.drop(columns=[target]), dataset[target]),
        n_splits=info["n_splits"],
    )
    task = UserTask(task_name=name, task_cache_path=task_cache_dir)
    wrapper = task.create_task(
        dataset=dataset,
        target_feature=target,
        problem_type="classification",
        splits=splits,
    )
    task.save_task(wrapper)
    return task, wrapper.metadata


def make_regression_task(
    name: str, info: dict, task_cache_dir: Path
) -> tuple[UserTask, TabArenaTaskMetadata]:
    dataset = _load_raw(info)
    target = info["target"]
    splits = {}
    for fold, (train_idx, test_idx) in enumerate(
        KFold(n_splits=info["n_splits"], shuffle=True, random_state=42).split(dataset)
    ):
        splits[fold] = {0: (train_idx.tolist(), test_idx.tolist())}
    task = UserTask(task_name=name, task_cache_path=task_cache_dir)
    wrapper = task.create_task(
        dataset=dataset,
        target_feature=target,
        problem_type="regression",
        splits=splits,
    )
    task.save_task(wrapper)
    return task, wrapper.metadata


# ---------------------------------------------------------------------------
# Datasets — eudirectlapse + spanish_motor_lapse
# ---------------------------------------------------------------------------
CLASSIFICATION = {
    "eudirectlapse": {
        "file": "eudirectlapse.csv",
        "target": "lapse",
        "n_splits": 5,
        "desc": "EU direct insurance lapse, 23K rows, 12.8% positive",
    },
    "spanish_motor_lapse": {
        "file": "spanish_motor_lapse.csv",
        "target": "LapseB",
        "n_splits": 5,
        "desc": "Spanish motor lapse (last policy-year per ID), 53.5K rows, 35.4% positive",
    },
}

REGRESSION = {
    "eudirectlapse_premium": {
        "file": "eudirectlapse.csv",
        "target": "prem_pure",
        "n_splits": 2,
        "desc": "EU direct insurance pure premium, 23K rows",
    },
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    TASK_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    EVAL_DIR.mkdir(parents=True, exist_ok=True)

    tasks, meta_list = [], []

    for name, info in CLASSIFICATION.items():
        task, meta = make_classification_task(name, info, TASK_CACHE_DIR)
        tasks.append(task)
        meta_list.append(meta)
        print(f"  ✓ {name} (classification) — {info['desc']}")

    for name, info in REGRESSION.items():
        task, meta = make_regression_task(name, info, TASK_CACHE_DIR)
        tasks.append(task)
        meta_list.append(meta)
        print(f"  ✓ {name} (regression) — {info['desc']}")

    task_collection = TaskMetadataCollection.from_source(meta_list)

    for task, meta in zip(tasks, meta_list):
        task.with_task_metadata(meta).load().validate_metadata()

    # Models — trimmed for a first pass on an 8-core M1: TabPFN is a hosted-API
    # call (server-side compute), LightGBM + Linear are the cheapest strong baselines.
    # Full 7-model panel is deferred to the GPU run.
    experiments = TabArenaV0pt1ExperimentBundle(
        models=[
            # --- Foundation ---
            (TabPFNClientModel.config_generator(), 0),
            # --- Tree-based ---
            ("LightGBM", 0, {"device_type": "cpu"}),
            # --- Statistical ---
            ("Linear", 0),
            # --- Deferred to GPU run ---
            # ("XGBoost", 0),
            # ("CatBoost", 0),
            # ("RandomForest", 0),
            # (LogisticGlmModel.config_generator(), 0),
        ],
        # ponytail: holdout = no bagging (1 fit per model per CV split). The default
        # 8 bagged folds x 2 CV splits x 7 models x 2 tasks = 224 fits is too heavy for
        # CPU. Point estimates suffice for a first pass; re-enable bagging on GPU.
        holdout_experiments=True,
    ).build_experiments(num_gpus=0)

    context = AbstractArenaContext(task_metadata=task_collection, methods=[])

    print(f"\nRunning {len(experiments)} experiments across {len(tasks)} lapse tasks...")
    context.build_and_run_jobs(
        experiments,
        expname=RESULTS_DIR,
        user_tasks=tasks,
        new_result_prefix="[Lapse] ",
        debug_mode=True,
    )

    leaderboard = context.compare(output_dir=EVAL_DIR)
    print("\n=== Lapse Benchmark Leaderboard ===")
    print(leaderboard.to_markdown())
    print(f"\nResults saved to {EVAL_DIR}")
