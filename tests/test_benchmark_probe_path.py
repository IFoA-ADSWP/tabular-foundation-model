"""The paid path can carry one benchmark measurement (#528).

The probe is `scripts/benchmarks/benchmark_regressor_fit.py --measure`: one fine-tune at
10,000 rows x 30 epochs whose wall time sizes the fair test. Until this existed, the box
could only run `scripts/run_pilot.py`'s arms, so the probe was implemented but unlaunchable
-- the exact shape of #450, where both ends were individually correct and only the seam was
wrong.

Three places can lose the measurement, and each is asserted here rather than grepped for:

  1. The launcher does not forward the mode, so the box silently runs arms.
  2. The bootstrap runs the benchmark but does not emit its directory.
  3. The artifact comes back, but verification reports zero predictions and refuses a payload
     that is exactly what was asked for.

The launcher tests drive the real `vast_run.sh` against `mock_vastai.sh`; the bootstrap
tests run the real `bootstrap_pilot.sh` on a stubbed box. Neither provisions anything.

Run:  python -m pytest tests/test_benchmark_probe_path.py -v
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

# The launcher harness is shared, not copied: two copies of it would drift, and the seam
# between the launcher and the mock is precisely the thing under test (#450).
from tests.test_pilot2_seed_passthrough import (
    _launch,
    _payload_after_launch,
    _payload_export,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = REPO_ROOT / "scripts" / "gpu_helpers" / "bootstrap_pilot.sh"
VERIFIER = REPO_ROOT / "scripts" / "gpu_helpers" / "verify_artifacts.py"
VAST_RUN = REPO_ROOT / "scripts" / "gpu_helpers" / "vast_run.sh"
BENCHMARK_SCRIPT = REPO_ROOT / "scripts" / "benchmarks" / "benchmark_regressor_fit.py"

RUN_STAMP = "20261111T000000Z"


@pytest.fixture(scope="module")
def bench():
    """The real harness module, imported once (no GPU, no fit)."""
    spec = importlib.util.spec_from_file_location("benchmark_regressor_fit_probe", BENCHMARK_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["benchmark_regressor_fit_probe"] = module
    spec.loader.exec_module(module)
    return module


def measurement(**overrides):
    """A record with the shape `benchmark_regressor_fit.py --measure` writes."""
    block = {
        "wall_seconds": 158.4,
        "rows": 10_000,
        "epochs": 30,
        "device": "cuda",
        "tabpfn_version": "8.5.0",
        "frame": "freMTPL2freq:ClaimNb",
        "seed": 42,
    }
    block.update(overrides)
    return {
        "schema_version": 1,
        "kind": "benchmark_fit",
        "created_utc": "2026-11-11T00:00:00Z",
        "measurement": block,
        "config": {"n_features": 9, "model_version": "V3"},
    }


def _write_measurement(directory: Path, name="regressor-fit-20261111T000000Z.json", **overrides):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(json.dumps(measurement(**overrides)))
    return path


# ---------------------------------------------------------------------------
# 1. The launcher forwards the mode, and refuses to guess what it means
# ---------------------------------------------------------------------------
def test_the_onstart_payload_exports_the_benchmark_mode(tmp_path):
    """The box branches on this value; an unforwarded mode silently runs the arm loop."""
    payload = _payload_after_launch(tmp_path, "--benchmark", "regressor-fit")

    assert "export BENCHMARK=" in payload, payload
    assert _payload_export(payload, "BENCHMARK") == "regressor-fit", payload


def test_the_payload_omits_the_mode_when_unset(tmp_path):
    """Absent, not empty: an `export BENCHMARK=` line would read as a mode the box cannot run."""
    payload = _payload_after_launch(tmp_path, "--arms", "A_raw")

    assert "export BENCHMARK=" not in payload, payload
    assert _payload_export(payload, "BENCHMARK") == "<unset>", payload


def test_the_mode_owns_the_frame_so_a_mixed_launch_is_refused(tmp_path):
    """`--benchmark regressor-fit --arms A_raw` has two answers. Refused, not resolved.

    The measurement is one fixed point (10,000 rows x 30 epochs). Silently dropping the arm
    list is the seam failure #450 keeps closing: both ends look fine and the operator's
    setting became a belief.
    """
    state, result = _launch(
        tmp_path, "--benchmark", "regressor-fit", "--arms", "A_raw", "--seeds", "42"
    )
    combined = result.stdout + result.stderr

    assert result.returncode == 2, combined
    assert "owns the frame" in combined, combined
    assert not (state / "created.txt").exists(), "the refusal happened after provisioning"


def test_an_unknown_mode_is_refused_before_anything_is_rented(tmp_path):
    state, result = _launch(tmp_path, "--benchmark", "regressor-fit-typo")
    combined = result.stdout + result.stderr

    assert result.returncode == 2, combined
    assert "unknown --benchmark" in combined, combined
    assert not (state / "created.txt").exists()


# ---------------------------------------------------------------------------
# 1b. The image must match the card (#528)
# ---------------------------------------------------------------------------
def test_a_pinned_offer_reads_its_cuda_and_picks_the_matching_image(tmp_path):
    """`--offer-id` used to hardcode CUDA=12.4 and select a torch build the card cannot run.

    Measured 2026-11-11: a Blackwell RTX PRO 4000 (sm_120) on the cu124 image reached the first
    epoch and died with "no kernel image is available". The offer knows its ceiling; read it.
    """
    state, result = _launch(tmp_path)
    combined = result.stdout + result.stderr

    assert result.returncode == 0, combined
    assert "host cuda<=13.0 (from the offer)" in combined, combined
    assert "image: pytorch/pytorch:2.7.0-cuda12.8-cudnn9-runtime" in combined, combined
    assert (state / "created.txt").exists(), combined


def test_a_pinned_offer_whose_cuda_cannot_be_read_is_refused(tmp_path):
    """A guess is worse than a refusal: the last guess cost a paid run that never fitted."""
    offers = tmp_path / "no-offers.json"
    offers.write_text("[]")

    state, result = _launch(tmp_path, extra_env={"MOCK_OFFERS": str(offers)})
    combined = result.stdout + result.stderr

    assert result.returncode == 2, combined
    assert "cannot be read" in combined, combined
    assert "CUDA=<host cuda>" in combined, combined
    assert not (state / "created.txt").exists()


def test_the_cuda_ceiling_can_be_stated_for_a_pinned_offer(tmp_path):
    """When the offer is gone from the list, the operator may state the ceiling explicitly."""
    offers = tmp_path / "no-offers.json"
    offers.write_text("[]")

    state, result = _launch(
        tmp_path, extra_env={"MOCK_OFFERS": str(offers), "CUDA": "13.0"}
    )
    combined = result.stdout + result.stderr

    assert result.returncode == 0, combined
    assert "image: pytorch/pytorch:2.7.0-cuda12.8-cudnn9-runtime" in combined, combined
    assert (state / "created.txt").exists(), combined


def test_the_ssh_transport_pulls_the_modes_tree():
    """The two modes write different trees, and the ssh path copies a directory, not the log.

    Without this the pilot's artifacts still arrive but the probe's record never does -- and
    the failure would appear as "the measurement did not arrive" on a paid instance.
    """
    script = VAST_RUN.read_text()
    pull = script.split("=== pulling artifacts ===", 1)[1]

    assert 'if [ -n "$BENCHMARK" ]; then PULL_SUBDIR="outputs/benchmark"' in pull, pull
    assert "root@$HOST:/workspace/tfm/$PULL_SUBDIR/*" in pull, pull


# ---------------------------------------------------------------------------
# 2. The bootstrap runs the measurement and emits its directory
# ---------------------------------------------------------------------------
STUB_NVIDIA_SMI = "#!/bin/bash\necho 'NVIDIA RTX PRO 4000, 49140 MiB, 550.54'\n"

# Every python3 call succeeds, the argv is recorded, and `--out <path>` is materialised so the
# emitter has the file the real harness would have written. Not a python interpreter: a shell
# double, so the test never imports tabpfn or touches a GPU.
STUB_PYTHON3 = """#!/bin/bash
printf '%s\\n' "$*" >> "$TFM_TEST_ARGV"
if [ -n "${TFM_TEST_FAIL_MEASURE:-}" ]; then
  case "$*" in *benchmark_regressor_fit.py*) exit 1 ;; esac
fi
out=""
prev=""
for a in "$@"; do
  [ "$prev" = "--out" ] && out="$a"
  prev="$a"
done
if [ -n "$out" ]; then
  mkdir -p "$(dirname "$out")"
  cat > "$out" <<'JSON'
{"schema_version": 1, "kind": "benchmark_fit",
 "measurement": {"wall_seconds": 158.4, "rows": 10000, "epochs": 30,
                 "device": "cuda", "tabpfn_version": "8.5.0",
                 "frame": "freMTPL2freq:ClaimNb", "seed": 42}}
JSON
fi
exit 0
"""

STUB_GIT = (
    "#!/bin/bash\n"
    'if [ "${1:-}" = "clone" ]; then\n'
    '  for last; do :; done\n'
    '  mkdir -p "$last"\n'
    '  cp -R "$TFM_TEST_TREE"/. "$last"/\n'
    "fi\n"
    "exit 0\n"
)

STUB_EMITTER = """#!/bin/bash
printf '%s\\n' "${1:-}" > "$TFM_TEST_EMIT_DIR"
echo "__ARTIFACTS_INFO__ bytes=0 sha256=- lines=0 files=0"
echo "__ARTIFACTS_BEGIN__"
echo "__ARTIFACTS_END__"
"""


def _run_bootstrap(tmp_path, **env_overrides):
    """Run the real bootstrap on a stubbed box; return (completed process, argv, emit dir)."""
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    for name, body in (
        ("nvidia-smi", STUB_NVIDIA_SMI),
        ("python3", STUB_PYTHON3),
        ("git", STUB_GIT),
    ):
        (stubs / name).write_text(body)
        (stubs / name).chmod(0o755)

    # The "remote": only the paths the bootstrap runs by name are needed. The python3 double
    # ignores its script, so these exist to keep the tree honest, not to execute.
    tree = tmp_path / "remote"
    (tree / "scripts" / "gpu_helpers").mkdir(parents=True)
    (tree / "scripts" / "benchmarks").mkdir(parents=True)
    (tree / "scripts" / "run_pilot.py").write_text("# stub\n")
    (tree / "scripts" / "benchmarks" / "benchmark_regressor_fit.py").write_text("# stub\n")
    (tree / "scripts" / "gpu_helpers" / "fetch_weights.py").write_text("# stub\n")
    (tree / "scripts" / "gpu_helpers" / "emit_artifacts.sh").write_text(STUB_EMITTER)

    argv = tmp_path / "argv.txt"
    argv.write_text("")
    emit = tmp_path / "emit-dir.txt"
    (tmp_path / "home").mkdir()

    env = {
        "PATH": f"{stubs}:/usr/bin:/bin:/usr/sbin:/sbin",
        "HOME": str(tmp_path / "home"),
        "TABPFN_TOKEN": "pk_stub_not_a_real_token",
        "WORKDIR": str(tmp_path / "workspace" / "tfm"),
        "TFM_RUN_STAMP": RUN_STAMP,
        "TFM_TEST_TREE": str(tree),
        "TFM_TEST_ARGV": str(argv),
        "TFM_TEST_EMIT_DIR": str(emit),
    }
    env.update(env_overrides)

    result = subprocess.run(
        ["bash", str(BOOTSTRAP)],
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(tmp_path),
    )
    return result, argv.read_text().splitlines(), emit


def test_the_bootstrap_runs_the_measure_and_emits_its_directory(tmp_path):
    """One command replaces the arm loop, and the record leaves through the artifact channel."""
    result, argv, emit = _run_bootstrap(tmp_path, BENCHMARK="regressor-fit")
    combined = result.stdout + result.stderr

    assert "BOOTSTRAP FINISHED" in result.stdout, combined
    assert "########## BENCHMARK regressor-fit ##########" in result.stdout, combined

    measured = [line for line in argv if "benchmark_regressor_fit.py" in line]
    assert measured, combined
    assert "--measure" in measured[0], measured
    assert f"--out outputs/benchmark/regressor-fit-{RUN_STAMP}.json" in measured[0], measured

    # The record must be on disk where the emitter was pointed, not only in the log.
    record = tmp_path / "workspace" / "tfm" / "outputs" / "benchmark" / (
        f"regressor-fit-{RUN_STAMP}.json"
    )
    assert record.exists(), combined
    assert json.loads(record.read_text())["kind"] == "benchmark_fit"

    # The emitter was handed the benchmark directory, not the pilot's.
    assert emit.read_text().strip() == "outputs/benchmark", emit.read_text()

    # And no arm ran: the two modes must not both execute.
    assert not [line for line in argv if "run_pilot.py" in line], argv
    assert "ARM RECORDS" not in result.stdout, combined


def test_the_bootstrap_refuses_a_frame_alongside_the_benchmark(tmp_path):
    """Run directly on a box (the header documents it), the mix must not be resolved silently."""
    result, argv, emit = _run_bootstrap(tmp_path, BENCHMARK="regressor-fit", ARMS="A_raw")
    combined = result.stdout + result.stderr

    assert result.returncode == 2, combined
    assert "owns the frame" in combined, combined
    assert not [line for line in argv if "benchmark_regressor_fit.py" in line], argv
    assert emit.exists() is False


def test_the_bootstrap_refuses_an_unknown_mode(tmp_path):
    result, argv, _ = _run_bootstrap(tmp_path, BENCHMARK="regressor-fit-typo")
    combined = result.stdout + result.stderr

    assert result.returncode == 2, combined
    assert "unknown BENCHMARK" in combined, combined
    assert not [line for line in argv if "benchmark_regressor_fit.py" in line], argv


def test_a_failed_measure_still_finishes_and_exits_nonzero(tmp_path):
    """The failure must not hang the launcher's poll, and must not read as a success.

    `finish; exit "$BENCH_RC"` is the one line where a failed fit could turn into a green
    bootstrap: the completion marker has to fire (or the launcher waits out its whole ceiling
    on a box that is already done), and the exit code has to stay non-zero.
    """
    result, _, emit = _run_bootstrap(
        tmp_path, BENCHMARK="regressor-fit", TFM_TEST_FAIL_MEASURE="1"
    )
    combined = result.stdout + result.stderr

    assert result.returncode == 1, combined
    assert "BENCHMARK EXITED rc=1" in combined, combined
    assert "BOOTSTRAP FINISHED" in result.stdout, combined
    # An empty payload is still emitted; the verifier is what turns it into a refusal.
    assert emit.exists(), combined


# ---------------------------------------------------------------------------
# 3. A measurement payload verifies -- and its absence is a refusal
# ---------------------------------------------------------------------------
def _verify(dest: Path, *flags):
    return subprocess.run(
        [sys.executable, str(VERIFIER), "--verify-only", "--raw", "/dev/null",
         "--dest", str(dest), *flags],
        capture_output=True,
        text=True,
    )


def test_one_complete_measurement_verifies_and_names_the_wall_time(tmp_path):
    """The payload has no predictions, so this check replaces "verified=N" rather than skipping it."""
    dest = tmp_path / "returned"
    _write_measurement(dest)

    result = _verify(dest, "--expect-measurement")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "wall_seconds=158.4" in result.stdout, result.stdout
    assert "frame=freMTPL2freq:ClaimNb" in result.stdout, result.stdout


def test_a_payload_without_a_measurement_is_refused(tmp_path):
    """An empty return is not "no outputs" here -- the launch existed to produce this record."""
    dest = tmp_path / "returned"
    dest.mkdir()

    result = _verify(dest, "--expect-measurement")

    assert result.returncode == 7, result.stdout + result.stderr
    assert "found 0" in result.stdout, result.stdout


def test_two_measurements_in_one_payload_is_refused(tmp_path):
    """One capture is one point; a second record means a mixed launch or a duplicated emit."""
    dest = tmp_path / "returned"
    _write_measurement(dest, name="a.json")
    _write_measurement(dest, name="b.json")

    result = _verify(dest, "--expect-measurement")

    assert result.returncode == 7, result.stdout + result.stderr
    assert "found 2" in result.stdout, result.stdout


def test_a_record_missing_an_acceptance_field_is_refused(tmp_path):
    """Dropping `device` leaves a fit nobody can attribute; it must not read as measured."""
    dest = tmp_path / "returned"
    record = _write_measurement(dest)
    payload = json.loads(record.read_text())
    del payload["measurement"]["device"]
    record.write_text(json.dumps(payload))

    result = _verify(dest, "--expect-measurement")

    assert result.returncode == 7, result.stdout + result.stderr
    assert "device" in result.stdout, result.stdout


def test_a_zero_wall_time_is_refused(tmp_path):
    """The record's one job is a time; zero is the shape of a fit that never ran."""
    dest = tmp_path / "returned"
    _write_measurement(dest, wall_seconds=0)

    result = _verify(dest, "--expect-measurement")

    assert result.returncode == 7, result.stdout + result.stderr
    assert "not a positive time" in result.stdout, result.stdout


def test_a_fit_at_another_point_is_not_the_pre_registered_measurement(tmp_path):
    """A 3,000-row, 3-epoch fit is a fit, but it is not the point the estimate may rest on.

    Presence-only checks would accept exactly this: the record is complete, and it would then
    price the whole 255-fit matrix from a fit twelve epochs short.
    """
    dest = tmp_path / "returned"
    _write_measurement(dest, name="small.json", rows=3_000, epochs=3)

    result = _verify(dest, "--expect-measurement")

    assert result.returncode == 7, result.stdout + result.stderr
    assert "not the pre-registered point" in result.stdout, result.stdout
    assert "rows=3000" in result.stdout and "epochs=3" in result.stdout, result.stdout


def test_the_record_the_harness_writes_passes_the_verifier(bench, tmp_path):
    """Producer -> verifier, with no GPU: the seam a paid run would otherwise test first.

    The bootstrap test's record is written by its python3 double, so on its own it proves the
    tree is emitted, not that the harness's record is verifiable. Building the record here and
    feeding it to the real verifier closes that gap: a renamed or dropped field fails in CI,
    not after the spend.
    """
    record = bench.build_record(
        wall_seconds=158.4,
        rows=10_000,
        n_features=9,
        epochs=30,
        device="cuda",
        frame="freMTPL2freq:ClaimNb",
        seed=42,
        tabpfn_version="8.5.0",
        weights={"checkpoint": "tabpfn-v3-regressor-v3_default.ckpt", "downloaded": True},
        gpu_name="NVIDIA RTX PRO 4000",
    )
    dest = tmp_path / "returned"
    dest.mkdir()
    (dest / f"regressor-fit-{RUN_STAMP}.json").write_text(json.dumps(record))

    result = _verify(dest, "--expect-measurement")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "wall_seconds=158.4" in result.stdout, result.stdout
    assert "frame=freMTPL2freq:ClaimNb" in result.stdout, result.stdout


def test_the_two_payload_contracts_cannot_be_asked_for_at_once(tmp_path):
    dest = tmp_path / "returned"
    _write_measurement(dest)

    result = _verify(dest, "--expect-measurement", "--expect-seeds", "42")

    assert result.returncode == 2, result.stdout + result.stderr
    assert "different payloads" in result.stdout, result.stdout


def test_an_empty_benchmark_payload_is_a_refusal_not_a_warning(tmp_path):
    """Exit 3 means "the box produced no outputs", which for a probe is a lost run.

    Asserted through the wire format rather than the tree, because the remap happens where
    the declared size is read -- the point a truncated emit is detected.
    """
    raw = tmp_path / "log.txt"
    raw.write_text(
        "__ARTIFACTS_INFO__ bytes=0 sha256=- lines=0 files=0\n"
        "__ARTIFACTS_BEGIN__\n"
        "__ARTIFACTS_END__\n"
    )
    result = subprocess.run(
        [sys.executable, str(VERIFIER), "--raw", str(raw),
         "--dest", str(tmp_path / "returned"), "--expect-measurement"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 7, result.stdout + result.stderr
    assert "declared empty" in result.stdout, result.stdout


# ---------------------------------------------------------------------------
# 4. End to end through the launcher: the measurement comes back, or the run fails
# ---------------------------------------------------------------------------
def test_a_mock_probe_run_returns_the_measurement_and_exits_zero(tmp_path):
    """The whole paid path at $0: create -> emit -> verify -> destroy, with the record on disk."""
    tree = tmp_path / "probe-tree"
    _write_measurement(tree, name="regressor-fit-20261111T000000Z.json")

    _, result = _launch(
        tmp_path,
        "--benchmark", "regressor-fit",
        extra_env={"MOCK_OUTPUT_TREE": str(tree)},
    )
    combined = result.stdout + result.stderr

    assert result.returncode == 0, combined
    assert "OK measurement" in combined, combined
    returned = list((tmp_path / "returned").rglob("regressor-fit-*.json"))
    assert len(returned) == 1, returned
    assert json.loads(returned[0].read_text())["kind"] == "benchmark_fit"


def test_a_probe_run_that_returns_nothing_is_not_a_success(tmp_path):
    """The failure this guards: a launch that measured nothing exits 0 and looks like a datum."""
    _, result = _launch(tmp_path, "--benchmark", "regressor-fit")
    combined = result.stdout + result.stderr

    assert result.returncode == 1, combined
    assert "did not arrive intact" in combined, combined
