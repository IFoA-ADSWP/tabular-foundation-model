# Plan — record the one-version-per-figure rule

**Status:** Current — implemented with this change, 2026-11-23.
**Origin:** #655, unblocked when #649 closed.

## Why a rule and not a fix

The adoption-figure defect was not arithmetic. The numbers were correct for their era and read as
current, because nothing in the procedure said a figure has one era. A one-off correction fixes
one figure; a rule stated where the next figure author meets it fixes the class.

## What changes

- **`.opencode/skills/dataviz/SKILL.md`** — the rule appears in both the static and HTML
  procedures: one figure depicts one model version, stated in-figure, with a re-tested cell
  disclosed by a marker rather than folded into the plotted numbers.
- **`GLOSSARY.md`** — **Version panel** defined: a set of cells measured at one model version and
  compared together, with re-tests held apart and disclosed.

The glossary entry states the *reason* — a cross-version difference attributes to the version,
not to the methods — and deliberately omits how a marker is drawn, which is the skill's business.

## Not changed

No figure. Acceptance for #655 asks explicitly that none is touched; the figures that motivated
the rule were corrected under #649.
