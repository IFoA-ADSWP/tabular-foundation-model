"""Tests for scripts/eval/insurance_benchmark_v1/rescore_altmetrics.py (issue #123).

Fully offline/synthetic — no dependency on real committed .npz files under
predictions/, so these pass on a clean checkout before any capture run has happened.
Same importlib module-load pattern as tests/test_frontier_cli.py.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts/eval/insurance_benchmark_v1/rescore_altmetrics.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("rescore_altmetrics_test", _SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load_module()


# ---- a. inverse_transform -----------------------------------------------

def test_inverse_transform_identity_floor_clip():
    euro, pos_mask, diag = mod.inverse_transform(np.array([-1.0, 0.0, 5.0]), "identity")
    assert euro[0] == mod.FLOOR and euro[1] == mod.FLOOR and euro[2] == 5.0
    assert list(pos_mask) == [False, False, True]
    assert diag["n_floor_clipped"] == 2


def test_inverse_transform_expm1_ceiling_clip_no_overflow():
    # bemtl97_amount's real poissonglm outlier: 2451.76 on the log1p scale. expm1 of
    # that overflows to +inf (float64 exp overflows ~709.78) — must be caught and
    # clipped to EURO_CEILING, not left as inf (which corrupts std()/SE downstream).
    euro, pos_mask, diag = mod.inverse_transform(np.array([2451.76, 1.0]), "expm1")
    assert np.isfinite(euro).all()
    assert euro[0] == mod.EURO_CEILING
    assert diag["n_ceiling_clipped"] == 1
    assert pos_mask[0] and pos_mask[1]


def test_inverse_transform_ceiling_clip_on_large_but_finite_value():
    # a value large enough to be domain-absurd but NOT literally inf under expm1
    # (regression guard: an earlier version only checked for actual overflow-to-inf
    # and missed merely-huge-but-finite results)
    euro, pos_mask, diag = mod.inverse_transform(np.array([50.0]), "expm1")  # expm1(50) ~ 5.18e21
    assert euro[0] == mod.EURO_CEILING
    assert diag["n_ceiling_clipped"] == 1


def test_inverse_transform_exp_normal_range():
    euro, pos_mask, diag = mod.inverse_transform(np.array([np.log(5.0)]), "exp")
    assert euro[0] == pytest.approx(5.0)
    assert diag["n_ceiling_clipped"] == 0 and diag["n_floor_clipped"] == 0


def test_inverse_transform_positive_mask_measured_pre_floor():
    euro, pos_mask, _ = mod.inverse_transform(np.array([-5.0]), "identity")
    assert euro[0] == mod.FLOOR  # floored to a positive value...
    assert pos_mask[0] is np.bool_(False)  # ...but mask reflects the true pre-floor sign


# ---- b. compute_fold_metrics ---------------------------------------------

def test_compute_fold_metrics_full_fold_when_no_zero_mass():
    cfg = dict(scale="log1p", inverse="expm1", metrics=["mae", "gamma_deviance", "tweedie_deviance_p1.5"])
    y_true = np.log1p(np.array([1.0, 2.0, 3.0, 4.0, 5.0]))
    y_pred = np.log1p(np.array([1.1, 2.1, 2.9, 4.2, 5.1]))
    rows = mod.compute_fold_metrics(y_true, y_pred, cfg)
    gamma_row = next(r for r in rows if r["metric"] == "gamma_deviance")
    assert gamma_row["gamma_subset_used"] is False
    assert gamma_row["n_used"] == gamma_row["n_fold"] == 5


def test_compute_fold_metrics_subset_when_zero_mass_present():
    cfg = dict(scale="log1p", inverse="expm1", metrics=["mae", "gamma_deviance", "tweedie_deviance_p1.5"])
    y_true = np.log1p(np.array([0.0, 0.0, 3.0, 4.0, 5.0]))  # 2/5 zero mass
    y_pred = np.log1p(np.array([0.1, 0.0, 2.9, 4.2, 5.1]))
    rows = mod.compute_fold_metrics(y_true, y_pred, cfg)
    gamma_row = next(r for r in rows if r["metric"] == "gamma_deviance")
    assert gamma_row["gamma_subset_used"] is True
    assert gamma_row["n_used"] == 3
    assert gamma_row["zero_mass_frac"] == pytest.approx(0.4)


def test_compute_fold_metrics_applicability_gating():
    cfg = dict(scale="raw", inverse="identity", metrics=["mae"])
    y_true = np.array([0.0, 1.0, 2.0])
    y_pred = np.array([0.1, 1.1, 1.9])
    rows = mod.compute_fold_metrics(y_true, y_pred, cfg)
    assert len(rows) == 1 and rows[0]["metric"] == "mae"


def test_compute_fold_metrics_empty_positive_subset_raises():
    cfg = dict(scale="raw", inverse="identity", metrics=["gamma_deviance"])
    y_true = np.array([0.0, 0.0, 0.0])  # all-zero -> empty positive subset
    y_pred = np.array([1.0, 1.0, 1.0])
    with pytest.raises(AssertionError, match="empty positive subset"):
        mod.compute_fold_metrics(y_true, y_pred, cfg)


def test_compute_fold_metrics_tweedie_full_fold_always():
    cfg = dict(scale="raw", inverse="identity", metrics=["tweedie_deviance_p1.5"])
    y_true = np.array([0.0, 0.0, 3.0, 4.0, 5.0])  # zero mass present
    y_pred = np.array([0.1, 0.2, 2.9, 4.2, 5.1])
    rows = mod.compute_fold_metrics(y_true, y_pred, cfg)
    assert rows[0]["n_used"] == rows[0]["n_fold"] == 5  # not subsetted


# ---- c. mean_se / paired_test ---------------------------------------------

def test_mean_se_basic():
    mean, se = mod.mean_se(pd.Series([1.0, 2.0, 3.0, 4.0, 5.0]))
    assert mean == pytest.approx(3.0)
    assert se == pytest.approx(np.std([1, 2, 3, 4, 5], ddof=1) / np.sqrt(5))


def test_paired_test_zero_variance_branch():
    a = np.array([1.0, 1.0, 1.0])
    b = np.array([1.0, 1.0, 1.0])
    t, p = mod.paired_test(a, b)
    assert np.isnan(t) and np.isnan(p)  # identical deltas, mean==0, sd==0

    b2 = np.array([0.5, 0.5, 0.5])
    t2, p2 = mod.paired_test(a, b2)
    # matches analyze_pr_auc.py's convention verbatim: np.isfinite(inf) is False, so
    # the "0.0 if isfinite(t) else nan" branch yields nan here, not 0.0
    assert np.isinf(t2) and np.isnan(p2)


# ---- d. summarize() -------------------------------------------------------

def _toy_per_fold_df():
    rows = []
    values = {"tabpfn": [1.0, 1.1, 0.9, 1.0, 1.05],
              "ols": [2.0, 2.1, 1.9, 2.0, 2.05],
              "poissonglm": [3.0, 3.1, 2.9, 3.0, 3.05],
              "cat": [1.5, 1.6, 1.4, 1.5, 1.55]}
    for method, vals in values.items():
        for fold, v in enumerate(vals):
            rows.append({"dataset": "toy", "seed": 42, "method": method, "fold": fold,
                        "metric": "mae", "value": v})
    return pd.DataFrame(rows)


def test_summarize_rank_ascending_lower_is_better():
    s = mod.summarize(_toy_per_fold_df())
    order = s.sort_values("rank")["method"].tolist()
    assert order == ["tabpfn", "cat", "ols", "poissonglm"]


def test_summarize_paired_cols_only_on_tabpfn_row():
    s = mod.summarize(_toy_per_fold_df())
    tabpfn_row = s[s.method == "tabpfn"].iloc[0]
    assert pd.notna(tabpfn_row["best_glm"]) and pd.notna(tabpfn_row["p_vs_glm"])
    other_row = s[s.method == "ols"].iloc[0]
    assert pd.isna(other_row["best_glm"]) and pd.isna(other_row["p_vs_glm"])


def test_summarize_best_family_member_is_min_mean():
    s = mod.summarize(_toy_per_fold_df())
    tabpfn_row = s[s.method == "tabpfn"].iloc[0]
    assert tabpfn_row["best_glm"] == "ols"  # ols (mean~2.0) beats poissonglm (mean~3.0)
    assert tabpfn_row["best_gbdt"] == "cat"  # only gbdt-family method present


# ---- e. load_prediction_store / build_per_fold_rows -----------------------

def _write_toy_npz(tmp_path: Path, dataset: str, methods: list[str], n_folds: int,
                    seed: int, problem_type: str = "regression",
                    zero_mass: bool = False) -> Path:
    store = {}
    rng = np.random.default_rng(0)
    for k in range(n_folds):
        n = 6
        y_true = rng.uniform(0.1, 5.0, size=n).astype(np.float32)
        if zero_mass:
            y_true[:2] = 0.0
        store[f"y_true__fold{k}"] = y_true
        store[f"test_idx__fold{k}"] = np.arange(n, dtype=np.int32)
        for m in methods:
            store[f"{m}__fold{k}"] = (y_true + rng.normal(0, 0.1, size=n)).astype(np.float32)

    predictions_dir = tmp_path / "predictions"
    predictions_dir.mkdir(parents=True, exist_ok=True)
    npz_path = predictions_dir / f"{dataset}__seed{seed}.npz"
    manifest_path = predictions_dir / f"{dataset}__seed{seed}.manifest.json"
    np.savez_compressed(npz_path, **store)
    manifest_path.write_text(json.dumps({
        "schema_version": 1, "dataset": dataset, "target": "y", "drop": [],
        "problem_type": problem_type, "primary_metric": "rmse", "n_folds": n_folds,
        "seed": seed, "methods": methods, "model_version": "v3_default",
    }))
    return predictions_dir


def test_load_prediction_store_roundtrip(tmp_path):
    predictions_dir = _write_toy_npz(tmp_path, "toy", mod.METHODS, mod.N_FOLDS, 42)
    loaded = mod.load_prediction_store("toy", 42, predictions_dir)
    assert loaded is not None
    pred_store, manifest = loaded
    assert manifest["dataset"] == "toy"
    assert "y_true__fold0" in pred_store


def test_load_prediction_store_missing_returns_none(tmp_path):
    predictions_dir = tmp_path / "predictions"
    predictions_dir.mkdir()
    assert mod.load_prediction_store("nope", 42, predictions_dir) is None


def test_load_prediction_store_rejects_classification_manifest(tmp_path):
    predictions_dir = _write_toy_npz(tmp_path, "toy", mod.METHODS, mod.N_FOLDS, 42,
                                      problem_type="classification")
    with pytest.raises(AssertionError, match="expected regression"):
        mod.load_prediction_store("toy", 42, predictions_dir)


def test_load_prediction_store_rejects_method_mismatch(tmp_path):
    predictions_dir = _write_toy_npz(tmp_path, "toy", ["ols", "cat"], mod.N_FOLDS, 42)
    with pytest.raises(AssertionError, match="method set mismatch"):
        mod.load_prediction_store("toy", 42, predictions_dir)


def test_build_per_fold_rows_row_count_matches_methods_x_folds_x_metrics(tmp_path):
    # load_prediction_store requires the full METHODS set (guards against a stale/
    # partial capture), so use it here rather than a subset.
    predictions_dir = _write_toy_npz(tmp_path, "toy", mod.METHODS, mod.N_FOLDS, 42)
    pred_store, manifest = mod.load_prediction_store("toy", 42, predictions_dir)
    n_methods = len(mod.METHODS)
    cfg = dict(scale="log1p", inverse="expm1", metrics=["mae", "gamma_deviance", "tweedie_deviance_p1.5"])
    rows = mod.build_per_fold_rows("toy", 42, pred_store, manifest, cfg)
    assert len(rows) == n_methods * mod.N_FOLDS * 3  # methods x folds x metrics

    cfg_count = dict(scale="raw", inverse="identity", metrics=["mae"])
    rows_count = mod.build_per_fold_rows("toy", 42, pred_store, manifest, cfg_count)
    assert len(rows_count) == n_methods * mod.N_FOLDS * 1


# ---- f. sanity_check_altmetrics --------------------------------------------

def test_sanity_check_passes_on_valid_frame(tmp_path):
    predictions_dir = _write_toy_npz(tmp_path, "toy", mod.METHODS, mod.N_FOLDS, 42)
    pred_store, manifest = mod.load_prediction_store("toy", 42, predictions_dir)
    cfg = mod.REG_ALT_CONFIG["ausautoBI8999"]  # full 3-metric config
    rows = mod.build_per_fold_rows("toy", 42, pred_store, manifest, cfg)
    per_fold_df = pd.DataFrame(rows)
    summary_df = mod.summarize(per_fold_df)
    mod.sanity_check_altmetrics(per_fold_df, summary_df)  # should not raise


def test_sanity_check_catches_nonfinite_value():
    per_fold_df = pd.DataFrame([{
        "dataset": "toy", "seed": 42, "method": "tabpfn", "fold": 0, "metric": "mae",
        "value": float("inf"), "n_fold": 5, "n_used": 5, "gamma_subset_used": np.nan,
    }])
    summary_df = pd.DataFrame([{
        "dataset": "toy", "seed": 42, "metric": "mae", "method": "tabpfn", "n_folds": 1,
        "mean": 1.0, "se": 0.1, "rank": 1, "p_vs_glm": np.nan, "p_vs_gbdt": np.nan,
    }])
    with pytest.raises(AssertionError, match="non-finite"):
        mod.sanity_check_altmetrics(per_fold_df, summary_df)


def test_sanity_check_catches_bad_rank_permutation():
    # 5 fold rows per method/metric (matches N_FOLDS) so the earlier fold-count
    # assertion passes and the rank-permutation check is actually what's exercised.
    per_fold_df = pd.DataFrame([
        {"dataset": "toy", "seed": 42, "method": m, "fold": fold, "metric": "mae",
         "value": 1.0, "n_fold": 5, "n_used": 5, "gamma_subset_used": np.nan}
        for m in ("tabpfn", "ols") for fold in range(5)
    ])
    summary_df = pd.DataFrame([
        {"dataset": "toy", "seed": 42, "metric": "mae", "method": "tabpfn", "n_folds": 5,
         "mean": 1.0, "se": 0.1, "rank": 1, "p_vs_glm": np.nan, "p_vs_gbdt": np.nan},
        {"dataset": "toy", "seed": 42, "metric": "mae", "method": "ols", "n_folds": 5,
         "mean": 1.0, "se": 0.1, "rank": 1, "p_vs_glm": np.nan, "p_vs_gbdt": np.nan},  # duplicate rank
    ])
    with pytest.raises(AssertionError, match="not a 1..k permutation"):
        mod.sanity_check_altmetrics(per_fold_df, summary_df)


# ---- g. CLI parsing ---------------------------------------------------------

def test_parse_defaults():
    args = mod.make_parser().parse_args([])
    assert args.filters == [] and args.seed == 42
    assert args.predictions_dir is None and args.out_dir is None


def test_parse_filters_and_seed():
    args = mod.make_parser().parse_args(["ausautoBI8999", "bemtl97_amount", "--seed", "7"])
    assert args.filters == ["ausautoBI8999", "bemtl97_amount"]
    assert args.seed == 7


# ---- h. end-to-end offline smoke -------------------------------------------

def test_main_end_to_end_synthetic(tmp_path, monkeypatch):
    predictions_dir = tmp_path / "predictions"
    predictions_dir.mkdir()
    out_dir = tmp_path / "out"

    # severity-style dataset with zero mass, exercises gamma subsetting
    _write_toy_npz(tmp_path, "spanish_motor_severity", mod.METHODS, mod.N_FOLDS, 42,
                    zero_mass=True)
    # count-style dataset, mae-only applicability
    _write_toy_npz(tmp_path, "freMTPL2freq", mod.METHODS, mod.N_FOLDS, 42)

    argv = ["rescore_altmetrics.py", "spanish_motor_severity", "freMTPL2freq",
            "--predictions-dir", str(predictions_dir), "--out-dir", str(out_dir)]
    monkeypatch.setattr(sys, "argv", argv)
    mod.main()

    per_fold = pd.read_csv(out_dir / "alt_metrics_per_fold.csv")
    summary = pd.read_csv(out_dir / "alt_metrics_summary.csv")

    assert set(per_fold["dataset"].unique()) == {"spanish_motor_severity", "freMTPL2freq"}
    assert set(per_fold[per_fold.dataset == "freMTPL2freq"]["metric"].unique()) == {"mae"}
    assert "gamma_deviance" in per_fold[per_fold.dataset == "spanish_motor_severity"]["metric"].unique()
    expected_per_fold_cols = {
        "dataset", "seed", "method", "fold", "scale", "inverse_fn", "metric", "value",
        "n_fold", "n_used", "zero_mass_frac", "gamma_subset_used",
        "n_true_floor_clipped", "n_true_ceiling_clipped",
        "n_pred_floor_clipped", "n_pred_ceiling_clipped",
    }
    assert expected_per_fold_cols == set(per_fold.columns)
    expected_summary_cols = {
        "dataset", "seed", "metric", "method", "n_folds", "mean", "se", "rank",
        "best_glm", "delta_vs_glm", "t_vs_glm", "p_vs_glm",
        "best_gbdt", "delta_vs_gbdt", "t_vs_gbdt", "p_vs_gbdt",
    }
    assert expected_summary_cols == set(summary.columns)


def test_main_skips_missing_dataset(tmp_path, monkeypatch, capsys):
    predictions_dir = tmp_path / "predictions"
    predictions_dir.mkdir()
    out_dir = tmp_path / "out"
    _write_toy_npz(tmp_path, "freMTPL2freq", mod.METHODS, mod.N_FOLDS, 42)

    argv = ["rescore_altmetrics.py", "--predictions-dir", str(predictions_dir),
            "--out-dir", str(out_dir)]
    monkeypatch.setattr(sys, "argv", argv)
    mod.main()
    captured = capsys.readouterr()
    assert "SKIP ausautoBI8999" in captured.out  # not captured, should be skipped not fatal


def test_main_exits_nonzero_when_nothing_captured(tmp_path, monkeypatch):
    predictions_dir = tmp_path / "predictions"
    predictions_dir.mkdir()
    argv = ["rescore_altmetrics.py", "--predictions-dir", str(predictions_dir),
            "--out-dir", str(tmp_path / "out")]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit) as exc_info:
        mod.main()
    assert exc_info.value.code == 1
