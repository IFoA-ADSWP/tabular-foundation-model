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
| `dataset` | `name`, `file`, `target`, `drop`, `sha256`, `n_rows`, `n_cols`, plus `source_url` / `source_repo` / `source_ref` / `source_ref_is_pinned` | the sha256 is over the bytes on disk, so a changed CSV is visible |
| `split` | `n_folds`, `seed`, `sha256`, `rule` | `sha256` is the train-index hash; `rule` is `{constructor, params}`, so a fold change is a rule change |
| `model` | `version`, `weights_sha256`, `client_version` | `version` is the resolved label (`v3_default`), never a filename |
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
  carries the missing keys by name, e.g. `provenance.model.version`.
- **`unusable`** — it cannot identify the dataset or the split at all, or carries no
  `provenance` block. That includes every record written before this decision: they are read
  for a verdict, never upgraded.

An unknown or higher `schema_version` raises rather than guessing what the record meant. A
record that predates the block still gets a verdict (`unusable`, naming `provenance`); a record
that declares a layout this reader has not been taught is a bug in the reader's deployment, not
a fact about the run.

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

## Consequences

- The pilot's arm record moves to `schema_version` 3, and the run manifest and the failure
  record keep `2` — they have no block, and inheriting the arm record's version would claim a
  shape they do not have. Renumbering them is the parent spec's work, not this one's.
- The top-level `dataset_fingerprint` and `split_fingerprint` keys stay, holding the same
  objects the block holds: old readers keep working, and one record cannot show two
  fingerprints that disagree.
- `dataset_fingerprint` takes the frame, the target and the drop columns rather than a dataset
  name, so a second runner can call it without inheriting the pilot's registry.
- A record written by an older runner is not rewritten. Its bytes are the evidence; the
  verdict is the statement about them.
