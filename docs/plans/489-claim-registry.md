# Plan — the findings registry becomes a pointer, and stops being able to drift

**Status:** Current — delivered 2026-11-08.
**Origin:** #489 on map #484, resolving the architecture decision recorded on #486. No new capability.
**Design:** `docs/current/FINETUNING_FINDINGS.md` is a pointer; the owning document is the store.

## Scope

The registry went stale because it restated detail it did not own. On 2026-10-31 it was correct; by 8
November two rows contradicted their owners, and nothing failed. The status brief carries the same defect
internally: its summary table says the anchor rests on one seed, and the replication further down the same
page says otherwise.

Three changes, and the third is the one that matters:

1. **The registry** becomes `Claim | Status | Owner`, with a qualitative claim and no number in it. The row
   id stays, folded into the claim cell, because the decision log cites these rows by name.
2. **The brief** keeps its history and gains a dated marker saying which sentence in it is current.
3. **`check_doc_status.py`** gains a second assertion: each registry row is three columns, and after
   stripping row references and ISO dates, no digit remains in the claim. The check and the stripped rows
   land together — check first turns CI red on the rows it exists to catch.

## Decisions worth arguing with

**A check rather than a promise.** The registry's own head already said it was "deliberately not a
restatement". It drifted anyway, because the only enforcement was review attention. The assertion is
mechanical, cheap, and lives in an existing job rather than adding a ninth.

**The digit rule is blunt on purpose.** It forbids `coil2000` in a claim cell, so a dataset with a digit in
its name must be described ("the anchor dataset") rather than named. That is a real cost and it is the right
trade: the alternative is a rule with exceptions, and a rule with exceptions is a rule that gets argued with
in review.

**A missing registry fails.** A check that passes because its subject moved is worse than no check — the
same failure mode `check_doc_status.py` already suffered when `docs/reports/` was dissolved and it kept
pointing at the dead path for six weeks.

**L3 is marked superseded, not deleted.** It was true on the day it was written, and the programme's history
of a design that could not see the effect is worth keeping. F2 is the same: still true of the budget it
measured.

**Owners are single.** Where the old rows named two documents (F3, F7, F8), the row now names the one that
carries the number. A claim with two owners is two claims.

## Shape

```
docs/current/FINETUNING_FINDINGS.md    # Claim | Status | Owner, no digits
docs/current/FINETUNING_STATUS_BRIEF.md # dated marker above its narrative
scripts/check_doc_status.py             # + registry_problems(); runs on the default check only
tests/test_check_doc_status.py          # + 5 tests, including one against the shipped registry
CHANGELOG.md                            # one entry
```

## Verification

```sh
python3 scripts/check_doc_status.py          # 41/41 reports, and "every claim names its owner"
./scripts/check.sh                           # all eight green
```

Run on 2026-11-08: the status check printed both assertions and all eight checks passed.

The before/after is worth keeping in the PR: the registry as it stands on `main` fails the new check on all
fourteen of its table rows — thirteen for shape, and any three-column rewrite of F1 for the number it
restates (`+0.0022 / +0.0026 / +0.0034`).

## What this does not do

It does not write the closing report, move any document between tiers, or touch the front door — those are
the tickets this one unblocks. It does not change the decision log, which cites rows by id and keeps
working. It does not delete a claim: statuses change, text stays.
