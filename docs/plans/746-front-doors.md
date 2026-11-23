# Plan — the fine-tuning front doors state what is current (#746)

**Status:** current — implemented, 2026-11-23.

Phase 2 is closed, but a reader following the front doors is misled: `docs/README.md` lists a
superseded status brief as current, the campaign index has blank and truncated statuses for the
ladder result and design, and the root README never points at the current answer.

## What

- `docs/experiments/pilot2-phase2/README.md` — a Phase 2 closed banner, a numbered reading order
  (outcome → findings → regressor line → matrix → rules → provenance), and a full status cell for
  every document, matched to that document's own status line.
- `docs/README.md` — the current list rewritten around the Phase 2 outcome, the fair test, the
  ladder and the paper matrix; the status brief, experiment reference and pilot design moved to
  reference; the Start-here and replicator rows point at the matrix.
- `README.md` — a "Current results (2026-11)" block, and the round-1 paper distinguished from the
  current programme.
- Status-line corrections: the status brief and experiment reference become reference; the pilot
  design becomes a design record; the SAP is signed, not a draft; `active` becomes current or
  reference on five analyses/results, each keeping its existing dated marker.
- `REPORT_REGISTRY.md` and `CHANGELOG.md` follow.

No document is deleted or rewritten beyond its status line; every dated marker is retained.

## Verification

- `check.sh doclinks`, `docstatus`, `citation`, `evidence`, `ruff`.
- Full `pytest` in CI.

## Out of scope

- Evidence pruning and the evidence budget (#584, #694).
- Worktree and branch cleanup.
- Re-tiering documents whose status is not contradicted by another page.
