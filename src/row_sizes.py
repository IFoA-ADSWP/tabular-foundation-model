"""A declared row-size point, turned into rows (#264).

Moved here from the size-sweep script, unchanged in behaviour, because the sweep and the
frontier must select the *same* rows for the same declared size. Two slicers would make
one declaration mean two measurements, which is the class of bug `GLOSSARY.md` calls a
bug in the artifact.

The seed is fixed rather than taken from the experiment: this seed selects which rows
represent the table, and a run's split seed must not also move the slice, or changing one
would silently change the other. A declared size that is at least the table's length is
the whole table, which is why `None` and an oversized `n` are the same point.
"""

from __future__ import annotations

import numpy as np

SLICE_SEED = 42


def slice_data(
    X: np.ndarray, y: np.ndarray, n: int | None
) -> tuple[np.ndarray, np.ndarray]:
    """A stratified slice of `n` rows (`None` = the whole table), deterministic at 42."""
    if n is None or len(X) <= n:
        return X, y
    from sklearn.model_selection import train_test_split

    Xsliced, _, ysliced, _ = train_test_split(
        X, y, train_size=n, stratify=y, random_state=SLICE_SEED
    )
    return Xsliced, ysliced
