# Historic Fine-Tuning Testing — Appraisal and Limitations

> Date: 2026-09-12 | Status: current | Related: #22
> Companion to `NEXT_STAGE_PROPOSAL.md` (the proposed next stage) and
> `CLASSIFIER_HOMOGENEITY_HYPOTHESIS_METHOD.md` (the historic pooling study itself).
>
> **Purpose:** the historic fine-tuning work produced a negative verdict. This document sets out
> what was actually run, under what constraints, and **why that verdict may not be a fair test of
> fine-tuning** — so that the next stage can be designed to be one.

---

## 1. Summary of the historic work

Four studies, in chronology order. All were **CPU-only and small-scale**, and all reported
fine-tuning as neutral-to-harmful.

| Study | Design | Scale | Verdict as recorded |
|---|---|---|---|
| Small-finetune trials | in-domain fine-tune on coil2000 | 1–3 steps, context 64/128 | negligible |
| Stage A domain fine-tuning | fine-tune on other datasets, eval on target | target 800 / pool 400 rows | not positive |
| Pooling Round 2 | LODO, `similarity_topk` vs `mixed_baseline`, seeds 42–44 | target 800 / pool 400, context 64, 3 steps | pooled-negative (ΔROC −0.10) |
| Pooling Round 3 | same, larger budget | context 128, 5 steps | pooled-negative (ΔROC −0.08) → **DOWNGRADE** |

The pooling rounds are the closest thing in the project's history to the test we now want to run:
one model fine-tuned on other datasets, evaluated on a target it never trained on. Their verdict
is the reason the next stage has to be justified carefully rather than simply proposed.

---

## 2. The constraints that shaped it — and what they cost

These were real constraints at the time, not oversights. But each one bounds what the result can
be read to mean.

| Constraint | Consequence |
|---|---|
| **CPU-only execution** (Apple Silicon; thread-capped to avoid torch segfaults) | Hard ceiling on scale: 800 target rows, 400 pool rows per dataset, batch size 1, 3–5 gradient steps. The fine-tune saw at most ~192–640 pooled rows in total. |
| **The v2-era model line, weights unrecorded** | The verdict attaches to no specific checkpoint; the project has since moved v2 → v2.5 → v3, and the historic report itself says not to assume it holds on later versions. |
| **A legacy private API** | The fine-tuning was hand-rolled against `tabpfn.finetune_utils` / `fit_from_preprocessed`, an interface that no longer exists in this form. |
| **Small target count** (4 targets) | The study notes a single unstable dataset can dominate the pooled picture; one target degraded catastrophically. |

---

## 3. The pivotal finding: the historic comparison was not like-for-like

The historic runner evaluates the two TabPFN arms with **different inference contexts**.

**Raw arm** — no subsample constraint is set, so the full training split serves as the inference
context:

```python
model = TabPFNClassifier(ignore_pretraining_limits=True, device=..., n_estimators=..., random_state=...)
model.fit(X_train, y_train)          # full training context
probs = model.predict_proba(X_test)[:, 1]
```

**Fine-tuned arm** — the inference context is explicitly subsampled to `context_samples`:

```python
eval_cfg = {**cfg, "inference_config": {"SUBSAMPLE_SAMPLES": context_samples}}   # 64 or 128
eval_model = clone_model_for_evaluation(model, eval_cfg, TabPFNClassifier)
eval_model.fit(X_train, y_train)     # context subsampled to 64 (R2) / 128 (R3)
probs = eval_model.predict_proba(X_test)[:, 1]
```

So in Round 2 the fine-tuned arm predicted the test set with **64 rows of inference context**,
while the raw arm it was compared against used the **full training split** (~800 rows). The delta
therefore measures *the effect of a ~10x smaller inference context* at least as much as it
measures fine-tuning.

### 3.1 The fingerprint that supports this reading

| Round | Inference context (fine-tuned arm) | Δ ROC AUC |
|---|---|---|
| R2 | 64 | **−0.1021** |
| R3 | 128 | **−0.0821** |

The only material change between the rounds was doubling the context — and the deficit shrank by
+0.02. The historic write-up interpreted this as "diminishing returns on fine-tuning budget", but
it is equally consistent with: **the fine-tuned arm was handicapped by its context, and halving
the handicap halved the deficit.** TabPFN's accuracy is strongly context-dependent — the project's
own size sweep (§13 of the analysis file) established the model's sensitivity to training-set size
— so a 10x context reduction is a large, uncontrolled effect.

**This is a confounded comparison.** That does not prove fine-tuning helps; it does mean the
historic negative verdict is not, on its own, a fair test of fine-tuning. The deficit may be
partly (or largely) a context artefact.

### 3.2 Why this matters more than the other limitations

The other limitations (§2, §4) make the historic result *small and dated*. This one makes it
**uninterpretable in the direction it was read**: a comparison in which one arm silently received
a much smaller inference budget cannot be used to conclude that fine-tuning degrades performance —
which is precisely the conclusion that was drawn and actioned.

---

## 4. Further methodological limitations

1. **Hand-rolled training loop over a private API.** The loop reaches into `_initialize_model_variables()`,
   drives `fit_from_preprocessed` by hand, and constructs a bespoke evaluation model. This is the
   same class of code that produced **two silent defects in our own R1** arm: a model left in a
   batched-executor state that could not serve a standard prediction, and an optimiser construction
   behind a bare exception handler that could leave the loop taking **no gradient step at all**
   while still reporting metrics. A hand-rolled loop is not wrong in itself, but it is exactly where
   this failure mode lives, and nothing in the historic record verifies the loop took the steps it
   was supposed to.
2. **A minimal optimiser configuration.** Vanilla `Adam` at learning rate 1e-5, batch size 1, no
   weight decay, no learning-rate schedule, no validation split and no early stopping. Compare the
   modern shipped trainer, which uses AdamW, weight decay, a warmup schedule, a held-out validation
   split and best-checkpoint selection.
3. **A tiny effective fine-tune.** `batch_size=1`, chunk size capped at `context_samples`, and
   `max_finetune_steps` of 3 or 5. The arm trained on a few hundred pooled rows for a handful of
   steps. If fine-tuning needs more than that to show an effect, this design could not have found
   one — and the historic write-up acknowledges the budget "may be too small to express any real
   benefit".
4. **Skips inside the loop.** Batches whose context and query class sets differ are skipped. With
   `batch_size=1` that can reduce the number of gradient steps actually taken, so the nominal
   `max_finetune_steps` is an upper bound, not a guarantee.
5. **No positive control anywhere.** Fine-tuning has **never been shown to improve performance on
   any dataset in this project** — not in-domain, not transfer. A negative transfer result is
   uninformative when the mechanism has never once demonstrated a gain: we cannot distinguish
   "fine-tuning does not transfer" from "this fine-tuning setup does not work at all".
6. **Undocumented feature and target harmonisation.** The pooling rounds fine-tuned across datasets
   with different schemas (86 / 11 / 19 / 23 columns in the datasets we would pool today) and
   different target definitions. How those were reconciled is not documented, so a negative result
   could equally reflect an incoherent pooled training task.
7. **No arm-level audit artefacts.** Per-arm effective configuration, predictions and fitted models
   were not retained, so the historic results cannot be recomputed or re-examined at the level
   needed to test the §3 hypothesis directly.
8. **The two pool policies were indistinguishable** (6/12 wins each). With the comparison
   confounded, the policy question was never really answered either.

---

## 5. What the historic work still gives us — do not discard it

The verdict is not usable, but the **machinery** is, and several findings stand:

- **The LODO design itself** — one model fine-tuned on other datasets, evaluated on a target that
  was not in the pool. This is the right design for the question, and it is already specified.
- **Pool-policy machinery and its logging fields** — `pool_policy`, `pool_k`, `selected_pool_datasets`,
  similarity distances. The instrumentation existed and was better than R1's.
- **A pre-registered decision rule in the right shape** — a pooled, multi-metric, seed-stability
  criterion, specified *before* the run.
- **Partially usable evidence on the fine-tune lever**: the deficit did not grow with budget, and
  calibration stayed stable as budget increased, so whatever was happening was not simple
  overfitting onto the pool.
- **Fully usable evidence on the model's sensitivity to data scale** (§13 size sweep): TabPFN leads
  on log loss at 1K and 5K rows against all three GBDT families. The baseline a fine-tuned arm must
  beat is strong, and its context sensitivity is documented.
- **A closed line of enquiry**: `n_estimators` as an accuracy lever is settled — do not re-chase it.

---

## 6. What a *fair* test requires

Ordered by how much each one protects the result. These are the requirements the next stage should
be judged against.

### 6.1 Control the inference budget — the single most important correction

Both arms must predict the test set with an **identical, recorded inference context**. Either:

- **fix it equal** (e.g. both arms at the same context size), which gives a clean fine-tuning
  contrast; or
- **vary it as an explicit factor**, so context and fine-tuning are estimated separately rather
  than confounded.

Either way, the effective inference context per arm must be recorded in the run manifest. Nothing
in the historic record asserts the arms matched, and that omission is what produced the unusable
comparison.

### 6.2 Establish a positive control first

Before asking whether fine-tuning *transfers*, demonstrate that it can **help at all** — an
in-domain fine-tune, at adequate scale and budget, with matched context, showing a repeated
positive delta over raw TabPFN. If the mechanism cannot produce a gain where it is most favoured,
a transfer null tells us nothing. This inverts the historic ordering, which went to transfer
before ever establishing a positive in-domain result.

### 6.3 Use compute to remove the scale ceiling

This is what has changed. The historic runs were CPU-bound at 800/400 rows with a handful of steps.
With GPU available, the fair test can:

- train on **full target datasets** (up to 53K rows) rather than 800;
- use a **materially larger pool** and a batch size above 1;
- run **more steps and a larger context** without a CPU ceiling;
- run **multiple seeds and folds** so the delta has a distribution;
- retain **per-arm predictions and fitted weights** so results are auditable.

### 6.4 Use the shipped trainer, not a hand-rolled loop

`tabpfn.finetuning.finetuned_classifier.FinetunedTabPFNClassifier` — AdamW, weight decay, a warmup
schedule, an internal validation split and best-checkpoint selection, all maintained by the library
and verified in `FINE_TUNING_METHOD.md`. The historic loop re-implemented a worse version of this
against an API that no longer exists.

### 6.5 Add the controls that separate the competing explanations

| Control | What it rules out |
|---|---|
| **Matched-context raw arm** | the §3 confound |
| **In-domain fine-tune** (positive control) | "the fine-tuning setup simply doesn't work" |
| **Random-pool fine-tune** (same size, no domain relationship) | "fine-tuning degrades, regardless of pool" vs "wrong pool data degrades" |
| **Same-schema pool** | the harmonisation confound |
| **Raw + in-domain at full context** | context effects masquerading as fine-tuning effects |

### 6.6 Record enough to audit

The manifest specified in `NEXT_STAGE_PROPOSAL.md` §4.2: dataset content hashes, split indices and
hash, pool contents, **per-arm effective configuration including the inference context**, per-arm
predictions, model hashes, cost, and an in-code assertion that the target is absent from its own
pool.

### 6.7 Pre-register the decision rule and the power

Fix the rule and the required effect size before the run; size the test split from a power
calculation. R1's coil2000 test set carried a 95% CI width of 0.118 on ROC AUC — wider than any
effect the historic study was trying to detect, which means the historic design could not have
resolved a realistic fine-tuning gain even had one existed.

---

## 7. Verdict

| Claim | Status |
|---|---|
| "Fine-tuning has been tested and does not help." | **Not supported.** The principal comparison was confounded by an unequal inference context, and the fine-tuning path was hand-rolled against a legacy API at a scale far below where an effect would be expected. |
| "Fine-tuning improves insurance prediction." | **Not supported either.** Nothing has ever demonstrated a positive result, and there is still no positive control. |
| "The historic machinery is reusable." | **Yes** — LODO design, pool policies, logging fields, decision-rule shape, and the size-sweep evidence all carry forward. |
| "The historic result is a fair test of fine-tuning." | **No.** That is the finding of this document, and the reason the next stage must be designed from the fairness requirements in §6 rather than by scaling the historic run as-is. |

**Bottom line.** The historic work was CPU-limited and small-scale, and its headline comparison is
confounded. It should be treated as *an untested question plus a reusable design*, not as evidence
that fine-tuning does not work. With compute now available, the fair test is: **match the inference
budget between arms, establish a positive in-domain control first, use the shipped trainer, scale to
the full datasets, and record everything** — then ask whether a single model fine-tuned on other
datasets transfers to one it has never seen.
