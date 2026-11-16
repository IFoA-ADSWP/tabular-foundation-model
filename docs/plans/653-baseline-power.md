# Plan — the baseline forest exposes the power behind Inconclusive

**Status:** Current — implemented with this change, 2026-11-16.
**Origin:** #653, from the figure-honesty audit.
**Design:** the row's minimum detectable effect becomes a field of the row, and the one row where it
exceeds its floor *and* the verdict is Inconclusive is marked.

## Scope

1. `Row` carries `mde`, read from the verdict the analysis already returns.
2. The decision column appends **"· underpowered"** on the single row where `Inconclusive` and
   `mde > floor` — French frequency at the matched budget, MDE 2.35% against a 2% floor.
3. The caption and finding 1 say what that means: the design could not have detected the bar it was
   tested against.
4. Two tests: the flagged row and its MDE; and the fact that No-go rows may also sit above their floor
   without being underpowered, because their upper bound already excludes a gain.

## Decisions worth arguing with

**Only the Inconclusive row is flagged.** Primary French frequency also has an MDE above its floor
(3.09% against 2%) and is a No-go: the interval's upper bound is below the floor, so the design
resolved the question in the direction that matters. Flagging every MDE > floor row would call a
decisive No-go underpowered.

**The flag is text, not another tick.** A second marker beside the floor would need a legend entry and
would still leave the reader to work out that 2.35% > 2% means "could not have seen the bar".

**The MDE stays a row field even where it is not drawn.** It is what the test asserts and what a later
figure can use; deriving it at the call site would put the rule in two places.

## Verification

```sh
.venv/bin/python scripts/infra/baseline_figures.py
.venv/bin/python -m pytest tests/test_baseline_figures.py -q
PATH="$PWD/.venv/bin:$PATH" ./scripts/check.sh
```
