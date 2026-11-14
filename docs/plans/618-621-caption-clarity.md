# Plan — the cold-read caption fixes

**Status:** Current — implemented with this change, 2026-11-14.
**Origin:** #618–#621, from the effectiveness evaluation of the five figures and their reports. The
evaluation is recorded in the conversation that produced the tickets; this is the fix.
**Design:** prose only. No figure is re-rendered, no number changes, no new evidence.

## Scope

| Ticket | Change |
| --- | --- |
| #618 | the Phase 2 and fair-test captions state which direction is good; the fair-test result names `M` (Poisson deviance, weighted RMSE) |
| #619 | `regime_characterization.md` §1 bridges "on the frontier" and "best metric"; the matrix caption opens on its finding |
| #620 | the D2 caption names the two readings it draws, the bar order, and why the third is prose-only |
| #621 | both READMEs route a reader to `docs/figures/`; the root tree stops calling the legacy `outputs/current/` tree "latest" |

## Decisions worth arguing with

**The sign convention goes in the caption, not the section.** A reader can meet the figure without the
table above it; a caption that does not say which direction wins is a caption that can be read
backwards.

**The frontier/best bridge is written once, in §1.** Both numbers are true and both appear in the
document; leaving the reader to infer the rule is the defect, not either number.

**The third D2 reading is named as absent rather than drawn.** Two candidates do not need a panel, but
an unmentioned absence reads as an oversight.

**The root README's stale line is corrected, not deleted.** `outputs/current/` exists and is tracked;
it holds v2-era figures and tables, so the tree keeps it and relabels it.

## Verification

```sh
PATH="$PWD/.venv/bin:$PATH" ./scripts/check.sh
```

No figure bytes change; the caption tests read the tables, not the prose, so they stay green.
