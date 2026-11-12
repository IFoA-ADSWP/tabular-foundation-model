# Plan — the front door becomes one route

**Status:** Current — delivered 2026-11-08.
**Origin:** #488 on map #484, following the architecture decision on #486 and the evidence map on #490.
**Design:** the door answers the actuary's question before it explains the taxonomy.

## Scope

The top of `docs/README.md` changes; nothing below the role table does. Three sentences, then a route, then
the index demoted.

Two defects are fixed in the same change, because they sit in the lines being rewritten:

- The door asserted that `check_doc_status.py` "currently **fails**" and offered its output as a backfill
  list. It passes, and the script has since gained a second assertion. The sentence now says what the check
  does and how to run it, and deliberately carries no count.
- The old "Start here" section claimed that at the larger budget "every fine-tuning rung beat raw with
  intervals excluding zero". Only the anchor did; the breadth cells bounded the effect under the bar. That
  overclaim is replaced by the three sentences, which state the gain, the equivalences and the stop.

## Decisions worth arguing with

**Three sentences, not a paragraph.** The third names the report and the evidence map, so a reader who reads
only the door still has both. The second carries no measurement — a door that quotes a number goes stale
before the page it points at does.

**The route replaces the question table rather than joining it.** The old table was eleven questions, one of
which pointed at `outputs/gpu-pilot/` as "the raw evidence" — true, and useless to a reader who does not know
what a capture is. Three rows now: outcome, evidence, method. The role table and the tier list survive below
and absorb the detail.

**"Eras" is renamed "Programme history".** The document already used *era* for a different axis — code eras,
fine-tuning versus scripts versus notebook, defined in the *Era legend* below. One word, two meanings, in one
file is the kind of thing that makes a reader doubt both. The programme's stages keep their own name, and the
collision is noted where it could recur.

**The new report is added to the current-tier list; the evidence map is not.** The map is not a report and
does not claim a tier, so it joins `MODEL_VERSIONS.md` and `REPORT_REGISTRY.md` in the "not tiered" paragraph
instead.

## Shape

```
docs/README.md   # top rewritten; role table and everything below untouched
CHANGELOG.md     # one entry
```

## Verification

```sh
./scripts/check.sh
```

Run on 2026-11-08: green. `doclinks` resolves both new links; `docstatus` still sees the same reports, since
no tiered document moved.

## What this does not do

It does not move, delete or retier any report. It does not touch the role table, the era legend or the legacy
tables below. It does not add the figure the report does not have.
