# Plan — a scoping note on insurance data scarcity

**Status:** Proposed — note written 2026-11-23; it authorises nothing.
**Origin:** a question raised after map #716 closed: if foundation models help where data is
scarce, which insurance tasks are actually scarce?

## Why a note rather than a ticket

The question is not yet sharp enough to ticket. It is a *direction*, and the map discipline says
fog belongs in a note until a destination can be stated. Writing it down also stops the
direction being re-argued from memory each time it comes up.

## What it records

1. **The condition.** Scarcity alone is not the lever; the structure must be transferable. The
   prior is synthetic, so a small-*n* advantage is plausible only where the relationship is
   learnable from few rows and resembles other tabular problems.
2. **Where scarcity is intrinsic** — layer experience, specialty lines, tails, catastrophe
   accumulation, emerging risks, credibility-scale risks, immature cohorts, long-latency morbidity
   — separated from structural (fraud labels) and cold-start scarcity.
3. **The programme's own tension.** The classification size sweep and the frequency/severity
   losses point different ways; the honest reading is that the loss tracks *task shape*, not row
   count.
4. **The evaluation trap.** Small cells cannot support a pre-registered floor — at 1,000 rows the
   MDE exceeds the 2% floors. A small-data arm needs a *population* of tasks or bootstrap
   intervals, not one cell.
5. **What is testable** — the 464-triangle reserving population — and what is not (marine,
   aviation, space; no public microdata).

## What it does not do

No run, no spend, no ticket, and no claim that a small-data advantage exists. If the direction is
pursued it becomes a map with its own destination, and this note is its starting position.
