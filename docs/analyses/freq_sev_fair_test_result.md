# Frequency/severity fair test — result

> **Status:** current — verdict recorded 2026-11-12. Supersedes the gate's preview
> (`docs/analyses/freq_sev_power.md`), which said in advance that it was not a verdict.
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

## Limits

- **Not a comparison with actuarial baselines.** Both arms are TabPFN; `E_glm` and `F_catboost` are
  not in this run. This measures the value of fine-tuning, not the value of TabPFN.
- **The epoch ladder was not run.** `B_ft10` and `B_ft3` are a follow-up; no floor is registered for
  them, so they could not have moved these decisions.
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
  --severity-french 20261112T210029Z --severity-spanish 20261112T220641Z
```

It prints the table above and `--json` emits the same as data. `./scripts/check.sh citation` proves
each cited id has the capture it claims.
