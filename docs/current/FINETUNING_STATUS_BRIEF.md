# Fine-Tuning Investigation — Status Brief

> **Status:** current as of 2026-11-05.


> Date: 2026-09-24 | Status: **Two probes complete; funded diagnostics and full pilot defined**
> Related: #22 | Stakeholder summary; full design in `docs/current/FINETUNING_PILOT_DESIGN.md`

> **Superseded for the outcome (2026-11-08).** This page is the pre-result narrative — how the programme
> arrived at the Phase 2 answer. The answer itself is owned by the closing report, not by this page. Note one
> thing before quoting it: the summary table below still says the anchor rests on one seed, and the
> replication further down this same page supersedes that sentence. The table is left as it was written,
> because a document that edits its own history cannot be checked against it.

---

## What we found — two probes, two answers

### Probe 1 (Sep 12, $0.05) — the R1 smoke test

Fine-tuned TabPFN on four insurance classification datasets at **2,000 training rows** using a GPU. This was the first time the fine-tuning path ever completed successfully — a code defect had silently prevented it from running in all prior attempts.

**Result: a small fine-tune changed nothing measurable.**

| Dataset | Raw TabPFN | Fine-tuned | Delta |
|---|---|---|---|
| COIL 2000 (NL) | 0.7675 | 0.7690 | +0.001 |
| EU Direct Lapse | 0.5881 | 0.5976 | +0.010 |
| Spanish Motor Lapse | 0.7233 | 0.7272 | +0.004 |
| US Lapse Agent | 0.9363 | 0.9355 | −0.001 |

Every delta ≤0.01 ROC AUC — inside the noise floor. **Meanwhile, raw TabPFN's advantage over the best actuarial baseline is an order of magnitude larger: +0.068 on COIL 2000 vs +0.001 from fine-tuning.**

### Probe 2 (Sep 13, $0.01) — the budget probe

Ran the same test at **10,000 training rows** on `uslapseagent` — the dataset where fine-tuning most consistently showed a signal. Three epoch rungs: 3, 10, 30 (the library default).

**Result: fine-tuning beat raw TabPFN at every budget level.**

| Epochs | ROC AUC delta | 95% CI | Brier |
|---|---|---|---|
| 3 | +0.0022 | excludes 0 | improving |
| 10 | +0.0026 | excludes 0 | improving |
| 30 | +0.0034 | excludes 0 | improving |

Monotone in epochs — more training buys more gain. **The earlier negative was a small-data artefact**: the 2,000-row loader cap starved the model. The library documents 50,000 samples; we were using 2,000.

The research context from Molnar's [*Tabular Foundation Models*](https://tabularfoundationmodels.com/) reinforces two design choices: raw TabPFN is an in-context predictor that already uses the supplied table, and synthetic pretraining tasks are not the same thing as synthetic augmentation in our fine-tuning data. The pilot therefore compares fine-tuning with matched raw in-context prediction and treats prior mismatch as a diagnostic question.

---

## What this means

| Finding | Status |
|---|---|
| At 2K rows, fine-tuning doesn't help | **Superseded** — a small-data artefact of our own row cap |
| At 10K rows, fine-tuning beats raw TabPFN | **Current** — one seed, one split, paired intervals excluding zero |
| Raw TabPFN already leads competing baselines | **Current** — any fine-tuning gain is a within-model improvement |
| The epoch ladder is flat at 2K rows | **Current at 2K** — but not at 10K, where it's monotone |

---

## What we're doing next

**Complete — the replication passed (2026-11-04).** Fine-tuning at 30 epochs on `uslapseagent` beats
the in-run raw baseline by **+0.0035 ROC AUC**, 95% interval **[+0.0027, +0.0043]**, Brier no worse.
That is twenty times smaller than raw TabPFN's +0.068 margin over the best actuarial baseline, and per
D14 the line stops here: published, not expanded. Evidence: `results/20261104T123839Z/` and
`docs/analyses/finetuning_replication_result.md`. The paragraph below records the state before the run.

**Breadth has its first answer, and it is negative (2026-11-05, D18).** On `eudirectlapse` — the one R1
dataset where a GLM beats TabPFN at full data — 30-epoch fine-tuning moves ROC AUC by **+0.0007**
[−0.0003, +0.0018] across **238 seeds**: below the pre-registered δ = 0.002 and not separable from zero.
That is an **equivalence** reading, not a failure to reach the bar. The anchor's +0.0035 on
`uslapseagent` therefore looks dataset-specific. `coil2000` and `spanish_motor_lapse` remain unmeasured;
the second needs ~512 seeds (~$14), which the remaining balance does not cover. Result:
`docs/analyses/finetuning_breadth_eudirectlapse_result.md`; evidence committed under `results/`.

*2026-11-09: a historical projection. The Spanish cell completed for $0.065 (D20), inside the balance.*

**Breadth reopened as a specification (2026-11-04, D16).** The owner has amended D14's "no expansion
even on a pass" so that the full value of fine-tuning can be quantified: whether the gain holds on
`coil2000`, `eudirectlapse` and `spanish_motor_lapse`, and where the row-scale threshold sits between
2,000 and 10,000 rows. **Nothing is authorised to run.** The specification is
`docs/current/FINETUNING_BREADTH_SPEC.md`: it fixes the arms, the seed rule and the stop conditions
before any spend, and it opens with **$0.74 of variance probes** that replace its own cost range with a
measured total. The replication's result and its within-model framing are unchanged; this reopens what
to measure, not what the +0.0035 means.

**Continued once (2026-11-03, superseded by the result above).** The two-seed anchor did not replicate: seed 43 cleared all three
rungs, seed 44 cleared none. That stop was recorded as a null, and it was not one — a null control over
the anchor's committed capture shows the design resolves **±0.010** against a **0.002–0.003** effect, so
it could not tell "no effect" from "no power". D11 is restated accordingly in
`FINETUNING_DECISION_LOG.md`, and one pre-registered v3_default replication is authorised at about **$0.23**
measured (a $0.15-per-launch ceiling), with **no expansion afterwards** (D14). Its design is D13; its threshold is D12; its evidence is
`results/20261031T021845Z/` and `docs/analyses/null_control_scoring_path.md`.

The redirect is **calibration, preprocessing, and task-specific model selection** — not further
fine-tuning at this scale. The diagnostics remain open and now serve explanation rather than a gate.

The historical sections below are kept as they were, so this document still records what was being
asked before the result arrived.

---

**The decision that was requested before the run:** approve the core arm set and staged scale.

| Core arms | Description |
|---|---|
| `A_raw` | Raw TabPFN control |
| `B_ft3`, `B_ft10`, `B_ft30` | Full supervised fine-tuning at 3, 10, and 30 epochs |
| `E_glm`, `F_catboost` | Existing reference baselines |

**Staged scale:**

1. **Anchor:** replicate the 10K `uslapseagent` result on two additional seeds (3 seeds total).
2. **Breadth:** if the anchor replicates, run the same core arms on the four R1 datasets at 2K and 10K rows where available.
3. **Scale extension:** if breadth is positive, test larger available row counts.
4. **Transfer:** only after in-domain replication, test same-schema pooling and then heterogeneous pooling.

Class weighting, resampling, PEFT, synthetic augmentation, and transfer are conditional follow-ups, not part of the core in-domain decision.

**Superseded 2026-11-03 (D14).** Steps 2–4 above are **not authorised**: a pass publishes and stops,
because a 0.002–0.003 effect is about 20 times smaller than raw TabPFN's margin over the best actuarial
baseline. The immediate question is not whether fine-tuning generalises across the four R1 datasets. It
is whether the 10K result exists at all, on a design that can see it.

---

## Research decisions to record before execution

| # | Question | Working decision |
|---|---|---|
| 1 | What is the primary pilot dataset? | `uslapseagent`, because it produced the 10K positive result |
| 2 | Which datasets form the in-domain family? | The four R1 datasets: `coil2000`, `eudirectlapse`, `spanish_motor_lapse`, `uslapseagent` |
| 3 | What counts as a meaningful gain? | Pre-register a calibration tolerance and minimum practical effect before the pilot |
| 4 | How will model adaptation be separated from data treatment? | Record preprocessing, class weighting, resampling, synthetic augmentation, and row count as explicit factors |
| 5 | When can transfer and pooling be considered? | Only after the in-domain result is credible across seeds and datasets |
| 6 | What is the primary transfer pool? | Coherent same-schema pooling first; heterogeneous pooling second, with the `T_RANDOM_LABELS` control |

---

## Evidence files

| File | What it is |
|---|---|
| `outputs/finetune/pilot/pilot_metrics.parquet` | R1 aggregate metrics (16 rows, all 4 arms × 4 datasets) |
| `outputs/finetune/pilot/pilot_predictions.parquet` | Per-row predictions for all 12 R1 runs (12,000 rows) |
| `outputs/finetune/pilot/<dataset>/<arm>/meta.json` | Per-run config, versions, device, timings |
| `notebooks/baseline_experiments/06_synthetic_data_exploration.ipynb` | Earlier synthetic-data and augmentation evidence |

## Detailed reports

| Report | Audience | Read for |
|---|---|---|
| `docs/current/FINETUNING_PILOT_DESIGN.md` | Technical | Complete funded diagnostics-plus-pilot design and decision framework |
| `docs/archive/PILOT_2_BRIEFING.md` | Anyone | Historical five-step programme; use the full pilot design for the current scope |
| `docs/current/FINETUNING_FINDINGS.md` | Anyone | What the repository currently believes, and which document owns each claim |
| `docs/current/FINETUNING_EXPERIMENT_REFERENCE.md` | Technical | The full experiment design and decision rules |
| `docs/current/FINETUNING_COST_AND_CONTROLS.md` | Technical | Every cost figure, in units of a run we have already done |
| `docs/current/FINETUNING_STATISTICAL_ANALYSIS_PLAN.md` | Statistician | How the numbers will be computed |
| `docs/current/FINETUNING_DIAGNOSTICS_DESIGN.md` | Anyone | Why we should understand datasets before fine-tuning them |
| `docs/current/FINETUNING_DECISION_LOG.md` | Decision-makers | Historical transfer and pooling decisions, with their caveats |
| `docs/reference/PILOT_2_DESIGN.md` | Technical | Earlier transfer and pooling design used as the Phase 3 reference |
| `docs/archive/PRE_FINETUNING_INVESTIGATIONS.md` | Technical | Earlier in-domain, transfer, pooling, small-n, and synthetic-data questions |
| `docs/reference/FINE_TUNING_PILOT_RESULTS.md` | Technical | The full R1 numbers, interpretation warnings, statistical limits |
| `docs/archive/SMOKE_TEST_SCOPE.md` | Technical | What R1 did and never exercised, execution record |
| `docs/archive/HISTORIC_FINETUNING_APPRAISAL.md` | Technical | Why the prior negative verdict was confounded and unusable |
| `docs/MASTER-REPORT-DIGEST.md` §14.16 | Anyone | One-paragraph verdict in the context of the full benchmark arc |
