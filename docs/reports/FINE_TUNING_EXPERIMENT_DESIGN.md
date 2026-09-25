# Experiment Design: Insurance-Specialized TabPFN Fine-Tuning (v6)

---

## The design being proposed (read this first — everything below is reference)

**Status.** This document is v6, written before the probe. The sections below are the original plan and are
kept as reference. **This section is what is proposed now, and where the two disagree, this one wins.**

### The question

Does fine-tuning beat raw TabPFN for **lapse classification**, and under what conditions? Whether it helps at
all was settled for one configuration; what remains is the conditions under which it does.

### What we already know, measured in this repository

- At **2,000 training rows**, full SFT did not beat raw: all three rungs at or below baseline, the
  pre-registered outcome 3 of 3.
- At **10,000 training rows**, all three rungs beat raw, intervals excluding zero, monotone in epochs:
  **+0.0022 / +0.0026 / +0.0034** ROC AUC, with Brier improving in step. One seed, one split.
- So the earlier negative was a **small-data artefact**, and the row cap was ours: the model is documented
  for 50,000 samples, and the loader defaulted to 2,000.
- Raw TabPFN already leads the competing baselines on `uslapseagent` (0.9363 against 0.9271 GLM, 0.9297
  CatBoost), so any gain is a **within-model** improvement, not the closing of a gap to another method.

### The design

|  |  |
| --- | --- |
| scope | lapse only: `uslapseagent`, `spanish_motor_lapse`, `eudirectlapse` |
| rows | lifted from the 2,000 default to 10,000+; `A_raw` re-measured in every run |
| arms | `A_raw` always in-run, versus full SFT, plus one parameter-efficient or meta-learning arm |
| staging | one dataset first; the others only if the first holds |
| seeds | 2-3, sized against the measured 0.0003 run-to-run spread |
| primary metric | ROC AUC; Brier and ECE reported separately, never folded in |
| pre-registered | a numeric calibration tolerance, stated before the run |
| analysis | paired bootstrap intervals, inverse-variance summary, Holm across the dataset family |
| cost | measured, not modelled: about **$0.037** for a four-arm run at 10,000 rows |

### Decision rules

- **Continue** if a rung beats in-run `A_raw` with an interval excluding zero, and repeats on a second seed.
- **Stop the line** if the rungs are flat or worse across two seeds on two datasets.
- **Escalate to the other lapse datasets** only after a positive result replicates on one.

### Limitations, stated alongside the design rather than discovered afterwards

1. **No temporal split is available** in any lapse dataset: none carries a usable time index. Every result is
   therefore conditional on a random split. A real limit, not an oversight.
2. **One seed so far.** The paired intervals are within-run and say nothing about seed variation.
3. **The row cap is ours.** 10,000 was chosen; the model documents 50,000.
4. **The literature is a generation behind.** The fine-tuning studies are TabPFNv2-based; we run the v3
   checkpoint, so their guidance transfers as an assumption.
5. **Spanish-data leakage risk.** Portfolio-level features against a policy-level target, which our split and
   context assertions do not cover.

### What is not being proposed

The 15-dataset sweep, the factorial N x train-ratio extension, the pooling arms, the transfer stage, and the
temporal-split test. Each is either out of scope for lapse, or contingent on a positive result that does not
yet exist. The reasons are in the sections below and in `TABPFN_FINETUNING_LITERATURE.md`.


> Date: 2026-09-11 | Status: **R1 complete — smoke test only; R2, R3 and Q4/Q5 not run** | Related: #22, #129, #156, #159
> Builds on: PRE_FINETUNING_INVESTIGATIONS.md, master report (v3, canonical folds)
>
> **Reconciled 2026-09-12.** R1 has now run. Read the outcome alongside this design:
> - **`SMOKE_TEST_SCOPE.md`** — what R1 proved and, more importantly, what it never exercised
>   (notably **arms C/D, so the transfer question in the Research Question below is still
>   untested**). Also records where R1 deviated from this design.
> - **`FINE_TUNING_PILOT_RESULTS.md`** — the R1 numbers (§5c) and their statistical limits (§5d).
>
> The `R3 Gate` in this document is the pre-specified decision rule for advancing rungs. R1
> evidence (arm B ≈ arm A, both inside the noise floor) points to its "otherwise stop" branch,
> but the gate is specified on R2 and **R2 has not been run** — so it has never been formally
> evaluated. Do not cite R1 as a gate decision.
>
> Deviations of R1 from this design: split was a fixed 2,000/1,000 cap rather than 70/30; the
> 15% validation split was not implemented; `context_samples` was recorded but used by neither
> arm; arms C/D were not run; R1 cost $0.34 on Vast rather than $0 on Colab T4 (T4 was 503).

---

> **Historical document.** Superseded by `PILOT_2_DESIGN.md` and `PILOT_2_DECISION_GRAPH.md`
> (2026-09-13). Kept for the record -- **do not reconcile it against the current design**, which
> is the front section above. The body below is archived for reference only, at
> `docs/reports/archive/FINE_TUNING_EXPERIMENT_DESIGN_BODY.md`.
