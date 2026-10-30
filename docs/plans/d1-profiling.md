# Plan — finish D1 as the diagnostics template (#302)

**Status:** Current — implementing 2026-10-30.
**Origin:** ticket #302 under the campaign spec #300.
**Design:** `docs/current/FINETUNING_DIAGNOSTICS_DESIGN.md` §D1 · **Record shape:** ADR 0003.

## Scope

D1 exists and emits through the shared writer, but it measures about half of the design's table and
profiles **one CSV per invocation**. The ticket needs one record per anchor dataset, and every
property the design names.

Two changes, both inside the existing record contract:

1. **Anchors, not a CSV.** D1 learns to profile the four anchor datasets by name, from the pilot's own
   dataset registry, so the dataset list has one source of truth and a run cannot silently profile a
   file the anchor will never use. One record per dataset per run; a single `--csv` remains for ad-hoc
   profiling.
2. **The rest of the table.** Per-column missingness (with the pattern marked as untested rather than
   guessed), target quantiles for non-binary targets, the numeric-to-categorical ratio, and a bounded
   VIF beside the existing maximum pairwise correlation. The design's "prior-mismatch proxies" row is
   recorded as the structured facts it actually consists of — type mix, target complexity, missingness —
   not as a single invented score.

## What is deliberately not done

- **No MCAR/MAR/MNAR test.** The design asks for the pattern; deciding it needs a statistical test whose
  result depends on assumptions the profile cannot check. The record states per-column rates and marks
  the pattern `untested`, so the gap is visible instead of papered over.
- **No histogram.** Quantiles carry the shape a reader needs and stay comparable between datasets; a
  binned histogram would be a second representation of the same numbers.
- **No change to the row cap or the split** — the cap decision is recorded in the signed plan.

## Seam

One seam, unchanged from #211 and agreed in the spec: **the record on disk**, read back by the test.
No test reaches into `profile_frame` for a value it could read from the record; the wrongness check the
ticket names — positive rate, row count and missingness recomputed from the raw CSV — is exactly a
record-versus-file assertion.

## Verification

- `./scripts/check.sh` green.
- A record per anchor dataset, each hash matching its file, values recomputable from that file.
- Two runs with identical inputs produce identical measurements (no wall-clock or ordering dependence).
- `git diff` over `outputs/` and `results/` empty.
