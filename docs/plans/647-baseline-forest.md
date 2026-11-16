# Plan — the actuarial baseline verdict as a forest

**Status:** Current — implemented with this change, 2026-11-15.
**Origin:** #647. The follow-on to the caption work: the newest result in the repository had no figure.
**Design:** one forest over the committed v5 captures, drawn by the same analysis function the verdict
document uses.

## Scope

1. `docs/figures/actuarial_baseline_forest.{pdf,png}` — per target and budget: `r`, 95% interval,
   registered floor, decision.
2. `scripts/infra/baseline_figures.py` — one entry point; `analyse()` called for both budget sets.
3. Embed and caption in `actuarial_baseline_summary.md`; index row; `tests/test_baseline_figures.py`.

## Decisions worth arguing with

**Two rows per target, one figure.** The document reports two budgets because they answer two
questions. Splitting them into two figures would hide the comparison; a single row would hide the
budget effect. The rows are labelled "full pool" and "10k rows" so the pair reads as one question
answered twice.

**`severity_spanish` is drawn once.** Its fold holds fewer than 10,000 rows, so both arms are the
same fit. Drawing it twice with identical intervals would imply a comparison that does not exist;
the row says "one fit" in its label.

**The sign goes first in the caption.** `r` is positive when TabPFN is better, which is the opposite
of how a reader might guess from the fair-test figure. Every point being left of zero is the result;
the caption says so before describing the encoding.

**The floor tick stays, even though it sits across the axis from every point.** It is what makes the
picture a verdict rather than a comparison: without it a reader cannot see how far the results are
from the bar that was registered before they were measured.

**The figure calls `analyse()`, not a reimplementation.** Both budget sets go through the function the
document uses, and the test parses the document's primary table, so figure and document fail together.

## Verification

```sh
.venv/bin/python scripts/infra/baseline_figures.py
.venv/bin/python -m pytest tests/test_baseline_figures.py -q
PATH="$PWD/.venv/bin:$PATH" ./scripts/check.sh pytest
```

The local full suite has been terminated by the environment three times (SIGTERM at 23%, 53% and 69%,
with another session active in a sibling worktree); CI carries the full-suite evidence for this change,
and that is stated in the pull request.
