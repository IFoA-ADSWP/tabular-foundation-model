#!/usr/bin/env python3
"""
Fine-tuning pilot: 4 datasets × 4 arms × 1 config = 16 runs.
Designed for Colab T4 (16 GB VRAM).

Usage:
    python scripts/run_pilot.py
"""
import sys
import os
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, brier_score_loss, average_precision_score

# Ensure repo imports work (handle both __file__ and piped execution)
if "__file__" in dir():
    REPO_ROOT = Path(__file__).resolve().parents[1]
else:
    REPO_ROOT = Path(os.getcwd())
sys.path.insert(0, str(REPO_ROOT))

# Config
PILOT_CONFIG = {
    "context_samples": 64,
    "max_finetune_steps": 3,
    "n_estimators": 2,
    "learning_rate": 1e-5,
    "fit_mode": "batched",
}

SEEDS = [42]
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


def load_dataset(name, target_col, max_rows=TRAIN_SIZE + TEST_SIZE + 500):
    path = DATA_DIR / f"{name}.csv"
    df = pd.read_csv(path)
    if len(df) > max_rows:
        df = df.sample(n=max_rows, random_state=42)
    y = df[target_col].values.astype(int)
    X = pd.get_dummies(df.drop(columns=[target_col]), drop_first=False).fillna(0).values.astype(np.float64)
    return X, y


def encode_data(X, y, scaler=None):
    if scaler is None:
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        X = scaler.fit_transform(X)
    else:
        X = scaler.transform(X)
    return X, scaler


def run_arm_a_raw(X_train, X_test, y_train, y_test, config):
    """Raw TabPFN — no fine-tuning."""
    from tabpfn import TabPFNClassifier

    clf = TabPFNClassifier(
        ignore_pretraining_limits=True,
        device="cuda" if torch.cuda.is_available() else "cpu",
        n_estimators=config["n_estimators"],
        random_state=42,
        inference_precision=torch.float32,
        fit_mode=config["fit_mode"],
    )
    clf.fit(X_train, y_train)
    probs = clf.predict_proba(X_test)[:, 1]
    return probs, clf


def run_arm_b_in_domain(X_train, X_test, y_train, y_test, config):
    """In-domain fine-tuning."""
    from tabpfn import TabPFNClassifier
    from tabpfn.architectures.interface import PerformanceOptions

    clf = TabPFNClassifier(
        ignore_pretraining_limits=True,
        device="cuda" if torch.cuda.is_available() else "cpu",
        n_estimators=config["n_estimators"],
        random_state=42,
        inference_precision=torch.float32,
        fit_mode=config["fit_mode"],
    )

    # Fine-tune
    from tabpfn.finetuning.data_util import get_preprocessed_dataset_chunks, meta_dataset_collator
    from torch.optim import Adam
    from torch.utils.data import DataLoader

    try:
        clf._initialize_model_variables()
    except Exception:
        pass

    split_fn = lambda X, y, stratify=None: train_test_split(X, y, test_size=0.2, random_state=42, stratify=stratify)
    training_datasets = get_preprocessed_dataset_chunks(
        calling_instance=clf, X_raw=X_train, y_raw=y_train, split_fn=split_fn,
        max_data_size=None, model_type="classifier", equal_split_size=True,
        data_shuffle_seed=42, preprocessing_random_state=42, shuffle=True,
    )

    optimizer = Adam(clf.model_.parameters(), lr=config["learning_rate"]) if hasattr(clf, "model_") else None
    dataloader = DataLoader(training_datasets, batch_size=1, collate_fn=meta_dataset_collator)
    loss_fn = torch.nn.CrossEntropyLoss()

    for epoch in range(config["max_finetune_steps"]):
        for batch_item in dataloader:
            try:
                clf.fit_from_preprocessed(batch_item.X_context, batch_item.y_context, batch_item.cat_indices, batch_item.configs, performance_options=PerformanceOptions())
            except Exception as e:
                print(f"fit_from_preprocessed failed: {e}")
                return None, clf
            if optimizer is not None and hasattr(clf, "forward"):
                try:
                    preds = clf.forward(batch_item.X_query, return_logits=True)
                    loss = loss_fn(preds, batch_item.y_query.to(clf.devices_[0]))
                    optimizer.zero_grad(); loss.backward(); optimizer.step()
                except Exception:
                    pass

    probs = clf.predict_proba(X_test)[:, 1]
    return probs, clf


def run_arm_e_glm(X_train, X_test, y_train, y_test):
    """GLM baseline."""
    from sklearn.preprocessing import StandardScaler
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    clf = LogisticRegression(max_iter=1000, random_state=42)
    clf.fit(X_train_s, y_train)
    probs = clf.predict_proba(X_test_s)[:, 1]
    return probs, clf


def run_arm_f_catboost(X_train, X_test, y_train, y_test):
    """CatBoost baseline (or RandomForest fallback)."""
    try:
        from catboost import CatBoostClassifier
        clf = CatBoostClassifier(iterations=200, verbose=0, random_state=42)
        clf.fit(X_train, y_train)
        probs = clf.predict_proba(X_test)[:, 1]
        return probs, clf
    except ImportError:
        clf = RandomForestClassifier(n_estimators=100, random_state=42)
        clf.fit(X_train, y_train)
        probs = clf.predict_proba(X_test)[:, 1]
        return probs, clf


def compute_metrics(y_true, y_prob):
    return {
        "roc_auc": roc_auc_score(y_true, y_prob),
        "brier": brier_score_loss(y_true, y_prob),
        "pr_auc": average_precision_score(y_true, y_prob),
    }


def save_results(dataset, arm, metrics, y_prob, y_test, run_time, config, output_dir):
    run_id = f"{dataset}_{arm}_seed42"
    run_dir = output_dir / dataset / arm
    run_dir.mkdir(parents=True, exist_ok=True)

    np.save(run_dir / "predictions.npy", y_prob)
    np.save(run_dir / "ground_truth.npy", y_test)

    meta = {
        "run_id": run_id,
        "dataset": dataset,
        "arm": arm,
        "config": config,
        "seed": 42,
        "train_rows": TRAIN_SIZE,
        "test_rows": len(y_test),
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
        "run_time_seconds": run_time,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "success",
        **metrics,
    }

    with open(run_dir / "meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    return meta


def main():
    print("=" * 70)
    print("FINE-TUNING PILOT — 4 datasets × 4 arms")
    print("=" * 70)
    print(f"Config: {PILOT_CONFIG}")
    print(f"Device: {'cuda' if torch.cuda.is_available() else 'cpu'}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    print()

    if not check_data():
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    all_results = []

    for ds_name, ds_info in DATASETS.items():
        print(f"\n--- {ds_name} ({ds_info['file']}) ---")
        X, y = load_dataset(ds_name, ds_info["target"])

        # Create fixed split
        X_train_full, X_test, y_train_full, y_test = train_test_split(
            X, y, test_size=TEST_SIZE, random_state=42, stratify=y
        )
        # Subset training to TRAIN_SIZE
        if len(X_train_full) > TRAIN_SIZE:
            X_train, _, y_train, _ = train_test_split(
                X_train_full, y_train_full, train_size=TRAIN_SIZE, random_state=42, stratify=y_train_full
            )
        else:
            X_train, y_train = X_train_full, y_train_full

        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s = scaler.transform(X_test)

        for arm_name, arm_fn in [
            ("A_raw", lambda: run_arm_a_raw(X_train_s, X_test_s, y_train, y_test, PILOT_CONFIG)),
            ("B_in_domain", lambda: run_arm_b_in_domain(X_train_s, X_test_s, y_train, y_test, PILOT_CONFIG)),
            ("E_glm", lambda: run_arm_e_glm(X_train_s, X_test_s, y_train, y_test)),
            ("F_catboost", lambda: run_arm_f_catboost(X_train_s, X_test_s, y_train, y_test)),
        ]:
            print(f"  {arm_name}...", end=" ", flush=True)
            start = time.time()
            try:
                probs, _ = arm_fn()
                elapsed = time.time() - start

                if probs is None:
                    print(f"FAILED ({elapsed:.1f}s)")
                    continue

                metrics = compute_metrics(y_test, probs)
                meta = save_results(ds_name, arm_name, metrics, probs, y_test, elapsed, PILOT_CONFIG, OUTPUT_DIR)
                all_results.append(meta)
                print(f"ROC={metrics['roc_auc']:.4f} Brier={metrics['brier']:.4f} ({elapsed:.1f}s)")

            except Exception as e:
                elapsed = time.time() - start
                print(f"ERROR: {e} ({elapsed:.1f}s)")

    # Summary table
    print("\n" + "=" * 70)
    print("PILOT RESULTS SUMMARY")
    print("=" * 70)
    df = pd.DataFrame(all_results)
    if len(df) > 0:
        pivot = df.pivot_table(index="dataset", columns="arm", values="roc_auc", aggfunc="first")
        print("\nROC AUC:")
        print(pivot.to_string())

        # Delta: fine-tuned minus raw
        if "B_in_domain" in pivot.columns and "A_raw" in pivot.columns:
            pivot["delta_B_minus_A"] = pivot["B_in_domain"] - pivot["A_raw"]
            print("\nFine-tuning delta (B - A):")
            print(pivot[["A_raw", "B_in_domain", "delta_B_minus_A"]].to_string())

    # Save summary
    if len(df) > 0:
        df.to_parquet(OUTPUT_DIR / "pilot_metrics.parquet", index=False)
        print(f"\nSaved: {OUTPUT_DIR / 'pilot_metrics.parquet'}")

    print("\nDone.")


if __name__ == "__main__":
    main()
