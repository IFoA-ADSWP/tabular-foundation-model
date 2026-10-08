#!/usr/bin/env python3
"""Size-sweep version re-test (issue #186, master report §23): the §13.2 winner table —
TabPFN's server-default arm against CatBoost / LightGBM / XGBoost on 3 datasets x 3 sizes,
mean log loss over 5 folds — recomputed for a refreshed sweep and set beside the committed
August v3 sweep. Reads the two CSVs written by run_home_turf_size_sweep.py; no API calls.

Per cell:
  * fold check: a GBDT whose per-fold log losses match the committed sweep's to 1e-4
    shows the slice and folds are the same; if none does, that cell's v3-vs-new comparison
    is skipped. Each GBDT's largest per-fold gap is reported, since one library can drift
    on its own (xgboost, §23).
  * winner by mean log loss, for both sweeps (the §13.2 rule);
  * paired t over the 5 folds (df=4, two-sided): new TabPFN − best GBDT, and new TabPFN −
    committed v3 TabPFN.

Output: version_retest_home_turf_sweep.csv (one row per cell).

Usage:
    python scripts/eval/insurance_benchmark_v1/analyze_sweep_retest.py \\
        --new results/<run>/home_turf_sweep_results.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
GBDTS = ["cat", "lgbm", "xgb"]


def default_arm(df: pd.DataFrame) -> pd.DataFrame:
    """Server-default TabPFN rows (n_estimators empty) plus the GBDT rows, errors dropped."""
    ok = df[df["error"].fillna("").astype(str) == ""]
    return ok[(ok.method != "tabpfn") | ok.n_estimators.isna()]


def per_fold(df: pd.DataFrame, dataset: str, n_rows: int, method: str) -> np.ndarray:
    r = df[(df.dataset == dataset) & (df.n_rows == n_rows) & (df.method == method)].sort_values("fold")
    return r["log_loss"].to_numpy(dtype=float)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--new", required=True, help="refreshed home_turf_sweep_results.csv")
    ap.add_argument("--old", default=str(HERE / "home_turf_sweep_results.csv"),
                    help="committed August v3 sweep (default)")
    args = ap.parse_args()
    new = default_arm(pd.read_csv(REPO / args.new if not Path(args.new).is_absolute() else args.new))
    old = default_arm(pd.read_csv(args.old))
    version = new["model_version"].dropna().unique().tolist() if "model_version" in new else ["unknown"]

    rows = []
    for (dataset, n_rows), _ in new.groupby(["dataset", "n_rows"], sort=False):
        cell = {"dataset": dataset, "n_rows": int(n_rows), "model_version_new": ",".join(version)}
        tab = per_fold(new, dataset, n_rows, "tabpfn")
        tab_old = per_fold(old, dataset, n_rows, "tabpfn")
        gb = {m: per_fold(new, dataset, n_rows, m) for m in GBDTS}
        gb_old = {m: per_fold(old, dataset, n_rows, m) for m in GBDTS}
        assert len(tab) == 5 and all(len(v) == 5 for v in gb.values()), f"{dataset}@{n_rows}: missing folds in --new"
        gaps = {m: np.abs(gb[m] - gb_old[m]).max() for m in GBDTS if len(gb_old[m]) == 5}
        cell.update({f"fold_gap_vs_old_{m}": g for m, g in gaps.items()})
        same_folds = bool(gaps) and min(gaps.values()) < 1e-4
        means = {"tabpfn": tab.mean(), **{m: v.mean() for m, v in gb.items()}}
        best_gb = min(GBDTS, key=lambda m: means[m])
        cell.update({"tabpfn_new": means["tabpfn"], "tabpfn_old": tab_old.mean() if len(tab_old) == 5 else np.nan,
                     **{m: means[m] for m in GBDTS},
                     "winner_new": min(means, key=means.get),
                     "winner_old": min({"tabpfn": tab_old.mean(), **{m: v.mean() for m, v in gb_old.items()}}.items(),
                                       key=lambda kv: kv[1])[0] if len(tab_old) == 5 else "",
                     "best_gbdt": best_gb})
        d = tab - gb[best_gb]
        cell.update({"delta_vs_best_gbdt": d.mean(), "p_vs_best_gbdt": stats.ttest_rel(tab, gb[best_gb]).pvalue,
                     "tabpfn_better_folds": int((d < 0).sum())})
        if len(tab_old) == 5 and same_folds:
            d2 = tab - tab_old
            cell.update({"delta_vs_old_tabpfn": d2.mean(), "p_vs_old_tabpfn": stats.ttest_rel(tab, tab_old).pvalue,
                         "new_better_folds_vs_old": int((d2 < 0).sum())})
        rows.append(cell)

    out = pd.DataFrame(rows)
    path = HERE / "version_retest_home_turf_sweep.csv"
    out.to_csv(path, index=False, float_format="%.6g")
    print(f"model version (new sweep): {version}")
    print(f"{'cell':22}{'v3 (Aug)':>10}{'new':>9}{'CAT':>9}{'LGBM':>9}{'XGB':>9}  winner old -> new   "
          f"new - best GBDT (p, folds)      new - v3 (p, folds)           fold gap cat/lgbm/xgb")
    for r in rows:
        vs_old = (f"{r['delta_vs_old_tabpfn']:+.4f} (p={r['p_vs_old_tabpfn']:.3f}, {r['new_better_folds_vs_old']}/5)"
                  if "delta_vs_old_tabpfn" in r else "n/a (folds differ)")
        print(f"{r['dataset'] + '@' + str(r['n_rows']):22}{r['tabpfn_old']:10.4f}{r['tabpfn_new']:9.4f}"
              f"{r['cat']:9.4f}{r['lgbm']:9.4f}{r['xgb']:9.4f}  {r['winner_old']:>6} -> {r['winner_new']:<6}  "
              f"{r['delta_vs_best_gbdt']:+.4f} (p={r['p_vs_best_gbdt']:.3f}, {r['tabpfn_better_folds']}/5)   "
              f"{vs_old:30} " + "/".join(f"{r.get('fold_gap_vs_old_' + m, np.nan):.0e}" for m in GBDTS))
    wins_old = sum(r["winner_old"] == "tabpfn" for r in rows)
    wins_new = sum(r["winner_new"] == "tabpfn" for r in rows)
    print(f"\nTabPFN wins {wins_old}/{len(rows)} cells (committed sweep) -> {wins_new}/{len(rows)} (new)")
    print(f"wrote {path.relative_to(REPO)}")


if __name__ == "__main__":
    main()
