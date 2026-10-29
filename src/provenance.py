"""Provenance: the identity a number was produced under, recorded one way.

Issue #211. `GLOSSARY.md` defines **provenance** as "dataset, seed, fold construction, model
version, and git sha", and `docs/adr/0001-experiment-spec-pins-version-and-guards-reuse.md`
adds that a model version is recorded, never inferred. This module is the one place the pilot
and the diagnostics compute those facts, so that D1-D5 cannot each spell them differently.

Three things live here:

* the dataset fingerprint and the matched-inference-context assertion, moved out of
  `scripts/run_pilot.py` (PR-4, PR-6) and imported back by it -- same behaviour, same words;
* the constants that give those helpers their meaning: which arms carry an inference context,
  and which arm is the baseline;
* `write_diagnostic_record`, the single writer every diagnostic emits through.

The writer exists because `outputs/gpu-pilot/README.md` records two failures this repository has
already paid for: a `csv.DictWriter` header written against an older schema shifted **every**
ledger column, and a record split across two clones made **three runs** invisible. Both were
caught once, by hand, on one dataset. Five producers make the same class of error undetectable,
because the point of the diagnostics is that their outputs are comparable.

So there is exactly one field definition here -- the `DiagnosticRecord` dataclass -- and the CSV
header is derived from it at write time. Each record gets its own
`<root>/<diagnostic>/<run_id>/` directory and is never appended to a file whose header an older
schema wrote, so a stale header cannot survive a field change. An existing record is refused
rather than replaced: its timestamp and git sha describe the run that produced it, and a second
run is a second record.

What is *not* here yet: the pilot's own `provenance` block, a verdict reader, and pilot schema 3.
Those are #240/#241's, and they extend this module rather than replace it. The pilot's record
shape is untouched by this change (`SCHEMA_VERSION` stays 2).
"""

from __future__ import annotations

import csv
import json
import subprocess
from dataclasses import asdict, dataclass, field, fields, replace
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

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
        "file": f"{name}.csv",
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


def matched_context_evidence(per_arm=None):
    """The matched-context assertion, as evidence a record can carry.

    Runs the assertion rather than restating its verdict, so a record cannot claim a pass the
    assertion did not give. `checked` is False when no arm carried an inference context: a
    diagnostic that ran no model states that, instead of a pass nobody earned.
    """
    per_arm = dict(per_arm or {})
    assert_matched_context(per_arm)
    return {
        "checked": any(rows is not None for rows, _ in per_arm.values()),
        "baseline_arm": BASELINE_TABPFN_ARM,
        "arms": {
            arm: {"rows": rows, "mechanism": mechanism}
            for arm, (rows, mechanism) in per_arm.items()
        },
    }


# ---------------------------------------------------------------------------
# Runtime  (#211)
# ---------------------------------------------------------------------------
def runtime_versions():
    """The stack that produced a result, recorded rather than assumed.

    TabPFN changes its default checkpoint and fine-tuning API across majors, so a number
    without the producing version is not reproducible. The keys match the pilot's own record
    (`run_pilot._runtime_versions`), so #241 can merge both into one `provenance.code.runtime`
    block without renaming anything.

    Imported lazily: `torch` and `catboost` are heavy, and a diagnostic that only reads a CSV
    should not pay for them unless the writer stamps the environment.
    """
    import platform

    versions = {"python": platform.python_version()}
    for mod_name, key in (
        ("numpy", "numpy"),
        ("pandas", "pandas"),
        ("sklearn", "scikit-learn"),
        ("torch", "torch"),
        ("tabpfn", "tabpfn"),
        ("catboost", "catboost"),
    ):
        try:
            versions[key] = getattr(__import__(mod_name), "__version__", "unknown")
        except Exception:
            versions[key] = None
    return versions


# ---------------------------------------------------------------------------
# Diagnostic records  (#211)
# ---------------------------------------------------------------------------
DIAGNOSTIC_RECORD_SCHEMA_VERSION = 1
DIAGNOSTICS_ROOT = REPO_ROOT / "outputs" / "diagnostics"

_UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
_CSV = "record.csv"
_JSON = "record.json"


@dataclass(frozen=True, kw_only=True)
class DiagnosticRecord:
    """One diagnostic's record. The field set below **is** the contract.

    A diagnostic supplies the values it measured and nothing else. `schema_version`,
    `created_utc`, `git_sha`, `git_dirty` and `runtime` are stamped by
    `write_diagnostic_record`, so two diagnostics cannot stamp them differently -- and a change
    to the shape of a record is a version bump here rather than an archaeology exercise later.

    `measurements` is the one free-form field: each diagnostic brings its own numbers, but they
    live under one fixed key. That is what keeps the keys comparable between D1 and D2 while
    their contents differ.

    `model_version` is the **resolved** label (`v3_default`, never a weights filename), per
    docs/MODEL_VERSIONS.md. A diagnostic that runs no model still records the label this
    environment resolves to, because its output is read against model runs; `matched_context`
    says whether any arm was actually compared.

    `seed` is the run's split seed. D1 profiles a whole table and has no split, so it records
    `None` -- the absence stated rather than a seed borrowed from elsewhere.

    `matched_context` is the evidence behind the PR-4 assertion, built by
    `matched_context_evidence`, so a record carries the verdict *and* the numbers compared.
    """

    schema_version: int = DIAGNOSTIC_RECORD_SCHEMA_VERSION
    diagnostic: str
    run_id: str
    created_utc: str | None = None
    git_sha: str | None = None
    git_dirty: bool | None = None
    model_version: str | None
    seed: int | None
    dataset_name: str
    dataset_sha256: str | None
    matched_context: Mapping[str, Any]
    runtime: Mapping[str, Any] | None = None
    measurements: Mapping[str, Any] = field(default_factory=dict)


# The single field definition. The JSON keys and the CSV header are both taken from it, so
# there is no per-call field list that could drift out of step with the dataclass.
DIAGNOSTIC_RECORD_FIELDS = tuple(f.name for f in fields(DiagnosticRecord))


def git_revision(repo_root=None):
    """`(sha, dirty)` of the code that ran.

    `dirty` counts changed **tracked** files only. Untracked files are excluded on purpose: a
    run's own outputs are untracked by design, and counting them would mark every record dirty,
    which would make the flag say nothing.
    """

    def run(*args):
        try:
            return subprocess.run(
                ["git", *args],
                cwd=repo_root or REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=10,
            ).stdout.strip()
        except Exception:
            return ""

    porcelain = run("status", "--porcelain")
    dirty = any(
        ln[:2].strip() and not ln.startswith("??") for ln in porcelain.splitlines()
    )
    return run("rev-parse", "HEAD") or None, dirty


def _csv_cell(value):
    """One CSV cell, spelled so two writers cannot disagree about a type.

    `measurements` is JSON with sorted keys, so the same numbers serialise to the same bytes.
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, Mapping):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    return str(value)


def _record_path(record, root):
    """`<root>/<diagnostic>/<run_id>` -- derived, never chosen by the caller."""
    for part in (record.diagnostic, record.run_id):
        if not part or part in (".", "..") or "/" in part or "\\" in part:
            raise ValueError(f"a record path component must be a plain name, got {part!r}")
    return Path(root or DIAGNOSTICS_ROOT) / record.diagnostic / record.run_id


def write_diagnostic_record(record, *, root=None):
    """Write one diagnostic's record under ``<root>/<diagnostic>/<run_id>/``.

    This is the only writer D1-D5 may use, and it makes the two failures recorded in
    `outputs/gpu-pilot/README.md` impossible rather than merely unlikely:

    * **a stale header.** The CSV header is `DIAGNOSTIC_RECORD_FIELDS`, derived from
      `DiagnosticRecord`. It is written into a *new* directory, never appended to a file an
      older schema wrote, so no header can outlive the field set that produced it.
    * **a split record.** One call writes `record.json` (the source of truth) and `record.csv`
      (the one-row view of it) into one directory whose path is derived from the diagnostic
      and the run id -- there is no second location a record could half-exist in.

    **REFUSES to replace an existing record**, with the same rule and the same shape of message
    `run_pilot.write_arm_run` uses. A record's `created_utc` and `git_sha` describe the run that
    produced it; replacing the file would re-stamp those fields and leave an old record claiming
    it was produced now. A second run is a second run: give it its own run id.

    Returns the directory written.
    """
    if record.git_sha is None or record.git_dirty is None:
        sha, dirty = git_revision()
        record = replace(
            record,
            git_sha=record.git_sha if record.git_sha is not None else sha,
            git_dirty=record.git_dirty if record.git_dirty is not None else dirty,
        )
    if not record.created_utc:
        record = replace(record, created_utc=datetime.now(timezone.utc).strftime(_UTC_FORMAT))
    if record.runtime is None:
        record = replace(record, runtime=runtime_versions())

    target = _record_path(record, root)
    if target.exists() and any(target.iterdir()):
        raise FileExistsError(
            f"REFUSING TO OVERWRITE: {target} already holds a record. It was produced by an "
            f"earlier run, and its created_utc and git_sha describe that run -- replacing it "
            f"would make an old record claim it was produced now. Write this run under a new "
            f"run id."
        )
    target.mkdir(parents=True, exist_ok=True)

    payload = asdict(record)
    if tuple(payload) != DIAGNOSTIC_RECORD_FIELDS:
        # Cannot happen through the dataclass; kept so a hand-built dict can never become a
        # second field definition in the future.
        raise RuntimeError("record fields and the dataclass have diverged")

    (target / _JSON).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with open(target / _CSV, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(DIAGNOSTIC_RECORD_FIELDS), lineterminator="\n")
        writer.writeheader()
        writer.writerow({k: _csv_cell(v) for k, v in payload.items()})
    return target


def read_diagnostic_record(path):
    """Read a record back as the dict it was written from. Fail-closed on the version."""
    record = json.loads((Path(path) / _JSON).read_text(encoding="utf-8"))
    version = record.get("schema_version")
    if version != DIAGNOSTIC_RECORD_SCHEMA_VERSION:
        raise ValueError(
            f"{path}: schema_version {version!r} is not one this reader understands "
            f"({DIAGNOSTIC_RECORD_SCHEMA_VERSION})"
        )
    return record
