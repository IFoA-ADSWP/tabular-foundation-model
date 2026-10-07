#!/usr/bin/env python3
"""Paired v3-vs-v3.5 analysis for one classification dataset (issue #186, Tier 3; master
report §18). Reads the per-fold predictions written by
`run_frontier_benchmark.py --save-predictions` and fits no hosted model — no API calls.

Inputs (predictions/):
    <ds>__seed42__v3_default.npz      same-day v3 run (seed 42)
    <ds>__seed<s>__v3.5_default.npz   v3.5, one per seed in --seeds

Sections:
  1. Integrity (seed 42): identical test folds and y_true across the two same-day runs,
     and every non-TabPFN method's predictions bit-identical between them — the model
     is the only variable.
  2. Alias drift: today's v3 folds vs the committed August v3 rows
     (frontier_pr_auc_results.csv, seed 42). `v3_default` is a server-side alias, so a
     mismatch would mean the checkpoint behind it moved (§17.4 candidate 2).
  3. Per seed: v3.5 vs v3, vs every harness method from the same run (lr, logisticglm,
     the GLMs, rf, cat, lgbm, xgb — the linear ones take categoricals as integer codes),
     and vs stronger linear specifications —
       onehot_lr      one-hot categoricals + standardised numerics (§17.3's fair LR)
       onehot_lr_logexp  onehot_lr + log(exposure), when the data has an exposure column
       glm_eng        §14.13's feature-engineered GLM, committed per-fold (seed 42 only)
     plus v3 vs the same stronger linear specifications, to test the published v3
     verdict against baselines it never faced (§19.4).
     v3 for seed 42 is the same-day run; for other seeds it is the committed August row,
     valid because section 2 shows no drift. Each non-42 seed is gated on August's
     baseline scores matching today's per fold, i.e. the folds are the same ones.

Statistics: paired t over the 5 folds of one seed (df=4, two-sided), delta = v3.5 −
reference. Seeds are reported side by side, never pooled: folds from different seeds
overlap, so 15 folds are not 15 independent samples. Scoring is float64 from the stored
float32 arrays (the #190 read-back convention).

Output: version_retest_<ds>.csv (long format, one row per seed x comparison x metric).

Usage:
    python scripts/eval/insurance_benchmark_v1/analyze_version_retest.py ausprivauto0405
    python scripts/eval/insurance_benchmark_v1/analyze_version_retest.py norauto --seeds 42
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_frontier_benchmark as fb  # noqa: E402

METRICS = ["log_loss", "brier", "auc", "pr_auc", "lift10"]
LOWER_BETTER = {"log_loss", "brier"}
N_FOLDS = 5
AUG_PER_FOLD = HERE / "frontier_pr_auc_results.csv"       # §14.12, Aug 2026, v3 + baselines
TUNED_PER_FOLD = HERE / "frontier_tuned_baseline_results.csv"  # §14.13, glm_eng, seed 42
METRIC = fb.metric_fn({})
EXPOSURE_COLS = ("Exposure", "Expo")  # ausprivauto0405, norauto


def load_store(ds_name: str, seed: int, version: str) -> dict[str, np.ndarray]:
    with np.load(fb.PREDICTIONS_DIR / f"{ds_name}__seed{seed}__{version}.npz") as d:
        return {k: d[k] for k in d.files}


def scores(store: dict, method: str) -> pd.DataFrame:
    return pd.DataFrame([
        fb.fold_scores(METRIC, store[f"y_true__fold{k}"].astype(np.float64),
                       fb._reconstruct_pp(method, store[f"{method}__fold{k}"].astype(np.float64)))
        for k in range(N_FOLDS)
    ])


def onehot_lr_scores(X: pd.DataFrame, y: np.ndarray, folds, cats: list[str], nums: list[str]) -> pd.DataFrame:
    from sklearn.compose import ColumnTransformer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    rows = []
    for tr, te in folds:
        pre = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), cats),
                                 ("num", StandardScaler(), nums)])
        model = make_pipeline(pre, LogisticRegression(max_iter=2000, random_state=0))
        p1 = model.fit(X.iloc[tr], y[tr]).predict_proba(X.iloc[te])[:, 1]
        rows.append(fb.fold_scores(METRIC, y[te].astype(np.float64), np.column_stack([1 - p1, p1])))
    return pd.DataFrame(rows)


def paired_rows(x: pd.DataFrame, ref: pd.DataFrame, **tags) -> list[dict]:
    """One row per metric for delta = x - ref (x is v3.5, or v3 for the fair-baseline rows)."""
    out = []
    for mt in METRICS:
        d = x[mt].to_numpy() - ref[mt].to_numpy()
        better = (d < 0) if mt in LOWER_BETTER else (d > 0)
        out.append({**tags, "metric": mt, "a_mean": x[mt].mean(), "b_mean": ref[mt].mean(),
                    "delta": d.mean(), "p_paired": stats.ttest_rel(x[mt], ref[mt]).pvalue,
                    "a_better_folds": int(better.sum()), "n_folds": len(d)})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("dataset")
    ap.add_argument("--seeds", type=int, nargs="+", default=[42, 7, 123])
    args = ap.parse_args()
    ds = next(d for d in fb.DATASETS if d["name"] == args.dataset)
    from sklearn.model_selection import StratifiedKFold

    raw = pd.read_csv(fb.DATA_RAW / ds["file"]).dropna(subset=[ds["target"]]).reset_index(drop=True)
    y = raw[ds["target"]].to_numpy(np.int64)
    X = raw.drop(columns=[ds["target"]] + ds["drop"])
    assert np.array_equal(y, fb.load_Xy(ds)[1]), "row order differs from the harness"
    cats = X.select_dtypes(include=["object", "category"]).columns.tolist()
    nums = [c for c in X.columns if c not in cats]
    aug = pd.read_csv(AUG_PER_FOLD)
    aug = aug[aug.dataset == ds["name"]]
    rows: list[dict] = []

    # ---- 1. integrity (seed 42, same day) ----
    v3_42 = load_store(ds["name"], 42, "v3_default")
    v35_42 = load_store(ds["name"], 42, "v3.5_default")
    methods = sorted({k.split("__")[0] for k in v3_42} - {"y_true", "test_idx"})
    for k in range(N_FOLDS):
        for key in (f"test_idx__fold{k}", f"y_true__fold{k}"):
            assert np.array_equal(v3_42[key], v35_42[key]), f"{key} differs between the two runs"
    worst = max(np.abs(v3_42[f"{m}__fold{k}"].astype(np.float64) - v35_42[f"{m}__fold{k}"]).max()
                for m in methods if m != "tabpfn" for k in range(N_FOLDS))
    print(f"=== {ds['name']}: integrity (seed 42)\n  test folds + y_true identical: yes; "
          f"max |baseline prediction diff| across runs = {worst:.3g} ({len(methods) - 1} methods)")

    # ---- 2. alias drift ----
    today = scores(v3_42, "tabpfn")
    then = aug[(aug.method == "tabpfn") & (aug.seed == 42)].sort_values("fold")
    print(f"\n=== {ds['name']}: alias drift — today's v3 vs committed August v3 (seed 42)")
    if len(then) == N_FOLDS:
        for mt in METRICS:
            diff = today[mt].to_numpy() - then[mt].to_numpy()
            print(f"  {mt:9} Aug {then[mt].mean():.6f}  today {today[mt].mean():.6f}  "
                  f"max |fold diff| {np.abs(diff).max():.2e}")
            rows.append({"seed": 42, "a": "v3_today", "b": "v3_august", "metric": mt,
                         "a_mean": today[mt].mean(), "b_mean": then[mt].mean(),
                         "delta": diff.mean(), "max_abs_fold_diff": np.abs(diff).max(),
                         "n_folds": N_FOLDS})
    else:
        print("  no committed August seed-42 per-fold rows — skipped")

    # ---- 3. per seed ----
    for s in args.seeds:
        v35_store = v35_42 if s == 42 else load_store(ds["name"], s, "v3.5_default")
        folds = list(StratifiedKFold(N_FOLDS, shuffle=True, random_state=s).split(np.zeros(len(y)), y))
        for k, (_, te) in enumerate(folds):
            assert np.array_equal(te, v35_store[f"test_idx__fold{k}"]), f"seed {s} fold {k}: test_idx differs"
        aug_s = aug[aug.seed == s]
        if s == 42:
            v3, v3_src = today, "same-day"
        else:
            # gate: August's per-fold baseline scores must match today's on this seed
            for m in ("logisticglm", "lgbm"):
                a = aug_s[aug_s.method == m].sort_values("fold")["log_loss"].to_numpy()
                assert len(a) == N_FOLDS, f"seed {s}: no committed August rows for {m}"
                gap = np.abs(a - scores(v35_store, m)["log_loss"].to_numpy()).max()
                assert gap < 1e-4, f"seed {s}: August {m} folds differ from today's by {gap:.1e}"
            v3 = aug_s[aug_s.method == "tabpfn"].sort_values("fold")[METRICS].reset_index(drop=True)
            v3_src = "august"
        v35 = scores(v35_store, "tabpfn")
        refs = {"v3": v3}
        refs.update({m: scores(v35_store, m) for m in methods if m != "tabpfn"})
        refs["onehot_lr"] = onehot_lr_scores(X, y, folds, cats, nums)
        expo = next((c for c in EXPOSURE_COLS if c in X), None)
        if expo is not None:
            refs["onehot_lr_logexp"] = onehot_lr_scores(X.assign(logExposure=np.log(X[expo])),
                                                        y, folds, cats, nums + ["logExposure"])
        if s == 42 and TUNED_PER_FOLD.exists():
            t = pd.read_csv(TUNED_PER_FOLD)
            g = t[(t.dataset == ds["name"]) & (t.method == "glm_eng")].sort_values("fold")
            if len(g) == N_FOLDS:
                refs["glm_eng"] = g[METRICS].reset_index(drop=True)

        print(f"\n=== {ds['name']}: seed {s} (v3 = {v3_src}) — delta = v3.5 − reference, paired t df=4")
        print(f"  {'reference':17}" + "".join(f"{mt:>26}" for mt in METRICS))
        for name, ref in refs.items():
            rs = paired_rows(v35, ref, seed=s, a="v3.5", b=name, v3_source=v3_src)
            rows.extend(rs)
            print(f"  {name:17}" + "".join(
                f"{r['delta']:+11.5f} p={r['p_paired']:.4f} {r['a_better_folds']}/5" for r in rs))
        print(f"  -- v3 ({v3_src}) − fair linear reference")
        for name in [n for n in ("onehot_lr", "onehot_lr_logexp", "glm_eng") if n in refs]:
            rs = paired_rows(v3, refs[name], seed=s, a="v3", b=name, v3_source=v3_src)
            rows.extend(rs)
            print(f"  {name:17}" + "".join(
                f"{r['delta']:+11.5f} p={r['p_paired']:.4f} {r['a_better_folds']}/5" for r in rs))

    out = HERE / f"version_retest_{ds['name']}.csv"
    pd.DataFrame(rows).to_csv(out, index=False, float_format="%.6g")
    print(f"\nwrote {out.relative_to(fb.REPO)}")


if __name__ == "__main__":
    main()
