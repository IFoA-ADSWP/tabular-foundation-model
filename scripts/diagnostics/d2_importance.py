#!/usr/bin/env python3
"""D2 -- what each model family uses, and where they disagree, as one record per dataset.

Usage:
    python scripts/diagnostics/d2_importance.py --all-anchors
    python scripts/diagnostics/d2_importance.py --dataset coil2000 --dataset uslapseagent
    python scripts/diagnostics/d2_importance.py --csv data/raw/coil2000.csv --target CARAVAN

The design (§D2) assumed the benchmark's fitted models could be re-opened. They are not committed --
only prediction arrays are -- so this diagnostic refits TabPFN, a GLM and LGBM locally, on a fixed
2,000-row subsample, and records that cap beside every number it produces. Importance from a
2,000-row subsample is an approximation; the record says so in the field a reader would look at,
rather than in a docstring they would not.

**Permutation importance on held-out rows, never refits.** A column of the test rows is shuffled and
the model is re-scored; the drop in ROC AUC is that feature's importance for that repeat. The fitted
context stays intact, which is the only affordable form for TabPFN (a refit per feature would be
`features x repeats` context preparations) and the honest one for GLM/LGBM too: the question is how
much the fitted model's prediction depends on the column.

**The three readings the design names are computed, not left to the reader.** Rankings alone would
leave "do they use the same features and rank them differently" as homework. Each record carries:

* `same_features_ranked_differently` -- Spearman correlation over the whole ranking, plus the largest
  rank moves within the shared top-k;
* `different_features` -- the top-k set differences and their Jaccard overlap;
* `interaction_only` -- LGBM top-k features whose univariate AUC is indistinguishable from a coin
  flip, i.e. only useful through a combination. That is a **screen** with its threshold recorded,
  not a proof of interaction.

**The wrongness check.** The whole pipeline is repeated on a label-permuted copy of one dataset. No
feature should dominate there. If one is as important as the real run's top feature, the measurement
is picking up leakage or an artefact, and the record says the control failed and the script exits
non-zero. Unlike D3, the failing record *is* written: those numbers are the only evidence of what
went wrong, and they cost most of an hour of CPU to produce.

**Two constraints recorded rather than smoothed over.**

* The TabPFN arm is the local open checkpoint -- `tabpfn` 6.4.1 resolves `auto` to a v2.5
  classifier, and there is no local v3. The record names what the library was asked for (`auto`, per
  #285: a label is not a filename), the version it resolved to, and the checkpoint file. Frontier
  numbers are v3-era; nothing here claims comparability with them.
* The model families are the benchmark's canonical method ids (`logisticglm`, `lgbm`), not a search
  for whichever scored best. Choosing them from `frontier_results_*.csv` would be model selection on
  test rows, which the decision log's leakage rule forbids.

Preprocessing is the R1 default -- per-column category codes, missing to 0 -- because whether that
encoding is the reason a model struggles is D4's question, not this one's.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "src"))

from anchor_datasets import load_anchor_datasets  # noqa: E402
from provenance import (  # noqa: E402  (importable after the src path insert above)
    DIAGNOSTICS_ROOT,
    DiagnosticRecord,
    matched_context_evidence,
    sha256_file,
    write_diagnostic_record,
)

DIAGNOSTIC = "d2_importance"
# The ticket's number, and the record's. The whole working set is capped -- not 2,000 training rows
# plus an unbounded test set -- so "the subsample is 2,000 rows" is literally true in the evidence.
SUBSAMPLE_CAP = 2000
TEST_ROWS = 500
DEFAULT_SEED = 42
TOP_K = 10
N_REPEATS = 3
# A feature whose univariate AUC is this close to 0.5 carries no marginal signal at all, so a tree
# model finding it useful is the design's "interaction structure only the tree model sees".
INTERACTION_MARGINAL_AUC = 0.02
# The dataset the wrongness check runs on: cheap (10 features), and it is the pilot's own anchor.
CONTROL_DATASET = "uslapseagent"
# One estimator, the library's fit mode, and batched prediction are throughput choices that the
# record states; `docs/plans/d2-feature-importance.md` carries the measurements behind them,
# including why `fit_with_cache` is rejected rather than used.
TABPFN_ESTIMATORS = 1
TABPFN_FIT_MODE = "fit_preprocessors"
PREDICT_BATCH = 10
# The benchmark's `logisticglm` is `penalty=None, max_iter=500`; on a 1,500-row subsample with 85
# near-collinear dummies the unpenalised MLE does not arrive in 500 steps. Measured on the runs'
# own splits: coil2000 converges at 1,262 iterations, eudirectlapse at 3,423, and
# spanish_motor_lapse needs 12,481 -- so 5,000 was still short and 20,000 is the budget that lets
# every anchor converge. The estimator is unchanged: only the budget, because an unconverged fit's
# importance describes the iteration limit rather than the data.
GLM_MAX_ITER = 20000
# A family whose test AUC is not at least this far above 0.5 has no ranking worth reading; its
# top-k is noise. The bound is one-sided on purpose: 0.49 and 0.35 are both "no signal".
CHANCE_MARGIN = 0.02
FAMILIES = ("tabpfn", "glm", "lgbm")


# ---------------------------------------------------------------------------
# The working set
# ---------------------------------------------------------------------------
def stratified_split(frame, target, *, cap, test_rows, seed):
    """The ticket's row cap, then a stratified split of it. Both seeded, both recorded.

    The cap is applied to the whole frame before the split, so `train_rows + test_rows == cap` and
    a reader never has to reconstruct whether the 2,000 included the test rows.
    """
    if len(frame) <= test_rows + 1:
        raise SystemExit(f"{len(frame)} row(s) cannot be split into {test_rows} test rows and a train set")
    if len(frame) > cap:
        subsample, _ = train_test_split(
            frame, train_size=cap, stratify=frame[target], random_state=seed
        )
    else:
        subsample = frame
    subsample = subsample.sort_index()
    train, test = train_test_split(
        subsample, test_size=test_rows, stratify=subsample[target], random_state=seed
    )
    return train.sort_index(), test.sort_index(), {
        "cap_rows": cap,
        "rows_available": int(len(frame)),
        "rows_sampled": int(len(subsample)),
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "seed": seed,
        "train_positive_rate": round(float(train[target].mean()), 6),
        "test_positive_rate": round(float(test[target].mean()), 6),
        "note": (
            f"importance is estimated from a {cap}-row subsample "
            f"({len(train)} train / {len(test)} test) and is therefore an approximation; "
            "the full table was not used"
        ),
    }


def encode_features(train, test, target):
    """The benchmark's `load_Xy` convention: per-column category codes, missing to 0.

    Categories come from the **training** rows only, so a value that appears only in the test rows
    cannot invent a feature value nothing was fitted on. A column that is constant across the
    training rows is dropped and named: it cannot be a lever, and TabPFN's own encoder removes it
    anyway, so keeping it would make one family's answer incommensurable with another's.
    """
    feature_names = [column for column in train.columns if column != target]
    train_encoded = train[feature_names].copy()
    test_encoded = test[feature_names].copy()

    for column in feature_names:
        if pd.api.types.is_numeric_dtype(train[column]):
            continue
        categories = pd.Index(train[column].dropna().unique())
        train_encoded[column] = pd.Categorical(train[column], categories=categories).codes
        test_encoded[column] = pd.Categorical(test[column], categories=categories).codes
        # Unseen categories (and missing values) arrive as -1; 0.0 matches the benchmark's fillna.
        train_encoded[column] = train_encoded[column].replace(-1, np.nan)
        test_encoded[column] = test_encoded[column].replace(-1, np.nan)

    train_encoded = train_encoded.fillna(0.0)
    test_encoded = test_encoded.fillna(0.0)

    dropped = [column for column in feature_names if train_encoded[column].nunique() <= 1]
    kept = [column for column in feature_names if column not in dropped]
    return (
        train_encoded[kept].to_numpy(dtype=np.float64),
        test_encoded[kept].to_numpy(dtype=np.float64),
        kept,
        dropped,
    )


def univariate_signal(X, y, feature_names):
    """ROC AUC of each feature used alone as a score, from the training rows only.

    The encoded column **is** what every family sees, category codes included -- so this is the
    marginal signal available in this preprocessing regime, not a claim about the raw column. That
    a code ordering is arbitrary for a categorical is exactly the limitation D4 exists to test.
    """
    _require_two_classes(y, "training")
    signal = {}
    for index, name in enumerate(feature_names):
        column = X[:, index]
        auc = 0.5 if np.all(column == column[0]) else float(roc_auc_score(y, column))
        signal[name] = round(auc, 6)
    return signal


# ---------------------------------------------------------------------------
# Permutation importance
# ---------------------------------------------------------------------------
def positive_probability(model):
    """A fitted classifier flattened to `X -> P(positive class)`.

    Every family is scored through one shape, so a family cannot accidentally be scored by
    `predict` while another is scored by `predict_proba`.
    """

    def predict(X):
        return np.asarray(model.predict_proba(X))[:, 1]

    return predict


def _require_two_classes(y, where):
    """Refuse a target with one class: AUC, and therefore importance, is undefined."""
    if len(np.unique(y)) < 2:
        raise SystemExit(f"the {where} rows carry a single class; importance is undefined")


def _scores(predict_probability, X):
    """The positive-class probability as a column, refusing a two-column answer.

    A `(n, 2)` matrix silently reaching `roc_auc_score` fails with a message about `y`, which sends
    a reader looking in the wrong place; this names the actual mistake.
    """
    scores = np.asarray(predict_probability(X))
    if scores.ndim != 1:
        raise SystemExit(
            f"predict_probability must return one probability per row, got shape {scores.shape}"
        )
    return scores


def permutation_importance(predict_probability, X, y, *, n_repeats, seed, batch=1):
    """AUC lost when one column is shuffled, per repeat.

    `predict_probability(X) -> positive-class probability`, so this is a function of a *fitted*
    model and never refits. Shuffling is seeded: two runs over the same rows produce the same
    matrix, which is what lets a reviewer recompute a number.

    `batch` stacks several permuted copies into **one** prediction call. It is throughput, not
    method: TabPFN spends most of a call preparing the context, so ten copies cost far less than
    ten calls (measured on coil2000: 85s for 5,000 rows against 277s for ten 500-row calls), and
    the permutations drawn are identical to the unbatched ones. A test pins that equivalence.

    Returns `(baseline_auc, matrix of shape (n_features, n_repeats))`.
    """
    _require_two_classes(y, "test")
    if batch < 1:
        raise SystemExit(f"batch must be at least 1, got {batch}")
    baseline = float(roc_auc_score(y, _scores(predict_probability, X)))
    rng = np.random.default_rng(seed)
    n_features = X.shape[1]
    importance = np.empty((n_features, n_repeats), dtype=float)
    for repeat in range(n_repeats):
        for start in range(0, n_features, batch):
            chunk = range(start, min(start + batch, n_features))
            stacked = np.vstack([_shuffle_column(X, index, rng) for index in chunk])
            scores = _scores(predict_probability, stacked).reshape(len(chunk), len(y))
            for row, index in enumerate(chunk):
                importance[index, repeat] = baseline - float(roc_auc_score(y, scores[row]))
    return baseline, importance


def _shuffle_column(X, index, rng):
    """A copy of `X` with one column permuted. The draw order is the caller's, not ours."""
    permuted = X.copy()
    permuted[:, index] = rng.permutation(permuted[:, index])
    return permuted


def rank_features(feature_names, importance):
    """One row per feature, most important first. Ties broken by name, so the order is total."""
    rows = [
        {
            "feature": name,
            "importance": round(float(np.mean(importance[index])), 6),
            "std": round(float(np.std(importance[index])), 6),
        }
        for index, name in enumerate(feature_names)
    ]
    rows.sort(key=lambda row: (-row["importance"], row["feature"]))
    return rows


# ---------------------------------------------------------------------------
# The three readings
# ---------------------------------------------------------------------------
def _spearman(rank_a, rank_b):
    """Spearman over every feature both rankings carry, from the ranks themselves.

    The families see one feature matrix, so the common set is normally all of it -- which makes
    "same features, ranked differently" a statement about the ordering rather than about a handful
    of top-k coincidences.
    """
    common = [feature for feature in rank_a if feature in rank_b]
    if len(common) < 3:
        return None
    a = np.array([rank_a[feature] for feature in common], dtype=float)
    b = np.array([rank_b[feature] for feature in common], dtype=float)
    return round(float(np.corrcoef(a, b)[0, 1]), 6)


def compare_readings(rankings, univariate, *, k):
    """The design's three readings, per family pair, as numbers rather than prose.

    `rankings` maps family -> `rank_features` output. `univariate` maps feature -> AUC.
    """
    top = {family: [row["feature"] for row in rows[:k]] for family, rows in rankings.items()}
    rank = {
        family: {row["feature"]: position + 1 for position, row in enumerate(rows)}
        for family, rows in rankings.items()
    }

    same_features = []
    different_features = []
    for a, b in combinations(list(rankings), 2):
        shared = [feature for feature in top[a] if feature in top[b]]
        union = sorted(set(top[a]) | set(top[b]))
        moves = sorted(
            (
                {
                    "feature": feature,
                    "rank_a": rank[a][feature],
                    "rank_b": rank[b][feature],
                    "rank_delta": abs(rank[a][feature] - rank[b][feature]),
                }
                for feature in shared
            ),
            key=lambda row: (-row["rank_delta"], row["feature"]),
        )
        same_features.append(
            {
                "a": a,
                "b": b,
                "spearman_all_features": _spearman(rank[a], rank[b]),
                "shared_top_k": len(shared),
                "largest_rank_moves": moves[:3],
            }
        )
        different_features.append(
            {
                "a": a,
                "b": b,
                "only_a": [feature for feature in top[a] if feature not in top[b]],
                "only_b": [feature for feature in top[b] if feature not in top[a]],
                "jaccard_top_k": round(len(shared) / len(union), 6) if union else None,
            }
        )

    interaction = None
    if "lgbm" in rankings:
        # "Only the tree model sees it" means neither OTHER family ranks it, TabPFN included --
        # TabPFN is itself an interaction learner, so a feature it puts first is not tree-only.
        # With no TabPFN arm the reading degrades to GLM-only and says which comparison it made.
        others = [family for family in ("tabpfn", "glm") if family in rankings]
        seen_by_others = {feature for family in others for feature in top[family]}
        detail = []
        for feature in top["lgbm"]:
            if feature in seen_by_others:
                continue
            detail.append(
                {
                    "feature": feature,
                    "lgbm_rank": rank["lgbm"][feature],
                    # A family may rank a feature it never reports in its top-k; `.get` keeps a
                    # missing rank a null rather than a KeyError through the `families=` seam.
                    "ranks": {
                        family: rank[family].get(feature) for family in ("tabpfn", "glm")
                        if family in rankings
                    },
                    "univariate_auc": univariate[feature],
                    "marginal": abs(univariate[feature] - 0.5) < INTERACTION_MARGINAL_AUC,
                }
            )
        interaction = {
            "compared_against": others,
            "rule": (
                "an LGBM top-k feature outside every other family's top-k whose univariate AUC is "
                f"within {INTERACTION_MARGINAL_AUC} of 0.5 -- no marginal signal, so any value the "
                "tree model finds comes from a combination"
            ),
            "tree_only_features": [row["feature"] for row in detail],
            "candidates": [row["feature"] for row in detail if row["marginal"]],
            "detail": detail,
        }

    return {
        "same_features_ranked_differently": same_features,
        "different_features": different_features,
        "interaction_only": interaction,
    }


def control_block(real_rankings, control_rankings, *, k):
    """Whether the label-permuted run's strongest feature clears the real run's strongest.

    The threshold is the real run's **top** importance in the same family, because the failure this
    check exists to catch is a feature that *dominates* an otherwise signal-free target -- leakage,
    or an artefact of the measurement. A top-k floor would be the wrong bar: with many weak features
    the k-th importance sits at zero (or below, since a permutation can raise AUC by chance), and
    the check would fail on noise. `k` is still recorded, because the reported top-k is where a
    dominating feature would show up first.
    """
    families = []
    for family, rows in real_rankings.items():
        real_top = rows[0]["importance"]
        control_top = control_rankings[family][0]
        families.append(
            {
                "family": family,
                "real_top_feature": rows[0]["feature"],
                "real_top_importance": real_top,
                "control_top_feature": control_top["feature"],
                "control_top_importance": control_top["importance"],
                # Recorded even when the check passes: a near miss is a fact about the measurement
                # that "passed" would hide.
                "ratio_to_real_top": (
                    round(control_top["importance"] / real_top, 6) if real_top > 0 else None
                ),
                "clears_threshold": control_top["importance"] >= real_top,
            }
        )
    return {
        "rule": (
            "the label-permuted run's top feature must not be as important as the real run's top "
            "feature in any family; if it is, the measurement is picking up leakage or an artefact"
        ),
        "k": k,
        "families": families,
        "passed": not any(row["clears_threshold"] for row in families),
    }


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
def _solver_note(model):
    """Iterations and convergence for a solver that has them; `None` for one that does not.

    A GLM that stopped at its iteration limit has not been fitted, and importance from it would be
    an artefact of the limit -- recorded so it cannot pass for a converged fit.
    """
    iterations = getattr(model, "n_iter_", None)
    if iterations is None:
        return None
    limit = getattr(model, "max_iter", None)
    reached = int(np.max(iterations))
    return {
        "iterations": reached,
        "max_iter": limit,
        "converged": (reached < limit) if limit else None,
    }


def _benchmark_methods():
    """The benchmark's own method registry, loaded rather than re-declared.

    A second copy of `LGBMClassifier(random_state=0)` here could drift from the one the frontier
    ran; this cannot. GLM is `logisticglm` -- the benchmark's canonical linear classifier -- and is
    not chosen by its test score, which would be selection on the evaluation set.
    """
    import importlib.util

    script = _REPO / "scripts" / "eval" / "insurance_benchmark_v1" / "run_frontier_benchmark.py"
    spec = importlib.util.spec_from_file_location("_frontier_methods", script)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise SystemExit(f"cannot load the benchmark method registry from {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["_frontier_methods"] = module
    spec.loader.exec_module(module)
    return module.CLASSIFICATION_METHODS


def tabpfn_provenance(*, n_estimators):
    """What the TabPFN arm asked for and what it actually loaded.

    #285's rule, applied to a diagnostic: a label is not a filename, so `auto` is recorded as the
    request and the package's own resolution is recorded beside it. A record that stated only the
    repository's `v3_default` label would describe intent while a v2.5 checkpoint produced the
    numbers.

    The resolution mirrors `tabpfn.base` exactly, because the obvious call is a trap: the library
    normalises `"auto"` to `None` *before* resolving, and `resolve_model_version("auto")` answers
    `v2` while `resolve_model_version(None)` answers the configured default. Getting this wrong
    would put a version in the record that no checkpoint matched.
    """
    import tabpfn
    from model_version import explicit_model_path

    requested = explicit_model_path()
    if requested == "auto":
        requested = None
    normalised = requested  # what the library will see: None means "use its default"
    resolved, checkpoint, reason = None, None, None
    try:
        from tabpfn.model_loading import resolve_model_path, resolve_model_version

        version = resolve_model_version(normalised)
        resolved = getattr(version, "value", str(version))
        paths, _, _, _ = resolve_model_path(normalised, which="classifier", version=resolved)
        checkpoint = paths[0].name if paths else None
    except Exception as error:  # pragma: no cover - only on a package that moved these helpers
        reason = f"{type(error).__name__}: {error}"
    return {
        "requested_model_path": requested or "auto",
        "resolved_version": resolved,
        "checkpoint": checkpoint,
        "resolution_reason": reason,
        "package_version": getattr(tabpfn, "__version__", None),
        "n_estimators": n_estimators,
        "fit_mode": TABPFN_FIT_MODE,
        "fit_mode_note": (
            "the pilot fits with n_estimators=2 and fit_mode='batched'; this diagnostic uses one "
            "estimator and the library default because a permutation run makes features x repeats "
            "predictions against one context on CPU. fit_with_cache was measured and rejected -- "
            "see docs/plans/d2-feature-importance.md, measurement B."
        ),
    }


def default_families(*, n_estimators):
    """The three families as fitted-model builders: `(X_train, y_train) -> fitted model`."""
    import torch
    from tabpfn import TabPFNClassifier

    from model_version import explicit_model_path

    pin = explicit_model_path()
    methods = _benchmark_methods()

    def build_tabpfn(X, y):
        kwargs = {
            "ignore_pretraining_limits": True,
            "device": "cpu",
            "n_estimators": n_estimators,
            "random_state": DEFAULT_SEED,
            "inference_precision": torch.float32,
            "fit_mode": TABPFN_FIT_MODE,
        }
        if pin:
            kwargs["model_path"] = pin
        model = TabPFNClassifier(**kwargs)
        model.fit(X, y)
        return model

    def build_from_registry(method_id, *, max_iter=None):
        def build(X, y):
            model = methods[method_id].build()
            if max_iter is not None:
                model.set_params(max_iter=max_iter)
            model.fit(X, y)
            return model

        return build

    return {
        "tabpfn": build_tabpfn,
        "glm": build_from_registry("logisticglm", max_iter=GLM_MAX_ITER),
        "lgbm": build_from_registry("lgbm"),
    }


# ---------------------------------------------------------------------------
# One dataset
# ---------------------------------------------------------------------------
def main(argv=None, *, root=None, datasets=None, families=None):
    """Run D2 and write one record per dataset."""
    parser = argparse.ArgumentParser(description="D2 -- feature importance across three families.")
    parser.add_argument("--csv", type=Path, help="the table to explain (ad-hoc, single file)")
    parser.add_argument("--target", help="target column in --csv")
    parser.add_argument(
        "--dataset",
        action="append",
        default=[],
        metavar="NAME",
        help="explain a registered pilot dataset by name (repeatable)",
    )
    parser.add_argument(
        "--all-anchors",
        action="store_true",
        help="explain every dataset the pilot registry declares",
    )
    parser.add_argument("--name", default=None, help="dataset name recorded (default: file stem)")
    parser.add_argument("--run-id", default=None, help="record directory prefix (default: UTC now)")
    parser.add_argument(
        "--control-dataset",
        default=CONTROL_DATASET,
        metavar="NAME",
        help="dataset the label-permutation control runs on (default: %(default)s)",
    )
    parser.add_argument(
        "--no-control",
        action="store_true",
        help="skip the wrongness check -- an explicitly weaker run, recorded as such",
    )
    parser.add_argument("--subsample", type=int, default=SUBSAMPLE_CAP, help="row cap (default: %(default)s)")
    parser.add_argument("--test-rows", type=int, default=TEST_ROWS, help="held-out rows (default: %(default)s)")
    parser.add_argument("--repeats", type=int, default=N_REPEATS, help="permutation repeats (default: %(default)s)")
    parser.add_argument(
        "--predict-batch",
        type=int,
        default=PREDICT_BATCH,
        help="permuted copies per prediction call -- throughput, not method (default: %(default)s)",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="split and permutation seed")
    parser.add_argument(
        "--n-estimators",
        type=int,
        default=TABPFN_ESTIMATORS,
        help="TabPFN ensemble size (default: %(default)s; the pilot uses 2)",
    )
    args = parser.parse_args(argv)

    if args.csv is None and not args.dataset and not args.all_anchors:
        parser.error("give --csv, or --dataset NAME, or --all-anchors")
    if args.csv is not None and args.target is None:
        parser.error("--csv needs --target")

    targets = _targets(args, datasets)
    names = [name for name, _, _ in targets]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise SystemExit(f"duplicate dataset name(s) {duplicates}: one record per name, per run")
    if not args.no_control and args.control_dataset not in names:
        raise SystemExit(
            f"--control-dataset {args.control_dataset!r} is not among the datasets run "
            f"({names}); the control's threshold is the real run's, so it cannot be borrowed"
        )
    missing = [str(file) for _, file, _ in targets if not file.exists()]
    if missing:
        raise SystemExit(f"no such file(s): {missing}")

    # `families` is the test seam. A record produced through it must not borrow a model label for a
    # TabPFN this process never loaded, so it says what it is instead.
    provenance = tabpfn_provenance(n_estimators=args.n_estimators) if families is None else None
    families = families or default_families(n_estimators=args.n_estimators)
    model_version = (
        provenance["requested_model_path"] if provenance is not None else "injected-families"
    )
    base_run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    control_passed = None
    for name, file, target in targets:
        measurements = explain_dataset(
            path=file,
            target=target,
            families=families,
            provenance=provenance,
            run_control=not args.no_control and name == args.control_dataset,
            cap=args.subsample,
            test_rows=args.test_rows,
            repeats=args.repeats,
            seed=args.seed,
            batch=args.predict_batch,
        )
        if args.no_control:
            # `control: None` already means "not this dataset"; without this line a skipped check
            # would read exactly like a dataset the control never had to cover.
            measurements["limitations"].append(
                "the label-permutation control was not run (`--no-control`): this record carries "
                "no wrongness check"
            )
        record = DiagnosticRecord(
            diagnostic=DIAGNOSTIC,
            run_id=f"{base_run_id}-{name}",
            dataset_name=name,
            dataset_sha256=sha256_file(file),
            # `auto` when nobody pinned a checkpoint (#285) -- never the repository's label for a
            # model this diagnostic did not load.
            model_version=model_version,
            seed=args.seed,
            matched_context=matched_context_evidence(),
            measurements=measurements,
        )
        written = write_diagnostic_record(record, root=root or DIAGNOSTICS_ROOT)
        print(f"{DIAGNOSTIC} {name}: {written}")
        for family, result in measurements["families"].items():
            print(f"  {family:8} auc={result['test_auc']:.4f}  top: {', '.join(result['top_k'][:5])}")
        control = measurements.get("control")
        if control is not None:
            print(f"  control: {'passed' if control['passed'] else 'FAILED'}")
            control_passed = control["passed"]

    if control_passed is False:
        print(
            "CONTROL FAILED: a label-permuted run produced a feature as important as the real "
            "run's most important feature. The records were written because they are the evidence "
            "of the failure; the importance in them is not interpretable.",
            file=sys.stderr,
        )
        return 1
    return 0


def explain_dataset(*, path, target, families, provenance, run_control, cap, test_rows, repeats, seed, batch):
    """D2's measurements for one dataset. Pure apart from the models it is handed."""
    frame = pd.read_csv(path)
    if target not in frame.columns:
        raise SystemExit(f"target column {target!r} is not in {path}: {list(frame.columns)}")
    frame = frame.dropna(subset=[target]).reset_index(drop=True)

    train, test, split = stratified_split(frame, target, cap=cap, test_rows=test_rows, seed=seed)
    X_train, X_test, feature_names, dropped = encode_features(train, test, target)
    y_train = train[target].to_numpy(dtype=np.int64)
    y_test = test[target].to_numpy(dtype=np.int64)
    univariate = univariate_signal(X_train, y_train, feature_names)

    measured = _measure_all(
        families, X_train, y_train, X_test, y_test, feature_names,
        repeats=repeats, seed=seed, batch=batch,
    )
    rankings = {family: result["ranking"] for family, result in measured.items()}

    measurements = {
        "question": "which features does each family use, and where do they disagree",
        "subsample": split,
        "preprocessing": {
            "regime": "R1 default -- per-column category codes, missing to 0",
            "note": (
                "categories come from the training rows only; a categorical's code ordering is "
                "arbitrary, which D4 tests rather than assumes"
            ),
            "n_features": len(feature_names),
            "n_dropped_constant": len(dropped),
            "dropped_constant": dropped,
        },
        "tabpfn": provenance,
        "importance": {
            "method": "permutation on the held-out rows",
            "metric": "drop in ROC AUC",
            "repeats": repeats,
            "seed": seed,
            "predict_batch": batch,
            "top_k": TOP_K,
        },
        "families": {
            family: {
                "test_auc": round(result["test_auc"], 6),
                # A model with no signal still has a ranking, but it is a ranking of noise. Saying
                # so in the record is cheaper than a reader discovering it from the AUC three keys
                # away. One-sided: a family below chance is not "at chance", it is also unusable.
                "no_better_than_chance": result["test_auc"] < 0.5 + CHANCE_MARGIN,
                "solver": result["solver"],
                "top_k": [row["feature"] for row in result["ranking"][:TOP_K]],
                "ranking": result["ranking"],
            }
            for family, result in measured.items()
        },
        "univariate": univariate,
        "readings": compare_readings(rankings, univariate, k=TOP_K),
        "control": None,
        "limitations": [
            f"importance is measured on a {split['rows_sampled']}-row subsample, not the whole table",
            "permutation importance credits a correlated pair twice: a feature with a near-duplicate "
            "can look unimportant because the model can fall back on its twin",
            "the TabPFN arm is the local open checkpoint, not the v3 the frontier numbers used",
            *_no_signal_notes(measured),
        ],
    }

    if run_control:
        measurements["control"] = _control(
            families,
            X_train,
            y_train,
            X_test,
            y_test,
            feature_names,
            rankings,
            repeats=repeats,
            seed=seed,
            batch=batch,
        )
    return measurements


def _no_signal_notes(measured):
    """Name every family whose test AUC is not meaningfully above chance, and say why it matters."""
    notes = []
    for family, result in measured.items():
        auc = result["test_auc"]
        if auc >= 0.5 + CHANCE_MARGIN:
            continue
        position = "at chance" if abs(auc - 0.5) < CHANCE_MARGIN else "below chance"
        notes.append(
            f"{family} is {position} (test AUC {auc:.4f}): its importance ranking is a ranking of "
            "noise, and any reading taken from it is uninterpretable"
        )
    return notes


def _control(families, X_train, y_train, X_test, y_test, feature_names, real_rankings, *, repeats, seed, batch):
    """The same pipeline on label-permuted copies of the split, and the verdict against it."""
    rng = np.random.default_rng(seed)
    y_train_permuted = rng.permutation(y_train)
    y_test_permuted = rng.permutation(y_test)
    _require_two_classes(y_train_permuted, "permuted training")
    _require_two_classes(y_test_permuted, "permuted test")

    measured = _measure_all(
        families,
        X_train,
        y_train_permuted,
        X_test,
        y_test_permuted,
        feature_names,
        repeats=repeats,
        seed=seed,
        batch=batch,
    )
    rankings = {family: result["ranking"] for family, result in measured.items()}
    block = control_block(real_rankings, rankings, k=TOP_K)
    block["permuted_test_auc"] = {
        family: round(result["test_auc"], 6) for family, result in measured.items()
    }
    block["note"] = (
        "a permuted target leaves no signal, so every family should sit at chance and no feature "
        "should dominate; a dominance here would mean the real run measured an artefact"
    )
    return block


def _measure_all(families, X_train, y_train, X_test, y_test, feature_names, *, repeats, seed, batch):
    measured = {}
    for family, build in families.items():
        model = build(X_train, y_train)
        baseline, importance = permutation_importance(
            positive_probability(model), X_test, y_test, n_repeats=repeats, seed=seed, batch=batch
        )
        measured[family] = {
            "test_auc": baseline,
            "solver": _solver_note(model),
            "ranking": rank_features(feature_names, importance),
        }
    return measured


def _targets(args, datasets):
    if args.csv is not None:
        return [(args.name or args.csv.stem, args.csv, args.target)]
    registry = datasets if datasets is not None else load_anchor_datasets()
    names = list(registry) if args.all_anchors else args.dataset
    unknown = [name for name in names if name not in registry]
    if unknown:
        raise SystemExit(f"unknown dataset(s) {unknown}; the registry holds {sorted(registry)}")
    return [(name, Path(registry[name]["file"]), registry[name]["target"]) for name in names]


if __name__ == "__main__":
    raise SystemExit(main())
