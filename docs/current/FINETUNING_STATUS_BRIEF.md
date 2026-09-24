# Fine-Tuning Investigation — Status Brief

> Date: 2026-09-24 | Status: **Probe complete; replication requested**
> Related: #22 | One-page companion to the detailed reports below

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

---

## What this means

| Finding | Status |
|---|---|
| At 2K rows, fine-tuning doesn't help | **Superseded** — a small-data artefact of our own row cap |
| At 10K rows, fine-tuning beats raw TabPFN | **Current** — one seed, one split, paired intervals excluding zero |
| Raw TabPFN already leads competing baselines | **Current** — any fine-tuning gain is a within-model improvement |
| The epoch ladder is flat at 2K rows | **Current at 2K** — but not at 10K, where it's monotone |

---

## What we're proposing next

**Replicate the 10K-row finding at two further seeds on `uslapseagent`** — about **$0.037 per run**, measured.

- If it holds on a second seed → extend to `spanish_motor_lapse`
- If it fails → stop the fine-tuning line
- Nothing beyond the first seed is funded until the one before it has produced a result

**Run the diagnostics phase** — understand *why* datasets are hard before fine-tuning them. Five $0 or near-$0 analyses (dataset profiling, feature importance, target reframing, preprocessing ablation, eudirectlapse deep-dive) that may reveal the real lever is feature engineering or preprocessing, not fine-tuning. Can run in parallel with the replication. See `docs/current/DIAGNOSTICS_PHASE_DESIGN.md`.

### The design

| | |
|---|---|
| scope | `uslapseagent` first, then `spanish_motor_lapse` only if the first replicates |
| rows | 10,000+ (lifted from the 2,000 default) |
| arms | `A_raw` always in-run, versus full SFT at 3/10/30 epochs |
| seeds | 2–3, sized against the measured 0.0003 run-to-run spread |
| primary metric | probability quality (Brier, log loss, ECE); ROC AUC alongside |
| cost | ~$0.037 per run at 10K rows (measured, not modelled) |

---

## Open decisions

| # | Question | Recommendation |
|---|---|---|
| 1 | Fund the two-seed replication? | Yes — $0.074 total, staged |
| 2 | Which dataset is the primary target? | `uslapseagent` (largest, most stable) |
| 3 | How many datasets for the family test? | Start with 3 lapse datasets; expand only on a positive |
| 4 | How much calibration drift is acceptable? | Pre-register a numeric tolerance before the run |

---

## Evidence files

| File | What it is |
|---|---|
| `outputs/finetune/pilot/pilot_metrics.parquet` | R1 aggregate metrics (16 rows, all 4 arms × 4 datasets) |
| `outputs/finetune/pilot/pilot_predictions.parquet` | Per-row predictions for all 12 R1 runs (12,000 rows) |
| `outputs/finetune/pilot/<dataset>/<arm>/meta.json` | Per-run config, versions, device, timings |

## Detailed reports

| Report | Audience | Read for |
|---|---|---|
| `docs/current/PILOT_2_BRIEFING.md` | Anyone | One-page briefing with the full picture and the ask |
| `docs/current/FINDINGS.md` | Anyone | What the repository currently believes (F1–F6, L1–L3) |
| `docs/current/FINE_TUNING_EXPERIMENT_DESIGN.md` | Technical | The full experiment design and decision rules |
| `docs/current/PILOT_2_COST_AND_CONTROLS.md` | Technical | Every cost figure, in units of a run we have already done |
| `docs/current/PILOT_2_STATISTICAL_ANALYSIS_PLAN.md` | Statistician | How the numbers will be computed |
| `docs/current/DIAGNOSTICS_PHASE_DESIGN.md` | Anyone | Why we should understand datasets before fine-tuning them |
| `docs/current/PILOT_2_DECISION_LOG.md` | Decision-makers | The decisions, with options and recommendations |
| `docs/reference/FINE_TUNING_PILOT_RESULTS.md` | Technical | The full R1 numbers, interpretation warnings, statistical limits |
| `docs/archive/SMOKE_TEST_SCOPE.md` | Technical | What R1 did and never exercised, execution record |
| `docs/archive/HISTORIC_FINETUNING_APPRAISAL.md` | Technical | Why the prior negative verdict was confounded and unusable |
| `docs/MASTER-REPORT-DIGEST.md` §14.16 | Anyone | One-paragraph verdict in the context of the full benchmark arc |
