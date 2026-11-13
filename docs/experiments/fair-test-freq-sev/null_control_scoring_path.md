# Null control — can the scoring path detect a known-null effect?

> **Status:** active — analysis, 2026-11-03. **Question:** at the pilot's size, can the harness tell a
> real effect from noise? **Data:** `results/20261031T021845Z/` (the anchor, eight arm records with
> committed predictions). **Method:** scores-only, 5,000 label permutations per seed. **No spend, no
> launch, no GPU.** **Decision it informs:** D11's restatement, D12, and the resolution gate in D13.
> **Recorded on:** [#338](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/338) and
> [#125](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/125).

## Answer

**The scoring path does not invent effects, and the anchor's size could not have detected one.** Those
are separate findings and only the first is reassuring.

| | Value |
|---|---|
| Permutation p, all six arm × seed cells | 0.29 – 0.84 |
| Observed ΔAUC inside the null band | 6 of 6 |
| Two-seed rule (both seeds, same direction, bounds not markers), under the null | 0.0008 – 0.0012 |
| Per-seed null SD of ΔAUC | 0.0052 – 0.0055 |
| Per-seed null 95% half-width | ≈ ±0.010 |
| Effect in question (R1, and the anchor) | 0.002 – 0.003 |

## Method

Predictions are held fixed. The true labels are shuffled 5,000 times per seed with
`numpy.random.default_rng(20261102 + seed)`. Every arm is rescored against the **same** permutation, which
preserves the between-arm correlation that makes the comparison paired. ΔAUC is each tuned arm against
`A_raw` computed on that permutation.

A shuffled label set is the sharp null — the scores cannot know the labels — so whatever the harness
reports is measurement noise by construction. No refit, no launch, no spend; runtime about 31 s on CPU.

## What it establishes

1. **The harness does not manufacture deltas.** Under a known null it stays inside its band, and the
   two-seed rule D9 used fires at about one in a thousand. The earlier failed replication was not an
   artifact of the scoring machinery.
2. **A negative at 1,000 test rows is uninformative.** The design's resolution is roughly three times the
   effect it was asked to detect, so "no effect" and "no power" produce the same observation.
3. **D11's reading was the wrong row of its own pre-registered mapping.** The decision log's §3 maps
   "test-set power unreachable within the envelope" to *report the power limit, not a null*. That is the
   reading this measurement selects.

## Limits

- **Scoring path only.** This validates the metric, the paired comparison and the capture→rescore route.
  It does **not** test a training-side defect such as the 0-step inference-config asymmetry recorded as
  W1 in #125, which needs a refit.
- **Not a power design.** It measures the null band at the anchor's size. It does not say what size would
  suffice; that is the sizing analysis in `../pilot2-phase2/replication_sizing.md`.
- **Two different half-widths exist.** This document reports the band under a *known null* (≈±0.010). The
  power diagnosis in `../pilot2-phase2/anchor_power_diagnosis.md` reports the interval around an *observed*
  effect (±0.0036). They answer different questions and neither may be quoted as the other.

## Reproduction

The recipe above is complete and deterministic. Turning it into a committed tool is the verdict-tool
ticket (#398), which must reproduce these figures on this capture as a test — until then, the numbers
here are the record and the method is the contract.
