# Epoch ladder — result: the sign of fine-tuning flips between the two severity targets

**Status:** current — result note, 2026-11-22. **Tickets:** #672 (the ladder), #629 (the direction
decision and its amendment), map #623. **Design and resolution:** `EPOCH_LADDER_DESIGN.md`.
**Model:** `v3_default` — tabpfn 8.5.0, `tabpfn-v3-regressor-v3_default.ckpt` (recorded in every slot's
`meta.json`; no version era is mixed).
**Evidence:** [`results/20261121T153848Z/`](../../../results/20261121T153848Z/) (`severity_french`,
RMSE on log amount), [`results/20261121T232424Z/`](../../../results/20261121T232424Z/)
(`severity_spanish`, weighted RMSE, unit `claiming_policy`), and the four `eudirectlapse` launches of
PR #677 (`outputs/gpu-pilot/runs/20261121T055128Z`, `…T070014Z`, `…T080738Z`, `…T084033Z`).

Seeds 1001–1020, Arms `A_raw` / `B_ft3` / `B_ft10` / `B_ft30`, paired across seeds. Severity targets:
10,000 rows on French per-claim RMSE, and 4,760 rows (the data's cap) on Spanish claim-weighted
per-policy RMSE, five folds each. `eudirectlapse`: one stratified 10,000/1,000 split, not folds. All
intervals are 95 %.

## The verdicts, in the pre-registered rule's terms

#672 froze: **CONFIRMED** if both bar parts hold — (1) the 30 − raw paired interval excludes zero in
the helpful direction, (2) the 30 − 10 interval is not negative beyond the noise band;
**REFUTED** if the falsifier is hit — the 30 − raw interval excludes zero harmful, or the 30 − 10
interval excludes zero negative; **UNRESOLVED** if the interval covers zero.

| Dataset | `30 − raw` (95 % CI) | bar / falsifier | Verdict |
| --- | --- | --- | --- |
| `eudirectlapse` | +0.00205 AUC [−0.0047, +0.0089], t = 0.63 | interval covers zero | **UNRESOLVED** |
| `severity_french` | **+1.37 %** [+0.61 %, +2.12 %] (worse) | falsifier hit: 30 − raw excludes zero **harmful** | **REFUTED** |
| `severity_spanish` | **−1.29 %** [−2.08 %, −0.50 %] (better) | bar 1 holds; bar 2 holds (30 − 10 = −2.60 %) | **CONFIRMED** |

Percentages are relative to the **lower** arm of each contrast (for 30 − raw, the raw mean). The
French severity metric is per-claim RMSE (one weight per row); the Spanish metric is claim-weighted
per-policy RMSE.

### `severity_french` — REFUTED

| Arm | mean RMSE (log) |
| --- | ---: |
| `A_raw` | **1.11991** |
| `B_ft30` | 1.13521 |
| `B_ft10` | 1.19613 |
| `B_ft3` | 1.21031 |

`B_ft3 − A_raw` +8.07 % [+5.90 %, +10.25 %]; `B_ft10 − B_ft3` −1.17 % [−4.09 %, +1.75 %];
`B_ft30 − B_ft10` −5.09 % [−8.03 %, −2.15 %]; `B_ft30 − A_raw` **+1.37 % worse** [+0.61 %, +2.12 %].

### `severity_spanish` — CONFIRMED, with the monotone clause failing

| Arm | mean weighted RMSE |
| --- | ---: |
| `A_raw` | 0.65053 |
| `B_ft3` | 0.65122 |
| `B_ft10` | 0.65929 |
| **`B_ft30`** | **0.64214** |

`B_ft3 − A_raw` +0.11 % [−0.38 %, +0.59 %]; `B_ft10 − B_ft3` **+1.24 % worse** [+0.70 %, +1.79 %];
`B_ft30 − B_ft10` −2.60 % [−3.47 %, −1.73 %]; `B_ft30 − A_raw` **−1.29 % better** [−2.08 %, −0.50 %];
`B_ft30 − B_ft3` −1.39 % [−2.42 %, −0.37 %].

**The rule says CONFIRMED; the hypothesis says the ladder is non-decreasing in epochs, and it is
not** — ten epochs is worse than three. The frozen rule tests the two bar parts and no monotonicity
clause, so it cannot express this. That is a defect in the pre-registration, recorded here rather
than papered over: both statements are true at once, and the decision record should say so.
**Decision (#711, 2026-11-22):** CONFIRMED stands under the frozen rule — retrofitting a
monotonicity clause now would move the bar — and the shape is recorded as **non-monotone**. The
next ladder freezes the clause and its consequence before its run; a failed clause will not flip the
bar verdict, but it will bar any dose-response claim.

## What the pair establishes

1. **The sign of fine-tuning against raw flips between the two severity datasets** — French worse at
   every rung, Spanish better at 30. This is **not a new finding**: the fair test's single-rung
   comparison already recorded `severity_french` −0.92 % [−1.16, −0.68] No-go and
   `severity_spanish` +1.64 % [+0.24, +3.05] Inconclusive (the fair test's `r` is improvement-positive,
   the reverse of this note's contrast). The ladder **confirms and tightens the
   per-target record**: it adds the dose axis and shows the Spanish gain is reached only at 30. It
   does **not** make a task-level severity claim: the two targets sit on different estimands, and by
   the estimand decision (#729, 2026-11-22) the fair test's pooled severity row is descriptive only.
   What flips is each target's own registered metric.
2. **The 10 → 30 step improves on both severity targets** (−5.09 %, −2.60 %), the one dose contrast
   that survives both. Where fine-tuning is used, 30 epochs is the best rung on both; on French it is
   still worse than raw, so the rung buys the smaller harm, not a gain. Ten epochs is the worst on
   Spanish and no better than 3 on French.
3. **Three epochs is not a cheap substitute** — indistinguishable from raw on Spanish, clearly worse
   on French.

## Deviation from the pre-registered method

#672 froze **paired bootstrap** intervals; the numbers above use **t-based** 95 % intervals on the 20
paired differences. Recorded as a dated deviation per `FINETUNING_STATISTICAL_ANALYSIS_PLAN.md`, with
the result computed **both ways**: percentile bootstrap over the same 20 seeds gives
French 30 − raw [+0.0096, +0.0242], French 30 − 10 [−0.0968, −0.0354], Spanish 30 − raw
[−0.0131, −0.0038], Spanish 30 − 10 [−0.0223, −0.0118]. **Every verdict is unchanged.**

The analysis plan also lists the epoch ladder as *exploratory, no decision role*. The adoption
language below is therefore read as the decision this result supports, not as a powered decision
test; promoting the ladder out of exploratory status is a decision for #629, not something this note
can assert.

## Resolution — which floor this note invokes

Two different floors exist and they should not be confused:

- **Registered**: #672 froze an MDE of **0.0021 AUC** (SD 0.0034). The `eudirectlapse` run's observed
  paired SD is **0.0145**, so its half-width is ~0.0068 against that MDE — about **3.2× wider**,
  with the observed SD 4.3× the frozen one. UNRESOLVED is still the correct verdict, but the
  registered power was not achieved and that is a fact about the design, not about the target.
- **Observed**: for the severity targets, resolution is read from the intervals the run produced, not
  imported from the classification case. French `10 − 3` (−1.17 %) has an interval covering zero and
  is unresolved; Spanish `10 − 3` (+1.24 %) has an interval excluding zero and is resolved.

**Decision (#712, 2026-11-22):** the next ladder freezes a per-metric MDE and a seed count that meets
it, and every result carries "registered MDE vs observed half-width" per target. This note supplies
the pair for `eudirectlapse`; no ladder MDE is registered for the severity targets (the fair test's
severity MDEs belong to a different design), so their resolution is read from their own intervals,
as above. No verdict changes; `eudirectlapse` remains UNRESOLVED, stated at its observed resolution.

## Limits

- The two severity verdicts are **not like-for-like**: per-claim RMSE (weight 1 per row) on 10,000
  rows versus claim-weighted per-policy RMSE on 4,760 rows. What flips is each target's registered
  metric, not one measurement. By the estimand decision (#729) that is a reporting rule: every
  severity verdict names its unit and weighting, and no task-level severity number carries a claim.
- Two targets defeat "harm is a property of the severity class"; they do not establish a per-target
  rule in general (n = 2), and they do not say *why* the sign flips.
- **On Spanish the estimand as well as the dataset moves the sign.** A post-hoc diagnostic
  (2026-11-22, exploratory) scores these same slots unweighted: Spanish reads +0.81% worse rather than
  −1.29% better, with the weighted gain carried by multi-claim policies (−1.81%) while single-claim
  policies lose (+2.03%). French has one weight per row and no such lever, and its harm is uniform
  across folds and seeds. Recorded in
  [`EPOCH_LADDER_ESTIMAND_DIAGNOSTIC.md`](EPOCH_LADDER_ESTIMAND_DIAGNOSTIC.md), which carries the
  regenerate command (`scripts/analyses/severity_estimand.py`); it changes no verdict.
- `eudirectlapse` is a single split, not five folds, and its interval is wider than the design
  assumed.
- Both severity captures were recovered by the re-emit path after transport faults; each capture is
  verified against its declared sha256, and the recovery costs sit in
  `outputs/gpu-pilot/run_*.json` and `outputs/gpu-pilot/reemit_*.json` beside the runs they saved.
