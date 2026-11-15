#!/usr/bin/env python3
"""Train-fraction test (issue #186, master report §17.4): does training TabPFN on fewer rows
explain why the TabArena lapse harness scored eudirectlapse at AUC 0.6101 while the frontier
harness scores 0.6331 on the same test folds?

The TabArena run used holdout_experiments=True, which holds part of each training fold out
for validation (AutoGluon's default holdout fraction, about 10% at this size). This script
keeps the frontier harness's test folds and TabPFN call and trains on a stratified
`--fraction` of each training fold instead of all of it. If AUC falls by ~0.02, the holdout
explains the gap; if it does not, the remaining candidate is the TabArena wrapper's
preprocessing.

Same as run_frontier_benchmark.py: load_Xy, StratifiedKFold(5, shuffle=True,
random_state=seed), TabPFNClassifier(model_path=TABPFN_MODEL_PATH, random_state=0), its
retry loop and fold_scores. Different: the training rows, drawn per fold with
train_test_split(train_size=fraction, stratify=y, random_state=0).

Outputs (results/<UTC-timestamp>/):
    train_fraction_<ds>.csv            per-fold scores, plus the full-fold run when its
                                       stored predictions exist, and the paired deltas
    train_fraction_<ds>.npz            per-fold y_true, test_idx, train_idx, predictions
    train_fraction_<ds>.manifest.json  data file, fraction, seed, model_version, client
                                       version, git SHA, predictions_sha256

Usage:
    python scripts/eval/insurance_benchmark_v1/run_train_fraction_test.py \\
        --data data/raw/eudirectlapse.csv --target lapse --fraction 0.9 [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.model_selection import StratifiedKFold, train_test_split

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_frontier_benchmark as fb  # noqa: E402

N_FOLDS = 5
METRICS = ["log_loss", "brier", "auc", "pr_auc", "lift10"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", required=True, help="CSV path, repo-root-relative or absolute")
    ap.add_argument("--target", required=True)
    ap.add_argument("--fraction", type=float, default=0.9, help="share of each training fold kept")
    ap.add_argument("--seed", type=int, default=42, help="StratifiedKFold random_state")
    ap.add_argument("--dry-run", action="store_true", help="print fold sizes and exit (no API calls)")
    args = ap.parse_args()
    assert 0 < args.fraction < 1, "--fraction must be in (0, 1)"

    data = Path(args.data) if Path(args.data).is_absolute() else fb.REPO / args.data
    ds = dict(name=data.stem, file=str(data), target=args.target, drop=[])  # as Tier 2's --data run
    X, y = fb.load_Xy(ds)
    folds = list(StratifiedKFold(N_FOLDS, shuffle=True, random_state=args.seed).split(X, y))
    subs = [train_test_split(tr, train_size=args.fraction, stratify=y[tr], random_state=0)[0]
            for tr, _ in folds]
    for k, ((tr, te), sub) in enumerate(zip(folds, subs)):
        print(f"fold {k}: train {len(tr)} -> {len(sub)} rows ({y[sub].mean():.3f} positive), test {len(te)}")
    if args.dry_run:
        return

    from tabpfn_client import TabPFNClassifier
    fb._load_api_key()
    model_path = fb._model_path()
    metric = fb.metric_fn({})
    store: dict[str, np.ndarray] = {}
    rows = []
    for k, ((tr, te), sub) in enumerate(zip(folds, subs)):
        for attempt in range(1, 4):  # same retry policy as the frontier harness
            try:
                model = TabPFNClassifier(model_path=model_path, random_state=0)
                model.fit(X[sub], y[sub])
                pp = model.predict_proba(X[te])
                break
            except Exception as e:
                wait = [10, 60, 300][attempt - 1]
                print(f"  fold {k} attempt {attempt}/3 failed: {e!r}; retrying in {wait}s", flush=True)
                time.sleep(wait)
                if attempt == 3:
                    raise
        if pp.ndim == 1 or pp.shape[1] == 1:
            pp = np.column_stack([1 - pp, pp]) if pp.ndim == 1 else np.column_stack([1 - pp[:, 0], pp[:, 0]])
        s = fb.fold_scores(metric, y[te], pp)
        rows.append({"run": f"fraction_{args.fraction}", "fold": k, "n_train": len(sub), **s})
        store[f"y_true__fold{k}"] = y[te].astype(np.int64)
        store[f"test_idx__fold{k}"] = te.astype(np.int32)
        store[f"train_idx__fold{k}"] = np.sort(sub).astype(np.int32)
        store[f"tabpfn__fold{k}"] = pp[:, 1].astype(np.float32)
        print(f"  fold {k}: AUC {s['auc']:.4f}  log loss {s['log_loss']:.4f}", flush=True)

    # paired comparison with the full-training-fold run, when its predictions are stored
    full_path = fb.PREDICTIONS_DIR / f"{ds['name']}__seed{args.seed}__{model_path}.npz"
    comparison = None
    if full_path.exists():
        with np.load(full_path) as full:
            for k, (_, te) in enumerate(folds):
                assert np.array_equal(full[f"test_idx__fold{k}"], te), f"fold {k}: stored test fold differs"
                s = fb.fold_scores(metric, full[f"y_true__fold{k}"].astype(np.float64),
                                   fb._reconstruct_pp("tabpfn", full[f"tabpfn__fold{k}"].astype(np.float64)))
                rows.append({"run": "full", "fold": k, "n_train": len(folds[k][0]), **s})
        t = pd.DataFrame(rows)
        a, b = t[t.run != "full"].reset_index(drop=True), t[t.run == "full"].reset_index(drop=True)
        comparison = {}
        print(f"\n{args.fraction:.0%} of each training fold vs all of it ({full_path.name}), paired t df=4:")
        for mt in METRICS:
            d = a[mt] - b[mt]
            p = stats.ttest_rel(a[mt], b[mt]).pvalue
            comparison[mt] = {"fraction_mean": a[mt].mean(), "full_mean": b[mt].mean(),
                              "delta": d.mean(), "p_paired": p}
            print(f"  {mt:8} {a[mt].mean():.4f} vs {b[mt].mean():.4f}  delta {d.mean():+.4f}  p={p:.3f}")

    out = fb.REPO / "results" / time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    out.mkdir(parents=True, exist_ok=True)
    stem = f"train_fraction_{ds['name']}"
    pd.DataFrame(rows).to_csv(out / f"{stem}.csv", index=False, float_format="%.6g")
    np.savez_compressed(out / f"{stem}.npz", **store)
    with np.load(out / f"{stem}.npz") as saved:
        sha = fb.predictions_data_sha256(saved)
    try:
        git_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=fb.REPO, capture_output=True,
                                 text=True, check=True).stdout.strip()
    except Exception:
        git_sha = "unknown"
    manifest = {
        "dataset": ds["name"], "data_file": str(data.relative_to(fb.REPO)), "target": args.target,
        "split": f"StratifiedKFold({N_FOLDS}, shuffle=True, random_state={args.seed})",
        "train_rows": f"stratified {args.fraction} of each training fold, "
                      "train_test_split(random_state=0)",
        "model_version": model_path, "tabpfn_client_version": version("tabpfn-client"),
        "script_git_sha": git_sha, "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "predictions_sha256": sha, "predictions_sha256_scheme": fb.PREDICTIONS_SHA256_SCHEME,
        "full_fold_reference": full_path.name if comparison else None, "comparison": comparison,
    }
    (out / f"{stem}.manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"\nwrote {out.relative_to(fb.REPO)}/{stem}.{{csv,npz,manifest.json}}")


if __name__ == "__main__":
    main()
