"""Home-turf size-sweep pilot: TabPFN vs GBDT on 3 insurance datasets x 3 sizes.

Maps the dataset-size ceiling as a curve and scores on insurance-native metrics
(log loss + Brier primary, 1-AUC secondary). Not part of the v1 TabArena harness:
standalone sklearn + tabpfn_client runner using the v1 fold logic
(StratifiedKFold(5, shuffle=True, random_state=42)).

Cells: 3 datasets (coil2000, uslapseagent, bemtl97-leak-fixed) x sizes (1K, 5K, full).
Methods: TabPFN default / n_estimators=8 / n_estimators=1 (hosted API) + CAT/XGB/LGBM (CPU).
Trim for the 30-min budget: full-size bemtl97 runs TabPFN default only (extra configs
dropped, noted in the CSV via 'trimmed' column).

Usage:
    source /tmp/tabarena/.venv-ta/bin/activate
    python scripts/benchmarks/run_home_turf_size_sweep.py

Output: scripts/eval/insurance_benchmark_v1/home_turf_sweep_results.csv
"""
from __future__ import annotations

import os
import sys
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
DATA_RAW = REPO / "data" / "raw"
EVAL_DIR = REPO / "scripts" / "eval" / "insurance_benchmark_v1"
OUT_CSV = EVAL_DIR / "home_turf_sweep_results.csv"
LOG_FILE = EVAL_DIR / "home_turf_sweep_run.log"

# ---------------------------------------------------------------------------
# API key: TABPFN_API_KEY env, else repo-root .env or TABPFN_ENV_FILE
# ---------------------------------------------------------------------------
def _load_api_key() -> None:
    """TABPFN_API_KEY env, else the first TABPFN_API_KEY= line from the repo-root
    .env or the file pointed to by TABPFN_ENV_FILE (if set)."""
    if os.environ.get("TABPFN_API_KEY"):
        return
    candidates = [
        Path.cwd() / ".env",
        Path(os.environ["TABPFN_ENV_FILE"]) if os.environ.get("TABPFN_ENV_FILE") else None,
    ]
    for p in candidates:
        if p and p.exists():
            for line in p.read_text().splitlines():
                if line.startswith("TABPFN_API_KEY="):
                    os.environ["TABPFN_API_KEY"] = line.split("=", 1)[1].strip()
                    return
    raise RuntimeError(
        "TABPFN_API_KEY not set: export TABPFN_API_KEY=... or add a "
        "TABPFN_API_KEY=... line to a .env file in the repo root "
        "(or set TABPFN_ENV_FILE to point at one)"
    )

# ---------------------------------------------------------------------------
# Dataset registry
# ---------------------------------------------------------------------------
DATASETS = [
    dict(name="coil2000", file="coil2000.csv", target="CARAVAN", drop=[]),
    dict(name="uslapseagent", file="uslapseagent.csv", target="surrender", drop=[]),
    # §6 leakage fix: claim == (nclaims>0) == (amount>0) exactly; drop the leak features
    dict(name="bemtl97", file="bemtl97.csv", target="claim", drop=["nclaims", "amount"]),
]
SIZES = [1000, 5000, None]  # None = full
N_FOLDS = 5


def load_Xy(ds: dict) -> tuple[np.ndarray, np.ndarray]:
    df = pd.read_csv(DATA_RAW / ds["file"])
    df = df.dropna(subset=[ds["target"]]).reset_index(drop=True)
    y = df[ds["target"]].to_numpy(dtype=np.int64)
    X = df.drop(columns=[ds["target"]] + ds["drop"])
    for col in X.select_dtypes(include=["object", "category"]).columns:
        X[col] = X[col].astype("category").cat.codes.replace(-1, np.nan)
    X = X.fillna(0.0).astype(np.float32)
    return X.to_numpy(dtype=np.float32), y


def slice_data(X: np.ndarray, y: np.ndarray, n: int | None) -> tuple[np.ndarray, np.ndarray]:
    """Stratified slice preserving class balance (deterministic seed)."""
    if n is None or len(X) <= n:
        return X, y
    from sklearn.model_selection import train_test_split
    Xs, _, ys, _ = train_test_split(X, y, train_size=n, stratify=y, random_state=42)
    return Xs, ys


# ---------------------------------------------------------------------------
# Methods
# ---------------------------------------------------------------------------
def make_tabpfn(n_estimators: int | None):
    from tabpfn_client import TabPFNClassifier
    kw: dict = {"random_state": 0}
    if n_estimators is not None:
        kw["n_estimators"] = n_estimators
    return TabPFNClassifier(model_path="v3_default", **kw)


def make_cat():
    from catboost import CatBoostClassifier
    return CatBoostClassifier(random_state=0, verbose=0)


def make_xgb():
    from xgboost import XGBClassifier
    return XGBClassifier(random_state=0)


def make_lgbm():
    from lightgbm import LGBMClassifier
    return LGBMClassifier(random_state=0, device_type="cpu", verbose=-1)


def predict_proba(model, X: np.ndarray) -> np.ndarray:
    if isinstance(X, np.ndarray):
        return model.predict_proba(X)
    return model.predict_proba(X)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    _load_api_key()
    os.environ.setdefault("TABPFN_CLIENT_TIMEOUT", "240")  # cap hangs; v1 max infer ~41s
    EVAL_DIR.mkdir(parents=True, exist_ok=True)

    log = open(LOG_FILE, "w")
    def say(msg: str) -> None:
        line = f"[{time.strftime('%H:%M:%S')}] {msg}"
        print(line, flush=True)
        log.write(line + "\n")
        log.flush()

    from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
    from sklearn.model_selection import StratifiedKFold

    t0_all = time.time()
    all_rows: list[dict] = []

    # Ensemble probe: is n_estimators=8 (API cap) identical to the server default?
    n8_equals_default: bool | None = None

    for ds in DATASETS:
        X_full, y_full = load_Xy(ds)
        say(f"dataset={ds['name']} full_shape={X_full.shape} pos_rate={y_full.mean():.4f}")

        for n in SIZES:
            X, y = slice_data(X_full, y_full, n)
            n_rows = len(X)
            cell_t0 = time.time()

            # Methods for this cell. Trim: full bemtl97 keeps TabPFN default only.
            methods: list[tuple[str, dict]] = [
                ("tabpfn", {"n_estimators": None}),
            ]
            trim_extra = ds["name"] == "bemtl97" and n is None
            if not trim_extra:
                # n8 included only while the probe is pending (None) or proved different (False)
                if n8_equals_default is not True:
                    methods.append(("tabpfn", {"n_estimators": 8}))
                methods.append(("tabpfn", {"n_estimators": 1}))
            methods += [("cat", {}), ("xgb", {}), ("lgbm", {})]

            say(f"cell {ds['name']} n={n_rows} methods={[m[0] + str(m[1]) for m in methods]}{' TRIMMED(no extra tabpfn configs)' if trim_extra else ''}")

            skf = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=42)
            for fold, (tr, te) in enumerate(skf.split(X, y)):
                Xtr, Xte, ytr, yte = X[tr], X[te], y[tr], y[te]
                for mname, mkw in methods:
                    row = {
                        "dataset": ds["name"],
                        "n_rows": n_rows,
                        "method": mname,
                        "fold": fold,
                        "n_estimators": mkw.get("n_estimators"),
                        "trimmed": trim_extra,
                        "error": "",
                        "train_s": np.nan,
                        "infer_s": np.nan,
                        "log_loss": np.nan,
                        "brier": np.nan,
                        "roc_auc": np.nan,
                    }
                    try:
                        if mname == "tabpfn":
                            model = make_tabpfn(mkw["n_estimators"])
                        elif mname == "cat":
                            model = make_cat()
                        elif mname == "xgb":
                            model = make_xgb()
                        else:
                            model = make_lgbm()
                        t = time.time()
                        model.fit(Xtr, ytr)
                        row["train_s"] = round(time.time() - t, 2)
                        t = time.time()
                        p = predict_proba(model, Xte)
                        row["infer_s"] = round(time.time() - t, 2)
                        if p.ndim == 1 or p.shape[1] == 1:  # single-class fallback
                            pp = np.column_stack([1 - p, p]) if p.ndim == 1 else np.column_stack([1 - p[:, 0], p[:, 0]])
                        else:
                            pp = p
                        row["log_loss"] = log_loss(yte, pp)
                        row["brier"] = brier_score_loss(yte, pp[:, 1])
                        row["roc_auc"] = roc_auc_score(yte, pp[:, 1])

                        if mname == "tabpfn" and mkw.get("n_estimators") == 8 and n8_equals_default is None:
                            pass  # compare after the default row is written
                    except Exception as e:
                        row["error"] = f"{type(e).__name__}: {e}".replace("\n", " ")
                        say(f"  FAILED {ds['name']} n={n_rows} {mname} {mkw} fold={fold}: {row['error']}")

                    all_rows.append(row)
                    if row["log_loss"] == row["log_loss"]:  # not NaN
                        say(f"  {ds['name']} n={n_rows} {mname}{mkw} f{fold} ll={row['log_loss']:.4f} brier={row['brier']:.4f} auc={row['roc_auc']:.4f} ({row['train_s']}s+{row['infer_s']}s)")
                    # flush CSV so partial results survive a crash/timeout
                    pd.DataFrame(all_rows).to_csv(OUT_CSV, index=False)

            say(f"cell {ds['name']} n={n_rows} done in {time.time() - cell_t0:.0f}s")

            # Ensemble probe verdict (checked on first cell, applied everywhere)
            if n8_equals_default is None and not trim_extra:
                cell_rows = [r for r in all_rows if r["dataset"] == ds["name"] and r["n_rows"] == n_rows]
                dflt = [r for r in cell_rows if r["method"] == "tabpfn" and r["n_estimators"] is None and r["error"] == ""]
                n8 = [r for r in cell_rows if r["method"] == "tabpfn" and r["n_estimators"] == 8 and r["error"] == ""]
                if dflt and n8:
                    same = all(abs(a["log_loss"] - b["log_loss"]) < 1e-8 for a, b in zip(dflt, n8))
                    n8_equals_default = same
                    say(f"PROBE: n_estimators=8 vs server default identical={same} -> {'skip n8 elsewhere' if same else 'keep n8'}")
                else:
                    n8_equals_default = False

    pd.DataFrame(all_rows).to_csv(OUT_CSV, index=False)
    say(f"ALL DONE in {time.time() - t0_all:.0f}s -> {OUT_CSV}")
    log.close()


if __name__ == "__main__":
    main()
