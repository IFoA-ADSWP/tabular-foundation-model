"""The four frequency/severity targets, loaded for the fair test (#555).

The pre-registration (#552) fixes two actuarial tasks across two portfolios. This module is the
data half of that: one loader per target, returning features, the target on the scale the model is
trained on, the policy groups that folds must respect, and the claim weight and cluster id that
grouped severity needs.

Three traps are handled here, not in the runner:

1. **French severity is two files.** The claim rows are the unit; policy features join on `IDpol`.
   The claim file's `IDpol` is numeric in the committed CSV (the conversion from the R factor is
   recorded in `data/README.md`), and a claim whose policy is absent would silently vanish.
2. **The Spanish views are row-aligned, not keyed.** The severity view carries the cost but not the
   claim count, so the weight comes from the frequency view by position. The alignment is asserted
   in `tests/test_freq_sev_data.py`; this loader asserts it again before using it.
3. **Sibling targets are never features.** For French severity, `ClaimNb` is dropped; for Spanish
   frequency, the severity view is not joined at all; for Spanish severity, `Cost_claims_year` and
   `Policies_in_force` are dropped. A count as a feature would predict the amount by leaking the
   frequency.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from regression_data import RAW_DIR


@dataclass(frozen=True)
class TargetSpec:
    """One pre-registered target and the treatment it was registered with."""

    name: str
    task: str  # "frequency" | "severity"
    portfolio: str  # "french" | "spanish"
    files: tuple[str, ...]
    target_column: str
    drop: tuple[str, ...]
    metric: str
    log_features: tuple[str, ...] = ()
    target_scale: str = "native"  # "log" for severity
    weight_source: str | None = None  # "spain_claim_count" | None

    @property
    def dataset(self) -> str:
        """The dataset directory name: the primary file's stem, one per target."""
        return Path(self.files[0]).stem


@dataclass
class LoadedTarget:
    """A target's frame, split groups, and the arrays the capture must retain."""

    spec: TargetSpec
    X: np.ndarray
    y: np.ndarray
    groups: np.ndarray
    weights: np.ndarray
    clusters: np.ndarray
    files: tuple[Path, ...]
    features: tuple[str, ...] = ()

    @property
    def rows(self) -> int:
        return len(self.y)


TARGETS: tuple[TargetSpec, ...] = (
    TargetSpec(
        name="frequency_french",
        task="frequency",
        portfolio="french",
        files=("freMTPL2freq.csv",),
        target_column="ClaimNb",
        drop=("IDpol",),
        metric="poisson_deviance",
        log_features=("Exposure",),
    ),
    TargetSpec(
        name="frequency_spanish",
        task="frequency",
        portfolio="spanish",
        files=("spanish_motor_freq.csv",),
        target_column="N_claims_year",
        drop=(),
        metric="poisson_deviance",
    ),
    TargetSpec(
        name="severity_french",
        task="severity",
        portfolio="french",
        files=("freMTPL2sev.csv", "freMTPL2freq.csv"),
        target_column="ClaimAmount",
        drop=("IDpol", "ClaimNb", "Exposure"),
        metric="rmse",
        target_scale="log",
    ),
    TargetSpec(
        name="severity_spanish",
        task="severity",
        portfolio="spanish",
        files=("spanish_motor_severity.csv", "spanish_motor_freq.csv"),
        target_column="Cost_claims_year",
        drop=("Cost_claims_year", "Policies_in_force"),
        metric="rmse",
        target_scale="log",
        weight_source="spain_claim_count",
    ),
)


def _features(frame: pd.DataFrame, *, drop: tuple[str, ...], target: str,
              log_features: tuple[str, ...], source: str) -> tuple[np.ndarray, tuple[str, ...]]:
    """The feature matrix, categoricals code-encoded and target-blind.

    Encoding is over the whole column and independent of the target, matching `regression_data`,
    so the fold split cannot leak through the codes.
    """
    missing = [column for column in (*drop, target, *log_features) if column not in frame.columns]
    if missing:
        raise KeyError(f"{source} has no columns {missing}")
    features = frame.drop(columns=[*drop, target])
    for column in log_features:
        features[column] = np.log(np.clip(features[column].to_numpy(dtype=float), 1e-12, None))
    for column in features.columns:
        if not np.issubdtype(features[column].dtype, np.number):
            features[column] = features[column].astype("category").cat.codes
    return features.to_numpy(dtype=float), tuple(features.columns)


def _aligned_spanish(raw_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The two Spanish views, with the row alignment asserted before the count is used as a weight."""
    frequency = pd.read_csv(raw_dir / "spanish_motor_freq.csv")
    severity = pd.read_csv(raw_dir / "spanish_motor_severity.csv")
    shared = [column for column in frequency.columns if column in severity.columns]
    unequal = [column for column in shared if not frequency[column].equals(severity[column])]
    if unequal or len(frequency) != len(severity):
        raise ValueError(
            "the Spanish frequency and severity views are not row-aligned: "
            f"{unequal or 'row counts differ'}"
        )
    return frequency, severity


def load_target(spec: TargetSpec, *, raw_dir: Path | None = None) -> LoadedTarget:
    """Load one target, in file order, with its groups, weights and cluster ids."""
    root = raw_dir or RAW_DIR

    if spec.name == "severity_french":
        claims = pd.read_csv(root / "freMTPL2sev.csv")
        policies = pd.read_csv(root / "freMTPL2freq.csv")
        frame = claims.merge(policies, on="IDpol", how="left", validate="many_to_one",
                             indicator=True)
        if (frame["_merge"] != "both").any():
            raise ValueError("a French claim has no policy row")
        frame = frame.drop(columns=["_merge"])
        X, features = _features(frame, drop=spec.drop, target=spec.target_column, log_features=(),
                                source="freMTPL2sev+freMTPL2freq")
        y = np.log(frame[spec.target_column].to_numpy(dtype=float))
        if not np.all(np.isfinite(y)):
            raise ValueError("a French claim amount is not positive, so log(amount) is undefined")
        groups = frame["IDpol"].to_numpy(dtype=np.int64)
        weights = np.ones(len(frame), dtype=float)
        return LoadedTarget(spec, X, y, groups, weights, groups.copy(),
                            tuple(root / name for name in spec.files), features)

    if spec.name == "severity_spanish":
        frequency, severity = _aligned_spanish(root)
        mask = frequency["N_claims_year"].to_numpy() > 0
        frame = severity.loc[mask].reset_index(drop=True)
        counts = frequency.loc[mask, "N_claims_year"].to_numpy(dtype=float)
        X, features = _features(frame, drop=spec.drop, target=spec.target_column, log_features=(),
                                source="spanish_motor_severity")
        y = np.log(frame[spec.target_column].to_numpy(dtype=float) / counts)
        if not np.all(np.isfinite(y)):
            raise ValueError("a claiming policy has a non-positive cost, so log(Cost/N) is undefined")
        groups = np.arange(len(frame), dtype=np.int64)
        return LoadedTarget(spec, X, y, groups, counts, groups.copy(),
                            tuple(root / name for name in spec.files), features)

    path = root / spec.files[0]
    frame = pd.read_csv(path)
    X, features = _features(frame, drop=spec.drop, target=spec.target_column,
                            log_features=spec.log_features, source=str(path))
    y = frame[spec.target_column].to_numpy(dtype=float)
    groups = (
        frame["IDpol"].to_numpy(dtype=np.int64)
        if "IDpol" in frame.columns
        else np.arange(len(frame), dtype=np.int64)
    )
    weights = np.ones(len(frame), dtype=float)
    return LoadedTarget(spec, X, y, groups, weights, groups.copy(), (path,), features)
