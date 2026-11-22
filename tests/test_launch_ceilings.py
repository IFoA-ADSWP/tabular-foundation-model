"""The paid-run path measures its own ceilings (#701, #433).

Measured on 2026-11-21: `--poll-minutes 210` expired after 142 minutes because the loop counted
polls, the fit count omitted folds (400 fits, not 80), a capture of 182 chunks needed ~2 hours for
one pass, a `git clone` hung for 28 minutes, and the launch's own checkout vanished for ten minutes
while every poll failed silently. Each has a bound here, and each test fails if the bound is
removed.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

from tests.test_pilot2_seed_passthrough import _launch

GH = Path(__file__).resolve().parents[1] / "scripts" / "gpu_helpers"
PRIMARY = ("--fairtest", "primary")


def _fast(tmp_path, **env):
    """A primary launch that cannot take minutes of wall clock: no poll sleep, short bounds."""
    base = {
        "TFM_POLL_SECONDS": "0",
        "TFM_POLL_DEADLINE_SECS": "2",
        "STALL_SECONDS": "2",
        "BOOT_SECONDS": "2",
    }
    base.update(env)
    return base


def test_the_ceiling_is_a_duration_not_a_poll_count(tmp_path):
    """`--poll-minutes 240` used to mean 720 iterations (~2.7 h). The override is seconds."""
    started = time.monotonic()
    _, result = _launch(
        tmp_path,
        *PRIMARY,
        "--poll-minutes", "240",
        extra_env=_fast(tmp_path, MOCK_CLONE_HANG="1", BOOT_SECONDS="0", STALL_SECONDS="0",
                        TFM_POLL_DEADLINE_SECS="2"),
    )
    elapsed = time.monotonic() - started
    combined = result.stdout + result.stderr

    assert result.returncode == 1, combined
    assert "did not report BOOTSTRAP FINISHED" in combined, combined
    assert elapsed < 60, f"a 2-second ceiling took {elapsed:.0f}s of wall clock"


def test_the_spend_gate_counts_folds_and_refuses_a_short_ceiling(tmp_path):
    """The registered frame is 5 folds x 20 seeds x 4 arms = 400 fits, not arms x seeds = 80."""
    seeds = ",".join(str(seed) for seed in range(1001, 1021))
    _, result = _launch(
        tmp_path,
        *PRIMARY,
        "--poll-minutes", "60",
        extra_env={
            "TFM_FAIRTEST_TARGETS": "severity_french",
            "TFM_FAIRTEST_ARMS": "A_raw,B_ft3,B_ft10,B_ft30",
            "TFM_FAIRTEST_SEEDS": seeds,
            "TFM_TRAIN_ROWS": "10000",
        },
    )
    combined = result.stdout + result.stderr

    assert result.returncode == 2, combined
    assert "= 400 fits" in combined, combined
    # 400 fits at 45 s is 300 min; 200 expected chunks at 20 s x 2 copies x 2 passes is 267 min;
    # plus 15 of cold start.
    assert "ceiling 582 min" in combined, combined
    assert "below the 582 min" in combined, combined


def test_a_box_whose_log_stops_advancing_is_released(tmp_path):
    """#433: the log has not advanced after its first marker; release rather than bill on."""
    state, result = _launch(
        tmp_path,
        *PRIMARY,
        "--poll-minutes", "240",
        extra_env=_fast(tmp_path, MOCK_STALL="1", BOOT_SECONDS="0", TFM_POLL_DEADLINE_SECS="10"),
    )
    combined = result.stdout + result.stderr

    assert result.returncode == 1, combined
    assert "has written nothing" in combined, combined
    assert "RELEASING the instance" in combined, combined
    assert (state / "destroyed.txt").exists(), "a stalled box must not be kept"


def test_a_healthy_fit_phase_is_not_a_stall(tmp_path):
    """The runner prints NOTHING while it fits -- 14.7 min per target in the gate's own frame.

    A log-only watchdog released every healthy box minutes into its first target. A busy GPU is
    progress, so the same silent window with the GPU working must not abort.
    """
    state, result = _launch(
        tmp_path,
        *PRIMARY,
        "--poll-minutes", "240",
        extra_env=_fast(tmp_path, MOCK_STALL="1", MOCK_GPU_UTIL="90", BOOT_SECONDS="0",
                        TFM_POLL_DEADLINE_SECS="10"),
    )
    combined = result.stdout + result.stderr

    assert "has written nothing" not in combined, combined
    assert "RELEASING the instance" not in combined, combined


def test_a_hung_bootstrap_is_released_before_the_ceiling(tmp_path):
    """The measured failure: `git clone` hung 28 minutes with no marker and no new log line."""
    state, result = _launch(
        tmp_path,
        *PRIMARY,
        "--poll-minutes", "240",
        extra_env=_fast(tmp_path, MOCK_CLONE_HANG="1", STALL_SECONDS="0", TFM_POLL_DEADLINE_SECS="10"),
    )
    combined = result.stdout + result.stderr

    assert result.returncode == 1, combined
    assert "no bootstrap marker within" in combined, combined
    assert (state / "destroyed.txt").exists(), combined


def test_a_launch_whose_checkout_vanishes_refuses_instead_of_polling_on(tmp_path):
    """The worktree was pruned mid-run and merges failed silently for ten minutes (#701)."""
    helper = tmp_path / "repo" / "scripts" / "gpu_helpers" / "collect_chunks.py"
    state, result = _launch(
        tmp_path,
        *PRIMARY,
        "--poll-minutes", "240",
        extra_env=_fast(tmp_path, MOCK_DELETE_ON_LOG=str(helper), MOCK_STALL="1",
                        STALL_SECONDS="0", BOOT_SECONDS="0", TFM_POLL_DEADLINE_SECS="10"),
    )
    combined = result.stdout + result.stderr

    assert result.returncode == 1, combined
    assert "checkout" in combined and "is gone" in combined, combined
    assert (state / "destroyed.txt").exists(), combined


def test_transfer_minutes_follows_the_pacing_not_the_bandwidth():
    """182 chunks at 20 s, two copies: the measured ~2 h for the French severity capture."""
    sys.path.insert(0, str(GH))
    from transfer_minutes import minutes_to_complete

    # One pass is the measured ~2 h; a launch waits for both passes and the box reports
    # BOOTSTRAP FINISHED only after the last one.
    assert minutes_to_complete(182, 20, 2, 1) == 122
    assert minutes_to_complete(182, 20, 2, 2) == 243
    assert minutes_to_complete(1, 20, 1, 1) == 1
    with pytest.raises(ValueError):
        minutes_to_complete(0, 20, 2, 2)


def test_chunk_pacing_that_outruns_the_reader_is_refused(tmp_path):
    """Measured 2026-11-22: pause 5 x 2 copies x one pass lost 5 of 48 chunks."""
    _, result = _launch(
        tmp_path,
        *PRIMARY,
        "--poll-minutes", "240",
        extra_env={"TFM_CHUNK_PAUSE": "5", "TFM_CHUNK_REPEAT": "2", "TFM_CHUNK_PASSES": "1"},
    )
    combined = result.stdout + result.stderr

    assert result.returncode == 2, combined
    assert "of visibility" in combined, combined


def test_the_overrides_allow_fast_pacing_deliberately(tmp_path):
    state, result = _launch(
        tmp_path,
        *PRIMARY,
        "--poll-minutes", "240",
        extra_env={
            "TFM_CHUNK_PAUSE": "5", "TFM_CHUNK_REPEAT": "2", "TFM_CHUNK_PASSES": "1",
            "TFM_ALLOW_FAST_CHUNKS": "1", "TFM_ALLOW_SINGLE_PASS": "1",
        },
    )
    combined = result.stdout + result.stderr

    # The guard is what this tests: the launch reached provisioning. The mock's transfer under
    # fast pacing is not the subject (and one pass with a tiny payload may not verify).
    assert "FATAL: chunk pacing" not in combined, combined
    assert (state / "created.txt").exists(), combined


def test_a_frame_that_costs_more_than_the_credit_warns(tmp_path):
    """A 582-minute frame with $3.70 of credit cannot finish; say so before provisioning."""
    seeds = ",".join(str(seed) for seed in range(1001, 1021))
    _, result = _launch(
        tmp_path,
        *PRIMARY,
        "--poll-minutes", "600",
        extra_env={
            "TFM_FAIRTEST_TARGETS": "severity_french",
            "TFM_FAIRTEST_ARMS": "A_raw,B_ft3,B_ft10,B_ft30",
            "TFM_FAIRTEST_SEEDS": seeds,
            "MOCK_CREDIT": "1.5",
        },
    )
    combined = result.stdout + result.stderr

    assert "above the $1.5000 credit" in combined, combined
