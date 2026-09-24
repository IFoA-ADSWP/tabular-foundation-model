# Research Context — *Tabular Foundation Models*

> **External research source.** This is a research-context note, not project evidence and not a benchmark result.
> **Author:** Christoph Molnar
> **Source:** [Tabular Foundation Models — online book](https://tabularfoundationmodels.com/)
> **PDF supplied:** [tabular-foundation-models-christoph-molnar-A4.pdf](https://tabularfoundationmodels.com/downloads/tabular-foundation-models-christoph-molnar-A4.pdf)
> **Accessed:** 2026-09-24
> **License stated by the author/site:** CC BY-NC 4.0

## Purpose

This note records the ideas from Molnar's guide that are relevant to the insurance TabPFN investigation. It is deliberately a short synthesis rather than a reproduction of the book. The book is an accessible technical and opinionated overview; it should guide questions and interpretation, not substitute for this repository's controlled measurements.

## Main ideas relevant to this project

### 1. TabPFN is an in-context predictor, not a conventional fitted model

The guide describes prior-data-fitted networks and TabPFN as models that retain task data as context at prediction time. The programming interface may look like `fit` and `predict`, but the important distinction is that the training table remains part of the prediction context.

This supports the project's distinction between:

- **raw in-context prediction** — no weight update;
- **in-domain supervised fine-tuning** — model weights are updated on a target-domain dataset;
- **transfer/pooling** — weights are updated on source datasets and evaluated on a target absent from the pool.

It also explains why a small amount of additional target data can change in-context performance without any conventional training step.

### 2. The pretraining prior is a source of inductive bias

The guide explains that PFN-style models are pretrained on many synthetic tasks, commonly generated through structural causal models and a task prior. The prior determines which relationships and task structures the model is prepared to solve.

For insurance, this makes dataset structure a first-class research question rather than a secondary implementation detail. Relevant structures include:

- class imbalance and rare-event prevalence;
- nonlinear feature interactions;
- missingness patterns;
- count and zero-inflated targets;
- feature-type mixtures and high-cardinality categoricals;
- domain-specific relationships between policy, vehicle, customer, and claim variables.

This supports the diagnostics-first approach: before asking whether fine-tuning helps, profile the structures that may not match the model's prior.

### 3. Synthetic data has two different meanings

The guide's discussion of synthetic pretraining tasks should not be confused with synthetic-data augmentation for a downstream insurance model.

| Use of synthetic data | Purpose | Current project interpretation |
|---|---|---|
| Model pretraining | Teach the model a broad prior over possible tabular tasks | Relevant background to why TabPFN may already capture useful structure |
| Fine-tuning augmentation | Add synthetic rows to a real insurance training set | A separate intervention that may add noise rather than signal |
| Stress testing / scenario generation | Explore hypothetical portfolios or rare events | A possible future use case, not evidence for predictive fine-tuning |

The repository's earlier augmentation experiments were negative. Molnar's book is therefore useful for understanding the model's pretraining mechanism, not for claiming that synthetic augmentation will improve this project.

### 4. Scaling and inference remain engineering constraints

The guide highlights large-table scaling and inference cost as continuing challenges. This is consistent with the project's decision to keep the row-count ladder explicit and to record measured cost per run.

A model that performs well at 10,000 rows may not be the right operating point at 50,000 or 100,000 rows. The research question is not simply "does the model work?" but:

- at what context size does it work best;
- how does performance change with the number of rows and features;
- what is the inference cost;
- and does fine-tuning improve the operating point that matters in deployment?

### 5. A foundation model does not remove the need for task understanding

The guide argues that TFMs require a different modeling mindset from conventional table modelling. That does not make domain expertise unnecessary. It changes where the work sits:

- before the model: data definition, target construction, feature semantics, leakage checks, and data-generating-process understanding;
- at the model: context construction, row limits, preprocessing, and adaptation choices;
- after the model: calibration, interpretability, monitoring, fairness, and business metrics.

This is the rationale for pairing the fine-tuning pilot with dataset diagnostics rather than treating fine-tuning as a standalone model switch.

## Implications for the current research programme

1. **Raw in-context prediction is the control.** Fine-tuning must beat an in-run raw TabPFN result under the same context and split.
2. **Dataset diagnostics are part of model evaluation.** Feature structure, target definition, imbalance, and missingness can explain apparent fine-tuning gains or failures.
3. **Fine-tuning and data augmentation are separate interventions.** A gain from class weighting, resampling, or synthetic rows must not be attributed to weight adaptation without a matched comparison.
4. **Transfer requires a target-exclusion claim.** Pooled fine-tuning and synthetic pretraining are not evidence about a held-out target unless target data are absent.
5. **The prior matters, but the book is not our benchmark.** Project conclusions must continue to come from pinned v3 runs, canonical splits, per-arm artifacts, and the pre-registered statistical plan.

## Questions this source raises for the pilot

| Question | Why it matters |
|---|---|
| Does the fine-tuning gain come from learning the insurance prior or from changing calibration? | Separates representation adaptation from probability post-processing |
| Which insurance structures are absent from the model's effective prior? | Guides feature engineering and target-definition diagnostics |
| Does more context data substitute for fine-tuning? | Tests the 2K versus 10K row result mechanistically |
| Does synthetic pretraining-like structure help only when the joint distribution is realistic? | Explains why naive augmentation may hurt |
| Where is the operating limit for context size and inference cost? | Determines whether the model is deployable at portfolio scale |

## Source boundaries

This note does not establish any of the following:

- a measured improvement on this repository's insurance datasets;
- a causal explanation for the Probe 1 versus Probe 2 difference;
- evidence that a particular pooling strategy will transfer;
- evidence that synthetic augmentation will help;
- a replacement for the current statistical analysis plan.

Those claims require the pinned experiments and evidence already governed by the fine-tuning pilot design.

## Recommended citation

> Molnar, C. (2026). *Tabular Foundation Models: A short and opinionated guide*. https://tabularfoundationmodels.com/

The linked PDF is the downloadable version supplied for this research note. Readers should consult the online chapters for the current version and links.
