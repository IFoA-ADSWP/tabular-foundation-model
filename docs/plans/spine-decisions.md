# Plan — record the launch id and the spend gate (#245)

**Status:** Current — agreed 2026-10-29, implementing.
**Origin:** issue #245 (the paid-run path's spine ticket), closed with twelve decisions; this
change is the durable record of them, requested by the map's review as "ADR + glossary".
**Glossary:** `GLOSSARY.md` · **ADR:** `docs/adr/0002-launch-identity-and-the-spend-gate.md`

## Scope

Documentation only. Three artifacts, no code:

1. `docs/adr/0002-launch-identity-and-the-spend-gate.md` — the three contracts settled on
   #245 (identity, spend gate, provider seam), the alternatives rejected, and the
   consequences an implementer inherits.
2. `GLOSSARY.md` — a `## Paid-run path` section adding *launch*, *launch id*, *arrival* and
   *spend gate*. *Run* stays exactly as it is.
3. `CHANGELOG.md` — an `[Unreleased]` entry, since the vocabulary change is user-facing for
   anyone reading a record.

## Why the ADR is long where ADR 0001 was short

The review of the first draft found seven of the twelve decisions absent: who mints, the id's
shape, the `local-` prefix, the record rename, the four gate checks, the refusal contract and
the closed provider operation set. An implementer reading only that draft could not have built
what #245 decided. Each of those is now stated, and the two things the research left open are
marked as open rather than asserted.

## Two reconciliations the draft got wrong

- **Six refusals, four checks.** The launcher's six existing refusals are not all pre-spend
  facts: an unavailable ssh key, an oversized onstart payload and a create that returns no id
  happen at or after create. The gate checks only what can be proven *before* an instance
  exists; the rest stay runtime failures, and the ADR says so instead of counting them into
  the gate.
- **"Gate" now names two things.** The spend gate is distinguished in vocabulary, and the
  numeral is not reused — the ADR no longer says the other gate "runs four checks" in the same
  breath as the spend gate's four, which recreated the collision it was resolving.

## Verification

No test changes. The checks that apply: `python scripts/check_doc_links.py` must not add a
broken reference (the pre-existing 49 stand), `python scripts/check_doc_status.py` unchanged,
and `pytest tests/test_check_doc_links.py tests/test_check_doc_status.py -q` green.
