# Pilot 2 — Design for a Fair Test of Fine-Tuning

> Date: 2026-09-12, revised 2026-09-13 | **Status: DESIGN — awaiting team sign-off. No spend is
> authorised by this document.** Related: #22
>
> **Revision 2026-09-13** adds the leakage policy (§3.1), the frozen-configuration rule at Gate 1
> (§5), an explicit pool order and the missing schema-matched arm (§6.2–6.3), a funded cost envelope
> (§4.5), and four checklist lines (§8).
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

### 3.1 Leakage policy — non-negotiable

**The rule.** No test row may enter **training, validation, early stopping, the inference context, or
model selection** — for any arm, in any stage, in any form. *Model selection* includes choosing the
epoch budget, the pool policy, or the feature set by looking at test performance.

This rule is stated in `FINE_TUNING_METHOD.md` §9, `FINE_TUNING_PILOT_RESULTS.md` §0.2 and the
"zero leakage rule" in `INSURANCE_DOMAIN_FINETUNING_METHOD_PROTOCOL.md` — all of which describe **R1
or the historic protocol**. It is restated here because *this* is the document the next experiment is
held to, and the rule belongs in the document that governs the run rather than in one describing a
past one.

**Two things are true at once, and both must be reported.** In-domain evaluation is **not** leakage:
the split is disjoint, the test rows are never seen, and the scaler is fit on train only. And
in-domain evaluation is **not transfer evidence**: it cannot support a claim that fine-tuning
generalises. Saying only the first invites an overclaim; saying only the second invites the "reads as
leakage" reaction that R1's report already had to address. Stage 1 exists to test the *mechanism*;
only Stage 2 tests the *claim*.

**What is asserted, and what is only stated.** The transfer stage's exclusion is asserted in code and
recorded (`build_pool`, PR-5: target absent by **name and content hash**, `out_of_pool_asserted:
true`). The equivalent assertion for the **inference context** does not yet exist — it is true by
construction today because the split is disjoint, but "true by construction" is this project's
least-reliable category of guarantee. **PR-10** (in `PILOT_2_PREREQUISITES.md`) adds the mirror assertion: context and
validation indices disjoint from test indices, asserted and recorded per arm.

**Verified in the runner (2026-09-13).** The split is stratified and seeded
(`train_test_split(..., stratify=y, random_state=seed)`) and the **validation split is derived from
the training split** (`y[train_idx]`), not from the whole dataset — so early stopping cannot see test
rows. `validation_split_ratio` must still be **recorded per arm** (PR-1), together with the effective
training rows, so the reserve is visible rather than assumed.

**One selection step with no leakage but with a bias risk.** The loader caps each dataset before the
split, taking the first ~3,500 rows of the file. If any file is ordered — by date, by region, by
outcome — that is a systematic selection step, and it can make a test split unrepresentative without
a single row leaking. It must be **recorded** and reported as a limitation; stratifying *at* the cap
is the cheap fix if it proves to matter.

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
- **Early stopping must be handled explicitly, because it becomes live at 30 epochs.** It is inert at
  3 epochs but the library default is *on*, so `B_ft30` may not run 30 epochs at all — it runs however
  many the validation split permitted. That would silently convert the design's central correction
  ("give the mechanism its default budget") into "give it whatever early stopping allowed". Either
  **fix the epoch count with early stopping disabled** for the budget comparison, or **record the
  epochs actually executed per arm** and report the ladder against those. State which, before the run.

### 4.3 Scale rungs

| Rung | Train / test | Datasets | Seeds × folds | Purpose | Est. GPU |
|---|---|---|---|---|---|
| **P1a** | 2,000 / 1,000 (R1 parity) | 4 | 3 × 5 | Isolate the budget effect at known scale | 5.7 h (~$3.12) |
| **P1b** | 5,000 / 2,000 | 4 | 3 × 5 | The rung where TabPFN leads log loss historically | 14.3 h (~$7.80) |
| **P1c** | full (9.8K–53.5K) | 4 | 3 × 5 | The scale compute now allows | 57.4 h (~$31.21) |

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

### 4.5 Cost — measured, not estimated

**The unit cost is known.** R1 ran the full A/B comparison on all four datasets at 2,000/1,000, one
seed, one split. The run that produced it cost **$0.0482**, including provisioning — 5.3 min on an
L40S at $0.544/hr.

Every projection below is built from R1's measured arm times:

| | coil2000 | eudirectlapse | spanish_motor_lapse | uslapseagent | **total** |
| --- | --- | --- | --- | --- | --- |
| `A_raw` | 15.9 s | 12.3 s | 6.5 s | 6.3 s | **41.1 s** |
| `B_in_domain` (3 epochs) | 35.7 s | 36.4 s | 18.3 s | 26.6 s | **116.9 s** |

So **fine-tuning costs 2.85x the raw arm** at 3 epochs, and one split of A+B is 158 s (~$0.024 of
compute).

**Pilot 2 multiplies that by three independent choices.**

| Factor | R1 | Pilot 2 | Multiplier |
| --- | --- | --- | --- |
| Repeats | 1 seed x 1 split | 3 seeds x 5 folds | **15x** |
| Epochs | 3 | up to 30 | **~10x** on the gradient work |
| Rows | 2,000 | up to full | **~10x** |

That is the whole explanation of a large programme figure: not overhead, but **up to ~1,500x R1's
compute** if every axis is taken to its top. The purpose of the rungs is to let us decline parts of
that stack, not to buy it whole.

| Rung | GPU time | **Measured model** | Earlier estimate |
| --- | --- | --- | --- |
| P1a (2,000/1,000, 3x5) | 5.7 h | **$3.12** | ~$1 |
| P1b (~2.5x rows) | 14.3 h | **$7.80** | ~$3.5 |
| P1c (full, ~10x rows) | 57.4 h | **$31.21** | ~$12 |

The earlier figures were **optimistic by 2.5-3x** because they assumed a modest epoch cost. Scaling
from what R1 actually measured is the honest basis.

**The dominant uncertainty is cheap to settle.** The 3->30 epoch multiplier is an *assumption*
(modeled as ~30 s fixed plus ~29 s per epoch) and the 30-epoch rung is ~65% of the ladder's cost.
The section 4.2 ladder-first rule settles it on one dataset:

```
1 dataset, 1 split, full ladder (A + B3 + B10 + B30)  =  ~6 min  =  ~$0.05
```

**Funded First Step: ~$0.05.** One run that measures the epoch->cost *and* epoch->gain curves
together, before anything is scaled. If the ladder is flat, the budget hypothesis dies at twenty
cents instead of at fifteen dollars.

**The levers, in order of size**

1. **Repeats** — the largest multiplier and the cheapest to cut. 15x -> 3x (3 seeds, one split) takes
   P1a from $3.12 to **~$0.62**, trading a variance estimate for 80% of the cost. A deliberate
   choice, not a default.
2. **Epochs** — the top rung is two-thirds of the ladder; the $0.20 probe decides whether it earns it.
3. **Rows** — P1c is optional and already gated behind P1b.

### 4.5.1 What R1's spend does and does not tell us

**$0.5256 across 13 instances was spent, and it is not the price of an experiment. It is the price of
a pipeline that did not yet work.** R1 hit four defects on the paid path: a transport that could not
run commands, a poll that silently captured nothing, instances that could never start
(`intended_status: stopped`), and a licence gate that rejected every dataset. Instances were created,
billed, and returned nothing — **6 of the 13 produced no arm result at all**, and a further five ran
only a preflight.

| | |
| --- | --- |
| The two runs that produced results | **$0.0768** |
| The other eleven — failed, stalled, or preflight-only | $0.4488 |
| Total | $0.5256 |

So the right anchor for Pilot 2 is the **marginal cost of a successful run — $0.0482** for a full
four-dataset A/B comparison — not R1's average. The debugging spend is one-off: those defects are
fixed, and the assertions in `PILOT_2_PREREQUISITES.md` exist so they cannot return silently.
Budgeting Pilot 2 at R1's total would price in a mistake we have already paid for.

**Recommended envelope, on the measured model:**

| Step | Cost | What it buys |
| --- | --- | --- |
| The ladder probe (1 dataset, 1 split, 3/10/30) | **~$0.05** | the epoch->cost and epoch->gain curves |
| P1a at 3 seeds x 1 split | **~$0.62** | a first in-domain answer with a variance estimate |
| *Subtotal* | **~$0.67** | |
| P1a at full 3x5 | $3.12 | a tighter paired CI — a separate decision |
| P1b | $7.80 | gated on P1a |
| P1c | $31.21 | gated on P1b; optional |
| Stage 2 (LODO, P1a scale) | ~$0.85 | gated on Gate 1 |

### 4.5.2 What it costs to complete Pilot 2 — three scenarios

There is no single figure, because two choices drive it: **how many repeats** (3 or 15) and **how far
up the ladder** we go. On the measured model:

| Scenario | Includes | Total | vs ~$9.60 credit |
| --- | --- | --- | --- |
| **Lean** — *recommended* | probe + P1a (3 seeds x 1 split) + Stage 2 at P1a scale (3 seeds x 1 split) | **~$1.49** | fits, ~$8 left |
| **As the design specifies** | probe + P1a + P1b at full 3x5 + Stage 2 at P1a, 3x5 | **~$15.05** | needs **+$5.45** |
| **Full ladder** | the above plus P1c at 3x5 and Stage 2 at P1c scale | **~$82.9** | needs **+$73** |

The dominant line in the full scenario is **Stage 2 at P1c scale (~$40)**, driven by pooling ~74,000
rows at 30 epochs; P1c's own Stage 1 rung is another ~$31.

**So the honest answer to "what will it cost to finish?" is: ~$1.50 to answer the hypothesis, ~$15 to
run the design as written, and ~$83 to run it end to end at the top of every axis.** Only the first
fits the current credit.

**The estimate's weak point is the epoch model** (~30 s fixed plus ~29 s per epoch), which is
assumed rather than measured and sets the 10x multiplier in every figure above. The ~$0.05 probe
replaces it with a measurement before any of this is committed.

Against ~$9.60 of credit, **the probe plus a reduced-repeat P1a fit comfortably**; the full rungs and
Stage 2 need a top-up decision taken in light of the probe's result.

## 5. Gate 1

**Proceed to Stage 2 if and only if all four criteria in §4.4 hold.**

**The winning configuration is FROZEN at this gate.** Stage 2 inherits the epoch budget that won in
Stage 1 and **does not re-tune per target**. This is what makes the transfer claim mean *"a single
model evaluated on a dataset it was never trained on"*; if the configuration were chosen per target,
Stage 2 would be N configurations and the claim would collapse back into the R1 situation. Choosing
the budget on Stage 1's in-domain evidence is legitimate **only** because that is Stage 1's whole
purpose — this is the one place where selection happens, and it happens once, before any target is
evaluated.

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
| `C_pooled_all(T)` | all other datasets | T | transfer, **heterogeneous** pool — run second (§6.3) |
| `D_pooled_schema(T)` | **same-schema sub-pool** | T | transfer, **coherent** pool — **the recommended starting point** |
| `D2_pooled_sim(T)` | similarity-selected pool | T | pool-composition variant (optional, secondary) |
| `R_random(T)` | **control:** randomly permuted labels, same pool size | T | separates "fine-tuning degrades" from "wrong pool data degrades" |
| `E_glm(T)`, `F_catboost(T)` | — | T | actuarial floor |

`B_in_domain(T)` is carried into Stage 2 deliberately: it lets us report **how much of the in-domain
gain transfer retains**, which is the question a deployment decision actually turns on.

### 6.3 The blocking decision — feature and target harmonisation

Pooling needs one model with one input dimension, but the datasets differ: **86 / 11 / 19 / 23
columns** for coil2000 / uslapseagent / eudirectlapse / spanish_motor_lapse, and the targets have
different definitions (`CARAVAN`, `surrender`, `lapse`, `LapseB`) — all binary insurance events, but
not the same event.

These options are named **H1–H4** deliberately: the previous edition used `A`–`D`, which collided
with the arm names in §6.2 (`A_raw`, `C_pooled_all`) so the same letter meant two things in one
document.

| Option | Approach | Trade-off | Arm that runs it |
|---|---|---|---|
| **H1. Same-schema sub-pools** | pool only datasets that share a usable schema | cleanest, smallest pools — **recommended starting point**, because it removes the harmonisation confound entirely | `D_pooled_schema(T)` |
| H2. Feature intersection | keep only universally-present features | may discard the most predictive columns | — (not built) |
| H3. Union with missingness | all columns, imputed/flagged | largest pool, heavy imputation, risk of the historic incoherence | `C_pooled_all(T)` |
| H4. Minimal common schema | hand-picked harmonised features | interpretable, discards most signal | — (not built) |

**Recommendation: start with H1 (`D_pooled_schema`).** If the transfer arm is negative under a
coherent pool, the result is interpretable. Under H3 (`C_pooled_all`), a negative could mean "pooling
incoherent schemas destroys the model" — the ambiguity that made the historic result unusable.

**Pool order is therefore pre-registered, not merely preferred:**

1. **Coherent pool first** (`D_pooled_schema`, H1). This is the interpretable test, and it gates the second.
2. **Heterogeneous pool second** (`C_pooled_all`, H3), and its result is read **only if** the coherent
   pool's result was interpretable. A negative under H3 after a *positive* H1 is informative ("the
   pool's incoherence cost us the gain"); a negative under H3 after a *negative* H1 tells us nothing new.

**Run order does not license tuning.** The budget stays frozen (§5); only the pool policy varies
between these arms, and it varies by design, not by looking at the target's test rows.

The pooling *target* framing (a generic insurance prior) must be stated explicitly in any report.

### 6.4 Targets

The historic four (`eudirectlapse`, `coil2000`, `ausprivauto0405`, `freMTPL2freq_binary`) for
comparability with the R2/R3 evidence, or the R1 four for continuity. **Needs a team decision** —
the historic set makes the re-test legible; the R1 set connects to R1.

### 6.5 Pre-registered decision rule

**Comparators are named explicitly, and the control is tested first.** A rule that does not name
its comparators can be satisfied by the wrong arm — which is the defect the rejected R3 gate below
has. So: **apply every criterion to `R_random` first.** If the control passes a criterion, that
criterion cannot discriminate the hypothesis and must be replaced before the run.

"The mechanism works" for transfer requires **all** of:

1. **`C`/`D` beat `A_raw`** on pooled mean Δlog loss (and ΔROC AUC), and
2. **`C`/`D` beat `R_random`** — the label-permuted control. Without this, "fine-tuning on *any*
   data helps" cannot be separated from "the pool's *signal* helps", and the control's own stated
   reading ("separates fine-tuning degrades from wrong pool data degrades") overstates what a
   permuted-label pool can show: it controls *fine-tuning on signal-free data*, which is narrower;
3. the **primary** pool policy is the one that must clear the bar — `D_pooled_schema` (H1, coherent),
   per the pre-registered order in §6.3. `C_pooled_all` is **confirmatory, not an alternative bite
   at the cherry**: "positive for at least one policy" across two policies is a multiplicity hazard,
   and with the order fixed in advance there is no justification for choosing the winner after seeing
   both;
4. **stable across seeds and targets** — not driven by one seed or one target. The aggregation rule
   must be stated (inverse-variance / random-effects summary), because a plain mean over targets of
   9.8K–53.5K rows lets the largest target dominate;
5. calibration not materially degraded — **with the ECE/Brier tolerance set numerically in advance**;
   an unset tolerance is not a pre-registration;
6. **and** the transfer arm's gain is reported as a **fraction of `B_in_domain`'s gain**, so the
   "how much transfers" question is answered numerically — and so a small absolute gain cannot be
   presented as a large one relative to what in-domain adaptation achieved.

**Rejected:** the `R3 gate` in `FINE_TUNING_EXPERIMENT_DESIGN.md` — its second criterion (B > E)
is satisfied by raw TabPFN, so it cannot discriminate the fine-tuning hypothesis.

### 6.6 Cost

Stage 2 multiplies Stage 1's per-target cost by the number of targets and pool policies. At P1a
scale, roughly **$2–4**; at P1c scale, **$15–30**. Gated behind Gate 1, so nothing is spent until the
mechanism is established. Note that at P1c scale Stage 2 **cannot be funded from the current
balance** — see §4.5.1; the gate bounds the *order* of spending, not its ceiling.

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
- [ ] **No test row entered training, validation, early stopping, the inference context, or model
      selection** — for any arm, in any stage (the §3.1 rule).
- [ ] **Context and validation indices asserted disjoint from test indices, and recorded** (PR-10),
      with `validation_split_ratio` and effective training rows per arm.
- [ ] **Epochs actually executed recorded per arm**, and the ladder reported against those — not
      against the epochs requested (§4.2).
- [ ] **The loader's pre-split row cap recorded**, and reported as a selection limitation if the
      source files are ordered (§3.1).

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

**These are tracked with options, recommendations and blanks to fill in
`PILOT_2_DECISION_LOG.md`**, which is the document the review works through. Three of them
(**D1** transfer vs few-shot, **D2** the schema-matching rule, **D3** the target set) change the
*shape of the code*, not its parameters, so Stage 2 is not built until they are answered.

1. **Sign-off on the two-stage, gated structure** — Stage 1 first, transfer only on a positive.
2. **Feature harmonisation** (§6.3) — is option **H1** (same-schema sub-pools, run as
   `D_pooled_schema`) acceptable as the starting point, with H3 (`C_pooled_all`) second and read only
   if H1 was interpretable? Who owns the schema-matching call?
3. **Target set for Stage 2** (§6.4) — historic four or R1 four?
4. **Budget envelope** (§4.5.1) — the full design is ~$35–50 against ~$9.60 of credit. Recommended:
   fund **P1a + P1b (~$5)** and treat P1c and Stage 2 as a separate top-up decision. Confirm, or set
   a different ceiling.
5. **Pool policy** — the historic comparison was a coin flip under a confounded design. Re-test
   `similarity_topk` vs `mixed_baseline`, or fix one policy and spend the budget on power?
6. **Audit schema sign-off** — is the manifest in `NEXT_STAGE_PROPOSAL.md` §4.2 sufficient for the
   project's audit requirement?
