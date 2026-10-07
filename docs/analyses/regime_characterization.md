# Regime Characterization — When Default TabPFN Wins (Issue #53)

Analysis note feeding the adoption guidance (one-pager `docs/archive/TABPFN_BENCHMARK_SUMMARY.md`).
Answers: what distinguishes the datasets where default TabPFN wins from those where it is
dominated, so the adoption rule is predictive rather than descriptive. Desk analysis over
committed evidence only — no new fits, no new numbers without a source.

Verdicts here are log-loss verdicts. To read them correctly — what a metric does and does
not measure, and why log loss and AUC disagree on imbalanced data — see
`docs/analyses/metrics_explained.md` (wiki: Metrics-Explained).

Central puzzle (from issue #53): TabPFN loses frequency/severity on Spanish motor at
53,502 rows but wins lapse at the same size (AUC 0.7553 vs 0.7500, 5/5 folds). If the
adoption rule is "small data only", Spanish lapse at 53.5K rows should not be a win.

## 1. Regime table

12-dataset frontier (`scripts/eval/insurance_benchmark_v1/frontier_results_*.csv`,
reported in master report §14.2–§14.10) + 2 lapse tasks (§14.10) + the 9-cell size sweep
(§13.2, `home_turf_sweep_results.csv`). All frontier numbers are 5-fold mean ± SE, D3
beyond-SE Pareto rule (§14.1). GLM gap = (best GLM/LR floor score − best score) / best
score — the "how far is the linear floor from achievable" proxy; null deviance cited
where the report records it. TabPFN n_params is the settled constant 10,000,000 (§14.1).

| dataset | rows | target (metric) | balance | TabPFN mean ± SE | position | best competitor (mean, params) | GLM floor (params, score; gap) | outcome class |
|---|---|---|---|---|---|---|---|---|
| coil2000 | 9,822 | CARAVAN purchase (log loss) | 6% pos | 0.20059 ± 0.00221 | **on frontier, best** | lr 0.20554 (86) | lr 0.20554 (86); +2.5% | WIN |
| bemtl16 | 58,723 | liability claims (log loss) | 36.0% pos | 0.23803 ± 0.00129 | **on frontier, best** | lgbm 0.23985 (3,100) | logisticglm 0.26315 (14); +10.6% | WIN |
| uslapseagent | 29,317 | surrender (log loss) | 38% pos | 0.24909 ± 0.00518 | **on frontier, best** | cat 0.25286 (63,394) | logisticglm 0.27624 (11); +10.9% | WIN |
| ausautoBI8999 | 22,036 | log AggClaim (RMSE) | continuous | 0.96491 ± 0.00868 | **on frontier, best** | cat 0.96883 (63,944) | ols 1.07133 (12); +11.0% | WIN |
| ausprivauto0405_vehvalue | 67,856 | VehValue (RMSE) | continuous | 0.71162 ± 0.01246 | **on frontier, best** | lgbm 0.71645 (3,100) | poissonglm 1.00932 (7); +41.8% | WIN (within SE of lgbm) |
| norauto | 184,000 | NbClaim (log loss) | 4.6% pos | 0.17619 ± 0.00061 | on frontier (fold-noise tie) | lgbm 0.17518 (3,100) | logisticglm 0.17846 (6); +1.9% | TIE |
| bemtl97 | 163,212 | claim (log loss) | 11.2% pos | 0.34279 ± 0.00057 | on frontier (fold-noise tie) | lgbm 0.34177 (3,100) | lr 0.34270 (11); +0.3% | TIE |
| ausprivauto0405 | 67,856 | ClaimOcc (log loss) | 6.8% pos | 0.24026 ± 0.00037 | **off frontier** | logisticglm 0.23947 (7) | GLM is the best; 0.0% | GLM-captured (retracted §14.11.3 — calibration tie, TabPFN best AUC of suite) |
| spanish_motor_freq | 53,502 | N_claims_year (Poisson dev) | 11.1% >0 | 0.98764 ± 0.01624 | **off frontier** | lgbm 0.89157 (3,100) | poissonglm 1.01250 (21); null dev 1.0123 — GLM at the intercept floor; +13.6% vs lgbm | DOMINATED |
| spanish_motor_severity | 53,502 | log1p cost (RMSE) | continuous | 1.88616 ± 0.01165 | **off frontier** (5th of 8) | lgbm 1.83719 (3,100) | ols 1.87810 (21); +2.2% | DOMINATED |
| bemtl97_amount | 163,212 | log1p amount (RMSE) | ~89% zero mass | 0.72825 ± 0.01057 | **off frontier** | lgbm 0.48499 (3,100) | ols 0.70799 (12); +46.0% | DOMINATED |
| freMTPL2freq | 678,013 | frequency (Poisson dev) | count | 0.38770 ± 0.00201 | **off frontier** | lgbm 0.29113 (3,100) | poissonglm 0.32109 (11); +10.3% | DOMINATED |
| spanish_motor_lapse | 53,502 | surrender (AUC) | 35.4% pos | **0.7553 ± 0.0026** | wins all 5 folds | lgbm 0.7500 ± 0.0022 | LR 0.6841 ± 0.0015 (gap 0.071 AUC / +9.4% on TabPFN) | WIN |
| eudirectlapse | 23,000 | lapse (AUC) | 12.8% pos | 0.6101 ± 0.0049 | loses all 5 folds | linear 0.6260 ± 0.0037 | LR is the best; 0.0% | LOSE |

Size sweep (§13.2; `home_turf_sweep_results.csv`): bemtl97 / coil2000 / uslapseagent ×
1K / 5K / full (163,212 / 9,822 / 29,317 rows) × 5 folds, log loss. **TabPFN wins 8/9
cells** — all six ≤5K cells plus both small full-size cells (coil2000 9,822, uslapseagent
29,317); the only loss is bemtl97@full (163K), LGBM 0.3418 vs TabPFN 0.3428, a 0.0010
fold-noise margin.

Totals across the 14 tasks: **6 wins, 2 fold-noise ties, 6 losses; on the parsimony
frontier 7 of 12 frontier datasets** (one-pager §"The evidence"; §14.4). The loss count
reflects the log-loss axis only — §14.11's AUC rescore reclassifies ausprivauto0405 to
tie-with-ranking-edge. Money chart
(`plot_money_chart.py` docstring): every off-frontier point sits at ≥53.5K training rows
with ratio ≥1.03.

## 2. Hypothesis test — thin-signal vs GLM-captured

Issue #53 hypothesis: TabPFN wins where the signal is thin and no simple model extracts
it (Spanish lapse: LR 0.684 — genuinely hard); loses where GLMs already capture the
signal (Spanish freq: Poisson GLM at the null floor). Classify each dataset:

- **(a) thin-signal / hard** — linear floor far from achievable (GLM gap ≥ ~2.5%, or
  AUC gap ≥ ~0.05): coil2000 (+2.5%), bemtl16 (+10.6%), uslapseagent (+10.9%),
  ausautoBI8999 (+11.0%), vehvalue (+41.8%), spanish_lapse (0.071 AUC),
  spanish_freq (+13.6%), spanish_severity (+2.2%), bemtl97_amount (+46.0%),
  freMTPL2freq (+10.3%).
- **(b) GLM-captured** — linear floor within ~2% of achievable: norauto (+1.9%),
  bemtl97 (+0.3%), ausprivauto0405 (0.0%, GLM is best on log loss; TabPFN best AUC,
  §14.11.3), eudirectlapse (0.0%, LR is best).

**Result — the hypothesis is half-right, and the freq example misreads its own evidence.**

*Confirmed direction (b): when GLMs already capture the signal, TabPFN has no edge on
log loss/calibration — but holds a significant AUC ranking edge on 2 of the 4
GLM-captured tasks (norauto, bemtl97; ausprivauto0405 at +1.5 SE, §14.11.3).* ausprivauto0405 was TabPFN's only outright frontier
domination (7-param logisticglm beats it beyond SE on log loss, §14.7; retracted on the
full metric set, §14.11.3); eudirectlapse goes to LR all 5 folds (§14.10); norauto and
bemtl97 reduce TabPFN to a beyond-SE fold-noise tie on log loss (§14.6, §14.3) while
TabPFN still wins AUC (2.5–2.6 SE, §14.11.3). GLM gap ≈ 0 ⇒ no log-loss win, in 4/4
cases.

*Contradicted direction (a): thin signal is necessary but NOT sufficient — 4 of the 10
thin-signal tasks lose, and they include Spanish freq, the issue's own example.* Spanish
freq is the thinest signal in the suite (poissonglm 1.01250 vs null deviance 1.0123 —
the GLM is at the intercept-only floor, §14.9), yet TabPFN (0.98764) lands only 2.5%
above that floor while LGBM (0.89157) is 12% below it; only LGBM extracts the signal
(cat 0.99757, rf 0.99808, xgb 1.35178 all fail too, §14.9). Same shape on freMTPL2freq
(678K rows): TabPFN 0.38770 is worse than the 11-param GLM 0.32109 (§14.8). bemtl97_amount
has the largest GLM gap of all (+46%) and TabPFN still loses — to ols, an intercept-scale
12-param model (§14.8). So "GLM far from floor" does not predict a TabPFN win.

**What the data actually shows — the lapse flip, correctly read.** At the same 53,502
rows the two Spanish motor tasks split because of *which* model extracts the signal:

| task | linear floor | TabPFN | LGBM | reading |
|---|---|---|---|---|
| Spanish lapse (AUC) | LR 0.6841 — far from achievable | 0.7553 (best, 5/5 folds) | 0.7500 | linear cannot extract it; TabPFN extracts it best (§14.10) |
| Spanish freq (Poisson dev) | GLM 1.01250 — at the null floor 1.0123 | 0.98764 (≈ floor +2.5%) | 0.89157 (floor −12%) | linear cannot extract it; TabPFN cannot either **on the count axis** (§14.14 reframe flips it); only LGBM can (§14.9) |

The discriminator is not "thin vs captured" — both are thin. It is whether TabPFN's prior
extracts the signal that linear models miss, at parity or better with the trees:

- **Wins (6/6):** GLM gap large AND (classification/lapse axis — coil2000, bemtl16,
  uslapseagent, spanish_lapse — or severity at ≤68K rows — ausautoBI8999 22K,
  vehvalue 67.9K). TabPFN leads beyond SE on 5 of the 6 (vehvalue is the within-SE tie).
- **Losses (6/6):** GLM gap ≈ 0 (ausprivauto0405, eudirectlapse) or fold-noise tie
  (norauto, bemtl97) — 4/4 GLM-captured tasks — plus the tree-only-signal tasks:
  both frequency tasks (spanish_freq, freMTPL2freq) and zero-inflated severity at 163K
  (bemtl97_amount), where TabPFN cannot beat even the GLM floor (spanish_sev, +2.2% gap,
  also loses — 5th of 8, worse than ols). Scoping footnote (2026-08-07, issue #67,
  §14.14): "tree-only" holds on the **count axis** — the same Spanish motor target
  reframed as claim/no-claim classification puts TabPFN at AUC rank #1,
  paired-significant at both seeds (p=0.0010/0.0020).

Consistency check with the size axis: all five off-frontier frontier datasets are ≥53.5K
rows (money chart docstring), but ≥53.5K is the *onset* zone, not a death zone — bemtl16
(58.7K), vehvalue (67.9K) and spanish_lapse (53.5K) all win there. Below 29.3K rows TabPFN
won every classification task tested (8/9 sweep cells including the two full-size ones;
§13.2).

## 3. Regime descriptor (paste-ready for the one-pager)

> **Use default TabPFN when** training rows are ≤ ~5K (won 8/9 size-sweep cells, §13.2),
> **or** the task is classification/lapse-style and the linear floor is far from
> achievable — best LR/GLM ≥ ~3% behind the best model (or ≥ ~0.05 AUC): that condition
> holds for every TabPFN win (coil2000, bemtl16, uslapseagent, ausautoBI8999,
> vehvalue; Spanish lapse LR 0.684 vs TabPFN 0.7553).
> **Expect otherwise:** TabPFN dominated on the trade-off at scale — every off-frontier
> frontier point sits at ≥53.5K rows (`plot_money_chart.py`) — with no edge when the GLM
> floor already sits within ~2% of achievable (ausprivauto0405, eudirectlapse, norauto,
> bemtl97: GLM gap ≈ 0 ⇒ no log-loss edge, no win in 4/4 — note §14.11 AUC rescore:
> TabPFN holds the ranking edge even in GLM-captured regimes (norauto, bemtl97,
> ausprivauto0405)), and no edge on frequency targets at scale even
> when the GLM floor is weak, because there the signal is tree-extractable only (Spanish
> freq: LGBM 0.8916 vs TabPFN 0.9876, Poisson GLM at the 1.0123 null floor; freMTPL2freq
> at 678K rows). "Tree-extractable only" is scoped to the count axis: reframed as
> claim/no-claim classification (binary or ordinal), TabPFN wins the ranking axis —
> AUC rank #1, paired-significant, seed-stable (§14.14). Between the two regimes, prefer the GLM: the 11–86-param GLM family is
> never dominated on any dataset (§14.4), and on frequency it is statistically
> indistinguishable from TabPFN at 21 params (§14.9).

## 4. Caveats

- **Lapse: 2-fold → 5-fold history.** The first Spanish lapse gap (AUC 0.752 vs 0.745,
  §14.9) carried a 2-fold caveat; the §14.10 re-run at 5 folds settles it — 0.7553 vs
  0.7500, TabPFN wins all five folds (0.7465–0.7621 vs 0.7416–0.7550). The premium
  regression task in the lapse leaderboard stays 2-fold (§14.10); the leaderboard ELO
  lead is partly carried by that premium task (RMSE 19.07 vs 81.84, §14.10; one-pager
  caveats).
- **Protocol differences (v1 vs frontier).** v1 baseline ran the TabArena harness
  (3-fold, ranked on 1−AUC — rank-invariant, blind to calibration, §11.2/§12.2); the
  frontier runs are 5-fold KFold seed 42 on log loss / RMSE / Poisson deviance with the
  D3 beyond-SE rule (§14.1). The vehvalue outcome flips between protocols (v1: +67.2%
  loss, rank 8/8, §4.1 vs frontier: 0.71162 win, §14.8) — protocol-specific, not a
  stable model property (one-pager caveats; §14.8).
- **Hosted v3 pin.** All hosted runs are pinned to `model_path="v3_default"` (tabpfn-client
  0.3.3) for reproducibility (§14.9). The §12.1 "~1K context ceiling" mechanism is
  superseded by the v3 model-version correction — API limits accept up to 1M rows — but
  the measured size pattern stands as mechanism-independent (§12.1). Re-test procedure
  when the client/model version changes: master report §15 (Version-Drift Re-Test
  Policy, issue #55).
- **Label-leak exclusions.** bemtl97 (`nclaims`/`amount` leak, §6) is leak-fixed
  everywhere here; bemtl97_amount drops `claim` (§14.8); Spanish motor drops the
  history-variable leak (pre-run AUC 0.76/0.92) and sibling targets `Cost_claims_year` /
  `N_claims_year` (§14.9, §14.10); freMTPL2freq drops `IDpol` and uses a log(`Exposure`)
  offset (§14.8). Excluded rows are not part of any number above.

## 5. Evidence index

- Master report: `docs/analyses/tabpfn_vs_gbdt_baselines_finetuning.md` — §4.1 (v1
  verdicts), §6 (leak), §8 (verdict), §11.2/§12.2 (metric blindness), §12.1 (size
  pattern + v3 correction), §13.2 (sweep table), §14.1 (protocol, D3 rule, 10M-param
  constant), §14.2/§14.3 (frontier results + narratives), §14.4 (actuary takeaways),
  §14.6 (norauto), §14.7 (ausprivauto0405, bemtl16), §14.8 (regression Phase 2),
  §14.9 (Spanish freq), §14.10 (5-fold lapse + Spanish severity), §14.11 (AUC/Brier
  re-score, DOMINATED retraction), §14.14 (count/frequency classification reframe,
  issue #67).
- Frontier CSVs: `scripts/eval/insurance_benchmark_v1/frontier_results_*.csv` (12
  datasets: 6 classification + 4 regression + Spanish freq + Spanish severity).
- Reframe (issue #67): `scripts/eval/insurance_benchmark_v1/reframe_frequency_results.csv`,
  `reframe_frequency_summary.csv`.
- Sweep: `scripts/eval/insurance_benchmark_v1/home_turf_sweep_results.csv`.
- Lapse: `scripts/eval/lapse_benchmark_v1/tabarena_leaderboard.csv` (ELO),
  `results_per_split.csv` (per-fold AUC).
- Money chart: `scripts/eval/insurance_benchmark_v1/plot_money_chart.py` (docstring:
  off-frontier ⇒ ≥53.5K rows, ratio ≥1.03; sweep 8/9).
- One-pager: `docs/archive/TABPFN_BENCHMARK_SUMMARY.md`.
