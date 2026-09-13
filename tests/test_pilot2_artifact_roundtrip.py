"""PR-2 acceptance test: the artifact payload round-trips AND is verifiable.

The acceptance criterion for PR-2 is that a round-trip reproduces each arm's
predictions with a matching sha256, for a payload at least as large as the real one.
R1 failed this silently: it returned no predictions at all, so its headline numbers
could not be recomputed or paired-tested.

These tests build a synthetic payload in exactly the wire format the bootstrap emits
(base64 of a tar.gz, folded into `__ART__`-tagged lines under the log's 500-char line
cap, preceded by a self-declared `__ARTIFACTS_INFO__` line) and drive the real
verification code over it -- including the failure modes that were previously
indistinguishable from success.

Run:  python -m pytest tests/test_pilot2_artifact_roundtrip.py -v
"""
import base64
import hashlib
import importlib.util
import io
import json
import sys
import tarfile
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "gpu_helpers" / "verify_artifacts.py"

LINE_WIDTH = 440
LINE_TAG = "__ART__"


def _load():
    spec = importlib.util.spec_from_file_location("verify_artifacts", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["verify_artifacts"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def va():
    return _load()


def array_data_sha256(arr: np.ndarray) -> str:
    """The hash the runner records: sha256 of the ARRAY's bytes, not the .npy file."""
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()


def build_payload(runs, *, base64_chars=60_000):
    """Assemble a payload the way bootstrap_pilot.sh does.

    `runs`: list of (run_path, y_prob) where run_path is e.g. "coil2000/A_raw".
    `base64_chars`: pad the archive so the payload is at least as large as a real one
    (~120 KB of raw predictions becomes ~160 KB of base64).
    """
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for run_path, y_prob in runs:
            y = np.asarray(y_prob, dtype=np.float64)
            meta = {
                "run_id": run_path.replace("/", "_") + "_seed42",
                "predictions_sha256": array_data_sha256(y),
            }
            for name, blob in (
                (f"{run_path}/predictions.npy", _npy_bytes(y)),
                (f"{run_path}/meta.json", json.dumps(meta).encode()),
            ):
                ti = tarfile.TarInfo(name)
                ti.size = len(blob)
                tf.addfile(ti, io.BytesIO(blob))
        # Padding file so payload size is representative, not toy-sized. It must be
        # INCOMPRESSIBLE: repeated bytes gzip to almost nothing, which would make the
        # payload tiny and the truncation test meaningless.
        filler = np.random.default_rng(7).integers(0, 256, size=max(0, base64_chars * 3 // 4),
                                                  dtype=np.uint8).tobytes()
        ti = tarfile.TarInfo("pilot_metrics.parquet")
        ti.size = len(filler)
        tf.addfile(ti, io.BytesIO(filler))
    blob = buf.getvalue()
    b64 = base64.b64encode(blob).decode()
    folded = [b64[i : i + LINE_WIDTH] for i in range(0, len(b64), LINE_WIDTH)]
    info = (
        f"__ARTIFACTS_INFO__ bytes={len(blob)} sha256={hashlib.sha256(blob).hexdigest()} "
        f"lines={len(folded)} files={len(runs) * 2 + 1}"
    )
    log = "\n".join([info, "__ARTIFACTS_BEGIN__", *[LINE_TAG + x for x in folded], "__ARTIFACTS_END__"])
    return log, len(folded)


def _npy_bytes(arr: np.ndarray) -> bytes:
    b = io.BytesIO()
    np.save(b, arr)
    return b.getvalue()


def sample_runs():
    rng = np.random.default_rng(0)
    return [
        ("coil2000/A_raw", rng.random(1000)),
        ("coil2000/B_in_domain", rng.random(1000)),
        ("uslapseagent/A_raw", rng.random(1000)),
    ]


# --------------------------------------------------------------------------
# The round trip
# --------------------------------------------------------------------------
def test_parse_info_reads_every_field_not_just_the_first(va):
    """Regression: a `(\\S+)` capture reads only `bytes=...` and silently disables
    BOTH guards (the length check and the checksum check), so a truncated or
    tampered payload would sail through. Every field must be parsed."""
    raw = "__ARTIFACTS_INFO__ bytes=1234 sha256=deadbeef lines=42 files=7\n"
    info = va.parse_info(raw)
    assert info == {"bytes": "1234", "sha256": "deadbeef", "lines": "42", "files": "7"}


def test_npy_data_hash_matches_array_bytes_not_container(va, tmp_path):
    """The subtlety that would make a naive check always fail."""
    arr = np.random.default_rng(1).random(50)
    p = tmp_path / "predictions.npy"
    np.save(p, arr)
    # The container's bytes are NOT the array's bytes ...
    assert hashlib.sha256(p.read_bytes()).hexdigest() != array_data_sha256(arr)
    # ... but parsing the header and hashing the payload IS.
    assert va.npy_data_sha256(str(p)) == array_data_sha256(arr)


def test_round_trip_restores_and_verifies(va, tmp_path):
    log, n_lines = build_payload(sample_runs())
    dest = tmp_path / "out"
    rc, report = va.restore(log, str(dest))
    assert rc == va.EXIT_OK, report
    assert dest.joinpath("coil2000/A_raw/predictions.npy").exists()
    verified, mismatched, missing, details = va.verify_predictions(str(dest))
    assert (verified, mismatched, missing) == (3, 0, 0), details


def test_payload_is_representative_size(va, tmp_path):
    """Guard against a toy-sized test that cannot catch log truncation."""
    log, n_lines = build_payload(sample_runs())
    assert n_lines > 100, f"payload only {n_lines} lines; make the test realistic"


def test_longest_line_respects_the_log_cap(va, tmp_path):
    """The container log caps lines at 500 chars; every payload line must fit."""
    log, _ = build_payload(sample_runs())
    longest = max(len(ln) for ln in log.splitlines())
    assert longest <= 500, f"longest line {longest} exceeds the 500-char log cap"


# --------------------------------------------------------------------------
# Failure modes that were previously indistinguishable from success
# --------------------------------------------------------------------------
def test_truncated_payload_is_detected_not_unpacked(va, tmp_path):
    """A short read must say so, not surface later as 'truncated gzip input'."""
    log, n_lines = build_payload(sample_runs())
    lines = log.splitlines()
    # Drop the last third of the payload lines, as a too-small --tail window would.
    keep = [ln for ln in lines if not ln.startswith(LINE_TAG)]
    tags = [ln for ln in lines if ln.startswith(LINE_TAG)]
    truncated = "\n".join(keep[:1] + keep[1:2] + tags[: len(tags) * 2 // 3] + [keep[-1]])
    rc, report = va.restore(truncated, str(tmp_path / "out"))
    assert rc == va.EXIT_INCOMPLETE
    assert "short" in report and f"of {n_lines} lines" in report


def test_checksum_mismatch_is_detected(va, tmp_path):
    log, _ = build_payload(sample_runs())
    tampered = log.replace("sha256=", "sha256=deadbeef", 1)
    rc, report = va.restore(tampered, str(tmp_path / "out"))
    assert rc == va.EXIT_INCOMPLETE
    assert "sha256 mismatch" in report


def test_absent_payload_markers_reported(va, tmp_path):
    rc, report = va.restore("no markers here at all\n", str(tmp_path / "out"))
    assert rc == va.EXIT_NO_PAYLOAD
    assert "no artifact markers" in report


def test_declared_empty_payload_is_not_a_failure_to_unpack(va, tmp_path):
    log = "__ARTIFACTS_INFO__ bytes=0 sha256=- lines=0 files=0\n__ARTIFACTS_BEGIN__\n__ARTIFACTS_END__"
    rc, report = va.restore(log, str(tmp_path / "out"))
    assert rc == va.EXIT_NO_PAYLOAD
    assert "declared empty" in report


def test_missing_predictions_fails_verification(va, tmp_path):
    """meta.json claims a hash but the predictions never arrived."""
    log, _ = build_payload(sample_runs())
    dest = tmp_path / "out"
    rc, _ = va.restore(log, str(dest))
    assert rc == va.EXIT_OK
    (dest / "coil2000/A_raw/predictions.npy").unlink()
    verified, mismatched, missing, details = va.verify_predictions(str(dest))
    assert missing == 1
    assert any("MISSING" in d for d in details)


def test_tampered_predictions_fail_verification(va, tmp_path):
    log, _ = build_payload(sample_runs())
    dest = tmp_path / "out"
    rc, _ = va.restore(log, str(dest))
    assert rc == va.EXIT_OK
    p = dest / "coil2000/A_raw/predictions.npy"
    np.save(p, np.zeros(1000))  # same shape, different values
    verified, mismatched, missing, details = va.verify_predictions(str(dest))
    assert mismatched == 1
    assert any("MISMATCH" in d for d in details)


def test_runs_without_a_claimed_hash_are_skipped_not_failed(va, tmp_path):
    """R1-schema meta.json (no predictions_sha256) must not be read as a failure."""
    dest = tmp_path / "out"
    d = dest / "old_arm"
    d.mkdir(parents=True)
    (d / "meta.json").write_text(json.dumps({"run_id": "old"}))
    np.save(d / "predictions.npy", np.zeros(10))
    verified, mismatched, missing, _ = va.verify_predictions(str(dest))
    assert (verified, mismatched, missing) == (0, 0, 0)


# --------------------------------------------------------------------------
# CLI behaviour
# --------------------------------------------------------------------------
def test_cli_end_to_end_and_exit_codes(va, tmp_path, monkeypatch, capsys):
    log, _ = build_payload(sample_runs())
    raw = tmp_path / "log.txt"
    raw.write_text(log)
    dest = tmp_path / "out"
    monkeypatch.setattr(
        sys, "argv", ["verify_artifacts.py", "--raw", str(raw), "--dest", str(dest)]
    )
    assert va.main() == 0
    out = capsys.readouterr().out
    assert "OK restored" in out
    assert "verified=3" in out


def test_cli_missing_log_is_reported(va, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        ["verify_artifacts.py", "--raw", str(tmp_path / "nope.txt"), "--dest", str(tmp_path)],
    )
    assert va.main() == va.EXIT_NO_PAYLOAD
    assert "missing captured log" in capsys.readouterr().out


# --------------------------------------------------------------------------
# END TO END: the REAL emitter piped into the REAL verifier, locally, at $0.
# This is the PR-2 acceptance test proper -- it exercises both scripts as the
# pipeline actually uses them, rather than a reimplementation of the wire format.
# --------------------------------------------------------------------------
EMIT = REPO_ROOT / "scripts" / "gpu_helpers" / "emit_artifacts.sh"


def _build_output_tree(root: Path, n_arms=4):
    """Mimic the runner's on-disk layout: <dataset>/<arm>/{predictions,ground_truth}.npy + meta.json."""
    import subprocess  # noqa: F401  (kept local to the helper for clarity)

    runs = {
        "coil2000/A_raw": 1000,
        "coil2000/B_in_domain": 1000,
        "uslapseagent/A_raw": 1000,
        "uslapseagent/B_in_domain": 1000,
    }
    rng = np.random.default_rng(11)
    for run_path, n in list(runs.items())[:n_arms]:
        d = root / run_path
        d.mkdir(parents=True, exist_ok=True)
        y_prob = rng.random(n)
        y_true = (rng.random(n) < 0.3).astype(np.int64)
        np.save(d / "predictions.npy", y_prob)
        np.save(d / "ground_truth.npy", y_true)
        meta = {
            "schema_version": 2,
            "run_id": run_path.replace("/", "_") + "_seed42",
            "predictions_sha256": array_data_sha256(y_prob),
        }
        (d / "meta.json").write_text(json.dumps(meta))
    (root / "pilot_metrics.parquet").write_bytes(np.random.default_rng(12).integers(
        0, 256, size=30_000, dtype=np.uint8).tobytes())
    return list(runs.items())[:n_arms]


def test_e2e_real_emit_then_real_verify(va, tmp_path):
    """Emit with the shell script, verify with the python script -- no spend, no box."""
    import subprocess

    tree = tmp_path / "pilot"
    runs = _build_output_tree(tree)

    emitted = subprocess.run(
        ["bash", str(EMIT), str(tree)], capture_output=True, text=True, check=True
    ).stdout
    assert "__ARTIFACTS_BEGIN__" in emitted and "__ARTIFACTS_END__" in emitted
    assert "__ARTIFACTS_INFO__" in emitted

    raw = tmp_path / "log.txt"
    raw.write_text(emitted)
    dest = tmp_path / "restored"

    rc = subprocess.run(
        [sys.executable, str(SCRIPT), "--raw", str(raw), "--dest", str(dest)],
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0, f"stdout={rc.stdout}\nstderr={rc.stderr}"
    assert f"verified={len(runs)}" in rc.stdout, rc.stdout

    # Byte fidelity: what came back must be what the runner wrote.
    for run_path, _ in runs:
        orig = np.load(tree / run_path / "predictions.npy")
        back = np.load(dest / run_path / "predictions.npy")
        assert np.array_equal(orig, back), f"{run_path} predictions differ after round trip"
        assert va.npy_data_sha256(str(dest / run_path / "predictions.npy")) == \
            array_data_sha256(orig)
        # Regression: meta.json is one level deeper than the old `*/meta.json` glob
        # assumed, so it was never returned from the box at all.
        assert (dest / run_path / "meta.json").exists(), f"{run_path}/meta.json did not return"


def test_e2e_truncated_emit_is_rejected(va, tmp_path):
    """A too-small --tail window must be reported as a short read, not unpacked."""
    import subprocess

    tree = tmp_path / "pilot"
    _build_output_tree(tree)
    emitted = subprocess.run(
        ["bash", str(EMIT), str(tree)], capture_output=True, text=True, check=True
    ).stdout

    lines = emitted.splitlines()
    info = [ln for ln in lines if ln.startswith("__ARTIFACTS_INFO__")]
    tags = [ln for ln in lines if ln.startswith(LINE_TAG)]
    truncated = "\n".join(info + ["__ARTIFACTS_BEGIN__"] + tags[: len(tags) // 2] + ["__ARTIFACTS_END__"])

    raw = tmp_path / "log.txt"
    raw.write_text(truncated)
    rc = subprocess.run(
        [sys.executable, str(SCRIPT), "--raw", str(raw), "--dest", str(tmp_path / "out")],
        capture_output=True,
        text=True,
    )
    assert rc.returncode == va.EXIT_INCOMPLETE
    assert "short" in rc.stdout


def test_e2e_empty_tree_declares_zero_not_failure(tmp_path):
    """No outputs at all must be an explicit empty payload, not a broken one."""
    import subprocess

    tree = tmp_path / "empty_pilot"
    tree.mkdir()
    emitted = subprocess.run(
        ["bash", str(EMIT), str(tree)], capture_output=True, text=True, check=True
    ).stdout
    assert "bytes=0" in emitted and "lines=0" in emitted
    assert "__ARTIFACTS_BEGIN__" in emitted
