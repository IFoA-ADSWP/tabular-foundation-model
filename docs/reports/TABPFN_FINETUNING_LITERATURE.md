# What the literature says about fine-tuning TabPFN — and what it means here

**Purpose.** External evidence, kept deliberately separate from our own measurements. This file records what
the published work and the vendor's own guidance claim, **and whether we have checked it**. Our own results
live in `PROBE_RESULTS.md`, `FINE_TUNING_PILOT_RESULTS.md` and the run records — not here.

**Two rules for this document.**

1. Every claim carries a source and a **verification status**: `verified` (we read it in the primary
   source), `unverified` (repeated second-hand, not yet seen in the source), or `corrected` (the common
   version is wrong).
2. Do not tidy a claim into something stronger than its source says. The whole point of keeping this
   separate is that our results can't borrow credibility from it, or lend it.

## The sources

| # | Source | What it is |
| --- | --- | --- |
| 1 | *On Finetuning Tabular Foundation Models* — arXiv **2506.08982** (Rubachev, Kotelnikov, Kartashev, Babenko; v2, Jun 2025) | The primary study. Code: `github.com/yandex-research/tabpfn-finetuning` |
| 2 | Prior Labs, **Fine-Tuning** — `docs.priorlabs.ai/capabilities/fine-tuning` | The vendor's own guidance. Structure: *When to Fine-Tune*, *Good Candidates*, *When Fine-Tuning is Less Likely to Help*, *Decision Flowchart* |
| 3 | *Drift-Resilient TabPFN* — arXiv **2411.10634** (NeurIPS 2024) | The paper on temporal distribution shifts, which the summaries of (1) tend to omit |
| 4 | TabPFN-2.5 technical report — `storage.googleapis.com/prior-labs-tabpfn-public/reports/` | Model release notes; useful for capability boundaries, not for fine-tuning outcomes |

## Where fine-tuning is reported to succeed

Attributed to (1) unless noted:

- **I.I.D. splits.** On datasets whose splits are independent and identically distributed, fine-tuning
  reaches state-of-the-art results. The mechanism is stated plainly: gradient adaptation makes the dot
  products between test-object query representations and in-context training-object key representations
  better reflect true target similarity — the model becomes a sharper retrieval system rather than a
  general prior.
- **Domains missing from the synthetic pretraining distribution** — the vendor's guidance (2) frames these
  as the good candidates, on the reasoning that a prior cannot cover what it never saw.
- **Full fine-tuning over parameter-efficient variants**, for time-efficiency and effectiveness (1).
- **Larger batches help** (1). A configuration finding, not a dataset one — and the reason our own config
  deserves an audit rather than trust.

## Where it fails or is less likely to help

- **Temporal shift — the important one for us.** With gradual temporal shifts and rich feature sets,
  TabPFNv2 is *"less stable and prior methods remain better"* (1). This is the clearest negative claim in
  the paper, and the one that most directly bears on insurance lapse and surrender data.
- **Very small datasets.** Overfitting risk; the prior is doing the work and there is too little signal to
  reshape it usefully (`unverified` as a numeric threshold — see the table below).
- **Large datasets.** The stated limit is **1M cells** (*rows × columns*), the practical ceiling for
  straightforward fine-tuning — a cell budget, **not** a row count.
- **(3) is the nuance the summaries lose:** temporal drift is a problem for *fine-tuning*, but it is the
  subject of a whole separate line of work that adapts TabPFN *in context*. "TabPFN cannot handle drift" is
  not what the literature says; "fine-tuning is not the tool for it" is.

## Verification status of the claims commonly repeated

| Claim as usually seen | Status | Note |
| --- | --- | --- |
| Fine-tuning helps on I.I.D. academic benchmarks | `verified` | (1), stated directly |
| Fine-tuning fails under gradual temporal shift | `verified` | (1), stated directly — see the quotation above |
| The limit is "50,000 rows or 1M cells" | `corrected` | (1) frames it as **1M cells (rows × columns)**. Row count and cell count diverge by the feature count |
| "1,000 to 50,000 rows" is Prior Labs' recommended band | `unverified` | (2) has the matching section structure; **the numeric band was not present in the portion we could read**. Read the page directly before quoting it |
| Drift-Resilient TabPFN is irrelevant to this question | `corrected` | It is the most relevant paper for a temporal domain, and it is absent from the common summaries |
| Fine-tuning is amortised over repeated inference on a fixed schema | `unverified` | Consistent with (2)'s framing; no numbers seen |

## What this does to our own result

**Our negative is consistent with the published finding, not in tension with it.** `uslapseagent` is
insurance lapse — real-world, temporal, rich-featured — which is precisely the condition under which (1)
reports prior methods remaining better. So the probe did not produce an anomalous result; it reproduced a
documented boundary.

Three implications, in order of how cheap they are to act on:

1. **Audit our fine-tuning configuration against (1) before believing the verdict.** We ran
   `learning_rate=1e-5` with `n_estimators=2`, inherited from the reduced first-pilot exercise. Given (1)'s
   batch-size finding, a negative from that config is evidence about *our configuration*, not about
   fine-tuning.
2. **Distinguish "fine-tuning doesn't help" from "fine-tuning isn't the tool here."** For a temporal
   domain the literature predicts the second. That distinction changes what we would tell the team, and it
   changes whether the follow-up is worth funding.
3. **An I.I.D. academic dataset is the fair test of the method** (OpenML-CC18, TabZilla and similar are
   named in (1)). If fine-tuning gains there and not on lapse, the finding is a *domain boundary* — which
   is a more useful and more defensible statement than a flat negative.

## One thing the literature does not explain

Our probe found calibration improving monotonically with epochs (PR AUC, Brier, log loss) while ROC AUC did
not move. The retrieval-sharpening mechanism in (1) predicts a *ranking* improvement, so our calibration
observation is not explained by the published account. Either it is noise at one seed, or it is a distinct
effect. It is also the observation with commercial relevance, since a fixed schema scored repeatedly is
exactly the amortised setting.

## Open questions, as questions

- Does our configuration reproduce (1)'s batch-size result? *(cheap: one run, one dataset)*
- What does (2) actually state as its rows band? *(cheap: read the page)*
- Does fine-tuning gain on an I.I.D. academic dataset at our scale? *(one run, one dataset)*
- Is the calibration effect real, and does it survive at the full row count? *(the narrow follow-up the
  proposal already names)*
