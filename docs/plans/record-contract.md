# Plan — the pilot writes a provenance block, and one reader states the verdict

**Issue:** #241 (slice of #240, on top of #211's `src/provenance.py`).
**Status:** Current.

## What and why

No pilot arm record has ever said which model version produced it. Model identity there is a
weights hash plus a filename list, so a comparison across model eras needs an archaeology pass
through `docs/MODEL_VERSIONS.md` and a guess. Meanwhile `GLOSSARY.md` defines provenance as
"dataset, seed, fold construction, model version, and git sha", and every record in the tree is
missing at least one of the five.

This ticket does three things and nothing else:

1. **Writes** a `provenance` block into the pilot arm record and bumps that record to schema 3.
2. **Reads** any record into a stated verdict — `comparable` / `partial` / `unusable` — naming
   the missing keys instead of leaving a reader to infer them.
3. **Records** the vocabulary and the version-not-hash decision in an ADR, adds *record* and
   *verdict* to `GLOSSARY.md`, and leaves every committed record byte-for-byte alone.

## The block

One writer in `src/provenance.py`, so a runner supplies values and never restates key names:

| Section | Keys | Source today |
| --- | --- | --- |
| `dataset` | the dataset-fingerprint object: `name`, `file`, `target`, `drop`, `sha256`, `n_rows`, `n_cols`, source pinning | `dataset_fingerprint`, now called with a frame |
| `split` | `n_folds`, `seed`, `sha256` (train-index hash), `rule` (constructor + parameters, as a mapping) | `make_split` |
| `model` | `version` (resolved label), `weights_sha256`, `client_version` | `src/model_version.resolve_model_path()` + `_weights_provenance` |
| `code` | `git_sha`, `dirty`, `runtime`, `image` | `_git_info`, `_runtime_versions`, `_container_provenance` |

`dataset_fingerprint` stops taking a dataset name and a data directory: it takes the frame, the
target column and the drop columns, plus the file whose bytes are hashed. The pilot keeps a
four-line adapter that binds its own registry (`DATASETS`, `DATA_DIR`, `DATA_REF`) to the shared
helper — that binding is the runner's declaration, not a fact `src/` can know.

The existing top-level `dataset_fingerprint` and `split_fingerprint` keys stay, pointing at the
same objects the block holds, so a reader of the old layout keeps working through the transition
and cannot see two different fingerprints in one record.

## The verdict

Computed from the record, never stored in it:

* **`comparable`** — every dataset carries `sha256`, and `split.sha256`, `model.version` and
  `code.git_sha` are present.
* **`partial`** — the record names its dataset and its split, and is missing at least one of
  those four; `missing` lists them as dotted keys (`provenance.model.version`).
* **`unusable`** — it cannot identify the dataset or the split at all, or carries no
  provenance block. Not an exception: an old record gets a verdict, not an upgrade.

`schema_version` is dispatched on and **fails closed**: absent (the pre-versioned records) reads
as the legacy layout, a version this module does not know raises rather than guessing.

## Schema versions

`ARM_RECORD_SCHEMA_VERSION = 3` for the arm record. The run manifest and the failure record keep
`RUN_SCHEMA_VERSION = 2`: #241 does not give them a block, and bumping them would claim a shape
they do not have. That renumbering is the parent spec's, not this slice's.

## Evidence untouched

No committed record is rewritten. The legacy records are read through the verdict in a test
that classifies every one of them with no exception, and the PR states the empty
`git diff origin/main -- outputs/ results/` as evidence.

## Verification

* `tests/test_record_contract.py` — the record-boundary seam: a record written through the
  pilot's write path (`save_results`) and read back from disk; the verdict rules table-driven;
  an unknown schema version raising; a committed v2 record yielding `partial` naming
  `provenance.model.version`; `analyse_pilot.discover` reading a schema-3 record.
* The existing pilot suites pass unchanged: metrics, predictions and the refusal-to-overwrite
  rule are not touched.
* `./scripts/check.sh` (ruff, pytest, shellcheck) green; `git diff origin/main -- outputs/
  results/` empty.

## Out of scope

The frontier runner's records (#243), an audit table of the committed tree, and any migration of
existing analysis scripts onto the reader (#235).
