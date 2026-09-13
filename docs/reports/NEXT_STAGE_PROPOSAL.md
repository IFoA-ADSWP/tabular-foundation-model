# Next-Stage Proposal — A Single Fine-Tuned Model Tested on an Unseen Dataset

> Date: 2026-09-12 | **Status: PROPOSAL — awaiting team confirmation. Nothing here is approved,
> funded or scheduled; no GPU spend is authorised by this document.**
> Related: #22, `FINE_TUNING_EXPERIMENT_DESIGN.md`, `CLASSIFIER_HOMOGENEITY_HYPOTHESIS_METHOD.md`,
> `SMOKE_TEST_SCOPE.md`, `FINE_TUNING_PILOT_RESULTS.md`, `FINE_TUNING_METHOD.md`
>
> **Read §2 before §5.** The transfer experiment this document proposes has already been designed
> and run twice — on the v2 API — and came out strongly negative. That changes what the next stage
> should be, and how it should be justified.

---

## 1. Purpose and status

R1 (`SMOKE_TEST_SCOPE.md`) proved the GPU pipeline works and sensibly checked the fine-tuning
code. This document proposes the **next stage**: a scaled experiment whose objective is the one
R1 could not reach —

> **a single fine-tuned model, evaluated on a dataset it was never trained on.**

That is the leave-one-dataset-out (LODO) design. Everything below is a proposal for the team:
the design, the scale options, the audit/data-capture requirements, and the decisions we need
from the team before any run.

---

## 2. What the historic work already attempted — and why it changes the proposal

> **Read `HISTORIC_FINETUNING_APPRAISAL.md` alongside this section.** The historic study reached a
> negative verdict, but that appraisal shows **the comparison was confounded**: the fine-tuned arm
> was evaluated with a subsampled inference context (64 then 128 rows) while the raw arm used the
> full training split — and the deficit shrank as the handicap was reduced. So the historic result
> is *not* usable evidence that fine-tuning fails; it is an attempt whose design we can now correct.
> This section reports what was run and recorded; the appraisal explains why it should not be read
> as a verdict.

`CLASSIFIER_HOMOGENEITY_HYPOTHESIS_METHOD.md` documents a **completed LODO transfer study**,
run on the v2-era model line in April 2026, on CPU, at small scale. It is the experiment we were
about to propose, and it already has a recorded verdict.

### 2.1 The design (historic)

Fine-tune TabPFN on a **pool of other insurance datasets**, evaluate on a **target dataset that
was not in the pool** — one model per target, evaluated on data it never trained on. Four targets
(`eudirectlapse`, `coil2000`, `ausprivauto0405`, `freMTPL2freq_binary`), three seeds
(42/43/44), two pool policies (`similarity_topk` with k=2, and `mixed_baseline`), target-rows 800,
pool-rows 400 per dataset, `test_size=0.3`. Metrics: ROC AUC, PR AUC, Brier, LogLoss, ECE.

### 2.2 The results (historic) — pooled-negative under both rounds and both policies

| Round | Budget | Policy | Δ ROC AUC | Δ PR AUC | Δ Brier | Δ LogLoss | Rule |
|---|---|---|---|---|---|---|---|
| R2 | context 64, steps 3 | mixed_baseline | **−0.1021** | −0.0502 | +0.0025 | +0.0115 | FAIL |
| R2 | context 64, steps 3 | similarity_topk | **−0.0958** | −0.0489 | +0.0021 | +0.0103 | FAIL |
| R3 | context 128, steps 5 | mixed_baseline | **−0.0821** | −0.0385 | +0.0006 | +0.0036 | FAIL |
| R3 | context 128, steps 5 | similarity_topk | **−0.0811** | −0.0367 | +0.0007 | +0.0045 | FAIL |

The study's own pre-registered rule held: **if Round 3 remained pooled-negative, downgrade the
classifier fine-tuning hypothesis for this dataset family before expanding the data universe.**
Round 3 was pooled-negative, so the recorded recommendation was **DOWNGRADE** — do not scale the
fine-tuning budget further or add datasets.

Three other facts worth carrying:

- **More budget did not rescue it.** Doubling the budget (context 64→128, steps 3→5) improved ΔROC
  by only ~0.02 with diminishing returns. Pooled deltas stayed strongly negative.
- **It is not simple overfitting.** Calibration was *stable* across the budget increase, so the
  problem is a systematic ROC/PR deficit, not variance.
- **Pool policy barely mattered.** Head-to-head, `similarity_topk` beat `mixed_baseline` on ROC in
  6/12 cases and PR in 6/12 — a coin flip. The "homogeneous pools help" hypothesis was not
  supported.

### 2.3 What this means for the proposal — three consequences

1. **The next stage is not "test transfer". It is "re-test the v2 transfer verdict on v3."** The
   LODO design exists, is documented, and has been run. What has *not* been done is any of it on
   the current model line. The historic report carries an explicit version caveat: it was v2-era,
   weights ID unrecorded, and the authors say not to assume the results hold on v2.5/v3.
2. **Our R1 pilot is consistent with it.** R1 found the in-domain fine-tune indistinguishable
   from raw; the historic work found the transfer fine-tune substantially *worse* than raw. Both
   point the same way, which raises the evidential bar for the next run: we need a design that can
   detect a *positive* result if one exists, not one that confirms the expected negative.
3. **In several ways R1 was a step backwards in instrumentation.** The historic pooling rounds
   already used **three seeds**, **paired per-target deltas**, **two pool policies**, **ECD/LogLoss
   calibration metrics**, and logged `pool_policy`, `pool_k`, `selected_pool_datasets` and
   similarity distances. R1 used one seed, no folds, no calibration, and did not record its
   effective per-arm config or return per-arm predictions. The audit work in §4 is largely about
   getting back to — and past — the standard the project already had.

**Honest framing for the team:** this is a *replication on a newer model*, with a design strong
enough to overturn the v2 verdict if that verdict is model-dependent. It is not a first look.

---

## 3. Historic scales, features and protocol — what is relevant

Read to avoid re-deriving settled choices. Sources: `tabpfn_vs_gbdt_baselines_finetuning.md`
(§13 size sweep, §14 frontier benchmark), `tabpfn_finetune_limit_test_plan.md`,
`CLASSIFIER_HOMOGENEITY_HYPOTHESIS_METHOD.md`.

| Dimension | Historic usage | Relevant to us? |
|---|---|---|
| **Train sizes (benchmark)** | 1K / 5K / full (9,822 / 29,317 / 163,212 rows) | **Yes — reuse as the scale ladder.** R1 sat at 2K, inside this range but off-ladder. |
| **Train sizes (pooling)** | target 800 rows, pool 400 rows per dataset | Yes — the precedent is *much smaller* than R1's 2,000. Small pools were sufficient to show the negative. |
| **Folds** | 5 folds, mean ± SE, paired t (df=4), canonical fold files reused across studies | **Yes — the single most valuable inheritance.** R1's one-split design cannot produce a paired test; the canonical folds already exist. |
| **Seeds** | 42/43/44 across the pooling rounds | Yes — reuse for continuity. |
| **Features** | one-hot encoding; median imputation where needed; `StandardScaler` + LogisticRegression for the tuned linear baseline; leak-prone features dropped for bemtl97 | Partly. R1 one-hot-encodes everything with no ID/date screening — worth revisiting. |
| **Metrics** | log loss primary ("the metric an insurer pays on"), plus Brier, ECE, ROC/PR AUC | **Yes.** R1 used ROC AUC primary and reported no calibration metric at all. |
| **Fine-tune config ladder** | context 64/128, n_estimators 2/8, steps 1/3/5 | Yes — R1 used 64/2/3, i.e. the ladder's Round-2 setting. |
| **Ensemble size** | `n_estimators=8` tested and **closed** — bit-identical to the default at these sizes | **No — closed. Do not re-chase.** |
| **Compute** | 163K rows = ~51 min cold fit; small cells ~3 s. TabPFN's cost is compute, not accuracy | Yes — informs rung cost and device choice. |
| **Verdicts** | TabPFN leads log loss at 1K and 5K on every dataset (8/9 cells); ties at 163K. v1's headline losses were a **dataset-size mismatch**, not a model ceiling | Yes — the baseline is strong; this is what a fine-tuned arm must beat. |
| **Ruled out** | CPU-without-support, class imbalance, fine-tuning (§12.4 of the analysis) | Yes — do not re-litigate without new evidence. |

---

## 4. Structural gaps to fix before the next run (audit and data capture)

These are corrections to our own R1 instrumentation. None is a research question; all are
prerequisites, and each corresponds to something that actually went wrong or was missing.

### 4.1 Gaps found in R1

| # | Gap | Consequence |
|---|---|---|
| 1 | Effective **per-arm** config not recorded — the same `PILOT_CONFIG` is written for every arm, including `context_samples: 64`, which neither arm uses | The metadata misdescribes what ran; a reader cannot tell what the fine-tune used |
| 2 | **Per-arm predictions are not returned** from the box (only `pilot_metrics.parquet` + `meta.json`) | Arm B's numbers can be read but not recomputed or paired-tested |
| 3 | **No fine-tuned model saved** (4 models existed only in memory) | Cannot audit, reload or reuse the artefact; no weight hash |
| 4 | **No dataset fingerprint** (row count, sha256, column list) | Cannot prove which data version produced a result |
| 5 | **No split/fold record** (indices or fold assignment, and their hash) | Cannot reproduce the exact split; no basis for paired comparison |
| 6 | **No environment capture** beyond package versions — no GPU model/driver/CUDA, no container image digest, no host/machine id | Runs are not attributable to hardware; device variance is unquantified |
| 7 | `arms` field is not per-run (all ten R1 records show the same value regardless of what ran) | Metadata cannot be used to determine what executed |
| 8 | `bootstrap_rc` is 0 on every run, including runs that failed the preflight | Exit code cannot be used as a success signal |
| 9 | The ledger is written as authoritative rather than derived; a schema change silently misaligned it | Cost/provenance figures were briefly nonsense |
| 10 | **No cost per arm**, only per instance | Cannot price a design decision |
| 11 | **No decision-rule outcome recorded** — the R3 gate was never evaluated against a result | The plan's own gate is not part of the record |
| 12 | **Failed attempts are not first-class records** (six of ten R1 instances produced nothing usable) | Failure rate, cause and wasted spend are invisible in the outputs |

### 4.2 Proposed data-capture contract — a run manifest per run

One immutable JSON per run, written on the box and again on the collecting side, with everything
needed to **recompute the metrics and verify the data version without asking us**:

```
run_id, started_at, finished_at, status, exit_reason
git:      repo, branch, commit_sha, dirty_flag
host:     instance_id, machine_id, host_id, gpu_name, gpu_count, vram_gb,
          driver_version, cuda_version, image_ref, image_digest, cpu_ram_gb
env:      python, torch, numpy, tabpfn, scikit-learn, catboost
datasets: per dataset -> {name, path, sha256, n_rows, n_cols, columns[], positive_rate,
                         target_col, source_version}
split:    per target -> {policy, seed, fold, n_train, n_test, pos_train, pos_test,
                         index_hash, out_of_pool_asserted}
pool:     per target -> {policy, k, selected_datasets[], rows_per_dataset,
                         similarity_distance_mean}          # historic fields, retained
arms:     per arm -> {arm_id, effective_config{...}, passed_params[], defaulted_params[],
                      n_rows_used, n_rows_held_out, device, seconds, metrics{roc_auc, pr_auc,
                      brier, log_loss, ece}, predictions_ref, predictions_sha256,
                      model_ref, model_sha256, cost_usd}
gate:     {rule_id, criteria[], outcome, evaluated_at}
artifacts: per file -> {path, bytes, sha256}
cost:     {dph_total, wall_minutes, est_cost_usd, instance_state_history[]}
```

**Acceptance criteria for the audit schema** (all must hold before the scaled run is authorised):

1. A third party can **recompute every metric from the returned predictions** and match the
   reported values to 1e-9.
2. Every dataset is identified by content hash, so a result can be tied to a data version.
3. Every arm records its **effective** configuration, distinguishing parameters we passed from
   library defaults.
4. The split is reproducible from recorded indices/fold assignment, verified by hash.
5. `out_of_pool_asserted` is true for every LODO run — the **target must provably not be in the
   pool** for that model. This is the single most important integrity check in the LODO design,
   and it should be asserted in code, not by convention.
6. Failed runs are recorded, with cause, and their cost is attributed.
7. The decision rule and its outcome are part of the record.

### 4.3 Data-capture corrections to the runner

- Return **per-arm predictions** for every arm, chunked to respect the 500-character log line cap
  (the mechanism exists and is verified — it is simply not applied to predictions).
- Save the **fine-tuned model weights** where size permits, with a hash; where it does not, record
  the reason and the exact reproduction command.
- Record **per-arm cost** and the instance state history.
- Make the ledger **derived** from the per-run manifests, never authoritative.
- Emit the manifest even on the failure path (the pattern already used for the completion marker).

---

## 5. Proposed scaled experiment (for team confirmation)

### 5.1 Objective

For each target dataset, fine-tune **one** model on a pool of **other** datasets and evaluate it on
the target's held-out test split — then compare it to raw TabPFN on the same rows.

```
arm A  raw TabPFN on the target                       (the baseline that must be beaten)
arm B  in-domain fine-tune on the target's train split (upper bound / R1 replication)
arm C  pooled fine-tune on ALL other datasets          (LODO, heterogeneous pool)
arm D  pooled fine-tune on a HOMOGENEOUS pool          (similarity_topk, historic policy)
arm E  GLM baseline        arm F  CatBoost baseline
```

Arm B is included deliberately: it bounds what in-domain adaptation can achieve, so we can say
whether transfer closes the gap to B as well as to A.

### 5.2 The open technical decision — feature harmonisation (needs team input)

**This is the design's real blocker and it is not addressed by the existing design doc.** Pooling
datasets means training on one model with one input dimension, but the datasets do not share a
schema:

| dataset | rows | columns |
|---|---|---|
| coil2000 | 9,822 | 86 |
| uslapseagent | 29,317 | 11 |
| eudirectlapse | 23,060 | 19 |
| spanish_motor_lapse | 53,502 | 23 |

Options, with the trade-off each carries:

| Option | What it means | Cost |
|---|---|---|
| **A. Same-schema sub-pools only** | pool only datasets sharing a usable schema; `similarity_topk` then selects within compatible ones | smallest, cleanest pools; limits the pool universe |
| **B. Feature intersection** | keep only features present in every pooled dataset | loses information; may discard the most predictive columns |
| **C. Union with missingness** | all columns; rows lack the ones their dataset doesn't have, imputed/flagged | largest pool; heavy imputation, and TabPFN must tolerate the missingness pattern |
| **D. Minimal common schema** | hand-pick a small harmonised feature set (age, premium, tenure, …) across datasets | interpretable, defensible; discards most signal |

The historic study ran at 800 target / 400 pool rows and evidently pooled *something* workably —
but its feature-harmonisation approach is not documented in the method file, so **we cannot
inherit it**. **Recommendation: decide this first, and pilot it on one target with a mock/CPU run
before spending anything.** Note also that the *targets* differ across datasets (CARAVAN,
surrender, lapse, LapseB) — all binary insurance events, so pooling learns a generic "insurance
event" prior. That is a defensible framing, but it must be stated explicitly rather than assumed.

### 5.3 Scale options

Historic precedent says scale up in **budget**, not in dataset count (Round 3 did that and failed).
Our options:

| Rung | Target rows | Pool | Seeds × folds | Device | Purpose |
|---|---|---|---|---|---|
| **S0** | 800 / 400 per dataset | historic parity | 3 seeds × 5 folds | CPU | **Reproduce the v2 protocol on v3 at the historic scale.** If the verdict doesn't reproduce even here, the rest is moot. |
| **S1** | 2,000 / 1,000 per dataset | 3–4 datasets | 3 seeds × 5 folds | GPU | The R1 scale, done properly: folds, seeds, transfer arms, full audit |
| **S2** | 5,000 / 2,000 | full pools | 3 seeds × 5 folds | GPU | The historic "5K" rung — where TabPFN leads on log loss |
| **S3** | full (9.8K–53K) | full pools | 3 seeds × 5 folds | GPU | Production scale; only if S1/S2 show a signal |

**Proposed sequence: S0 → (gate) → S1 → (gate) → S2.** S3 only on a positive S2. S0 is cheap and
runs on CPU at the historic scale, so it can be done for **$0** — and it directly answers "is the
v2 verdict model-dependent?", which is the cheapest informative question available.

**A caution on CPU.** The master report's "do not chase fine-tuning with CPU" applies to the
*scale*, not absolutely: the historic pooling work ran fine on CPU at 800/400 rows (with
`OMP_NUM_THREADS=1 MKL_NUM_THREADS=1` to avoid torch segfaults), whereas our own CPU attempt at
2,000 rows hit a memory ceiling. So S0 is CPU-viable; S1 and above are GPU.

### 5.4 Statistical design (the corrections that matter most)

- **Minimum three seeds** (42/43/44, matching the historic study) so Δ has a distribution, not a
  point.
- **Reuse the canonical folds** already in `scripts/eval/*/results_per_split.csv` where the target
  matches, for direct comparability with the benchmark work; otherwise 5 stratified folds.
- **Paired comparison only.** Every arm predicts the same test rows; report paired Δ with an
  interval on the delta, never two independent scores.
- **Sufficient test size.** R1's coil2000 test set held 57 positives, giving a 95% CI width of
  0.118 — wider than any effect we could hope to see. **Size the test split from a power
  calculation on the observed variance before choosing a rung**; otherwise we spend to re-measure
  noise.
- **Metrics: log loss primary** (insurer-facing and the historic primary), plus Brier, ECE,
  ROC AUC, PR AUC. Report calibration, since fine-tuning degraded it on `freMTPL2freq_binary`.
- **Decision rule, tightened.** The historic rule (pooled ΔROC > 0 and ΔPR > 0 for the same
  policy, stable across seeds, calibration not materially degraded) is sound and should be reused.
  The `R3 gate` in `FINE_TUNING_EXPERIMENT_DESIGN.md` should **not** be — its second criterion is
  satisfied by raw TabPFN, so it cannot discriminate the fine-tuning hypothesis.
- **Pre-register the outcome mapping:** what result would (a) support, (b) fail to support, or
  (c) overturn the v2 verdict — written down before the run.

### 5.5 Cost estimate (assumption-stated, needs confirmation)

Anchored on measured R1 figures: 4 datasets × (A 41 s + B 117 s) plus ~2 min provisioning per
instance, 5.3 min total, **$0.0482** — i.e. roughly **$0.01 per minute** at ~$0.55/hr.

| Rung | Rough GPU time | Rough cost | Notes |
|---|---|---|---|
| S0 | 0 (CPU) | **$0** | historic scale, CPU-viable |
| S1 | ~2–4 h | **$1–2** | 4 targets × 3 seeds × 5 folds × ~6 arms |
| S2 | ~8–16 h | **$4–9** | 5K rows; fine-tune cost scales with rows |
| S3 | much larger | $10+ | gated on a positive S2 |

These are order-of-magnitude estimates from one data point and should not be treated as a budget.
Sourcing, the paid-run approval gate, and the teardown/watchdog discipline from
`REPRODUCIBILITY_RUNBOOK.md` §C all still apply unchanged.

### 5.6 Gates

- **Gate 0 — team sign-off.** Design agreed, feature-harmonisation option chosen (§5.2), audit
  schema implemented (§4.2) and its acceptance criteria passing, decision rule pre-registered.
- **Gate 1 — free smoke.** One target, one seed, mock-verified end to end, at $0. Confirms the
  manifest, the LODO assertion, and the artifact return *before* any spend.
- **Gate 2 — S0.** CPU, historic scale, does the v2 verdict reproduce on v3?
- **Gate 3 — S1/S2** only if S0/S1 shows a signal worth pursuing.

---

## 6. What we are explicitly NOT proposing

1. **Not scaling the fine-tuning budget as a lever.** Historic Round 3 doubled it and bought ~0.02
   ROC while staying strongly negative. Budget is not the binding constraint.
2. **Not adding new datasets first.** The historic stop-rule says confirm the model line before
   expanding the universe.
3. **Not re-testing `n_estimators`.** Closed as a no-op.
4. **Not running the pooling proposal as an approved experiment yet.** This document is the
   proposal; execution follows team confirmation.
5. **Not claiming anything from R1 about fine-tuning as a strategy.** R1 was four in-domain
   adaptations, not a transfer test — see `FINE_TUNING_PILOT_RESULTS.md` §0.

---

## 7. Decisions we need from the team

1. **Feature harmonisation** — which of the four options in §5.2, and who owns that call?
2. **Target set** — the historic four (`eudirectlapse`, `coil2000`, `ausprivauto0405`,
   `freMTPL2freq_binary`) for comparability, or the R1 four (which include `spanish_motor_lapse`,
   a newer dataset)?
3. **Is S0 worth doing?** It is free and answers whether the v2 verdict is model-dependent. If the
   team regards the v2 negative as decisive, the honest next step may be to stop rather than scale.
4. **Pool policy** — `similarity_topk` vs `mixed_baseline` was a coin flip historically. Do we
   re-test it, or fix the policy and spend the budget on power instead?
5. **Audit schema sign-off** — is the manifest in §4.2 sufficient to satisfy the project's audit
   requirement, or does it need fields we have not anticipated?
