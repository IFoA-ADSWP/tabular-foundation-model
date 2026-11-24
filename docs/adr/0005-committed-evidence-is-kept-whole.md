# Committed evidence is kept whole; the clone is the price

> **Status:** accepted, 2026-11-24 · issues #584, #694, #739

The repository is the evidence base for the paper. Its weight is mostly cited run
captures, and the citation rule treats a capture as the producer of a published number.
This record decides whether that weight is a problem to fix before submission.

## Context

Measured on 2026-11-24, after the epoch-ladder and fair-test evidence landed:

| Item | Size |
|---|---:|
| `.git` before `git gc --prune=now` | 730 MB |
| `.git` after `git gc --prune=now` | **600 MB** (one pack, 565 MiB) |
| `results/` checkout | 517 MB |
| `results/` tracked content | 495 MB across 10,435 files |
| run directories | 87 |
| cited run content | **514 MB** |
| uncited run content | 5 MB |

The tracked weight by array:

| Array | Size | Read by |
|---|---:|---|
| `quantiles.npy` | 277 MB | `freq_sev_quantiles.py` only |
| `ground_truth.npy` | 54 MB | row bootstrap, rescore, estimand diagnostic |
| `predictions.npy` | 52 MB | the same |
| `test_index.npy` | 50 MB | the same |
| `cluster_id.npy` + `weights.npy` | 57 MB | the grouped severity analyses |
| `exposure.npy` | 12 MB | French frequency |
| `meta.json` + `capture.json` | 8 MB | the citation gate |
| other | 21 MB | |

**220 MB of the 277 MB of quantiles is in runs no cited analysis reads**: the two ladder
captures (187 MB) and the two #572 row-scaling captures (33 MB). The 57 MB that
`freq_sev_quantiles.py` reads belongs to the four registered fair-test runs.

#694 proposed that ~100 MB was duplicated. Re-measuring `predictions_sha256` and
`truth_sha256` across all 87 trees finds one identical group — `20261113T223003Z` and
`20261114T003003Z`, 2.3 MB each, both cited. The four pairs the ticket listed are different
training budgets on the same folds, not duplicates.

## Decision

1. **Accept the budget** at roughly **600 MB `.git` + 517 MB checkout**. The number is the
   citation rule working as designed: 514 of 520 MB of run content is cited.
2. **`git gc --prune=now` is the only applied reduction.** It removed 130 MB of loose
   objects. No tracked evidence is deleted, moved or rewritten.
3. **Keep every array a cited capture hashes.** Predictions, truth, test indices, weights
   and clusters are what the row bootstrap, rescore and estimand diagnostic read. Quantiles
   are the contract's proof that the distribution was captured, even where no current
   analysis reads a particular run's copy.
4. **No history rewrite before submission.** Stable SHAs are what every run id, citation
   and capture points at.
5. **A clone below ~300 MB would require external evidence storage** — release assets, a
   separate `-evidence` repository, or both, with manifests and DOIs kept here. That is a
   post-submission project with a changed citation rule, not a pre-submission cleanup.

## Considered options

- **Prune the uncited runs and the exact duplicate.** 7 MB. Real, but invisible to a clone
  and not worth deleting a cited 2.3 MB copy or a partial run that a future analysis may
  claim.
- **Prune the 220 MB of unused quantiles.** Takes the checkout from 517 MB to ~300 MB and a
  full clone from ~1.1 GB to ~0.9 GB, because the old blobs remain in history. It requires a
  capture-contract amendment permitting a pruned quantile hash. Rejected: checkout-only
  saving, contract complexity, and the evidence is worth more than the disk.
- **Externalise the arrays or rewrite history.** The only routes to a materially smaller
  clone. Both break stable SHAs/citations and cost more than the disk they save before a
  submission.

## Consequences

- A fresh clone is about 600 MB of history and 517 MB of checkout. That is the price of the
  citation rule and is accepted.
- Every future run adds its arrays. If the budget is ever exceeded, this record is the
  place to revisit — with a measured table, not a projection.
- Readers who only need the numbers can use the capture manifests and result notes; they do
  not need to clone the arrays, but a clone will carry them.
- #694 is closed as measured: its 100 MB duplicate premise is not supported. The
  enforce-a-budget half is superseded by this acceptance; a future gate would be a new
  decision, not a silent change.

## How to re-measure

```
git count-objects -vH
du -sh .git results
```

Then walk `results/` grouping by filename, and take the cited set as the bare run ids
appearing under `docs/` (the same set `scripts/check_citations.py` checks). The measurement
is dated because run content changes; the numbers above are not a permanent constant.
