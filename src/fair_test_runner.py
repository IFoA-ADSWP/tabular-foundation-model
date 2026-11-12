"""The regressor fair-test runner (#539).

The pre-registration fixes what a run is: four targets, seven Arms, five folds, three model seeds
inside each fold, 10,000 training rows (50,000 for the `S_50k` sensitivity), and 10,000 test rows
shared by every Arm and seed of a fold. This module produces that run and nothing else — the
model sits behind `Backend`, so the matrix is testable without `tabpfn` and a paid launch is a
separate decision.

Writes the v3 capture (#538): `test_index`, `quantiles`, and exposure for freMTPL2freq, each
hashed in the manifest, plus the four record keys the citation gate requires.
"""

from __future__ import annotations

import json
import platform
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol

import numpy as np

import metrics
from provenance import sha256_array, sha256_file, split_section
from regression_data import fold_splits, load_column, load_frame, sample
from run_capture import (
    EXPOSURE,
    PREDICTIONS,
    QUANTILES,
    TEST_INDEX,
    TRUTH,
    build_capture,
    render_capture,
)

QUANTILE_LEVELS = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)


# ---------------------------------------------------------------------------
# What the pre-registration declares
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Arm:
    """One training configuration of the fair test."""

    name: str
    epochs: int
    train_rows: int = 10_000
    transform: str = "none"  # "log1p" for X_log1p


ARMS: dict[str, Arm] = {
    "A_raw": Arm("A_raw", epochs=0),
    "B_ft30": Arm("B_ft30", epochs=30),
    "B_ft10": Arm("B_ft10", epochs=10),
    "B_ft3": Arm("B_ft3", epochs=3),
    "X_log1p": Arm("X_log1p", epochs=30, transform="log1p"),
    "S_50k": Arm("S_50k", epochs=30, train_rows=50_000),
    "D_exposure": Arm("D_exposure", epochs=0),
}


@dataclass(frozen=True)
class Target:
    """One target, its dataset, and the Arms that apply to it."""

    name: str
    dataset: str
    column: str
    drop: tuple[str, ...]
    metric: str
    arms: tuple[str, ...]
    log_features: tuple[str, ...] = ()
    exposure_column: str | None = None


TARGETS: tuple[Target, ...] = (
    Target(
        "claimnb",
        "freMTPL2freq",
        "ClaimNb",
        ("IDpol",),
        "poisson_deviance",
        ("A_raw", "B_ft30", "B_ft10", "B_ft3", "X_log1p", "S_50k"),
        log_features=("Exposure",),
        exposure_column="Exposure",
    ),
    Target(
        "severity",
        "spanish_motor_severity",
        "Cost_claims_year",
        (),
        "rmse",
        ("A_raw", "B_ft30", "B_ft10", "B_ft3", "S_50k"),
    ),
    Target(
        "vehvalue",
        "ausprivauto0405",
        "VehValue",
        ("ClaimOcc", "Exposure"),
        "rmse",
        ("A_raw", "B_ft30", "B_ft10", "B_ft3", "S_50k"),
    ),
    Target(
        "exposure",
        "freMTPL2freq",
        "Exposure",
        ("IDpol",),
        "rmse",
        ("D_exposure",),
        exposure_column="Exposure",
    ),
)


@dataclass(frozen=True)
class RunConfig:
    folds: int = 5
    seeds: tuple[int, ...] = (0, 1, 2)
    test_rows: int = 10_000
    fold_seed: int = 42
    targets: tuple[Target, ...] = TARGETS


@dataclass(frozen=True)
class SlotSpec:
    target: Target
    arm: Arm
    fold: int
    seed: int


def slot_matrix(config: RunConfig) -> list[SlotSpec]:
    """Every Arm × fold × model seed, in a fixed order."""
    slots = []
    for target in config.targets:
        for arm_name in target.arms:
            for fold in range(config.folds):
                for seed in config.seeds:
                    slots.append(SlotSpec(target, ARMS[arm_name], fold, seed))
    return slots


# ---------------------------------------------------------------------------
# The model seam
# ---------------------------------------------------------------------------
class Backend(Protocol):
    """The only surface the runner needs from `tabpfn`."""

    def provenance(self) -> dict:
        """`versions` and `weights`: what ran, and on which bytes."""

    def fit_predict(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_test: np.ndarray,
        *,
        seed: int,
        epochs: int,
    ) -> tuple[np.ndarray, np.ndarray]:
        """One fit: predictions `(n,)` and quantiles `(9, n)` on the test rows."""


# ---------------------------------------------------------------------------
# Writing one slot
# ---------------------------------------------------------------------------
def _transform(values: np.ndarray, arm: Arm) -> np.ndarray:
    return np.log1p(values) if arm.transform == "log1p" else values


def _write_slot(
    slot_dir: Path,
    *,
    spec: SlotSpec,
    truth: np.ndarray,
    predictions: np.ndarray,
    quantiles: np.ndarray,
    test_index: np.ndarray,
    exposure: np.ndarray | None,
    provenance: dict,
    meta_extra: dict,
    reported_scale: str,
    quantile_scale: str,
) -> None:
    slot_dir.mkdir(parents=True, exist_ok=True)
    np.save(slot_dir / PREDICTIONS, np.asarray(predictions, dtype=float))
    np.save(slot_dir / TRUTH, np.asarray(truth, dtype=float))
    np.save(slot_dir / TEST_INDEX, np.asarray(test_index, dtype=np.int64))
    np.save(slot_dir / QUANTILES, np.asarray(quantiles, dtype=float))
    if exposure is not None:
        np.save(slot_dir / EXPOSURE, np.asarray(exposure, dtype=float))

    verdict = getattr(metrics, spec.target.metric)(truth, predictions)
    meta = {
        "arm": spec.arm.name,
        "seed": spec.seed,
        "fold": spec.fold,
        "dataset": spec.target.dataset,
        "target": spec.target.column,
        "transform": spec.arm.transform,
        "reported_scale": reported_scale,
        "quantile_scale": quantile_scale,
        "log_features": list(spec.target.log_features),
        "drop": list(spec.target.drop),
        "test_rows": int(len(truth)),
        "quantile_levels": list(QUANTILE_LEVELS),
        "verdict_metric": spec.target.metric,
        "verdict_metric_value": float(verdict),
        "rmse": float(metrics.rmse(truth, predictions)),
        "predictions_sha256": sha256_array(np.asarray(predictions, dtype=float)),
        **provenance,
        **meta_extra,
    }
    (slot_dir / "meta.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n")


def _split_rule(config: RunConfig) -> str:
    if config.folds == 1:
        return "holdout-80-20"
    return f"KFold(shuffle=True, random_state={config.fold_seed})"


_DATASET_BLOCKS: dict[str, dict] = {}


def _dataset_block(dataset: str) -> dict:
    """The frame's identity: a row position means nothing without the file it addresses."""
    if dataset not in _DATASET_BLOCKS:
        from regression_data import RAW_DIR  # noqa: PLC0415

        path = RAW_DIR / f"{dataset}.csv"
        _DATASET_BLOCKS[dataset] = {
            "name": dataset,
            "path": str(path),
            "sha256": sha256_file(path),
        }
    return _DATASET_BLOCKS[dataset]


def _run_ids(base: str, count: int) -> list[str]:
    """One bare run id per target.

    A capture carries one dataset, and the fair test spans three, so the fair test is three runs.
    Each id stays a bare timestamp: a suffixed directory would be read by the citation check as a
    run id that does not exist.
    """
    moment = datetime.strptime(base, "%Y%m%dT%H%M%SZ")
    if count == 1:
        return [base]
    return [
        (moment + timedelta(seconds=index)).strftime("%Y%m%dT%H%M%SZ")
        for index in range(count)
    ]


def run(
    config: RunConfig,
    backend: Backend,
    out_root: Path,
    *,
    run_id: str | None = None,
    train_rows_cap: int | None = None,
    epochs_cap: int | None = None,
) -> dict[str, Path]:
    """Produce one run per target and its capture; returns {target: run directory}.

    One capture carries one dataset (#362), so the fair test — three datasets plus a diagnostic on
    the first — is three runs of one Launch. The pre-registration proposes three pilot experiments in
    its registry section; they are not declared in `experiments.toml`, so this split is the
    runner's choice and is recorded here.
    """
    base = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_ids = _run_ids(base, len(config.targets))
    provenance: dict | None = None
    produced: dict[str, Path] = {}

    for target, target_run_id in zip(config.targets, run_ids):
        run_dir = Path(out_root) / target_run_id
        if run_dir.exists():
            raise FileExistsError(f"{run_dir} exists; a record is refused rather than replaced")
        X, y = load_frame(
            target.dataset,
            target.column,
            target.drop,
            log_features=target.log_features,
        )
        exposure_all = (
            load_column(target.dataset, target.exposure_column)
            if target.exposure_column is not None
            else None
        )
        splits = fold_splits(len(y), n_folds=config.folds, seed=config.fold_seed)

        for fold, split in enumerate(splits):
            test_index = sample(split.test, config.test_rows, seed=config.fold_seed)
            exposure_test = None if exposure_all is None else exposure_all[test_index]

            for arm_name in target.arms:
                arm = ARMS[arm_name]
                rows = arm.train_rows if train_rows_cap is None else min(
                    arm.train_rows, train_rows_cap
                )
                epochs = (
                    arm.epochs if epochs_cap is None else min(arm.epochs, epochs_cap)
                )
                for seed in config.seeds:
                    train_index = sample(split.train_pool, rows, seed=1_000 * seed + fold)
                    predictions, quantiles = backend.fit_predict(
                        X[train_index],
                        _transform(y[train_index], arm),
                        X[test_index],
                        seed=seed,
                        epochs=epochs,
                    )
                    truth = y[test_index]
                    if arm.transform == "log1p":
                        # Predictions and truth are stored on the count scale, or the count
                        # deviance would be computed on log values and X_log1p could not be
                        # compared with A_raw. Quantiles stay on the scale the Arm trained on and
                        # unclipped, as the amendment fixes them.
                        predictions = np.clip(np.expm1(predictions), 0.0, None)
                        reported_scale = "count"
                        quantile_scale = "log1p"
                    else:
                        reported_scale = "native"
                        quantile_scale = "native"
                    if provenance is None:
                        # After a fit, the checkpoint is on disk; before one, a cold cache would
                        # record a null hash and pass a path-only gate.
                        provenance = backend.provenance()
                    if not (
                        np.all(np.isfinite(predictions))
                        and np.all(np.isfinite(truth))
                        and np.all(np.isfinite(quantiles))
                    ):
                        raise RuntimeError(
                            f"{target.name}/{arm.name} seed {seed} fold {fold}: "
                            "non-finite predictions"
                        )
                    slot_provenance = {
                        **provenance,
                        "provenance": {
                            "dataset": _dataset_block(target.dataset),
                            "split": split_section(
                                n_folds=config.folds,
                                seed=config.fold_seed,
                                rule=_split_rule(config),
                            ),
                        },
                    }
                    _write_slot(
                        run_dir / target.dataset / arm.name / f"seed{seed}_fold{fold}",
                        spec=SlotSpec(target, arm, fold, seed),
                        truth=truth,
                        predictions=predictions,
                        quantiles=quantiles,
                        test_index=test_index,
                        exposure=exposure_test,
                        provenance=slot_provenance,
                        meta_extra={
                            "train_rows": int(len(train_index)),
                            "epochs": epochs,
                            "fold_seed": config.fold_seed,
                            "n_folds": config.folds,
                        },
                        reported_scale=reported_scale,
                        quantile_scale=quantile_scale,
                    )

        (run_dir / "capture.json").write_text(render_capture(build_capture(run_dir)))
        produced[target.name] = run_dir
    return produced


# ---------------------------------------------------------------------------
# The real backend
# ---------------------------------------------------------------------------
def _main_output(model, X_test) -> tuple[np.ndarray, np.ndarray]:
    """The point prediction and the nine quantiles from one forward pass.

    `output_type="main"` returns the predictive mean and the quantiles together. The mean of the
    quantiles is not the predictive mean, so the two are taken from the library rather than derived.
    """
    output = model.predict(
        X_test, output_type="main", quantiles=list(QUANTILE_LEVELS)
    )
    return np.asarray(output["mean"], dtype=float), np.vstack(output["quantiles"])


class TabPFNBackend:
    """Drives the shipped regressor on the pinned v3 line."""

    def __init__(self, device: str = "cuda", n_estimators: int = 8) -> None:
        self.device = device
        self.n_estimators = n_estimators
        self._provenance: dict | None = None

    def provenance(self) -> dict:
        if self._provenance is not None:
            return self._provenance
        import tabpfn  # noqa: PLC0415
        from tabpfn import TabPFNRegressor  # noqa: PLC0415
        from tabpfn.constants import ModelVersion  # noqa: PLC0415

        model = TabPFNRegressor.create_default_for_version(ModelVersion.V3, device="cpu")
        raw_path = getattr(model, "model_path", None)
        path = Path(raw_path) if raw_path else None
        if path is None or not path.is_file():
            raise RuntimeError(
                "the checkpoint is not on disk, so its sha256 cannot be recorded; "
                "refusing a capture that would pass a path-only gate"
            )
        self._provenance = {
            "versions": {"tabpfn": tabpfn.__version__, "python": platform.python_version()},
            "weights": {"path": str(path), "sha256": sha256_file(path)},
        }
        return self._provenance

    def fit_predict(self, X_train, y_train, X_test, *, seed, epochs):
        from tabpfn import TabPFNRegressor  # noqa: PLC0415
        from tabpfn.constants import ModelVersion  # noqa: PLC0415
        from tabpfn.finetuning.finetuned_regressor import (  # noqa: PLC0415
            FinetunedTabPFNRegressor,
        )

        if epochs == 0:
            model = TabPFNRegressor.create_default_for_version(
                ModelVersion.V3,
                device=self.device,
                n_estimators=self.n_estimators,
                random_state=seed,
            )
            model.fit(X_train, y_train)
            return _main_output(model, X_test)

        model = FinetunedTabPFNRegressor(
            device=self.device,
            epochs=epochs,
            random_state=seed,
            validation_split_ratio=0.0,
            early_stopping=False,
            n_estimators_finetune=2,
            n_estimators_validation=2,
            n_estimators_final_inference=self.n_estimators,
            model_version=ModelVersion.V3,
        )
        model.fit(X_train, y_train)
        return _main_output(model, X_test)
