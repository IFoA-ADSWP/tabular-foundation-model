# Pilot 2 — Design for a Fair Test of Fine-Tuning

> Date: 2026-09-12 | **Status: DESIGN — awaiting team sign-off. No spend is authorised by this
> document.** Related: #22
> Basis: `HISTORIC_FINETUNING_APPRAISAL.md` (why the historic verdict is unusable),
> `NEXT_STAGE_PROPOSAL.md` (scale options, audit schema), `FINE_TUNING_METHOD.md` (how the
> fine-tune works), `SMOKE_TEST_SCOPE.md` (what R1 did and did not exercise).

---

## 1. Objective

Run a **fair test** of fine-tuning, in two gated stages:

- **Stage 1 — does the mechanism work at all?** In-domain fine-tuning, matched inference context,
  a realistic budget. This is the **positive control** that has never existed in this project.
- **Stage 2 — does it transfer?** One model fine-tuned on a pool of other datasets, evaluated on a
  target it was never trained on.

Stage 2 runs **only if Stage 1 shows a gain.** The historical work went straight to the transfer
question and got a negative answer that the appraisal has shown to be confounded; this ordering
prevents us repeating that.

---

## 2. Why Pilot 2 is a different experiment, not a bigger R1

Three things change, and all three are corrections rather than scale-ups.

| # | R1 / historic | Pilot 2 | Why |
|---|---|---|---|
| 1 | Historic fine-tuned arm had a **context handicap** (64/128 rows of inference context vs the raw arm's full training split) | **Matched inference context, asserted and recorded per arm** | The confound that made the historic verdict unusable |
| 2 | Fine-tuned at **3 epochs** (R1) or 3–5 gradient steps (historic) | **Budget ladder up to the library default of 30 epochs** | The mechanism has never been given a realistic budget — we are 10× below the library's own default |
| 3 | Target rows capped at 2,000 (R1) / 800 (historic) | **Ladder to full datasets** (up to 53,502 rows) | The historic ceiling was CPU; that constraint is gone |

Two supporting facts make the fair test tractable:

- **The matched context is free in the modern path.** The shipped trainer refits its inference
  model on the full training split (`_setup_inference_model` → `fit(self.X_, self.y_)`), so arm B's
  inference context equals arm A's *by construction*. The historic handicap was an artefact of a
  hand-rolled `SUBSAMPLE_SAMPLES` evaluation config that no longer exists. We must still **record**
  the effective context per arm — but we no longer have to engineer parity.
- **The library default is `epochs=30`.** Our 3-epoch setting came from a config field
  (`max_finetune_steps`) that was never a TabPFN parameter. Any claim that "fine-tuning doesn't
  help" currently rests on running it at a tenth of its default budget.

---

## 3. Shared design (both stages)

**Arms**

| Arm | What it is | Role |
|---|---|---|
| `A_raw` | raw TabPFN, full training context, no gradient steps | the baseline that must be beaten |
| `B_ft3` | in-domain fine-tune, 3 epochs | R1/historic parity — the "old" setting |
| `B_ft10` | in-domain fine-tune, 10 epochs | budget ladder |
| `B_ft30` | in-domain fine-tune, 30 epochs (library default) | **the fair-budget arm** |
| `E_glm`, `F_catboost` | actuarial baselines | the practical floor |

**Data.** For each dataset: stratified split, scaler fit on train only, target dropped from
features, identical test rows for every arm. Row cap raised per rung (§4.3). Record a content hash
for every input file.

**Metrics.** **Log loss primary** (the historic primary and the metric an insurer pays on), plus
Brier, ECE (calibration), ROC AUC, PR AUC. Calibration is mandatory — the historic study saw
calibration degrade after fine-tuning on one target, and reporting it is how we would see that.

**Inference and reproducibility.** 3 seeds (42/43/44, matching the historic study for continuity) ×
5 stratified folds (or repeated splits) — so every delta is a **distribution**, not a point, and
every comparison is **paired** on identical test rows.

**Statistical requirements.** Report paired Δ with a 95% CI on the delta. Size the test split from a
power calculation on observed variance — R1's coil2000 test set gave a CI width of 0.118, wider than
any plausible effect. **No run may be reported as a win without a CI that excludes zero.**

---

## 4. Stage 1 — the positive control (in-domain, fair)

### 4.1 Question

With a matched inference context and a realistic budget, does in-domain fine-tuning improve
held-out performance over raw TabPFN?

This is the most favourable setting fine-tuning can have: same distribution, target data in hand,
no harmonisation problem. If it cannot show a gain here, the transfer question is moot.

### 4.2 Design

- **Datasets:** the R1 four — `coil2000`, `uslapseagent`, `eudirectlapse`, `spanish_motor_lapse` —
  for continuity with R1. Add `ausprivauto0405` and `freMTPL2freq_binary` only if the budget ladder
  shows something worth confirming on the historic targets.
- **Arms:** §3, with the epoch ladder `B_ft3` / `B_ft10` / `B_ft30`.
- **Budget-ladder-first rule:** run the epoch ladder on the **cheapest dataset** (coil2000, 9,822
  rows) across all seeds and folds before scaling. If Δlog loss is flat from 3 → 30 epochs, the
  budget hypothesis is dead and we stop before paying for the bigger rungs.

### 4.3 Scale rungs

| Rung | Train / test | Datasets | Seeds × folds | Purpose | Est. GPU |
|---|---|---|---|---|---|
| **P1a** | 2,000 / 1,000 (R1 parity) | 4 | 3 × 5 | Isolate the budget effect at known scale | ~1.5 h |
| **P1b** | 5,000 / 2,000 | 4 | 3 × 5 | The rung where TabPFN leads log loss historically | ~4–6 h |
| **P1c** | full (9.8K–53.5K) | 4 | 3 × 5 | The scale compute now allows | ~15–25 h |

Rungs are gated: P1b only if P1a is either promising or ambiguous; P1c only on a positive P1b.

### 4.4 Pre-registered decision rule

**"The mechanism works"** requires **all** of:

1. mean Δlog loss (`B_ft*` − `A_raw`) **< 0** on at least **half** the datasets;
2. the **paired 95% CI on Δlog loss excludes 0** for at least one dataset;
3. **calibration not materially degraded** (ECE and Brier within a pre-set tolerance);
4. the sign is **stable across seeds** — not driven by one seed or one fold.

Interpretation is fixed in advance:

| Outcome | Reading |
|---|---|
| Gain appears at 30 but not 3 epochs | The historic negative was a **budget artefact**. Proceed to Stage 2 with the winning budget. |
| Gain at no budget | Fine-tuning is not a promising lever for this dataset family. **Stop.** Record a decisive negative — now a *fair* one. |
| Gain only in-domain, not transferable | **Stop after Stage 2** and report in-domain adaptation as the limit. |

### 4.5 Cost

Anchored on R1: 4 datasets × (A 41 s + B 117 s) + ~2 min provisioning = 5.3 min for **$0.0482**
(≈ $0.01/min at ~$0.55/hr). Fine-tune cost scales with rows × epochs, so a 30-epoch run at 2,000
rows is roughly 10× the 3-epoch arm on the same data.

| Rung | Rough GPU time | Rough cost |
|---|---|---|
| P1a | ~1.5 h | **~$1** |
| P1b | ~4–6 h | **~$3–4** |
| P1c | ~15–25 h | **~$9–15** |

Order-of-magnitude only, from a single data point; not a budget. Sourcing, the per-run approval gate
and the teardown/watchdog discipline in `REPRODUCIBILITY_RUNBOOK.md` §C all still apply.

---

## 5. Gate 1

**Proceed to Stage 2 if and only if all four criteria in §4.4 hold.**

**If they do not hold, stop and publish the negative.** That outcome is genuinely informative —
unlike the historic one — because it is the first test of fine-tuning under matched context, a
realistic budget and adequate power. It would justify redirecting effort to calibration,
preprocessing and task-specific model selection, which is where the historic recommendation already
pointed.

---

## 6. Stage 2 — transfer (leave-one-dataset-out)

### 6.1 Question

Does a single model fine-tuned on a pool of **other** datasets transfer to a target it was never
trained on?

### 6.2 Design

For each target `T`:

```
pool(T) = other datasets, explicitly excluding T      # asserted in code, not by convention
fine-tune ONE model on pool(T)   ->   evaluate on T's held-out test split
```

| Arm | Trained on | Evaluated on | Role |
|---|---|---|---|
| `A_raw(T)` | — (in-context only) | T | baseline |
| `B_in_domain(T)` | T's train split | T | **upper bound** — how much of the gap in-domain adaptation can close |
| `C_pooled_all(T)` | all other datasets | T | the transfer test (heterogeneous pool) |
| `D_pooled_homog(T)` | similarity-selected pool | T | pool-composition test |
| `R_random(T)` | **control:** randomly permuted labels, same pool size | T | separates "fine-tuning degrades" from "wrong pool data degrades" |
| `E_glm(T)`, `F_catboost(T)` | — | T | actuarial floor |

`B_in_domain(T)` is carried into Stage 2 deliberately: it lets us report **how much of the in-domain
gain transfer retains**, which is the question a deployment decision actually turns on.

### 6.3 The blocking decision — feature and target harmonisation

Pooling needs one model with one input dimension, but the datasets differ: **86 / 11 / 19 / 23
columns** for coil2000 / uslapseagent / eudirectlapse / spanish_motor_lapse, and the targets have
different definitions (`CARAVAN`, `surrender`, `lapse`, `LapseB`) — all binary insurance events, but
not the same event.

| Option | Approach | Trade-off |
|---|---|---|
| **A. Same-schema sub-pools** | pool only datasets that share a usable schema | cleanest, smallest pools — **recommended starting point**, because it removes the harmonisation confound entirely |
| B. Feature intersection | keep only universally-present features | may discard the most predictive columns |
| C. Union with missingness | all columns, imputed/flagged | largest pool, heavy imputation, risk of the historic incoherence |
| D. Minimal common schema | hand-picked harmonised features | interpretable, discards most signal |

**Recommendation: start with A.** If the transfer arm is negative under A, the result is
interpretable. Under C, a negative could mean "pooling incoherent schemas destroys the model" — the
ambiguity that made the historic result unusable. The pooling *target* framing (a generic insurance
prior) must be stated explicitly in any report.

### 6.4 Targets

The historic four (`eudirectlapse`, `coil2000`, `ausprivauto0405`, `freMTPL2freq_binary`) for
comparability with the R2/R3 evidence, or the R1 four for continuity. **Needs a team decision** —
the historic set makes the re-test legible; the R1 set connects to R1.

### 6.5 Pre-registered decision rule

Reuse the historic rule's shape (it was well designed):

1. pooled mean Δlog loss (and ΔROC AUC) **positive** for at least one pool policy;
2. **stable across seeds** — not driven by one target or seed;
3. calibration not materially degraded;
4. **and** the transfer arm's gain is reported as a fraction of `B_in_domain`'s gain, so the
   "how much transfers" question is answered numerically.

**Rejected:** the `R3 gate` in `FINE_TUNING_EXPERIMENT_DESIGN.md` — its second criterion (B > E)
is satisfied by raw TabPFN, so it cannot discriminate the fine-tuning hypothesis.

### 6.6 Cost

Stage 2 multiplies Stage 1's per-target cost by the number of targets and pool policies. At P1a
scale, roughly **$2–4**; at P1c scale, **$15–30**. Gated behind Gate 1, so nothing is spent until the
mechanism is established.

---

## 7. Prerequisites — build and verify before any spend

Each item fixes a gap found in R1 or in the historic work.

| # | Prerequisite | Fixes |
|---|---|---|
| 1 | **Run manifest** per `NEXT_STAGE_PROPOSAL.md` §4.2, with all seven acceptance criteria passing | 12 R1 capture gaps |
| 2 | **Per-arm predictions returned** from the box, chunked past the 500-char log cap | arm B was unverifiable in R1 |
| 3 | **Fine-tuned weights saved** where size permits, with hash; else the exact reproduction command | no model artefact in R1 |
| 4 | **Matched-context assertion** — `effective_context` recorded per arm, and the A-vs-B comparison refuses to report if they differ | the historic confound |
| 5 | **LODO exclusion assertion** — the target is provably absent from `pool(T)`, asserted in code | the integrity check transfer rests on |
| 6 | **Dataset content hashes** + split indices and their hash | data version and split reproducibility |
| 7 | **Epoch-ladder support** in the runner (`epochs` as a first-class factor, not `max_finetune_steps`) | the budget defect |
| 8 | **Mock-verified end-to-end run** at $0 before any paid run | R1's transport/staging failures |

---

## 8. Fairness checklist — the pre-run gate

No paid run proceeds unless every line is true. This is the list that would have caught the historic
confound.

- [ ] Both TabPFN arms have the **same recorded effective inference context**.
- [ ] Both arms use the **same device, precision, and estimator count**.
- [ ] The fine-tuned arm's budget is stated, and at least one arm uses the **library default (30 epochs)**.
- [ ] Every metric is computed on **identical test rows** across arms, from returned predictions.
- [ ] Δ is reported **paired, with a 95% CI**, and the test split is sized by a power calculation.
- [ ] **≥3 seeds and ≥5 folds** (or repeated splits) are run; the sign is checked for seed stability.
- [ ] **Calibration** (ECE, Brier) is reported for every arm.
- [ ] For transfer runs: **`out_of_pool_asserted = true`**, verified in code.
- [ ] The **random-pool control** is included.
- [ ] The **decision rule and the outcome mapping were written down before the run**.
- [ ] Dataset hashes, git SHA, package versions, GPU/driver and image digest are recorded.
- [ ] Fine-tuned weights saved or a reproduction command recorded.
- [ ] Cost and instance-state history recorded per arm.

---

## 9. What would make us stop

1. **Stage 1 shows no gain at any budget (3/10/30 epochs), in-domain, matched context, P1a or P1b.**
   Stop. This is the fair negative the project has never had.
2. **The epoch ladder is flat from 3 → 30.** The budget hypothesis dies; stop before scaling.
3. **Transfer is negative under same-schema pooling (option A)** while in-domain is positive.
   Conclude that in-domain adaptation is the limit, and report that.
4. **Test-set power cannot be reached within the cost envelope** for the effect size in question.
   Report the power limit rather than a null.

---

## 10. Open decisions for the team

1. **Sign-off on the two-stage, gated structure** — Stage 1 first, transfer only on a positive.
2. **Feature harmonisation** (§6.3) — is option A (same-schema sub-pools) acceptable as the
   starting point? Who owns the schema-matching call?
3. **Target set for Stage 2** (§6.4) — historic four or R1 four?
4. **Budget envelope** — which rungs are funded? P1a only (~$1), through P1b (~$4), or to P1c
   (~$15)?
5. **Pool policy** — the historic comparison was a coin flip under a confounded design. Re-test
   `similarity_topk` vs `mixed_baseline`, or fix one policy and spend the budget on power?
6. **Audit schema sign-off** — is the manifest in `NEXT_STAGE_PROPOSAL.md` §4.2 sufficient for the
   project's audit requirement?
