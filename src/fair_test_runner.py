"""The regressor fair-test runner (#539, #555, #597).

The pre-registration fixes what a run is: four targets (frequency and severity across a French and
a Spanish portfolio), a set of **methods**, five folds built on policies, and three model seeds
inside each fold. A method is a predictor; an Arm is one training configuration of the TabPFN
method (`GLOSSARY.md`). The actuarial baselines (#597) enter through the method axis, so the same
runner produces the comparison and the fair test — the model sits behind `Backend`, so the matrix
is testable without `tabpfn` and a paid launch is a separate decision.

Writes capture v5 (#597): every slot records `method`, keeps `test_index`, exposure for freMTPL2freq
and the severity weight/cluster pair, and makes `quantiles` optional — a GLM has no honest
predictive distribution to record, and emitting the mean nine times would assert one.
"""

from __future__ import annotations

import json
import platform
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Mapping, Protocol

import numpy as np
import pandas as pd

import metrics
from freq_sev_data import TARGETS as FREQ_SEV_TARGETS
from freq_sev_data import TargetSpec, load_target
from provenance import sha256_array, sha256_file, split_section
from regression_data import RAW_DIR, group_fold_splits, load_column, sample
from run_capture import (
    CLUSTER,
    EXPOSURE,
    PREDICTIONS,
    QUANTILES,
    TEST_INDEX,
    TRUTH,
    WEIGHTS,
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


ARMS: dict[str, Arm] = {
    "A_raw": Arm("A_raw", epochs=0),
    "B_ft30": Arm("B_ft30", epochs=30),
    "B_ft10": Arm("B_ft10", epochs=10),
    "B_ft3": Arm("B_ft3", epochs=3),
}

# The pre-registration gives every target the same four Arms (#552). The old design's
# `X_log1p`, `S_50k` and `D_exposure` are gone with their targets: a ClaimNb-only transform,
# a row cap no severity sample can reach, and a diagnostic the method-level design owned.
TARGET_ARMS: tuple[str, ...] = ("A_raw", "B_ft30", "B_ft10", "B_ft3")

# The pre-registered target set, re-exported so the CLI and the tests name one thing (#552).
TARGETS = FREQ_SEV_TARGETS


@dataclass(frozen=True)
class Method:
    """One predictor under comparison (`GLOSSARY.md`).

    `arms` is empty for a method that has no training configurations: `E_glm` is one model, not a
    ladder, and calling it an Arm is the pilot's naming bug. A method without Arms trains on the
    whole fold pool — the baselines' primary budget — while `A_raw`/`B_ft30` keep their 10,000-row
    context.
    """

    name: str
    arms: tuple[str, ...] = ()

    @property
    def is_tabpfn(self) -> bool:
        return self.name == "tabpfn"


METHODS: dict[str, Method] = {
    "tabpfn": Method("tabpfn", arms=TARGET_ARMS),
    "E_glm": Method("E_glm"),
    "F_catboost": Method("F_catboost"),
    "M_intercept": Method("M_intercept"),
}

DEFAULT_METHODS: tuple[str, ...] = ("tabpfn",)


@dataclass(frozen=True)
class RunConfig:
    folds: int = 5
    seeds: tuple[int, ...] = (0, 1, 2)
    test_rows: int = 10_000
    fold_seed: int = 42
    targets: tuple[TargetSpec, ...] = FREQ_SEV_TARGETS
    # The gate runs `A_raw` alone; the fair test runs every Arm (#552). The ladder belongs to the
    # TabPFN method, and is ignored by the baselines.
    arms: tuple[str, ...] = TARGET_ARMS
    methods: tuple[str, ...] = DEFAULT_METHODS


@dataclass(frozen=True)
class SlotSpec:
    target: TargetSpec
    method: Method
    arm: Arm | None
    fold: int
    seed: int

    @property
    def label(self) -> str:
        """The directory and record label: the Arm for TabPFN, the method for a baseline."""
        return self.arm.name if self.arm is not None else self.method.name


def slot_matrix(config: RunConfig) -> list[SlotSpec]:
    """Every Method × (Arm) × fold × model seed, in a fixed order."""
    slots = []
    for target in config.targets:
        for method_name in config.methods:
            method = METHODS[method_name]
            arms: tuple[Arm | None, ...] = (
                tuple(ARMS[name] for name in config.arms) if method.is_tabpfn else (None,)
            )
            for arm in arms:
                for fold in range(config.folds):
                    for seed in config.seeds:
                        slots.append(SlotSpec(target, method, arm, fold, seed))
    return slots


# ---------------------------------------------------------------------------
# The model seam
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class FitRequest:
    """One fit's data, on both scales a method may need.

    It carries the source frame as well as the encoded arrays because the baselines cannot read
    `X` alone: the GLM needs the raw levels and the exposure column, and CatBoost needs the raw
    strings. `X` stays exactly what TabPFN has always been given, so the two arms are unchanged.
    """

    target: TargetSpec
    X_train: np.ndarray
    X_test: np.ndarray
    y_train: np.ndarray
    frame: pd.DataFrame
    train_index: np.ndarray
    test_index: np.ndarray
    weights_train: np.ndarray
    weights_test: np.ndarray
    exposure_train: np.ndarray | None
    exposure_test: np.ndarray | None
    seed: int
    epochs: int


class Backend(Protocol):
    """The only surface the runner needs from a method."""

    method: str

    def provenance(self) -> dict:
        """`versions` and `weights`: what ran, and on which bytes."""

    def fit_predict(self, request: FitRequest) -> tuple[np.ndarray, np.ndarray | None]:
        """One fit: predictions `(n,)` and quantiles `(9, n)`, or `None` for a method that has none.

        A baseline declines quantiles rather than fabricating them (#597).
        """


# ---------------------------------------------------------------------------
# Writing one slot
# ---------------------------------------------------------------------------
def _metric_value(spec: TargetSpec, truth: np.ndarray, predictions: np.ndarray,
                  weights: np.ndarray) -> float:
    """The target's verdict metric: weighted when the design weights a grouped target."""
    if spec.weight_source is not None:
        return metrics.weighted_rmse(truth, predictions, weights)
    return getattr(metrics, spec.metric)(truth, predictions)


def _write_slot(
    slot_dir: Path,
    *,
    spec: SlotSpec,
    truth: np.ndarray,
    predictions: np.ndarray,
    quantiles: np.ndarray | None,
    test_index: np.ndarray,
    exposure: np.ndarray | None,
    weights: np.ndarray | None,
    clusters: np.ndarray | None,
    provenance: dict,
    meta_extra: dict,
    reported_scale: str,
    quantile_scale: str | None,
) -> None:
    slot_dir.mkdir(parents=True, exist_ok=True)
    np.save(slot_dir / PREDICTIONS, np.asarray(predictions, dtype=float))
    np.save(slot_dir / TRUTH, np.asarray(truth, dtype=float))
    np.save(slot_dir / TEST_INDEX, np.asarray(test_index, dtype=np.int64))
    if quantiles is not None:
        np.save(slot_dir / QUANTILES, np.asarray(quantiles, dtype=float))
    if exposure is not None:
        np.save(slot_dir / EXPOSURE, np.asarray(exposure, dtype=float))
    severity = spec.target.task == "severity"
    if severity:
        np.save(slot_dir / WEIGHTS, np.asarray(weights, dtype=float))
        np.save(slot_dir / CLUSTER, np.asarray(clusters, dtype=np.int64))

    verdict = _metric_value(
        spec.target, truth, predictions, weights if weights is not None else np.ones(len(truth))
    )
    # A weighted estimate is not `rmse`; recording it under that name made rescore disagree with
    # the record on every Spanish severity slot (review, 2026-11-12).
    metric_name = "weighted_rmse" if spec.target.weight_source is not None else spec.target.metric
    unit = (
        "claim"
        if spec.target.name == "severity_french"
        else "claiming_policy"
        if severity
        else "policy"
    )
    meta = {
        "method": spec.method.name,
        # Null for a baseline: it has no training configuration to name, and inventing one is the
        # distinction the glossary forbids (#597).
        "arm": spec.arm.name if spec.arm is not None else None,
        "seed": spec.seed,
        "fold": spec.fold,
        "dataset": spec.target.dataset,
        "target": spec.target.target_column,
        "task": spec.target.task,
        "unit": unit,
        "weighted": spec.target.weight_source is not None,
        "transform": spec.target.target_scale,
        "reported_scale": reported_scale,
        "quantile_scale": quantile_scale,
        "log_features": list(spec.target.log_features),
        "drop": list(spec.target.drop),
        "test_rows": int(len(truth)),
        "quantile_levels": list(QUANTILE_LEVELS) if quantiles is not None else None,
        "verdict_metric": metric_name,
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


def _dataset_block(spec: TargetSpec) -> dict:
    """The frame's identity: a row position means nothing without the file it addresses.

    French severity is a join, so the block names both files and the join key; a row index in the
    claim table cannot be resolved without the policy file (#552).
    """
    if spec.name not in _DATASET_BLOCKS:
        files = []
        for name in spec.files:
            path = RAW_DIR / name
            files.append({"name": name, "path": str(path), "sha256": sha256_file(path)})
        _DATASET_BLOCKS[spec.name] = {
            "name": spec.dataset,
            "path": files[0]["path"],
            "sha256": files[0]["sha256"],
            "files": files,
            **({"join_key": "IDpol"} if len(files) > 1 else {}),
        }
    return _DATASET_BLOCKS[spec.name]


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
    backends: Mapping[str, Backend] | Backend,
    out_root: Path,
    *,
    run_id: str | None = None,
    train_rows_cap: int | None = None,
    train_rows: int | None = None,
    epochs_cap: int | None = None,
) -> dict[str, Path]:
    """Produce one run per target and its capture; returns {target: run directory}.

    One capture carries one dataset (#362), so the four targets are four runs of one Launch. The
    target's rows, groups, weight and cluster come from `freq_sev_data`; the folds are built on
    policies, so a policy's claims never straddle one.

    `backends` is one backend per selected method — a single backend is accepted and shared, which
    is what a TabPFN-only run is. A baseline is a different predictor, so a run that selects two of
    them cannot share one object.
    """
    if not isinstance(backends, Mapping):
        backends = {method: backends for method in config.methods}
    missing = [method for method in config.methods if method not in backends]
    if missing:
        raise ValueError(f"no backend for method(s): {', '.join(missing)}")
    misplaced = [
        name for name in config.methods if getattr(backends[name], "method", name) != name
    ]
    if misplaced:
        raise ValueError(
            f"a backend is wired to the wrong method: {', '.join(misplaced)}; a baseline is a "
            "different predictor, so its backend cannot stand in for TabPFN"
        )

    base = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_ids = _run_ids(base, len(config.targets))
    provenance: dict[str, dict] = {}
    produced: dict[str, Path] = {}

    for target, target_run_id in zip(config.targets, run_ids):
        run_dir = Path(out_root) / target_run_id
        if run_dir.exists():
            raise FileExistsError(f"{run_dir} exists; a record is refused rather than replaced")
        loaded = load_target(target)
        if loaded.frame is None:
            raise RuntimeError(f"{target.name} carries no source frame; a baseline cannot encode")
        splits = group_fold_splits(
            loaded.groups, n_folds=config.folds, seed=config.fold_seed
        )
        exposure_all = (
            load_column("freMTPL2freq", "Exposure")
            if target.name == "frequency_french"
            else None
        )
        severity = target.task == "severity"

        for fold, split in enumerate(splits):
            test_index = (
                sample(split.test, config.test_rows, seed=config.fold_seed)
                if target.task == "frequency"
                else np.asarray(split.test)
            )
            exposure_test = None if exposure_all is None else exposure_all[test_index]
            weights_test = loaded.weights[test_index]
            clusters_test = loaded.clusters[test_index]

            for method_name in config.methods:
                method = METHODS[method_name]
                arms: tuple[Arm | None, ...] = (
                    tuple(ARMS[name] for name in config.arms) if method.is_tabpfn else (None,)
                )
                for arm in arms:
                    # `train_rows` is the row budget for EVERY arm (#572): the fair test's premise
                    # is a matched inference context, so a raised budget must reach the control as
                    # well as the treatment or the comparison stops being like-for-like.
                    # `train_rows_cap` remains the smoke path's ceiling, which lowers but never
                    # raises. A baseline with no Arm trains on the whole fold pool.
                    if train_rows is not None:
                        rows = train_rows
                    elif train_rows_cap is not None:
                        budget = (
                            arm.train_rows if arm is not None else len(split.train_pool)
                        )
                        rows = min(budget, train_rows_cap)
                    elif arm is not None:
                        rows = arm.train_rows
                    else:
                        rows = len(split.train_pool)
                    rows = min(rows, len(split.train_pool))
                    epochs = (
                        None
                        if arm is None
                        else (arm.epochs if epochs_cap is None else min(arm.epochs, epochs_cap))
                    )
                    for seed in config.seeds:
                        train_index = sample(split.train_pool, rows, seed=1_000 * seed + fold)
                        request = FitRequest(
                            target=target,
                            X_train=loaded.X[train_index],
                            X_test=loaded.X[test_index],
                            y_train=loaded.y[train_index],
                            frame=loaded.frame,
                            train_index=train_index,
                            test_index=test_index,
                            weights_train=loaded.weights[train_index],
                            weights_test=weights_test,
                            exposure_train=(
                                None if exposure_all is None else exposure_all[train_index]
                            ),
                            exposure_test=exposure_test,
                            seed=seed,
                            epochs=epochs,
                        )
                        predictions, quantiles = backends[method.name].fit_predict(request)
                        truth = loaded.y[test_index]
                        if method.name not in provenance:
                            # After a fit, the checkpoint is on disk; before one, a cold cache
                            # would record a null hash and pass a path-only gate.
                            provenance[method.name] = backends[method.name].provenance()
                        finite = np.all(np.isfinite(predictions)) and np.all(np.isfinite(truth))
                        if quantiles is not None:
                            finite = finite and bool(np.all(np.isfinite(quantiles)))
                        if not finite:
                            raise RuntimeError(
                                f"{target.name}/{method.name} seed {seed} fold {fold}: "
                                "non-finite predictions"
                            )
                        slot = SlotSpec(target, method, arm, fold, seed)
                        slot_provenance = {
                            **provenance[method.name],
                            "provenance": {
                                "dataset": _dataset_block(target),
                                "split": split_section(
                                    n_folds=config.folds,
                                    seed=config.fold_seed,
                                    rule=_split_rule(config),
                                ),
                            },
                        }
                        _write_slot(
                            run_dir / target.dataset / slot.label / f"seed{seed}_fold{fold}",
                            spec=slot,
                            truth=truth,
                            predictions=predictions,
                            quantiles=quantiles,
                            test_index=test_index,
                            exposure=exposure_test,
                            weights=weights_test,
                            clusters=clusters_test,
                            provenance=slot_provenance,
                            meta_extra={
                                "train_rows": int(len(train_index)),
                                "epochs": epochs,
                                "fold_seed": config.fold_seed,
                                "n_folds": config.folds,
                                "features": list(loaded.features),
                            },
                            reported_scale="log" if severity else "native",
                            quantile_scale=(
                                None
                                if quantiles is None
                                else ("log" if severity else "native")
                            ),
                        )

        (run_dir / "capture.json").write_text(render_capture(build_capture(run_dir)))
        produced[target.name] = run_dir
    return produced


GATE_MDE_CONSTANT = 2.8016


def gate_summary(
    runs: dict[str, Path], *, control: str = "A_raw", treatment: str = "B_ft30"
) -> dict[str, dict]:
    """Per-target fold-level SD of the paired improvement, and the 80%-power MDE (#552).

    The gate must predict the statistic the fair test reports: for each fold, average
    `r_{t,f,s} = (M_control - M_treatment) / M_control` over the model seeds, then take the
    fold-level SD. Two earlier versions are superseded: one used `SD_fold(M_A_raw)` (which
    includes fold difficulty), the next averaged the metric across seeds before taking the ratio
    (a ratio of means, not the registered mean of ratios).
    """
    summary: dict[str, dict] = {}
    for target, run_dir in runs.items():

        def by_seed(arm: str) -> dict[tuple[int, int], float]:
            metas = sorted(Path(run_dir).glob(f"*/{arm}/seed*_fold*/meta.json"))
            values: dict[tuple[int, int], float] = {}
            for path in metas:
                record = json.loads(path.read_text())
                values[(int(record["fold"]), int(record["seed"]))] = float(
                    record["verdict_metric_value"]
                )
            return values

        raw = by_seed(control)
        fine = by_seed(treatment)
        paired = sorted(set(raw) & set(fine))
        if not paired:
            raise ValueError(f"{run_dir} has no fold with both {control} and {treatment}")
        by_fold: dict[int, list[float]] = {}
        for fold, seed in paired:
            by_fold.setdefault(fold, []).append(
                (raw[(fold, seed)] - fine[(fold, seed)]) / raw[(fold, seed)]
            )
        folds = sorted(by_fold)
        if len(folds) < 2:
            raise ValueError(
                f"{run_dir} has fewer than two folds with both {control} and {treatment}"
            )
        improvements = [float(np.mean(by_fold[fold])) for fold in folds]
        sd = float(np.std(improvements, ddof=1))
        summary[target] = {
            "folds": len(folds),
            "seeds_per_fold": int(len(paired) / len(folds)),
            "mean_control": float(np.mean([raw[key] for key in paired])),
            "mean_treatment": float(np.mean([fine[key] for key in paired])),
            "mean_improvement": float(np.mean(improvements)),
            "sd_r": sd,
            "mde": GATE_MDE_CONSTANT * sd / np.sqrt(len(folds)),
            "mde_units": "relative",
        }
    return summary


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

    method = "tabpfn"

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

    def fit_predict(self, request: FitRequest):
        from tabpfn import TabPFNRegressor  # noqa: PLC0415
        from tabpfn.constants import ModelVersion  # noqa: PLC0415
        from tabpfn.finetuning.finetuned_regressor import (  # noqa: PLC0415
            FinetunedTabPFNRegressor,
        )

        X_train, y_train, X_test = request.X_train, request.y_train, request.X_test
        seed, epochs = request.seed, request.epochs or 0

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
