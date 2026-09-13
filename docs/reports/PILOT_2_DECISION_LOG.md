# Pilot 2 — Decision Log (for the technical review)

> Companion to `PILOT_2_DESIGN.md`. **Purpose:** the review's answers, recorded against the
> sections they change, so that a decision cannot be remembered differently by different people
> later — the failure mode this project has already paid for once.
>
> **Nothing in Stage 2 is built, and no spend is authorised, until D1, D2 and D3 are answered.**
> Those three change the *shape of the code*, not its parameters.

## How to use this document

1. Work through §1 in order. Each entry gives the question, why it changes the experiment, the
   options, and a recommendation. Fill the `DECISION` line, name an owner, date it.
2. §2 lists what is **already settled in the design** — confirm it, do not re-open it.
3. §3 is the pre-registered outcome mapping: what each possible result will mean. Agreeing it
   *before* the run is what stops a null being re-litigated afterwards.
4. §4 is the sign-off block.

---

## 1. Open decisions

### D1 — Does the transfer arm see any of the target's rows? **[BLOCKS BUILD]**

**Why it matters.** This is not a tuning detail; it changes what the experiment claims. The current
design is silent, which means it currently supports either reading.

| Option | What it means | The claim it supports |
| --- | --- | --- |
| **(a) Pure transfer** | no target rows anywhere — scaler fit on pool rows, context from pool only, evaluated on the target's held-out test split | "a single model, evaluated on a dataset it has never seen" — the claim the project actually posed |
| (b) Few-shot / adaptation | k target rows permitted (fit, context, or both), k recorded | "the pool plus a little target data" — a *different* and weaker claim |

**Recommendation: (a) pure transfer.** It is the question the project asked. Few-shot can follow as
a separate arm *if* pure transfer shows anything, and it would then be reported as its own claim.

DECISION: ______  Owner: ______  Date: ______  Section: §6.2

### D2 — The schema-matching rule, and who owns it **[BLOCKS BUILD]**

**Why it matters.** H1 (same-schema sub-pools) needs an a-priori definition derived from feature
metadata only. **If the rule were ever chosen by looking at target performance it would be model
selection on test rows** — a direct violation of the §3.1 leakage rule we have just written down.
The rule is therefore also a *recorded run input*, versioned like any other.

| Option | Reproducible? | Risk |
| --- | --- | --- |
| (a) exact column-name overlap | yes, mechanical | may yield small pools |
| (b) required shared semantic fields | yes, if the field list is fixed in advance | the field list is a judgement call — fix it before the run |
| (c) a named owner makes the call | only if written down | unreproducible unless the rationale is recorded |
| (d) similarity-selected (`D2_pooled_sim`) | yes | not schema matching; kept as a secondary arm |

**Recommendation: (a) or (b), with the rule and its version recorded in the run manifest.** Prefer
mechanical over judgement so a third party can rebuild the same pool.

DECISION: ______  Owner: ______  Date: ______  Section: §6.3

### D3 — The target set **[BLOCKS BUILD]**

| Option | Trade-off |
| --- | --- |
| historic four (`eudirectlapse`, `coil2000`, `ausprivauto0405`, `freMTPL2freq_binary`) | makes the re-test legible against R2/R3 — but that comparison was **confounded**, so its legibility is weaker than it looks |
| **R1 four** (`coil2000`, `uslapseagent`, `eudirectlapse`, `spanish_motor_lapse`) | continuity with the smoke test; baselines, environments and failure modes already characterised |

**Recommendation: the R1 four.** We have measured baselines, a known environment and a known
pipeline for those four; the historic set's main virtue is comparability with a result the appraisal
has already shown to be unusable.

DECISION: ______  Owner: ______  Date: ______  Section: §6.4

### D4 — The aggregation and multiplicity rule **[BLOCKS INTERPRETATION]**

**Why it matters.** Targets span 9.8K–53.5K rows, so a plain mean over targets lets the largest
dominate. And "positive for *at least one* comparison" across targets × policies × seeds × folds is
a chance finding waiting to happen.

**Recommendation:** an **inverse-variance / random-effects summary** as the primary statistic, with
**one pre-specified primary target** and the rest reported as secondary. The primary pool policy is
`D_pooled_schema` (see §6.5).

DECISION: ______  Owner: ______  Date: ______  Section: §6.5

### D5 — The pool's row source

**Why it matters.** `build_pool` currently asserts *which datasets* are in the pool; it has no
concept of rows, so nothing enforces where the pool's rows come from.

| Option | Note |
| --- | --- |
| (a) other datasets' **train splits only** | keeps the split discipline uniform and the pool reproducible |
| (b) all rows of the other datasets | not a leak for the target, but inconsistent with our own discipline for no gain |

**Recommendation: (a).** One rule, applied everywhere.

DECISION: ______  Owner: ______  Date: ______  Section: §6.2

### D6 — `R_random`'s permutation policy

**Why it matters.** "Randomly permuted labels" admits several implementations and only one of them
is reproducible.

**Recommendation:** permute **within each pool dataset**, preserving that dataset's marginal class
balance, with the seed recorded. And state in the report what it actually controls — **fine-tuning on
signal-free data** — which is narrower than "wrong pool data degrades the model".

DECISION: ______  Owner: ______  Date: ______  Section: §6.2

### D7 — The funded envelope

**Why it matters.** The full design is ~$35–50 against ~$9.60 of credit; P1c alone can consume it
(§4.5.1).

**Recommendation:** fund **P1a + P1b (~$5)**, leaving ~$4.6 of headroom, and treat **P1c and Stage 2
as an explicit top-up decision** taken in light of P1b.

DECISION: ______  Owner: ______  Date: ______  Section: §4.5.1

### D8 — Label-semantics framing

**Why it matters.** Pool members' targets are *different events* (`CARAVAN`, `surrender`, `lapse`,
`LapseB`). Pooling trains one classifier on a mixture of outcome definitions, so the pooled arm is a
**multi-domain prior**, not a specialist.

**Recommendation:** confirm that any report frames the pooled arm this way and states the
heterogeneous-outcome limitation explicitly, rather than describing it as a single "insurance model".

DECISION: ______  Owner: ______  Date: ______  Section: §6.3

---

## 2. Settled in the design — confirm, do not re-open

| # | Settled | Where |
| --- | --- | --- |
| 1 | **No test row may enter training, validation, early stopping, the inference context, or model selection** — any arm, any stage | §3.1 |
| 2 | **Early stopping handled explicitly** — disabled for the budget comparison, or the epochs actually executed recorded per arm | §4.2 |
| 3 | **Frozen configuration at Gate 1** — Stage 2 does not re-tune per target | §5 |
| 4 | **Pool order pre-registered** — coherent pool first, heterogeneous second, second read only if the first was interpretable | §6.3 |
| 5 | **H1–H4 naming** and the option→arm mapping (the old A–D letters collided with the arm names) | §6.3 |
| 6 | **`D_pooled_schema` added** — the recommended strategy previously had no arm | §6.2 |
| 7 | **§6.5 comparators named**, control tested first: `C`/`D` must beat `A_raw` **and** `R_random` | §6.5 |
| 8 | **Scope boundary** — no spend is authorised by the design or by this log | §1 header |

---

## 3. Pre-registered outcome mapping — agree this now

Stating the reading of each outcome **before** the run is what makes the answer decisive instead of
debatable afterwards. Confirm this mapping, or amend it here rather than later.

| Outcome | Reading | Next step |
| --- | --- | --- |
| Stage 1 gain at 30 epochs but not at 3 | the historic negative was a **budget artefact** | proceed to Stage 2 with the winning budget |
| No gain at any budget (3/10/30), in-domain, matched context | fine-tuning is not a promising lever for this dataset family — **a fair negative**, unlike the historic one | stop; redirect to calibration, preprocessing, task-specific model selection |
| Gain in-domain, not transferable under the coherent pool | in-domain adaptation is the **limit** | report as the limit; do not chase further |
| Transfer positive under the coherent pool, negative under the heterogeneous pool | the pool's **incoherence** cost the gain | report the composition finding; consider schema work |
| Test-set power unreachable within the envelope | report the **power limit**, not a null | revisit scale or accept the limit |

DECISION (accept as written / amend): ______  Owner: ______  Date: ______

---

## 4. Sign-off

| Name | Role | Approve / conditional | Conditions | Date |
| --- | --- | --- | --- | --- |
| | | | | |
| | | | | |
| | | | | |

**Review checklist — the review is complete when:**

- [ ] D1, D2, D3 answered (these block the build)
- [ ] D4–D8 answered
- [ ] §2 confirmed without re-opening
- [ ] §3 outcome mapping agreed
- [ ] An owner is named for the schema-matching rule (D2)
- [ ] The funded envelope is settled, and any top-up is an explicit decision
- [ ] `PILOT_2_PREREQUISITES.md` counts re-checked after the build (PR-1, PR-3, PR-9 still await
      one real box; see the Gate Amendment there)
