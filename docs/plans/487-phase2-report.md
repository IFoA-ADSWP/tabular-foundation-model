# Plan — the Phase 2 closing report

**Status:** Current — delivered 2026-11-08.
**Origin:** #487 on map #484; written against the outline resolved on #485 and the pointer architecture on
#486. No new capability, no new evidence.
**Design:** the report is the canonical statement of Phase 2's outcome; the owning analyses keep the detail.

## Scope

One new current-tier document, written so an adoption-minded actuary can finish it in one sitting and then
state the answer and its three caveats. Six sections, in the order the outline fixed: the answer, should you
care, dataset by dataset, three ways to misread this, what would change our mind, how to check us.

## Decisions worth arguing with

**Every number names its owner inline, except the four in the headline table.** The headline cells are the
report's own; everything else links. That is the same rule the registry now follows, applied to prose.

**`coil2000` gets a paragraph instead of a result.** The temptation is to write a dash and move on. A stop
that is not explained reads as an omission, and the reason it stopped is a property of the dataset, which is
more durable than a budget argument.

**The report does not recommend adoption.** Resolved on #485. It states the outcome, its size against the
model-choice margin, and what would change the picture. The decision belongs to the reader and to the
decision record.

**Short rather than 2,500 words.** The outline targeted about 2,500; the draft lands at ~1,450. The sections
turned out denser than the outline assumed — the answer table carries most of the weight that three
paragraphs would have carried — and padding to hit a target is the failure mode this whole effort is
against. The cold-read ticket (#492) is the test of whether it is too thin, and it is a better test than a
word count.

## Shape

```
docs/current/FINETUNING_PHASE2_OUTCOME.md   # the report
docs/REPORT_REGISTRY.md                     # one row, as analysis-review requires
CHANGELOG.md                                # one entry
```

## Verification

```sh
./scripts/check.sh        # all eight green
```

Run on 2026-11-08: green.

`analysis-review` ran before this was called done. Its hard findings, and the fixes applied:

1. **A claim with no evidence file** — the +0.068 and the baseline ROC AUCs were stated without an inline
   owner. Fixed: both now link `FINE_TUNING_PILOT_RESULTS.md`, and the cost anchors link
   `FINETUNING_COST_AND_CONTROLS.md`.
2. **Registry row missing.** Fixed: one row added with a `v3_default` version pin.
3. **Version pin** — the baseline comparison is from the pilot's first era, and a reader could reasonably
   suspect a v2-era number. Fixed by stating that its version stamp records `v3_default` and tabpfn 8.5.0,
   and by extending the pin sentence to cover it rather than only the measured cells.

Soft findings accepted rather than fixed: the `eudirectlapse` cell is a `B_ft30`-only statement (recorded in
the text), and its Brier sits at the guard, so the report explicitly declines a calibration claim.

## What this does not do

It does not move the registry, the brief or the front door — those are separate tickets. It does not link an
evidence-map page that does not exist yet; section 6 names the trees and links the owners that do. It does
not add a figure.
