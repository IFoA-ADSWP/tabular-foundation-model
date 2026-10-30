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

#241 adds the record contract to the same module, so the block's vocabulary has one definition:

* `dataset_fingerprint` now takes the frame the caller loaded, plus the target and drop
  columns, instead of resolving a dataset name against a runner's registry;
* `split_section`, `model_section` and `code_section` are the sections' single field
  definitions, and `provenance_block` assembles them into the one top-level key a record
  carries -- a runner supplies values and never restates a key name;
* `read_record` and `verdict` turn any record into a stated verdict -- `comparable`,
  `partial` or `unusable` -- naming the keys that are missing, dispatching on a
  `schema_version` per record kind and raising on one it does not know rather than
  guessing. A pilot arm record and a capture manifest written before the block are read
  through their documented top-level keys, so they are `partial` rather than unreadable;
  an argv-only manifest identifies nothing and is `unusable`.

A verdict is computed from the record, never stored in it: a record that claims to be
comparable while lacking a content hash is exactly the failure the verdict exists to catch.
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


def dataset_fingerprint(name, *, frame=None, target, drop=(), path=None, repo_root=REPO_ROOT, source=None):
    """Content hash + shape + class balance for a dataset, from the frame the caller loaded.

    Moved from `scripts/run_pilot.py` by #211; #241 replaces the `name`-plus-`data_dir`
    signature with the frame itself, so a second runner can fingerprint what it actually
    loaded without inheriting the pilot's dataset registry. `target` and `drop` are recorded
    because they define the feature matrix: the same bytes with a different leak-drop is a
    different experiment, and a reader comparing two records has to be able to see that.
    `drop` is the set of columns **as applied by the runner**, not a claim about what should
    have been dropped.

    A table that is not on disk is STATE, not an error: the original behaviour, kept so a run
    that could not find its data is legible instead of absent. With `frame` supplied the frame
    is fingerprinted; with only `path` the file is read; with neither, `ValueError`.

    `sha256` is over the bytes on disk, which is what `path` is for. A frame that never came
    from a file records `sha256: None` -- the absence stated, because a hash this helper
    invented from the in-memory rows would not be checkable against a re-download.
    """
    file_path = Path(path) if path is not None else None
    if frame is None:
        if file_path is None:
            raise ValueError(
                f"dataset_fingerprint({name!r}): pass the frame the caller loaded, or the path "
                f"to the table; a fingerprint of neither would describe nothing"
            )
        if not file_path.exists():
            return {"name": name, "path": str(file_path), "exists": False}
        frame = pd.read_csv(file_path)

    y = frame[target].astype(int)
    drop = list(drop)
    if file_path is not None and file_path.exists():
        try:
            recorded_path = str(file_path.resolve().relative_to(Path(repo_root).resolve()))
        except ValueError:  # a file outside the repo is recorded where it is
            recorded_path = str(file_path)
        content_sha256 = sha256_file(file_path)
    else:
        recorded_path = None if file_path is None else str(file_path)
        content_sha256 = None
    return {
        "name": name,
        "path": recorded_path,
        "file": file_path.name if file_path is not None else None,
        "target": target,
        "drop": drop,
        "sha256": content_sha256,
        "n_rows": int(len(frame)),
        "n_cols": int(frame.shape[1]),
        "columns": list(frame.columns),
        "positive_rate": round(float(y.mean()), 6),
        "n_positive": int(y.sum()),
        # Provenance of the bytes: a content hash alone tells you a file CHANGED, not
        # where to get the original back. DATA_REF pins the source; default `main` is a
        # moving branch and is recorded as such so the gap is visible rather than implied.
        "source_url": source.url if source else None,
        "source_repo": source.repo if source else None,
        "source_ref": source.ref if source else None,
        "source_ref_is_pinned": source.ref_is_pinned if source else None,
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


# ---------------------------------------------------------------------------
# The record contract: a provenance block, and the verdict it earns  (#241)
# ---------------------------------------------------------------------------
# A record declares the layout it was written with, and the reader dispatches on it per KIND:
# an arm record and a capture manifest do not share a version space, so a capture declaring 3
# must not be read just because some other layout has a 3 in it.
ARM_RECORD_SCHEMA_VERSION = 4  # 4 adds the optional `experiment` section (ADR 0004)
PILOT_RUN_SCHEMA_VERSION = 2  # the invocation manifest and meta.FAILED.json
FRONTIER_MANIFEST_SCHEMA_VERSION = 1  # #240's layout; the committed ones predate it
CAPTURE_SCHEMA_VERSION = 2  # 1 is the committed layout; 2 is #240's

ARM_RECORD_KIND = "pilot_arm"
PILOT_MANIFEST_KIND = "pilot_manifest"
FRONTIER_MANIFEST_KIND = "frontier_manifest"
CAPTURE_KIND = "capture"

COMPARABLE = "comparable"
PARTIAL = "partial"
UNUSABLE = "unusable"

_PROVENANCE = "provenance"
_DATASET = "dataset"
_SPLIT = "split"
_MODEL = "model"
_CODE = "code"
_EXPERIMENT = "experiment"

# The block's vocabulary, defined once. The builders assemble their sections from these names
# and `verdict` builds its missing-key paths from the same ones, so a rename cannot leave the
# reader pointing at a key no writer emits.
DATASET_NAME = "name"
DATASET_SHA256 = "sha256"
SPLIT_N_FOLDS = "n_folds"
SPLIT_SEED = "seed"
SPLIT_SHA256 = "sha256"
SPLIT_RULE = "rule"
MODEL_VERSION = "version"
MODEL_VERSION_SOURCE = "version_source"
MODEL_WEIGHTS_SHA256 = "weights_sha256"
MODEL_CLIENT_VERSION = "client_version"
CODE_GIT_SHA = "git_sha"
CODE_DIRTY = "dirty"
CODE_RUNTIME = "runtime"
CODE_IMAGE = "image"

SPLIT_KEYS = (SPLIT_N_FOLDS, SPLIT_SEED, SPLIT_SHA256, SPLIT_RULE)
MODEL_KEYS = (MODEL_VERSION, MODEL_VERSION_SOURCE, MODEL_WEIGHTS_SHA256, MODEL_CLIENT_VERSION)
CODE_KEYS = (CODE_GIT_SHA, CODE_DIRTY, CODE_RUNTIME, CODE_IMAGE)

EXPERIMENT_ID = "id"
EXPERIMENT_MODEL_VERSION = "model_version"
EXPERIMENT_DECLARED = "declared"
EXPERIMENT_RESOLVED = "resolved"
EXPERIMENT_KEYS = (EXPERIMENT_ID, EXPERIMENT_MODEL_VERSION, EXPERIMENT_DECLARED,
                   EXPERIMENT_RESOLVED)


@dataclass(frozen=True)
class RecordLayout:
    """One record kind's layout: which versions exist, and what an absent version means.

    `absent_means` is `None` where every committed record of that kind declares a version, so
    an absent one is a record this reader cannot place -- not a legacy record to guess at. It
    is 1 only where an unversioned layout is documented: the pilot arm records written before
    `schema_version` existed, and the frontier run manifests #240 describes as unversioned.

    A kind whose pre-block layout is recorded well enough to read has a reader in
    `_LEGACY_SECTION_READERS`: the pilot arm record carries `dataset_fingerprint` and
    `split_fingerprint` at the top level, and a capture manifest carries its dataset name,
    fold count, seed, model version and script sha. The kinds with no such reader (the
    invocation manifests) cannot identify a split at all, so they stay `unusable` rather than
    being reinterpreted here -- #243 owns the frontier's own block.
    """

    kind: str
    known_versions: tuple[int, ...]
    absent_means: int | None


RECORD_LAYOUTS = {
    ARM_RECORD_KIND: RecordLayout(ARM_RECORD_KIND, (1, 2, 3, ARM_RECORD_SCHEMA_VERSION), 1),
    PILOT_MANIFEST_KIND: RecordLayout(PILOT_MANIFEST_KIND, (1, PILOT_RUN_SCHEMA_VERSION), None),
    FRONTIER_MANIFEST_KIND: RecordLayout(
        FRONTIER_MANIFEST_KIND, (FRONTIER_MANIFEST_SCHEMA_VERSION,), 1
    ),
    CAPTURE_KIND: RecordLayout(CAPTURE_KIND, (1, CAPTURE_SCHEMA_VERSION), None),
}

_MISSING = object()


def split_rule(constructor, **params):
    """The fold construction as a RULE, not a sentence.

    `KFold(5, shuffle=True, random_state=42)` in a description string is prose: two records
    carrying it can differ in construction and still compare equal as text. A constructor
    name plus its parameters can be compared field by field, which is what makes a fold
    change visible as a rule change rather than as a metric change.
    """
    return {"constructor": constructor, "params": dict(sorted(params.items()))}


def _check_section(name, keys, section):
    """Refuse a section whose key order has drifted from the contract's one definition."""
    if tuple(section) != tuple(keys):
        raise RuntimeError(
            f"{name}: section keys {tuple(section)} and the contract's {tuple(keys)} have "
            f"diverged -- the builder and the verdict would disagree about what a record says"
        )
    return section


def split_section(*, n_folds=None, seed=None, sha256=None, rule=None):
    """The split section. `sha256` is the existing train-index hash; `rule` is `split_rule`."""
    return _check_section(
        _SPLIT,
        SPLIT_KEYS,
        {SPLIT_N_FOLDS: n_folds, SPLIT_SEED: seed, SPLIT_SHA256: sha256, SPLIT_RULE: rule},
    )


def model_section(*, version=None, weights_sha256=None, client_version=None, version_source=None):
    """The model section.

    `version` is the **resolved** label (`v3_default`, never a weights filename), per
    docs/MODEL_VERSIONS.md. `weights_sha256` corroborates it; it never substitutes, because a
    hash cannot be mapped back to a version label without reading that document and guessing.
    `client_version` is the package that served the model -- `tabpfn` for a local run,
    `tabpfn-client` for the API -- recorded so "which stack produced this" is one lookup.

    `version_source` says what kind of claim `version` is. `resolver` means "the label this
    repository resolves to"; it is not evidence that the estimator was constructed with it.
    The pilot declares the version and does not pass it to `TabPFNClassifier`, so the block
    states which claim it is making rather than implying a pin (#285).
    """
    return _check_section(
        _MODEL,
        MODEL_KEYS,
        {
            MODEL_VERSION: version,
            MODEL_VERSION_SOURCE: version_source,
            MODEL_WEIGHTS_SHA256: weights_sha256,
            MODEL_CLIENT_VERSION: client_version,
        },
    )


def code_section(*, git_sha=None, dirty=None, runtime=None, image=None):
    """The code section: what ran, and where."""
    return _check_section(
        _CODE,
        CODE_KEYS,
        {CODE_GIT_SHA: git_sha, CODE_DIRTY: dirty, CODE_RUNTIME: runtime, CODE_IMAGE: image},
    )


def experiment_section(*, id=None, model_version=None, declared=None, resolved=None):  # noqa: A002
    """The experiment a run named, its declaration, and what it executed (ADR 0004).

    All three keys are emitted together. `declared` is the registry's base config;
    `resolved` is what the arms ran. The pair exists so a drifted default is visible in the
    artifact -- #238 refuses a contradiction, so today they agree only because a
    disagreement cannot be run, not because nothing checked.
    """
    return _check_section(
        _EXPERIMENT,
        EXPERIMENT_KEYS,
        {
            EXPERIMENT_ID: id,
            EXPERIMENT_MODEL_VERSION: model_version,
            EXPERIMENT_DECLARED: declared,
            EXPERIMENT_RESOLVED: resolved,
        },
    )


def provenance_block(*, dataset, split=None, model=None, code=None, experiment=None):
    """The one top-level `provenance` key a record carries.

    Every section is emitted with its full key set even when a value is unknown, so a reader
    sees the same vocabulary in every record and a null states the absence. `dataset` is an
    object for a per-dataset record and a non-empty list of those objects for a run-level
    record -- the one structural asymmetry the reader normalises.

    A runner supplies values; the key names live here. That is what stops a second producer
    from spelling the same fact differently and calling it a new shape.
    """

    def section(given, name, keys, empty):
        if given is None:
            return empty()
        return _check_section(name, keys, dict(given))

    block = {
        _DATASET: dataset,
        _SPLIT: section(split, _SPLIT, SPLIT_KEYS, split_section),
        _MODEL: section(model, _MODEL, MODEL_KEYS, model_section),
        _CODE: section(code, _CODE, CODE_KEYS, code_section),
    }
    # Optional, and absent rather than null-filled: a run that named no experiment has no
    # declaration to state (ADR 0004). v3 records never carried it and still read.
    if experiment is not None:
        block[_EXPERIMENT] = section(experiment, _EXPERIMENT, EXPERIMENT_KEYS, experiment_section)
    return block


@dataclass(frozen=True)
class Verdict:
    """What a record can prove about itself. Computed from the record, never stored in it."""

    status: str
    missing: tuple[str, ...] = ()
    schema_version: int | None = None

    def __str__(self):  # a verdict is read in a log or a table, so it reads as one line
        if not self.missing:
            return self.status
        return f"{self.status}: missing {', '.join(self.missing)}"


def _dataset_path(index, key):
    """One dataset entry's key, addressed by index -- the record's own order."""
    return f"{_PROVENANCE}.{_DATASET}[{index}].{key}"


def _section_path(section, key):
    return f"{_PROVENANCE}.{section}.{key}"


def _present(value):
    """A value that identifies something. Empty string and null do not."""
    return value is not None and value != ""


def _declared_schema_version(record, layout, where):
    """The layout the record was written with, refusing one this reader cannot place.

    Absent and explicit `null` are different facts: absent means the record predates the
    field, which is only readable where the layout documents an unversioned form; `null` means
    the writer stamped nothing, which no layout can place. A bool is rejected before the
    membership test, because `True == 1` would otherwise pass as version 1.
    """
    version = record.get("schema_version", _MISSING)
    if version is _MISSING:
        if layout.absent_means is None:
            raise ValueError(
                f"{where}: a {layout.kind} record must declare schema_version -- this layout "
                f"has no unversioned form this reader can place"
            )
        return layout.absent_means
    if isinstance(version, bool) or not isinstance(version, int):
        raise ValueError(
            f"{where}: schema_version {version!r} is not an integer -- a record that cannot "
            f"name its layout is not one this reader understands"
        )
    if version not in layout.known_versions:
        raise ValueError(
            f"{where}: schema_version {version!r} is not one this reader knows for a "
            f"{layout.kind} record ({', '.join(str(v) for v in layout.known_versions)})"
        )
    return version


def _dataset_entries(dataset):
    """Normalise the one documented asymmetry: a per-dataset object, or a run-level list."""
    if isinstance(dataset, Mapping):
        return [dataset]
    if isinstance(dataset, (list, tuple)):
        return [dict(d) if isinstance(d, Mapping) else {} for d in dataset]
    return []


def _legacy_arm_sections(record):
    """A pre-block pilot arm record's top-level keys, read as the block's sections.

    The 8 v2 records in the tree carry `dataset_fingerprint` and `split_fingerprint` at the
    top level. Reading them through the same rule engine is what makes #240's claim true: a
    v2 record names its data and its split, and cannot name its model, so it is `partial` --
    not indistinguishable from a manifest that records only `argv`.

    Nothing is written back and nothing is upgraded: this is a lens over bytes that stay as
    they were produced. The v2 `split_fingerprint` recorded its construction as `policy`
    ("stratified_kfold" / "holdout_then_train_cap"), so that is recorded as a rule with no
    parameters, because that is all the file states.
    """
    fingerprint = record.get("dataset_fingerprint")
    split_fp = record.get("split_fingerprint") or {}
    git = record.get("git") or {}
    policy = split_fp.get("policy")
    return {
        _DATASET: [fingerprint] if isinstance(fingerprint, Mapping) else [],
        _SPLIT: split_section(
            n_folds=split_fp.get("n_folds"),
            seed=split_fp.get("seed"),
            sha256=split_fp.get("train_index_sha256"),
            rule=split_fp.get("rule") or (split_rule(policy) if policy else None),
        ),
        _MODEL: model_section(
            version=record.get("model_version"),
            weights_sha256=(record.get("weights") or {}).get("sha256"),
            client_version=(record.get("versions") or {}).get("tabpfn"),
            version_source="legacy" if record.get("model_version") else None,
        ),
        _CODE: code_section(
            git_sha=record.get("git_sha") or git.get("commit_sha"),
            dirty=git.get("dirty"),
            runtime=record.get("versions") or None,
            image=(record.get("container") or {}).get("image_ref"),
        ),
    }


def _legacy_capture_sections(record):
    """A v1 capture manifest's documented keys, read as the block's sections.

    A capture pins predictions, not the bytes of the CSV: it carries the dataset's *name*,
    file, target and drop, the fold count and seed, the model version and client version, and
    the script's git sha (#240's capture-manifest table). It does not carry a dataset content
    hash or a split fingerprint, so those are the items a verdict must name as missing -- which
    is the difference between a capture and an argv-only run manifest: this record identifies
    its dataset and its split, so it is `partial`, not `unusable`.

    `split` is recorded as a description string (`KFold(5, shuffle=True, random_state=42)`).
    It is deliberately NOT parsed into a rule: turning prose into `{constructor, params}` would
    be a guess, and a guessed rule is worse than an absent one. The fold count and seed still
    identify the split; the rule is missing and a future capture writer records it properly.
    """
    # A null `dataset` means the file names no dataset at all, so there is no entry to
    # describe; a present-but-empty name is still an entry, and is named as the missing key.
    datasets = (
        [
            {
                DATASET_NAME: record.get("dataset"),
                "file": record.get("data_file"),
                "target": record.get("target"),
                "drop": record.get("drop") or [],
                DATASET_SHA256: None,
            }
        ]
        if record.get("dataset") is not None
        else []
    )
    return {
        _DATASET: datasets,
        _SPLIT: split_section(
            n_folds=record.get("n_folds"),
            seed=record.get("seed"),
            sha256=None,
            rule=None,
        ),
        _MODEL: model_section(
            version=record.get("model_version"),
            weights_sha256=None,
            client_version=record.get("tabpfn_client_version"),
            version_source="legacy" if record.get("model_version") else None,
        ),
        _CODE: code_section(
            git_sha=record.get("script_git_sha"),
            dirty=None,
            runtime=None,
            image=None,
        ),
    }


# The two kinds whose pre-block layout can still identify a dataset and a split. Everything
# else must carry the block to say anything; an argv-only manifest identifies neither.
_LEGACY_SECTION_READERS = {
    ARM_RECORD_KIND: _legacy_arm_sections,
    CAPTURE_KIND: _legacy_capture_sections,
}


def read_record(path, *, kind):
    """Load a record of `kind` from a file or a record directory, failing closed on the version.

    A directory is read as `<dir>/meta.json`, which is where the pilot writes its arm record.
    Nothing is written back: a record written before this contract existed gets a verdict,
    not an upgrade, because its bytes are the evidence.
    """
    layout = _layout(kind)
    p = Path(path)
    if p.is_dir():
        p = p / "meta.json"
    record = json.loads(p.read_text(encoding="utf-8"))
    _declared_schema_version(record, layout, p)
    return record


def _layout(kind):
    layout = RECORD_LAYOUTS.get(kind)
    if layout is None:
        raise ValueError(
            f"unknown record kind {kind!r}; known kinds are {', '.join(sorted(RECORD_LAYOUTS))}"
        )
    return layout


def verdict(record, *, kind):
    """The verdict a record of `kind` earns, and the keys that are missing.

    * `comparable` -- every dataset carries a content hash, and the split hash, the model
      version and the git sha are all present. These are the items that make "same data,
      same split, same model, same code" checkable rather than asserted.
    * `partial` -- the record identifies its dataset and its split (a name, a seed, and a
      construction) but is missing at least one of those four.
    * `unusable` -- it cannot identify the dataset or the split at all. That is a verdict,
      not an exception: an old record is a historical fact, not a failure.

    `kind` is required because a record does not carry one: the caller knows whether it is
    reading an arm record or a capture manifest, and guessing from shape is how a reader ends
    up confidently misreading the wrong layout. A record of a kind with a documented
    pre-block layout -- a pilot arm record or a capture manifest -- is read through those keys
    when the block is absent (`_LEGACY_SECTION_READERS`); the invocation manifests must carry
    the block to identify a split at all.

    Accepts the record as a mapping or as a path to one. Missing keys are named by index --
    `provenance.dataset[1].sha256` -- so one form addresses every record, per-dataset or
    run-level.
    """
    if isinstance(record, (str, Path)):
        record = read_record(record, kind=kind)
    layout = _layout(kind)
    schema_version = _declared_schema_version(record, layout, "record")

    block = record.get(_PROVENANCE)
    legacy_reader = _LEGACY_SECTION_READERS.get(kind)
    if isinstance(block, Mapping):
        datasets = _dataset_entries(block.get(_DATASET))
        split = block.get(_SPLIT) or {}
        model = block.get(_MODEL) or {}
        code = block.get(_CODE) or {}
    elif legacy_reader is not None:
        legacy = legacy_reader(record)
        datasets = _dataset_entries(legacy[_DATASET])
        split, model, code = legacy[_SPLIT], legacy[_MODEL], legacy[_CODE]
    else:
        return Verdict(UNUSABLE, (_PROVENANCE,), schema_version)

    # First: can it identify the dataset and the split at all? Without that there is nothing
    # to be partial about, and "missing a content hash" would overstate what the record says.
    missing: list[str] = []
    if not datasets:
        missing.append(f"{_PROVENANCE}.{_DATASET}")
    for index, entry in enumerate(datasets):
        if not _present(entry.get(DATASET_NAME)):
            missing.append(_dataset_path(index, DATASET_NAME))
    # A split is identified by its seed and its construction. `n_folds` counts folds where
    # there are folds; the pilot's holdout path has one train/test partition and records it as
    # a rule (`train_test_split` and its sizes), so a fold count alone cannot be the test.
    if not _present(split.get(SPLIT_SEED)):
        missing.append(_section_path(_SPLIT, SPLIT_SEED))
    elif not _present(split.get(SPLIT_N_FOLDS)) and not _present(split.get(SPLIT_RULE)):
        missing.append(_section_path(_SPLIT, SPLIT_N_FOLDS))
    if missing:
        return Verdict(UNUSABLE, tuple(missing), schema_version)

    for index, entry in enumerate(datasets):
        if not _present(entry.get(DATASET_SHA256)):
            missing.append(_dataset_path(index, DATASET_SHA256))
    if not _present(split.get(SPLIT_SHA256)):
        missing.append(_section_path(_SPLIT, SPLIT_SHA256))
    if not _present(model.get(MODEL_VERSION)):
        missing.append(_section_path(_MODEL, MODEL_VERSION))
    if not _present(code.get(CODE_GIT_SHA)):
        missing.append(_section_path(_CODE, CODE_GIT_SHA))

    return Verdict(PARTIAL if missing else COMPARABLE, tuple(missing), schema_version)
