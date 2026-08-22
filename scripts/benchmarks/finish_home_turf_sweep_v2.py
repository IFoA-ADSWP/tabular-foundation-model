"""Finisher v2: fill remaining home-turf sweep cells to a uniform matrix.

Differences vs finish_home_turf_sweep.py:
  * DROPS the n_estimators=1 arm entirely (it caused server disconnects).
  * Adds the n_estimators=8 arm to every non-trimmed cell (config-lite uniformity).
  * Keys cache on (dataset, n_rows, method, n_estimators, fold) so n8 fills
    independently of the default arm.
  * Treats rows with a non-empty 'error' as NOT complete -> retried once.
  * Runs fast fills (n8 arms + bemtl97-full GBDT) before slow tabpfn-full
    retries, and hard-stops at a wall-clock budget so one cell cannot kill the run.

Output: scripts/eval/insurance_benchmark_v1/home_turf_sweep_results.csv
"""
from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutTimeout
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root
from src.api_key import load_api_key as _load_api_key  # noqa: E402
REPO = HERE.parent.parent
DATA_RAW = REPO / "data" / "raw"
EVAL_DIR = REPO / "scripts" / "eval" / "insurance_benchmark_v1"
OUT_CSV = EVAL_DIR / "home_turf_sweep_results.csv"
PER_FIT_TIMEOUT = 300.0
WALL_BUDGET_S = 35 * 60  # protect the 40-min budget; slow tabpfn-full retries last

os.environ["TABPFN_CLIENT_TIMEOUT"] = "300"


_load_api_key()

SPEC = {
    "coil2000": ("coil2000.csv", "CARAVAN", []),
    "uslapseagent": ("uslapseagent.csv", "surrender", []),
    "bemtl97": ("bemtl97.csv", "claim", ["nclaims", "amount"]),
}
SIZES = [1000, 5000, None]
T0 = time.time()


def load_Xy(name: str) -> tuple[np.ndarray, np.ndarray]:
    file, target, drop = SPEC[name]
    df = pd.read_csv(DATA_RAW / file).dropna(subset=[target]).reset_index(drop=True)
    y = df[target].to_numpy(dtype=np.int64)
    X = df.drop(columns=[target] + drop)
    for col in X.select_dtypes(include=["object", "category"]).columns:
        X[col] = X[col].astype("category").cat.codes.replace(-1, np.nan)
    return X.fillna(0.0).astype(np.float32).to_numpy(dtype=np.float32), y


def slice_data(X, y, n):
    if n is None or len(X) <= n:
        return X, y
    from sklearn.model_selection import train_test_split
    Xs, _, ys, _ = train_test_split(X, y, train_size=n, stratify=y, random_state=42)
    return Xs, ys


def fit_predict(mname: str, mkw: dict, Xtr, ytr, Xte):
    if mname == "tabpfn":
        from tabpfn_client import TabPFNClassifier
        model = TabPFNClassifier(model_path="v3_default", random_state=0, **mkw)
    elif mname == "cat":
        from catboost import CatBoostClassifier
        model = CatBoostClassifier(random_state=0, verbose=0)
    elif mname == "xgb":
        from xgboost import XGBClassifier
        model = XGBClassifier(random_state=0)
    else:
        from lightgbm import LGBMClassifier
        model = LGBMClassifier(random_state=0, device_type="cpu", verbose=-1)
    model.fit(Xtr, ytr)
    return model.predict_proba(Xte)


def intended_methods(name: str, n_rows: int) -> list[tuple[str, dict]]:
    """Final intended matrix. n1 dropped; n8 everywhere except trimmed full bemtl97."""
    m = [("tabpfn", {"n_estimators": None}), ("tabpfn", {"n_estimators": 8})]
    if name == "bemtl97" and n_rows > 50000:  # trimmed largest cell (harness cap)
        m = [("tabpfn", {"n_estimators": None})]
    return m + [("cat", {}), ("xgb", {}), ("lgbm", {})]


def main() -> None:
    from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
    from sklearn.model_selection import StratifiedKFold

    # --- 1) Clean: drop the n_estimators=1 arm entirely -------------------
    df = pd.read_csv(OUT_CSV)
    n1 = df["n_estimators"].eq(1.0).sum()
    df = df[~df["n_estimators"].eq(1.0)]
    df.to_csv(OUT_CSV, index=False)
    print(f"[clean] dropped {n1} n_estimators=1 rows; kept {len(df)} rows", flush=True)

    # --- 2) Build missing-task list ---------------------------------------
    # cache key: complete = row present AND error empty
    ok = df[df["error"].fillna("").eq("")].copy()
    have = {
        (r.dataset, r.n_rows, r.method,
         (None if pd.isna(r.n_estimators) else r.n_estimators), r.fold)
        for r in ok.itertuples()
    }
    todo: list[tuple[str, int, str, dict, int]] = []
    for name in SPEC:
        Xf, yf = load_Xy(name)
        for n in SIZES:
            Xs, ys = slice_data(Xf, yf, n)
            n_rows = len(Xs)
            for mname, mkw in intended_methods(name, n_rows):
                for fold in range(5):
                    key = (name, n_rows, mname, mkw.get("n_estimators"), fold)
                    if key not in have:
                        todo.append((name, n_rows, mname, mkw, fold))
    print(f"[plan] {len(todo)} missing (dataset,n_rows,method,fold) combos", flush=True)

    # bemtl97-full tabpfn retries are slow -> move to the end
    def sort_key(t):
        ne = t[3].get("n_estimators") or 0
        return (t[0] == "bemtl97" and t[1] > 50000 and t[2] == "tabpfn", t[0], t[1], t[2], ne, t[3])
    todo.sort(key=sort_key)

    # --- 3) Run missing tasks ---------------------------------------------
    new_rows = []
    for name, n_rows, mname, mkw, fold in todo:
        if time.time() - T0 > WALL_BUDGET_S:
            print(f"[stop] wall-clock budget {WALL_BUDGET_S}s reached; {len(todo)} tasks left", flush=True)
            break
        Xf, yf = load_Xy(name)
        X, y = slice_data(Xf, yf, n_rows)
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        tr, te = list(skf.split(X, y))[fold]
        row = {"dataset": name, "n_rows": n_rows, "method": mname, "fold": fold,
               "n_estimators": mkw.get("n_estimators"),
               "trimmed": bool(name == "bemtl97" and n_rows > 50000),
               "error": "", "train_s": np.nan, "infer_s": np.nan,
               "log_loss": np.nan, "brier": np.nan, "roc_auc": np.nan}
        t0 = time.time()
        try:
            with ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(fit_predict, mname, mkw, X[tr], y[tr], X[te])
                p = fut.result(timeout=PER_FIT_TIMEOUT)
            row["train_s"] = round(time.time() - t0, 2)
            pp = p if p.shape[1] > 1 else np.column_stack([1 - p[:, 0], p[:, 0]])
            row["log_loss"] = log_loss(y[te], pp)
            row["brier"] = brier_score_loss(y[te], pp[:, 1])
            row["roc_auc"] = roc_auc_score(y[te], pp[:, 1])
            print(f"OK {name} n={n_rows} {mname}{mkw} f{fold} ll={row['log_loss']:.4f} auc={row['roc_auc']:.4f} ({row['train_s']}s)", flush=True)
        except FutTimeout:
            row["error"] = f"TimeoutError: fit+pred >{PER_FIT_TIMEOUT}s"
            print(f"TIMEOUT {name} n={n_rows} {mname}{mkw} f{fold}", flush=True)
        except Exception as e:
            row["error"] = f"{type(e).__name__}: {e}".replace("\n", " ")
            print(f"FAILED {name} n={n_rows} {mname}{mkw} f{fold}: {row['error']}", flush=True)
        new_rows.append(row)
        pd.concat([pd.read_csv(OUT_CSV), pd.DataFrame(new_rows)], ignore_index=True).to_csv(OUT_CSV, index=False)

    print(f"[done] +{len(new_rows)} rows, elapsed {time.time() - T0:.0f}s -> {OUT_CSV}", flush=True)


if __name__ == "__main__":
    main()
