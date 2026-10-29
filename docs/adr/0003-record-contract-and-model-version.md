# A record carries one provenance block, and model identity is a version, not a hash

> **Status:** accepted, 2026-10-29

Every run record in this repository describes itself in its own vocabulary, and no shape
carries all five items `GLOSSARY.md` calls provenance. The pilot's arm records name their
dataset and split, and identify their model by a weights hash and a filename list — no version,
in any of them. Two pilot numbers from different model eras are therefore indistinguishable
without reading `docs/MODEL_VERSIONS.md` and guessing which label produced a hash.

We therefore give every record one top-level `provenance` block with four sections (dataset,
split, model, code), written through one set of builders in `src/provenance.py`, and read by
one `verdict` function that states what the record can prove. A record cannot claim to be
comparable while missing the field that makes a comparison meaningful, because the claim is
computed from the record rather than written into it.

## The vocabulary

| Section | Keys | What makes it checkable |
| --- | --- | --- |
| `dataset` | `name`, `file`, `target`, `drop`, `sha256`, `n_rows`, `n_cols`, plus `source_url` / `source_repo` / `source_ref` / `source_ref_is_pinned` | the sha256 is over the bytes on disk, so a changed CSV is visible; `drop` is the leak-drop **as applied by the runner** |
| `split` | `n_folds`, `seed`, `sha256`, `rule` | `sha256` is the train-index hash; `rule` is `{constructor, params}`, so a fold change is a rule change |
| `model` | `version`, `version_source`, `weights_sha256`, `client_version` | `version` is the resolved label (`v3_default`), never a filename; `version_source` says what kind of claim that is (`resolver` for today's pilot, `legacy` for a pre-block record carrying its own `model_version`) |
| `code` | `git_sha`, `dirty`, `runtime`, `image` | `dirty` says whether `git_sha` describes the code that ran |

**The one documented asymmetry.** A per-dataset record (pilot arm run, prediction capture) has
`provenance.dataset` as an object. A run-level record (pilot run manifest, frontier run
manifest) covers N datasets and has it as a non-empty list of those objects. The reader
normalises to a list; every other rule is identical. A second difference would be a fourth
record shape, which is what this decision exists to prevent.

**The split's `rule` is a rule, not prose.** `KFold(5, shuffle=True, random_state=42)` in a
description string is text two different constructions can share. A constructor name plus its
parameters can be compared field by field. A holdout split has no fold count, so it records
`train_test_split` and its sizes instead of a fold count of one it does not have.

## Verdicts

Computed from the record, never stored in it:

- **`comparable`** — every dataset carries `sha256`, and `split.sha256`, `model.version` and
  `code.git_sha` are present and non-null.
- **`partial`** — the record identifies its dataset and its split (a name, a seed, and either a
  fold count or a construction rule) but is missing at least one of those four. The verdict
  carries the missing keys by name, addressed by index —
  `provenance.dataset[1].sha256`, `provenance.model.version` — so one form addresses every
  record, per-dataset or run-level.
- **`unusable`** — it cannot identify the dataset or the split at all.

**The pre-block layout.** A pilot arm record written before this decision carries
`dataset_fingerprint` and `split_fingerprint` at the top level, not under `provenance`. It is
read through those documented keys rather than declared unreadable, because they *do* identify
its data and its split: the eight v2 records are therefore `partial`, missing their model
version (and their git sha), which is exactly what #240 says they are. The eleven records that
predate fingerprints identify neither, and stay `unusable`. Nothing is written back or upgraded;
the lens is over bytes that stay as they were produced. Other record kinds have no documented
pre-block layout that identifies a split, so for them an absent block is `unusable` — #243 owns
the frontier's own shape.

**Per-kind version dispatch.** `schema_version` is checked against the layout of the kind the
caller says it is reading. A capture manifest declaring `3` is refused even though an arm
record has a `3`, because the two do not share a version space. Absent, explicit `null` and a
bool are three different facts: absent is the documented unversioned form of a kind that has
one, `null` is a writer that stamped nothing, and `True == 1` is a type error rather than
version 1. Only some kinds have a documented unversioned form — the arm records that predate
the field and the frontier run manifests #240 describes as unversioned — so the others raise.

## Why a version, not only a weights hash

`schema_version` 2 pilot records carry `weights.sha256` and no `model.version`. A hash
corroborates a version — it proves the bytes — but it cannot be *inverted* into a label. To
recover the version you read `docs/MODEL_VERSIONS.md` and match the hash by hand, which is the
archaeology pass this decision removes, and which silently breaks the moment a checkpoint is
re-downloaded or a second hash appears in the timeline.

So the two fields do different jobs and both stay:

- `version` says **which model** this number is about, in the vocabulary a report uses.
- `weights_sha256` says **which bytes** were on disk for that version, so a re-download that
  silently swapped checkpoints is visible.

A record with the hash and no version is `partial`, not `comparable`. That is a deliberate
departure from the earlier framing that "schema v2 is the standard": under `GLOSSARY.md`'s
definition of provenance, a v2 pilot record cannot say which model produced it.

## Why the builder and the verdict live together

`src/provenance.py` now holds three reasons to change: the pilot's fingerprints and the
matched-context assertion (#211), the diagnostics' record writer (#211), and the record shape
with its verdict (#241). A reviewer is right to ask whether that is one module or three.

The builder and the verdict belong together because they are the two halves of one contract,
and the failure this decision prevents lives in the gap between them. A key the writer emits and
the reader does not look for is a record that silently reads as complete; a key the reader
demands and the writer never emits is a verdict nobody can ever earn. Keeping them in one file
means a rename is one edit and the key tuples (`SPLIT_KEYS`, `MODEL_KEYS`, `CODE_KEYS`) are the
single definition both sides use — the builders assemble their sections from those tuples and
`verdict` builds its missing-key paths from the same names, with a runtime check that refuses a
section whose key order has drifted. Split them across modules and that invariant becomes a
convention instead of a check.

The diagnostic writer stays here for the same reason it was put here: it is a second producer
of the same facts. What is *not* here is the pilot's record file itself — `run_pilot.save_results`
still owns that, because the arm record carries far more than provenance. This module owns the
block, and the block is what has to agree across producers.

## Consequences

- The pilot's arm record moves to `schema_version` 3. The invocation manifest and
  `meta.FAILED.json` stay at 2 — they have no block, and inheriting the arm record's version
  would claim a shape they do not have. Renumbering them is the parent spec's work.
- `dataset_fingerprint` takes the frame, the target and the drop columns rather than a dataset
  name, so a second runner can call it without inheriting the pilot's registry. Its
  missing-table return (`{"name", "path", "exists": False}`) is unchanged from #211.
- **What a reader of the old layout can and cannot do.** The top-level `dataset_fingerprint` and
  `split_fingerprint` keys stay, holding the same objects the block holds, so a script that read
  either object keeps working. Inside `dataset_fingerprint`, `target_col` is renamed to `target`
  and `drop` is added, so a script that keyed on `target_col` breaks — the two in-tree readers
  that did (`tests/test_provenance.py`, `tests/test_pilot2_prerequisites.py`) are updated in the
  same change, and this is a rename, not a compatibility promise. `analyse_pilot.py` reads only
  `status` and `effective_config`, so it is unaffected.
- **The model version is a declaration, not an observation.** `run_pilot` constructs
  `TabPFNClassifier` without a `model_path` and never calls `resolve_model_path()`, so the value
  in `provenance.model.version` is the label this repository resolves to, not proof that the
  estimator was asked for it. The block says so with `version_source: resolver`. Pinning the
  model changes what runs on a paid box, which is not this change's business: tracked as #285.
- A record written by an older runner is not rewritten. Its bytes are the evidence; the
  verdict is the statement about them.
