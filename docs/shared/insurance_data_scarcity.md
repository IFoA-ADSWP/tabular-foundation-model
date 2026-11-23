# Where insurance data is scarce — and where a foundation model could matter

> **Status:** proposed — scoping note, 2026-11-23. It measures nothing, restates no number as its
> own, and **authorises no run**. Its purpose is to seed a future wayfinder map, so that the
> "small data" direction is entered from a stated position rather than from intuition.

## 1. The condition is not scarcity. It is scarcity *with transferable structure*

The literature reviewed in
[the frontier note](tfm_insurance_literature_frontier.md) reports that tabular foundation models
help where target data is small, and the credit-risk review (arXiv:2605.18147) is the clearest
statement of it. That is easy to over-read.

TabPFN's prior is learned from **synthetic** tasks, not from insurance. It therefore transfers a
*function-class* prior — smooth, low-order, adapts in context — and not any insurance domain
knowledge. A small-data advantage is plausible only when both hold:

1. the relationship is learnable from few rows, rather than driven by a rare event; and
2. the structure resembles other tabular problems, so the prior is relevant.

Where data is scarce **and** the signal is idiosyncratic — one aviation hull loss, a novel cyber
accumulation — there is nothing for the prior to bring. Where data is scarce and the structure is
ordinary — a new motor book with 800 policies — there is.

## 2. Where insurance genuinely has little data

| Task | Why it is scarce | Kind |
|---|---|---|
| Excess-of-loss reinsurance layers | Only losses reaching the attachment point count; a layer may see a handful in a decade. Exposure rating exists because this is true | intrinsic |
| Specialty lines — marine, aviation, energy, space, terrorism, political risk | Tens of policies per class, fewer claims | intrinsic |
| Extreme tails — 1-in-100, 1-in-200 events | Rarity is the definition of the event | intrinsic |
| Catastrophe accumulation | Correlated events, so effective *n* is far below the row count | intrinsic |
| Emerging risks — cyber, climate-attributed perils, AI liability | No history exists yet | zero-data |
| Cold start — new product, segment or geography | Rows exist, outcomes do not | fixable with time |
| Credibility-scale risks — one large commercial client | Classic small-group problem; per-risk experience is n≈1 | intrinsic |
| Immature reserving cohorts | Late development periods hold few cells | intrinsic, partially |
| Fraud | Confirmed-fraud labels are rare *and* noisy | structural |
| Long-latency morbidity — mesothelioma, extreme-age mortality | Latency exceeds the observation window | intrinsic |

## 3. What this programme's own evidence already says

Two results pull in different directions, and the tension is the useful part:

- **Classification, across row budgets.** The size sweep in
  [`docs/MASTER-REPORT-DIGEST.md`](../MASTER-REPORT-DIGEST.md) records an 8-of-9 win across
  1k / 5k / full, with the single loss at 163k rows inside fold noise. On classification the
  small-data advantage neither appears only at small *n* nor vanishes at full data.
- **Frequency and severity, at scale.** The fair test
  ([`freq_sev_fair_test_result.md`](../experiments/fair-test-freq-sev/freq_sev_fair_test_result.md))
  records decisive losses on count and severity targets. Those cells carry **large** row counts.

So the observed pattern is not "small data good, big data bad". The loss concentrates where the
task is **count or severity with a strong offset structure**, which is a statement about task
shape, not about *n*. Any small-data hypothesis has to explain that, not ignore it.

## 4. The trap: the tasks with most to gain are the ones you cannot measure

A 200-row table cannot support a pre-registered floor. The pattern is already recorded: the
direction decision in
[the phase conclusion](../experiments/baseline-conclusion-2026-11/CONCLUSION.md) warns
that at 1,000 rows the minimum detectable effect exceeds the 2% floors, so cells are
**Inconclusive by construction**.

A small-data arm therefore cannot be one cell with one bar. It needs either a **population** of
small tasks with pooled inference, or bootstrap intervals reported instead of null bands. That
design choice is the whole difficulty of the direction, and it is why this belongs in a map
rather than a ticket.

## 5. What is testable here, and what is not

**Testable:** the sibling `tabpfn-reserving` work already holds **464 real triangles**. A triangle
is roughly 55 cells and its late development periods are sparse — genuine intrinsic scarcity with
real structure. More importantly, 464 of them are a *population* of small problems, which is the
only shape that supports an inference about a small-data advantage without per-cell power.

**Not testable here:** marine, aviation, space, and layer-loss experience. The real prizes, and
there is no public microdata. They would be judgement fixtures at best, and should be named as
unavailable rather than approximated with something easier.

## 6. What a future arm would look like

> **Sketch only, not a candidate.** *On genuinely small, structured insurance tasks, does the
> frequency/severity deficit reverse — and does fine-tuning or an exposure-aware form change it
> in the small-*n* regime as it did not in the large-*n* one?*

Its design would need, at minimum: a population of small tasks (the triangles, or pooled
cross-portfolio folds); an inference method that survives small per-task *n*; and a stated rule
for what "reverses" means across a population rather than within one cell.

## 7. Boundaries

- **Nothing here is authorised.** No run, no spend, no ticket.
- **The numbers above are owned elsewhere** and are cited, not restated as this note's own.
- **This note does not claim a small-data advantage exists.** It identifies where one could be
  tested and what would make the test meaningless.
