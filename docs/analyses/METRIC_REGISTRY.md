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
| `auc` | 1 | Area under the ROC curve: the probability that a randomly chosen positive is scored above a randomly chosen negative. Recorded under the key `roc_auc`. | D9's acceptance is a paired 95% interval on ROC AUC, so the recorded number is the one the decision is judged on (`docs/current/FINETUNING_DECISION_LOG.md`). |
| `pr_auc` | 1 | Area under the precision–recall curve (average precision) for the positive class. | The imbalance rescores (#122) needed a metric that does not reward the majority class; the pilot records AUC and PR AUC together so a change in ranking under imbalance is visible. |
| `brier` | 1 | Mean squared error of the predicted probabilities: `mean((p - y)^2)`. | D6 judges calibration by whether Brier increases, so the recorded Brier is the number the anchor's calibration verdict rests on. |
| `log_loss` | 1 | Cross-entropy of the predicted probabilities, with probabilities clipped to `[1e-15, 1 - 1e-15]`. | `PILOT_2_DESIGN.md` §3 names log loss the primary loss; the clip is what makes the recorded value finite on confident mistakes. |
| `ece` | 1 | Expected calibration error over 10 equal-width probability bins: the bin-weighted gap between mean predicted probability and observed frequency. | D11 redirected the next step to calibration, which needs a number for "how far off are the levels" rather than for ranking. |

## Not yet in the registry

`lift` and `calibration_slope` are the next slice (#360). They are scores-only metrics in the
sense that no run records them, so rescore supplies them rather than comparing them.
