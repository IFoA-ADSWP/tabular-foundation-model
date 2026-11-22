# Epoch ladder — how much of the severity sign flip is the estimand

> **Status:** current — post-hoc exploratory diagnostic, 2026-11-22. **Refs** #672, #629.
> **No bar, no verdict, no decision role.** The statistical analysis plan lists pooled-policy and
> per-seed-spread readings as exploratory, and this reading was chosen after the result was seen. Both
> verdicts and every registered number stay with [`EPOCH_LADDER_RESULT.md`](EPOCH_LADDER_RESULT.md),
> which is their authority. **Model pin:** `v3_default` — tabpfn 8.5.0,
> `tabpfn-v3-regressor-v3_default.ckpt`, recorded in every slot's `meta.json`; no era is mixed.

**Question, asked after the fact:** the ladder records `severity_french` as REFUTED and
`severity_spanish` as CONFIRMED, and calls the two "not like-for-like". How much of that contrast is
the datasets, and how much is the estimand each one's registered metric defines?

**Short answer:** part of it is the estimand. French severity carries one weight per row, all 1,
so it has no estimand to switch and its harm is uniform: **0 of 20 seeds and all five folds
worse**. Spanish severity reverses under the unweighted metric — **weighted (registered) −1.29%,
unweighted +0.81%** — and inside the weighted metric the gain sits on multi-claim policies
(−1.81%) while single-claim policies lose (+2.03%). The CONFIRMED verdict stands, because the
registered estimand is the weighted one. What does not stand is the wider sentence a reader may
take from it: "fine-tuning predicts Spanish severity better" holds per claim-equivalent and
reverses per policy.

## What was recomputed, and how

`scripts/analyses/severity_estimand.py` reads the two committed captures and nothing else:

| Target | Run id | Slots | Registered metric |
|---|---|---:|---|
| `severity_french` (`freMTPL2sev`) | `20261121T153848Z` | 4 arms × 20 seeds × 5 folds | unweighted RMSE, log amount, 10,000 training rows |
| `severity_spanish` (`spanish_motor_severity`) | `20261121T232424Z` | 4 arms × 20 seeds × 5 folds | weighted RMSE, log cost, 4,760 rows (the data's cap) |

Each arm's metric is averaged over a seed's five folds; a contrast is the per-seed relative difference
`(M_arm − M_raw) / M_raw`, so its interval is a paired t over 20 seeds (19 df). A negative percentage
is a lower metric, which is better. Nothing is re-run or re-split: the same slots the ladder scored
are scored a second way.

**The intervals here are descriptive, not a test.** They are the ladder's own interval machinery applied
to a second metric; no hypothesis is being tested, and a difference whose interval is clear of zero in
this note is still not a registered finding. It says what the slots contain under another weighting,
which is what the reader needs to read the registered verdict — not a second verdict.

## French severity — no estimand lever, and the harm is uniform

The French capture's `weights.npy` is 1 on every row (it is a per-claim target), so weighted and
unweighted RMSE are the same number. There is no metric choice to reverse the sign:

| Arm | Mean RMSE (log) | vs `A_raw` | Seeds better |
|---|---:|---:|---:|
| `A_raw` | 1.11991 | — | — |
| `B_ft3` | 1.21031 | +8.07% [+5.90, +10.25] | 0/20 |
| `B_ft10` | 1.19613 | +6.81% [+3.71, +9.90] | 0/20 |
| `B_ft30` | 1.13521 | +1.37% [+0.61, +2.12] | 0/20 |

The 30-epoch harm is not a fold or a seed: it is positive in every fold (+3.10%, +1.22%, +0.75%,
+0.96%, +0.85%) and every one of the 20 paired seeds is worse. Nor is the 10,000-row cap the story —
#572's arm repeated this target on each fold's whole claim pool and stayed No-go.

## Spanish severity — the sign is the weighting

Same slots, two multipliers:

| Metric | `A_raw` | `B_ft3` | `B_ft10` | `B_ft30` | 30 − raw | Seeds better |
|---|---:|---:|---:|---:|---:|---:|
| **weighted (registered)** | 0.65053 | 0.65122 | 0.65929 | **0.64214** | **−1.29% [−2.08, −0.50]** | 16/20 |
| unweighted | 0.49102 | 0.50320 | 0.50020 | 0.49499 | **+0.81% [+0.26, +1.36]** | 7/20 |

The weighting is not a post-hoc choice: `weighted_rmse` is the registered verdict metric, and the
grouped severity target is why schema v4 carries `weights.npy` and `cluster_id.npy` at all. But
the unweighted reading of the same slots is a loss of +0.81%, with an interval clear of zero.
Three of five folds carry the weighted gain (−3.30%, −1.24%, −1.68%); the other two are flat
(−0.06%, +0.08%).

### The strata that carry it

The weight is `N_claims_year`: each fold's 1,190 test rows hold 654–689 single-claim policies
(weight 1), and the rest carry 2–18 claims.

| Stratum | `A_raw` weighted RMSE | `B_ft30` weighted RMSE | 30 − raw | Seeds better | Share of weighted squared error |
|---|---:|---:|---:|---:|---:|
| weight = 1 (single claim) | 0.41809 | 0.42840 | **+2.03%** | 8/20 | 12% |
| weight > 1 (multi-claim) | 0.72956 | 0.71621 | **−1.81%** | 16/20 | **88%** |

So the registered win is a win on multi-claim policies, and they dominate a claim-equivalent metric by
construction. On the majority of policies by count — the single-claim ones — 30 epochs is worse.

## Where the dispersion is

The captures record predictions as well as scores, and the arms differ in how much of the target they
try to explain. French predictions spread out under short fine-tuning and creep back towards raw at 30
epochs; Spanish predictions barely move:

| Arm | French std of predictions | French corr with raw | Spanish std | Spanish corr with raw |
|---|---:|---:|---:|---:|
| `A_raw` | 0.1406 | 1.000 | 0.2271 | 1.000 |
| `B_ft3` | 0.3186 | 0.452 | 0.2263 | 0.919 |
| `B_ft10` | 0.3038 | 0.523 | 0.2311 | 0.927 |
| `B_ft30` | 0.1540 | 0.614 | 0.2428 | 0.935 |

The harm tracks that drift: 3 and 10 epochs make the French model's predictions more than twice as
dispersed as raw's and cost 8.07% and 6.81%; 30 epochs pulls the spread back near raw's and costs
1.37%. The error by truth quintile puts the early-epoch damage in the body rather than the tail — on
French, `B_ft3`'s quintile-2/3/4 RMSE is 0.549/0.513/0.563 against raw's 0.324/0.216/0.254 — while
`B_ft30` is slightly *better* than raw in the top quintile (1.5047 vs 1.5351) and slightly worse in the
bottom.

Nothing here establishes that dispersion is the mechanism. It is the description that fits all three
facts at once (harm falls as spread returns, the damage is mid-distribution, Spanish spread never
leaves raw's) and it makes a prediction the design could test: a rung beyond 30 would be expected to
recover more, or overshoot.

## What this establishes, and what it does not

- **Establishes:** the "not like-for-like" caveat is measurable, not rhetorical. On Spanish, changing
  only the weighting — same fits, same rows — moves the sign; on French there is no such lever and the
  harm is uniform across folds and seeds.
- **Does not establish a verdict, or touch one.** Both ladder verdicts are the registered rule applied
  to the registered metrics, and they stand. This note cannot promote a rung, move a floor or decide
  whether the ladder leaves exploratory status — that is #629's call.
- **Does not generalise.** Two datasets; what flips is each target's registered comparison, not one
  measurement; and the unweighted Spanish column is descriptive rather than a registered result.
- **Quintiles are descriptive only.** The same test rows recur in all 20 seeds of a fold, so the pooled
  quintile RMSEs are not an independent estimate and carry no interval.
- **The ladder stops at 30.** French harm shrinking monotonically across rungs says nothing about
  where it would cross zero; that needs a new rung, and a dated amendment before the run.

## Reproduce

```
.venv/bin/python scripts/analyses/severity_estimand.py
```

It reads `results/20261121T153848Z/` and `results/20261121T232424Z/` and prints every table above;
`--results <path>` points it at another checkout of `results/`, and `--severity-french` /
`--severity-spanish` take run ids. Model pin for both captures: `v3_default`, tabpfn 8.5.0
(`tabpfn-v3-regressor-v3_default.ckpt`), as each slot's `meta.json` records.
