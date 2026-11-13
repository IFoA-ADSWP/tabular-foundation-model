"""The Spanish lapse cell is leak-safe and its seed rule agrees with the verdict tool (#444).

Seam: the matrix `load_dataset` returns, the fingerprint the record carries, and the constant the
pre-registration states. The expected feature width is computed here from the committed CSV, not
from the loader, so a change that keeps the columns would fail rather than reproduce itself.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import verdict  # noqa: E402

SCRIPT = REPO / "scripts" / "run_pilot.py"
SPANISH = REPO / "data" / "raw" / "spanish_motor_lapse.csv"
EUDIRECT = REPO / "data" / "raw" / "eudirectlapse.csv"
PREREG = REPO / "docs" / "experiments" / "pilot2-phase2" / "FINETUNING_PREREGISTRATION_SPANISH_2026-11.md"
REGISTRY = REPO / "scripts" / "eval" / "insurance_benchmark_v1" / "experiments.toml"

LEAK_COLUMNS = ("N_claims_year", "Cost_claims_year")


def _load():
    spec = importlib.util.spec_from_file_location("run_pilot_for_spanish_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mod = _load()


def _encoded_width(path: Path, target: str, drop: tuple[str, ...] = ()) -> int:
    """The feature width after one-hot encoding, computed independently of the loader."""
    frame = pd.read_csv(path)
    return pd.get_dummies(
        frame.drop(columns=[target, *drop]), drop_first=False
    ).shape[1]


def test_the_spanish_matrix_excludes_the_post_outcome_columns():
    features, target, _info = mod.load_dataset("spanish_motor_lapse", "LapseB")

    assert features.shape[1] == _encoded_width(SPANISH, "LapseB", LEAK_COLUMNS)
    assert features.shape[1] < _encoded_width(SPANISH, "LapseB")
    assert len(target) == len(pd.read_csv(SPANISH))


def test_a_dataset_without_a_declared_drop_keeps_every_column():
    features, _target, _info = mod.load_dataset("eudirectlapse", "lapse")

    assert features.shape[1] == _encoded_width(EUDIRECT, "lapse")


def test_the_fingerprint_records_the_columns_the_loader_applies():
    fingerprint = mod.dataset_fingerprint("spanish_motor_lapse")

    assert fingerprint["drop"] == list(LEAK_COLUMNS)
    assert mod.declared_drop("spanish_motor_lapse") == LEAK_COLUMNS


def test_the_registry_entry_and_the_runner_name_the_same_table():
    """The pilot's own table and the registry's view must not drift apart."""
    import tomllib

    with REGISTRY.open("rb") as handle:
        entry = tomllib.load(handle)["pilot_datasets"]["spanish_motor_lapse"]
    declared = mod.DATASETS["spanish_motor_lapse"]

    assert entry == {"file": declared["file"], "target": declared["target"]}


def test_the_preregistered_seed_rule_matches_the_verdict_tool():
    """0.000714 is δ / (Z_ALPHA + Z_POWER); if either constant moves, the document must move."""
    text = PREREG.read_text(encoding="utf-8")
    match = re.search(r"k = ceil\(\(sd / (\d\.\d{6})\)²\)", text)
    assert match, "the pre-registration does not state the seed rule in the expected shape"

    expected = 0.002 / (verdict.Z_ALPHA + verdict.Z_POWER)
    assert float(match.group(1)) == pytest.approx(expected, abs=5e-7)


def test_the_preregistered_reference_seed_count_reproduces_through_the_tool():
    text = PREREG.read_text(encoding="utf-8")

    assert "the anchor's realised SD 0.0081 gives 129 seeds" in text
    assert verdict.resolution(0.0081, 0.002)["seeds_needed"] == 129
