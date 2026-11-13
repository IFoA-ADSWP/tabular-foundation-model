# Frequency/severity fair test — result

> **Status:** current — verdict recorded 2026-11-12; the row-scaling arm (#572) added 2026-11-13
> and does not change the verdict. Supersedes the gate's preview (`docs/analyses/freq_sev_power.md`),
> which said in advance that it was not a verdict.
> **Question:** does fine-tuning TabPFN beat using it untouched, on claim frequency and per-claim
> severity, across a French and a Spanish portfolio?
> **Answer:** yes for claim frequency (pooled **+6.85%**, CI [+2.65%, +10.36%], **Go** against the
> 2% floor); no for severity (pooled **+0.36%**, CI [−0.99%, +2.06%], **heterogeneous** — the two
> portfolios disagree in sign, so no task-level gain is claimed).

## Design, as registered

`docs/current/REGRESSOR_FINETUNING_PREREGISTRATION_FREQ_SEV_2026-11.md`. Four targets; arms
`A_raw` versus `B_ft30`; five policy-grouped folds (`random_state=42`); three model seeds per fold;
training capped at 10,000 rows; every arm and seed in a target sees the same test rows. The
statistic is the per-fold, per-seed relative improvement

```
r_{t,f,s} = (M(A_raw) - M(B_ft30)) / M(A_raw)
```

averaged over seeds inside each fold. Target intervals are paired t over five folds (4 df); task
intervals are the registered two-way bootstrap (portfolios × folds, 10,000 draws, indicative
because two portfolios is a thin resample).

Recomputed from the retained captures by `scripts/analyses/freq_sev_fair_test.py`, which reads
each slot's recorded `verdict_metric_value` and applies the decision rule below. The run ids:

| Target | Run id | Capture |
|---|---|---|
| frequency_french | `20261112T164543Z` | v3, `freMTPL2freq`, 30 entries |
| frequency_spanish | `20261112T184155Z` | v3, `spanish_motor_freq`, 30 entries |
| severity_french | `20261112T210029Z` | v4, `freMTPL2sev`, 30 entries |
| severity_spanish | `20261112T220641Z` | v4, `spanish_motor_severity`, 30 entries |

Every capture passes `check_citations.check_run_dir`: 2 arms × 5 folds × 3 seeds, all hashes
present. Severity captures carry `weights_sha256` and `cluster_sha256`; frequency captures carry
`exposure_sha256` and neither of the severity pair, as the contract requires.

The row-scaling arm (#572) is a fifth capture, `20261113T003320Z` — v4, `freMTPL2sev`, 30 entries,
same contract — and is not one of the four the verdict is registered on. It is reported separately
below.

## Result

| Target | r | 95% CI | MDE | Floor | Decision |
|---|---:|---|---:|---:|---|
| frequency_french | **+9.69%** | [+7.43%, +11.95%] | 2.28% | 2% | **Go** |
| frequency_spanish | **+4.00%** | [−0.64%, +8.65%] | 4.69% | 4% | **Inconclusive** |
| severity_french | **−0.92%** | [−1.16%, −0.68%] | 0.24% | 2% | **No-go** |
| severity_spanish | **+1.64%** | [+0.24%, +3.05%] | 1.42% | 2% | **Inconclusive** |
| **Task: frequency** | **+6.85%** | [+2.65%, +10.36%] | — | 2% | **Go** |
| **Task: severity** | **+0.36%** | [−0.99%, +2.06%] | — | 2% | **Heterogeneous** |

Decision rule, from the pre-registration: **Go** when the CI excludes zero and the point estimate is
at or above the floor; **No-go** when the CI upper bound is below the floor; **Inconclusive** when
the CI covers both zero and the floor, or the target is underpowered. Task floors are 2%; Spanish
frequency carries its own 4% per-target floor and does not decide the frequency task.

## What the numbers say, and what they do not

**Frequency: fine-tuning helps, and the French target decides it.** French frequency's interval sits
entirely above its floor, four times its own MDE. Spanish frequency is directionally positive
(+4.00%) but its interval includes zero, so on its own it is inconclusive — the pooled task interval
is what carries the decision, exactly as registered.

**Severity: fine-tuning does not help, and on the French claims it slightly hurts.** The French
effect is small but real — the CI excludes zero and lies entirely below it, so "no effect" is
*excluded*: fine-tuning made per-claim severity worse by about 0.9%. Spanish severity is positive
(CI [+0.24%, +3.05%], excludes zero) but below the 2% floor and covers it, so it is inconclusive
rather than a win. Because the two portfolios disagree in sign, the task is **heterogeneous** and no
task-level severity gain is claimed, per the pre-registration.

**The gate's preview held.** Measured against the gate's point estimates (+9.42% / +4.49% / −0.92% /
+1.63%), the fair test returned +9.69% / +4.00% / −0.92% / +1.64% — same seeds, same folds, so this
is the reproduction it should be. The **intervals widened** relative to the gate's MDEs (1.65% →
2.28%, 3.85% → 4.69%, 0.50% → 0.24%, 1.35% → 1.42%): the gate's five folds underestimated
fold-level variance for the two frequency targets. That is why Spanish frequency's MDE (4.69%) now
exceeds its own 4% floor.

## The row-scaling arm (#572)

The verdict above is measured on a 10,000-row training cap — 48% of the French severity claims
available to a fold, and 1.8% of the French frequency policies. #572 registered a repeat of the
severity comparison at a 40,000-row budget applied to **both** arms. On French severity the budget
clamped to the fold's whole claim pool, so the arm trained on **21,131–21,177 rows**: 2.1× the cap
and every claim the fold had. Thirty entries, same folds, same seeds, same decision rule.

| Training budget | r | 95% CI | MDE | Decision |
|---|---:|---|---:|---:|
| 10,000 rows (`20261112T210029Z`) | −0.92% | [−1.16%, −0.68%] | 0.24% | No-go |
| 40,000 budget, 21,177 rows (`20261113T003320Z`) | −0.79% | [−1.55%, −0.03%] | 0.77% | No-go |

**The No-go survives at 2.1× the rows.** The point estimate moves 0.13 points toward zero and the
interval is about three times wider (−0.68% to −0.03% at the upper bound). It still excludes zero,
but by only three basis points: the harm is small at this budget, and this run does not pin its
size. Against the floor the answer is unambiguous — an upper bound of −0.03% is two points below
the registered 2% — so the cap was not what made French severity a No-go.

**The registered 4× was not reachable.** The amendment raised the budget to 40,000 rows; a fold's
whole claim pool is 21,131–21,177, so the arm ran at the largest budget this dataset can express.
#572's hypothesis — that the severity null is row starvation — is therefore answered at 2.1×, not
at the 4× it named, and the gap is the data's rather than the design's.

**The reading is the target's, not the task's.** The No-go above applies the registered rule to
`severity_french`'s own interval. The task verdict is not recomputed at the raised budget, because
Spanish severity was not re-run: severity still reads **Heterogeneous** from the four registered
captures, and no task-level number moves.

The per-fold pattern says the same without the average: four of five folds are negative (−0.29%,
−1.19%, −1.17%, −1.33%) and the fifth is +0.02%.

**What this does not settle.** The frequency half of the amendment — `frequency_french`, the more
starved target at 1.8% of the available policies — has not run. The frequency Go therefore still
rests on 10,000 rows per fold, and nothing here says whether +9.69% is a floor or a midpoint. The
capture's quantiles are recorded but not analysed; the distributional question is answered on the
four registered captures only.

## Limits

- **Not a comparison with actuarial baselines.** Both arms are TabPFN; `E_glm` and `F_catboost` are
  not in this run. This measures the value of fine-tuning, not the value of TabPFN.
- **The epoch ladder was not run.** `B_ft10` and `B_ft3` are a follow-up; no floor is registered for
  them, so they could not have moved these decisions.
- **The row cap is settled for severity and open for frequency.** The French severity comparison was
  repeated on each fold's whole claim pool (21,131–21,177 rows, 2.1× the cap) and stayed No-go;
  French frequency, measured on 1.8% of its policies, has not been re-run at a raised budget.
- **Spanish frequency is underpowered at its floor.** Its MDE (4.69%) is above the 4% bar, so a true
  effect of 4% would be missed roughly half the time. More folds would fix it; the pre-registration
  fixes five, so that is a new registration.
- **Severity's Spanish interval is clustered by policy** as registered; the French severity point
  estimate is one small negative number and should not be read as a magnitude worth acting on.
- **Quantiles were captured but are not analysed here.** The verdict uses the recorded deviance /
  weighted RMSE per slot; calibration and interval work is a separate question.

## Reproduce

```
python scripts/analyses/freq_sev_fair_test.py \
  --frequency-french 20261112T164543Z --frequency-spanish 20261112T184155Z \
  --severity-french 20261112T210029Z --severity-spanish 20261112T220641Z \
  --row-scale-french 20261113T003320Z
```

It prints the tables above — including the row-scaling arm's per-fold ratios — and `--json` emits
the same as data. `--row-scale-french` keeps the arm out of the severity task mean, so the four
registered rows are byte-for-byte what was published on 2026-11-12. `./scripts/check.sh citation`
proves each cited id has the capture it claims.
