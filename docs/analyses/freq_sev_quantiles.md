# Frequency/severity fair test — what the quantiles say

> **Status:** current — analysis, 2026-11-12. Reads the captures of
> `docs/analyses/freq_sev_fair_test_result.md`; it does not change that verdict.
> **Question:** the fair test scored point predictions. Each slot also carries nine quantiles. Does
> fine-tuning improve the **predictive distribution**, or only the point?
> **Answer:** only the point. Distributional accuracy is unchanged for both frequency targets at
> best, and measurably **worse** for Spanish frequency (pinball +0.0026, t = +3.9) and French
> severity (+0.0127, t = +4.4).

## Method

Every slot stores `quantiles.npy` — nine levels, rows × levels — and `ground_truth.npy`. For each
slot the script computes:

- **coverage** at each level: the share of truths at or below that quantile;
- **pinball (quantile) loss**: the proper scoring rule for a quantile forecast, averaged over levels.

Slots are paired `(fold, seed)` between `A_raw` and `B_ft30`; the difference is a paired t over 15
slots (5 folds × 3 seeds, 14 df, |t| > 2.145 at 95%).

Two instruments are printed because **coverage is not trustworthy on the count targets**, and the
reason is a finding in itself (see §3).

Reproduce with `scripts/analyses/freq_sev_quantiles.py` on the four run ids of the verdict:
`20261112T164543Z`, `20261112T184155Z`, `20261112T210029Z`, `20261112T220641Z`. The #572
row-scaling captures (`20261113T003320Z`, `20261113T095502Z`) are not analysed here; this document
covers the four captures the verdict is registered on.

## 1. Pinball loss — the comparison that holds

| target | A_raw | B_ft30 | B − A | t | reading |
|---|---:|---:|---:|---:|---|
| frequency_french | 0.0259 | 0.0259 | −0.0000 | −0.1 | no change |
| frequency_spanish | 0.1022 | 0.1048 | **+0.0026** | **+3.9** | worse |
| severity_french | 0.2978 | 0.3105 | **+0.0127** | **+4.4** | worse |
| severity_spanish | 0.1471 | 0.1487 | +0.0017 | +1.2 | no change |

So the frequency task's Go — +9.69% on Poisson deviance for French, +4.00% for Spanish — is a claim
about the **conditional mean only**. Where the distribution can be measured, fine-tuning either
leaves it alone or degrades it. For French severity the point metric and the distribution agree:
both get worse.

## 2. Coverage, per level

| target | arm | 0.1 | 0.2 | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| frequency_french | A_raw | 0.00 | 0.00 | 0.04 | 0.26 | 0.51 | 0.76 | 0.91 | 0.95 | 0.95 |
| | B_ft30 | 0.00 | 0.11 | 0.25 | 0.37 | 0.60 | 0.75 | 0.86 | 0.93 | 0.95 |
| frequency_spanish | A_raw | 0.00 | 0.00 | 0.00 | 0.07 | 0.38 | 0.80 | 0.89 | 0.89 | 0.89 |
| | B_ft30 | 0.87 | 0.89 | 0.89 | 0.89 | 0.89 | 0.89 | 0.89 | 0.89 | 0.89 |
| severity_french | A_raw | 0.12 | 0.23 | 0.34 | 0.44 | 0.49 | 0.59 | 0.68 | 0.78 | 0.88 |
| | B_ft30 | 0.17 | 0.25 | 0.38 | 0.53 | 0.63 | 0.69 | 0.73 | 0.77 | 0.84 |
| severity_spanish | A_raw | 0.11 | 0.21 | 0.31 | 0.41 | 0.50 | 0.60 | 0.70 | 0.80 | 0.88 |
| | B_ft30 | 0.10 | 0.21 | 0.32 | 0.42 | 0.51 | 0.60 | 0.68 | 0.77 | 0.85 |

French frequency is the one target where fine-tuning visibly helps at the low levels (0.2 and 0.3
move from 0.00/0.04 toward nominal), while the upper levels drift slightly low. The severity targets
are close to nominal in the middle and under-cover at the top in both arms.

## 3. The coverage metric is broken on the count targets, in both arms

Spanish frequency's flat 0.89 at every level is not a calibrated interval and not a collapsed one —
every row carries nine distinct values. It is a **sign artefact**. The first row's quantiles:

```
A_raw  [-0.004 -0.002 -0.001 -0.001  0.000  0.001  0.001  0.002  0.004]
B_ft30 [ 0.003  0.004  0.004  0.006  0.052  0.061  0.064  0.066  0.069]
```

`A_raw` emits **negative counts** at its lower quantiles, so no observation ever falls below them and
coverage reads 0% at low levels. `B_ft30` shifts them just above zero, so coverage jumps to 87% at
every level. Both intervals are about a fifth of a claim wide, against a count distribution where a
substantial share of policies claim nothing.

This is a **model-interface finding, not a fine-tuning finding**: the quantile head is not usable for
these count targets as configured, whichever arm produced it. It also means any coverage number
quoted from this run — including the flattering French frequency row — should be read with the
0.2-claim width in mind.

## Limits

- Fifteen paired slots per arm. Four tests, no multiplicity correction; the two significant results
  are t = 3.9 and 4.4, which would survive a Bonferroni-style adjustment at 0.05/4, and the two null
  results are nulls at this resolution rather than demonstrated equivalence.
- Severity quantiles are on the log scale, so pinball values are not comparable across tasks and the
  coverage levels are read directly (coverage is invariant to a monotone transform).
- Spanish severity's point metric is policy-weighted and clustered; the quantile loss here is
  unweighted per row. The comparison between arms is still paired and like-for-like.
- Nothing here says *why* fine-tuning degrades the distribution. The candidate — a fine-tune that
  sharpens the conditional mean while the quantile heads drift — would need a diagnostic.

## What this changes

Nothing in the verdict's decision, which was registered on point metrics. It changes the sentence
that may accompany it: **fine-tuning improves how often we expect claims, not how uncertain that
expectation is** — and for two of the four targets the uncertainty got slightly worse. Any downstream
use that consumes intervals rather than means should not inherit the frequency Go.
