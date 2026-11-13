"""Stage A pilot runner for insurance domain fine-tuning comparisons.

This executes a controlled first-pass experiment from
`docs/archive/pilot2-phase2/INSURANCE_DOMAIN_FINETUNING_METHOD_PROTOCOL.md`:
- held-out target insurance dataset
- domain fine-tune pool from other insurance datasets
- model arms: raw TabPFN, domain-fine-tuned TabPFN, GLM, RandomForest,
  and CatBoost when available

Outputs are appended to:
- outputs/current/tables/domain_finetune_study_runs.csv

Legacy — fine-tuning-era script, kept for provenance; registered reports cite its outputs (outputs/current/tables/)."""

from __future__ import annotations

import argparse
import csv
import resource
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, log_loss, roc_auc_score
from sklearn.model_selection import train_test_split


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    path: Path
    target_col: str
    line_of_business: str
    exposure_structure: str
    claim_process: str


DATASETS = {
    "eudirectlapse": DatasetSpec(
        name="eudirectlapse",
        path=Path("data/raw/eudirectlapse.csv"),
        target_col="lapse",
        line_of_business="retail_policy_lapse",
        exposure_structure="policy_level",
        claim_process="renewal_or_cancellation",
    ),
    "coil2000": DatasetSpec(
        name="coil2000",
        path=Path("data/raw/coil2000.csv"),
        target_col="CARAVAN",
        line_of_business="cross_sell_marketing",
        exposure_structure="household_level",
        claim_process="product_purchase",
    ),
    "ausprivauto0405": DatasetSpec(
        name="ausprivauto0405",
        path=Path("data/raw/ausprivauto0405.csv"),
        target_col="ClaimOcc",
        line_of_business="motor",
        exposure_structure="policy_year",
        claim_process="claim_occurrence",
    ),
    "freMTPL2freq_binary": DatasetSpec(
        name="freMTPL2freq_binary",
        path=Path("data/raw/freMTPL2freq_binary.csv"),
        target_col="ClaimIndicator",
        line_of_business="motor",
        exposure_structure="exposure_fraction",
        claim_process="claim_occurrence",
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Stage A insurance domain fine-tune pilot")
    parser.add_argument(
        "--target-dataset",
        choices=list(DATASETS.keys()),
        default="eudirectlapse",
        help="Held-out target dataset for evaluation",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--target-rows", type=int, default=4000)
    parser.add_argument("--pool-rows-per-dataset", type=int, default=2000)
    parser.add_argument(
        "--pool-policy",
        choices=["all", "homogeneous", "heterogeneous", "similarity_topk", "mixed_baseline"],
        default="all",
        help=(
            "How to choose domain fine-tune pool datasets from non-target datasets: "
            "all=use all candidates, homogeneous=closest label prevalence, "
            "heterogeneous=most distant label prevalence, "
            "similarity_topk=closest by composite similarity, "
            "mixed_baseline=current baseline pool"
        ),
    )
    parser.add_argument(
        "--pool-k",
        type=int,
        default=2,
        help="Number of pool datasets to keep when pool-policy uses top-k selection",
    )
    parser.add_argument("--sim-weight-feature", type=float, default=0.45)
    parser.add_argument("--sim-weight-target", type=float, default=0.35)
    parser.add_argument("--sim-weight-context", type=float, default=0.20)
    parser.add_argument("--test-size", type=float, default=0.3)
    parser.add_argument("--tabpfn-device", type=str, default="cpu")
    parser.add_argument("--tabpfn-context-samples", type=int, default=64)
    parser.add_argument("--tabpfn-n-estimators", type=int, default=2)
    parser.add_argument("--tabpfn-max-finetune-steps", type=int, default=1)
    parser.add_argument(
        "--log-path",
        type=Path,
        default=Path("outputs/current/tables/domain_finetune_study_runs.csv"),
    )
    parser.add_argument(
        "--logbook-path",
        type=Path,
        default=Path("outputs/current/logs/domain_finetune_logbook.md"),
        help="Markdown logbook file to append run interpretation and notes",
    )
    parser.add_argument(
        "--observations",
        type=str,
        default="",
        help="Free-text observations from this run",
    )
    parser.add_argument(
        "--comments",
        type=str,
        default="",
        help="Free-text analyst comments for this run",
    )
    parser.add_argument("--prefer-upstream-src", action="store_true", default=True)
    parser.add_argument("--no-prefer-upstream-src", dest="prefer_upstream_src", action="store_false")
    return parser.parse_args()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def configure_import_path(prefer_upstream_src: bool) -> Path | None:
    upstream_src = repo_root().parent / "TabPFN-upstream" / "src"
    if prefer_upstream_src and upstream_src.exists():
        sys.path.insert(0, str(upstream_src))
        return upstream_src
    return None


def resolve_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    return repo_root() / path


def read_and_sample(spec: DatasetSpec, rows: int, seed: int) -> pd.DataFrame:
    path = resolve_path(spec.path)
    frame = pd.read_csv(path)
    if spec.target_col not in frame.columns:
        raise ValueError(f"Target column '{spec.target_col}' not in {path}")
    frame = frame.dropna(subset=[spec.target_col]).copy()

    class_counts = frame[spec.target_col].value_counts(dropna=False)
    if class_counts.min() < 2 or len(class_counts) < 2:
        sampled = frame.sample(n=min(rows, len(frame)), random_state=seed)
    else:
        sampled_parts = []
        for _, group in frame.groupby(spec.target_col, sort=False):
            n_group = max(1, round(rows * len(group) / len(frame)))
            sampled_parts.append(group.sample(n=min(n_group, len(group)), random_state=seed))
        sampled = pd.concat(sampled_parts, axis=0)
        sampled = sampled.sample(n=min(rows, len(sampled)), random_state=seed)
    return sampled.reset_index(drop=True)


def safe_split(X: np.ndarray, y: np.ndarray, test_size: float, seed: int):
    _, counts = np.unique(y, return_counts=True)
    stratify_target = y if len(counts) > 1 and counts.min() >= 2 else None
    return train_test_split(X, y, test_size=test_size, random_state=seed, stratify=stratify_target)


def ece_score(y_true: np.ndarray, y_prob: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    ece = 0.0
    for i in range(bins):
        lo = edges[i]
        hi = edges[i + 1]
        mask = (y_prob >= lo) & (y_prob < hi if i < bins - 1 else y_prob <= hi)
        if not np.any(mask):
            continue
        conf = float(np.mean(y_prob[mask]))
        acc = float(np.mean(y_true[mask]))
        ece += abs(acc - conf) * (np.sum(mask) / len(y_true))
    return float(ece)


def ensure_binary_int(y: pd.Series | np.ndarray) -> np.ndarray:
    vals = np.asarray(y)
    if vals.dtype.kind in {"i", "u", "b"}:
        uniq = np.unique(vals)
        if len(uniq) == 2:
            return vals.astype(int)
    unique_vals = pd.Series(vals).dropna().unique().tolist()
    if len(unique_vals) != 2:
        raise ValueError(f"Expected binary target, found classes={unique_vals}")
    mapper = {unique_vals[0]: 0, unique_vals[1]: 1}
    return np.array([mapper[v] for v in vals], dtype=int)


def positive_rate(y: np.ndarray) -> float:
    return float(np.mean(y == 1))


def binary_entropy(y: np.ndarray) -> float:
    p = float(np.clip(positive_rate(y), 1e-8, 1.0 - 1e-8))
    return float(-(p * np.log(p) + (1 - p) * np.log(1 - p)))


def feature_profile(frame: pd.DataFrame, target_col: str) -> dict[str, float]:
    X = frame.drop(columns=[target_col])
    n_rows = max(1, len(X))
    n_cols = max(1, X.shape[1])

    numeric = X.select_dtypes(include=[np.number])
    numeric_ratio = float(numeric.shape[1] / n_cols)
    missing_rate = float(X.isna().mean().mean())
    unique_ratio = float(X.nunique(dropna=False).mean() / n_rows)

    # Simple value scale profile for numeric columns, robust to outliers.
    if numeric.shape[1] > 0:
        q25 = numeric.quantile(0.25)
        q75 = numeric.quantile(0.75)
        iqr_mean = float((q75 - q25).replace([np.inf, -np.inf], np.nan).fillna(0.0).mean())
    else:
        iqr_mean = 0.0

    return {
        "log_n_rows": float(np.log1p(n_rows)),
        "log_n_cols": float(np.log1p(n_cols)),
        "numeric_ratio": numeric_ratio,
        "missing_rate": missing_rate,
        "unique_ratio": unique_ratio,
        "log_iqr_mean": float(np.log1p(max(0.0, iqr_mean))),
    }


def feature_space_distance(a: dict[str, float], b: dict[str, float]) -> float:
    keys = [
        "log_n_rows",
        "log_n_cols",
        "numeric_ratio",
        "missing_rate",
        "unique_ratio",
        "log_iqr_mean",
    ]
    return float(np.mean([abs(a[k] - b[k]) for k in keys]))


def target_behavior_distance(y_target: np.ndarray, y_pool: np.ndarray) -> float:
    p_dist = abs(positive_rate(y_target) - positive_rate(y_pool))
    h_dist = abs(binary_entropy(y_target) - binary_entropy(y_pool))
    return float(0.6 * p_dist + 0.4 * h_dist)


def context_distance(target_spec: DatasetSpec, pool_spec: DatasetSpec) -> float:
    mismatch = 0
    mismatch += int(target_spec.line_of_business != pool_spec.line_of_business)
    mismatch += int(target_spec.exposure_structure != pool_spec.exposure_structure)
    mismatch += int(target_spec.claim_process != pool_spec.claim_process)
    return float(mismatch / 3.0)


def normalize_weights(w_feature: float, w_target: float, w_context: float) -> tuple[float, float, float]:
    total = float(w_feature + w_target + w_context)
    if total <= 0:
        return 0.45, 0.35, 0.20
    return w_feature / total, w_target / total, w_context / total


def choose_pool_specs(
    target_spec: DatasetSpec,
    target_frame: pd.DataFrame,
    target_y: np.ndarray,
    pool_specs: list[DatasetSpec],
    pool_frames: list[pd.DataFrame],
    policy: str,
    pool_k: int,
    sim_weight_feature: float,
    sim_weight_target: float,
    sim_weight_context: float,
) -> tuple[list[DatasetSpec], list[pd.DataFrame], float | None, float | None]:
    if policy in {"all", "mixed_baseline"}:
        return pool_specs, pool_frames, None, None

    target_prev = positive_rate(target_y)
    target_profile = feature_profile(target_frame, target_spec.target_col)

    scored: list[tuple[float, float, DatasetSpec, pd.DataFrame]] = []
    w_f, w_t, w_c = normalize_weights(sim_weight_feature, sim_weight_target, sim_weight_context)

    for spec, frame in zip(pool_specs, pool_frames):
        y_pool = ensure_binary_int(frame[spec.target_col])
        prev_dist = abs(positive_rate(y_pool) - target_prev)
        if policy == "similarity_topk":
            f_dist = feature_space_distance(target_profile, feature_profile(frame, spec.target_col))
            t_dist = target_behavior_distance(target_y, y_pool)
            c_dist = context_distance(target_spec, spec)
            sim_dist = w_f * f_dist + w_t * t_dist + w_c * c_dist
        else:
            sim_dist = np.nan
        scored.append((prev_dist, sim_dist, spec, frame))

    if policy == "similarity_topk":
        scored = sorted(scored, key=lambda x: x[1])
    else:
        scored = sorted(scored, key=lambda x: x[0], reverse=(policy == "heterogeneous"))

    k = max(1, min(pool_k, len(scored)))
    chosen = scored[:k]
    chosen_specs = [item[2] for item in chosen]
    chosen_frames = [item[3] for item in chosen]
    mean_prev_dist = float(np.mean([item[0] for item in chosen])) if chosen else None
    mean_sim_dist = None
    if policy == "similarity_topk" and chosen:
        mean_sim_dist = float(np.mean([item[1] for item in chosen]))
    return chosen_specs, chosen_frames, mean_prev_dist, mean_sim_dist


def evaluate_probs(y_true: np.ndarray, y_prob: np.ndarray) -> dict[str, float]:
    y_prob = np.clip(y_prob, 1e-8, 1.0 - 1e-8)
    return {
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
        "pr_auc": float(average_precision_score(y_true, y_prob)),
        "brier": float(np.mean((y_prob - y_true) ** 2)),
        "log_loss": float(log_loss(y_true, y_prob)),
        "ece": ece_score(y_true, y_prob),
    }


def append_rows(log_path: Path, rows: list[dict[str, Any]]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    if not log_path.exists():
        with log_path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        return

    with log_path.open("r", newline="") as handle:
        reader = csv.DictReader(handle)
        existing = list(reader)
        fieldnames = reader.fieldnames or []

    merged = list(fieldnames)
    for row in rows:
        for key in row.keys():
            if key not in merged:
                merged.append(key)

    if merged != fieldnames:
        with log_path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=merged)
            writer.writeheader()
            for old_row in existing:
                writer.writerow({k: old_row.get(k, "") for k in merged})

    with log_path.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=merged)
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in merged})


def append_logbook_entry(
    logbook_path: Path,
    args: argparse.Namespace,
    target_dataset: str,
    run_rows: list[dict[str, Any]],
) -> None:
    logbook_path.parent.mkdir(parents=True, exist_ok=True)

    metric_rows = [row for row in run_rows if row.get("roc_auc", "") != ""]
    raw_row = next((row for row in metric_rows if row.get("model_variant") == "raw"), None)
    tuned_row = next((row for row in metric_rows if row.get("model_variant") == "domain_finetuned"), None)

    interpretation_lines: list[str] = []
    if raw_row is not None and tuned_row is not None:
        d_roc = float(tuned_row["roc_auc"]) - float(raw_row["roc_auc"])
        d_pr = float(tuned_row["pr_auc"]) - float(raw_row["pr_auc"])
        d_brier = float(tuned_row["brier"]) - float(raw_row["brier"])
        d_logloss = float(tuned_row["log_loss"]) - float(raw_row["log_loss"])
        interpretation_lines.append(
            f"- Domain-finetuned minus raw TabPFN: ROC AUC {d_roc:+.4f}, PR AUC {d_pr:+.4f}, Brier {d_brier:+.4f}, LogLoss {d_logloss:+.4f}."
        )
        if d_brier < 0 and d_logloss < 0:
            interpretation_lines.append("- Primary calibration endpoints improved for domain fine-tuned TabPFN on this target.")
        elif d_brier > 0 and d_logloss > 0:
            interpretation_lines.append("- Primary calibration endpoints degraded for domain fine-tuned TabPFN on this target.")
        else:
            interpretation_lines.append("- Mixed calibration endpoint movement; keep this target in follow-up runs.")
    else:
        interpretation_lines.append("- Could not compute raw-vs-domain-finetuned delta for this run.")

    lines = [
        f"## Run {datetime.now(timezone.utc).isoformat()}",
        "",
        "### Configuration",
        f"- Stage: A",
        f"- Target dataset: {target_dataset}",
        f"- Seed: {args.seed}",
        f"- Target rows: {args.target_rows}",
        f"- Pool rows per dataset: {args.pool_rows_per_dataset}",
        f"- Pool policy: {args.pool_policy}",
        f"- Pool k: {args.pool_k}",
        f"- Device/context/steps: {args.tabpfn_device}/{args.tabpfn_context_samples}/{args.tabpfn_max_finetune_steps}",
        "",
        "### Results",
        "| Model Variant | ROC AUC | PR AUC | Brier | LogLoss | ECE | Notes |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]

    for row in run_rows:
        roc = row.get("roc_auc", "")
        pr = row.get("pr_auc", "")
        brier = row.get("brier", "")
        ll = row.get("log_loss", "")
        ece = row.get("ece", "")
        notes = row.get("notes", "")
        lines.append(
            "| "
            f"{row.get('model_variant','')} | "
            f"{f'{float(roc):.4f}' if roc != '' else ''} | "
            f"{f'{float(pr):.4f}' if pr != '' else ''} | "
            f"{f'{float(brier):.4f}' if brier != '' else ''} | "
            f"{f'{float(ll):.4f}' if ll != '' else ''} | "
            f"{f'{float(ece):.4f}' if ece != '' else ''} | "
            f"{notes} |"
        )

    lines.append("")
    lines.append("### Interpretation")
    lines.extend(interpretation_lines)
    lines.append("")
    lines.append("### Observations")
    lines.append(f"- {args.observations if args.observations else 'No observations supplied at runtime.'}")
    lines.append("")
    lines.append("### Comments")
    lines.append(f"- {args.comments if args.comments else 'No comments supplied at runtime.'}")
    lines.append("\n")

    with logbook_path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def run_tabpfn_raw(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    tabpfn_device: str,
    n_estimators: int,
    seed: int,
) -> np.ndarray:
    from tabpfn import TabPFNClassifier

    model = TabPFNClassifier(
        ignore_pretraining_limits=True,
        device=tabpfn_device,
        n_estimators=n_estimators,
        random_state=seed,
    )
    model.fit(X_train, y_train)
    probs = model.predict_proba(X_test)[:, 1]
    return probs


def run_tabpfn_finetuned(
    X_pool: np.ndarray,
    y_pool: np.ndarray,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    tabpfn_device: str,
    context_samples: int,
    n_estimators: int,
    max_finetune_steps: int,
    seed: int,
) -> tuple[np.ndarray, int]:
    import torch
    from torch.optim import Adam
    from torch.utils.data import DataLoader

    from tabpfn import TabPFNClassifier
    from tabpfn.finetune_utils import clone_model_for_evaluation  # type: ignore[import-not-found]
    from tabpfn.utils import meta_dataset_collator

    cfg = {
        "ignore_pretraining_limits": True,
        "device": tabpfn_device,
        "n_estimators": n_estimators,
        "random_state": seed,
        "inference_precision": torch.float32,
    }
    model = TabPFNClassifier(**cfg, fit_mode="batched", differentiable_input=False)
    model._initialize_model_variables()

    optimizer = Adam(model.model_.parameters(), lr=1e-5)
    loss_fn = torch.nn.CrossEntropyLoss()

    splitter = lambda features, target: safe_split(features, target, test_size=0.3, seed=seed)
    datasets = model.get_preprocessed_datasets(
        X_pool,
        y_pool,
        splitter,
        min(context_samples, len(X_pool)),
    )
    loader = DataLoader(datasets, batch_size=1, collate_fn=meta_dataset_collator)

    steps = 0
    for xb, xvb, yb, yvb, cix, conf in loader:
        if len(np.unique(yb)) != len(np.unique(yvb)):
            continue
        optimizer.zero_grad()
        model.fit_from_preprocessed(xb, yb, cix, conf)
        logits = model.forward(xvb, return_logits=True)
        loss = loss_fn(logits, yvb.to(tabpfn_device))
        loss.backward()
        optimizer.step()
        steps += 1
        if steps >= max_finetune_steps:
            break

    eval_cfg = {**cfg, "inference_config": {"SUBSAMPLE_SAMPLES": context_samples}}
    eval_model = clone_model_for_evaluation(model, eval_cfg, TabPFNClassifier)
    eval_model.fit(X_train, y_train)
    probs = eval_model.predict_proba(X_test)[:, 1]
    return probs, steps


def main() -> None:
    args = parse_args()
    start = time.perf_counter()
    upstream_src = configure_import_path(args.prefer_upstream_src)

    target_spec = DATASETS[args.target_dataset]
    pool_specs_all = [spec for key, spec in DATASETS.items() if key != args.target_dataset]

    target_df = read_and_sample(target_spec, args.target_rows, args.seed)
    pool_frames_all = [read_and_sample(spec, args.pool_rows_per_dataset, args.seed) for spec in pool_specs_all]

    y_target = ensure_binary_int(target_df[target_spec.target_col])
    X_target_df = target_df.drop(columns=[target_spec.target_col])

    pool_specs, pool_frames, selected_pool_mean_prev_distance, selected_pool_mean_similarity_distance = choose_pool_specs(
        target_spec=target_spec,
        target_frame=target_df,
        target_y=y_target,
        pool_specs=pool_specs_all,
        pool_frames=pool_frames_all,
        policy=args.pool_policy,
        pool_k=args.pool_k,
        sim_weight_feature=args.sim_weight_feature,
        sim_weight_target=args.sim_weight_target,
        sim_weight_context=args.sim_weight_context,
    )

    X_pool_frames = []
    y_pool_parts = []
    for spec, frame in zip(pool_specs, pool_frames):
        y_pool_parts.append(ensure_binary_int(frame[spec.target_col]))
        X_pool_frames.append(frame.drop(columns=[spec.target_col]))

    selected_pool_names = ";".join(spec.name for spec in pool_specs)

    # Fit encoder on pooled domain + target train universe to keep feature alignment.
    joint_df = pd.concat([X_target_df] + X_pool_frames, axis=0, ignore_index=True)
    joint_encoded = pd.get_dummies(joint_df, drop_first=False)
    joint_encoded = joint_encoded.fillna(0)

    X_target_enc = joint_encoded.iloc[: len(X_target_df), :].to_numpy(dtype=np.float32)
    X_pool_enc = joint_encoded.iloc[len(X_target_df) :, :].to_numpy(dtype=np.float32)
    y_pool = np.concatenate(y_pool_parts, axis=0)

    X_train, X_test, y_train, y_test = safe_split(X_target_enc, y_target, args.test_size, args.seed)

    run_rows: list[dict[str, Any]] = []

    # GLM baseline
    t0 = time.perf_counter()
    glm = LogisticRegression(max_iter=1000, solver="liblinear", random_state=args.seed)
    glm.fit(X_train, y_train)
    glm_prob = glm.predict_proba(X_test)[:, 1]
    glm_metrics = evaluate_probs(y_test, glm_prob)
    run_rows.append(
        {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "stage": "A",
            "target_dataset": target_spec.name,
            "seed": args.seed,
            "model_family": "glm",
            "model_variant": "logistic_regression",
            "target_rows": len(X_target_df),
            "pool_rows": len(X_pool_enc),
            "train_rows": len(X_train),
            "test_rows": len(X_test),
            "tabpfn_device": args.tabpfn_device,
            "tabpfn_context_samples": args.tabpfn_context_samples,
            "tabpfn_max_finetune_steps": args.tabpfn_max_finetune_steps,
            "pool_policy": args.pool_policy,
            "pool_k": args.pool_k,
            "selected_pool_datasets": selected_pool_names,
            "selected_pool_mean_prev_distance": (
                f"{selected_pool_mean_prev_distance:.6f}" if selected_pool_mean_prev_distance is not None else ""
            ),
            "fine_tune_steps_executed": "",
            **glm_metrics,
            "fit_predict_wall_time_sec": f"{time.perf_counter() - t0:.6f}",
            "upstream_src": str(upstream_src) if upstream_src is not None else "",
            "notes": "",
        }
    )

    # RandomForest baseline
    t0 = time.perf_counter()
    rf = RandomForestClassifier(n_estimators=300, random_state=args.seed, n_jobs=-1)
    rf.fit(X_train, y_train)
    rf_prob = rf.predict_proba(X_test)[:, 1]
    rf_metrics = evaluate_probs(y_test, rf_prob)
    run_rows.append(
        {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "stage": "A",
            "target_dataset": target_spec.name,
            "seed": args.seed,
            "model_family": "tree",
            "model_variant": "random_forest",
            "target_rows": len(X_target_df),
            "pool_rows": len(X_pool_enc),
            "train_rows": len(X_train),
            "test_rows": len(X_test),
            "tabpfn_device": args.tabpfn_device,
            "tabpfn_context_samples": args.tabpfn_context_samples,
            "tabpfn_max_finetune_steps": args.tabpfn_max_finetune_steps,
            "pool_policy": args.pool_policy,
            "pool_k": args.pool_k,
            "selected_pool_datasets": selected_pool_names,
            "selected_pool_mean_prev_distance": (
                f"{selected_pool_mean_prev_distance:.6f}" if selected_pool_mean_prev_distance is not None else ""
            ),
            "fine_tune_steps_executed": "",
            **rf_metrics,
            "fit_predict_wall_time_sec": f"{time.perf_counter() - t0:.6f}",
            "upstream_src": str(upstream_src) if upstream_src is not None else "",
            "notes": "",
        }
    )

    # CatBoost baseline (optional)
    try:
        from catboost import CatBoostClassifier

        t0 = time.perf_counter()
        cb = CatBoostClassifier(
            random_seed=args.seed,
            loss_function="Logloss",
            verbose=False,
            iterations=300,
            depth=6,
        )
        cb.fit(X_train, y_train)
        cb_prob = cb.predict_proba(X_test)[:, 1]
        cb_metrics = evaluate_probs(y_test, cb_prob)
        run_rows.append(
            {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "stage": "A",
                "target_dataset": target_spec.name,
                "seed": args.seed,
                "model_family": "tree",
                "model_variant": "catboost",
                "target_rows": len(X_target_df),
                "pool_rows": len(X_pool_enc),
                "train_rows": len(X_train),
                "test_rows": len(X_test),
                "tabpfn_device": args.tabpfn_device,
                "tabpfn_context_samples": args.tabpfn_context_samples,
                "tabpfn_max_finetune_steps": args.tabpfn_max_finetune_steps,
                "pool_policy": args.pool_policy,
                "pool_k": args.pool_k,
                "selected_pool_datasets": selected_pool_names,
                "selected_pool_mean_prev_distance": (
                    f"{selected_pool_mean_prev_distance:.6f}" if selected_pool_mean_prev_distance is not None else ""
                ),
                "fine_tune_steps_executed": "",
                **cb_metrics,
                "fit_predict_wall_time_sec": f"{time.perf_counter() - t0:.6f}",
                "upstream_src": str(upstream_src) if upstream_src is not None else "",
                "notes": "",
            }
        )
    except Exception as exc:
        run_rows.append(
            {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "stage": "A",
                "target_dataset": target_spec.name,
                "seed": args.seed,
                "model_family": "tree",
                "model_variant": "catboost",
                "target_rows": len(X_target_df),
                "pool_rows": len(X_pool_enc),
                "train_rows": len(X_train),
                "test_rows": len(X_test),
                "tabpfn_device": args.tabpfn_device,
                "tabpfn_context_samples": args.tabpfn_context_samples,
                "tabpfn_max_finetune_steps": args.tabpfn_max_finetune_steps,
                "pool_policy": args.pool_policy,
                "pool_k": args.pool_k,
                "selected_pool_datasets": selected_pool_names,
                "selected_pool_mean_prev_distance": (
                    f"{selected_pool_mean_prev_distance:.6f}" if selected_pool_mean_prev_distance is not None else ""
                ),
                "fine_tune_steps_executed": "",
                "roc_auc": "",
                "pr_auc": "",
                "brier": "",
                "log_loss": "",
                "ece": "",
                "fit_predict_wall_time_sec": "",
                "upstream_src": str(upstream_src) if upstream_src is not None else "",
                "notes": f"catboost_not_available: {exc}",
            }
        )

    # Raw TabPFN
    t0 = time.perf_counter()
    raw_prob = run_tabpfn_raw(
        X_train,
        y_train,
        X_test,
        tabpfn_device=args.tabpfn_device,
        n_estimators=args.tabpfn_n_estimators,
        seed=args.seed,
    )
    raw_metrics = evaluate_probs(y_test, raw_prob)
    run_rows.append(
        {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "stage": "A",
            "target_dataset": target_spec.name,
            "seed": args.seed,
            "model_family": "tabpfn",
            "model_variant": "raw",
            "target_rows": len(X_target_df),
            "pool_rows": len(X_pool_enc),
            "train_rows": len(X_train),
            "test_rows": len(X_test),
            "tabpfn_device": args.tabpfn_device,
            "tabpfn_context_samples": args.tabpfn_context_samples,
            "tabpfn_max_finetune_steps": args.tabpfn_max_finetune_steps,
            "pool_policy": args.pool_policy,
            "pool_k": args.pool_k,
            "selected_pool_datasets": selected_pool_names,
            "selected_pool_mean_prev_distance": (
                f"{selected_pool_mean_prev_distance:.6f}" if selected_pool_mean_prev_distance is not None else ""
            ),
            "fine_tune_steps_executed": "",
            **raw_metrics,
            "fit_predict_wall_time_sec": f"{time.perf_counter() - t0:.6f}",
            "upstream_src": str(upstream_src) if upstream_src is not None else "",
            "notes": "",
        }
    )

    # Domain-fine-tuned TabPFN
    t0 = time.perf_counter()
    tuned_prob, steps = run_tabpfn_finetuned(
        X_pool_enc,
        y_pool,
        X_train,
        y_train,
        X_test,
        tabpfn_device=args.tabpfn_device,
        context_samples=args.tabpfn_context_samples,
        n_estimators=args.tabpfn_n_estimators,
        max_finetune_steps=args.tabpfn_max_finetune_steps,
        seed=args.seed,
    )
    tuned_metrics = evaluate_probs(y_test, tuned_prob)
    run_rows.append(
        {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "stage": "A",
            "target_dataset": target_spec.name,
            "seed": args.seed,
            "model_family": "tabpfn",
            "model_variant": "domain_finetuned",
            "target_rows": len(X_target_df),
            "pool_rows": len(X_pool_enc),
            "train_rows": len(X_train),
            "test_rows": len(X_test),
            "tabpfn_device": args.tabpfn_device,
            "tabpfn_context_samples": args.tabpfn_context_samples,
            "tabpfn_max_finetune_steps": args.tabpfn_max_finetune_steps,
            "pool_policy": args.pool_policy,
            "pool_k": args.pool_k,
            "selected_pool_datasets": selected_pool_names,
            "selected_pool_mean_prev_distance": (
                f"{selected_pool_mean_prev_distance:.6f}" if selected_pool_mean_prev_distance is not None else ""
            ),
            "fine_tune_steps_executed": steps,
            **tuned_metrics,
            "fit_predict_wall_time_sec": f"{time.perf_counter() - t0:.6f}",
            "upstream_src": str(upstream_src) if upstream_src is not None else "",
            "notes": "",
        }
    )

    max_rss_bytes = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    for row in run_rows:
        row["pool_policy"] = args.pool_policy
        row["pool_k"] = args.pool_k
        row["selected_pool_datasets"] = selected_pool_names
        row["selected_pool_mean_prev_distance"] = (
            f"{selected_pool_mean_prev_distance:.6f}" if selected_pool_mean_prev_distance is not None else ""
        )
        row["selected_pool_mean_similarity_distance"] = (
            f"{selected_pool_mean_similarity_distance:.6f}" if selected_pool_mean_similarity_distance is not None else ""
        )
        row["max_rss_bytes"] = max_rss_bytes
        row["total_run_wall_time_sec"] = f"{time.perf_counter() - start:.6f}"

    log_path = resolve_path(args.log_path)
    append_rows(log_path, run_rows)
    append_logbook_entry(
        logbook_path=resolve_path(args.logbook_path),
        args=args,
        target_dataset=target_spec.name,
        run_rows=run_rows,
    )

    print("=== Domain Fine-Tuning Stage A Pilot ===")
    print(f"target_dataset={target_spec.name}")
    print(f"target_rows={len(X_target_df)} pool_rows={len(X_pool_enc)}")
    print(f"pool_policy={args.pool_policy} pool_k={args.pool_k} selected_pool_datasets={selected_pool_names}")
    if selected_pool_mean_similarity_distance is not None:
        print(f"selected_pool_mean_similarity_distance={selected_pool_mean_similarity_distance:.6f}")
    print(f"train_rows={len(X_train)} test_rows={len(X_test)}")
    print(f"tabpfn_device={args.tabpfn_device} context={args.tabpfn_context_samples} finetune_steps={args.tabpfn_max_finetune_steps}")
    print(f"log_path={log_path}")
    print(f"logbook_path={resolve_path(args.logbook_path)}")
    print("\nModel results (ROC AUC | PR AUC | Brier | LogLoss | ECE):")
    for row in run_rows:
        if row.get("roc_auc", "") == "":
            print(f"- {row['model_variant']}: skipped ({row['notes']})")
            continue
        print(
            f"- {row['model_variant']}: "
            f"{float(row['roc_auc']):.4f} | {float(row['pr_auc']):.4f} | "
            f"{float(row['brier']):.4f} | {float(row['log_loss']):.4f} | {float(row['ece']):.4f}"
        )


if __name__ == "__main__":
    main()
