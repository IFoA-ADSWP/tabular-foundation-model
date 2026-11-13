# Lapse Students

> **Status:** index — this campaign's reading order, not a report of its own.

The two lapse datasets could previously only be compared against **estimates** of the boosted-tree
baselines: CatBoost, XGBoost and RandomForest were never fitted at full size, so the Spanish Motor Lapse
headroom came from a 2,000-row pilot subsample and EU Direct Lapse's negative sign rested on a
`LinearModel` proxy. This campaign turns those cells into measurements on the teacher's own five folds,
reusing the committed teacher scores (#377, under map #368).

**One run, no spend** — no GPU, no hosted call, no protocol change.

## Documents

| Document | Status | What it holds |
| --- | --- | --- |
| [`377-lapse-students.md`](../../plans/377-lapse-students.md) | Current | the plan: what was estimated, why the teacher's folds are the right comparison, and what the two measurements must show |

The plan stays in `docs/plans/`, which holds one file per task; this folder holds what the campaign is.

## Runs

Committed under `results/`:

```
20261031-lapse-students
```
