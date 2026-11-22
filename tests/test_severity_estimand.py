"""The estimand diagnostic's claims, checked against the captures it reads (#672).

The note's argument is that Spanish severity's sign is the weighting's while French has no such lever.
That is three assertions, and each is pinned here so a corrected capture or a changed metric definition
cannot leave the prose standing:

- the same Spanish slots read better weighted and worse unweighted;
- the Spanish gain sits on multi-claim policies and the loss on single-claim ones;
- French harm holds in every seed and every fold at 30 epochs.

These are arithmetic on committed captures, not a re-run; the load is the only slow part, so it is done
once per module.
"""

from __future__ import annotations

from pathlib import Path

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


def _axes(slots):
    return sorted({key[1] for key in slots}), sorted({key[2] for key in slots})


def test_spanish_sign_reverses_with_the_weighting(diag, spanish):
    weighted = diag.by_seed(spanish, weighted=True)
    unweighted = diag.by_seed(spanish, weighted=False)

    mean, low, high, better = diag.contrast(weighted, "B_ft30", "A_raw")
    assert mean < 0 and high < 0, "the registered metric must read better"
    assert better == 16

    mean, low, high, better = diag.contrast(unweighted, "B_ft30", "A_raw")
    assert mean > 0 and low > 0, "the unweighted metric must read worse"
    assert better == 7


def test_spanish_gain_is_on_multi_claim_policies(diag, spanish):
    single = diag.stratum_by_seed(spanish, lambda weight: weight == 1)
    multi = diag.stratum_by_seed(spanish, lambda weight: weight > 1)

    assert single.mean() > 0, "single-claim policies should lose"
    assert multi.mean() < 0, "multi-claim policies should carry the gain"


def test_french_harm_is_uniform(diag, french):
    weighted = diag.by_seed(french, weighted=True)
    unweighted = diag.by_seed(french, weighted=False)

    # The French capture weights every row 1, so the two metrics are the same number.
    assert weighted["B_ft30"].tolist() == unweighted["B_ft30"].tolist()

    mean, low, _high, better = diag.contrast(weighted, "B_ft30", "A_raw")
    assert mean > 0 and low > 0, "30 epochs must be worse than raw"
    assert better == 0, "no seed may be better at 30 epochs"

    seeds, folds = _axes(french)
    for fold in folds:
        values = [
            (diag.score(french[("B_ft30", seed, fold)], weighted=True)
             - diag.score(french[("A_raw", seed, fold)], weighted=True))
            / diag.score(french[("A_raw", seed, fold)], weighted=True)
            for seed in seeds
        ]
        assert sum(values) / len(values) > 0, f"fold {fold} must be worse"
