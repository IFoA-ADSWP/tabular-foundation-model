# Fine-Tuning Investigation — Status Brief

> Date: 2026-09-24 | Status: **R1 complete; Pilot 2 designed, awaiting team sign-off**
> Related: #22 | One-page companion to the detailed reports below

---

## What we tested (R1 — 2026-09-12)

We fine-tuned TabPFN on four insurance classification datasets using a GPU, then measured whether the fine-tuned model beat the raw model on held-out data. This was the **first time the fine-tuning path ever completed successfully** — a code defect in the hand-rolled training loop had silently prevented it from running in all prior attempts.

**Result: a small fine-tune changed nothing measurable.**

| Dataset | Raw TabPFN | Fine-tuned | Delta |
|---|---|---|---|
| COIL 2000 (NL) | 0.7675 | 0.7690 | +0.001 |
| EU Direct Lapse | 0.5881 | 0.5976 | +0.010 |
| Spanish Motor Lapse | 0.7233 | 0.7272 | +0.004 |
| US Lapse Agent | 0.9363 | 0.9355 | −0.001 |

Every delta is ≤0.01 ROC AUC — inside the noise floor. Three datasets slightly up, one slightly down. **Meanwhile, raw TabPFN's advantage over the best actuarial baseline (GLM) is an order of magnitude larger: +0.068 on COIL 2000 vs +0.001 from fine-tuning.**

---

## What this result means — and what it doesn't

### What it means

Using the foundation model as-is buys far more than adapting it. The value is in the pretrained weights, not in fine-tuning them on a small insurance dataset.

### Critical scope limits (read before quoting these numbers)

| Limit | What we ran | What the library default is |
|---|---|---|
| **Epoch budget** | 3 passes | **30** (we used 1/10th of the default) |
| **Training data** | 2,000 rows per dataset (64–93% discarded) | Full datasets (up to 53K rows) |
| **Seeds / folds** | 1 seed, 1 split | 3 seeds × 5 folds recommended |
| **Transfer** | None — each model tested on the dataset it was trained on | Leave-one-dataset-out (never run) |
| **Datasets** | 4 of 15 classification; 0 regression | 15 classification + 4 regression |

### What it cannot support

- **"Fine-tuning doesn't help"** — the lever tested was deliberately small (3 epochs). A larger budget might behave differently.
- **"Fine-tuning doesn't transfer"** — transfer was never tested. We fine-tuned and evaluated on the same dataset each time. The deployment question (train on other portfolios, predict on a new one) is untested.
- **Any deployment claim** — single seed, single split, no calibration metrics, no out-of-time holdout.

---

## What we found that worked — and what didn't, on the engineering side

| Finding | Impact |
|---|---|
| Arm B (fine-tuned) had **never completed anywhere** — believed to be memory, was actually a call-sequence defect | Fixed by using the library's own `FinetunedTabPFNClassifier` instead of driving the model by hand |
| The hand-rolled loop could take **zero gradient steps** while still reporting metrics | Fixed — library trainer handles this correctly |
| GPU pipeline works end-to-end: provision → run → return artifacts → tear down | Verified at $0.53 across 13 instances |
| Per-arm predictions were not returned for the fine-tuned arm | Fixed in the runner (chunked transport) |
| No audit trail (no per-arm config, no dataset hashes, no split records) | Fixed — manifest schema v2 implemented |

---

## What we're proposing next (Pilot 2)

A **two-stage gated experiment** — Stage 1 only runs if it looks promising, Stage 2 only runs if Stage 1 succeeds.

### Stage 1 — Does the mechanism work at all? (positive control)

- Same four datasets, but with a **fair epoch budget**: 3, 10, and 30 epochs (the library default)
- **Matched inference context** between raw and fine-tuned arms (the historic confound)
- 3 seeds × 5 folds — every delta is a distribution, not a point
- **Log loss primary** (what an insurer pays on), plus calibration (ECE, Brier)
- Budget-ladder-first: run the cheapest dataset first; if 3 → 30 epochs is flat, stop before paying for bigger runs

**Estimated cost:** ~$1–4 depending on how many rungs we need.

### Stage 2 — Does it transfer? (leave-one-dataset-out)

- Fine-tune on a pool of **other** datasets, evaluate on a target it never saw
- The historic version of this experiment (on an older model) came out **strongly negative** — this would be the first re-test on the current model line
- Requires a team decision on **feature harmonisation** (the datasets have 11–86 columns and don't share a schema)

**Estimated cost:** ~$2–30 depending on scale, gated behind a positive Stage 1.

---

## What we need from the team

| Decision | Options | Recommendation |
|---|---|---|
| **1. Sign off on the two-stage structure** | Stage 1 first, transfer only on a positive | Yes — prevents repeating the historic mistake of testing transfer before establishing a positive control |
| **2. Feature harmonisation** (for Stage 2) | A: same-schema sub-pools, B: feature intersection, C: union with imputation, D: minimal common schema | **A** — cleanest, removes the harmonisation confound |
| **3. Target set for Stage 2** | Historic 4 (for comparability with v2 results) or R1 4 (for continuity) | Team's call — historic set makes the re-test legible |
| **4. Budget envelope** | P1a only (~$1), through P1b (~$4), or to P1c (~$15) | At least P1a — it's $1 and answers whether the epoch ladder moves |
| **5. Pool policy** | Re-test `similarity_topk` vs `mixed_baseline`, or fix one and spend on power | Fix one — the historic comparison was a coin flip under a confounded design |

---

## Evidence files

| File | What it is |
|---|---|
| `outputs/finetune/pilot/pilot_metrics.parquet` | R1 aggregate metrics (16 rows, all 4 arms × 4 datasets) |
| `outputs/finetune/pilot/pilot_predictions.parquet` | Per-row predictions for all 12 R1 runs (12,000 rows) |
| `outputs/finetune/pilot/<dataset>/<arm>/meta.json` | Per-run config, versions, device, timings |
| `outputs/gpu-pilot/run_*.json` | Per-run audit manifests (13 instances) |

## Detailed reports

| Report | Audience | Read for |
|---|---|---|
| `FINE_TUNING_PILOT_RESULTS.md` | Technical | The full R1 numbers, interpretation warnings, statistical limits |
| `SMOKE_TEST_SCOPE.md` | Technical | What R1 did and never exercised, execution record |
| `FINE_TUNING_METHOD.md` | Statistician | The exact estimator, call sequence, and leakage controls |
| `HISTORIC_FINETUNING_APPRAISAL.md` | Technical + decision-makers | Why the prior negative verdict was confounded and unusable |
| `PILOT_2_DESIGN.md` | Technical + decision-makers | The proposed next experiment (full spec) |
| `NEXT_STAGE_PROPOSAL.md` | Technical + decision-makers | The LODO transfer design and audit schema |
| `MASTER-REPORT-DIGEST.md` §14.16 | Anyone | One-paragraph verdict in the context of the full benchmark arc |
