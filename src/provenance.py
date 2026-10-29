"""Provenance: the identity a number was produced under, recorded one way.

Issue #211. `GLOSSARY.md` defines **provenance** as "dataset, seed, fold construction, model
version, and git sha", and `docs/adr/0001-experiment-spec-pins-version-and-guards-reuse.md`
adds that a model version is recorded, never inferred. This module is the one place the pilot
and the diagnostics compute those facts, so that D1-D5 cannot each spell them differently.

Two things live here:

* the dataset fingerprint and the matched-inference-context assertion, moved out of
  `scripts/run_pilot.py` (PR-4, PR-6) and imported back by it -- same behaviour, same words;
* the constants that give those helpers their meaning: which arms carry an inference context,
  and which arm is the baseline.

`write_diagnostic_record`, the single writer every diagnostic emits through, lands next.

What is *not* here yet: the pilot's own `provenance` block, a verdict reader, and pilot schema 3.
Those are #240/#241's, and they extend this module rather than replace it. The pilot's record
shape is untouched by this change (`SCHEMA_VERSION` stays 2).
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]

# Which arms are fine-tuning arms (subject to the matched-context assertion, PR-4).
FT_ARMS = ("B_in_domain", "B_ft3", "B_ft10", "B_ft30", "C_pooled_all", "D_pooled_homog")
BASELINE_TABPFN_ARM = "A_raw"


# ---------------------------------------------------------------------------
# Data provenance  (PR-6)
# ---------------------------------------------------------------------------
def sha256_file(path, chunk=1 << 20):
    """sha256 of a file's bytes, streamed so a large CSV never lands in memory."""
    h = sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


@dataclass(frozen=True)
class DataSource:
    """Where a dataset's bytes came from, as the caller pinned them.

    `ref_is_pinned` is the caller's statement about `ref`, not a judgement made here: `main` is
    a moving branch, so a record that used it says so rather than implying a pin. The pinning
    policy belongs to the runner that chose the ref.
    """

    url: str
    repo: str
    ref: str
    ref_is_pinned: bool


def dataset_fingerprint(name, *, target, data_dir, repo_root, source):
    """Content hash + shape + class balance for a dataset (PR-6).

    Moved from `scripts/run_pilot.py` unchanged in behaviour. Only the inputs the pilot used to
    read off its own module globals are explicit, because a diagnostic needs the same
    fingerprint without inheriting the pilot's dataset registry. #241 narrows this further to a
    frame plus target, when the pilot's record gains its `provenance` block.
    """
    path = Path(data_dir) / f"{name}.csv"
    if not path.exists():
        return {"name": name, "path": str(path), "exists": False}
    df = pd.read_csv(path)
    y = df[target].astype(int)
    return {
        "name": name,
        "path": str(path.relative_to(repo_root)),
        "file": path.name,
        "sha256": sha256_file(path),
        "n_rows": int(len(df)),
        "n_cols": int(df.shape[1]),
        "columns": list(df.columns),
        "target_col": target,
        "positive_rate": round(float(y.mean()), 6),
        "n_positive": int(y.sum()),
        # Provenance of the bytes: a content hash alone tells you a file CHANGED, not
        # where to get the original back. DATA_REF pins the source; default `main` is a
        # moving branch and is recorded as such so the gap is visible rather than implied.
        "source_url": source.url,
        "source_repo": source.repo,
        "source_ref": source.ref,
        "source_ref_is_pinned": source.ref_is_pinned,
    }


# ---------------------------------------------------------------------------
# Matched inference context  (PR-4)
# ---------------------------------------------------------------------------
def inference_context_rows(arm, n_train):
    """Effective inference context for an arm, and the mechanism behind it.

    This is what the historic study got wrong: the fine-tuned arm there was
    evaluated with SUBSAMPLE_SAMPLES=64/128 while the raw arm used the whole
    training split. In the shipped trainer the inference model is refit on the
    full training data (`_setup_inference_model` -> `fit(self.X_, self.y_)`), so
    both arms carry the full training split as context.
    """
    if arm == BASELINE_TABPFN_ARM:
        return n_train, "TabPFNClassifier.fit(X_train) -- full training split"
    if arm in FT_ARMS:
        return n_train, "FinetunedTabPFNClassifier refits inference on full X_ (shipped trainer)"
    return None, "not a TabPFN context-carrying arm"


def assert_matched_context(per_arm):
    """Refuse to compare TabPFN arms whose inference contexts differ (PR-4)."""
    a = per_arm.get(BASELINE_TABPFN_ARM)
    if a is None or a[0] is None:
        return True
    ft = {k: v for k, v in per_arm.items() if k in FT_ARMS and v[0] is not None}
    if not ft:
        return True
    mismatched = {k: v[0] for k, v in ft.items() if v[0] != a[0]}
    if mismatched:
        raise AssertionError(
            "MATCHED-CONTEXT VIOLATION: raw arm context="
            f"{a[0]} but {mismatched} differ. The historic comparison was invalidated "
            "by exactly this; fix the context before reporting any delta."
        )
    return True
