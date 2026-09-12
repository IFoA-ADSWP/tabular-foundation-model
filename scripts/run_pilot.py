#!/usr/bin/env python3
"""
Fine-tuning pilot: step-by-step execution for CLI.

Usage:
    python scripts/run_pilot.py                          # all datasets, all arms, default config
    python scripts/run_pilot.py --dataset coil2000       # one dataset
    python scripts/run_pilot.py --aggregate              # aggregate results
    python scripts/run_pilot.py --epochs 30              # epoch ladder (library default is 30)
    python scripts/run_pilot.py --seeds 42,43,44 --folds 5
    python scripts/run_pilot.py --rung P1c               # scale rung (see RUNG presets)

Pilot 2 additions (see docs/reports/PILOT_2_PREREQUISITES.md):
  PR-1  run manifest written per invocation and per arm
  PR-3  fine-tuned weights saved + sha256 (--save-models)
  PR-4  matched-inference-context assertion between the two TabPFN arms
  PR-5  LODO exclusion assertion for pooled/transfer arms
  PR-6  dataset and split fingerprints (sha256 + index hash)
  PR-7  `epochs` as a first-class, recorded factor
"""
import sys
import os
import json
import time
import hashlib
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    roc_auc_score,
    brier_score_loss,
    average_precision_score,
    log_loss,
    f1_score,
)

# Ensure repo imports work (handle both __file__ and piped execution)
if "__file__" in dir():
    REPO_ROOT = Path(__file__).resolve().parents[1]
else:
    REPO_ROOT = Path(os.getcwd())
sys.path.insert(0, str(REPO_ROOT))

SCHEMA_VERSION = 2

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
# `epochs` is the real fine-tuning budget. The shipped trainer's default is 30;
# we default to 3 to preserve R1 parity, and the ladder is {3, 10, 30}.
#
# `context_samples` is LEGACY: it was never a TabPFN parameter and is used by
# NEITHER arm. Arm A fits on all training rows; arm B's trainer subsamples via
# `n_finetune_ctx_plus_query_samples` (default 50000, inert at our sizes). It is
# retained only so the record can show it was carried forward and is unused --
# see FINE_TUNING_PILOT_RESULTS.md §5d.4.
DEFAULT_CONFIG = {
    "epochs": 3,
    "n_estimators": 2,
    "learning_rate": 1e-5,
    "fit_mode": "batched",
    "context_samples": 64,  # UNUSED by both arms -- recorded as such
}

LEGACY_UNUSED_KEYS = ("context_samples",)

# Scale rungs (PILOT_2_DESIGN.md §4.3). None = use the file as-is (full).
RUNG = {
    "P1a": {"train_size": 2000, "test_size": 1000},
    "P1b": {"train_size": 5000, "test_size": 2000},
    "P1c": {"train_size": None, "test_size": None},  # full data
}

DEFAULT_SEED = 42
SEEDS = [DEFAULT_SEED]
TRAIN_SIZE = 2000
TEST_SIZE = 1000

DATASETS = {
    "coil2000": {"file": "coil2000.csv", "target": "CARAVAN"},
    "uslapseagent": {"file": "uslapseagent.csv", "target": "surrender"},
    "eudirectlapse": {"file": "eudirectlapse.csv", "target": "lapse"},
    "spanish_motor_lapse": {"file": "spanish_motor_lapse.csv", "target": "LapseB"},
}

DATA_DIR = REPO_ROOT / "data" / "raw"
OUTPUT_DIR = REPO_ROOT / "outputs" / "finetune" / "pilot"

# Which arms are fine-tuning arms (subject to the matched-context assertion).
FT_ARMS = ("B_in_domain", "B_ft3", "B_ft10", "B_ft30", "C_pooled_all", "D_pooled_homog")
BASELINE_TABPFN_ARM = "A_raw"


# ---------------------------------------------------------------------------
# Fingerprints, versions, hashes  (PR-6, PR-1)
# ---------------------------------------------------------------------------
def _sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _sha256_array(arr):
    a = np.ascontiguousarray(arr)
    return hashlib.sha256(a.tobytes()).hexdigest()


def _git_info():
    def run(*args):
        try:
            return subprocess.run(
                ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, timeout=10
            ).stdout.strip()
        except Exception:
            return None

    return {
        "branch": run("rev-parse", "--abbrev-ref", "HEAD"),
        "commit_sha": run("rev-parse", "HEAD"),
        "dirty": bool(run("status", "--porcelain")),
    }


def _host_info():
    info = {
        "hostname": os.uname().nodename,
        "cpu_ram_gb": None,
        "gpu_count": 0,
    }
    try:
        if hasattr(os, "sysconf") and "SC_PAGE_SIZE" in dir(os):
            info["cpu_ram_gb"] = round(
                os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1e9, 1
            )
    except Exception:
        pass
    if torch.cuda.is_available():
        info.update(
            {
                "gpu_count": torch.cuda.device_count(),
                "gpu_name": torch.cuda.get_device_name(0),
                "vram_gb": round(torch.cuda.get_device_properties(0).total_memory / 1e9, 1),
                "cuda_version": getattr(torch.version, "cuda", None),
            }
        )
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
        if out:
            info["driver_version"] = out.splitlines()[0]
    except Exception:
        pass
    return info


def dataset_fingerprint(name):
    """Content hash + shape + class balance for a dataset (PR-6)."""
    path = DATA_DIR / f"{name}.csv"
    if not path.exists():
        return {"name": name, "path": str(path), "exists": False}
    df = pd.read_csv(path)
    target = DATASETS[name]["target"]
    y = df[target].astype(int)
    return {
        "name": name,
        "path": str(path.relative_to(REPO_ROOT)),
        "file": f"{name}.csv",
        "sha256": _sha256_file(path),
        "n_rows": int(len(df)),
        "n_cols": int(df.shape[1]),
        "columns": list(df.columns),
        "target_col": target,
        "positive_rate": round(float(y.mean()), 6),
        "n_positive": int(y.sum()),
    }


def _checkpoints():
    """Record the checkpoint file(s) actually on disk.

    docs/MODEL_VERSIONS.md requires the weights ID, not just the pip version:
    "tabpfn==2.6.0 is the pip package, not the model." The resolved cache file
    is the only reliable proof of which weights ran.
    """
    roots = [
        Path.home() / ".cache" / "tabpfn",
        Path.home() / "Library" / "Caches" / "tabpfn",
    ]
    found = []
    for root in roots:
        if root.is_dir():
            found += sorted(p.name for p in root.glob("*.ckpt"))
    return found


def _runtime_versions():
    """Record the stack that produced a result.

    TabPFN changes its default checkpoint and fine-tuning API across majors,
    so a metric without the producing version is not reproducible.
    """
    import platform

    versions = {
        "python": platform.python_version(),
        "torch": torch.__version__,
        "numpy": np.__version__,
    }
    for mod_name, key in (("tabpfn", "tabpfn"), ("sklearn", "scikit-learn")):
        try:
            versions[key] = getattr(__import__(mod_name), "__version__", "unknown")
        except Exception:
            versions[key] = None
    return versions


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
def download_file(filename, repo="IFoA-ADSWP/tabular-foundation-model"):
    url = f"https://raw.githubusercontent.com/{repo}/main/data/raw/{filename}"
    dest = DATA_DIR / filename
    if dest.exists():
        return True
    print(f"Downloading {filename}...", end=" ", flush=True)
    import urllib.request

    try:
        urllib.request.urlretrieve(url, dest)
        print("OK")
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        return False


def check_data():
    missing = []
    for name, info in DATASETS.items():
        path = DATA_DIR / info["file"]
        if not path.exists():
            missing.append(info["file"])
    if missing:
        print(f"Missing data files: {missing}")
        print("Downloading from GitHub...")
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        for f in missing:
            download_file(f)
        still_missing = []
        for name, info in DATASETS.items():
            if not (DATA_DIR / info["file"]).exists():
                still_missing.append(info["file"])
        if still_missing:
            print(f"ERROR: Could not download: {still_missing}")
            return False
    return True


def load_dataset(name, target_col, max_rows=None):
    """Load and encode a dataset.

    Note (PR-6): the row cap is a *uniform* sample, not stratified, so the sampled
    class balance can differ from the population. This is recorded in the
    fingerprint rather than hidden.
    """
    path = DATA_DIR / f"{name}.csv"
    df = pd.read_csv(path)
    sampled = False
    if max_rows is not None and len(df) > max_rows:
        df = df.sample(n=max_rows, random_state=DEFAULT_SEED)
        sampled = True
    y = df[target_col].values.astype(int)
    X = (
        pd.get_dummies(df.drop(columns=[target_col]), drop_first=False)
        .fillna(0)
        .values.astype(np.float64)
    )
    return X, y, {"row_cap": max_rows, "row_cap_applied": sampled, "rows_loaded": int(len(df))}


def make_split(X, y, *, seed, train_size, test_size, fold=None, n_folds=None):
    """Produce a train/test split plus its fingerprint (PR-6).

    Two modes:
      * fold is None  -> single holdout split, train_size/test_size honoured
      * fold is given -> StratifiedKFold on all rows; train_size/test_size ignored
    """
    if fold is not None:
        skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=seed)
        folds = list(skf.split(X, y))
        train_idx, test_idx = folds[fold]
    else:
        n_test = test_size if test_size is not None else max(int(0.3 * len(y)), 1)
        idx_all = np.arange(len(y))
        train_idx, test_idx = train_test_split(
            idx_all, test_size=n_test, random_state=seed, stratify=y
        )
        if train_size is not None and len(train_idx) > train_size:
            train_idx, _ = train_test_split(
                train_idx,
                train_size=train_size,
                random_state=seed,
                stratify=y[train_idx],
            )

    train_idx = np.sort(np.asarray(train_idx))
    test_idx = np.sort(np.asarray(test_idx))
    fp = {
        "policy": "stratified_kfold" if fold is not None else "holdout_then_train_cap",
        "seed": seed,
        "fold": fold,
        "n_folds": n_folds,
        "n_train": int(len(train_idx)),
        "n_test": int(len(test_idx)),
        "pos_train": int(y[train_idx].sum()),
        "pos_test": int(y[test_idx].sum()),
        "train_index_sha256": _sha256_array(train_idx),
        "test_index_sha256": _sha256_array(test_idx),
        "test_rows_excluded_from_fit": True,
    }
    return X[train_idx], X[test_idx], y[train_idx], y[test_idx], train_idx, test_idx, fp


# ---------------------------------------------------------------------------
# Metrics  (log loss primary, per PILOT_2_DESIGN.md §3)
# ---------------------------------------------------------------------------
def expected_calibration_error(y_true, y_prob, n_bins=10):
    """Expected calibration error, equal-width bins."""
    y_true = np.asarray(y_true, dtype=float)
    y_prob = np.asarray(y_prob, dtype=float)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    idx = np.clip(np.digitize(y_prob, edges[1:-1], right=True), 0, n_bins - 1)
    ece = 0.0
    n = len(y_true)
    for b in range(n_bins):
        m = idx == b
        if not m.any():
            continue
        ece += (m.sum() / n) * abs(y_true[m].mean() - y_prob[m].mean())
    return float(ece)


def compute_metrics(y_true, y_prob):
    return {
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
        "brier": float(brier_score_loss(y_true, y_prob)),
        "pr_auc": float(average_precision_score(y_true, y_prob)),
        "log_loss": float(log_loss(y_true, np.clip(y_prob, 1e-15, 1 - 1e-15))),
        "ece": expected_calibration_error(y_true, y_prob),
    }


# ---------------------------------------------------------------------------
# Effective configuration + matched context  (PR-4, PR-7)
# ---------------------------------------------------------------------------
def effective_config(arm, config):
    """Return the kwargs an arm will actually use, and the provenance of each.

    Guards the defect that made R1's metadata misleading: the same config dict was
    written for every arm, including keys no arm used.
    """
    kwargs, passed = {}, []

    if arm == BASELINE_TABPFN_ARM:
        kwargs = {
            "ignore_pretraining_limits": True,
            "n_estimators": config["n_estimators"],
            "fit_mode": config["fit_mode"],
            "inference_precision": "float32",
        }
        passed = ["n_estimators", "fit_mode"]
    elif arm in FT_ARMS:
        kwargs = {
            "epochs": config["epochs"],  # PR-7: the real budget
            "learning_rate": config["learning_rate"],
            "n_estimators_finetune": config["n_estimators"],
        }
        passed = ["epochs", "learning_rate", "n_estimators"]

    defaulted = [k for k in kwargs if k not in passed]
    unused = [k for k in LEGACY_UNUSED_KEYS if k in config]
    return {
        "arm": arm,
        "kwargs": kwargs,
        "passed_params": passed,
        "library_defaulted_params": defaulted,
        "legacy_config_keys_ignored": unused,
        "source_config": dict(config),
    }


def inference_context_rows(arm, n_train):
    """Effective inference context for an arm, and the mechanism behind it.

    This is what the historic study got wrong: the fine-tuned arm there was
    evaluated with SUBSAMPLE_SAMPLES=64/128 while the raw arm used the whole
    training split. In the shipped trainer the inference model is refit on the
    full training data (`_setup_inference_model` -> `fit(self.X_, self.y_)`), so
    both arms carry the full training split as context.
    """
    if arm == BASELINE_TABPFN_ARM:
        return n_train, "TabPFNClassifier.fit(X_train) -- full training split"
    if arm in FT_ARMS:
        return n_train, "FinetunedTabPFNClassifier refits inference on full X_ (shipped trainer)"
    return None, "not a TabPFN context-carrying arm"


def assert_matched_context(per_arm):
    """Refuse to compare TabPFN arms whose inference contexts differ (PR-4)."""
    a = per_arm.get(BASELINE_TABPFN_ARM)
    if a is None or a[0] is None:
        return True
    ft = {k: v for k, v in per_arm.items() if k in FT_ARMS and v[0] is not None}
    if not ft:
        return True
    mismatched = {k: v[0] for k, v in ft.items() if v[0] != a[0]}
    if mismatched:
        raise AssertionError(
            "MATCHED-CONTEXT VIOLATION: raw arm context="
            f"{a[0]} but {mismatched} differ. The historic comparison was invalidated "
            "by exactly this; fix the context before reporting any delta."
        )
    return True


# ---------------------------------------------------------------------------
# Pool construction  (PR-5)
# ---------------------------------------------------------------------------
def build_pool(target, pool_names, fingerprints):
    """Build a LODO pool for `target`, asserting the target is absent (PR-5).

    A transfer result is only meaningful if the target was provably not in the pool
    that trained the model. Asserted by name AND by content hash, in code.
    """
    if target in pool_names:
        raise AssertionError(
            f"LODO VIOLATION: target '{target}' appears in its own pool {pool_names}"
        )
    tfp = fingerprints.get(target, {}).get("sha256")
    overlap = [
        n
        for n in pool_names
        if tfp is not None and fingerprints.get(n, {}).get("sha256") == tfp
    ]
    if overlap:
        raise AssertionError(
            f"LODO VIOLATION: pool member(s) {overlap} have the same content hash as "
            f"target '{target}'"
        )
    return {
        "policy": "leave_one_dataset_out",
        "target": target,
        "pool_datasets": list(pool_names),
        "out_of_pool_asserted": True,
        "target_sha256": tfp,
    }


# ---------------------------------------------------------------------------
# Arms
# ---------------------------------------------------------------------------
def run_arm_a_raw(X_train, X_test, y_train, y_test, config):
    from tabpfn import TabPFNClassifier

    clf = TabPFNClassifier(
        ignore_pretraining_limits=True,
        device="cuda" if torch.cuda.is_available() else "cpu",
        n_estimators=config["n_estimators"],
        random_state=DEFAULT_SEED,
        inference_precision=torch.float32,
        fit_mode=config["fit_mode"],
    )
    clf.fit(X_train, y_train)
    probs = clf.predict_proba(X_test)[:, 1]
    return probs, clf


def run_arm_b_in_domain(X_train, X_test, y_train, y_test, config):
    """Arm B: TabPFN fine-tuned on this dataset's own training split.

    Uses the SHIPPED fine-tuner rather than driving the model by hand. The
    hand-rolled version this replaces called ``clf.fit_from_preprocessed`` in a
    loop and then ``clf.predict_proba``, which raises:

        Invalid forward pass: Bad combination of inference mode
        (use_inference_mode=True), input X, or executor type
        (InferenceEngineBatchedNoPreprocessing)

    The model was left in batched-executor mode, which cannot serve a standard
    predict. It failed on all four datasets in 2-5 s with 50.8 GB of VRAM free,
    so arm B's long-standing "does not fit" story was never memory -- it was this
    call sequence.

    The old code also carried two silent-failure traps, both removed by using the
    library's own trainer:

    * ``optimizer = Adam(clf.model_.parameters()) if hasattr(clf, "model_") else
      None`` -- ``model_`` is created by ``_initialize_model_variables()``, which
      was itself called inside a bare ``except Exception: pass``. A failure there
      left ``optimizer=None``, so the loop called the fit method but took NO
      gradient step, and the arm would have reported numbers for a model that was
      never fine-tuned.
    * the loss/backward/step block was wrapped in ``except Exception: pass``,
      hiding any error in the one part of the arm that actually learns.

    CONFIG MAPPING -- PR-7 replaced the old `max_finetune_steps -> epochs` alias
    with a real `epochs` parameter. The library default is 30; R1 ran 3.

    Still a faithful record of what is NOT applied:
        context_samples -> not a TabPFN parameter; ignored by both arms.
    """
    from tabpfn.finetuning.finetuned_classifier import FinetunedTabPFNClassifier

    clf = FinetunedTabPFNClassifier(
        device="cuda" if torch.cuda.is_available() else "cpu",
        epochs=config["epochs"],
        learning_rate=config["learning_rate"],
        n_estimators_finetune=config["n_estimators"],
        random_state=DEFAULT_SEED,
    )
    clf.fit(X_train, y_train)
    probs = clf.predict_proba(X_test)[:, 1]
    return probs, clf


def run_arm_e_glm(X_train, X_test, y_train, y_test, config=None):
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)
    clf = LogisticRegression(max_iter=1000, random_state=DEFAULT_SEED)
    clf.fit(X_train_s, y_train)
    probs = clf.predict_proba(X_test_s)[:, 1]
    return probs, clf


def run_arm_f_catboost(X_train, X_test, y_train, y_test, config=None):
    try:
        from catboost import CatBoostClassifier

        clf = CatBoostClassifier(iterations=200, verbose=0, random_state=DEFAULT_SEED)
        clf.fit(X_train, y_train)
        probs = clf.predict_proba(X_test)[:, 1]
        return probs, clf
    except ImportError:
        clf = RandomForestClassifier(n_estimators=100, random_state=DEFAULT_SEED)
        clf.fit(X_train, y_train)
        probs = clf.predict_proba(X_test)[:, 1]
        return probs, clf


ARMS = {
    "A_raw": run_arm_a_raw,
    "B_in_domain": run_arm_b_in_domain,
    "E_glm": run_arm_e_glm,
    "F_catboost": run_arm_f_catboost,
}


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
def save_model_artifact(clf, run_dir, arm):
    """Save the fitted model with a hash, or record why it could not be saved (PR-3)."""
    out = {"model_path": None, "model_sha256": None, "model_saved": False, "model_save_note": None}
    if clf is None:
        out["model_save_note"] = "no estimator object returned"
        return out
    try:
        from tabpfn import save_fitted_tabpfn_model

        path = run_dir / f"{arm}.tabpfn_fit"
        save_fitted_tabpfn_model(clf, path)
        if path.exists():
            out.update(
                {
                    "model_path": path.name,
                    "model_sha256": _sha256_file(path),
                    "model_saved": True,
                }
            )
        else:
            out["model_save_note"] = "save call returned but no file appeared"
    except Exception as e:  # recorded, never silent
        out["model_save_note"] = f"{type(e).__name__}: {e}"
    return out


def save_results(
    dataset,
    arm,
    metrics,
    y_prob,
    y_test,
    run_time,
    config,
    output_dir,
    *,
    seed,
    fold,
    n_folds,
    split_fp,
    dataset_fp,
    arm_fp,
    context_rows,
    context_note,
    extra=None,
    model_info=None,
):
    """Write one arm-run record. Layout is legacy-compatible for the single-split case."""
    if fold is None and seed == DEFAULT_SEED:
        run_dir = output_dir / dataset / arm
    else:
        run_dir = output_dir / dataset / arm / f"seed{seed}_fold{fold}"
    run_dir.mkdir(parents=True, exist_ok=True)

    np.save(run_dir / "predictions.npy", y_prob)
    np.save(run_dir / "ground_truth.npy", y_test)

    run_id = f"{dataset}_{arm}_seed{seed}" + (f"_fold{fold}" if fold is not None else "")

    meta = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "dataset": dataset,
        "arm": arm,
        "seed": seed,
        "fold": fold,
        "n_folds": n_folds,
        "train_rows": split_fp["n_train"],
        "test_rows": split_fp["n_test"],
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
        "run_time_seconds": run_time,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "success",
        "versions": _runtime_versions(),
        "checkpoints": _checkpoints(),
        # PR-4: effective inference context, per arm
        "inference_context": {"rows": context_rows, "mechanism": context_note},
        # PR-6
        "dataset_fingerprint": dataset_fp,
        "split_fingerprint": split_fp,
        "predictions_sha256": _sha256_array(y_prob),
        # PR-1 / PR-7: what this arm actually used
        "effective_config": arm_fp,
        # legacy key retained so existing readers do not break
        "config": dict(config),
        **metrics,
    }
    if model_info:
        meta.update(model_info)
    if extra:
        meta.update(extra)

    with open(run_dir / "meta.json", "w") as f:
        json.dump(meta, f, indent=2, default=str)

    return meta


def write_run_manifest(manifest, output_dir):
    """Write the invocation-level manifest (PR-1)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    rid = manifest["run_id"]
    path = output_dir / f"manifest_{rid}.json"
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2, default=str)
    print(f"\n[manifest] {path}")
    return path


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def run_single_dataset(
    ds_name,
    arms=None,
    *,
    config=None,
    seeds=None,
    folds=None,
    train_size=TRAIN_SIZE,
    test_size=TEST_SIZE,
    save_models=False,
    fingerprints=None,
    run_ctx=None,
):
    """Run the selected arms for one dataset across seeds/folds.

    `arms` exists so the driver can run one arm per subprocess. A kernel
    OOM-kill takes down the whole interpreter, so arms sharing a process
    cannot be isolated with try/except -- the `except Exception` below never
    runs when the OOM killer fires.
    """
    config = config or dict(DEFAULT_CONFIG)
    seeds = seeds or [DEFAULT_SEED]
    arms = list(ARMS) if arms is None else arms

    if ds_name not in DATASETS:
        print(f"ERROR: Unknown dataset '{ds_name}'. Choose from: {list(DATASETS.keys())}")
        return []

    print(f"\n--- {ds_name} ({DATASETS[ds_name]['file']}) ---")
    max_rows = (train_size + test_size + 500) if (train_size and test_size) else None
    X, y, load_info = load_dataset(ds_name, DATASETS[ds_name]["target"], max_rows=max_rows)

    dataset_fp = (fingerprints or {}).get(ds_name) or dataset_fingerprint(ds_name)
    dataset_fp = dict(dataset_fp)
    dataset_fp["rows_used"] = int(len(y))
    dataset_fp["load_info"] = load_info
    dataset_fp["pos_rate_used"] = round(float(y.mean()), 6)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []

    for seed in seeds:
        fold_list = [None] if not folds else list(range(folds))
        for fold in fold_list:
            X_tr, X_te, y_tr, y_te, tr_idx, te_idx, split_fp = make_split(
                X,
                y,
                seed=seed,
                train_size=train_size,
                test_size=test_size,
                fold=fold,
                n_folds=folds,
            )

            from sklearn.preprocessing import StandardScaler

            scaler = StandardScaler()
            X_tr_s = scaler.fit_transform(X_tr)
            X_te_s = scaler.transform(X_te)

            # PR-4: work out every arm's effective context BEFORE running, so a
            # mismatch is caught rather than reported.
            per_arm_ctx = {
                a: inference_context_rows(a, split_fp["n_train"]) for a in arms
            }
            assert_matched_context(per_arm_ctx)

            tag = f"seed{seed}" + (f"/fold{fold}" if fold is not None else "")
            print(f"  [{tag}] train={split_fp['n_train']} test={split_fp['n_test']}")

            for arm_name in arms:
                arm_fn = ARMS.get(arm_name)
                if arm_fn is None:
                    print(f"    {arm_name}... SKIPPED (unknown arm)")
                    continue
                arm_fp = effective_config(arm_name, config)
                ctx_rows, ctx_note = per_arm_ctx.get(arm_name, (None, None))
                print(f"    {arm_name}...", end=" ", flush=True)
                start = time.time()
                try:
                    probs, clf = arm_fn(X_tr_s, X_te_s, y_tr, y_te, config)
                    elapsed = time.time() - start
                    if probs is None:
                        print(f"FAILED ({elapsed:.1f}s)")
                        continue
                    metrics = compute_metrics(y_te, probs)

                    run_dir = (
                        OUTPUT_DIR / ds_name / arm_name
                        if (fold is None and seed == DEFAULT_SEED)
                        else OUTPUT_DIR / ds_name / arm_name / f"seed{seed}_fold{fold}"
                    )
                    run_dir.mkdir(parents=True, exist_ok=True)
                    model_info = (
                        save_model_artifact(clf, run_dir, arm_name)
                        if save_models
                        else {"model_saved": False, "model_save_note": "not requested (--save-models)"}
                    )

                    meta = save_results(
                        ds_name,
                        arm_name,
                        metrics,
                        probs,
                        y_te,
                        elapsed,
                        config,
                        OUTPUT_DIR,
                        seed=seed,
                        fold=fold,
                        n_folds=folds,
                        split_fp=split_fp,
                        dataset_fp=dataset_fp,
                        arm_fp=arm_fp,
                        context_rows=ctx_rows,
                        context_note=ctx_note,
                        model_info=model_info,
                    )
                    meta["_split_index_hash"] = split_fp["train_index_sha256"][:12]
                    results.append(meta)
                    print(
                        f"logloss={metrics['log_loss']:.4f} ROC={metrics['roc_auc']:.4f} "
                        f"ECE={metrics['ece']:.4f} ({elapsed:.1f}s)"
                    )
                except Exception as e:
                    elapsed = time.time() - start
                    print(f"ERROR: {type(e).__name__}: {e} ({elapsed:.1f}s)")

    return results


def aggregate_results(output_dir=None):
    """Aggregate all arm-run records into pilot_metrics.parquet.

    Globs recursively, so both the legacy `<dataset>/<arm>/meta.json` layout and
    the multi-seed `<dataset>/<arm>/seed*/fold*/meta.json` layout are collected.
    """
    output_dir = output_dir or OUTPUT_DIR
    print("\n" + "=" * 70)
    print("PILOT RESULTS SUMMARY")
    print("=" * 70)

    all_results = []
    for meta_path in sorted(output_dir.glob("**/meta.json")):
        try:
            with open(meta_path) as f:
                all_results.append(json.load(f))
        except Exception:
            continue

    if not all_results:
        print("No results found.")
        return

    df = pd.DataFrame(all_results)
    key = "log_loss" if "log_loss" in df.columns else "roc_auc"
    agg = "mean"
    pivot = df.pivot_table(index="dataset", columns="arm", values=key, aggfunc=agg)
    print(f"\n{key} (mean over seeds/folds):")
    print(pivot.to_string())

    if {"A_raw", "B_in_domain"} <= set(pivot.columns):
        pivot["delta_B_minus_A"] = pivot["B_in_domain"] - pivot["A_raw"]
        print(f"\nFine-tuning delta (B - A) on {key}:")
        print(pivot[["A_raw", "B_in_domain", "delta_B_minus_A"]].to_string())

    df.to_parquet(output_dir / "pilot_metrics.parquet", index=False)
    print(f"\nSaved: {output_dir / 'pilot_metrics.parquet'}")


def main():
    parser = argparse.ArgumentParser(description="Fine-tuning pilot (Pilot 2 schema v2)")
    parser.add_argument("--dataset", type=str, help="Run one dataset")
    parser.add_argument(
        "--arms",
        type=str,
        help=f"Comma-separated arms to run (default: all). Choices: {','.join(ARMS)}",
    )
    parser.add_argument("--aggregate", action="store_true", help="Aggregate results")
    parser.add_argument(
        "--epochs",
        type=int,
        default=DEFAULT_CONFIG["epochs"],
        help="Fine-tuning passes (PR-7). Library default is 30; 3 preserves R1 parity.",
    )
    parser.add_argument("--seeds", type=str, default=str(DEFAULT_SEED), help="e.g. 42,43,44")
    parser.add_argument("--folds", type=int, default=None, help="Stratified k-fold count")
    parser.add_argument("--rung", type=str, choices=sorted(RUNG), help="Scale preset (P1a/P1b/P1c)")
    parser.add_argument("--train-size", type=int, default=None)
    parser.add_argument("--test-size", type=int, default=None)
    parser.add_argument("--learning-rate", type=float, default=DEFAULT_CONFIG["learning_rate"])
    parser.add_argument("--n-estimators", type=int, default=DEFAULT_CONFIG["n_estimators"])
    parser.add_argument(
        "--save-models", action="store_true", help="Persist fitted models with hashes (PR-3)"
    )
    parser.add_argument(
        "--assert-lodo-for",
        type=str,
        default=None,
        help="Dataset name; assert it is absent from the pool (PR-5)",
    )
    parser.add_argument(
        "--pool", type=str, default=None, help="Comma-separated pool datasets (PR-5)"
    )
    args = parser.parse_args()

    arms = None
    if args.arms:
        arms = [a.strip() for a in args.arms.split(",") if a.strip()]
        unknown = [a for a in arms if a not in ARMS]
        if unknown:
            parser.error(f"unknown arm(s) {unknown}; choose from {list(ARMS)}")

    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]

    train_size, test_size = TRAIN_SIZE, TEST_SIZE
    rung_name = args.rung
    if rung_name:
        preset = RUNG[rung_name]
        train_size = preset["train_size"]
        test_size = preset["test_size"]
    if args.train_size is not None:
        train_size = args.train_size
    if args.test_size is not None:
        test_size = args.test_size

    config = dict(DEFAULT_CONFIG)
    config["epochs"] = args.epochs
    config["learning_rate"] = args.learning_rate
    config["n_estimators"] = args.n_estimators

    started = datetime.now(timezone.utc)
    run_id = started.strftime("%Y%m%dT%H%M%SZ")

    print("=" * 70)
    print("FINE-TUNING PILOT — Pilot 2 schema v%d" % SCHEMA_VERSION)
    print("=" * 70)
    print(f"Run id:   {run_id}")
    print(f"Config:   {config}")
    print(f"Epochs:   {config['epochs']}  (library default 30; 3 = R1 parity)")
    print(f"Arms:     {arms or list(ARMS)}")
    print(f"Seeds:    {seeds}")
    print(f"Folds:    {args.folds}")
    print(f"Rung:     {rung_name or 'explicit/ad-hoc'}  train={train_size} test={test_size}")
    from tabpfn import TabPFNClassifier  # noqa: F401  (import cost measured once)

    print(f"Device:   {'cuda' if torch.cuda.is_available() else 'cpu'}")
    if torch.cuda.is_available():
        print(f"GPU:      {torch.cuda.get_device_name(0)}")
        print(f"VRAM:     {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    print()

    if not check_data():
        sys.exit(1)

    if args.aggregate:
        aggregate_results()
        return

    # Fingerprints for every dataset (PR-6), computed once and reused.
    fingerprints = {n: dataset_fingerprint(n) for n in DATASETS}

    pool_meta = None
    if args.pool:
        pool_names = [p.strip() for p in args.pool.split(",") if p.strip()]
        target = args.assert_lodo_for or (args.dataset or "")
        pool_meta = build_pool(target, pool_names, fingerprints)
        print(f"[LODO] target '{target}' asserted absent from pool {pool_names}")

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "started_at": started.isoformat(),
        "status": "running",
        "git": _git_info(),
        "host": _host_info(),
        "env": _runtime_versions(),
        "checkpoints": _checkpoints(),
        "config": config,
        "epochs": config["epochs"],
        "legacy_config_keys_ignored": list(LEGACY_UNUSED_KEYS),
        "seeds": seeds,
        "folds": args.folds,
        "rung": rung_name,
        "train_size": train_size,
        "test_size": test_size,
        "arms": arms or list(ARMS),
        "datasets": [d for d in ([args.dataset] if args.dataset else DATASETS)],
        "dataset_fingerprints": fingerprints,
        "pool": pool_meta,
        "save_models": bool(args.save_models),
    }

    try:
        if args.dataset:
            run_single_dataset(
                args.dataset,
                arms,
                config=config,
                seeds=seeds,
                folds=args.folds,
                train_size=train_size,
                test_size=test_size,
                save_models=args.save_models,
                fingerprints=fingerprints,
            )
        else:
            for ds_name in DATASETS:
                run_single_dataset(
                    ds_name,
                    arms,
                    config=config,
                    seeds=seeds,
                    folds=args.folds,
                    train_size=train_size,
                    test_size=test_size,
                    save_models=args.save_models,
                    fingerprints=fingerprints,
                )
        manifest["status"] = "success"
    except Exception as e:
        manifest["status"] = "failed"
        manifest["error"] = f"{type(e).__name__}: {e}"
        raise
    finally:
        manifest["finished_at"] = datetime.now(timezone.utc).isoformat()
        write_run_manifest(manifest, OUTPUT_DIR)

    if not args.dataset:
        aggregate_results()


if __name__ == "__main__":
    main()
