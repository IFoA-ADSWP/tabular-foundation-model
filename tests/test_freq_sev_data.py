"""The data contracts the frequency/severity pre-registration rests on (#552).

Two files carry claims that the fair test will join or stitch, and both have a trap that produces a
silent, plausible-looking result rather than an error:

1. `freMTPL2sev.csv` is converted from an R `.rda` in which `IDpol` is a **factor of strings**. Read
   naively it joins to `freMTPL2freq.csv` zero times, and a merged frame with no rows looks like
   "no claims" rather than a broken key.
2. The two Spanish views have no key at all. They are row-aligned, and only the 20 shared columns
   prove it; equal row counts prove nothing.

Run:  python -m pytest tests/test_freq_sev_data.py -v
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from freq_sev_data import TARGETS, load_target
from regression_data import group_fold_splits

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


def test_every_french_claim_joins_a_policy():
    """The whole claim table keys to a policy; one orphan would silently drop rows from severity."""
    policies = pd.read_csv(RAW / "freMTPL2freq.csv", usecols=["IDpol"])
    claims = pd.read_csv(RAW / "freMTPL2sev.csv")

    assert list(claims.columns) == ["IDpol", "ClaimAmount"]
    assert len(claims) == 26_444
    assert claims["IDpol"].nunique() == 24_944
    assert claims["IDpol"].dtype.kind in "iu", "IDpol must be numeric, not the .rda's factor of strings"

    missing = set(claims["IDpol"]) - set(policies["IDpol"])
    assert not missing, f"{len(missing)} claims have no policy row"
    assert (claims["ClaimAmount"] > 0).all(), "log(amount) needs a positive amount for every claim"


def test_the_claims_file_matches_its_manifest_hash():
    """The manifest is the only thing that would notice a silently rewritten data file."""
    entry = None
    for line in (RAW / "MANIFEST.sha256").read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        if name.strip() == "./freMTPL2sev.csv":
            entry = digest
            break

    assert entry is not None, "freMTPL2sev.csv is absent from MANIFEST.sha256"
    actual = hashlib.sha256((RAW / "freMTPL2sev.csv").read_bytes()).hexdigest()
    assert actual == entry


def test_the_spanish_frequency_and_severity_views_are_row_aligned():
    """Severity takes its per-claim weight from the frequency view's `N_claims_year`.

    The two prepared files carry no key, so the alignment is the contract. If a future preparation
    run reorders one view, the weight silently belongs to another policy; this is the assertion
    that catches it.
    """
    freq = pd.read_csv(RAW / "spanish_motor_freq.csv")
    severity = pd.read_csv(RAW / "spanish_motor_severity.csv")

    shared = [column for column in freq.columns if column in severity.columns]
    assert len(shared) == 20
    assert set(freq.columns) - set(severity.columns) == {"N_claims_year"}
    assert set(severity.columns) - set(freq.columns) == {"Cost_claims_year"}
    for column in shared:
        assert freq[column].equals(severity[column]), f"{column} is not aligned row for row"

    claiming = freq["N_claims_year"] > 0
    assert int(claiming.sum()) == 5_950
    assert int(freq.loc[claiming, "N_claims_year"].sum()) == 11_167


# ---------------------------------------------------------------------------
# The four targets the fair test loads (#555)
# ---------------------------------------------------------------------------
def _loaded():
    return {spec.name: load_target(spec) for spec in TARGETS}


def test_the_four_targets_load_at_their_pre_registered_sizes():
    loaded = _loaded()

    assert loaded["frequency_french"].rows == 678_013
    assert loaded["frequency_spanish"].rows == 53_502
    assert loaded["severity_french"].rows == 26_444
    assert loaded["severity_spanish"].rows == 5_950
    assert int(loaded["severity_spanish"].weights.sum()) == 11_167
    assert len(np.unique(loaded["severity_french"].groups)) == 24_944


def test_severity_is_loaded_on_the_log_scale():
    """The metric is RMSE of log(amount); a raw-scale target would be dominated by the tail."""
    french = _loaded()["severity_french"]

    assert french.y.max() == pytest.approx(np.log(4_075_400.56), rel=1e-9)
    assert (french.y >= 0).all(), "every amount is at least 1, so its log is non-negative"


def test_sibling_targets_and_the_claim_count_are_not_features():
    """A count as a feature predicts the amount by leaking the frequency, and vice versa."""
    loaded = _loaded()

    assert "ClaimNb" not in loaded["severity_french"].features
    assert "Exposure" not in loaded["severity_french"].features
    assert "Cost_claims_year" not in loaded["severity_spanish"].features
    assert "Policies_in_force" not in loaded["severity_spanish"].features
    assert "Cost_claims_year" not in loaded["frequency_spanish"].features


def test_grouped_folds_never_split_a_policy():
    """The French severity table has 26,444 claims over 24,944 policies."""
    french = _loaded()["severity_french"]

    splits = group_fold_splits(french.groups, n_folds=5, seed=42)

    for split in splits:
        train = set(french.groups[split.train_pool].tolist())
        test = set(french.groups[split.test].tolist())
        assert not (train & test), "a policy's claims are on both sides of a fold"
    assert sum(len(split.test) for split in splits) == french.rows


def test_the_spanish_frequency_file_excludes_its_sibling_and_history_columns():
    """The preparation drops them; a replacement file that added them back must fail here."""
    header = set(pd.read_csv(RAW / "spanish_motor_freq.csv", nrows=0).columns)

    assert not header & {"Cost_claims_year", "N_claims_history", "R_Claims_history"}
