"""Diagnostic: Is EU Lapse complex enough for TabPFN?

Runs GLM and RandomForest on EU Direct Lapse and freMTPL2 Binary
to determine if non-linear structure exists that TabPFN could exploit.

Usage:
    python scripts/diagnostic_complexity.py
"""
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import brier_score_loss, roc_auc_score

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"

TARGETS = {
    "eudirectlapse": "lapse",
    "freMTPL2freq_binary": "ClaimIndicator",
}


def load_and_prepare(name: str, target_col: str, max_rows: int = 3000):
    path = DATA_DIR / f"{name}.csv"
    if not path.exists():
        print(f"  [SKIP] {path.name} not found")
        return None

    df = pd.read_csv(path)
    if len(df) > max_rows:
        df = df.sample(n=max_rows, random_state=42)

    if target_col not in df.columns:
        print(f"  [SKIP] target '{target_col}' not in {name}")
        return None

    y = df[target_col].values
    X = pd.get_dummies(df.drop(columns=[target_col]), drop_first=False)
    X = X.astype(np.float64).fillna(0).values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y if len(np.unique(y)) == 2 else None
    )

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    return X_train, X_test, y_train, y_test


def evaluate(name, target, max_rows=3000):
    data = load_and_prepare(name, target, max_rows)
    if data is None:
        return None

    X_train, X_test, y_train, y_test = data
    n_train, n_features = X_train.shape
    results = {}

    glm = LogisticRegression(max_iter=1000, random_state=42)
    glm.fit(X_train, y_train)
    glm_probs = glm.predict_proba(X_test)[:, 1]
    results["GLM"] = brier_score_loss(y_test, glm_probs)
    results["GLM_ROC"] = roc_auc_score(y_test, glm_probs)

    rf = RandomForestClassifier(n_estimators=50, random_state=42, n_jobs=-1, max_depth=6)
    rf.fit(X_train, y_train)
    rf_probs = rf.predict_proba(X_test)[:, 1]
    results["RandomForest"] = brier_score_loss(y_test, rf_probs)
    results["RandomForest_ROC"] = roc_auc_score(y_test, rf_probs)

    return results, n_train, n_features


def main():
    print("=" * 70)
    print("COMPLEXITY DIAGNOSTIC: Is there non-linear structure to exploit?")
    print("=" * 70)

    for name, target in TARGETS.items():
        print(f"\n--- {name} ---")
        result = evaluate(name, target)
        if result is None:
            continue

        results, n_train, n_features = result
        glm_brier = results["GLM"]
        rf_brier = results["RandomForest"]
        rf_delta = glm_brier - rf_brier

        if rf_delta < 0.005:
            verdict = "LINEAR — no non-linear structure for TabPFN to exploit"
        elif rf_delta > 0.01:
            verdict = "NON-LINEAR — structure exists, TabPFN can exploit it"
        else:
            verdict = "MARGINAL — some non-linear structure but weak"

        print(f"  Rows: {n_train} train | Features: {n_features}")
        print(f"  GLM Brier:            {glm_brier:.5f}  (ROC: {results['GLM_ROC']:.4f})")
        print(f"  RandomForest Brier:   {rf_brier:.5f}  (ROC: {results['RandomForest_ROC']:.4f})")
        print(f"  Delta (GLM - RF):     {rf_delta:+.5f}")
        print(f"  VERDICT: {verdict}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
