"""The shared loader and fold split (#539).

The fold construction is a pre-registered constant (`KFold(5, shuffle=True, random_state=42)`),
so it gets its own test: the runner's own tests use a one-fold smoke shape, which is a different
branch and would let a change to the real split pass unnoticed.
"""

from __future__ import annotations


import numpy as np
import pytest

from regression_data import fold_splits, group_fold_splits, load_frame, sample


def test_the_canonical_split_is_five_folds_seeded_42():
    # Pinned by hand against sklearn's KFold(5, shuffle=True, random_state=42) over 20 rows, so a
    # change to the seed or to shuffle fails here rather than only "differing from seed 7".
    pinned = [
        [0, 1, 15, 17],
        [3, 5, 8, 11],
        [2, 13, 16, 18],
        [4, 9, 12, 19],
        [6, 7, 10, 14],
    ]
    assert [split.test.tolist() for split in fold_splits(20, n_folds=5, seed=42)] == pinned

    splits = fold_splits(1_000, n_folds=5, seed=42)

    assert len(splits) == 5
    again = fold_splits(1_000, n_folds=5, seed=42)
    assert all(
        np.array_equal(a.test, b.test) and np.array_equal(a.train_pool, b.train_pool)
        for a, b in zip(splits, again)
    )
    different = fold_splits(1_000, n_folds=5, seed=7)
    assert not np.array_equal(splits[0].test, different[0].test)


def test_the_folds_partition_the_rows_and_do_not_overlap():
    splits = fold_splits(1_000, n_folds=5, seed=42)

    tests = np.concatenate([split.test for split in splits])
    assert sorted(tests.tolist()) == list(range(1_000))
    for split in splits:
        assert set(split.test.tolist()).isdisjoint(split.train_pool.tolist())


def test_one_fold_is_the_smoke_shape_not_a_kfold():
    split = fold_splits(100, n_folds=1, seed=42)[0]

    assert len(split.train_pool) == 80
    assert len(split.test) == 20


def test_sampling_is_deterministic_and_sorted():
    positions = np.arange(100)

    first = sample(positions, 10, seed=3)
    assert np.array_equal(first, sample(positions, 10, seed=3))
    assert first.tolist() == sorted(first.tolist())
    assert not np.array_equal(first, sample(positions, 10, seed=4))


def test_sampling_more_than_the_pool_returns_the_pool():
    positions = np.arange(5)

    assert np.array_equal(sample(positions, 10, seed=1), positions)


def test_the_loader_log_transforms_only_the_named_column():
    X_log, y = load_frame(
        "freMTPL2freq", "ClaimNb", ("IDpol",), log_features=("Exposure",)
    )
    X_raw, _ = load_frame("freMTPL2freq", "ClaimNb", ("IDpol",))

    assert X_log.shape == X_raw.shape
    assert y.shape == (X_log.shape[0],)
    changed = np.where(~np.isclose(X_log, X_raw).all(axis=0))[0]
    assert len(changed) == 1, "exactly one column is log-transformed"
    column = changed[0]
    assert X_log[:, column] == pytest.approx(
        np.log(np.clip(X_raw[:, column], 1e-12, None))
    )


# ---------------------------------------------------------------------------
# Grouped folds (#555)
# ---------------------------------------------------------------------------
def test_grouped_folds_keep_a_group_on_one_side():
    """A policy's claims must never straddle a fold, or the test sees its own training rows."""
    groups = np.repeat(np.arange(10), 3)

    splits = group_fold_splits(groups, n_folds=5, seed=42)

    assert len(splits) == 5
    seen_test = 0
    for split in splits:
        train_groups = set(groups[split.train_pool].tolist())
        test_groups = set(groups[split.test].tolist())
        assert not (train_groups & test_groups), "a group is on both sides of a fold"
        assert train_groups | test_groups == set(range(10))
        seen_test += len(split.test)
    assert seen_test == len(groups), "every row is tested exactly once"


def test_grouped_folds_are_ordinary_folds_when_every_group_is_unique():
    """The frequency targets have one row per policy, so the grouped split must not differ."""
    ordinary = fold_splits(100, n_folds=5, seed=42)
    grouped = group_fold_splits(np.arange(100), n_folds=5, seed=42)

    for left, right in zip(ordinary, grouped):
        assert np.array_equal(left.train_pool, right.train_pool)
        assert np.array_equal(left.test, right.test)
