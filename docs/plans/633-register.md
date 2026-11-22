# Plan — register the conclusion, and gate it (#633)

The conclusion is written and merged (#632). This ticket makes it part of the governed surface: a
reader must be able to find it from the registry, know it owns the headline table, and see the change
in the changelog.

## What

- `docs/REPORT_REGISTRY.md` — one row per document, with audience, status, evidence files and the
  model version each carries. The conclusion spans v3 and v3.5, so its row names both per table
  rather than picking one.
- `docs/DOCUMENT_AUTHORITY.md` → "Who owns what" — the conclusion owns the headline table, and the
  row states what it does **not** own: the per-dataset numbers it restates, the adoption rule, and any
  verdict it did not generate.
- `CHANGELOG.md` — one entry naming the corrections and the review.
- Campaign README already lists both documents (#632); `EXPERIMENTS.md` already counts them.

## Verification

All eight, from a worktree with the main clone's venv on `PATH`:

- ruff, shellcheck, evidence, doclinks (113/0), docstatus (97/97), citation (69 cited, 15 exempt,
  54 checked), verdict (0.0104 against 0.0100) — run here.
- pytest — CI.

The `analysis-review` step was run before the merge of #632, in a fresh context, and its twenty
findings were folded into that PR; this ticket adds no prose that needs reviewing.

## Out of scope

- Any change to the evidence or to the conclusion's claims.
- The two blocked tickets (#662, #682).
