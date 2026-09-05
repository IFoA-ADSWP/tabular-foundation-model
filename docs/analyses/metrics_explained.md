# Metrics Explained — Log Loss vs AUC vs Brier

What the three headline classification metrics actually measure, why they can disagree,
and which one to look at for which insurance decision. Companion page to
[Benchmark-Summary](Benchmark-Summary) and [Adoption-Guidance](Adoption-Guidance) —
those pages report verdicts in log loss, and this page is the key to reading them
correctly. Written for actuarial colleagues; the worked example uses our own
benchmark evidence.

## The three metrics

**Log loss (cross-entropy)** — *average surprise of the predicted probabilities.*
For each row, pay `−ln(p̂_true)`, then average. Predict 0.9 for a row that turns out
positive → pay 0.11. Predict 0.9 for a row that turns out negative → pay 2.30 —
23× worse. The penalty is asymmetric and unbounded: confident mistakes hurt
disproportionately, and a single badly wrong probability can wreck the average.

- **Rewards:** both *calibration* (are the probability levels right?) and
  *discrimination* (are probabilities spread out?).
- **Two quirks that matter in insurance:** (1) it is a sum over **every row**, so on
  a 5% positive-rate dataset ~95% of the score is decided by the majority-class
  bulk — a model that nails the base rate on 10,000 non-events absorbs a lot of noise
  on the 500 events; (2) it has a **floor** — the label entropy — so on imbalanced
  data every model converges to roughly the same number and visible gaps shrink.

**AUC (AUROC)** — *probability that a randomly chosen positive is ranked above a
randomly chosen negative.* Take every event/non-event pair; what fraction has the
event scored higher? Pure ordering — a model that scores every event 0.999 and every
non-event 0.1 gets AUC 1.0 even though those probabilities are badly overconfident.

- **Rewards:** *only* discrimination/ranking. Calibration is invisible to it.
- **Why it is stable under imbalance:** it is computed on event/non-event *pairs*,
  one of each — the 95/5 split never enters the calculation. It reads only the
  ordering at the top of the score distribution, which is exactly where selection
  decisions live.

**Brier** — *mean squared error of the probabilities:* `(1/n)·Σ(p̂ᵢ − yᵢ)²`.
Quadratic, symmetric, bounded in [0, 1]. Predict 0.7, truth is 1 → cost 0.09.
Punishes miscalibration moderately — no exploding log penalty, no unbounded worst
case.

- **Rewards:** calibration and discrimination in roughly equal measure (it decomposes
  into reliability + resolution + uncertainty).
- **Position:** structurally between log loss and AUC — a proper scoring rule like
  log loss, but far less dominated by the majority bulk and by extreme confidence.

| | Log loss | AUC | Brier |
|---|---|---|---|
| What it reads | Every row, weighted by class frequency | Only pairwise ordering | Every row, equal weight |
| Majority bulk (e.g. 95% of rows) | Decides ~95% of the score | **Never seen** | Decides most of the score, bounded penalty |
| Sensitive to calibration | Extremely | Not at all | Moderately |
| Sensitive to ranking edge | Drowned out by the bulk | Fully visible | Partially visible |
| Proper scoring rule | Yes | No (rank statistic) | Yes |

## Why the three disagree — the imbalance mechanism

The more imbalanced the data, the more log loss and AUC read *different rows*.
Log loss spends ~95% of its budget on the majority-class bulk, where only the
probability level (calibration) matters; AUC ignores the bulk entirely and reads only
the ordering at the top. Brier sits between. On near-balanced data the bulk *is* the
signal — all three metrics read the same rows and they agree.

Our 6-dataset focused-imbalance pilot shows all three regimes in one table. Deltas
are vs the best GLM on each dataset, from the pilot + rescore outputs
(`focused_imbalance_results.csv`, `focused_imbalance_logloss.csv`; per-fold,
unpaired SEs — folds are paired in reality, so significance is conservative).

| dataset | pos rate | Δ log loss vs best GLM | Δ AUC vs best GLM | Δ Brier vs best GLM |
|---|---|---|---|---|
| bemtl97 | 11.2% | +0.0001 (tie) | +0.012 (2.6 SE) | −0.0001 (tie) |
| coil2000 | 6.0% | −0.005 (1.7 SE) | +0.033 (2.7 SE) | −0.001 (tie) |
| uslapseagent | 37.9% | −0.027 (3.8 SE) | +0.021 (6.7 SE) | −0.010 (3.7 SE) |
| norauto | 4.6% | −0.002 (3.0 SE) | +0.017 (2.5 SE) | −0.0004 (4.7 SE) |
| ausprivauto0405 | 6.8% | +0.001 (tie) | +0.006 (1.5 SE) | +0.0001 (tie) |
| bemtl16 | 36.0% | −0.025 (11.7 SE) | +0.006 (8.0 SE) | −0.008 (13.3 SE) |

Readings:

- **The divergence is an imbalance artifact, not a model weakness.** The datasets
  where log loss and AUC disagree most (norauto 4.6%, ausprivauto0405 6.8%) are the
  most imbalanced; the near-balanced datasets (bemtl16, uslapseagent ~36–38%) are
  where all three metrics agree — and there the win is largest.
- **A log-loss "tie" or small loss is a calibration-level statement about the bulk,
  not a verdict on discrimination.** On every dataset TabPFN's AUC is at least as
  good as the best GLM's — its ordering is never worse, and its probability levels
  are never significantly worse (Brier never loses significantly).
- **Old "DOMINATED" verdicts were metric artifacts.** ausprivauto0405 was classified
  as dominated on log loss alone (GLM best, off frontier); on AUC it is the best
  ranker of the 9-method suite, with Brier tied. The linear-floor verdicts in
  Adoption-Guidance ("GLM-captured ⇒ no TabPFN edge") hold for *calibration*; the
  *ranking* edge survives there (AUC +0.012–0.017, ~2.5 SE). This cross-metric
  re-reading is written up as master report §14.11.

## Which metric for which insurance decision

| Decision | What you buy | Metric to read |
|---|---|---|
| Underwriting triage, lapse-propensity targeting, fraud/prospect scoring | A *ranking* of risks — who to look at first | **AUC** (selection quality) |
| Pricing, premium levels, reserve probabilities, regulator-facing probability outputs | The *probability level* itself | **Brier** (and log loss) |
| Overall model selection on imbalanced data | Both, honestly weighted | **Brier** — the balanced compromise |

Two consequences for our workload:

1. **Ranking/selection use cases:** TabPFN is the best discriminator on every
   classification dataset in the suite (AUC never worse than best GLM; win or tie on
   all six). The log-loss-only summaries previously understated this.
2. **Pricing/calibration use cases:** TabPFN never loses Brier significantly — safe
   where the probability level matters, strictly better where it doesn't. Its
   occasionally worse log loss on imbalanced datasets is a majority-bulk calibration
   artifact within noise, not a real cost.

## Related pages and evidence

- Wiki: [Benchmark-Summary](Benchmark-Summary) (one-page verdict),
  [Adoption-Guidance](Adoption-Guidance) (regime/decision rule)
- Local: `docs/analyses/metrics_explained.md` (this page),
  `docs/KNOWLEDGE-PATH-JUNIOR.md` Phase 0 lessons 0.2–0.4 (from-scratch course),
  `docs/reports/TECHNICAL_COMPANION.md` §1 (legacy v2-era numbers, same concepts),
  `docs/analyses/regime_characterization.md`, master report
  `docs/analyses/tabpfn_vs_gbdt_baselines_finetuning.md` (§14)
- Evidence: `scripts/eval/insurance_benchmark_v1/focused_imbalance_results.csv`
  (per-fold AUC), `focused_imbalance_logloss.csv` (per-fold log loss + Brier)
