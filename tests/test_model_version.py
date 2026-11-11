"""Declared vs resolved model version — the comparison, and the resolver it must not change.

Issue #239. The registry pins a literal; execution resolves env-first. The artifact
carries both and this comparison, which #233 will consume. Two properties are load-
bearing and tested here: an absent declaration is not agreement, and adding the
comparison did not change how (or in what order) the resolver resolves.
"""

from __future__ import annotations

from src.model_version import (
    ANCHOR_CHECKPOINT,
    BASELINE_MODEL_PATH,
    checkpoint_mismatch,
    expected_checkpoint,
    resolve_model_path,
    version_mismatch,
)


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


# --- which weights a launch claims to run (D16, breadth) --------------------------------


def test_the_anchor_checkpoint_is_accepted():
    # The line the replication ran; a breadth cell must share it to be comparable (D15).
    assert checkpoint_mismatch([f"/cache/{ANCHOR_CHECKPOINT}"], ANCHOR_CHECKPOINT) is None


def test_a_different_line_is_refused_and_both_names_are_shown():
    reason = checkpoint_mismatch(
        ["/cache/tabpfn-v3.5-classifier-v3.5_default.ckpt"], ANCHOR_CHECKPOINT
    )
    assert reason is not None
    assert ANCHOR_CHECKPOINT in reason           # what was wanted
    assert "v3.5_default.ckpt" in reason         # what was there -- the difference between
    #                                              "the pin moved" and "nothing was fetched"


def test_an_empty_cache_is_a_refusal_not_a_pass():
    # If an operator asked for the assertion, no weights means nothing was confirmed.
    reason = checkpoint_mismatch([], ANCHOR_CHECKPOINT)
    assert reason is not None
    assert "fetch the weights" in reason


def test_no_request_is_absent_rather_than_a_pass():
    # Nothing asked, nothing checked: the empty expectation returns no mismatch, and the record
    # says so separately via `expected_checkpoint: null`.
    assert checkpoint_mismatch([], "") is None


def test_the_expected_checkpoint_comes_from_the_environment(monkeypatch):
    monkeypatch.setenv("TFM_EXPECT_CHECKPOINT", "some-other.ckpt")
    assert expected_checkpoint() == "some-other.ckpt"
    monkeypatch.delenv("TFM_EXPECT_CHECKPOINT")
    assert expected_checkpoint() == ""
