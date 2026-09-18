# What the literature says about fine-tuning TabPFN — and what it means here

**Purpose.** External evidence, kept deliberately separate from our own measurements. This file records what
the published work and the vendor's own guidance claim, **and whether we have checked it**. Our own results
live in `docs/current/PROBE_RESULTS.md`, `FINE_TUNING_PILOT_RESULTS.md` and the run records — not here.

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
| "1,000 to 50,000 rows" is Prior Labs' recommended band | `corrected` | Read directly, 13 Sep. **No such band exists on the page.** Its only row threshold is the small-data one below 1,000 rows. The upper figure was not theirs |
| Drift-Resilient TabPFN is irrelevant to this question | `corrected` | It is the most relevant paper for a temporal domain, and it is absent from the common summaries |
| Fine-tuning is amortised over repeated inference on a fixed schema | `verified` | (2) names it as a good candidate in its own words: an upfront cost that pays off across many future predictions |
| Fine-tuning a single model across several related tables | `verified` | (2) names this as a good candidate -- relevant to the pooling idea in `PILOT_2_DESIGN.md` |
| Fine-tuning is worth trying when the baseline is already close | `corrected` | (2) lists the opposite: if baseline TabPFN is within a few percent of the target metric, simpler approaches usually close the gap first |

## What this does to our own result

**Our negative is consistent with the published finding, not in tension with it.** `uslapseagent` is
insurance lapse — real-world, temporal, rich-featured — which is precisely the condition under which (1)
reports prior methods remaining better. So the probe did not produce an anomalous result; it reproduced a
documented boundary.

Three implications, in order of how cheap they are to act on:

1. **Our learning rate is not the suspect.** The vendor's own example is `epochs=30` with
   `learning_rate=1e-5` -- what we ran. The config axis (1) actually reports on is **batch size**, which
   is untested here. And a second, sharper point: (2) says fine-tuning is less likely to help *when the
   baseline is already within a few percent of the target*, which is exactly our situation (the arms sit
   within about 0.25 ROC AUC points of `A_raw`). That is a predicted failure condition we meet.
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

## Read directly from the vendor's page (13 Sep)

Fetched at source (`docs.priorlabs.ai/capabilities/fine-tuning.md`), so these are `verified`:

**Good candidates, in their framing.** Amortised prediction cost -- the same schema predicted repeatedly.
Niche or specialised domains whose distribution the pretraining priors do not cover well, with
domain-specific financial instruments named among the examples. And **multiple related tables**, where one
model is fine-tuned across a family of datasets -- which is the pooling idea in `PILOT_2_DESIGN.md`, and the
vendor names it as a reason to fine-tune.

**Less likely to help.** Datasets under **1,000 rows**, where overfitting risk outweighs adaptation. Cases
where the **baseline is already within a few percent** of the target metric, where their own advice is to try
feature engineering, metric tuning and preprocessing first. And **gradual temporal shifts with many
features**, where fine-tuning can be less stable.

**The operational sentence we did not follow.** On temporal data the page says plainly: *make sure your
train/validation split respects the time ordering.* Our probe used the loader's **stratified random split**
on insurance lapse data. That is a breach of the vendor's own guidance for exactly this kind of domain, and
it belongs beside the verdict as a limitation -- it is a stronger explanation of the negative than the
"domain boundary" framing alone, and it is fixable.

**Their defaults.** The documented example is `epochs=30`, `learning_rate=1e-5` -- the configuration we used.

## Newer and adjacent sources (searched 13 Sep)

Found by searching beyond the paper we started from. Status is per the rules at the top of this file.

### Read at source

**Exploring Fine-Tuning for Tabular Foundation Models** — arXiv **2601.09654** (Tanna, Seth, Bouadi,
Sankarapu; Jan 2026). `verified`. The most consequential find after our probe. Its findings:

- zero-shot TFMs already perform strongly, and the benefits of fine-tuning are **highly model- and
  data-dependent**;
- **full supervised fine-tuning often reduces accuracy *or* calibration quality**, while meta-learning and
  parameter-efficient fine-tuning (PEFT) give moderate gains under specific conditions;
- it analyses how **imbalance, size and dimensionality** affect outcomes, and covers calibration and
  fairness, across TALENT, OpenML-CC18 and TabZilla.

Two things follow. It **corroborates our accuracy result independently** — a second study reporting that
full SFT can hurt — and it **puts our calibration observation in tension with a second source**, since it
reports SFT degrading calibration where we saw it improving. It also names the three dataset factors worth
varying deliberately in the next design.

**Fine-tuned In-Context Learning Transformers are Excellent Tabular Data Classifiers** — arXiv
**2405.13396** (den Breejen, Bae, Cha, Yun; v2 Jan 2025). `verified`. A *positive* result on the earlier
generation: fine-tuning TabPFN gave a significant boost, and enabled complex decision boundaries. This is one
of the prior works the 2026 study calls inconsistent — which is the point: **fine-tuning's value changed with
the model generation**, so our negative is generation-specific rather than a general property of tabular
foundation models.

### Located, not yet read — `unverified`

| Source | Why it may matter here |
| --- | --- |
| **TabArena** — a living benchmark for tabular ML (NeurIPS 2025) | A maintained benchmark is the right place to choose the I.I.D. control dataset for the method-versus-domain test |
| **TabPFN Unleashed** — arXiv 2502.02527 | Scaling TabPFN; bears on whether our 2,000-row cap is the binding constraint |
| **Fine-Tuning or In-Context Learning? Understanding Their Trade-offs** — ACM 10.1145/3779211.3793170 | The decision question itself: when adaptation through gradients beats adaptation through context |
| **TabDPT** (arXiv 2410.18164, NeurIPS 2025), **LimiX** (2509.03505), **TabICLv2** (2602.11139) | Sibling models: whether our result is a TabPFN result or a tabular-foundation-model result |
| **Pocket Foundation Models** — distilling TFMs into CPU-ready GBDTs | Relevant to the deployment and CPU constraints rather than to training |

### Searched and not found

- **No literature located on insurance lapse prediction with temporal validation.** Our domain's own
  methodology — what a correct temporal split looks like for cohort lapse data — has no paper behind it in
  this search, so any choice we make there needs to be justified from first principles and recorded.
- **Nothing beyond Drift-Resilient TabPFN on distribution shift for TabPFN.** The shift literature is thin;
  the vendor's split guidance is currently the most actionable statement available.

### What this does to the plan

1. **Do not re-run the same full-SFT ladder.** Two sources now report that full SFT can hurt, and we have
   already measured it at this scale. Repeat first, not repeat the ladder.
2. **PEFT or meta-learning is the untested adaptation family**, reported as giving moderate gains under
   specific conditions — and it costs less compute than full SFT. That is the resource-efficient direction.
3. **Vary the three named factors deliberately** — imbalance, size, dimensionality — instead of varying
   epochs.
4. **If calibration is the question, pre-register it explicitly** with repeats: two sources now disagree with
   our calibration observation, which makes it more important to test properly rather than less.

## Second sweep: the vendor's own report, the tooling, and a lineage problem

### Read at source — `verified`

**TabPFN-2.5 — arXiv 2511.08667** (the vendor's own technical report; v2, Feb 2026). Three things matter
here:

- The report states that **fine-tuned on real data, the model shows stronger performance** — fine-tuning is
  part of the vendor's headline claim for this generation, which sits awkwardly beside the two studies
  reporting that full supervised fine-tuning can hurt.
- **Supported scale: up to 50,000 samples and 2,000 features — a 5x and 4x increase over TabPFNv2**, with
  exploratory runs far beyond that on an 80GB H100 using FP16 and FlashAttention-3. **Our probe capped
  training at 2,000 rows. That cap was the loader's default, not a model limit.** In other words, the binding
  constraint on our verdict was one we imposed ourselves.
- Their benchmark is **TabArena-lite** — so TabArena is the vendor's own evaluation surface, and the right
  place to choose an I.I.D. control dataset.

**TabTune — arXiv 2511.02802** (v3, Dec 2025). A unified library covering seven tabular foundation models
through one interface, with standardised preprocessing, **consistent fine-tuning procedures**, and
**standardised evaluation for deployment-oriented metrics including calibration and fairness**. This is the
practical route to testing adaptation families without re-implementing them — and its authors are the same
group as the January 2026 fine-tuning study, so its procedures are the ones that study evaluated.

### The lineage problem — this is the caveat that matters most

**Both fine-tuning studies we rely on are TabPFNv2-based. Our probes ran the v3 checkpoint** (the run's
licence is `tabpfn-3-license-v1.0`, from the `tabpfn_3` repository, via the installed `tabpfn` package).
So every condition in this document was established on an earlier generation than the one we measured.
That does not discard them — the vendor's current documentation is consistent with them, including the
`epochs=30`, `learning_rate=1e-5` defaults — but it means **cross-generation transfer is an assumption, not a
fact**, and it cuts both ways: our negative may not reproduce on v2 conditions, and v2 guidance may not bind
v3.

### Located, `unverified`

- **Lapse-prediction domain literature does exist** — a life-insurance lapse prediction study and a mortgage
  life lapse study in the insurance-modelling literature, plus an actuarial trade article on AI lapse
  prediction. Not read (paywalled), so their validation practice is unverified, but the earlier conclusion
  that "no such literature exists" was wrong: our search phrasing was.
- **Zero-shot meta-learning for tabular prediction** (PMLR v267, Wu et al.) — meta-learning as an adaptation
  route, distinct from both PEFT and full fine-tuning.

### Searched and not found — record the absence so nobody repeats the search

- **How much data fine-tuning needs** (any scaling relationship between rows and gain) — nothing found.
- **Imbalance and calibration specifics for TFM fine-tuning** — nothing found beyond the 2026 study's
  statement that imbalance is a factor.
- **Benchmark variance under repeated seeds** — nothing found. But this one is answerable from our own
  records rather than from the literature: `A_raw` scored 0.9360 in the first pilot and 0.9363 in the probe,
  on the same dataset and split. A 0.0003 spread across two runs is a measured starting point for how many
  repeats a comparison needs.

### What this changes about the next design

1. **Lift the row cap before concluding anything about scale.** The model supports 50,000 samples; we used
   2,000 because a loader default said so. The same probe shape, more rows, no new machinery — the cheapest
   substantive experiment available.
2. **Test adaptation families with TabTune** rather than writing them: zero-shot against meta-learning
   against parameter-efficient against full supervised, with its standardised calibration metrics. That
   directly addresses our contested calibration observation at low cost.
3. **Use TabArena-lite for the I.I.D. control** — the vendor's own benchmark, so the comparison is on the
   surface the field uses.
4. **Estimate variance from our own runs** instead of waiting for a paper: two runs of the same arm on the
   same split already bound the noise.
5. **Verify any v2-derived guidance against the v3 checkpoint** before it drives a design, and say so in the
   write-up when it can't be verified.

## In this repository (v2-era, and it says so)

Five documents already covered this ground before the current line of work began. They are cited here rather
than rediscovered, with the caveat they carry themselves: v2-era, weights ID unrecorded.

| document | what it is | how to use it |
| --- | --- | --- |
| `INSURANCE_DOMAIN_FINETUNING_METHOD_PROTOCOL.md` | the same test, proposed April 2026: H1 probability quality, H2 ranking, zero-leakage rule, arms, tuning policy, initial budget | **the protocol transfers**; its numbers do not |
| `INSURANCE_SPECIFIC_FINETUNING_EVIDENCE.md` | evidence review of insurance-specific fine-tuning; short answer, then what cannot be claimed yet | cite for the framing, not the figures |
| `TABPFN_FINE_TUNING_LIMIT_STUDY.md` | empirical study of which row/context/step settings are workable on Apple Silicon | feasibility, not efficacy |
| `tabpfn_finetune_limit_test_plan.md` | the plan behind that study (CPU row scaling, M1 spot checks) | feasibility, not efficacy |
| `tabpfn_small_finetune_methodology.md` | small, low-risk fine-tuning readiness method and defaults | feasibility, not efficacy |

The three feasibility documents are the origin of the standing rule not to chase fine-tuning on CPU. **None of
the five reports whether fine-tuning improves predictions on lapse data** -- that question was open in April
and is the one this line of work answers, first negatively at 2,000 rows and then positively at 10,000.
