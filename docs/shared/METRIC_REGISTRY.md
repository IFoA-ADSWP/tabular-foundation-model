# Metric registry

Status: current as of 2026-10-31.

One row per metric definition the project names. A number is only citable with the definition
that produced it: "ECE" is three different calculations under one word, so every rescored row
carries `metric/version` and every row here states what that version computes and the finding
that put it there. This is the table #356 decided and the rows #361 built.

## Rules

- **Identity is a name and a version string** — `auc/1`, `ece/1.0.0` — not a content hash and not
  a commit sha. A hash cannot be cited; a version plus this table can be checked.
- **Any edit that could move a value bumps the version**, bug fixes included. Old numbers keep
  their old identity and are never silently recomputed. A correction is stated in the report
  that cites it.
- **A run's own recorded metrics keep the identity they were computed under**: the record's
  `provenance.code.git_sha`. No record field was added for this (#356). A rescore row names the
  version below instead, and carries `recorded_value` and `agrees` beside it.
- **The registry and the tool are checked against each other.** `tests/test_metric_registry.py`
  reads this table and `src/rescore.py`, and fails when they disagree.

## The recorded five

| Metric | Version | Definition | Motivated by |
| --- | --- | --- | --- |
| `auc` | 1 | Area under the ROC curve: the probability that a randomly chosen positive is scored above a randomly chosen negative. Recorded under the key `roc_auc`. | D9's acceptance is a paired 95% interval on ROC AUC, so the recorded number is the one the decision is judged on (`../experiments/pilot2-phase2/FINETUNING_DECISION_LOG.md`). |
| `pr_auc` | 1 | Area under the precision–recall curve (average precision) for the positive class. | The imbalance rescores (#122) needed a metric that does not reward the majority class; the pilot records AUC and PR AUC together so a change in ranking under imbalance is visible. |
| `brier` | 1 | Mean squared error of the predicted probabilities: `mean((p - y)^2)`. | D6 judges calibration by whether Brier increases, so the recorded Brier is the number the anchor's calibration verdict rests on. |
| `log_loss` | 1 | Cross-entropy of the predicted probabilities, with probabilities clipped to `[1e-15, 1 - 1e-15]`. | `PILOT_2_DESIGN.md` §3 names log loss the primary loss; the clip is what makes the recorded value finite on confident mistakes. |
| `ece` | 1 | Expected calibration error over 10 equal-width probability bins: the bin-weighted gap between mean predicted probability and observed frequency. | D11 redirected the next step to calibration, which needs a number for "how far off are the levels" rather than for ranking. |

## The regression six (#538), plus the weighted variant (#555)

A regression slot's record holds its verdict metric by name (`verdict_metric`) and its value in
`verdict_metric_value`, so `rescore` compares a value only when the names match.

| Metric | Version | Definition | Motivated by |
| --- | --- | --- | --- |
| `rmse` | 1 | Root mean squared error over all rows, on the stored target scale. | The pre-registered verdict metric for `spanish_motor_severity` and `ausprivauto0405` `VehValue`. |
| `weighted_rmse` | 1 | Root mean squared error with one weight per row, `Σw(y−ŷ)²/Σw`, on the stored target scale. | The grouped severity target (#552): a Spanish claiming policy contributes `N_claims_year` claim-equivalents at its mean cost, so an unweighted RMSE would count a one-claim policy as much as a five-claim one. |
| `mae` | 1 | Mean absolute error over all rows, on the stored target scale. | A colleague's preferred summary when a squared loss overweights the tail; it needs no input the capture lacked. |
| `medae` | 1 | Median absolute error over all rows. | Reported beside MAE because severity and vehicle value are heavy-tailed, and the median shows typical rather than average error. |
| `rmsle` | 1 | Root mean squared error of `log1p` on truth and prediction, with predictions clipped below at 0; rows with negative truth are excluded (none of the three targets has one). | The metric colleagues asked for when proportional error matters; the clip makes it defined when a model predicts below zero. |
| `poisson_deviance` | 1 | Deviance of counts: `2·Σ[y·log(y/ŷ) − (y − ŷ)]`, `ŷ` clipped at `1e-12`, and the `y = 0` row contributing `2ŷ`. Exposure is a feature, not an offset; a rate-scale variant is a different name and version. | The pre-registered verdict metric for `freMTPL2freq` `ClaimNb`, where 95% of rows are zero, so the `y = 0` term is most of the number. |
| `gini` | 1 | The normalised Gini, `2·C − 1`, where `C` is the concordance of predictions with truth over pairs with different truth (ties on truth excluded, ties on prediction score one half, a constant prediction scores 0; constant truth is undefined and reported as `nan`). | A ranking measure an actuarial reader asks for first; it is defined from the same arrays as the rest. |

## Not yet in the registry

`lift` and `calibration_slope` are the next slice (#360). They are scores-only metrics in the
sense that no run records them, so rescore supplies them rather than comparing them.
