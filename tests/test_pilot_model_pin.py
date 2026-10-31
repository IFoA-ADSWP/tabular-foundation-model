"""The pilot pins the model version it records (#285).

The record stated the resolver's label while `TabPFNClassifier` was constructed with no
`model_path`, so the version was a declaration about what should load, not evidence of what did.

The library is stubbed here: the assertion is about the arguments the pilot hands it, and loading
real weights to observe them would make this test slow and dependent on a download.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_pilot.py"
sys.path.insert(0, str(REPO_ROOT / "src"))


@pytest.fixture(scope="module")
def rp():
    spec = importlib.util.spec_from_file_location("run_pilot_model_pin", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["run_pilot_model_pin"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(autouse=True)
def _fresh_pin(rp):
    """The pin is cached per process, so each test must start from a cold cache."""
    rp.pinned_model_path.cache_clear()
    yield
    rp.pinned_model_path.cache_clear()


@pytest.fixture
def capture(monkeypatch):
    """Replace the two constructors with recorders and hand back what they were given."""
    seen = []

    def _probs(self, X):
        return np.column_stack([np.full(len(X), 0.5), np.full(len(X), 0.5)])

    class RecordingClassifier:
        def __init__(self, **kwargs):
            seen.append(("classifier", kwargs))

        def fit(self, X, y):
            return self

        predict_proba = _probs

    class RecordingFinetuned:
        def __init__(self, **kwargs):
            seen.append(("finetuned", kwargs))

        def fit(self, X, y):
            return self

        predict_proba = _probs

    pkg = types.ModuleType("tabpfn")
    pkg.TabPFNClassifier = RecordingClassifier
    ft = types.ModuleType("tabpfn.finetuning")
    ft_mod = types.ModuleType("tabpfn.finetuning.finetuned_classifier")
    ft_mod.FinetunedTabPFNClassifier = RecordingFinetuned
    pkg.finetuning = ft
    ft.finetuned_classifier = ft_mod
    monkeypatch.setitem(sys.modules, "tabpfn", pkg)
    monkeypatch.setitem(sys.modules, "tabpfn.finetuning", ft)
    monkeypatch.setitem(sys.modules, "tabpfn.finetuning.finetuned_classifier", ft_mod)
    return seen


def _data():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(20, 3))
    y = (rng.random(20) < 0.5).astype(int)
    return X, X, y, y


def test_no_pin_is_passed_when_nobody_set_one(rp, capture, monkeypatch, tmp_path):
    """A label is not a filename. Unset means the library chooses, and nothing is passed (#285)."""
    monkeypatch.delenv("TABPFN_MODEL_PATH", raising=False)
    monkeypatch.chdir(tmp_path)  # no .env here, so the environment is genuinely unset
    X, Xte, y, yte = _data()
    rp.run_arm_a_raw(X, Xte, y, yte, {"n_estimators": 2, "fit_mode": "fit_preprocessors"})

    kind, kwargs = capture[0]
    assert kind == "classifier"
    assert "model_path" not in kwargs, kwargs


def test_an_explicit_pin_is_passed_through(rp, capture, monkeypatch):
    """When an operator names a model path, it reaches the constructor unchanged."""
    monkeypatch.setenv("TABPFN_MODEL_PATH", "v3.5_default")
    X, Xte, y, yte = _data()
    rp.run_arm_a_raw(X, Xte, y, yte, {"n_estimators": 2, "fit_mode": "fit_preprocessors"})

    assert capture[0][1]["model_path"] == "v3.5_default"


def test_arm_b_passes_an_explicit_pin_through_extra_classifier_kwargs(rp, capture, monkeypatch):
    """The fine-tuner has no model_path of its own; it forwards classifier kwargs."""
    monkeypatch.setenv("TABPFN_MODEL_PATH", "v3.5_default")
    X, Xte, y, yte = _data()
    rp.run_arm_b_in_domain(
        X,
        Xte,
        y,
        yte,
        {"epochs": 1, "learning_rate": 1e-5, "n_estimators": 2, "early_stopping": False},
    )

    kind, kwargs = capture[0]
    assert kind == "finetuned"
    assert kwargs["extra_classifier_kwargs"]["model_path"] == "v3.5_default", kwargs


def test_the_record_says_auto_when_nothing_was_pinned(rp, monkeypatch, tmp_path):
    """The smoke's failure, recorded honestly: no operator pin means the library chose."""
    monkeypatch.delenv("TABPFN_MODEL_PATH", raising=False)
    monkeypatch.chdir(tmp_path)
    rp.pinned_model_path.cache_clear()

    block = rp._model_provenance()
    assert block["version"] == "auto"
    assert block["version_source"] == "auto"


def test_the_record_states_an_explicit_pin(rp, monkeypatch):
    monkeypatch.setenv("TABPFN_MODEL_PATH", "v9_test_only")
    rp.pinned_model_path.cache_clear()

    block = rp._model_provenance()
    assert block["version"] == "v9_test_only"
    assert block["version_source"] == "pinned"


def test_the_pin_is_resolved_once_per_process(rp, monkeypatch):
    """One resolution: a mid-run environment change must not let record and estimators diverge."""
    monkeypatch.setenv("TABPFN_MODEL_PATH", "v3_default")
    rp.pinned_model_path.cache_clear()
    first = rp.pinned_model_path()

    monkeypatch.setenv("TABPFN_MODEL_PATH", "v3.5_default")
    assert rp.pinned_model_path() == first, "the pin was re-read mid-run"
    rp.pinned_model_path.cache_clear()


def test_arm_b_passes_nothing_when_nobody_pinned(rp, capture, monkeypatch, tmp_path):
    """The fine-tuned arm must not forward an empty or None model_path either."""
    monkeypatch.delenv("TABPFN_MODEL_PATH", raising=False)
    monkeypatch.chdir(tmp_path)
    X, Xte, y, yte = _data()
    rp.run_arm_b_in_domain(
        X, Xte, y, yte,
        {"epochs": 1, "learning_rate": 1e-5, "n_estimators": 2, "early_stopping": False},
    )
    kind, kwargs = capture[0]
    assert kind == "finetuned"
    assert "extra_classifier_kwargs" not in kwargs, kwargs
