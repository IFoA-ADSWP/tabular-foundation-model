"""The fair test's captures survive the trip: chunked emit, poll merge, restore, cite (#564).

The gate ran the fair test's primary comparison and shipped only its summary, because the log
transport could carry ~6.6 MB and a capture is ~30 MB per target. These tests drive the real
scripts over a synthetic payload in several poll windows -- the shape the launcher sees -- and
require the restored capture to pass the citation check, which is what makes it evidence rather
than a file that arrived.

The failure that matters is the quiet one: a chunk that never arrives must refuse, naming the
sequence number, instead of restoring a truncated capture that looks complete.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
EMIT = REPO_ROOT / "scripts" / "gpu_helpers" / "emit_artifacts.sh"
COLLECT = REPO_ROOT / "scripts" / "gpu_helpers" / "collect_chunks.py"
VERIFY = REPO_ROOT / "scripts" / "gpu_helpers" / "verify_artifacts.py"

sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check_citations import check_run_dir  # noqa: E402
from provenance import sha256_array  # noqa: E402
from run_capture import build_capture, render_capture  # noqa: E402

RUN_ID = "20261112T090000Z"
LEVELS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]


def _slot(run: Path, fold: int, arm: str = "A_raw") -> None:
    """One severity slot, in the layout the runner writes and the capture reader expects."""
    slot = run / "spanish_motor_severity" / arm / f"seed0_fold{fold}"
    slot.mkdir(parents=True)
    predictions = np.array([0.1, 0.2, 0.3])
    truth = np.array([0.0, 0.5, 1.0])
    np.save(slot / "predictions.npy", predictions)
    np.save(slot / "ground_truth.npy", truth)
    np.save(slot / "test_index.npy", np.array([10, 11, 12], dtype=np.int64))
    np.save(slot / "quantiles.npy", np.tile(predictions, (9, 1)))
    np.save(slot / "weights.npy", np.array([1.0, 2.0, 4.0]))
    np.save(slot / "cluster_id.npy", np.array([0, 0, 1], dtype=np.int64))
    (slot / "meta.json").write_text(
        json.dumps(
            {
                "arm": arm,
                "seed": 0,
                "fold": fold,
                "dataset": "spanish_motor_severity",
                "task": "severity",
                "test_rows": 3,
                "predictions_sha256": sha256_array(predictions),
                "verdict_metric": "weighted_rmse",
                "verdict_metric_value": 0.5,
                "rmse": 0.5,
                "quantile_levels": LEVELS,
                "versions": {"tabpfn": "8.5.0", "python": "3.12.0"},
                "weights": {"path": "/models/tabpfn-v3.ckpt", "sha256": "0" * 64},
            }
        )
        + "\n"
    )


@pytest.fixture()
def capture_run(tmp_path: Path) -> Path:
    """A v4 capture directory, exactly as the runner seals one."""
    run = tmp_path / RUN_ID
    run.mkdir()
    for fold in (0, 1):
        _slot(run, fold)
    (run / "capture.json").write_text(render_capture(build_capture(run)))
    assert check_run_dir(run, RUN_ID) == []
    return run


def _emit(run: Path, *, chunk_lines: int, pause: int = 0, repeat: int = 1) -> str:
    env = dict(os.environ)
    env.update({
        "PAYLOAD_ID": run.name,
        "TFM_CHUNK_LINES": str(chunk_lines),
        "TFM_CHUNK_PAUSE": str(pause),
        "TFM_CHUNK_REPEAT": str(repeat),
    })
    done = subprocess.run(
        ["bash", str(EMIT), str(run)],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    return done.stdout


def _polls(log: str, size: int, stride: int | None = None) -> list[str]:
    """The overlapping windows a poller reads: the log grows between polls, it does not reset.

    Overlap is the property the transfer depends on -- a chunk is sealed only where its marker
    and its end marker share a window -- so a test with disjoint windows would fail a transport
    that works, and prove nothing about the one that does not.
    """
    lines = log.splitlines()
    step = stride or max(1, size // 3)
    starts = list(range(0, max(1, len(lines) - size + 1), step)) or [0]
    if starts[-1] + size < len(lines):
        starts.append(len(lines) - size)
    return ["\n".join(lines[start : start + size]) + "\n" for start in starts]


def _merge(windows: list[str], state: Path, tmp_path: Path) -> subprocess.CompletedProcess:
    result = None
    for index, window in enumerate(windows):
        path = tmp_path / f"poll{index}.log"
        path.write_text(window)
        result = subprocess.run(
            [sys.executable, str(COLLECT), "merge", "--window", str(path), "--state", str(state)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
    assert result is not None
    return result


def test_a_capture_survives_polled_chunked_transfer(tmp_path, capture_run):
    log = _emit(capture_run, chunk_lines=2)
    assert "__ART_CHUNK__" in log, "the payload did not chunk at all"
    declared = log.count("__ART_CHUNK__")

    state = tmp_path / "chunks"
    _merge(_polls(log, 9), state, tmp_path)

    raw = tmp_path / "artifacts.raw"
    assembled = subprocess.run(
        [sys.executable, str(COLLECT), "assemble", "--state", str(state), "--out", str(raw)],
        capture_output=True,
        text=True,
    )
    assert assembled.returncode == 0, (
        assembled.stdout
        + f"\nchunks={declared} lines={len(log.splitlines())}\n"
        + "\n".join(line[:60] for line in log.splitlines() if not line.startswith("__ART__"))
    )
    assert f"chunks={declared}" in assembled.stdout

    results = tmp_path / "results"
    verified = subprocess.run(
        [sys.executable, str(VERIFY), "--raw", str(raw), "--dest", str(results),
         "--expect-captures", "1"],
        capture_output=True,
        text=True,
    )
    assert verified.returncode == 0, verified.stdout + verified.stderr
    restored = results / RUN_ID
    assert (restored / "capture.json").is_file()
    assert check_run_dir(restored, RUN_ID) == []


def test_a_missing_chunk_is_refused_and_named(tmp_path, capture_run):
    log = _emit(capture_run, chunk_lines=2)
    state = tmp_path / "chunks"
    _merge(_polls(log, 9), state, tmp_path)

    # Drop the second chunk, as a window that scrolled past it would.
    for victim in sorted((state / RUN_ID).glob("0*.txt"))[1:2]:
        victim.unlink()

    raw = tmp_path / "artifacts.raw"
    assembled = subprocess.run(
        [sys.executable, str(COLLECT), "assemble", "--state", str(state), "--out", str(raw)],
        capture_output=True,
        text=True,
    )
    assert assembled.returncode == 1
    assert "missing seq 2" in assembled.stdout, assembled.stdout
    assert not raw.exists()


def test_repeated_polls_do_not_duplicate_chunks(tmp_path, capture_run):
    log = _emit(capture_run, chunk_lines=2)
    state = tmp_path / "chunks"
    # The same wide window, read five times, as a slow poller would.
    _merge([log] * 5, state, tmp_path)

    declared = log.count("__ART_CHUNK__")
    sealed = sorted((state / RUN_ID).glob("0*.txt"))
    assert len(sealed) == declared

    raw = tmp_path / "artifacts.raw"
    assembled = subprocess.run(
        [sys.executable, str(COLLECT), "assemble", "--state", str(state), "--out", str(raw)],
        capture_output=True,
        text=True,
    )
    assert assembled.returncode == 0, (
        assembled.stdout
        + "\n".join(line[:60] for line in log.splitlines() if not line.startswith("__ART__"))
    )
    assert raw.read_text().count("\n__ART__") == log.count("\n__ART__")


def test_an_unwired_transport_does_not_restore(tmp_path, capture_run):
    """Without a payload id the restored block has no place under results/, so it is refused."""
    log = _emit(capture_run, chunk_lines=0)
    raw = tmp_path / "artifacts.raw"
    raw.write_text(log.replace(f"payload={RUN_ID}", "payload="))
    results = tmp_path / "results"
    verified = subprocess.run(
        [sys.executable, str(VERIFY), "--raw", str(raw), "--dest", str(results),
         "--expect-captures", "1"],
        capture_output=True,
        text=True,
    )
    assert verified.returncode == 8
    assert "no payload=<run id>" in verified.stdout


def test_a_frequency_capture_carrying_weights_is_refused(capture_run):
    """v4's rule, applied through the citation check rather than a second copy of it."""
    manifest = json.loads((capture_run / "capture.json").read_text())
    entry = manifest["captures"][0]
    slot = next(capture_run.glob(f"{manifest['dataset']}/*/seed*_fold*/meta.json")).parent
    record = json.loads((slot / "meta.json").read_text())
    record["task"] = "frequency"
    (slot / "meta.json").write_text(json.dumps(record))

    problems = check_run_dir(capture_run, RUN_ID)
    assert any("v4 frequency entry carries weights_sha256" in problem for problem in problems), (
        problems,
        entry,
    )


def test_four_targets_restore_as_four_captures(tmp_path, capture_run):
    """The registered run's shape: one payload block per target, cited separately (#564).

    A single payload proves the chunking; four prove the block iteration, which is where the
    first block's INFO would otherwise stand in for the other three.
    """
    import shutil

    ids = [f"20261112T09000{index}Z" for index in range(4)]
    logs = []
    for run_id in ids:
        run = tmp_path / "box" / run_id
        shutil.copytree(capture_run, run)
        logs.append(_emit(run, chunk_lines=2))

    state = tmp_path / "chunks"
    _merge(_polls("\n".join(logs), 9), state, tmp_path)

    raw = tmp_path / "artifacts.raw"
    assembled = subprocess.run(
        [sys.executable, str(COLLECT), "assemble", "--state", str(state), "--out", str(raw)],
        capture_output=True,
        text=True,
    )
    assert assembled.returncode == 0, (
        assembled.stdout
        + "\n".join(line[:60] for line in logs[0].splitlines() if not line.startswith("__ART__"))
    )
    assert "payloads=4" in assembled.stdout

    results = tmp_path / "results"
    verified = subprocess.run(
        [sys.executable, str(VERIFY), "--raw", str(raw), "--dest", str(results),
         "--expect-captures", "4"],
        capture_output=True,
        text=True,
    )
    assert verified.returncode == 0, verified.stdout + verified.stderr
    restored = sorted(path.name for path in results.iterdir() if path.is_dir())
    assert restored == sorted(ids)
    for run_id in ids:
        assert check_run_dir(results / run_id, run_id) == []


def _window_of(log: str, start: int, size: int) -> str:
    lines = log.splitlines()
    return "\n".join(lines[start : start + size]) + "\n"


def test_a_chunk_whose_end_marker_is_glued_to_a_truncated_line_is_not_sealed(
    tmp_path, capture_run
):
    """Measured 2026-11-12: the window's edge truncates a 447-char payload line to 296 and glues
    `__ART_CHUNK_END__` onto it. Sealing that would hash a mangled archive and refuse the whole
    payload at the end; dropping it unsealed lets the repeat pass supply a whole chunk (#566).
    """
    log = _emit(capture_run, chunk_lines=2)
    lines = log.splitlines()

    # Truncate the last payload line of the first chunk and glue the end marker to it.
    first_end = next(i for i, line in enumerate(lines) if line == "__ART_CHUNK_END__")
    truncated = lines[first_end - 1][:200] + "__ART_CHUNK_END__"
    mangled = lines[: first_end - 1] + [truncated] + lines[first_end + 1 :]

    state = tmp_path / "chunks"
    window = tmp_path / "poll.log"
    window.write_text("\n".join(mangled) + "\n")
    subprocess.run(
        [sys.executable, str(COLLECT), "merge", "--window", str(window), "--state", str(state)],
        check=True, capture_output=True, text=True,
    )

    assert not (state / RUN_ID / "001.txt").exists(), "a truncated chunk was sealed as if whole"

    # The repeat pass -- the same chunk again, intact -- seals it.
    window.write_text(log)
    subprocess.run(
        [sys.executable, str(COLLECT), "merge", "--window", str(window), "--state", str(state)],
        check=True, capture_output=True, text=True,
    )
    assert (state / RUN_ID / "001.txt").exists()


def test_each_chunk_is_emitted_twice_when_repeat_is_two(tmp_path, capture_run):
    """The one-way channel's only retry is a second copy (#566)."""
    log = _emit(capture_run, chunk_lines=2, repeat=2)

    markers = [line for line in log.splitlines() if line.startswith("__ART_CHUNK__ seq=")]
    declared = int(log.split("chunks=")[1].split()[0])
    assert len(markers) == 2 * declared, log[:200]

    state = tmp_path / "chunks"
    _merge(_polls(log, 9), state, tmp_path)
    raw = tmp_path / "artifacts.raw"
    assembled = subprocess.run(
        [sys.executable, str(COLLECT), "assemble", "--state", str(state), "--out", str(raw)],
        capture_output=True,
        text=True,
    )
    assert assembled.returncode == 0, assembled.stdout
    verified = subprocess.run(
        [sys.executable, str(VERIFY), "--raw", str(raw), "--dest", str(tmp_path / "results"),
         "--expect-captures", "1"],
        capture_output=True,
        text=True,
    )
    assert verified.returncode == 0, verified.stdout + verified.stderr
