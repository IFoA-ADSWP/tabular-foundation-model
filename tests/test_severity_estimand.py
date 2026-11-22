"""The estimand diagnostic's claims, checked against the captures it reads (#672).

The note's argument is that Spanish severity's sign is the weighting's while French has no such lever.
That is three assertions, and each is pinned here so a corrected capture or a changed metric definition
cannot leave the prose standing:

- the same Spanish slots read better weighted and worse unweighted;
- the Spanish gain sits on multi-claim policies and the loss on single-claim ones;
- French harm holds in every seed and every fold at 30 epochs, and its dispersion ordering is the one
  the note quotes.

Two more assertions pin numbers the prose leans on: the multi-claim rows' share of the weighted squared
error, and the ordering of the French prediction spreads. The quintile RMSEs and the Spanish spread are
printed by the script but not pinned — they are descriptions of a second slice of the same slots, and a
test that restated them would be asserting a recomputation rather than a seam.

These are arithmetic on committed captures, not a re-run; the load is the only slow part, so it is done
once per module.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
FRENCH = REPO / "results" / "20261121T153848Z"
SPANISH = REPO / "results" / "20261121T232424Z"


@pytest.fixture(scope="module")
def diag(load_script):
    return load_script("severity_estimand", REPO / "scripts" / "analyses" / "severity_estimand.py")


@pytest.fixture(scope="module")
def french(diag):
    return diag.load(FRENCH, "freMTPL2sev")


@pytest.fixture(scope="module")
def spanish(diag):
    return diag.load(SPANISH, "spanish_motor_severity")


def test_spanish_sign_reverses_with_the_weighting(diag, spanish):
    weighted = diag.by_seed(spanish, weighted=True)
    unweighted = diag.by_seed(spanish, weighted=False)

    mean, _low, high, better = diag.contrast(weighted, "B_ft30", "A_raw")
    assert mean < 0 and high < 0, "the registered metric must read better"
    assert better == 16

    mean, low, _high, better = diag.contrast(unweighted, "B_ft30", "A_raw")
    assert mean > 0 and low > 0, "the unweighted metric must read worse"
    assert better == 7


def test_spanish_gain_is_on_multi_claim_policies(diag, spanish):
    single = diag.stratum_by_seed(spanish, lambda weight: weight == 1)
    multi = diag.stratum_by_seed(spanish, lambda weight: weight > 1)

    assert single.mean() > 0, "single-claim policies should lose"
    assert multi.mean() < 0, "multi-claim policies should carry the gain"

    squared = 0.0
    multi_squared = 0.0
    for key in sorted(spanish):
        if key[0] != "A_raw":
            continue
        slot = spanish[key]
        cell = (slot["y_true"] - slot["y_pred"]) ** 2 * slot["weight"]
        squared += float(cell.sum())
        multi_squared += float(cell[slot["weight"] > 1].sum())
    assert multi_squared / squared > 0.85, "multi-claim rows must dominate the weighted metric"


def test_french_harm_is_uniform(diag, french):
    weighted = diag.by_seed(french, weighted=True)
    unweighted = diag.by_seed(french, weighted=False)

    # The French capture weights every row 1, so the two metrics are the same number.
    assert weighted["B_ft30"].tolist() == unweighted["B_ft30"].tolist()

    mean, low, _high, better = diag.contrast(weighted, "B_ft30", "A_raw")
    assert mean > 0 and low > 0, "30 epochs must be worse than raw"
    assert better == 0, "no seed may be better at 30 epochs"

    assert all(value > 0 for value in diag.per_fold_relative(french, "B_ft30", "A_raw", weighted=True))


def test_french_dispersion_ordering_is_the_one_the_note_quotes(diag, french):
    spreads = {
        arm: np.mean([slots["y_pred"].std() for key, slots in french.items() if key[0] == arm])
        for arm in diag.ARMS
    }

    assert spreads["B_ft3"] > 2 * spreads["A_raw"], "3 epochs more than doubles the spread"
    assert spreads["A_raw"] < spreads["B_ft30"] < spreads["B_ft10"] < spreads["B_ft3"]
