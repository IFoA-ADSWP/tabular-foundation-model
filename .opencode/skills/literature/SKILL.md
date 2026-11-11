---
name: literature
description: 'Citation hygiene for literature docs — no identifier, no citation: every cited work carries a verified DOI or arXiv id and a verified/unverified/corrected status, maintained in references.bib. Use when writing or auditing citations, adding references, reviewing docs/current/FINETUNING_LITERATURE.md or archive/papers/, or maintaining references.bib.'
---

# Literature

One rule, three statuses. The statuses are defined once, in
`docs/current/FINETUNING_LITERATURE.md` — `verified` (read in the primary source),
`unverified` (second-hand, not yet seen at source), `corrected` (the source says
something else). Use those meanings; do not invent parallel ones.

## The rule

**No identifier, no citation.** A work enters the reference list only with a persistent
identifier — DOI or arXiv id — resolved from the primary source (the publisher's page,
the DOI resolver, the arXiv abstract page) and matched to the work claimed (title,
authors). No identifier found → the claim is written as `unverified`, or held back.

## Write mode — new citations

1. List the claims that need sources.
2. For each: resolve and verify the identifier at source.
3. Assign the status. `corrected` entries record what changed and where.
4. Add the entry to `references.bib` at the repo root, keyed by identifier — dedup on
   the identifier, never on the title.
5. Cite from the doc with the status visible.

Done when: every citation in the doc carries a resolved identifier or an explicit
`unverified` mark.

## Audit mode — existing docs

Report-only by default: list the violations — claims with no identifier, entries with
no status, identifiers that do not resolve to the claimed work. Edits to an existing doc
only on explicit ask; a correction then lands with its `corrected` note saying what
changed.
