"""Acceptance tests for the Pilot 2 prerequisites implemented in scripts/run_pilot.py.

These are the checks recorded in docs/reports/PILOT_2_PREREQUISITES.md. Each test
corresponds to one prerequisite's acceptance criterion, so a prerequisite can only
be marked DONE when the matching test passes.

Run:  python -m pytest tests/test_pilot2_prerequisites.py -v
"""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_pilot.py"


def _load_run_pilot():
    """Load scripts/run_pilot.py as a module (it is a script, not a package module)."""
    spec = importlib.util.spec_from_file_location("run_pilot", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["run_pilot"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def rp():
    return _load_run_pilot()


# --------------------------------------------------------------------------
# PR-6 -- dataset and split fingerprints
# --------------------------------------------------------------------------
def test_pf_dataset_fingerprint_has_content_hash(rp):
    fp = rp.dataset_fingerprint("coil2000")
    if not fp.get("exists", True):
        pytest.skip("dataset not present locally")
    assert len(fp["sha256"]) == 64
    assert fp["n_rows"] > 0
    assert fp["n_cols"] > 0
    assert 0.0 < fp["positive_rate"] < 1.0
    assert fp["target_col"] == rp.DATASETS["coil2000"]["target"]
    # columns are recorded, so a schema change is visible
    assert len(fp["columns"]) == fp["n_cols"]


def test_pf_dataset_fingerprint_is_stable_and_content_addressed(rp):
    a = rp.dataset_fingerprint("coil2000")
    b = rp.dataset_fingerprint("coil2000")
    if not a.get("exists", True):
        pytest.skip("dataset not present locally")
    assert a["sha256"] == b["sha256"]


def test_pf_split_index_hash_is_reproducible(rp):
    rng = np.random.default_rng(0)
    X = rng.normal(size=(400, 5))
    y = (rng.random(400) < 0.3).astype(int)

    _, _, _, _, tr1, te1, fp1 = rp.make_split(X, y, seed=42, train_size=200, test_size=100)
    _, _, _, _, tr2, te2, fp2 = rp.make_split(X, y, seed=42, train_size=200, test_size=100)

    assert np.array_equal(tr1, tr2) and np.array_equal(te1, te2)
    assert fp1["train_index_sha256"] == fp2["train_index_sha256"]
    assert fp1["test_index_sha256"] == fp2["test_index_sha256"]
    assert fp1["test_rows_excluded_from_fit"] is True


def test_pf_split_changes_with_seed(rp):
    rng = np.random.default_rng(1)
    X = rng.normal(size=(400, 5))
    y = (rng.random(400) < 0.3).astype(int)
    _, _, _, _, _, _, fp42 = rp.make_split(X, y, seed=42, train_size=200, test_size=100)
    _, _, _, _, _, _, fp43 = rp.make_split(X, y, seed=43, train_size=200, test_size=100)
    assert fp42["test_index_sha256"] != fp43["test_index_sha256"]


def test_pf_split_record_carries_class_counts(rp):
    rng = np.random.default_rng(2)
    X = rng.normal(size=(500, 4))
    y = (rng.random(500) < 0.2).astype(int)
    _, _, y_tr, y_te, _, _, fp = rp.make_split(X, y, seed=42, train_size=300, test_size=150)
    assert fp["pos_train"] == int(y_tr.sum())
    assert fp["pos_test"] == int(y_te.sum())
    assert fp["n_train"] == len(y_tr)
    assert fp["n_test"] == len(y_te)


def test_pf_folds_partition_without_overlap(rp):
    rng = np.random.default_rng(3)
    X = rng.normal(size=(300, 3))
    y = (rng.random(300) < 0.5).astype(int)
    seen = []
    for f in range(3):
        _, _, _, _, _, te, _ = rp.make_split(X, y, seed=42, train_size=None, test_size=None,
                                             fold=f, n_folds=3)
        seen.append(set(te.tolist()))
    union = set().union(*seen)
    assert len(union) == 300, "folds must cover every row exactly once"
    assert not (seen[0] & seen[1]), "folds must not overlap"


# --------------------------------------------------------------------------
# PR-4 -- matched-inference-context assertion
# --------------------------------------------------------------------------
def test_pr4_matched_context_passes_when_equal(rp):
    per_arm = {
        "A_raw": rp.inference_context_rows("A_raw", 2000),
        "B_in_domain": rp.inference_context_rows("B_in_domain", 2000),
    }
    assert per_arm["A_raw"][0] == per_arm["B_in_domain"][0] == 2000
    assert rp.assert_matched_context(per_arm) is True


def test_pr4_matched_context_raises_on_mismatch(rp):
    """The historic defect: fine-tuned arm with a subsampled context vs a full one."""
    per_arm = {"A_raw": (2000, "full train"), "B_in_domain": (64, "SUBSAMPLE_SAMPLES=64")}
    with pytest.raises(AssertionError) as exc:
        rp.assert_matched_context(per_arm)
    assert "MATCHED-CONTEXT VIOLATION" in str(exc.value)


def test_pr4_context_passes_without_ft_arm(rp):
    """A run of baselines only must not trip the assertion."""
    assert rp.assert_matched_context({"A_raw": (1000, "full"), "E_glm": (None, "n/a")}) is True


# --------------------------------------------------------------------------
# PR-5 -- LODO exclusion assertion
# --------------------------------------------------------------------------
def test_pr5_pool_excludes_target(rp):
    fps = {"a": {"sha256": "1" * 64}, "b": {"sha256": "2" * 64}, "t": {"sha256": "3" * 64}}
    meta = rp.build_pool("t", ["a", "b"], fps)
    assert meta["out_of_pool_asserted"] is True
    assert "t" not in meta["pool_datasets"]
    assert meta["target_sha256"] == "3" * 64


def test_pr5_pool_raises_if_target_in_pool(rp):
    fps = {"a": {"sha256": "1" * 64}, "t": {"sha256": "3" * 64}}
    with pytest.raises(AssertionError) as exc:
        rp.build_pool("t", ["a", "t"], fps)
    assert "LODO VIOLATION" in str(exc.value)


def test_pr5_pool_raises_on_content_hash_collision(rp):
    """Target duplicated under another name must still be caught."""
    fps = {"a": {"sha256": "3" * 64}, "t": {"sha256": "3" * 64}}
    with pytest.raises(AssertionError) as exc:
        rp.build_pool("t", ["a"], fps)
    assert "same content hash" in str(exc.value)


# --------------------------------------------------------------------------
# PR-7 -- epochs as a first-class factor
# --------------------------------------------------------------------------
def test_pr7_epochs_is_the_reported_budget(rp):
    fp = rp.effective_config("B_in_domain", {"epochs": 30, "learning_rate": 1e-5,
                                            "n_estimators": 2, "context_samples": 64})
    assert fp["kwargs"]["epochs"] == 30
    assert "epochs" in fp["passed_params"]


def test_pr7_legacy_context_samples_is_flagged_unused(rp):
    """R1's metadata claimed context_samples was in force; no arm uses it."""
    fp = rp.effective_config("B_in_domain", rp.DEFAULT_CONFIG)
    assert "context_samples" in fp["legacy_config_keys_ignored"]
    assert "context_samples" not in fp["kwargs"]


def test_pr7_raw_arm_reports_no_epochs(rp):
    fp = rp.effective_config("A_raw", rp.DEFAULT_CONFIG)
    assert "epochs" not in fp["kwargs"]
    assert fp["kwargs"]["n_estimators"] == 2


def test_pr7_default_is_r1_parity_and_ladder_reachable(rp):
    """Default stays at 3 for continuity; the ladder {3,10,30} needs no code change."""
    assert rp.DEFAULT_CONFIG["epochs"] == 3
    for e in (3, 10, 30):
        cfg = dict(rp.DEFAULT_CONFIG)
        cfg["epochs"] = e
        assert rp.effective_config("B_in_domain", cfg)["kwargs"]["epochs"] == e


# --------------------------------------------------------------------------
# Metrics -- log loss primary, calibration reported
# --------------------------------------------------------------------------
def test_metrics_include_log_loss_and_calibration(rp):
    y = np.array([0, 0, 1, 1] * 25)
    p = np.clip(y * 0.8 + 0.1, 1e-6, 1 - 1e-6)
    m = rp.compute_metrics(y, p)
    for k in ("roc_auc", "pr_auc", "brier", "log_loss", "ece"):
        assert k in m and np.isfinite(m[k])
    assert 0.0 <= m["ece"] <= 1.0


def test_ece_zero_for_perfect_calibration(rp):
    y = np.array([0] * 50 + [1] * 50)
    p = np.array([0.0] * 50 + [1.0] * 50)
    assert rp.expected_calibration_error(y, p) == pytest.approx(0.0, abs=1e-9)


def test_ece_positive_for_miscalibrated(rp):
    y = np.array([0] * 50 + [1] * 50)
    p = np.full(100, 0.5)  # predicts certainty of nothing; true rate is 0.5 -> ECE 0
    assert rp.expected_calibration_error(y, p) == pytest.approx(0.0, abs=1e-9)
    p2 = np.full(100, 0.9)  # claims 0.9, truth 0.5
    assert rp.expected_calibration_error(y, p2) == pytest.approx(0.4, abs=1e-9)


# --------------------------------------------------------------------------
# PR-1 (provenance) -- the reproducibility inputs that were previously implicit
# --------------------------------------------------------------------------
def test_pf_data_source_url_honours_a_pinned_ref(rp, monkeypatch):
    """A content hash tells you a file CHANGED; only a pinned ref lets you get it back."""
    assert "/main/" in rp.data_source_url("coil2000.csv")
    monkeypatch.setenv("TFM_DATA_REF", "deadbeef")
    monkeypatch.setattr(rp, "DATA_REF", "deadbeef")
    pinned = rp.data_source_url("coil2000.csv")
    assert "/deadbeef/" in pinned and "/main/" not in pinned


def test_pf_fingerprint_records_where_the_bytes_came_from(rp):
    fp = rp.dataset_fingerprint("coil2000")
    if not fp.get("exists", True):
        pytest.skip("dataset not present locally")
    assert fp["source_url"].endswith("/data/raw/coil2000.csv")
    assert fp["source_ref"] == rp.DATA_REF
    # `main` is a moving branch, so the flag must say so rather than imply a pin.
    assert fp["source_ref_is_pinned"] is (rp.DATA_REF != "main")


def test_pf_versions_record_the_packages_that_change_results(rp):
    """sklearn/pandas change RESULTS; catboost decides whether arm F is even CatBoost."""
    v = rp._runtime_versions()
    for key in ("python", "torch", "numpy", "tabpfn", "scikit-learn", "pandas", "catboost"):
        assert key in v, f"{key} must be recorded"
    assert v["scikit-learn"] is not None, "sklearn drives split, scaler, GLM and metrics"


def test_weights_provenance_is_null_safe_without_the_env(rp, monkeypatch):
    """Absent the fetch step (e.g. a local run) this must record nulls, not raise."""
    monkeypatch.delenv("TFM_WEIGHTS_MANIFEST", raising=False)
    w = rp._weights_provenance()
    assert w["sha256"] is None and w["path"] is None
    assert w["manifest_file"] is None


def test_weights_provenance_reads_the_checkpoint_hash(rp, monkeypatch, tmp_path):
    """The hash must reach the audit record, not stop at the log."""
    f = tmp_path / "weights.json"
    f.write_text(
        json.dumps(
            {
                "target_path": "/root/.cache/tabpfn/tabpfn-v3-classifier-v3_default.ckpt",
                "sha256": "a" * 64,
                "bytes": 212800000,
                "cached": False,
                "downloaded": True,
                "repo_id": "Prior-Labs/tabpfn_3",
            }
        )
    )
    monkeypatch.setenv("TFM_WEIGHTS_MANIFEST", str(f))
    w = rp._weights_provenance()
    assert w["sha256"] == "a" * 64
    assert w["bytes"] == 212800000
    assert w["downloaded"] is True
    assert w["source"] == "Prior-Labs/tabpfn_3"


def test_container_provenance_carries_the_image(rp, monkeypatch):
    """The image is chosen at run time from host CUDA -- it must be recorded."""
    monkeypatch.setenv("TFM_IMAGE_REF", "pytorch/pytorch:2.7.0-cuda12.8-cudnn9-runtime")
    monkeypatch.setenv("TFM_RUN_STAMP", "20260912T230000Z")
    monkeypatch.setenv("TFM_MACHINE_ID", "555001")
    monkeypatch.setenv("TFM_HOST_ID", "777001")
    c = rp._container_provenance()
    assert c["image_ref"].endswith("cudnn9-runtime")
    assert c["run_stamp"] == "20260912T230000Z"
    assert c["machine_id"] == "555001"


def test_container_provenance_empty_is_null_not_missing(rp, monkeypatch):
    monkeypatch.setenv("TFM_MACHINE_ID", "")
    c = rp._container_provenance()
    assert c["machine_id"] is None


def test_per_arm_record_carries_the_new_provenance(rp, tmp_path, monkeypatch):
    """Weights hash, container, and the ACTUAL estimator class, per arm."""
    monkeypatch.setenv("TFM_IMAGE_REF", "img:test")
    monkeypatch.delenv("TFM_WEIGHTS_MANIFEST", raising=False)
    y = np.random.default_rng(0).random(10)
    meta = rp.save_results(
        "ds",
        "F_catboost",
        {"log_loss": 0.5, "roc_auc": 0.7, "ece": 0.01, "brier": 0.1, "pr_auc": 0.2},
        y,
        (y > 0.5).astype(int),
        1.23,
        dict(rp.DEFAULT_CONFIG),
        tmp_path,
        seed=42,
        fold=None,
        n_folds=None,
        split_fp={"n_train": 5, "n_test": 5},
        dataset_fp={"name": "ds"},
        arm_fp={"arm": "F_catboost"},
        context_rows=None,
        context_note="n/a",
        estimator_class="sklearn.ensemble._forest.RandomForestClassifier",
    )
    assert meta["container"]["image_ref"] == "img:test"
    assert meta["weights"]["sha256"] is None
    # A RandomForest under the label F_catboost must be visible in the record.
    assert meta["estimator_class"].endswith("RandomForestClassifier")


# --------------------------------------------------------------------------
# Incomplete runs: both states must be STATED, never inferred from a gap
# --------------------------------------------------------------------------
def test_pf_failed_arm_is_recorded_not_silent(rp, tmp_path):
    """An arm that raises must leave a record in its own slot."""
    fr = rp.save_failure_record(
        tmp_path, "coil2000", "B_in_domain", 42, None, dict(rp.DEFAULT_CONFIG),
        RuntimeError("Invalid forward pass"), 12.5,
    )
    assert fr.name == "meta.FAILED.json"
    assert fr.parent == tmp_path / "coil2000" / "B_in_domain"
    d = json.loads(fr.read_text())
    assert d["status"] == "failed"
    assert d["arm"] == "B_in_domain" and d["dataset"] == "coil2000"
    assert "Invalid forward pass" in d["error"]
    assert d["error_type"] == "RuntimeError"
    assert d["elapsed_seconds"] == 12.5


def test_pf_failure_record_cannot_overwrite_a_success(rp, tmp_path):
    """The failure filename must never collide with the success record."""
    slot = tmp_path / "ds" / "A_raw"
    slot.mkdir(parents=True)
    (slot / "meta.json").write_text('{"status": "ok"}')
    rp.save_failure_record(tmp_path, "ds", "A_raw", 1, None, {}, ValueError("boom"), 1.0)
    assert (slot / "meta.json").read_text() == '{"status": "ok"}'
    assert (slot / "meta.FAILED.json").exists()


def test_pf_failure_record_uses_the_seed_fold_slot(rp, tmp_path):
    fr = rp.save_failure_record(tmp_path, "ds", "A_raw", 7, 2, {}, ValueError("x"), 1.0)
    assert fr.parent == tmp_path / "ds" / "A_raw" / "seed7_fold2"


def test_pf_a_killed_run_is_detectable(rp, tmp_path, capsys):
    """The OOM case: process died, so the manifest never got past status=running."""
    (tmp_path / "manifest_20260912T230000Z.json").write_text(
        json.dumps({"run_id": "20260912T230000Z", "status": "running", "pid": 4242})
    )
    rep = rp.report_incomplete(tmp_path)
    assert rep["incomplete_runs"], "a run still marked 'running' is an incomplete run"
    assert rep["incomplete_runs"][0][0] == "20260912T230000Z"
    out = capsys.readouterr().out
    assert "INCOMPLETE RUNS" in out


def test_pf_failed_arms_are_surfaced(rp, tmp_path, capsys):
    rp.save_failure_record(tmp_path, "coil2000", "B_in_domain", 42, None, {}, OSError("oom"), 3.0)
    rep = rp.report_incomplete(tmp_path)
    assert rep["failed_arms"] and rep["failed_arms"][0][1] == "B_in_domain"
    assert "FAILED ARMS" in capsys.readouterr().out


def test_pf_a_clean_run_reports_clean(rp, tmp_path, capsys):
    (tmp_path / "manifest_ok.json").write_text(json.dumps({"run_id": "ok", "status": "success"}))
    (tmp_path / "ds" / "A_raw").mkdir(parents=True)
    (tmp_path / "ds" / "A_raw" / "meta.json").write_text("{}")
    rep = rp.report_incomplete(tmp_path)
    assert rep == {"incomplete_runs": [], "failed_arms": []}
    assert "no incomplete runs, no failed arms" in capsys.readouterr().out


def test_pf_manifest_is_written_before_the_arms_run(rp):
    """The crash-safety invariant, asserted against the source order.

    A manifest written only in `finally` is absent whenever the process is killed (an
    OOM takes the interpreter down without unwinding), which is precisely how R1's runs
    vanished. The write must precede the first arm.
    """
    src = Path(rp.__file__).read_text()
    write_at = src.index("manifest[\"pid\"] = os.getpid()")
    run_at = src.index("    try:\n        if args.dataset:", write_at)
    assert write_at < run_at, "manifest must be written BEFORE the arms are dispatched"


# --------------------------------------------------------------------------
# PR-1 -- manifest shape
# --------------------------------------------------------------------------
def test_pr1_git_and_host_info_present(rp):
    g = rp._git_info()
    assert "commit_sha" in g and "branch" in g and "dirty" in g
    h = rp._host_info()
    assert "hostname" in h and "gpu_count" in h


# --------------------------------------------------------------------------
# PR-9 -- pre-fetch the gated weights so the licence gate moves off the run path
# --------------------------------------------------------------------------
def _load_fetch_weights():
    spec = importlib.util.spec_from_file_location(
        "fetch_weights", REPO_ROOT / "scripts" / "gpu_helpers" / "fetch_weights.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def fw():
    return _load_fetch_weights()


def test_pr9_sha256_matches_hashlib(fw, tmp_path):
    import hashlib

    p = tmp_path / "blob.bin"
    payload = b"tabpfn-weights-stand-in" * 1000
    p.write_bytes(payload)
    digest, size = fw._sha256_file(p)
    assert digest == hashlib.sha256(payload).hexdigest()
    assert size == len(payload)


def test_pr9_cache_dir_resolves_to_a_path(fw):
    cache_dir, how = fw.resolve_cache_dir()
    assert isinstance(cache_dir, Path)
    assert how  # names the mechanism used, so the manifest can record it
    assert cache_dir.name == "tabpfn"


def test_pr9_source_is_the_gated_v3_classifier(fw):
    """Must resolve to the gated v3 repo -- the versions that skip the gate are useless."""
    repo_id, filename, how = fw.resolve_source()
    assert repo_id == "Prior-Labs/tabpfn_3"
    assert filename == "tabpfn-v3-classifier-v3_default.ckpt"
    assert how  # either the library or the documented fallback


def test_pr9_check_only_reports_state_without_downloading(fw, monkeypatch, capsys, tmp_path):
    """--check-only must never download; it reports and exits non-zero if absent."""
    monkeypatch.setattr(fw, "resolve_cache_dir", lambda: (tmp_path, "test"))
    monkeypatch.setattr(
        fw, "resolve_source", lambda: (fw.DEFAULT_REPO, fw.DEFAULT_FILENAME, "test")
    )
    monkeypatch.setattr(sys, "argv", ["fetch_weights.py", "--check-only"])
    rc = fw.main()
    out = capsys.readouterr().out
    assert rc == 1, "a cold cache must exit non-zero so callers can branch"
    assert fw.MARKER in out
    assert '"cached": false' in out
    assert '"licence_gate_will_fire": true' in out
    assert not (tmp_path / fw.DEFAULT_FILENAME).exists()


def test_pr9_cached_weights_report_no_gate_and_exit_zero(fw, monkeypatch, capsys, tmp_path):
    """A warm cache is the whole point: gate will not fire, exit 0, hash recorded."""
    blob = tmp_path / fw.DEFAULT_FILENAME
    blob.write_bytes(b"cached-checkpoint" * 100)
    monkeypatch.setattr(fw, "resolve_cache_dir", lambda: (tmp_path, "test"))
    monkeypatch.setattr(
        fw, "resolve_source", lambda: (fw.DEFAULT_REPO, fw.DEFAULT_FILENAME, "test")
    )
    monkeypatch.setattr(sys, "argv", ["fetch_weights.py", "--check-only"])
    rc = fw.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert '"cached": true' in out
    assert '"licence_gate_will_fire": false' in out
    assert '"sha256": "' in out  # the weights ID the manifest needs
    assert '"downloaded": false' in out
