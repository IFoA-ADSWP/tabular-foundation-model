"""Load a regression target and split it into folds (#539).

One loader for the benchmark fit and the fair test, so the frame a cost estimate timed is the
frame the run scores. Categorical columns are code-encoded once, over the whole column and
independent of the target, which keeps the encoding from leaking anything it should not.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw"


@dataclass(frozen=True)
class FoldSplit:
    """One fold: where its training pool and its test rows live in the frame."""

    train_pool: np.ndarray
    test: np.ndarray


def load_frame(
    dataset: str,
    target: str,
    drop: tuple[str, ...] = (),
    *,
    raw_dir: Path | None = None,
    log_features: tuple[str, ...] = (),
) -> tuple[np.ndarray, np.ndarray]:
    """The target column and its feature matrix, categoricals encoded, in file order.

    File order matters: the capture's `test_index` is a position in this frame, and the frame is
    `data/raw/<dataset>.csv` with the drop list applied and nothing re-sorted.
    """
    path = (raw_dir or RAW_DIR) / f"{dataset}.csv"
    frame = pd.read_csv(path)
    missing = [column for column in (*drop, target) if column not in frame.columns]
    if missing:
        raise KeyError(f"{path} has no columns {missing}")
    y = frame[target].to_numpy(dtype=float)
    X = frame.drop(columns=list(drop) + [target])
    missing_log = [column for column in log_features if column not in X.columns]
    if missing_log:
        raise KeyError(f"{path} has no columns {missing_log} to log-transform")
    for column in log_features:
        X[column] = np.log(np.clip(X[column].to_numpy(dtype=float), 1e-12, None))
    for column in X.columns:
        if not np.issubdtype(X[column].dtype, np.number):
            X[column] = X[column].astype("category").cat.codes
    return X.to_numpy(dtype=float), y


def load_column(dataset: str, column: str, *, raw_dir: Path | None = None) -> np.ndarray:
    """One column of the raw frame, in file order — the exposure the capture retains."""
    path = (raw_dir or RAW_DIR) / f"{dataset}.csv"
    frame = pd.read_csv(path, usecols=[column])
    return frame[column].to_numpy(dtype=float)


def fold_splits(n_rows: int, *, n_folds: int = 5, seed: int = 42) -> list[FoldSplit]:
    """Canonical KFold over positions, in fold order.

    `n_folds=1` is the smoke shape only: one deterministic 80/20 split, because sklearn refuses a
    one-split KFold. The pre-registration always runs five, and this branch says so rather than
    quietly producing a different split under the same name.
    """
    if n_folds == 1:
        order = np.random.default_rng(seed).permutation(n_rows)
        cut = int(n_rows * 0.8)
        return [FoldSplit(train_pool=np.sort(order[:cut]), test=np.sort(order[cut:]))]

    from sklearn.model_selection import KFold  # noqa: PLC0415

    splitter = KFold(n_splits=n_folds, shuffle=True, random_state=seed)
    positions = np.arange(n_rows)
    return [
        FoldSplit(train_pool=np.sort(train), test=np.sort(test))
        for train, test in splitter.split(positions)
    ]


def group_fold_splits(groups: np.ndarray, *, n_folds: int = 5, seed: int = 42) -> list[FoldSplit]:
    """KFold over unique groups, expanded to row positions, in fold order.

    The fair test's severity targets have more than one row per policy (a claim table, a grouped
    Spanish view). A row-level fold would put a policy's claims on both sides and leak. Groups are
    split by the same canonical KFold, so the fold seed and shuffle are the pre-registered ones; the
    rows then follow their group.

    Identical to `fold_splits` when every group is unique, which is the case for the policy-level
    frequency targets.
    """
    groups = np.asarray(groups)
    unique_groups, codes = np.unique(groups, return_inverse=True)
    n_groups = len(unique_groups)
    if n_folds > 1 and n_folds > n_groups:
        raise ValueError(f"cannot split {n_groups} groups into {n_folds} folds")

    order = np.argsort(codes, kind="stable")
    counts = np.bincount(codes, minlength=n_groups)
    starts = np.concatenate([[0], np.cumsum(counts)])
    rows_by_group = [order[starts[index]:starts[index + 1]] for index in range(n_groups)]

    if n_folds == 1:
        permutation = np.random.default_rng(seed).permutation(n_groups)
        cut = int(n_groups * 0.8)
        folds = [(permutation[:cut], permutation[cut:])]
    else:
        from sklearn.model_selection import KFold  # noqa: PLC0415

        splitter = KFold(n_splits=n_folds, shuffle=True, random_state=seed)
        folds = list(splitter.split(np.arange(n_groups)))

    splits: list[FoldSplit] = []
    for train_groups, test_groups in folds:
        train_rows = np.sort(np.concatenate([rows_by_group[index] for index in train_groups]))
        test_rows = np.sort(np.concatenate([rows_by_group[index] for index in test_groups]))
        splits.append(FoldSplit(train_pool=train_rows, test=test_rows))
    return splits


def sample(positions: np.ndarray, size: int, *, seed: int) -> np.ndarray:
    """Up to `size` positions, sampled deterministically and returned sorted.

    Sorting is what makes the stored `test_index` a stable array and two slots' arrays comparable;
    an unsorted sample would make equality depend on the draw order.
    """
    if size >= len(positions):
        return np.asarray(positions)
    chosen = np.random.default_rng(seed).choice(positions, size=size, replace=False)
    return np.sort(chosen)
