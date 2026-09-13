# Presentation Plan — TabPFN for Insurance (AIDSET & Statistical Society Conference)

Plan for a 20-minute talk on the TabPFN insurance benchmark work. One core deck,
per-venue trims. Deadlines: both conferences due 2026-09-10 (check CFP dates —
abstract deadlines usually precede; set them on issues #108/#111).

Status: PLAN — not yet executed. Tracked in issues #108–#113 (venue-specific
abstract/poster/presentation), #105 (deliverables parent), #78 (Spanish deck).

## What is ready now (no new analysis needed)

| Material | Where | Status |
|---|---|---|
| All results tables (12 datasets, §14.2–§14.14) | `docs/analyses/tabpfn_vs_gbdt_baselines_finetuning.md` + `frontier_results_*.csv` | Ready |
| Frontier plots (incl. Spanish freq/severity) | `scripts/eval/insurance_benchmark_v1/*.png` | Ready |
| Spanish consolidated deck | issue #78 (colleague, Friday) | In progress |
| Narrative verdict (wins/losses/reframe) | report §14.9–§14.14 digest | Ready |

**Needs producing before 09-10:** venue abstracts (#108/#111), one reframe
contrast chart (currently a table only — §14.14.2), slide build.

## Narrative arc (13 slides)

1. **Title** — Foundation models for actuarial tabular data: where TabPFN wins, loses, and why
2. **The question** — can a 10M-param in-context learner replace GLMs/GBDTs in insurance pricing & triage?
3. **Method** — 12 datasets, 5-fold, 9–10 methods, paired t. One line on the metric lesson: v1 ranked on 1−AUC (calibration-blind) → v2 scores log loss/AUC/Brier/PR-AUC/lift10 (§11–§12)
4. **Result 1: at-scale pricing, TabPFN loses** — Spanish freq (LGBM −10.8% deviance, §14.9), severity (−2.7% RMSE, §14.10); parsimony: 21-param GLM ties 10M-param TabPFN
5. **Result 2: lapse, TabPFN wins** — 0.7553 vs 0.7500 AUC, all 5 folds (§14.10)
6. **Result 3: the reframe inversion (money slide)** — same rows, count → classification target: rank #1 on all 5 metrics, paired-significant, two seeds (§14.14). Chart to build.
7. **Regime synthesis** — thin-signal/ranking → TabPFN; GLM-captured/parsimony → classical; count axis → trees (regime_characterization.md)
8. **Actuarial takeaway** — TabPFN for claim-propensity triage and lapse; GLM/GBDT for pricing. Transparency + parsimony govern deployment.
9. **Caveats (own them)** — reframe n=1 (freMTPL2freq pending, gap B1); PR-AUC within noise; GLMs collapse on binary reframe; client version pin 0.3.3; fine-tuning degrades (§5)
10. **Next steps** — freMTPL2freq reframe (B1), fairness addendum (#107), use-case doc (#25)
11–13. **Appendix** — full digest table, protocol detail, files/links

## Division of labour

- **Colleague:** #78 deck (Friday) → evidence core for slides
- **Owner (scotthawes):** narrative/exec summary (#106) — reuses slides 4–8
- **Abstract writers:** one per venue, from slides 2 + 6 + 8 (TBD assignee)
- **Chart:** reframe contrast plot from `reframe_frequency_results.csv` (small script)

## Timeline to 09-10

- **This week:** #78 deck + confirm CFP deadlines for both venues → set abstract due dates on #108/#111
- **Aug 17–24:** abstracts drafted; reframe chart built
- **Aug 24–31:** slide build from deck
- **Sep 1–8:** review + rehearse (caveats slide as QA checklist)
- **Sep 8–10:** submit per venue requirements

## Open questions

1. CFP dates for both venues (sets the abstract schedule)
2. Abstract drafting owner (recommend: colleague + one reviewer)
