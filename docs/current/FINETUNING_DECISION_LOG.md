# Fine-Tuning — Decision Log for Technical Review

> **Status:** current as of 2026-11-03.


> **Supporting document.** The canonical current proposal is `docs/current/FINETUNING_PILOT_DESIGN.md`. This log preserves technical decisions from the earlier pilot design. Its transfer and pooling entries become active technical references only if the in-domain gate releases Phase 3; they are not blockers for Phases 1–2.

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

DECISION: **accepted as recommended (2026-10-30)** — permute within each pool dataset, preserving that
dataset's marginal class balance, with the seed recorded; the report states that this controls
fine-tuning on signal-free data, not "wrong pool data degrades the model".  Owner: scotthawes  Date: 2026-10-30  Section: §6.2

### D7 — The funded envelope

**Why it matters.** The figures are modelled from the first pilot's measured arm times, and the model
rests on **one** relationship nobody has measured: how cost grows with training length. On that basis
the design as written is **~$31** against **~$9.60** of credit, and the recommended staged path is
**~$4.70** (`docs/current/FINETUNING_COST_AND_CONTROLS.md` states the basis of every figure).

**Recommendation:** fund the **first step only (7p)**, which measures that relationship on one dataset.
Fund the in-domain steps on its result, and take the transfer experiment and any increase in data
scale as **separate decisions taken on measured numbers rather than modelled ones**.

DECISION: **No phase ceiling for the diagnostics-and-anchor phase (2026-10-30).** Spend is
bounded by the launcher's per-hour price cap and by the stop rule, not by a phase budget; the
measured anchor cost is $0.0368 a run. This **departs from the recommendation above**: the first
step is funded and the in-domain steps follow the anchor gate, as recommended, but the phase
itself carries no envelope. Accepted risk: a runaway retry loop is bounded by the price cap
only. Recorded with its consequence in the campaign map, #286.  Owner: scotthawes  Date: 2026-10-30  Section: §4.5.1

### D8 — Label-semantics framing

**Why it matters.** Pool members' targets are *different events* (`CARAVAN`, `surrender`, `lapse`,
`LapseB`). Pooling trains one classifier on a mixture of outcome definitions, so the pooled arm is a
**multi-domain prior**, not a specialist.

**Recommendation:** confirm that any report frames the pooled arm this way and states the
heterogeneous-outcome limitation explicitly, rather than describing it as a single "insurance model".

DECISION: **accepted as recommended (2026-10-30)** — pooled arms are reported as a multi-domain prior,
not a specialist, and the heterogeneous-outcome limitation is stated wherever a pooled number appears.
Owner: scotthawes  Date: 2026-10-30  Section: §6.3

### D9 — The anchor's acceptance, pre-registered

**Why it matters.** The anchor is the first paid step of the funded phase, and it decides whether the
fine-tuning line continues. Its acceptance has to exist before the run, or a result that does not
replicate can be re-described as a near miss afterwards.

**Decision (2026-10-30).** Two seeds — **43 and 44** — on `uslapseagent`, 10,000 training rows, arms
`A_raw`, `B_ft3`, `B_ft10`, `B_ft30`, each run carrying its own `A_raw` baseline so no comparison
crosses a run.

The anchor **passes** for a seed when, for **all three rungs**, the paired 95% interval of ROC AUC
against that run's in-run `A_raw` excludes zero in the direction seed 42 showed (positive). A rung that
fails is reported as failing; it is not dropped. The **interval bounds decide**. The `***` display
marker is not a criterion and carries no information of its own: it is derived from the same bounds,
as #296 settled. Calibration is judged by the signed plan's tolerance: Brier must not increase
against in-run `A_raw` by more than 0.001.

**Known conflict, recorded rather than hidden.** §12.1 of the statistical plan says this dataset "can
resolve >= 0.009 ROC" from R1's paired intervals, while `FINETUNING_PROBE_RESULTS.md` records measured
paired half-widths of 0.0022 / 0.0023 / 0.0043 in the same data. The acceptance above rests on the
runbook's interval rule, not on the 0.009 figure. The reconciliation is owed before the breadth phase,
and the deviation is entered under the plan's §10.

**Outcome reading** is the pre-registered mapping in §3, accepted as written. What to do when the two
seeds disagree is deliberately left to D10's ticket (#290), not decided here.

DECISION: **accepted as written above (2026-10-30)** — seeds 43 and 44; all three rungs must clear;
bounds decide, not markers.  Owner: scotthawes  Date: 2026-10-30  Section: §4.5.2

### D10 — Paid diagnostics are approved per run, on a measured estimate

**Why it matters.** D4 was priced at about 5p when the design was written. D3's three untouched
datasets have never been priced at all: reframing `freMTPL2freq` means nine methods over five folds
on 678K rows through the hosted client, and nobody has measured one fold. A standing ceiling for
"the diagnostics" would therefore be a number invented in this document, which is the failure D7
already names.

**Decision (2026-10-30).** Each paid diagnostic run is approved on its own, and the approval is
preceded by a **measured** estimate: run one fold (or one method) on the target dataset, record what
it cost, and scale. No standing ceiling for the diagnostics phase, and no run that begins with an
estimate phrased as a guess.

The anchor is **not** covered here. D7 governs it: the phase carries no envelope, and its cost is
measured ($0.0368 for a four-arm 10,000-row run) rather than modelled.

**What this means in practice.** A paid diagnostic ticket is blocked until its estimate exists, and
the estimate is recorded on the ticket. If the estimate is large enough to matter, it is a spending
decision rather than a ticket comment — which is the point of requiring the measurement.

DECISION: **accepted (2026-10-30)** — per-run approval, measured estimate first, no diagnostics
envelope; D7 continues to govern the anchor.  Owner: scotthawes  Date: 2026-10-30  Section: §4.5.3

### D11 — The anchor did not replicate; the fine-tuning line stops

**What was run.** `uslapseagent`, 10,000 training / 1,000 test rows, arms `A_raw`, `B_ft3`, `B_ft10`,
`B_ft30`, seeds **43** and **44**, one instance, one launch (`20261031T021925Z-c24870`, instance
`58479781`, 6.52 min, $0.0288). Eight arm records, `predictions_sha256` on every one, artifacts
verified (`verified=8 mismatched=0 missing=0`), lease `released`. Evidence committed at
`results/20261031T021845Z/`.

**The reading, per D9.** Paired bootstrap over the 1,000 test rows, 4,000 resamples, fixed seed,
percentile interval; each arm against that seed's own `A_raw`:

| seed | rung | ΔAUC | 95% paired CI | D9 |
| --- | --- | --- | --- | --- |
| 43 | B_ft3 | +0.0031 | [+0.0000, +0.0063] | pass |
| 43 | B_ft10 | +0.0050 | [+0.0010, +0.0092] | pass |
| 43 | B_ft30 | +0.0057 | [+0.0013, +0.0105] | pass |
| 44 | B_ft3 | +0.0009 | [−0.0017, +0.0036] | fail |
| 44 | B_ft10 | +0.0013 | [−0.0022, +0.0048] | fail |
| 44 | B_ft30 | +0.0010 | [−0.0026, +0.0049] | fail |

**D9 required both seeds to clear all three rungs. One seed did, one did not.** The anchor does not
replicate.

**Decision (2026-10-31).** The fine-tuning line **stops**. The 10,000-row gain is not stable across
splits at this scale; seed 43 reproduces the R1 pattern and seed 44 is indistinguishable from raw
TabPFN on all three rungs. Calibration is not the cause — seed 44's Brier moves are within +0.001 of
its `A_raw`, so the failure is in ranking.

This is a **fair negative**, not the historic one: matched context, in-run baseline, pre-registered
reading. Per the pre-registered outcome mapping, the redirect is calibration, preprocessing and
task-specific model selection — not further fine-tuning at this scale.

**What this does not settle.** Why seed 44 differs. The diagnostics (D1–D5) remain the way to ask
that question; they no longer gate anything.

DECISION: **stop the fine-tuning line (2026-10-31)** — the anchor did not replicate under D9.
Owner: scotthawes  Date: 2026-10-31  Section: §4.5.2

**Restated 2026-11-03, after the null control (#338).** The anchor's stop **stands for the v3 line** — D9
required both seeds and one did not clear — but its *reading as a null* does not. D11 called the result "a fair negative",
which is §3's row for *no gain at any budget*. The row for this case is the last one in that table:
*"Test-set power unreachable within the envelope → report the power limit, not a null."* That reading
was not available on 2026-10-31, because nobody had measured the design's resolution.

It is measured now. Scores-only over this run's committed capture, with 5,000 label permutations per
seed, gives a per-seed null SD of **0.0052–0.0055** and a 95% band of **±0.010**, against an effect of
**0.002–0.003**. Every observed delta sits inside that band (p 0.29–0.84), and the two-seed rule D9 used
fires under the null at 0.0008–0.0012. The design could not tell "no effect" from "no power".

So: the stop is a **power stop, not a null**. The redirect to calibration, preprocessing and
task-specific model selection is unchanged, and the diagnostics still serve explanation rather than a
gate. Method and figures: `docs/analyses/null_control_scoring_path.md`. Consequences: D12–D14 below.

**Which mapping governs what.** §3's last row prescribes "revisit scale or accept the limit". D14 takes
the first branch in a **bounded** form — one replication that revisits *seeds*, not rows, and no
breadth — and its three outcome branches govern the replication. §3 continues to govern the anchor's
own reading, which is the power row above.

### D12 — The continuation threshold, agreed before any replication

**Why it matters.** Without a threshold agreed in advance, a replication's outcome gets described
after the fact. The evidence so far is a 0.002–0.003 AUC effect, against a baseline margin about 20
times larger (+0.068 on COIL 2000; see D14), so "is another run worth it" needs a number, not a
feeling.

**Decision (2026-11-03).** The claim measure is **ROC AUC**, with Brier as a veto (tuned arm no more
than `A_raw` + 0.001). The comparator is the **in-run `A_raw`** — same seed, split and version. The
effect worth continuing for is **δ = 0.002 AUC**, because R1's own range was +0.0022 to +0.0034, so an
**equivalence bound of ±0.002** excludes all of it. **One rung**, pre-registered from a probe, carries the verdict; the
others are descriptive. A failure claims "no effect larger than 0.002" **only** when the interval lies
wholly inside ±0.002 — a wide interval containing zero is *unresolved* and licenses nothing.

**Cost, measured rather than assumed.** From the anchor's recorded arm times and the measured rate, a
four-arm ten-seed probe is **$0.11** and a 57-seed two-arm replication is **$0.12** across three
launches — about **$0.23** for the pair. The **ceiling is $0.15 per launch**: an authorisation decision,
not a cost estimate. Sources: `docs/analyses/replication_sizing.md` §7 for the cost model, and
`results/20261031T021845Z/` for the timings it is built from.

The model is **v3_default, pinned explicitly** — the same line the anchor ran (`version: auto` resolved
to `tabpfn-v3-classifier-v3_default.ckpt`), now named in the record instead of inferred from a checkpoint
field. **Same version means the measured variance transfers**: the 0.0036 half-width and the 0.00535
per-seed null SD stand, and the probe refines the between-seed term rather than re-deriving a line. The
pin passes a **path, not a label** (#285, #345).

**v3.5 is not available for this work** (corrected on evidence, 2026-11-03). It exists on the hosted
client line; `tabpfn 8.5.0` — the version the anchor ran on — enumerates only `V2, V2_5, V2_6, V3` and
exposes no v3.5 classifier checkpoint, and the fine-tuning path is local-package only, so a v3.5 pin
cannot be loaded at all. Agreed on the threshold ticket (#337).

DECISION: **accepted (2026-11-03)** — δ=0.002 AUC, Brier ≤ `A_raw`+0.001, one probe-selected rung,
in-run comparator, $0.15 per launch **ceiling**, v3_default pinned.
Owner: scotthawes  Date: 2026-11-03  Section: §4.5.4

### D13 — The replication design

**Why it matters.** A design that cannot see the effect produces another D11. The anchor's ambiguity
was **between splits**, so more test rows do not help: at the 19,317-row ceiling the row-only design
still gives 38% power on the conservative variance basis (`docs/analyses/replication_sizing.md` §5).

**Decision (2026-11-03).** A four-arm probe — ten seeds, 1,000 test rows, 10,000 training rows —
measures the **between-seed** variance (two seeds cannot estimate it, which is what made D11 ambiguous)
and picks the rung: the highest probe mean that still fits the per-launch
ceiling, with the next-best rung substituted (and recorded) if the winner does not fit. The
replication then runs `A_raw` plus that one rung over `k = ceil((sd_probe / 0.000714)²)` **fresh**
seeds, aggregated as a random-effects (REML) interval. (`0.000714` is the standard error that gives 80%
power at δ=0.002: δ divided by 2.80159, the sum of the two-sided z for 95% confidence and the one-sided
z for 80% power.)

Two safeguards, at two different moments: a **pre-spend resolution gate** stops the replication before
any money if `k` cannot reach 0.002, and a **fresh permutation null** on the replication's own capture —
whose acceptable **false-positive rate is at most 0.07** — voids the verdict on instrument failure
after the capture but before the verdict is read. A failure claims equivalence only inside ±0.002. The design must be committed as a pre-registration before the
probe launches — that document is also the dated amendment the escalation rule requires.

> **2026-11-10** (#535). This sentence read "acceptable **false-positive-rate band is 0.03–0.07**". The
> pre-registration that governs the run states a **one-sided** bound and gives the reason: a conjunction of
> three conditions is deliberately conservative, and the anchor's rule fires at about 0.001. A lower bound
> would void a *perfect* null — the anchor measured 0.0000 — which is backwards for an instrument check.

Ruled out, with reasons: per-seed conjunction (power 1.3×10⁻⁴¹ at 57 seeds), pooling rows (SE understated
1.69×, false-positive rate 0.25), and re-running the epoch ladder in the replication (three times the
cost for description no decision uses). All three figures, and the cost model, are worked in
`docs/analyses/replication_sizing.md` §§4–6; the null band the fresh check must reproduce is in
`docs/analyses/null_control_scoring_path.md`. Design agreed on #336.

DECISION: **accepted (2026-11-03)** — probe then two-arm replication, REML interval, resolution gate,
fresh null, pre-registration first.
Owner: scotthawes  Date: 2026-11-03  Section: §4.5.5

### D14 — The pilot continues once, then stops either way

**Why it matters.** This is the destination of the effort: whether the lever stays open. Deciding it on
the size of the effect, before the effect is measured, is how a lever stays open for a year.

**Decision (2026-11-03).** The pilot **continues** — one pre-registered v3 replication on
`uslapseagent`, about **$0.23** at the measured figures in D12 — and **not further**. There is **no Stage 2 expansion even on a pass**: a
0.002–0.003 effect is roughly 20 times smaller than raw TabPFN's margin over the best actuarial
baseline, so scaling it buys a larger sample of something no modelling choice depends on. A pass
publishes and stops; a decisive null archives, with code and evidence going to #340 and #341; an
unresolved result reopens this decision and is never reported as a soft pass.

**Evidence this rests on, by name.** The null control (`docs/analyses/null_control_scoring_path.md`)
for why the earlier stop was a power stop; the sizing analysis
(`docs/analyses/replication_sizing.md`) for why the row lever is not the answer and what the seed lever
costs; the dataset readiness assessment
(`docs/analyses/spanish_motor_lapse_stage2_readiness.md`) for why breadth is declined rather than
deferred — a paired half-width of ≈0.015 makes that dataset void as evidence. Destination agreed on
#339; the threshold it applies is D12.

**Which mapping governs.** §3's power row prescribes "revisit scale or accept the limit"; this decision
takes the first branch in a bounded form — seeds, not rows, and no breadth — and these three outcome
branches govern the replication. §3 still governs the anchor's reading.

Reopening requires a **named diagnostics finding** — a dataset whose closable gap is large relative to
0.002 — or a **measured classification behaviour change on a newer model version** (v3.5 or later, once
the local package can load one). Nothing vaguer.

DECISION: **continue once, no expansion (2026-11-03)** — one v3 replication; pass publishes, null
archives, unresolved reopens.
Owner: scotthawes  Date: 2026-11-03  Section: §3

### D15 — The replication passed; the pilot publishes and stops

**What was run.** Pre-registered on 2026-11-04, then executed in two launches:
a **probe** (4 arms × 10 seeds, seeds 45–54, $0.078) measured the between-seed variance and picked the
rung; the **resolution gate** fixed **k = 28** from that measurement before any replication spend; the
**replication** ran `A_raw` + `B_ft30` over 28 fresh seeds, 55–82 ($0.188). Evidence:
`results/20261104T123839Z/` (56 records, every one `status: success`), model
`tabpfn-v3-classifier-v3_default.ckpt` at tabpfn 8.5.0 — **unpinned**: every record reads
`version: auto`, and the checkpoint field names the file. The model that ran is v3; the record does not
claim a pin it did not have (#399 amendment, #402).

**Result.**

| | Value |
|---|---|
| Mean ΔAUC vs in-run `A_raw`, 28 seeds | **+0.0035** |
| 95% interval (between-seed SD 0.0021) | **[+0.00272, +0.00428]** |
| Brier, worst seed (guard ≤ +0.001) | +0.0003 |
| Null false-positive rate (5,000 permutations/seed) | 0.0000 |

**Decision (2026-11-04).** The pre-registered rule is met on all three conditions — interval lower
bound above zero, point estimate at or above 0.002, Brier inside the guard — and the entire interval
sits above δ. **Pass.** Fine-tuning at 30 epochs on `uslapseagent` at 10,000 rows improves ROC AUC by
about +0.0035 without degrading Brier.

**What it is worth, stated with the comparison that matters.** +0.0035 is real and small: raw TabPFN's
margin over the best actuarial baseline is **+0.068** on COIL 2000, roughly twenty times larger.
Choosing the model matters far more than tuning it, and no report may quote this number without that
measurement beside it.

**Consequence.** Per D14, a pass **publishes and stops**: no Stage 2, no breadth across the four R1
datasets, no further epoch rungs. Publication is
`docs/analyses/finetuning_replication_result.md`, with its registry row.

**Two corrections recorded rather than smoothed over.**

1. **D11's reading was the power row, not a null.** Its own §3 mapping said so; the null control
   measured a ±0.010 band against a 0.002–0.003 effect, which is what made two seeds unable to settle
   anything. This replication exists because 28 seeds can.
2. **The replication breached its $0.15 per-launch ceiling by 25%** ($0.188 against the ceiling —
   25% over, and 54% over the $0.122 projection). The projection used the probe's `B_ft30` timing on an RTX 4090 (38.9 s/seed); the
   replication ran at ~62 s/seed on an RTX PRO 4000. A projection built on one host's timings does not
   transfer. Total across the effort: **$0.308** of a $9.29 balance.

DECISION: **the replication passed (2026-11-04)** — +0.0035 AUC, 95% CI [+0.0027, +0.0043]; publish and
stop, per D14.
Owner: scotthawes  Date: 2026-11-04  Section: §3

### D16 — The owner reopens breadth, to quantify the full value of fine-tuning

**Why it matters.** D14 stopped the line after one replication, and D15 applied it. Both stand as
written. This entry records a **deliberate override** of D14's "no Stage 2 expansion even on a pass",
taken after the pass was known. It is recorded here rather than folded into a new reading because the
distinction matters: reopening after a favourable result is exactly the pattern pre-registration
exists to resist, so it must be visible as an override with named reasons, not presented as new
information.

**The reasons, in the order they weigh.**

1. **D14's headline comparison is a category mismatch.** It sets the within-model gain (+0.0035) against
   the between-model margin (+0.068) and calls the first twenty times smaller. F4 states that the
   fine-tuning gain *is* a within-model improvement, so that comparison sets a bar the question never
   raised. On its own terms — does adapting the weights add value beyond giving the model more
   context? — +0.0035 with an interval excluding zero is a genuine answer, and it currently exists on
   one dataset.
2. **One dataset is not a general finding.** `uslapseagent` is a lapse dataset, at two row counts, on
   one model line. Nothing establishes that the effect is not specific to it, and the diagnostics
   cannot settle it: D2 measured which features the families use, not what adaptation buys.
3. **The money is not what stops it.** At the measured anchors ($0.0368 for a four-arm 10,000-row
   launch), the whole programme is bounded at roughly $5 to $82, and **$0.74 of variance probes replaces
   both bounds with a measured total** before any replication is approved.

**What is authorised.** Nothing. This entry authorises a **specification**, not a run — the distinction
#300 draws for a passing gate. The specification is
`docs/current/FINETUNING_BREADTH_SPEC.md`; each launch is still approved separately on the estimate its
own probe produced, per D10.

**What this does not change.** The replication's result, its published reading, or the within-model
framing of F4. A generalised gain remains a within-model improvement: whether to fine-tune is a
different decision from which model to use, and D15's "twenty times smaller" measurement is still true
and still belongs beside any quoted effect. The diagnostics (D2–D5) continue unchanged; this entry
neither depends on them nor suspends them.

**The risk accepted, stated plainly.** D14's stop was pre-registered before the result existed, which
is part of why +0.0035 is credible. This entry reopens after the result. The mitigation is procedural
rather than rhetorical: the specification fixes the seed rule, the rung rule, the resolution gate and
the stop conditions before any spend, and the probe measures variance rather than assuming it.

DECISION: **breadth reopens as a specification (2026-11-04)** — quantify the gain on the other three R1
datasets and locate the row-scale threshold; no launch until a probe prices its own cell.
Owner: scotthawes  Date: 2026-11-04  Section: §3

### D17 — The `eudirectlapse` replication: its ceiling, its seed count, and how it is batched

**Why it matters.** The probe measured the variance, so `k` is no longer a projection. The old per-launch
ceiling ($0.15, set for the anchor's 28 seeds at $0.188) cannot carry this dataset, and the breadth spec's
own Stage 2 says to stop when `k`'s cost exceeds it. This entry takes that decision explicitly rather than
letting a terminal invocation take it.

**Measured inputs**, `results`-equivalent under `outputs/gpu-pilot/runs/` (three launches, $0.2189 total):

| Rung | mean ΔAUC | per-seed SD | `k` for δ = 0.002 | measured cost at `k` |
|---|---:|---:|---:|---:|
| `B_ft3` | +0.0012 | 0.00556 | 61 | — |
| `B_ft10` | +0.0005 | 0.00839 | 139 | — |
| **`B_ft30`** | **+0.0037** | **0.01100** | **238** | **≈ $2.95** |

The rung rule picks the highest probe mean, so **`B_ft30`** carries the verdict: **238 fresh seeds**. The
only reason `k` is eight times the anchor's is noise — this dataset's per-seed SD is ~3× the
`uslapseagent` probe's, and `k` scales with its square.

**Decision (2026-11-04).**

1. **Ceiling raised** for breadth replication launches: **$0.60 per launch**, from $0.15. One thirty-seed
   batch is ≈ $0.37 at the measured 153 s for `B_ft30`, so the ceiling carries a batch plus margin.
2. **Design fixed:** `A_raw` + `B_ft30` only (the anchor's replication shape — no ladder, no baselines), at
   10,000 train / 1,000 test, stratified split, **seeds 93–330** (fresh: the probe's 83–92 are estimation,
   not evidence, exactly as D13 kept the anchor's probe and replication seeds disjoint).
3. **Batched, not one launch.** One seventeen-hour launch concentrates every failure into one loss; a
   batch concentrates it into one batch. Each batch is pulled and verified before the next starts, so a
   lost batch is re-run rather than re-derived.

   **Amended the same day, after the first batch failed.** The first batch was thirty seeds and took
   **46.35 min** — over `vast_run.sh`'s **40-minute completion poll** (120 × 20 s), so the launcher
   exited non-zero, the `EXIT` trap destroyed the instance, and **no artifacts were pulled**: $0.2051
   and 46 minutes of compute lost. Batch size is now **twenty seeds** (measured ~86 s/seed at two arms,
   so ~29 min of compute plus ~3 min of boot), giving twelve batches: eleven of 20 and one of 18. The
   ceiling is a property of the launcher, not of the design, and it is now the binding constraint on
   batch size until `vast_run.sh` can be told a run needs longer.

> **2026-11-09** (#520). This is the **plan**. Twenty launches of twelve seeds ran (D18's "What was run"), and the change
> from twenty to twelve is recorded nowhere in the tree. See the note at D18.
4. **Operational controls.** `caffeinate` around each launcher invocation, because a sleeping machine
   suspends the launcher and the instance keeps billing; and a `vastai show instances` check before and
   after each batch, standing in for the watchdog #328/#367 still owe.

**Analysis precondition, named now so it is not discovered late.** `scripts/analyses/verdict.py` reads one
run; batching produces eight. The per-seed records must be pooled before the reading is computed, and that
pool is a small tool change. It blocks the **verdict**, not the run — but it must land before the result is
claimed, and the fresh permutation null runs on the pooled capture.

**What this does not do.** It does not price `coil2000` or `spanish_motor_lapse`. On the probe's figures
`spanish_motor_lapse` projects to ~512 seeds (≈ $6.3 at two arms) and `coil2000` is unmeasured, so the full
three-dataset programme still exceeds the $8.73 balance by some margin. This entry authorises **one**
dataset's replication and nothing else.

> **2026-11-09** (#520). A projection, and wrong by two orders of magnitude: the cell completed for **$0.065**
> (D20), because it priced a resolution figure rather than a variance figure nobody had measured.

DECISION: **`eudirectlapse` replication authorised (2026-11-04)** — `B_ft30`, 238 fresh seeds (93–330),
twelve batches planned, twenty launches run, $0.60 per launch ceiling, ≈ $2.95 and ≈ 11 h total.

> **2026-11-09** (#520). Corrected: this line read "eight batches", which matches neither the body above (twelve)
> nor the execution (twenty launches of twelve seeds, D18's "What was run"). The ≈ $2.95 here is also a
> projection: D18 records the cell at $4.30 across 29 launches.
Owner: scotthawes  Date: 2026-11-04  Section: §3

---

### D18 — Breadth, first dataset: the gain does not generalise — equivalence on `eudirectlapse`

**What was run.** D17's replication, in twenty paid launches — nineteen of twelve seeds, the last of
ten (238 seeds, 93–330) — two arms (`A_raw` + `B_ft30`), 10,000 training rows and 1,000 test rows,
model line asserted as `tabpfn-v3-classifier-v3_default.ckpt` before every launch. Result published as
`docs/analyses/finetuning_breadth_eudirectlapse_result.md`; evidence committed as twenty run
directories under `results/`.

> **2026-11-09** (#520). This is the **execution record, and it governs** D17's plan: twenty run directories carry
> nineteen batches of twelve seeds and one of ten. D17 planned twenty seeds per batch and never records the
> change to twelve.

**Result.**

| | Value |
|---|---|
| Mean ΔAUC, 238 seeds | **+0.0007** |
| 95% interval (between-seed SD 0.0082) | **[−0.0003, +0.0018]** |
| Seeds positive | 134 / 238 (56%) |
| ΔBrier, worst seed (guard ≤ +0.001) | +0.0010 |
| Null: SD / false-positive rate | 0.0085 / 0.0000 |
| Design needed at this SD | 132 seeds (the run carried 238) |

**Decision (2026-11-05).** The reading is **equivalence**. The interval covers zero *and* its upper
bound sits below δ = 0.002, so the effect is bounded under the bar rather than merely failing to reach
it. The instrument check passes (false-positive rate 0.0000 under permutation).

**What it settles.** On the one R1 dataset where a baseline beats TabPFN at full data — the only place
fine-tuning had a *gap to close* rather than a lead to extend — adaptation closes nothing. The anchor's
+0.0035 on `uslapseagent` is therefore dataset-specific, not a property of the model.

**What it does not settle, and what that means for the programme.** `coil2000` and
`spanish_motor_lapse` remain unmeasured; the latter projects to ~512 seeds (~$14) against a balance that
has ~$3.1 left. So breadth now stands at **one dataset answered, two unpriced**, and D16's question is
answered for the dataset that mattered most. No further launch is authorised by this entry.

> **2026-11-09** (#520). A projection, superseded by the measured **$0.065** (D20): the cell completed inside the
> balance.

**Cost, stated because it was not all well spent.** $4.30 across 29 launches, of which roughly a quarter
produced nothing — poll overruns, a launcher concurrency defect that duplicated 36 seeds and silently
attributed some batches' artifacts to others (#426), and one gated-fetch failure. The hardening is
tracked in #428; that defect, not the provider, explains the "verified but nothing on disk" batches.

DECISION: **breadth answers "no" on `eudirectlapse` (2026-11-05)** — +0.0007 AUC [−0.0003, +0.0018],
equivalence at δ = 0.002; the remaining two datasets are unpriced and not authorised.
Owner: scotthawes  Date: 2026-11-05  Section: §3

---

### D19 — Spanish cell pre-registered: no launch, no spend

*(D18 is the `eudirectlapse` result carried by #435; this entry follows it.)*

**What was run.** Nothing. This entry records a design, not a result.

**Design.** `spanish_motor_lapse`, 10,000 training rows and **10,000 test rows** — the size at which the
readiness study's P1 floor (paired half-width ≤ 0.006) is met, measured at **0.0051** on the committed
CSV by `scripts/analyses/proxy_resolution.py`. `N_claims_year` and `Cost_claims_year` are dropped from
every arm (post-outcome; 0.023 AUC). Probe: four arms × ten fresh seeds (331–340), ceiling **$0.50**.
Replication ceiling **$3.00**; `k` is filled by amendment after the probe. Document:
`docs/current/FINETUNING_PREREGISTRATION_SPANISH_2026-11.md`.

**Decision (2026-11-05).** No launch is authorised. The probe is a separate spend-gate decision; the
replication is unfunded. Both projections in the tree — ≈$6.3 (D17) and ≈$18.8 (the breadth
specification's per-dataset line) — exceed the $3.00 ceiling, so the documented default is a stop.

> **2026-11-09** (#520). ≈$18.8 is **derived**, not quoted: the breadth specification's programme line for
> three datasets at 512 seeds, divided by three. The specification states no per-dataset line.

**What it settles.** The cell has a leak-safe dataset, a measured test size, and a pre-registered gate.

**What it does not settle.** It does not answer the breadth question for Spanish and authorises no
spend.

DECISION: **Spanish cell pre-registered, nothing authorised (2026-11-05)** — 10,000/10,000, drops
applied, probe 331–340 under a $0.50 ceiling, `k` and the replication gated; default is a stop.
Owner: scotthawes  Date: 2026-11-05  Section: §3

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

DECISION (accept as written / amend): **accepted as written** (2026-10-30). Every outcome this design
can produce already has a stated reading, including the power-limited case, which is the one it is
most likely to meet.  Owner: scotthawes  Date: 2026-10-30  Section: §3

---

## Decided in review (2026-09-13)

Recorded so these are not re-argued, and so the *reason* survives with the decision -- a decision
without its reason cannot be re-checked when the situation changes. Section 1 holds what is still
OPEN; this holds what the design review settled.

### The probe (step 0)

| # | Decision | Reason |
| --- | --- | --- |
| **P1** | **Scope: one dataset.** The probe is not widened to four | The original plan stands. Four datasets would measure heterogeneity across datasets, but it moves two things at once and multiplies the cost. Deferred, not rejected |
| **P2** | **Dataset: `uslapseagent`** | Selected on **resolution, not cost**: 369 positives, resolves >= 0.009 ROC. `coil2000`, the repository's habitual first choice, resolves only >= 0.061 because 6% of its rows are positive. A null on the wrong dataset is not evidence |
| **P3** | **Scale: 2,000 train / 1,000 test only.** The 5,000-row rung is deferred | R1 parity, and this is a budget screen rather than a scale study. The 5,000-row rung is a separate decision if the ladder is positive but small |
| **P4** | **Epochs 3 / 10 / 30** | 3 = R1 parity, 10 = midpoint, 30 = the library default -- the "fair budget" nobody has tested |
| **P5** | **`A_raw` runs in the same pass** | Without it the probe can say only whether the budget matters, not whether fine-tuning works at all |
| **P6** | **One seed, one split** | Screening, not estimation. Three seeds is step 2, bought only on a positive |
| **P7** | **Three outcomes, not two** | A flat ladder whose arms still beat `A_raw` is not a dead programme: it is fine-tuning working with no budget effect, and it should carry **3 epochs** forward because that is cheaper |
| **P8** | **Early stopping disabled, or the executed epoch count recorded** | Otherwise "30 epochs" means "whatever early stopping allowed" and the probe measures a different quantity from the one it names. A precondition on the code, not a preference |
| **P9** | **The `ft3` rung is a replication gate** | R1 measured +0.0014 on coil2000 and -0.0008 to +0.0095 across the four. If `ft3` misses that band the pipeline has changed and nothing else in the run is interpretable |
| **P10** | **Every result is reported with its minimum detectable effect** | So a null is never read as evidence of absence beyond the resolution the test actually had |
| **P11** | **The budget is recorded as row-epochs** (training rows x epochs), not as epochs alone | An epoch is one pass over the split, so the same epoch count means different amounts of training at different scales: 30 epochs is 60,000 row-passes at 2,000 rows and 150,000 at 5,000. Without row-epochs, a future run at another scale can return a different answer under the same label and the two cannot be compared |
| **P12** | **The probe is a separate pilot, and it runs from merged code on `main`** | Kept separate so its result GATES the wider testing instead of being folded into it -- and run post-merge so the result references reviewed code at a recorded commit rather than an unmerged branch |

### Cost discipline

| # | Decision | Reason |
| --- | --- | --- |
| **C1** | **No programme-scale figure is quoted** | The one that existed stacked three unmeasured assumptions and read as a cost. A figure for that scope returns only when derived from measurements |
| **C2** | **Every figure states its basis** -- measured or modelled -- **and what would make it a measurement** | The single assumption is named: cost versus training length, which the probe measures |
| **C3** | **R1's total spend is not a planning figure** | Only ~8p of 53p produced a result; the rest bought a working pipeline. The planning figure is the marginal cost of a successful comparison |
| **C4** | **Controls are described by what is proven, not what is built** | Implemented and unit-tested is not the same as exercised on real hardware, and the watchdog's firing is scheduled rather than observed |

The parameters these decisions produce are tabulated in `docs/reference/PILOT_2_DECISION_GRAPH.md` under *Step 0 in
full*, with a reason beside every value.

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
- [ ] `docs/current/FINETUNING_PREREQUISITES.md` counts re-checked after the build (PR-1, PR-3, PR-9 still await
      one real box; see the Gate Amendment there)

---

## Current programme decisions

These are the decisions required before the next run.

| ID | Decision | Status |
|---|---|---|
| P1 | Core arm set (`A_raw`, `B_ft3`, `B_ft10`, `B_ft30`) | Proposed |
| P2 | Anchor dataset and row count (`uslapseagent`, 10K) | Proposed |
| P3 | Anchor seed count (three total, including seed 42) | Proposed |
| P4 | Breadth datasets (four R1 datasets) | Proposed |
| P5 | Breadth row counts (2K and 10K where available) | Proposed |
| P6 | Calibration tolerance and minimum effect | Required before execution |
| P7 | Conditional PEFT and data-treatment arms | Deferred pending P1–P5 |
| P8 | Transfer and pooling | Deferred pending in-domain replication |

---

> **Superseded 17 Sep.** This recorded the probe at 2,000 training rows, where fine-tuning did not beat
> raw. At 10,000 rows every rung beat raw, intervals excluding zero, monotone in epochs. The measurement
> below stands as the 2,000-row result; it is not the current answer. See the front section of
> `docs/current/FINETUNING_EXPERIMENT_REFERENCE.md`.

## P13 — the probe's outcome, and what it stands down

**Settled by measurement:** the in-domain fine-tuning hypothesis is dead at 2,000 training rows. The epoch
ladder is flat and the arms do not beat `A_raw` on the pre-registered primary; the one signal moving in
order is calibration. Which pre-registered outcome that is, and the evidence, are in `docs/current/FINETUNING_PROBE_RESULTS.md`.

**Stood down as a consequence:** D1 (transfer leakage), D2 (pool rule), D3 (dataset count), D5 (pool row
source), D8 (label harmonisation). Every one was contingent on in-domain fine-tuning showing a gain. None is
worth a team decision now, and leaving them open would imply a programme the first gate has already stopped.

**Still live:** the calibration tolerance (D6). If a follow-up asks about probabilities rather than ranking,
that number has to be set in advance -- an unset tolerance is not a pre-registration.

### D20 — Breadth, second dataset: equivalence on `spanish_motor_lapse`

**What was run.** D19's cell, amended after the probe (#466). A probe of four arms × seeds 331–340 to
measure the between-seed SD and the real cost, then a replication of arms `A_raw` + `B_ft30` over fresh
seeds **341–356**, 10,000 train / 10,000 test, `v3_default` asserted before each launch. Result published
as `docs/analyses/finetuning_breadth_spanish_result.md`.

**Result.**

| | Value |
|---|---|
| Mean ΔAUC, 16 seeds | **+0.00029** |
| Between-seed SD | 0.00093 |
| 95% interval | **[−0.00021, +0.00078]** |
| Seeds positive | 11 / 16 |
| ΔBrier, worst seed (guard ≤ +0.001) | +0.00034 |

**Decision (2026-11-06).** The reading is **equivalence**: the interval covers zero *and* its upper bound
sits below δ = 0.002, so the effect is bounded under the bar rather than merely failing to reach it.

**What it settles.** Two of the three datasets now measured bound the effect under δ — `eudirectlapse`
(D18) and this one — against a single gain on `uslapseagent` (+0.0035). The anchor's effect is twelve times
this dataset's point estimate, so it reads as **dataset-specific rather than a property of the model**.

**What it corrects.** D18 projected **~512 seeds (~$14)** for this dataset, from the **1,000-test-row**
half-width the readiness study measured and **rejected**. The probe measured the between-seed SD at
**0.0012**, which the pre-registered rule turns into `k = 3`; the replication ran at 16 for margin over SD
uncertainty and completed for **$0.065**. The projection was wrong by roughly two orders of magnitude
because it substituted a *resolution* figure from a configuration nobody runs for a *variance* figure
nobody had measured.

> **2026-11-09** (#520). This sentence read "~$9.50", which D18 never said — D18 projects **~$14**. Corrected so
> that a reader tracing the figure to D18 finds it.

**Cost.** $0.3315 across the cell (balance $3.1127 → $2.7812): $0.043 to measure one seed, $0.153 for the
probe across five attempts of which three failed on selection rather than on the infrastructure, and $0.065
for the replication. **The ledger is not a reliable cost record** — it disagreed with the credit balance in
both directions across the two launches, so figures here come from the balance.

DECISION: **breadth answers "no" on `spanish_motor_lapse` (2026-11-06)** — +0.00029 AUC [−0.00021,
+0.00078], equivalence at δ = 0.002; `coil2000` remains unmeasured.
Owner: scotthawes  Date: 2026-11-06  Section: §3

---

### D21 — Breadth stops on `coil2000`: resolution, not money

**What was run.** Nothing. A resolution measurement on the committed CSV:
`scripts/analyses/proxy_resolution.py --csv data/raw/coil2000.csv --target CARAVAN`, three split seeds per
size, 2,000 paired bootstrap resamples. Cost: **$0**.

**Why it was measured at all.** D20's cell completed for $0.065 after a $0.10 probe replaced a projection
that had been wrong by two orders of magnitude. The cheapest lesson from that is to check resolution
*before* declaring or funding a cell, so `coil2000` was checked before any spend.

**Result — the floor is not reachable at any size this dataset allows.**

| Train / test | Median half-width | Max | Against the 0.006 floor |
|---|---|---|---|
| 7,200 / 1,000 | 0.0240 | 0.0266 | 4.0× |
| 6,200 / 2,000 | 0.0202 | 0.0205 | 3.4× |
| 5,200 / 3,000 | 0.0183 | 0.0183 | 3.1× |
| **4,200 / 4,000** | **0.0149** | **0.0158** | **2.5×** |

**Decision (2026-11-06).** **Stop.** `coil2000` cannot be measured at the resolution the breadth design
requires, and no budget changes that.

**Why money cannot fix it.** The binding constraint is **586 positives** in a 9,822-row dataset. The Spanish
cell reached 0.0051 with 3,540 positives at 10,000 test rows; `coil2000` has a sixth of that, and the
half-width moves only 0.024 → 0.015 as the test set quadruples. Between-seed replication (`k`) tightens the
*seed* variance, not the *test-set* floor, so no seed count resolves a cell whose floor sits at 0.015 against
a δ of 0.002. Every outcome would read "unresolved" by construction.

**What breadth now says, complete.**

| Dataset | ΔAUC | 95% interval | Reading |
|---|---|---|---|
| `uslapseagent` (anchor) | +0.0035 | [+0.00272, +0.00428] | gain |
| `eudirectlapse` (D18) | +0.0007 | [−0.0003, +0.0018] | equivalence |
| `spanish_motor_lapse` (D20) | +0.0003 | [−0.0002, +0.0008] | equivalence |
| `coil2000` | — | — | **unresolvable; stopped on resolution** |

Three of four datasets are answered and two of those bound the effect under δ. `coil2000` is closed on a
property of the dataset rather than a property of the experiment — a different and more durable reason to
stop, which is why it is recorded here rather than left as an unstarted ticket.

DECISION: **breadth closes — `coil2000` stopped on resolution (2026-11-06)** — median half-width 0.0149 at
the largest usable split against a 0.006 floor and δ = 0.002; 586 positives, so no budget resolves it.
Owner: scotthawes  Date: 2026-11-06  Section: §3

### D22 — Phase 2 closes: the threshold is a resolution stop, and D21's seed inference is withdrawn

**What was run.** Four resolution measurements on the committed CSVs, at the 2,000-row cells' own
configuration — 2,000 train / 1,000 test rows, three split seeds, 2,000 paired bootstrap resamples, via
`scripts/analyses/proxy_resolution.py`. Cost: **$0**. The 10,000-row cells were not re-run; their results
stand (D14, D18, D20, D21).

| Dataset | Median half-width at 2,000 / 1,000 | Max | Against the 0.006 floor |
|---|---:|---:|---|
| `uslapseagent` | **0.0058** | 0.0060 | **clears it** — the only dataset that does |
| `spanish_motor_lapse` | 0.0167 | 0.0196 | 2.8× |
| `coil2000` | 0.0298 | 0.0307 | 5.0× |
| `eudirectlapse` | 0.0341 | 0.0382 | 5.7× |

**What it settles — Phase 2 is complete as run.** The pilot design's matrix asks two things: does in-domain
fine-tuning generalise, and where does the row-scale threshold sit. The first is answered at 10,000 rows on
three of four datasets. The second is answered only for `uslapseagent`, whose 2,000-row probe already lost
(−0.0025 on `B_ft3`) against its 10,000-row gain (+0.0035); for the other three the threshold cell cannot
resolve δ = 0.002 at the design's 1,000 test rows, so running it would not answer the question.

| Dataset | 10,000-row cell | Reading |
|---|---|---|
| `uslapseagent` | +0.0035 | gain |
| `eudirectlapse` | +0.0007 | equivalence |
| `spanish_motor_lapse` | +0.0003 | equivalence |
| `coil2000` | — | stopped on resolution (D21) |

**What it corrects.** D21 closes with "586 positives, so no budget resolves it", and its body argues that
"no seed count resolves a cell whose floor sits at 0.015 against a δ of 0.002". That inference puts a
**resolution half-width** where a **between-seed SD** belongs. They are different quantities, and D20 already
records what happens when they are confused: substituting a 1,000-test-row half-width for an unmeasured SD
inflated this programme's seed projection from `k` = 3 to ~512, and the cell then completed for **$0.065**.
`coil2000` was never probed — D21's own first line is "What was run. Nothing." — so its between-seed SD is
**unmeasured**, not infinite.

What survives is the part that never needed the seed argument: `coil2000` fails the design's P1 gate (paired
half-width ≤ 0.006) at every size the dataset allows — 0.0240 at 1,000 test rows down to 0.0149 at 4,000. The
stop is correct on resolution alone. **D21 is left untouched as history**; this entry records the correction,
the way D20 recorded its correction to D18.

**What this does not do.** It does not reopen or probe `coil2000`: a four-arm ten-seed probe would cost about
what the Spanish one did ($0.153), and the resolution gate refuses the cell before a probe would be
informative. It does not run the 2,000-row cells — three cannot resolve, and the one that can has already
answered negatively. It does not run a synthetic ablation: the scope map places that in "Phase 1 /
confirmatory follow-up, where diagnostics justify it", and D3/D4 have never run.

**Recorded limitation — the `eudirectlapse` rung.** Its equivalence (+0.0007) was replicated at `B_ft30`
only. The probe measured all three rungs — `B_ft3` +0.0012, `B_ft10` +0.0005, `B_ft30` +0.0037 — but every
interval covers zero and the ladder is non-monotone, so "30 was highest" sits inside the noise of a ten-seed
estimate. A `B_ft3` replication would settle it at `k` = 61 against 238, and is **not funded**; the result
stands as a statement about `B_ft30`. `spanish_motor_lapse` does not share this weakness — its ladder was
monotone (−0.0006 / −0.0002 / +0.0008), so carrying the top rung was the conservative choice.

DECISION: **Phase 2 closes (2026-11-07)** — the 10,000-row question is answered on three of four datasets;
the 2,000-row threshold is a resolution stop for three of four (0.0167 / 0.0298 / 0.0341 measured against a
0.006 floor at 1,000 test rows) and already answered negatively for `uslapseagent`; and D21's seed-cost
inference is withdrawn as a resolution-for-variance substitution, leaving the `coil2000` stop resting on the
P1 gate alone.
Owner: scotthawes  Date: 2026-11-07  Section: §3

---
