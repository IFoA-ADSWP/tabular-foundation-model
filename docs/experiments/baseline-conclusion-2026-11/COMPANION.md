# Can we use this model for pricing? — the short answer

> **Status:** current — 2026-11-21. The plain-language companion to
> [`CONCLUSION.md`](CONCLUSION.md). It adds no number of its own: every figure it mentions is in the
> technical conclusion, and the technical conclusion is the one to cite.

## What we did

We took a foundation model for tables — a model pre-trained on many datasets that predicts a new one
without being trained on it — and put it against the tools an insurer already uses: a generalised
linear model and a gradient-boosted tree ensemble. We did that on twelve benchmark targets drawn from nine public insurance
datasets, on the same folds, with the same scoring rules, and then on a set of smaller samples to see
where the cheap models stop being worse.

## What we found

**For ranking, it is the best thing we have tried.** When the question is "which policies are
riskiest?" — who will lapse, who will claim, which customers to look at first — the model was the best
method on three of the six classification targets and inside fold noise on two more, at these row
counts. It needed no tuning to do it. On the sixth a linear model has the lower log loss.

**For pricing, it is not.** When the question is "how much will we pay?" — how many claims, how large
each one — the trees won. A linear model also won more often than our earlier report said, once it
was given the exposure information the way an actuary would give it, rather than as one more column.

**Small data is not one thing.** On one of our datasets, at the sample sizes where a foundation model is
supposed to shine, nothing beat simply predicting the average — and no model arm was run at those
budgets, so that is a statement about the baselines, not about the model. On another, the linear model
improved steadily as we added rows. So "small data" is not a single regime, and a small dataset does
not automatically favour the model.

## What this means for you

Use the model where you need a **ranking** — triage, lapse prevention, claim propensity, prioritising
cases for a human. Use a GLM or a tree ensemble where you need a **number to price with**.

Do not treat the model as a drop-in replacement for a pricing model because it performs well on a
classification task. Those are different questions, and on our evidence they have different answers.

## What we could not settle

- **The zero-inflated count question.** The vendor advises a two-step model for claims with many
  zeros. We have not tested it. That test is designed and paused, on purpose: a new model version is
  due and is claimed to address exactly this, so an answer measured today could be out of date before
  it is read.
- **Reserving.** Our reserving work lives in its own repository and is not part of this comparison.
- **Other foundation models.** We could only measure one on our hardware; the others need a graphics
  card or a paid endpoint, and that is a budget decision rather than a modelling one.
- **Very small samples.** Several of our small-sample comparisons cannot separate a two-percent
  difference. We have said where that is, rather than calling it a tie.

## What would change this advice

A two-step model that beats the single model on zero-inflated claims. A second dataset where the
exposure-aware linear model beats the model on ranking, not just the one where it does. A new model
version — which re-opens every verdict here. Or a graphics card, which would let us compare against a
second family of models instead of one.

## How to check us

Read [`CONCLUSION.md`](CONCLUSION.md). It carries the table, the intervals, the gaps and the commands
that reproduce every number, each labelled with what it costs to run.

---

**In one sentence:** use it for ranking and triage, keep a GLM or a GBDT for pricing at scale, and
expect the count verdict to be re-tested when the next model version lands.
