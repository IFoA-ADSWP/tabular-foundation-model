"""Measure the four pinned lapse students on the teacher's own folds (issue #377).

#370 reported the two lapse Datasets from **estimates**: CatBoost, XGBoost and RandomForest were
never fitted at full size (`run_lapse_benchmark.py` lists them under
`# --- Deferred to the GPU run ---`), and the committed `LinearModel` row turned out to be
TabArena's `LinearModel`, not `src/baseline_config.py`'s pinned `logistic_regression`
(`scripts/eval/lapse_benchmark_v1/method_info.csv`). This script replaces those estimates with a
measurement on the same five folds the teacher was scored on.

What it does, and what it deliberately does not:

* **Reuses the teacher.** Per-fold AUCs are read from the committed
  `scripts/eval/lapse_benchmark_v1/results_per_split.csv`. There is no teacher code path here:
  this module imports no `tabpfn_client`, reads no API key and cannot spend. The re-scored means
  are checked against the published `v3_default` numbers (0.6101 / 0.7553) before anything is
  written -- a mismatch is a version-era mismatch, not a result.
* **Does not refit the teacher's Brier.** The committed lapse record holds no teacher
  probabilities, so teacher Brier is recorded as unknown with a reason rather than estimated
  from the 2,000-row pilot.
* **Fits only students, CPU, at the pinned configs** from `src/baseline_config.py`.
* **Writes a committed Record** under `results/20261031-lapse-students/` (per-fold scores, the
  per-fold predictions, and one `provenance` block per `docs/plans/record-contract.md`). #370's
  per-fold output went to `/tmp/opencode` and was lost; that is the failure this file exists to
  prevent, so an existing record is refused rather than overwritten.

Preprocessing is the repository's home-harness convention (`object`/`category` -> `.cat.codes`,
`fillna(0)`, float32) -- the same convention that produced the measured coil2000/uslapseagent
student rows in #370. The reused teacher rows came from TabArena's pipeline, so the gap carries a
pipeline asymmetry; a LightGBM **control** is fitted on the same folds and diffed against the
committed TabArena `[Lapse] GBM` row to size that asymmetry instead of assuming it away.

Usage:
    python scripts/benchmarks/measure_lapse_students.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))  # repo root, so `src.` imports resolve

from src.baseline_config import BASELINE_MODELS, RANDOM_SEED  # noqa: E402
from src.provenance import (  # noqa: E402
    CAPTURE_KIND,
    CAPTURE_SCHEMA_VERSION,
    code_section,
    dataset_fingerprint,
    git_revision,
    model_section,
    provenance_block,
    sha256_file,
    split_rule,
    split_section,
    verdict,
)

DATA_RAW = REPO / "data" / "raw"
COMMITTED_RESULTS = REPO / "scripts" / "eval" / "lapse_benchmark_v1" / "results_per_split.csv"
OUT_DIR = REPO / "results" / "20261031-lapse-students"

TEACHER_METHOD = "[Lapse] TabPFNClient (default)"
LINEAR_METHOD = "[Lapse] LR (default)"
LGBM_METHOD = "[Lapse] GBM (default)"

# The published v3_default per-fold means (docs/MODEL_VERSIONS.md, master report §14.10). The
# reused rows are only usable if they still land here; a miss is a model-era mismatch.
PUBLISHED_TEACHER_MEAN_AUC = {"eudirectlapse": 0.6101, "spanish_motor_lapse": 0.7553}
TEACHER_MEAN_TOLERANCE = 5e-5  # the published values are rounded to 4 dp

N_FOLDS = 5
SEED = RANDOM_SEED

DATASETS = {
    "eudirectlapse": {"file": "eudirectlapse.csv", "target": "lapse"},
    "spanish_motor_lapse": {"file": "spanish_motor_lapse.csv", "target": "LapseB"},
}


# ---------------------------------------------------------------------------
# Loading and folds — the lapse benchmark's rule, rebuilt
# ---------------------------------------------------------------------------
def load_Xy(info: dict) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """The frame, the binary target, and the feature matrix in the home-harness encoding."""
    frame = pd.read_csv(DATA_RAW / info["file"]).dropna(subset=[info["target"]])
    frame = frame.reset_index(drop=True)
    y = frame[info["target"]].to_numpy(dtype=np.int64)
    X = frame.drop(columns=[info["target"]])
    for col in X.select_dtypes(include=["object", "category"]).columns:
        X[col] = X[col].astype("category").cat.codes.replace(-1, np.nan)
    return frame, y, X.fillna(0.0).astype(np.float32).to_numpy(dtype=np.float32)


def make_folds(y: np.ndarray) -> list[tuple[np.ndarray, np.ndarray]]:
    """`StratifiedKFold(n_splits=5, shuffle=True, random_state=42)` — the benchmark's rule."""
    return list(
        StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED).split(np.zeros(len(y)), y)
    )


def fold_sha(folds: list[tuple[np.ndarray, np.ndarray]]) -> str:
    """One hash over every fold's train and test indices, in fold order."""
    h = sha256()
    for train_idx, test_idx in folds:
        for idx in (train_idx, test_idx):
            h.update(np.ascontiguousarray(idx, dtype=np.int64).tobytes())
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Students — pinned configs, nothing tuned here
# ---------------------------------------------------------------------------
def student_factories() -> dict[str, Callable[[], object]]:
    """The four students pinned in `src/baseline_config.BASELINE_MODELS`."""
    from catboost import CatBoostClassifier
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from xgboost import XGBClassifier

    return {
        # allow_writing_files=False is I/O hygiene, not a model parameter: CatBoost otherwise
        # drops a catboost_info/ tree into the working directory (AGENTS.md: experiment output).
        "catboost": lambda: CatBoostClassifier(
            **BASELINE_MODELS["catboost"], allow_writing_files=False
        ),
        "xgboost": lambda: XGBClassifier(**BASELINE_MODELS["xgboost"]),
        "random_forest": lambda: RandomForestClassifier(**BASELINE_MODELS["random_forest"]),
        "logistic_regression": lambda: LogisticRegression(**BASELINE_MODELS["logistic_regression"]),
    }


def lightgbm_control():
    """Not a pinned student: the row that sizes the pipeline asymmetry against TabArena's GBM."""
    from lightgbm import LGBMClassifier

    return LGBMClassifier(random_state=0, device_type="cpu", verbose=-1)


def scale_sensitive_factories() -> dict[str, Callable[[], object]]:
    """Sensitivity arms, not pinned students: same model, the encoding it needs to converge.

    The pinned `logistic_regression` config carries no scaler, and on raw category codes plus
    premium columns lbfgs hits its iteration limit. That makes the pinned arm a *lower bound*
    on linear performance, which matters because #370's eudirectlapse claim is that a linear
    model beats the teacher. The scaled arm says how much of the linear result is the model and
    how much is the missing scaler.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    return {
        "logistic_regression_scaled": lambda: make_pipeline(
            StandardScaler(), LogisticRegression(**BASELINE_MODELS["logistic_regression"])
        ),
    }



def fit_and_score(name, build, X, y, folds, role) -> list[dict]:
    rows = []
    for fold, (train_idx, test_idx) in enumerate(folds):
        model = build()
        model.fit(X[train_idx], y[train_idx])
        proba = model.predict_proba(X[test_idx])[:, 1]
        rows.append(
            {
                "fold": fold,
                "method": name,
                "role": role,
                "auc": float(roc_auc_score(y[test_idx], proba)),
                "brier": float(brier_score_loss(y[test_idx], proba)),
                "n_test": int(len(test_idx)),
                "y_true": y[test_idx],
                "y_pred": proba,
                "test_idx": test_idx,
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Teacher and proxy rows — reused, never refitted
# ---------------------------------------------------------------------------
def reused_rows(committed: pd.DataFrame, dataset_id: str) -> list[dict]:
    """The teacher, the LinearModel proxy and the TabArena GBM, straight from the record."""
    rows = []
    for method, name, role in (
        (TEACHER_METHOD, "tabpfn", "teacher"),
        (LINEAR_METHOD, "LinearModel", "committed-proxy"),
        (LGBM_METHOD, "lightgbm_tabarena", "committed-proxy"),
    ):
        sub = committed[(committed["dataset"] == dataset_id) & (committed["method"] == method)]
        if len(sub) != N_FOLDS:
            raise RuntimeError(f"{dataset_id}: expected {N_FOLDS} committed rows for {method!r}, got {len(sub)}")
        for _, r in sub.sort_values("fold").iterrows():
            rows.append(
                {
                    "fold": int(r["fold"]),
                    "method": name,
                    "role": role,
                    "auc": float(1.0 - r["metric_error"]),  # roc_auc error convention
                    # No committed teacher/proxy probabilities -> no Brier. Stated, not guessed.
                    "brier": None,
                    "n_test": None,
                }
            )
    return rows


def mean_se(values) -> tuple[float, float]:
    v = np.asarray(values, dtype=float)
    return float(v.mean()), float(v.std(ddof=1) / np.sqrt(len(v)))


def summarise(dataset: str, rows: list[dict]) -> dict:
    """Per-method mean ± SE, the teacher-minus-student gap, and the D3 test on each student."""
    by_method: dict[str, list[dict]] = {}
    for r in rows:
        by_method.setdefault(r["method"], []).append(r)

    teacher_mean, teacher_se = mean_se([r["auc"] for r in by_method["tabpfn"]])
    methods = {}
    for name, rs in by_method.items():
        m, se = mean_se([r["auc"] for r in rs])
        briers = [r["brier"] for r in rs if r["brier"] is not None]
        methods[name] = {
            "role": rs[0]["role"],
            "mean_auc": m,
            "se_auc": se,
            "mean_brier": float(np.mean(briers)) if briers else None,
            "brier_note": None if briers else "no committed probabilities; not measurable without a teacher call",
        }

    students = {k: v for k, v in methods.items() if v["role"] == "student"}
    # The map's gap rule is "teacher minus the best tuned GBDT (catboost, xgboost, lightgbm,
    # random_forest)" (#368). LightGBM is a committed harness row and is reproduced by the
    # local control, so both count toward the family; linear models never do.
    gbdt = {
        k: v
        for k, v in methods.items()
        if k in {"catboost", "xgboost", "random_forest", "lightgbm_tabarena", "lightgbm_control"}
    }

    def gap_for(pool: dict) -> dict | None:
        if not pool:
            return None
        best = max(pool, key=lambda k: pool[k]["mean_auc"])
        return {
            "best_student": best,
            "best_mean_auc": pool[best]["mean_auc"],
            "best_se_auc": pool[best]["se_auc"],
            "gap_auc": teacher_mean - pool[best]["mean_auc"],
            # The D3 rule, GLOSSARY.md: best_student_mean + SE < teacher_mean - SE.
            "d3_clears": bool(
                pool[best]["mean_auc"] + pool[best]["se_auc"] < teacher_mean - teacher_se
            ),
            "method": "D3: best_student_mean + SE_best < teacher_mean - SE_teacher (GLOSSARY.md, Frontier)",
        }

    return {
        "dataset": dataset,
        "teacher_mean_auc": teacher_mean,
        "teacher_se_auc": teacher_se,
        "methods": methods,
        "best_pinned_student_gap": gap_for(students),
        "best_gbdt_gap": gap_for(gbdt),
    }


# ---------------------------------------------------------------------------
# Capture hashing — the scheme the committed prediction manifests use
# ---------------------------------------------------------------------------
def predictions_sha256(arrays: dict[str, np.ndarray]) -> str:
    h = sha256()
    for key in sorted(arrays):
        arr = np.ascontiguousarray(arrays[key])
        h.update(key.encode())
        h.update(b"\0")
        h.update(arr.dtype.str.encode())
        h.update(b"\0")
        h.update(str(arr.shape).encode())
        h.update(b"\0")
        h.update(arr.tobytes())
    return h.hexdigest()


def _runtime() -> dict:
    import sklearn

    versions = {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__, "scikit-learn": sklearn.__version__}
    for name in ("xgboost", "catboost", "lightgbm"):
        try:
            module = __import__(name)
            versions[name] = getattr(module, "__version__", "unknown")
        except ImportError:  # stated absence, not a silent one
            versions[name] = None
    versions["accelerator"] = "cpu"
    versions["tabpfn_client"] = None  # never imported by this script
    return versions


def combined_split_sha(splits: list[dict]) -> str:
    """One hash over the per-dataset fold hashes, keyed by dataset, in DATASETS order.

    The record contract's `split.sha256` is one value, and this is a run-level record over two
    Datasets; folding them in one keyed hash keeps the section comparable while
    `measurements.split_index_sha256` keeps the per-Dataset values addressable.
    """
    h = sha256()
    for s in splits:
        h.update(f"{s['dataset']}:{s['sha256']}".encode())
        h.update(b"\0")
    return h.hexdigest()


def pipeline_asymmetry(per_fold: list[dict]) -> dict:
    """Size the teacher/student pipeline difference with the LightGBM control.

    The same model the committed `[Lapse] GBM` row names is fitted here under the home
    encoding. Agreement says the home pipeline and the folds land where TabArena's rows
    landed, so a student-vs-reused-teacher gap is not dominated by the encoding; a delta is
    reported as the size of the confound rather than waved away.
    """
    out = {
        "what": (
            "lightgbm_control (fitted here) minus lightgbm_tabarena (committed [Lapse] GBM row), "
            "mean AUC per dataset"
        ),
        "datasets": {},
    }
    datasets = sorted({r["dataset"] for r in per_fold})
    for ds in datasets:
        control = {r["fold"]: r["auc"] for r in per_fold if r["dataset"] == ds and r["method"] == "lightgbm_control"}
        committed = {r["fold"]: r["auc"] for r in per_fold if r["dataset"] == ds and r["method"] == "lightgbm_tabarena"}
        if not (control and committed):
            continue
        per_fold_delta = [control[f] - committed[f] for f in sorted(control.keys() & committed.keys())]
        out["datasets"][ds] = {
            "control_mean_auc": float(np.mean(list(control.values()))),
            "committed_mean_auc": float(np.mean(list(committed.values()))),
            "delta_mean_auc": float(np.mean(list(control.values())) - np.mean(list(committed.values()))),
            "delta_max_abs_per_fold": float(np.max(np.abs(per_fold_delta))),
        }
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    if (OUT_DIR / "record.json").exists():
        print(
            f"refusing to overwrite {OUT_DIR / 'record.json'}: a record's created_utc and git sha "
            "describe the run that produced it; a second run is a second record",
            file=sys.stderr,
        )
        return 2

    committed = pd.read_csv(COMMITTED_RESULTS)
    committed_sha = sha256_file(COMMITTED_RESULTS)

    per_fold: list[dict] = []
    datasets_meta: list[dict] = []
    captures: dict[str, np.ndarray] = {}
    summaries: list[dict] = []
    splits: list[dict] = []

    for dataset, info in DATASETS.items():
        frame, y, X = load_Xy(info)
        fold_list = make_folds(y)
        dataset_id = committed.loc[
            committed["dataset"].str.startswith(dataset + "-"), "dataset"
        ].unique()
        if len(dataset_id) != 1:
            raise RuntimeError(f"{dataset}: expected one committed dataset id, found {list(dataset_id)}")
        dataset_id = dataset_id[0]

        rows = reused_rows(committed, dataset_id)

        teacher_rows = [r for r in rows if r["method"] == "tabpfn"]
        teacher_mean, _ = mean_se([r["auc"] for r in teacher_rows])
        published = PUBLISHED_TEACHER_MEAN_AUC[dataset]
        if abs(teacher_mean - published) > TEACHER_MEAN_TOLERANCE:
            print(
                f"VERSION MISMATCH on {dataset}: re-scored teacher mean AUC {teacher_mean:.6f} does "
                f"not reproduce the committed v3_default value {published:.4f}. The reused rows are a "
                "different model era; refusing to write a record that mixes eras "
                "(docs/MODEL_VERSIONS.md).",
                file=sys.stderr,
            )
            return 3
        print(f"{dataset}: teacher re-score {teacher_mean:.6f} reproduces v3_default {published:.4f} ✓")

        for name, build in student_factories().items():
            rows.extend(fit_and_score(name, build, X, y, fold_list, "student"))
            print(f"  {dataset}: {name} fitted on {N_FOLDS} folds")
        for name, build in scale_sensitive_factories().items():
            rows.extend(fit_and_score(name, build, X, y, fold_list, "sensitivity"))
            print(f"  {dataset}: {name} fitted on {N_FOLDS} folds")
        rows.extend(fit_and_score("lightgbm_control", lightgbm_control, X, y, fold_list, "control"))
        print(f"  {dataset}: lightgbm_control fitted on {N_FOLDS} folds")

        for r in rows:
            r["dataset"] = dataset
            r["dataset_id"] = dataset_id
            r["source"] = (
                "reused:" + str(COMMITTED_RESULTS.relative_to(REPO))
                if r["role"] in {"teacher", "committed-proxy"}
                else "measured:scripts/benchmarks/measure_lapse_students.py"
            )
        per_fold.extend(rows)

        summary = summarise(dataset, rows)
        summaries.append(summary)

        # captures: every freshly fitted row (the teacher's probabilities were never committed)
        for r in rows:
            if r["role"] in {"teacher", "committed-proxy"}:
                continue
            key = f"{dataset}__{r['method']}__fold{r['fold']}"
            captures[f"{key}__y_true"] = np.asarray(r["y_true"])
            captures[f"{key}__y_pred"] = np.asarray(r["y_pred"])
            captures[f"{key}__test_idx"] = np.asarray(r["test_idx"])

        fingerprint = dataset_fingerprint(
            dataset,
            frame=frame,
            target=info["target"],
            drop=(),
            path=DATA_RAW / info["file"],
        )
        datasets_meta.append({**fingerprint, "committed_id": dataset_id})
        splits.append(
            {
                "dataset": dataset,
                "sha256": fold_sha(fold_list),
                "n_train_first_fold": int(len(fold_list[0][0])),
                "n_test_first_fold": int(len(fold_list[0][1])),
            }
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pred_dir = OUT_DIR / "predictions"
    pred_dir.mkdir(exist_ok=True)

    npz_path = pred_dir / f"lapse__seed{SEED}__students.npz"
    np.savez_compressed(npz_path, **captures)

    score_columns = ["dataset", "dataset_id", "fold", "method", "role", "auc", "brier", "source"]
    scores = pd.DataFrame([{k: r[k] for k in score_columns} for r in per_fold])
    scores.to_csv(OUT_DIR / "per_fold.csv", index=False)

    teacher_reuse = {
        "teacher_refit": False,
        "teacher_no_refit_reason": (
            "run_lapse_benchmark.py's only teacher path calls the hosted API; #377 forbids a "
            "hosted call and the five folds are already committed"
        ),
        "source": str(COMMITTED_RESULTS.relative_to(REPO)),
        "source_sha256": committed_sha,
        "rows": f"{TEACHER_METHOD} (per-fold roc_auc error; auc = 1 - metric_error)",
        "teacher_brier": "not measurable: the committed lapse record holds no teacher probabilities, "
        "and producing them needs a hosted call this ticket forbids",
        "version_evidence": (
            "v3_default attributed from docs/MODEL_VERSIONS.md's Aug-2026 timeline plus the "
            "re-scored means reproducing the published 0.6101 / 0.7553; the source CSV carries no "
            "version field, which is the gap #370 §4.5 named"
        ),
    }

    git_sha, git_dirty = git_revision()
    record = {
        "schema_version": CAPTURE_SCHEMA_VERSION,
        "kind": CAPTURE_KIND,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "issue": 377,
        "title": "Lapse student measurement — teacher folds reused, four pinned students fitted",
        "protocol": (
            f"StratifiedKFold(n_splits={N_FOLDS}, shuffle=True, random_state={SEED}); "
            "roc_auc (primary) + brier per fold; unscaled features encoded as cat.codes, "
            "fillna(0), float32 (the repository's home-harness convention)"
        ),
        "provenance": provenance_block(
            dataset=datasets_meta,
            split=split_section(
                n_folds=N_FOLDS,
                seed=SEED,
                # run-level: one keyed hash over both Datasets' fold hashes; the per-Dataset
                # values stay addressable under measurements.split_index_sha256
                sha256=combined_split_sha(splits),
                rule=split_rule("StratifiedKFold", n_splits=N_FOLDS, shuffle=True, random_state=SEED),
            ),
            model=model_section(
                version="v3_default",
                version_source="documented-timeline",
                weights_sha256=None,
                # no client ran in this record: the teacher's rows were reused, not called
                client_version=None,
            ),
            code=code_section(
                git_sha=git_sha,
                dirty=git_dirty,
                runtime=_runtime(),
                image=None,
            ),
        ),
        "teacher_reuse": teacher_reuse,
        "version_source_note": (
            "provenance.model.version_source = 'documented-timeline': v3_default is the label the "
            "committed rows are attributed by docs/MODEL_VERSIONS.md, not a label this run resolved "
            "from a client (none was imported). The era is corroborated by reproducing the "
            "published per-fold means, which is a documented claim, not a manifest."
        ),
        "measurements": {
            "per_fold_csv": "results/20261031-lapse-students/per_fold.csv",
            "predictions_npz": str(npz_path.relative_to(REPO)),
            "predictions_sha256": predictions_sha256(captures),
            "predictions_sha256_scheme": (
                "sha256 over arrays in sorted key order; per array: key, NUL, dtype.str, NUL, "
                "shape, NUL, C-contiguous data bytes"
            ),
            "se_definition": "sample std (ddof=1) / sqrt(n_folds)",
            "split_index_sha256": {s["dataset"]: s["sha256"] for s in splits},
            "sensitivity_note": (
                "logistic_regression_scaled is NOT a pinned student: it is the pinned model behind "
                "a StandardScaler, because the pinned config carries no scaler and lbfgs reports "
                "non-convergence on raw category codes. The pinned arm is therefore a lower bound "
                "on linear performance; the paired pair sizes that gap."
            ),
            "summaries": summaries,
        },
        "pipeline_asymmetry": pipeline_asymmetry(per_fold),
    }

    (OUT_DIR / "record.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    # The verdict is computed, never written into the record (GLOSSARY.md: Verdict).
    print(f"\nrecord verdict: {verdict(record, kind=CAPTURE_KIND)}")
    print(f"record: {OUT_DIR / 'record.json'}")
    print(f"scores: {OUT_DIR / 'per_fold.csv'}")

    print("\n| Dataset | Model | Role | AUC (mean ± SE) | Brier | Gap vs teacher | D3 clears |")
    print("| --- | --- | --- | ---: | ---: | ---: | --- |")
    for s in summaries:
        for name, m in sorted(s["methods"].items(), key=lambda kv: -kv[1]["mean_auc"]):
            gap = (
                f"{s['teacher_mean_auc'] - m['mean_auc']:+.4f}"
                if name != "tabpfn"
                else "—"
            )
            d3 = ""
            for key in ("best_pinned_student_gap", "best_gbdt_gap"):
                if s[key] and name == s[key]["best_student"]:
                    d3 = "yes" if s[key]["d3_clears"] else "no"
            brier = f"{m['mean_brier']:.4f}" if m["mean_brier"] is not None else "—"
            print(
                f"| {s['dataset']} | {name} | {m['role']} | "
                f"{m['mean_auc']:.4f} ± {m['se_auc']:.4f} | {brier} | {gap} | {d3} |"
            )
    for s in summaries:
        for key, label in (
            ("best_pinned_student_gap", "best pinned student"),
            ("best_gbdt_gap", "best GBDT (incl. LightGBM)"),
        ):
            g = s[key]
            if g:
                print(
                    f"{s['dataset']} / {label}: {g['best_student']} {g['best_mean_auc']:.4f} "
                    f"± {g['best_se_auc']:.4f} vs teacher {s['teacher_mean_auc']:.4f} "
                    f"± {s['teacher_se_auc']:.4f} -> gap {g['gap_auc']:+.4f}, "
                    f"D3 {'clears' if g['d3_clears'] else 'does not clear'}"
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
