"""TabArena insurance benchmark — foundation vs tree-based vs statistical models.

Usage:
    # 1. Clone and install TabArena (one-time)
    git clone https://github.com/autogluon/tabarena.git /tmp/tabarena
    uv venv --seed --python 3.12 .venv-ta
    source .venv-ta/bin/activate
    uv pip install --prerelease=allow -e "/tmp/tabarena/packages/tabarena[benchmark,tabfm]"

    # 2. Run
    python scripts/benchmarks/run_tabarena_insurance_benchmark.py

What it does:
    Wraps 6 classification + 3 regression insurance datasets from data/raw/
    as TabArena UserTasks, runs 10 models across 3 families, and outputs
    a leaderboard table comparing them.

    Datasets:   uslapseagent, coil2000, ausprivauto0405, bemtpl97, bemtpl16,
                norauto  (class)
                ausautoBI8999, ausprivauto0405-vehvalue, bemtpl97-amount  (reg)

    Models:
        Foundational  -> TabPFN (via tabpfn-client hosted API)   ← no GPU needed
                          TabFM (via PyTorch, 1K-row subsets)    ← CPU-feasible at this size
        Tree-based    -> LightGBM, XGBoost, CatBoost, RandomForest
        Statistical   -> LogisticRegression, Poisson GLM, Tweedie GLM, LinearRegression
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from autogluon.core.models import AbstractModel
from sklearn.model_selection import StratifiedKFold, KFold

from tabarena.benchmark.experiment import TabArenaV0pt1ExperimentBundle
from tabarena.benchmark.task import UserTask
from tabarena.benchmark.task.metadata import (
    TabArenaTaskMetadata,
    TaskMetadataCollection,
)
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

RUN_NAME = "insurance_benchmark_v1"
RESULTS_DIR = str(REPO / "scripts" / "experiments" / RUN_NAME)
EVAL_DIR = REPO / "scripts" / "eval" / RUN_NAME
TASK_CACHE_DIR = REPO / "scripts" / "task_cache" / RUN_NAME

# ---------------------------------------------------------------------------
# Dataset definitions — full
# ---------------------------------------------------------------------------
CLASSIFICATION_DATASETS = {
    "uslapseagent": {
        "file": "uslapseagent.csv",
        "target": "surrender",
        "n_splits": 5,
        "desc": "US life insurance lapse, 29K rows, 37.9% positive",
    },
    "coil2000": {
        "file": "coil2000.csv",
        "target": "CARAVAN",
        "n_splits": 5,
        "desc": "CoIL 2000 caravan insurance, 9.8K rows, 6.0% positive",
    },
    "ausprivauto0405": {
        "file": "ausprivauto0405.csv",
        "target": "ClaimOcc",
        "n_splits": 5,
        "desc": "Australian vehicle insurance claim occurrence, 68K rows, 6.8% positive",
    },
    "bemtl97": {
        "file": "bemtl97.csv",
        "target": "claim",
        "n_splits": 5,
        "desc": "Belgian motor TPL 1997, 163K rows, 11.2% positive",
    },
    "bemtl16": {
        "file": "bemtl16.csv",
        "target": "number_of_liability_claims",
        "n_splits": 5,
        "desc": "Belgian motor TPL 2016 panel (deduped), 59K rows, 36.0% positive",
    },
    "norauto": {
        "file": "norauto.csv",
        "target": "NbClaim",
        "n_splits": 5,
        "desc": "Norwegian auto claims (binarised), 184K rows, 4.6% positive",
    },
}

REGRESSION_DATASETS = {
    "ausautoBI8999": {
        "file": "ausautoBI8999.csv",
        "target": "AggClaim",
        "n_splits": 3,
        "desc": "Australian auto BI severity, 22K rows, log target",
    },
    "ausprivauto0405_vehvalue": {
        "file": "ausprivauto0405.csv",
        "target": "VehValue",
        "n_splits": 3,
        "desc": "Vehicle value regression, 68K rows, continuous target",
    },
    "bemtl97_amount": {
        "file": "bemtl97.csv",
        "target": "amount",
        "n_splits": 3,
        "desc": "Belgian motor TPL 1997 severity, 163K rows, log1p zero-inflated target",
    },
}

# ---------------------------------------------------------------------------
# Small subsets for GPU-bound models like TabFM (1K rows, CPU-feasible)
# ---------------------------------------------------------------------------
TABFM_SMALL_DATASETS = {
    "eudirectlapse_1k": {
        "file": "eudirectlapse.csv",
        "target": "lapse",
        "n_splits": 3,
        "n_rows": 1000,
        "desc": "EU lapse (1K subset for TabFM)",
    },
    "coil2000_1k": {
        "file": "coil2000.csv",
        "target": "CARAVAN",
        "n_splits": 3,
        "n_rows": 1000,
        "desc": "CoIL 2000 (1K subset for TabFM)",
    },
    "freMTPL2freq_binary_1k": {
        "file": "freMTPL2freq_binary.csv",
        "target": "ClaimIndicator",
        "n_splits": 3,
        "n_rows": 1000,
        "desc": "French motor TPL (1K subset for TabFM)",
    },
}


def _load_raw(info: dict) -> pd.DataFrame:
    path = DATA_RAW / info["file"]
    df = pd.read_csv(path)
    target = info["target"]
    if target not in df.columns:
        raise KeyError(f"Target column '{target}' not found in {path}")
    # Convert object columns to categorical (TabArena metadata requires non-object dtypes)
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].astype("category")
    return df.dropna(subset=[target])


def _sample_balanced(df: pd.DataFrame, target: str, n_rows: int, seed: int = 42) -> pd.DataFrame:
    """Stratified sample down to n_rows preserving class balance."""
    from sklearn.model_selection import train_test_split
    df_out, _ = train_test_split(
        df, train_size=n_rows, stratify=df[target], random_state=seed
    )
    return df_out


def make_classification_task(
    name: str, info: dict, task_cache_dir: Path
) -> tuple[UserTask, TabArenaTaskMetadata]:
    """Build a k-fold classification UserTask from a raw CSV."""
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
    """Build a k-fold regression UserTask from a raw CSV."""
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


def make_tabfm_task(
    name: str, info: dict, task_cache_dir: Path
) -> tuple[UserTask, TabArenaTaskMetadata]:
    """Build a 3-fold classification UserTask from a 1K stratified subset."""
    dataset = _load_raw(info)
    target = info["target"]
    dataset = _sample_balanced(dataset, target, n_rows=info["n_rows"])
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


# ---------------------------------------------------------------------------
# Custom model: TabPFN via hosted API  (no GPU required)
# ---------------------------------------------------------------------------

class TabPFNClientModel(AbstractModel):
    """TabPFN via tabpfn-client hosted API.

    Uses Prior Labs' cloud inference — no local GPU needed. Requires
    ``TABPFN_API_KEY`` env var or interactive login via ``tabpfn_client.init()``.
    """

    ag_key = "TabPFNClient"
    ag_name = "TabPFNClient"

    def _fit(self, X: pd.DataFrame, y: pd.Series, **kwargs) -> None:
        Xp = self.preprocess(X, y=y, is_train=True)
        if self.problem_type == "regression":
            from tabpfn_client import TabPFNRegressor
            self.model = TabPFNRegressor(model_path="v3_default", random_state=0)
        else:
            from tabpfn_client import TabPFNClassifier
            self.model = TabPFNClassifier(model_path="v3_default", random_state=0)
        self.model.fit(Xp, y)

    def _preprocess(self, X, is_train=False, **kwargs):
        X = super()._preprocess(X, **kwargs)
        return X.fillna(0).to_numpy(dtype=np.float32)

    def _set_default_params(self) -> None:
        pass

    def _get_default_auxiliary_params(self) -> dict:
        default = super()._get_default_auxiliary_params()
        default.update({"valid_raw_types": ["int", "float"]})
        return default

    @classmethod
    def supported_problem_types(cls) -> list[str]:
        return ["binary", "multiclass", "regression"]

    @classmethod
    def config_generator(cls) -> ConfigGenerator:
        from tabarena.utils.config_utils import ConfigGenerator
        return ConfigGenerator(search_space={}, model_cls=cls, manual_configs=[{}])


# ---------------------------------------------------------------------------
# Custom GLM models
# ---------------------------------------------------------------------------

class PoissonGlmModel(AbstractModel):
    """GLM with Poisson family — for claim count regression."""
    ag_key = "PoissonGLM"
    ag_name = "PoissonGLM"

    def _fit(self, X: pd.DataFrame, y: pd.Series, **kwargs) -> None:
        from sklearn.linear_model import PoissonRegressor
        Xp = self.preprocess(X, y=y, is_train=True)
        self.model = PoissonRegressor(alpha=0.0, max_iter=500)
        self.model.fit(Xp, y)

    def _preprocess(self, X, is_train=False, **kwargs):
        X = super()._preprocess(X, **kwargs)
        return X.fillna(0).to_numpy(dtype=np.float32)

    def _set_default_params(self) -> None:
        pass

    @classmethod
    def supported_problem_types(cls) -> list[str]:
        return ["regression"]

    @classmethod
    def config_generator(cls) -> ConfigGenerator:
        from tabarena.utils.config_utils import ConfigGenerator
        return ConfigGenerator(search_space={}, model_cls=cls, manual_configs=[{}])


class TweedieGlmModel(AbstractModel):
    """GLM with Tweedie family (p=1.5) — for pure premium regression."""
    ag_key = "TweedieGLM"
    ag_name = "TweedieGLM"

    def __init__(self, tweedie_p: float = 1.5, **kwargs):
        self.tweedie_p = tweedie_p
        super().__init__(**kwargs)

    def _fit(self, X: pd.DataFrame, y: pd.Series, **kwargs) -> None:
        from sklearn.linear_model import TweedieRegressor
        Xp = self.preprocess(X, y=y, is_train=True)
        self.model = TweedieRegressor(power=self.tweedie_p, alpha=0.0, max_iter=500)
        self.model.fit(Xp, y)

    def _preprocess(self, X, is_train=False, **kwargs):
        X = super()._preprocess(X, **kwargs)
        return X.fillna(0).to_numpy(dtype=np.float32)

    def _set_default_params(self) -> None:
        pass

    @classmethod
    def supported_problem_types(cls) -> list[str]:
        return ["regression"]

    @classmethod
    def config_generator(cls) -> ConfigGenerator:
        from tabarena.utils.config_utils import ConfigGenerator
        return ConfigGenerator(search_space={}, model_cls=cls, manual_configs=[{"tweedie_p": 1.5}])


class LogisticGlmModel(AbstractModel):
    """GLM with Binomial family (logistic) — for binary classification."""
    ag_key = "LogisticGLM"
    ag_name = "LogisticGLM"

    def _fit(self, X: pd.DataFrame, y: pd.Series, **kwargs) -> None:
        from sklearn.linear_model import LogisticRegression
        Xp = self.preprocess(X, y=y, is_train=True)
        self.model = LogisticRegression(penalty=None, solver="lbfgs", max_iter=500, random_state=0)
        self.model.fit(Xp, y)

    def _preprocess(self, X, is_train=False, **kwargs):
        X = super()._preprocess(X, **kwargs)
        return X.fillna(0).to_numpy(dtype=np.float32)

    def _set_default_params(self) -> None:
        pass

    @classmethod
    def supported_problem_types(cls) -> list[str]:
        return ["binary"]

    @classmethod
    def config_generator(cls) -> ConfigGenerator:
        from tabarena.utils.config_utils import ConfigGenerator
        return ConfigGenerator(search_space={}, model_cls=cls, manual_configs=[{}])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    TASK_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # ---- 1. Build full-size datasets ----
    print("Building classification tasks...")
    cls_tasks, cls_meta = [], []
    for name, info in CLASSIFICATION_DATASETS.items():
        task, meta = make_classification_task(name, info, TASK_CACHE_DIR)
        cls_tasks.append(task)
        cls_meta.append(meta)
        print(f"  ✓ {name} ({info['desc']})")

    print("Building regression tasks...")
    reg_tasks, reg_meta = [], []
    for name, info in REGRESSION_DATASETS.items():
        task, meta = make_regression_task(name, info, TASK_CACHE_DIR)
        reg_tasks.append(task)
        reg_meta.append(meta)
        print(f"  ✓ {name} ({info['desc']})")

    # ---- 2. Skip 1K-row TabFM subsets (TabFM dropped, see models list) ----
    tabfm_tasks, tabfm_meta = [], []

    all_tasks = cls_tasks + reg_tasks + tabfm_tasks
    all_meta = cls_meta + reg_meta + tabfm_meta
    task_collection = TaskMetadataCollection.from_source(all_meta)

    for task, meta in zip(all_tasks, all_meta):
        task.with_task_metadata(meta).load().validate_metadata()

    # ---- 3. Define models ----
    # Split by problem type: the bundle force-fits every model on every task, but the
    # GLMs are family-specific (Logistic = binary, Poisson/Tweedie = regression) and
    # autogluon refuses to fit them on mismatched tasks (aborts the whole run).
    common_models = [
        # --- Foundation (hosted API, no GPU) ---
        (TabPFNClientModel.config_generator(), 0),
        # ponytail: TabFM dropped — 6.1GB checkpoint on an 8GB Mac is
        # OOM-killed every time. Re-add on a GPU box (needs the 1K subsets).
        # --- Tree-based (registry, all CPU) ---
        ("LightGBM", 0, {"device_type": "cpu"}),
        ("XGBoost", 0),
        ("CatBoost", 0),
        ("RandomForest", 0),
    ]
    classification_models = common_models + [
        (LogisticGlmModel.config_generator(), 0),
        ("Linear", 0),
    ]
    regression_models = common_models + [
        (PoissonGlmModel.config_generator(), 0),
        (TweedieGlmModel.config_generator(), 0),
        ("Linear", 0),
    ]
    bundle_kwargs = dict(
        # ponytail: holdout = no bagging (1 fit per model per split). The default
        # 8-bag folds would be hundreds of fits across 7 datasets on an 8-core M1;
        # point estimates for this first full pass, re-enable bagging on GPU.
        holdout_experiments=True,
    )

    # ---- 4. Run benchmark ----
    # register=False on each panel: register() scopes the context's collection to the
    # just-run tasks, which would empty the regression panel after classification ran.
    # Collect all results, then one register() for both panels before compare().
    context = AbstractArenaContext(task_metadata=task_collection, methods=[])

    all_results: list[dict] = []
    for panel, problem_types, panel_tasks in [
        (classification_models, ["binary", "multiclass"], cls_tasks),
        (regression_models, ["regression"], reg_tasks),
    ]:
        experiments = TabArenaV0pt1ExperimentBundle(models=panel, **bundle_kwargs).build_experiments(num_gpus=0)
        print(f"\nRunning {len(experiments)} experiments on {problem_types} tasks...")
        results = context.build_and_run_jobs(
            experiments,
            expname=RESULTS_DIR,
            user_tasks=panel_tasks,
            register=False,
            new_result_prefix="[Insurance] ",
            debug_mode=True,
            build_kwargs={"problem_types": problem_types},
        )
        all_results.extend(results)

    context.register(all_results, new_result_prefix="[Insurance] ")

    # ---- 5. Output leaderboard ----
    leaderboard = context.compare(output_dir=EVAL_DIR)
    print("\n=== Insurance Benchmark Leaderboard ===")
    print(leaderboard.to_markdown())
    print(f"\nResults saved to {EVAL_DIR}")
