"""TabPFN hosted-API model shared by TabArena benchmark scripts.

Previously copy-pasted between run_tabarena_insurance_benchmark.py and
run_tabarena_insurance_imbalance_pilot.py. Requires the tabarena harness venv
(see docs/REPRODUCIBILITY_RUNBOOK.md).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from autogluon.core.models import AbstractModel

if TYPE_CHECKING:
    from tabarena.utils.config_utils import ConfigGenerator


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
    def config_generator(cls) -> "ConfigGenerator":
        from tabarena.utils.config_utils import ConfigGenerator
        return ConfigGenerator(search_space={}, model_cls=cls, manual_configs=[{}])
