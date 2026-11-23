# Epoch ladder — the registered interval, computed at last

> **Status:** current — analysis, 2026-11-23 (#752). Reads the two committed captures; no fit, no
> capture, no spend. **No verdict moves.** The ladder's frozen rule and its CONFIRMED / REFUTED /
> UNRESOLVED readings stay with [`EPOCH_LADDER_RESULT.md`](EPOCH_LADDER_RESULT.md).

**Question.** The ladder reports t-intervals over twenty seeds that share five fixed folds. The
statistical analysis plan registered a paired bootstrap over **rows**. Do the two agree?

**Answer: on the sign and on the exclusion of zero, yes; on the width, no — and the difference is
informative.** The row bootstrap is much narrower on French severity because it holds the seeds fixed
and resamples only rows, so it carries no seed-to-seed component.

## Method

```bash
python scripts/analyses/severity_row_bootstrap.py --target severity_french --reps 2000
python scripts/analyses/severity_row_bootstrap.py --target severity_spanish --reps 2000
```

Fixed by the protocol in #752, not chosen after the result:

- each fold's test rows are identical across the twenty seeds (asserted by the script);
- one row resample is drawn per replicate and applied to every seed, preserving the pairing;
- each seed's relative contrast `(M_arm − M_raw) / M_raw` is computed on the resampled rows and averaged
  across seeds; that average is the replicate;
- 2,000 replicates, 2.5 and 97.5 percentiles.

Metric: unweighted RMSE on log amount (French), weighted RMSE on log cost (Spanish), from the committed
captures. Rows: 26,444 French, 5,950 Spanish.

## Results

| Target | Contrast | Point | Row bootstrap, 95 % | Reported t-interval, 20 seeds |
| --- | --- | ---: | --- | --- |
| `severity_french` | `B_ft30 − A_raw` | +1.41 % | **[+1.32, +1.52]** | [+0.61, +2.12] |
| `severity_spanish` | `B_ft30 − A_raw` | −1.30 % | **[−2.23, −0.41]** | [−2.08, −0.50] |
| `severity_french` | `B_ft10 − A_raw` | +7.24 % | [+6.99, +7.51] | — |
| `severity_spanish` | `B_ft10 − A_raw` | +1.38 % | [+0.85, +1.91] | — |

## The reading

1. **The verdicts stand.** French worse, Spanish better, both excluding zero under the registered
   construction as well as the reported one. The `B_ft10` contrasts also agree: ten epochs is far worse
   than raw on French and worse on Spanish, which is the non-monotonicity the ladder records.
2. **The intervals answer different questions.** The row bootstrap asks what happens if the portfolio's
   policies are resampled; the t-interval asks what happens if the seeds are. The first carries no
   seed-to-seed component, so on French it is four times narrower — the seeds agree closely with one
   another and the row noise is small.
3. **Neither is complete**, which is what the referee objected to. A crossed seed × fold interval with
   both components shown is the honest summary; this note supplies the registered half of it and says
   which half is missing.
4. **What the paper should print:** the registered interval, the reported one, and one sentence naming
   what each holds fixed. Reporting only the t-interval claimed a construction the plan did not
   register; reporting only the bootstrap would understate the between-seed uncertainty.

## Record

- Issue #752 — protocol, and the verdict recorded there.
- Script and test: `scripts/analyses/severity_row_bootstrap.py`, `tests/test_severity_row_bootstrap.py`.
- Captures: `results/20261121T153848Z`, `results/20261121T232424Z`.
