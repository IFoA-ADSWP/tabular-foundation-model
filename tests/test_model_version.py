"""Declared vs resolved model version — the comparison, and the resolver it must not change.

Issue #239. The registry pins a literal; execution resolves env-first. The artifact
carries both and this comparison, which #233 will consume. Two properties are load-
bearing and tested here: an absent declaration is not agreement, and adding the
comparison did not change how (or in what order) the resolver resolves.
"""

from __future__ import annotations

from src.model_version import BASELINE_MODEL_PATH, resolve_model_path, version_mismatch


def test_an_absent_declaration_is_absent_not_agreement():
    # An ad-hoc run declares nothing. "No experiment declared this" and "the declaration
    # matched" are different facts, and collapsing them would make an unverified row look
    # verified (ADR 0001).
    assert version_mismatch(None, "v3_default") is None


def test_a_matching_declaration_agrees():
    assert version_mismatch("v3_default", "v3_default") is False


def test_a_drifted_declaration_is_flagged():
    assert version_mismatch("v3_default", "v3.5_default") is True


def test_the_comparison_is_exact():
    # Not a normalised/prefix comparison: a different label is a different measurement.
    assert version_mismatch("v3_default ", "v3_default") is True
    assert version_mismatch("v3", "v3_default") is True


def test_the_comparison_resolves_nothing(monkeypatch):
    # The environment must not influence the answer: `resolved` is passed in, already
    # resolved by the caller. Only resolve_model_path may read the environment.
    monkeypatch.setenv("TABPFN_MODEL_PATH", "v3.5_default")
    assert version_mismatch("v3_default", "v3_default") is False


def test_the_resolver_is_still_environment_first(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # no .env here, so only the env var can answer
    monkeypatch.setenv("TABPFN_MODEL_PATH", "v3.5_default")
    assert resolve_model_path() == "v3.5_default"


def test_the_resolver_still_falls_back_to_the_baseline(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TABPFN_MODEL_PATH", raising=False)
    monkeypatch.delenv("TABPFN_ENV_FILE", raising=False)
    assert resolve_model_path() == BASELINE_MODEL_PATH
