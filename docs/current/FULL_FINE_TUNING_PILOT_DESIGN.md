# Full Fine-Tuning Pilot — Design and Decision Framework

> Date: 2026-09-24 | Status: **Funded research workstream — design to be executed**
> Related: #22 | Follows the two measured probes documented in `FINDINGS.md`
> Diagnostics: `docs/current/DIAGNOSTICS_PHASE_DESIGN.md`
> Status summary: `docs/current/FINETUNING_STATUS_BRIEF.md`

---

## 1. Purpose

The two probes establish a useful but incomplete result:

- At **2,000 training rows**, full supervised fine-tuning did not beat raw TabPFN.
- At **10,000 training rows**, full supervised fine-tuning beat raw TabPFN at 3, 10, and 30 epochs, with paired intervals excluding zero and calibration improving alongside ranking.

This is a hypothesis about a data-scale threshold, not yet a general finding about TabPFN on insurance data. The full pilot must determine whether the 10K result is robust, whether it is caused by genuine domain adaptation, and whether preprocessing, feature engineering, class imbalance, or target definition explain part of the effect.

This is an authorized, funded workstream. The stages below are scientific decision boundaries, not requests to release new funding.

---

## 2. Research questions

1. Does the 10K-row gain reproduce across seeds and splits?
2. Does it reproduce across the four R1 classification datasets?
3. Is the effect primarily discrimination, calibration, or both?
4. Is ordinary full supervised fine-tuning sufficient, or does a parameter-efficient method add value?
5. Does the gain survive better preprocessing, feature screening, and class-imbalance treatment?
6. Is the result a genuine in-domain adaptation effect, or an artefact of the experiment design?

The pilot answers the in-domain question. A separate transfer proposal may follow only if the in-domain result is credible.

---

## 3. Work phases

### Phase 1 — Diagnostics

Run the five diagnostics in `docs/current/DIAGNOSTICS_PHASE_DESIGN.md` before drawing conclusions from the pilot.

The diagnostics cover:

1. dataset structure and target distributions;
2. feature-importance differences between TabPFN, GLM, and tree models;
3. target reframing where count or frequency targets are involved;
4. preprocessing and feature-engineering ablations;
5. a focused `eudirectlapse` investigation.

Diagnostics are not a substitute for the fine-tuning pilot. They identify confounds and determine which fine-tuning comparisons are meaningful.

### Phase 2 — Full in-domain fine-tuning pilot

The pilot uses the existing two probes as fixed reference conditions:

| Condition | Rows | Role |
|---|---:|---|
| Probe 1 reference | 2,000 | Reproduce the low-data negative regime |
| Probe 2 reference | 10,000 | Test the positive regime discovered by Probe 2 |
| Scale extension | larger available size, if practical | Determine whether improvement saturates |

The primary dataset is `uslapseagent`, because it produced the 10K positive result. The pilot then tests the same protocol on the other three R1 datasets:

- `coil2000`;
- `eudirectlapse`;
- `spanish_motor_lapse`.

The four-dataset family is the in-domain pilot scope. A wider 15-dataset sweep, pooled training, and cross-dataset transfer are not part of this pilot.

### 3.1 Experimental arms

| Arm | Description | Purpose |
|---|---|---|
| `A_raw` | Unmodified TabPFN | In-run control |
| `B_full_sft` | Full supervised fine-tuning | Main intervention |
| `C_data_treatment` | Class weighting, resampling, or calibration treatment | Separate data treatment from weight adaptation |
| `D_parameter_efficient` | Parameter-efficient adaptation or meta-learning | Test whether a smaller intervention is sufficient or superior |

`A_raw` is re-run in every condition. Fine-tuning is always compared with the raw model measured in the same run, not with a result imported from another split.

The main question is whether standard full fine-tuning is sufficient. The parameter-efficient arm is a comparison point, not a requirement for the main conclusion.

### 3.2 Training design

- Epoch budgets: 3, 10, and 30.
- Early stopping state is recorded explicitly.
- Training-row count is recorded for every run.
- Random seeds and split identifiers are persisted.
- The same preprocessing is used within each controlled comparison.
- Any class weighting or resampling is recorded as a separate arm.
- No result is promoted from a single run without a replication or an explicit limitation.

At minimum, run two additional seeds for the 10K `uslapseagent` condition. The two existing probes remain evidence, but the pilot must establish seed stability before making a general claim.

### 3.3 Metrics

Probability quality is primary because insurance decisions depend on usable probabilities:

| Priority | Metrics |
|---|---|
| Primary | Brier score, log loss, calibration error |
| Secondary | ROC AUC, PR AUC |
| Diagnostic | Prediction distributions, subgroup error, calibration by score band |

Report discrimination and calibration separately. A fine-tuned model that improves ROC AUC while worsening calibration is not a general performance improvement for pricing or probability decisions.

The existing GLM and tree baselines remain comparison points. Fine-tuning is not being treated as a replacement for every baseline; it is being tested as an in-domain improvement to TabPFN.

---

## 4. Decision framework

These are interpretation rules, not funding gates.

| Result | Interpretation |
|---|---|
| 10K gain does not reproduce on additional seeds | Treat Probe 2 as unstable or split-specific |
| Gain repeats on `uslapseagent` but not other datasets | Treat the effect as dataset-specific |
| Gain repeats across datasets | Fine-tuning has credible in-domain value |
| Gain disappears after preprocessing or feature treatment | The main lever is data preparation, not model adaptation |
| Gain is mainly calibration | Consider fine-tuning for probability use cases, not ranking claims |
| Gain is mainly ranking | Treat probability deployment as unresolved |
| No gain remains after diagnostics and replication | Stop or narrow the fine-tuning line |

No single metric, seed, or dataset is allowed to determine the conclusion by itself.

---

## 5. Expected outputs

The pilot will produce:

1. a dataset diagnostic report;
2. a preprocessing and feature-engineering comparison;
3. a row-count × dataset × epoch experiment matrix;
4. raw-versus-full-SFT paired results;
5. calibration and ranking results for each arm;
6. seed-to-run variation;
7. comparison with GLM and tree baselines;
8. a recommendation by use case: lapse probability, risk ranking, underwriting triage, or other insurance decisions;
9. a clear statement of what remains untested, especially cross-dataset transfer and temporal validation.

---

## 6. Boundaries

This pilot does not:

- claim that a random split is equivalent to a temporal split;
- treat one seed as proof of generalisation;
- infer that a 10K result automatically applies to 50K rows;
- claim that fine-tuning is superior where a simple GLM already captures the signal;
- include cross-dataset transfer, pooled training, or the full 15-dataset sweep;
- replace the diagnostics with a single fine-tuning score.

No lapse dataset currently provides a usable time index, so all results remain conditional on the available random-split protocol.

---

## 7. Relationship to the existing documents

| Document | Role |
|---|---|
| `docs/current/FINDINGS.md` | Current claims and their evidence status |
| `docs/current/FINETUNING_STATUS_BRIEF.md` | Stakeholder-facing summary of the two probes |
| `docs/current/DIAGNOSTICS_PHASE_DESIGN.md` | Phase 1 diagnostic work |
| `docs/current/FINE_TUNING_EXPERIMENT_DESIGN.md` | Technical experiment design and caveats |
| `docs/current/PILOT_2_COST_AND_CONTROLS.md` | Measured cost accounting |
| `docs/current/PILOT_2_STATISTICAL_ANALYSIS_PLAN.md` | Statistical analysis rules |
| `docs/current/PILOT_2_DECISION_LOG.md` | Decisions and owners |

This document is the full in-domain pilot design. It supersedes the narrower “replicate one seed first” framing in earlier proposal text, while retaining that replication as the first robustness step of the pilot.
