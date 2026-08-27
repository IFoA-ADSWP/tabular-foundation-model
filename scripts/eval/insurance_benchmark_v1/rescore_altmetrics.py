"""Alternative-metrics re-score for the regression frontier benchmarks (issue #123).

Reads captured per-fold predictions written by run_frontier_benchmark.py's
--save-predictions (#122): predictions/<dataset>__seed<seed>.npz + .manifest.json.
For each of the 6 regression datasets, computes MAE / Gamma deviance / Tweedie
deviance (p=1.5) on the EURO (or count) scale, inverse-transforming stored
log/log1p predictions per docs/analyses/altmetrics_rescore_spec.md §3. No refits,
no hosted-API calls — CPU-only, seconds to run, zero new dependencies (sklearn only).

RMSE/Poisson-deviance (the existing primary metrics) are NOT recomputed here — they
stay in frontier_results_<dataset>.csv, unchanged (spec §3 row 4, "existing
primary... unchanged"). This script strictly adds the 3 new metrics.

Gamma-deviance full-fold-vs-positive-subset is decided dynamically per fold, from
observed y_true zero mass after inverse-transform (spec marks this "verify at impl.");
not hardcoded per dataset. Tweedie(1.5) is skipped entirely (no row emitted) on the two
count datasets (freMTPL2freq, spanish_motor_freq) — pure-premium framing needs
exposure/premium data not in the benchmark (spec §8 Q4).

Outputs (same dir as this script by default):
  alt_metrics_per_fold.csv   dataset,seed,method,fold,metric,value,+scale-handling flags
  alt_metrics_summary.csv    dataset,seed,metric,method,mean,se,rank,+paired-test cols
                             (paired-test cols populated on tabpfn's row only)

Usage:
    python scripts/eval/insurance_benchmark_v1/rescore_altmetrics.py                       # all 6 datasets, seed 42
    python scripts/eval/insurance_benchmark_v1/rescore_altmetrics.py bemtl97_amount ausautoBI8999  # subset, case-insensitive
    python scripts/eval/insurance_benchmark_v1/rescore_altmetrics.py --seed 7              # a different capture seed
    python scripts/eval/insurance_benchmark_v1/rescore_altmetrics.py --predictions-dir /tmp/preds --out-dir /tmp/out
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import mean_absolute_error, mean_gamma_deviance, mean_tweedie_deviance

HERE = Path(__file__).resolve().parent
PREDICTIONS_DIR = HERE / "predictions"
PER_FOLD_CSV = HERE / "alt_metrics_per_fold.csv"
SUMMARY_CSV = HERE / "alt_metrics_summary.csv"

N_FOLDS = 5
FLOOR = 1e-9        # post-inverse floor guard (Gamma/Tweedie need y > 0; spec §3)
EURO_CEILING = 1e7  # post-inverse ceiling guard, domain-reasonable (no claim/severity
                    # value in this benchmark plausibly exceeds ~1e5-1e6; 1e7 is a
                    # generous margin). Real case this guards against: bemtl97_amount's
                    # poissonglm predicts 2451.76 on the log1p scale in one fold — a
                    # PRE-inverse clip near float64's overflow point (~710) still lets
                    # expm1 produce a "finite" but physically absurd ~1e304, which then
                    # overflows to inf when squared inside std()/SE. Clipping the actual
                    # euro-scale RESULT to a sane domain bound avoids both the raw
                    # overflow and the downstream squaring overflow.

METHODS = ["ols", "poissonglm", "tweedieglm", "rf", "cat", "lgbm", "xgb", "tabpfn"]
GLM_FAMILY = ["ols", "poissonglm", "tweedieglm"]   # regression-mode analog of analyze_pr_auc.GLM_FAMILY; rf excluded, same as that precedent
GBDT_FAMILY = ["cat", "lgbm", "xgb"]

# Per-dataset applicability + inverse-transform config (spec §3, docs/analyses/altmetrics_rescore_spec.md).
REG_ALT_CONFIG: dict[str, dict] = {
    "ausautoBI8999":            dict(scale="log",   inverse="exp",      metrics=["mae", "gamma_deviance", "tweedie_deviance_p1.5"]),
    "bemtl97_amount":           dict(scale="log1p",  inverse="expm1",    metrics=["mae", "gamma_deviance", "tweedie_deviance_p1.5"]),
    "spanish_motor_severity":   dict(scale="log1p",  inverse="expm1",    metrics=["mae", "gamma_deviance", "tweedie_deviance_p1.5"]),
    "ausprivauto0405_vehvalue": dict(scale="raw",    inverse="identity", metrics=["mae", "gamma_deviance", "tweedie_deviance_p1.5"]),
    "freMTPL2freq":             dict(scale="raw",    inverse="identity", metrics=["mae"]),
    "spanish_motor_freq":       dict(scale="raw",    inverse="identity", metrics=["mae"]),
}


# ---------------------------------------------------------------------------
# Scale handling
# ---------------------------------------------------------------------------
def inverse_transform(values: np.ndarray, inverse: str) -> tuple[np.ndarray, np.ndarray, dict]:
    """Apply exp/expm1/identity to move stored-scale values to the euro/count scale.

    Returns (euro, positive_mask, diagnostics):
      euro           — inverse-transformed values, clipped to [FLOOR, EURO_CEILING].
                        Both guards apply AFTER the inverse transform — the only
                        reading of the spec's floor-guard sentence that actually
                        protects Gamma deviance's positivity requirement, and
                        (for the ceiling) the only guard that targets the quantity
                        that actually matters: the euro-scale value itself, not an
                        arbitrary pre-transform cutoff based on float64's technical
                        overflow point (which still permits physically-absurd
                        "finite" results that overflow downstream when squared).
      positive_mask  — True where the PRE-floor-clip inverse value was > 0, so real
                        zero/negative mass isn't hidden by the floor guard. Computed
                        after the ceiling clip, which never changes sign (it only
                        caps already-large-positive values).
      diagnostics    — clip counts, for the per-fold CSV's diagnostic columns.
    """
    raw = np.asarray(values, dtype=np.float64)
    with np.errstate(over="ignore"):
        if inverse == "exp":
            euro_raw = np.exp(raw)
        elif inverse == "expm1":
            euro_raw = np.expm1(raw)
        elif inverse == "identity":
            euro_raw = raw
        else:
            raise ValueError(f"unknown inverse transform: {inverse!r}")
    # np.exp/expm1 overflow to actual +inf for large enough raw inputs; count those
    # together with any merely-huge-but-finite value exceeding the ceiling, BEFORE
    # replacing either case with the clip (order matters: inf > EURO_CEILING is True,
    # but only until it's been overwritten).
    n_ceiling_clipped = int((np.isposinf(euro_raw) | (euro_raw > EURO_CEILING)).sum())
    euro_raw = np.where(np.isposinf(euro_raw), EURO_CEILING, euro_raw)
    euro_raw = np.clip(euro_raw, None, EURO_CEILING)

    positive_mask = euro_raw > 0
    n_floor_clipped = int((euro_raw < FLOOR).sum())
    euro = np.clip(euro_raw, FLOOR, None)
    diagnostics = {"n_floor_clipped": n_floor_clipped, "n_ceiling_clipped": n_ceiling_clipped}
    return euro, positive_mask, diagnostics


# ---------------------------------------------------------------------------
# Per-fold metric computation
# ---------------------------------------------------------------------------
def compute_fold_metrics(y_true_raw: np.ndarray, y_pred_raw: np.ndarray, cfg: dict) -> list[dict]:
    """For one (method, fold): inverse-transform both arrays, compute every metric in
    cfg['metrics'] with its masking rule, return one dict per applicable metric."""
    inverse = cfg["inverse"]
    y_true_euro, y_true_pos_mask, true_diag = inverse_transform(y_true_raw, inverse)
    y_pred_euro, y_pred_pos_mask, pred_diag = inverse_transform(y_pred_raw, inverse)

    n_fold = len(y_true_euro)
    # Gamma deviance needs both arrays strictly positive; y_pred is already guaranteed
    # > 0 post floor-clip, so only y_true's zero mass drives subsetting.
    gamma_mask = y_true_pos_mask
    zero_mass_frac = float((~gamma_mask).sum()) / n_fold

    rows: list[dict] = []
    base = {
        "n_fold": n_fold,
        "zero_mass_frac": zero_mass_frac,
        "n_true_floor_clipped": true_diag["n_floor_clipped"],
        "n_true_ceiling_clipped": true_diag["n_ceiling_clipped"],
        "n_pred_floor_clipped": pred_diag["n_floor_clipped"],
        "n_pred_ceiling_clipped": pred_diag["n_ceiling_clipped"],
    }

    if "mae" in cfg["metrics"]:
        rows.append({
            **base, "metric": "mae", "value": float(mean_absolute_error(y_true_euro, y_pred_euro)),
            "n_used": n_fold, "gamma_subset_used": np.nan,
        })

    if "tweedie_deviance_p1.5" in cfg["metrics"]:
        assert (y_true_euro >= 0).all(), "tweedie deviance: y_true not >= 0 after inverse transform"
        assert (y_pred_euro > 0).all(), "tweedie deviance: y_pred not > 0 after inverse transform + floor"
        rows.append({
            **base, "metric": "tweedie_deviance_p1.5",
            "value": float(mean_tweedie_deviance(y_true_euro, y_pred_euro, power=1.5)),
            "n_used": n_fold, "gamma_subset_used": np.nan,
        })

    if "gamma_deviance" in cfg["metrics"]:
        subset_used = not gamma_mask.all()
        yt = y_true_euro[gamma_mask]
        yp = y_pred_euro[gamma_mask]
        n_used = int(gamma_mask.sum())
        assert n_used > 0, "gamma deviance: empty positive subset"
        assert (yt > 0).all() and (yp > 0).all(), "gamma deviance: subset not strictly positive"
        rows.append({
            **base, "metric": "gamma_deviance", "value": float(mean_gamma_deviance(yt, yp)),
            "n_used": n_used, "gamma_subset_used": subset_used,
        })

    return rows


# ---------------------------------------------------------------------------
# Loading captured predictions
# ---------------------------------------------------------------------------
def load_prediction_store(dataset: str, seed: int, predictions_dir: Path) -> tuple[dict[str, np.ndarray], dict] | None:
    """Load predictions/<dataset>__seed<seed>.npz + sibling .manifest.json. Returns None
    if the capture doesn't exist (caller decides whether that's a skip or an error).
    Asserts the manifest matches expectations (regression, right dataset, right methods)
    so a stale/partial capture never rescoring silently."""
    npz_path = predictions_dir / f"{dataset}__seed{seed}.npz"
    manifest_path = predictions_dir / f"{dataset}__seed{seed}.manifest.json"
    if not npz_path.exists() or not manifest_path.exists():
        return None

    manifest = json.loads(manifest_path.read_text())
    assert manifest["problem_type"] == "regression", f"{dataset}: expected regression manifest, got {manifest['problem_type']}"
    assert manifest["dataset"] == dataset, f"manifest dataset mismatch: {manifest['dataset']} != {dataset}"
    assert set(manifest["methods"]) == set(METHODS), f"{dataset}: method set mismatch: {manifest['methods']}"

    data = np.load(npz_path)
    pred_store = {k: data[k] for k in data.files}
    return pred_store, manifest


def build_per_fold_rows(dataset: str, seed: int, pred_store: dict, manifest: dict, cfg: dict) -> list[dict]:
    """Iterate methods x folds, call compute_fold_metrics, prepend identifying columns."""
    n_folds = manifest["n_folds"]
    assert n_folds == N_FOLDS, f"{dataset}: expected {N_FOLDS} folds, manifest says {n_folds}"

    rows: list[dict] = []
    for method in METHODS:
        for fold in range(n_folds):
            y_true = pred_store[f"y_true__fold{fold}"]
            y_pred = pred_store[f"{method}__fold{fold}"]
            for m in compute_fold_metrics(y_true, y_pred, cfg):
                rows.append({
                    "dataset": dataset, "seed": seed, "method": method, "fold": fold,
                    "scale": cfg["scale"], "inverse_fn": cfg["inverse"], **m,
                })
    return rows


# ---------------------------------------------------------------------------
# Statistics (identical convention to analyze_pr_auc.py: mean_se, paired_test)
# ---------------------------------------------------------------------------
def mean_se(values: pd.Series) -> tuple[float, float]:
    v = values.to_numpy(dtype=float)
    n = len(v)
    return float(v.mean()), float(v.std(ddof=1)) / np.sqrt(n)


def paired_test(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    """Paired t-test on per-fold deltas (a - b), df = n-1, two-sided."""
    d = a - b
    n = len(d)
    sd = d.std(ddof=1)
    if sd == 0:
        t = float(np.inf) if d.mean() != 0 else float("nan")
        return t, (0.0 if np.isfinite(t) else float("nan"))
    t = d.mean() / (sd / np.sqrt(n))
    p = 2.0 * stats.t.sf(abs(t), n - 1)
    return float(t), float(p)


def summarize(per_fold_df: pd.DataFrame) -> pd.DataFrame:
    """Per (dataset, seed, metric): mean/SE/rank per method; on the tabpfn row only,
    paired-test deltas vs the best GLM-family member and best GBDT-family member.
    Lower is always better for mae/gamma_deviance/tweedie_deviance_p1.5 (no DIRECTION
    dict needed, unlike analyze_pr_auc.py's mixed-direction classification metrics)."""
    rows: list[dict] = []
    for (dataset, seed, metric), sub in per_fold_df.groupby(["dataset", "seed", "metric"]):
        means: dict[str, tuple[float, float]] = {}
        folds: dict[str, np.ndarray] = {}
        for method, msub in sub.groupby("method"):
            means[method] = mean_se(msub["value"])
            folds[method] = msub.sort_values("fold")["value"].to_numpy(dtype=float)

        order = sorted(means, key=lambda m: means[m][0])  # ascending: lower is better
        ranks = {m: i + 1 for i, m in enumerate(order)}

        best_glm = min((m for m in GLM_FAMILY if m in means), key=lambda m: means[m][0], default=None)
        best_gbdt = min((m for m in GBDT_FAMILY if m in means), key=lambda m: means[m][0], default=None)

        for method, (mean, se) in means.items():
            row = {
                "dataset": dataset, "seed": seed, "metric": metric, "method": method,
                "n_folds": len(folds[method]), "mean": mean, "se": se, "rank": ranks[method],
                "best_glm": np.nan, "delta_vs_glm": np.nan, "t_vs_glm": np.nan, "p_vs_glm": np.nan,
                "best_gbdt": np.nan, "delta_vs_gbdt": np.nan, "t_vs_gbdt": np.nan, "p_vs_gbdt": np.nan,
            }
            if method == "tabpfn":
                if best_glm is not None:
                    t, p = paired_test(folds["tabpfn"], folds[best_glm])
                    row.update(best_glm=best_glm, delta_vs_glm=mean - means[best_glm][0], t_vs_glm=t, p_vs_glm=p)
                if best_gbdt is not None:
                    t, p = paired_test(folds["tabpfn"], folds[best_gbdt])
                    row.update(best_gbdt=best_gbdt, delta_vs_gbdt=mean - means[best_gbdt][0], t_vs_gbdt=t, p_vs_gbdt=p)
            rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Self-check (repo assert convention)
# ---------------------------------------------------------------------------
def sanity_check_altmetrics(per_fold_df: pd.DataFrame, summary_df: pd.DataFrame) -> None:
    assert per_fold_df["value"].notna().all(), "NaN in per-fold metric values"
    assert np.isfinite(per_fold_df["value"]).all(), "non-finite (inf) metric value — overflow guard failed"

    counts = per_fold_df.groupby(["dataset", "seed", "method", "metric"]).size()
    assert (counts == N_FOLDS).all(), f"expected {N_FOLDS} fold rows per method/metric, found mismatches"

    for ds in ("freMTPL2freq", "spanish_motor_freq"):
        sub = per_fold_df[per_fold_df.dataset == ds]
        if not sub.empty:
            assert set(sub.metric.unique()) == {"mae"}, f"{ds}: unexpected metrics {sub.metric.unique()}"

    g = per_fold_df[per_fold_df.metric == "gamma_deviance"]
    if not g.empty:
        subset_rows = g[g.gamma_subset_used == True]  # noqa: E712 (explicit bool compare vs NaN)
        full_rows = g[g.gamma_subset_used == False]  # noqa: E712
        assert (subset_rows["n_used"] < subset_rows["n_fold"]).all(), "subset flagged but n_used >= n_fold"
        assert (full_rows["n_used"] == full_rows["n_fold"]).all(), "full-fold flagged but n_used != n_fold"
        assert (g["n_used"] > 0).all(), "empty gamma-deviance subset slipped through"

    assert summary_df[["mean", "se", "rank"]].notna().all().all(), "NaN in summary mean/se/rank"
    assert np.isfinite(summary_df[["mean", "se"]].to_numpy(dtype=float)).all(), (
        "non-finite (inf) summary mean/se — a per-fold value was too extreme even after "
        "the euro-scale ceiling clip; notna() alone doesn't catch inf"
    )
    for _, sub in summary_df.groupby(["dataset", "seed", "metric"]):
        assert sorted(sub["rank"]) == list(range(1, len(sub) + 1)), "rank is not a 1..k permutation"
    for col in ("p_vs_glm", "p_vs_gbdt"):
        vals = summary_df[col].dropna()
        if len(vals):
            assert vals.between(0.0, 1.0).all(), f"{col} outside [0, 1]"

    print(f"SELF-CHECK OK: {len(per_fold_df)} per-fold rows, {len(summary_df)} summary rows")


# ---------------------------------------------------------------------------
# CLI / main
# ---------------------------------------------------------------------------
def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rescore_altmetrics.py",
        description="Alternative-metrics (MAE / Gamma deviance / Tweedie p=1.5) re-score "
                    "of captured regression predictions (issue #123, consumes #122 artefacts).",
    )
    parser.add_argument(
        "filters", nargs="*", metavar="DATASET",
        help="case-insensitive dataset-name filter(s) into REG_ALT_CONFIG; "
             "empty = all 6 datasets with a captured .npz for --seed",
    )
    parser.add_argument("--seed", type=int, default=42, metavar="N",
                        help="only rescore predictions captured with this split seed "
                             "(default 42; matches run_frontier_benchmark.py --save-predictions --seed)")
    parser.add_argument("--predictions-dir", metavar="DIR", default=None,
                        help="override predictions/ directory (default: <script-dir>/predictions)")
    parser.add_argument("--out-dir", metavar="DIR", default=None,
                        help="override output directory for the two CSVs "
                             "(default: <script-dir>, beside frontier_results_*.csv)")
    return parser


def main() -> None:
    parser = make_parser()
    args = parser.parse_args()

    predictions_dir = Path(args.predictions_dir) if args.predictions_dir else PREDICTIONS_DIR
    out_dir = Path(args.out_dir) if args.out_dir else HERE
    out_dir.mkdir(parents=True, exist_ok=True)

    wanted = {f.lower() for f in args.filters} if args.filters else None
    datasets = [d for d in REG_ALT_CONFIG if wanted is None or d.lower() in wanted]

    all_rows: list[dict] = []
    for dataset in datasets:
        cfg = REG_ALT_CONFIG[dataset]
        loaded = load_prediction_store(dataset, args.seed, predictions_dir)
        if loaded is None:
            print(f"SKIP {dataset}: no capture at {predictions_dir}/{dataset}__seed{args.seed}.npz")
            continue
        pred_store, manifest = loaded
        if len(cfg["metrics"]) < 3:
            print(f"  {dataset}: count target, computing {cfg['metrics']} only "
                  f"(gamma n/a, tweedie out of scope per spec §8 Q4)")
        all_rows.extend(build_per_fold_rows(dataset, args.seed, pred_store, manifest, cfg))

    if not all_rows:
        print("no datasets captured — nothing to rescore", file=__import__("sys").stderr)
        raise SystemExit(1)

    per_fold_df = pd.DataFrame(all_rows)
    summary_df = summarize(per_fold_df)
    sanity_check_altmetrics(per_fold_df, summary_df)

    per_fold_path = out_dir / PER_FOLD_CSV.name
    summary_path = out_dir / SUMMARY_CSV.name
    per_fold_df.to_csv(per_fold_path, index=False)
    summary_df.to_csv(summary_path, index=False)
    print(f"wrote {per_fold_path} ({len(per_fold_df)} rows)")
    print(f"wrote {summary_path} ({len(summary_df)} rows)")


if __name__ == "__main__":
    main()
