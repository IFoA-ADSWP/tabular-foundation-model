# Plan — a cited run must have a capture (#364)

**Status:** Current — implementing 2026-11-02.
**Origin:** #364, under the capture-and-rescore contract (#360). Replaces the narrower scope of
#351 ("did the arrays arrive"), which asked about payment rather than citation.

## The rule being enforced

A run is cited when its bare id (`YYYYMMDDTHHMMSSZ`) appears in a file under `docs/`. Every cited
run must have `results/<id>/capture.json` whose entries cover every arm × seed present in the run,
with non-null hashes. Conversation — issue text, commit messages — is not scanned.

## Forward-only, made explicit

`docs/` already cites 15 pre-rule runs (the R1 pilot of 2026-09-12/13) whose arrays were never
captured. They are exempt through `docs/analyses/legacy_citations.txt`, which is append-only and
**refuses any id at or after the rule date** — grandfathering a new citation is not possible, so the
exemption cannot quietly grow.

## Two defects found while wiring it

- **A launch id is not a run id.** The lease label is `<run id>-<hex>`, so a naive `\b…Z\b` regex
  matched the prefix of `20261031T021925Z-c24870` and demanded a capture for a launch that never
  was a run. The pattern now rejects a trailing `-` or word character.
- **The record glob missed the dataset level.** Records live at
  `results/<id>/<dataset>/<arm>/seed<seed>_foldNone/meta.json`; the first glob stopped one level
  short and reported every run as having no records.

## Wiring

`./scripts/check.sh citation` joins the gate, and CI gets a `citation` job. The check exits 1 with
one line per problem and 0 otherwise; it prints how many ids were cited, exempt and checked, so a
green run is evidence the scan happened rather than evidence it found nothing.

## Verification

Eight tests over synthetic repository trees: complete capture passes; no capture fails; missing
arm fails; null hashes fail; a legacy id is exempt; a post-rule id cannot be exempted; a launch id
cites nothing; a root-level README mention is not scanned. The committed anchor is the positive
fixture the check must keep passing.
