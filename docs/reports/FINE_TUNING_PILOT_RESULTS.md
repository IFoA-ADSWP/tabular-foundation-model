# Fine-Tuning Pilot — Pre-Fine-Tuning Baseline Results

> **Status:** complete. All four arms — `A_raw`, `B_in_domain`, `E_glm`, `F_catboost` — are measured on all four datasets. **Arm B ran successfully for the first time on 2026-09-12** (NVIDIA L40S; see §5b–5c) after its long-standing "does not fit" diagnosis was shown to be wrong. The research question in `PRE_FINETUNING_INVESTIGATIONS.md` is answered for the configuration tested: **a 3-pass in-domain fine-tune does not reliably beat raw TabPFN** (deltas ≤0.010, one negative), while raw TabPFN's advantage over the actuarial baselines is much larger (+0.007 to +0.068). Single seed, single split, 3 fine-tune passes — see §5c for the scope limits and §6 for the caveats.

## Version stamp

| Field | Value |
| --- | --- |
| Run date | 2026-09-12, 09:18:03 → 09:20:56 UTC (12 runs; ~3 min compute after ~90 s setup) |
| TabPFN weights | **`tabpfn-v3-classifier-v3_default.ckpt`** (212.8 MB) |
| TabPFN package | `tabpfn 8.5.0` |
| Device | CPU (Colab free tier, 12 GB, no swap) — `Device: cpu`, no GPU |
| Seed | 42 (single) |
| Branch / commit | `finetune-v2`, launcher `eb45e0e` |

Weights ID evidenced from the resolved cache file on the VM (`/root/.cache/tabpfn/tabpfn-v3-classifier-v3_default.ckpt`), **not** from the run manifests — `checkpoints` recording was added after this run and applies to future runs only. See §6.

`v3_default` is the repo's current citable line per `docs/MODEL_VERSIONS.md`, so these numbers sit on the same model line as the frontier benchmark work rather than the frozen v2-era tables.

## 1. Purpose

`PRE_FINETUNING_INVESTIGATIONS.md` frames the goal as: does fine-tuning TabPFN on insurance data improve performance on held-out insurance tasks, versus raw TabPFN and actuarial baselines?

Arm A (raw TabPFN) is the "no fine-tuning" reference. Without it the B-vs-A delta — the actual quantity of interest — has no denominator. This report supplies A, E and F.

## 2. Configuration

```python
PILOT_CONFIG = {
    "context_samples": 64,
    "max_finetune_steps": 3,
    "n_estimators": 2,
    "learning_rate": 1e-5,
    "fit_mode": "batched",
}
```

| Setting | Value |
| --- | --- |
| Train / test rows | 2,000 / 1,000 (stratified, `random_state=42`) |
| Preprocessing | `pd.get_dummies(drop_first=False)`, `fillna(0)`, `StandardScaler` |
| Datasets | `coil2000`, `uslapseagent`, `eudirectlapse`, `spanish_motor_lapse` |
| Max rows read | 3,500 per dataset |

Arms (from `ARMS` in `scripts/run_pilot.py`):

| Arm | Definition |
| --- | --- |
| `A_raw` | Raw TabPFN classifier, no fine-tuning |
| `B_in_domain` | TabPFN fine-tuned on the same dataset's training split |
| `E_glm` | Logistic regression on scaled features (GLM baseline) |
| `F_catboost` | CatBoost, 200 iterations (GBDT baseline) |

## 3. Results

ROC AUC is the primary metric; Brier and PR AUC reported alongside because a ROC-only win can hide calibration or ranking regressions.

| dataset | arm | ROC AUC | Brier | PR AUC | secs |
| --- | --- | --- | --- | --- | --- |
| coil2000 | **A_raw** | **0.7679** | **0.0507** | **0.1882** | 83.5 |
| coil2000 | E_glm | 0.6830 | 0.0559 | 0.1307 | 0.03 |
| coil2000 | F_catboost | 0.6993 | 0.0516 | 0.1753 | 3.2 |
| eudirectlapse | **A_raw** | **0.5879** | **0.1137** | **0.1939** | 68.9 |
| eudirectlapse | E_glm | 0.5744 | 0.1163 | 0.1601 | 0.02 |
| eudirectlapse | F_catboost | 0.5738 | 0.1151 | 0.1830 | 0.6 |
| spanish_motor_lapse | **A_raw** | **0.7230** | **0.1980** | **0.5699** | 54.2 |
| spanish_motor_lapse | E_glm | 0.6166 | 0.2222 | 0.4469 | 0.01 |
| spanish_motor_lapse | F_catboost | 0.7114 | 0.2015 | 0.5412 | 0.7 |
| uslapseagent | **A_raw** | **0.9360** | **0.0869** | **0.8359** | 33.8 |
| uslapseagent | E_glm | 0.9271 | 0.0910 | 0.8172 | 0.01 |
| uslapseagent | F_catboost | 0.9297 | 0.0934 | 0.8293 | 0.5 |

Deltas (A minus baseline; positive ROC/Brier-improvement means TabPFN better):

| dataset | ROC A−E | ROC A−F | Brier A−E | Brier A−F |
| --- | --- | --- | --- | --- |
| coil2000 | +0.0849 | +0.0686 | −0.0052 | −0.0009 |
| eudirectlapse | +0.0136 | +0.0141 | −0.0026 | −0.0014 |
| spanish_motor_lapse | +0.1065 | +0.0116 | −0.0242 | −0.0035 |
| uslapseagent | +0.0090 | +0.0064 | −0.0041 | −0.0065 |

## 4. Findings

1. **Raw TabPFN is first on all four datasets, on all three metrics.** The win is not a ROC artefact — Brier and PR AUC agree in every cell, so it is neither a ranking-only nor a calibration-only effect.

2. **The margins track the complexity diagnostic.** `spanish_motor_lapse` (+0.106 vs GLM) and `coil2000` (+0.085) show wide gaps; `eudirectlapse` is the narrowest at **+0.014**. The earlier complexity diagnostic classed `eudirectlapse` as `LINEAR — no non-linear structure for TabPFN to exploit`, and `docs/MODEL_VERSIONS.md` already records `eudirectlapse` as a *"genuine classification loss"* with additive structure. Independent methods converging on the same dataset being the weakest case for TabPFN is a consistency check, not a surprise — but it also means `eudirectlapse` is where fine-tuning has the least headroom to demonstrate value.

3. **`uslapseagent` is a near-tie** (+0.009 vs GLM) despite the highest absolute AUC (0.936). High absolute performance leaves little room for a delta, so this dataset cannot discriminate between methods well.

4. **Arm A is the entire compute cost.** 34–83 s per dataset versus sub-second for E and 0.5–3.2 s for F. Any future grid should be sized on arm A, and note A does not necessarily speed up proportionally on GPU (it is not FLOP-bound in the same way as training).

## 4b. GPU re-run of arm A — device variance, and what the artifact now holds

Arm A was re-run on a rented GPU on **2026-09-12 17:06 UTC**. The pipeline is now
proven end to end (provisioning, transport, licence, arm loop, artifact return), and
the GPU numbers differ slightly from the CPU table in §3:

| dataset | A_raw CPU (§3) | A_raw GPU | delta |
| --- | --- | --- | --- |
| coil2000 | 0.7679 | **0.7673** | −0.0006 |
| eudirectlapse | 0.5879 | **0.5872** | −0.0007 |
| spanish_motor_lapse | 0.7230 | **0.7239** | +0.0009 |
| uslapseagent | 0.9360 | **0.9355** | −0.0005 |

Same seed, same config, same checkpoint — so this is **device-dependent
floating-point**, not a behavioural change. It matters only for citation: quote
one device's numbers, and say which. The direction of every §4 conclusion is
unaffected (all four deltas are ~1e-3 against margins of 6e-3 to 1e-1).

Provenance recorded by the GPU run itself: `tabpfn 8.5.0`, `torch 2.7.0+cu128`,
`python 3.11.12`, device `cuda` on an **NVIDIA RTX PRO 5000 Blackwell**,
checkpoint `tabpfn-v3-classifier-v3_default.ckpt`.

**Caution — `outputs/gpu-pilot/` now mixes provenance.** The box clones the repo,
so the committed CPU outputs are already on disk, and the aggregate re-reads them.
The file therefore holds four GPU `A_raw` rows (17:06) alongside four CPU `E_glm`
and four CPU `F_catboost` rows (09:20). That is benign here — GLM and CatBoost are
CPU models and device cannot affect them — but it is the same failure mode that
once printed a complete results table made entirely of stale numbers. Read the
`device`, `timestamp` and `versions` columns before trusting any row.

## 5. Arm B: not measured, and why

Arm B has never completed a run. On the 12 GB CPU runtime it was killed by the kernel OOM killer:

```
Memory cgroup out of memory: Killed process 27691 (python3)
  total-vm:13561664kB  anon-rss:11824532kB
Swap: 0
```

~11.8 GB of a 12 GB cgroup with no swap. This is a **hardware ceiling, not a bug**.

The failure mode was worse than a normal error: the kernel SIGKILLs the interpreter, so the per-arm `except Exception` in `run_single_dataset` could never fire. No traceback was printed and the three remaining arms never ran — only `coil2000/A_raw` survived. That is the systemic issue addressed by the fix below.

**Fix applied** (commit `eb45e0e`, *not* in effect for this run's numbers):

- each arm now runs in its own subprocess, so a SIGKILL costs one arm rather than the batch;
- the launcher reports `rc` per arm, so a signal death is visible instead of silent;
- `--arms` on the runner and an `ARMS` env var on the launcher allow skipping arms a VM cannot hold.

**Consequence:** the B-vs-A delta — the primary quantity of interest — remains unmeasured. It requires the GPU runtime, and it is not guaranteed to fit there either: 11.8 GB was *system RAM* usage, and the T4 offers 16 GB *VRAM*, which is a different budget. `TabPFNClassifier` accepts a `memory_saving_mode` argument (confirmed present in 8.5.0) if trimming is needed, but enabling it changes the recorded config and must be treated as a deliberate, documented deviation rather than a silent one.

### 5b. Arm B on GPU: memory was never the blocker — CORRECTION

**The paragraph above is superseded in its reasoning.** Arm B ran on a rented GPU on
**2026-09-12 18:10 UTC** and did not come close to a memory limit:

```
########## ARM B_in_domain ##########
Device: cuda        GPU: NVIDIA RTX PRO 5000 Blackwell        VRAM: 50.8 GB
--- coil2000 ---            ERROR (5.1s)
--- uslapseagent ---        ERROR (2.2s)
--- eudirectlapse ---       ERROR (2.4s)
--- spanish_motor_lapse --- ERROR (2.0s)
```

```
Invalid forward pass: Bad combination of inference mode (use_inference_mode=True),
input X, or executor type (InferenceEngineBatchedNoPreprocessing).
```

Every dataset failed identically, in seconds, with **50.8 GB free**. The CPU OOM
recorded above was a real ceiling *for that runtime*; it was never the binding
constraint, and "arm B does not fit" is not supported by the evidence. Arm B is a
**deterministic code defect**, reproducible on demand and cheap to iterate on.

Two defects, both hidden by the same anti-pattern:

1. **The call sequence.** The hand-rolled loop left the model in batched-executor
   mode and then called standard `predict_proba`, which that executor cannot serve.
   Arm A survives the equivalent situation because TabPFN auto-switches it back
   ("*The model was in 'batched' mode, likely after finetuning...*"); arm B had no
   such reset.
2. **A silent no-op training loop.** `optimizer` was built only `if hasattr(clf,
   "model_")`, and `model_` is created by `_initialize_model_variables()`, itself
   called inside a bare `except Exception: pass`. Had that failed, `optimizer` would
   be `None`, the loop would call the fit method but take **no gradient step**, and
   the arm would have reported numbers for a model that was never fine-tuned. The
   loss/backward/step block was separately wrapped in `except Exception: pass`.

**Fix applied:** arm B now uses the fine-tuner 8.5.0 ships —
`tabpfn.finetuning.finetuned_classifier.FinetunedTabPFNClassifier` — instead of
driving the model by hand. Deviating from the library's own trainer is precisely
what made both defects invisible. Recorded config deviation: `max_finetune_steps`
maps to the trainer's `epochs`, `n_estimators` to `n_estimators_finetune`, and
`context_samples` is not applied (the shipped trainer subsamples via
`n_finetune_ctx_plus_query_samples`, default 50000). `tqdm`, which the finetuning
package imports, is a declared tabpfn dependency and so is already installed.

**Result (2026-09-12 20:16-20:19 UTC, NVIDIA L40S):** the fix worked and arm B
completed on all four datasets — the first successful run of this arm anywhere.

### 5c. Arm B measured — the B-vs-A delta

`A_raw` and `B_in_domain` ran **on the same device, in the same run, with the same
seed**, so this is a like-for-like comparison:

| dataset | A_raw | B_in_domain | delta | |
| --- | --- | --- | --- | --- |
| coil2000 | 0.7675 | **0.7690** | +0.0014 | B better |
| eudirectlapse | 0.5881 | **0.5976** | +0.0095 | B better |
| spanish_motor_lapse | 0.7233 | **0.7272** | +0.0039 | B better |
| uslapseagent | **0.9363** | 0.9355 | −0.0008 | A better |

Full arm-B metrics (ROC / Brier / PR AUC / seconds):

| dataset | ROC | Brier | PR AUC | secs |
| --- | --- | --- | --- | --- |
| coil2000 | 0.7690 | 0.0509 | 0.1933 | 35.7 |
| eudirectlapse | 0.5976 | 0.1133 | 0.1982 | 36.4 |
| spanish_motor_lapse | 0.7272 | 0.1967 | 0.5791 | 18.3 |
| uslapseagent | 0.9355 | 0.0870 | 0.8375 | 26.6 |

**Finding: a 3-pass in-domain fine-tune does not reliably beat raw TabPFN.** It wins on
three datasets and loses on the fourth, and every delta is ≤0.010 — within the range
§6.4 already flags as movable by a different split. At a single seed this is directional
evidence of *no meaningful effect*, not evidence of a small one.

**What this bounds, and what it does not.** The fine-tune was **3 passes**
(`max_finetune_steps=3` mapped to the shipped trainer's `epochs`) with the trainer's default
subsampling, one seed, and ROC AUC on four classification datasets. So this shows a *small*
GPU fine-tune buys nothing measurable — it does not show that no fine-tuning configuration
could help. A proposal to go further should name which of those limits it is changing.

Worth separating from the master report's §12 ruling, which is a different question:
that one was about which setup artifacts explain v1's losses, and its fine-tuning evidence
was CPU small-step work (§2.3, §5.2). This run extends the "negligible" finding into the GPU
regime rather than re-testing §12.

**The effect that does exist is TabPFN-versus-baselines, and it is much larger:**

| dataset | A_raw | best baseline | TabPFN gain | fine-tuning gain |
| --- | --- | --- | --- | --- |
| coil2000 | 0.7675 | 0.6993 | **+0.068** | +0.001 |
| eudirectlapse | 0.5881 | 0.5744 | +0.014 | +0.010 |
| spanish_motor_lapse | 0.7233 | 0.7114 | +0.012 | +0.004 |
| uslapseagent | 0.9363 | 0.9297 | +0.007 | −0.001 |

Fine-tuning therefore buys little and costs a lot: arm B used **117 s** of GPU
across the four datasets against arm A's **41 s**, roughly 3x, for ≤0.01 ROC.

**Caveats that must travel with this:** single seed, single split, no paired
significance testing, and no confidence intervals. The two near-ties
(`uslapseagent`, `eudirectlapse`) are the ones where the ordering is least secure.
A multi-seed repeat with paired tests is the obvious next step before this is
treated as settled — but the burden of proof now sits with the claim that
fine-tuning *helps*, not with the claim that it doesn't.

## 5d. Constraints, statistical validity, and what may have contributed to the result

This section exists because the pilot is a **reduced exercise**, not the full fine-tuning
study. Everything below is stated so a reader can judge the result without having to
reconstruct the design, and so the constraints are on the record *before* the numbers are
quoted anywhere.

### 5d.1 What the pilot was for

Three purposes, and only three:

1. prove the GPU pipeline works end to end (provision, transport, return artifacts, tear down);
2. sense-check the fine-tuning code;
3. produce **reusable** scripts rather than a one-off notebook session.

It was **not** designed to settle whether fine-tuning TabPFN is worthwhile in general, and
it should not be cited for that. The configuration is small by construction (§5d.4).

### 5d.2 Which datasets were fine-tuned, and what was evaluated on what

**All four datasets were fine-tuned, and each was evaluated on itself.** There is no
held-out dataset anywhere in the pilot:

| Dataset | Fine-tuned on | Evaluated on | Cross-dataset transfer? |
| --- | --- | --- | --- |
| `coil2000` | 2,000-row train split of coil2000 | the held-out 1,000 rows of coil2000 | none |
| `uslapseagent` | 2,000-row train split of uslapseagent | the held-out 1,000 rows of uslapseagent | none |
| `eudirectlapse` | 2,000-row train split of eudirectlapse | the held-out 1,000 rows of eudirectlapse | none |
| `spanish_motor_lapse` | 2,000-row train split of spanish_motor_lapse | the held-out 1,000 rows of spanish_motor_lapse | none |

So the design is **in-domain only**. Arm B learns from the same dataset it is scored on,
separated by a random split rather than by dataset. No arm fine-tunes on one set of datasets
and evaluates on an unseen one — which is the design the deployment question actually needs
(§5d.5).

The split mechanics are sound and identical for every arm: `train_test_split(test_size=1000,
random_state=42, stratify=y)` on the loaded frame, a 2,000-row train cap taken with a second
stratified split, and a `StandardScaler` **fit on train only** then applied to test. No
target column survives into the features (`drop(columns=[target_col])`). There is no test-set
leakage.

### 5d.3 The data actually used

`load_dataset` caps every dataset at 3,500 rows (`TRAIN_SIZE + TEST_SIZE + 500`) using
`df.sample(n=3500, random_state=42)`:

| Dataset | Rows available | Rows used | Discarded | Positive rate (full) | Positive rate (sample) | Test positives |
| --- | --- | --- | --- | --- | --- | --- |
| `coil2000` | 9,822 | 3,500 | 64% | 5.97% | 5.74% | 57 |
| `uslapseagent` | 29,317 | 3,500 | 88% | 37.86% | 36.86% | 369 |
| `eudirectlapse` | 23,060 | 3,500 | 85% | 12.81% | 13.17% | 132 |
| `spanish_motor_lapse` | 53,502 | 3,500 | 93% | 35.44% | 35.40% | 354 |

Three consequences worth stating plainly:

- **Between 64% and 93% of every dataset was never seen.** The pilot's result is a
  small-data result about a slice, not about the dataset.
- **The subsample is not stratified.** `df.sample` is uniform, so the sampled positive rate
  can drift from the full-population rate (coil2000 5.97% → 5.74%); the *split* that follows
  is stratified, but the drift is then baked into both arms. Small here, but it belongs in
  the deviation register because it means the pilot's class balance is not exactly the
  dataset's.
- **Of the 3,500 rows, 2,000 train / 1,000 test / 500 are discarded unused.**

### 5d.4 The effective configuration of each arm — and where it differs from what is recorded

| | `A_raw` | `B_in_domain` |
| --- | --- | --- |
| Training data it sees | all 2,000 train rows in the context | ~1,800 rows trained on (the trainer reserves 10% for validation — verified default `validation_split_ratio=0.1`) |
| Adaptation | none — conditioning only | 3 gradient passes |
| Estimators | `n_estimators=2` | `n_estimators_finetune=2` |
| Learning rate | n/a | 1e-5 |
| Fit mode | `batched` | n/a (library trainer) |
| Precision | `inference_precision=float32` | library default |
| Early stopping | n/a | **on** (library default `early_stopping=True`) — selecting on a 200-row validation slice, and largely inert at 3 epochs |

**Deviation register — recorded config vs effective config:**

| Recorded in `PILOT_CONFIG` | Actually used? | Note |
| --- | --- | --- |
| `context_samples: 64` | **by neither arm** | `A_raw` fits on all 2,000 rows; nothing caps the context at 64. A reader of the record would wrongly conclude the context was 64 rows. |
| `max_finetune_steps: 3` | yes, as `epochs=3` | renamed to the library trainer's parameter |
| `n_estimators: 2` | yes | becomes `n_estimators_finetune=2` for arm B |
| `learning_rate: 1e-5` | yes | arm B only |
| `fit_mode: batched` | arm A only | not a parameter of the library trainer |

**Library defaults that were *not* overridden** (verified in `tabpfn==8.5.0`, the version that
ran on the box — these are part of the effective configuration whether or not they were
chosen):

| Default | Value | Effect here |
| --- | --- | --- |
| `validation_split_ratio` | `0.1` | ~200 of the 2,000 train rows reserved as validation; ~1,800 trained on |
| `early_stopping` | `True` | Model selection on a 200-row slice; with only 3 epochs it can barely engage |
| `n_finetune_ctx_query_samples` | `50_000` | **Inert at this data size** — only ~1,800 rows are available, so the cap never binds |
| `finetune_ctx_query_split_ratio` | `0.2` | Governs the context/query split within each fine-tuning batch |

The sub-sampling default is worth calling out explicitly, because it is what `context_samples`
was evidently intended to control: the effective context is set by the library's
`n_finetune_ctx_query_samples` (50,000), not by the pilot's config, and at ~1,800 rows it does
not bind at all.

The mapping is deliberate, but it was **not recorded per-arm in the run metadata** — the same
`PILOT_CONFIG` is written for every arm, so the metadata currently overstates what arm B
used. This is a provenance defect, not a results defect; fixing it is Lane 1 of the
follow-up.

Also note the arms do not consume identical data: B optimises on ~1,800 rows while A
conditions on 2,000. The comparison is therefore "conditioning vs gradient adaptation on
essentially the same pool", which is a fair question but not the same as "same information,
different method".

### 5d.5 Is it statistically correct to fine-tune on a dataset and then test on the same dataset?

**Internally, yes — with important qualifications. As evidence for the decision the project
faces, no.**

*What is correct.* Fine-tuning on a training split and evaluating on a held-out test split of
the same dataset is a standard in-domain transfer-learning design. The split is stratified,
the scaler is fit on train only, the target never enters the features, and both arms are
scored on **identical test rows**. So the A-vs-B comparison is a valid like-for-like
measurement of "does 3 passes of in-domain fine-tuning change held-out performance on this
dataset".

*Why that is nevertheless the weakest form of the claim:*

1. **In-domain evaluation is optimistic by construction.** The model is adapted to, and
   scored on, the same population. It can absorb that dataset's idiosyncrasies — sampling
   quirks, cohort effects, encodings — which will not transfer to a new portfolio. The
   measured gain is an **upper bound** on what deployment would show, and it is only
   available at all if you already hold labelled data from the target.
2. **The design cannot test transfer.** The practical question is: can we adapt once and
   deploy on a *new* dataset? That requires a **cross-dataset** design — fine-tune on source
   datasets, evaluate on a target dataset never seen during fine-tuning. The pilot has no
   such arm, so transfer is entirely untested (§5d.2).
3. **The comparison does not isolate "fine-tuning" from "the target's data being used
   differently".** B optimises on the training split; A only conditions on it. That is a
   model-adaptation contrast, not evidence that fine-tuning helps in practice.

*What would make it statistically defensible:* multiple seeds or folds so the delta has a
distribution rather than a point; a **paired** test on the shared test rows (the pilot
already has the necessary structure, but see the evidence gap in §5d.9); a cross-dataset
transfer arm; ideally an out-of-time or external holdout; and a decision rule fixed in
advance stating what effect size would count as a win given the noise floor in §5d.6.

### 5d.6 What the test sets can actually resolve

Individual A_raw AUCs with bootstrap 95% CIs, computed from the saved predictions:

| Dataset | Test n | Test positives | AUC | 95% CI | CI width |
| --- | --- | --- | --- | --- | --- |
| `coil2000` | 1,000 | 57 | 0.7679 | [0.7076, 0.8256] | **0.1180** |
| `uslapseagent` | 1,000 | 369 | 0.9360 | [0.9202, 0.9516] | 0.0314 |
| `eudirectlapse` | 1,000 | 132 | 0.5879 | [0.5347, 0.6425] | 0.1078 |
| `spanish_motor_lapse` | 1,000 | 354 | 0.7230 | [0.6904, 0.7539] | 0.0634 |

**Every measured A-vs-B delta (0.0014 to 0.0095) is smaller than the sampling error on its
own test set.** On coil2000 the CI is ±0.06 and the delta is +0.0014. The pilot is
underpowered for the effect it set out to measure — it can show the effect is not *large*,
but it cannot show the effect is *zero*.

Because both arms predict the **same test rows**, the paired comparison is the more sensitive
one. Demonstrated here on a pair where row-level data exists (`A_raw` vs `E_glm`):

| Dataset | Unpaired CI width | Paired 95% CI on the delta | Delta | Excludes 0? |
| --- | --- | --- | --- | --- |
| `coil2000` | 0.1180 | [+0.0246, +0.1469] | +0.0849 | **yes** |
| `uslapseagent` | 0.0314 | [+0.0005, +0.0176] | +0.0090 | **yes** |
| `spanish_motor_lapse` | 0.0634 | [+0.0769, +0.1362] | +0.1065 | **yes** |
| `eudirectlapse` | 0.1078 | [−0.0120, +0.0391] | +0.0136 | no |

**TabPFN's advantage over the GLM is a real effect — it excludes zero on three of four
datasets. The fine-tuning effect is roughly an order of magnitude smaller than that**, and
on this footing would very likely fail to clear zero. This is the analysis arm B needs, and
it cannot currently be run (§5d.9).

No multi-seed and no cross-validation was performed, so there is **no estimate of variance**
for any delta: all four are single-split point estimates.

### 5d.7 Factor register — what may have contributed to the observed performance

| Factor | Direction on the result | Controlled? |
| --- | --- | --- |
| Data volume (2,000 train / 1,000 test rows; 64–93% discarded) | Caps how much either arm can learn; sets the noise floor | Deliberate, for cost/speed |
| Class imbalance (coil2000 5.97% positive; 57 test positives) | Widens CIs dramatically; AUC unstable | Uncontrolled |
| Unstratified 3,500-row subsample | Shifts sample positive rate away from population | Uncontrolled |
| Single split, single seed (42) | No variance estimate; the delta is one draw | Uncontrolled |
| Light fine-tune (3 passes, lr 1e-5) | Biases *toward* finding no gain | Deliberate — a small, bounded lever |
| Library trainer's internal 10% validation holdout + early stopping | B trains on ~1,800 rows, not 2,000, and selects on a 200-row slice | Uncontrolled (library defaults) |
| Device / run variance | A_raw read 0.767344 (RTX PRO 5000) and 0.767530 (L40S) across two GPU runs — ~2e-4 of run-to-run spread, present even for the *raw* arm | Partially — A and B shared a device within the decisive run |
| Metric choice (ROC AUC primary) | Ranking-focused; ignores calibration | Deliberate; Brier is also reported |
| No calibration metric on the fine-tuned model | Fine-tuning can distort probabilities; would not be visible here | Gap |
| Feature handling (`get_dummies` on all non-target columns) | One-hot of every categorical, including reference-like fields; no explicit ID/date screening | Uncontrolled |
| Sample size of the *comparison* (one split, one seed) | Cannot distinguish +0.0095 from 0 | Uncontrolled |

### 5d.8 What this pilot can and cannot support

**Can support:**

- the GPU pipeline works end to end and is reproducible by script;
- arm B runs on GPU (it had never completed before) and fits comfortably — 50.8 GB VRAM free;
- on these four datasets, at this data scale, with 3 fine-tune passes, in-domain fine-tuning
  did **not** reliably beat raw TabPFN;
- raw TabPFN beats the GLM/CatBoost baselines on these datasets, and for the GLM comparison
  that advantage is statistically visible under a paired test;
- using the foundation model buys an order of magnitude more than fine-tuning it
  (+0.068 vs +0.001 on coil2000).

**Cannot support:**

- any claim that fine-tuning TabPFN is or is not worthwhile *in general* — the lever tested
  was small, and the claim is scoped to 3 passes on ≤2,000 rows;
- any claim about **transfer** to an unseen dataset — no such arm exists;
- any claim at larger data scale — 64–93% of the data was unused;
- any claim of statistical significance for the fine-tuning deltas — they are inside the
  noise, and there is no variance estimate;
- any deployment-facing claim — in-domain, single-split, ROC-AUC only, no calibration or
  out-of-time assessment.

### 5d.9 Evidence gaps (things that are missing, not things that are wrong)

1. **Arm B has no row-level predictions anywhere.** Every other arm has `predictions.npy`
   on disk; B has none. The box's artifact payload returns `pilot_metrics.parquet` and
   `meta.json` only — per-arm predictions are `.npy` (gitignored) and are not in the payload.
   Consequence: B's numbers can be **read but not recomputed or paired-tested**. The analysis
   in §5d.6 that would settle the question is blocked by this, not by method.
2. **Recorded config ≠ effective config** (§5d.4) — `context_samples` is recorded but unused.
3. **No variance estimate** — one seed, one split.
4. **GPU device is not fixed across `A_raw` runs** — two runs of the same arm on different
   cards differed by ~2e-4.
5. The 500 discarded rows are never accounted for in the output.

### 5d.10 Design changes required before any stronger claim

1. Return per-arm predictions from the box (small, chunked) so results are recomputable.
2. Record the effective per-arm configuration in the run metadata.
3. Multiple seeds, and/or repeated stratified folds, so a delta has a distribution.
4. A **cross-dataset transfer arm** — fine-tune on source datasets, evaluate on a held-out
   target — if the deployment question is the one being asked.
5. Stratify the row subsample, or drop the cap where the data volume allows.
6. Pre-register the decision rule: what delta, at what confidence, counts as a win.
7. Add a calibration metric to the fine-tuned arm.

## 6. Provenance gaps and deviations

State these when citing these numbers.

1. **No `checkpoints` field in these manifests.** The run manifests record `versions.tabpfn = 8.5.0` — the *package*, which `docs/MODEL_VERSIONS.md` explicitly warns is not the model: *"`tabpfn==2.6.0` is the pip package, not the model."* The weights ID above was established after the fact from the VM cache. `_checkpoints()` now records resolved `.ckpt` basenames per run, so future runs carry this automatically.

2. **Package version deviates from the repo pin.** `requirements.txt` pins `tabpfn>=6,<7`; this run used **8.5.0**. Weights (`v3_default`) and fine-tuning API were verified compatible, but the package major differs from the repo's declared pin, so arm B's behaviour under 8.5.0 is unverified for the same reason it is unmeasured.

3. **`requirements.txt` is deliberately not used by the launcher.** It pins `numpy>=1.24,<2`, and numpy 1.x has no cp313 wheels, so pip compiles numpy from source (~20 min). The launcher installs named packages and lets pip resolve wheels (`numpy 2.1.3` in this run).

4. **Single seed, single split.** Seed 42, one 2,000/1,000 stratified split, no folds and no confidence intervals. Differences of ~0.01 ( `uslapseagent`, `eudirectlapse` ) are within the range a different split could plausibly move; treat those two rows as directional only. No paired significance testing has been done.

5. **Reported to 4 dp with no uncertainty.** Read as point estimates, not as separated effects.

## 7. What would change the conclusion

- Arm B on GPU **with the shipped `FinetunedTabPFNClassifier`** — the fix is in the
  code (§5b) but has not yet run; the previous GPU attempt failed on a code defect,
  not on memory, so this is now a matter of one verification run.
- Multi-seed replication and paired tests, particularly before claiming anything about the two near-ties.
- Confirming that the dataset pipeline's row cap (3,500) interacts with `eudirectlapse`'s 23k+ rows, which was flagged in the design review as a sizing risk.

## Source Workbooks

- `scripts/run_pilot.py` — pilot runner (arms, config, per-run persistence)
- `scripts/colab_helpers/launch_pilot.sh` — detached Colab launch (commit `eb45e0e`)
- `scripts/colab_helpers/poll_pilot.py` — remote log poll
- `scripts/colab_helpers/export_predictions.py` — packs the per-run `.npy` outputs into the committed predictions parquet (needed because `.gitignore` excludes `*.npy`)

## Evidence Files

- `outputs/finetune/pilot/pilot_metrics.parquet` — aggregated metrics (12 rows)
- `outputs/finetune/pilot/pilot_predictions.parquet` — per-row `y_true` / `y_prob` for all 12 runs (12,000 rows), so metrics can be recomputed or added to without re-running arm A. Verified to reproduce every ROC AUC and Brier in §3 to 1e-9
- `outputs/finetune/pilot/<dataset>/<arm>/meta.json` — per-run config, versions, device, timings

> **Not committed:** the runner's per-run `predictions.npy` / `ground_truth.npy`. `.gitignore:139` excludes `*.npy` repo-wide; `pilot_predictions.parquet` above is the committed equivalent, and the `.npy` originals remain on the run VM only.
