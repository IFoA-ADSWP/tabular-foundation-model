# Plan — the pre-registration and the verdict tool (#396, #398)

**Status:** current — 2026-11-04. **Origin:** #396 and #398, under spec #395.

## Why

Two artefacts stand between the decision and the probe. The plan document fixes what the run will be
judged against **before** any data exists; the tool computes that judgement from a capture instead of
arguing it. Without the first, "add 20 more seeds" is a decision made after seeing the answer. Without
the second, the gate between probe and replication becomes a reading of a table.

## What lands

- **`docs/current/FINETUNING_PREREGISTRATION_2026-11.md`** — dataset, model pin, probe shape, rung rule
  with its budget fallback, the seed formula, the aggregation, the null band, the decision rule, and the
  dated amendment to the escalation rule.
- **`src/verdict.py`** — per-seed deltas against the in-run baseline, the permutation null, the
  resolution at a seed count, and the reading. Reuses `capture_reader.read_run` so every input is
  already hash-verified, and `metrics` so the numbers match the registry.
- **`scripts/analyses/verdict.py`** — the thin CLI, same shape as `make_capture.py` and `rescore.py`.
- **A `verdict` gate check** that runs the tool against the committed anchor and fails if its null band
  drifts from the 0.010 the decision log cites. The code and the document cannot separate silently.

## The decisions in the tool

**Rows are never pooled.** Pooling understates the standard error by ~1.69× at this design's variance
ratio and lifts the false-positive rate to ~0.25. That is written in the module docstring, because a
rejected option that is not recorded gets reintroduced.

**The reading is computed from the interval and the Brier veto**, never asserted: pass requires the
lower bound above zero, the point at or above the target, and the Brier guard met; a null inside ±δ is
equivalence; everything else is unresolved.

**Refusals name the gap**: no baseline arm, no tuned arm, fewer than two seeds, fewer seeds than the
pre-registration declares, a seed set that reuses another run's (the probe and the replication must not
overlap), a non-positive target, too few permutations.

**Two claims are withheld rather than computed.** Zero between-seed variance makes a zero-width interval,
so any point estimate would read as a pass; it reads *unresolved* instead. And a rule that fires more
than 0.07 under the permutation null is **void** — an instrument failure, not an effect. The bound is
one-sided because a conjunction is deliberately conservative: the anchor's rule fires at about 0.001, and
a two-sided band would have voided the only rule that protects the claim.

**Output** is a long-format CSV when `--out` is given: one row per arm × seed × metric, carrying the
capture hash, the tool version and the target effect, so a row is self-describing and a citation can name
the arithmetic that produced it.

## Seams

One seam, the same one `rescore` uses: a run directory in, verified arrays out, a printed result and a
CSV. Tests build small run directories in a temporary directory; the committed anchor is the regression
fixture, and the sizing document's 57 seeds is a unit test of the formula.

## Out of scope

The probe itself (#399), the replication, and any change to the runner. Nothing here spends money.
