# Baseline conclusion, November 2026

> **Status:** current — campaign opened 2026-11-21; conclusion and companion written the same day.

The phase's closing distribution: one technical conclusion, one plain-language companion, and the
generated table they both quote.

## Documents

| Document | What it is |
|---|---|
| [`CONCLUSION.md`](CONCLUSION.md) | **Current.** The technical conclusion: the answer, the generated verdict tables, the gap register, four ways to misread it, the direction, what would change our mind, how to check us, and what each command costs. |
| [`COMPANION.md`](COMPANION.md) | **Current.** The same story for an actuary deciding adoption, ~2 pages, no method detail and no number of its own. |

## What this campaign owns

The headline table, by decision recorded in `docs/DOCUMENT_AUTHORITY.md` (#633). Every other
document keeps its own claims; this one restates them and cites them.

The table is **generated** by `scripts/analyses/baseline_conclusion.py`, and
`tests/test_baseline_conclusion_table.py` fails when the conclusion drifts from the generator.
