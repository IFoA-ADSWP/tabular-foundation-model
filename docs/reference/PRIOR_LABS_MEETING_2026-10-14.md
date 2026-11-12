# Meeting — Prior Labs data scientist (insurance domain)

> **Status:** reference — record of an external discussion, 2026-10-14. Not project evidence;
> nothing here has been measured by this repository. Cite it as *what an external practitioner
> advised*, never as a finding. Cross-checked against the repository in §4.

**Date:** 2026-10-14
**With:** a data scientist at Prior Labs (TabPFN's developers)
**Purpose:** practitioner feedback on where our insurance work sits, and where to spend effort next.
**Audience:** colleagues — what was said, what we think it means, and what it does or does not match in our own results.

---

## 1. Verbatim notes

Reproduced exactly as taken in the meeting. Bracketed `[?]` marks a line whose meaning was not
confirmed at the time; §2 gives the reading where one was confirmed afterwards.

```
Big interest in insurance
Effort to be strong in this side data distribution
Can confirm there are complications with zero inflated
Not in pertaining [?]
Some work arounds
Side comment next release end of year, better on inflated
Usually two staged is the best
Classifications is quite well
Tricky with regressions
Here you're avoiding this
Positive roles [?]
Scaling is sometimes off
Manually upscale factor
Take the target as a log and model log directly, train on the log and then invert
Exposure - glm has natural, xgboost offset, in tabpfn you handle differently,
  good approach is model as target the raw claim amount, have as input column/feature,
  in the inference rescale it by the exposure
Spend more time on fine tuning/feature engineering, regression fine-tuning keep
  classifcation as it is
What he has seen, very frequently data drift, time based split not performing
Easier said than done
More success with scaling the prior for more realistic for zero inflation
Otherwise, you might be able to try taking the data [?]
```

---

## 2. Gloss — what each line means

Read §1 in order; the notes are shorthand and some lines only make sense against their neighbours.

| # | Note | Reading |
| --- | --- | --- |
| 1 | Big interest in insurance | Prior Labs sees insurance as a domain worth serving. Context for everything below. |
| 2 | Effort to be strong in this side data distribution | The differentiator is not the model but **matching the data distribution** — insurance data has shapes (zero mass, exposure, drift) that the pretraining distribution does not. |
| 3 | Complications with zero inflated | Zero-inflated targets are a known hard case. He can confirm it from the vendor side. |
| 4 | Not in pertaining | **Confirmed: not in the pretraining prior.** Zero-inflated structure is absent from what TabPFN was trained on — which is why it struggles, and why line 13 ("scale the prior") follows. |
| 5 | Some work arounds | Workarounds exist for zero inflation; it is not a dead end. |
| 6 | Next release end of year, better on inflated | **Forward-looking vendor comment**, not a commitment in writing. Next TabPFN release, end of 2026, expected to handle zero inflation better. Worth a re-test trigger. |
| 7 | Usually two staged is the best | For zero-inflated / frequency–severity problems, a **two-stage** (hurdle) formulation is usually the best route — rather than one model on the raw target. |
| 8 | Classifications is quite well | Classification is TabPFN's strong axis. |
| 9 | Tricky with regressions | Regression is the weak axis. |
| 10 | Here you're avoiding this | **Confirmed: he means we are avoiding zero-inflation.** He observed that our work sidesteps the zero-inflated case rather than taking it on. |
| 11 | Positive roles `[?]` | *Meaning not confirmed.* Kept verbatim. Possibly a separate aside; do not build on it until clarified. |
| 12 | Scaling is sometimes off / Manually upscale factor | Predicted magnitudes can come out at the wrong scale; a **manual scale factor** may be needed to correct them. |
| 13 | Take the target as a log and model log directly, train on the log and then invert | Model `log(target)` directly, train there, then invert (`exp`/`expm1`) at scoring time. Keeps heavy-tailed severity targets in a range the model handles. |
| 14 | Exposure | The core technical point of the meeting. GLMs have a natural exposure offset; XGBoost has an offset API; **TabPFN has neither**. Recommended approach: make **raw claim amount** the target, put **exposure as an input feature**, then **rescale the prediction by exposure at inference**. |
| 15 | Spend more time on fine tuning/feature engineering | Where to spend effort. |
| 16 | regression fine-tuning keep classifcation as it is | **Split the instruction:** keep classification fine-tuning as-is (it already works), put the new effort into **regression** fine-tuning. |
| 17 | Very frequently data drift, time based split not performing | From what he has seen: drift is common, and time-based splits frequently fail to show good performance. |
| 18 | Easier said than done | His own caveat on line 17 — acknowledging that temporal splitting is hard to do well in practice. |
| 19 | Scaling the prior for more realistic for zero inflation | **The main suggested lever:** he has had more success making the *prior* realistic for zero inflation than fighting it downstream. Ties to lines 4 and 7. |
| 20 | try taking the data | **Confirmed: taking the data (log) — transformed**, i.e. same idea as line 13, stated as a fallback if the prior route does not work. |

---

## 3. Where this points

Four strands, in the order he emphasised them:

1. **Zero-inflation is the real gap.** Not in the pretraining prior (line 4); two-stage is usually
   the best fix (line 7); the most promising lever is scaling the prior to be realistic for it
   (line 19); and he observed we are currently avoiding it (line 10).
2. **Exposure is an unsolved design question for us.** Model raw amount, feed exposure as a
   feature, rescale at inference (line 14) — a concrete, testable recipe.
3. **Effort should shift toward regression.** Keep classification fine-tuning as-is; spend the new
   effort on regression fine-tuning and feature engineering (lines 15–16).
4. **Drift and temporal validation are the standing problem.** Time-based splits often don't
   perform, and it's easier said than done (lines 17–18).

Plus two smaller observations: scaling can be off and may need a manual factor (line 12), and a
log-target formulation is a good default (lines 13, 20).

---

## 4. Cross-check against this repository

What the repository already says about each point. Paths are given so the claim can be checked;
**"silent" means no document in this repo addresses it**, not that the point is wrong.

| Meeting point | Repository says | Verdict |
| --- | --- | --- |
| Zero-inflated complications + workarounds (3, 5) | Zero-inflated severity is a named failure mode — `docs/analyses/regime_characterization.md` §1 (~89% zero mass on `bemtl97_amount`); "the zero-inflation trap" in `docs/analyses/tabpfn_vs_gbdt_baselines_finetuning.md` §14.8. Classed a *target-definition problem that fine-tuning does not fix*. Workarounds recorded: log1p target, count→classification reframe (#67), Gamma/Tweedie/positive-subset metrics. | **Agrees** |
| Not in the pretraining prior (4) | Prior-mismatch is an established framing, but only for **calibration/class imbalance** (`docs/analyses/class_imbalance_analysis_summary.md`). The zero-inflation-generator adaptation is an *unexecuted plan* in `docs/archive/PRE_FINETUNING_INVESTIGATIONS.md` §E7. | **Partial** — concept agrees, no zero-inflation-specific evidence |
| Next release, better on zero inflation (6) | Nothing. The repo only defines a re-test policy when a new `model_path` appears (`tabpfn_vs_gbdt_baselines_finetuning.md` §15; `docs/MODEL_VERSIONS.md`). | **Silent** — *new information; consider adding a re-test trigger* |
| Two-stage is best (7) | Never evaluated. Sole mention is a glossary equivalence, pure premium = Tweedie *or* two models (`docs/KNOWLEDGE-PATH.md`). No hurdle/two-part analysis exists. | **Silent** |
| Classification strong, regression tricky (8, 9) | TabPFN is AUC/PR-AUC **#1 of 14 methods** on all 6 classification datasets, while "the regression gap … remains a genuine TabPFN limit that no setup change fixes" (`tabpfn_vs_gbdt_baselines_finetuning.md` §14.11, §14.13, §12.5). | **Agrees** |
| We are avoiding it (10) | The deferral is openly recorded: "the regression/severity axis the v1 classification pass deliberately deferred" (§14.8), and sidestepping is endorsed — "can the weakest axis be sidestepped by re-expressing the target?" (§14.14, issue #67). | **Agrees** — avoidance documented, partly remedied |
| Scaling off / manual factor (12) | Nothing reports magnitude-off predictions or a manual scale factor. The only "rescale" is `balance_probabilities`, which is condemned as harmful. | **Silent** |
| Log target, train on log, invert (13, 20) | This **is** current practice — `scripts/infra/prepare_insurance_datasets.py` (`log1p` amount, `log` AggClaim), scored on target as stored with `expm1` inversion in `docs/analyses/altmetrics_rescore_spec.md` §2. **Caveat:** log1p is implicated in numerically unstable fine-tuning standardisation (`docs/archive/STAGE_A_B_FINDINGS_AND_RECOMMENDATIONS.md` L119). | **Agrees**, with a fine-tuning caveat |
| Exposure: raw target + exposure feature + inference rescale (14) | `scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py` converts exposure to `log(Exposure)` and uses it as **an input feature for every method**; target stays raw `ClaimNb`. **But** no true offset anywhere, no documented inference rescale, and "exposure-weighted Poisson deviance / offsets refinement" is still an **open item** (§14.4/§14.5). Amount targets use `log1p` amount, not raw. | **Partial** — feature part matches; raw-amount target and inference rescale are **new** |
| More regression fine-tuning, keep classification as-is (15, 16) | Regression fine-tuning is explicitly the *decisive unrun test* (`docs/analyses/levers_assessment.md`); classification-only to date (`tabpfn_vs_gbdt_baselines_finetuning.md` §5.3). **But** the repo's measured verdict is that fine-tuning degrades or is negligible (§5, §14.16), which runs against a blanket "spend more time on fine-tuning". | **Split** — agrees regression FT is the gap; **contradicts** the blanket effort call |
| Data drift; time splits underperform (17, 18) | No dataset carries a time index, so **no temporal split is testable** — all results are conditional on random splits. `docs/current/FINETUNING_EXPERIMENT_REFERENCE.md` §6 says so plainly: "The vendor requires temporal splits… We used a stratified random split — easier than the domain." Literature: fine-tuning fails under gradual temporal shift (verified, `FINETUNING_LITERATURE.md`). | **Agrees** on difficulty; **silent** on the empirical claim — *no out-of-time result exists* |
| Scale the prior for zero inflation (19) | Prior-mismatch framing exists (above), but no report of success from making the prior realistic for zero inflation. | **Silent** — *the headline suggestion, untested here* |

### What this changes

Nothing in §4 overturns a measured result. Four items are **genuinely new** and worth a decision:

| Item | Type | Suggested handling |
| --- | --- | --- |
| Scale the prior to be realistic for zero inflation (19) | New lever, untested | Candidate for the levers assessment — it is the one thing he has *personally had success with*. |
| Two-stage / hurdle formulation (7) | Architecture never evaluated | Decide whether it belongs in the benchmark, or is out of scope. |
| Exposure: raw amount target + inference rescale (14) | Concrete method change | Only the rescale + raw-amount target parts are new; the feature part already matches. Feeds the open exposure/offset item (§14.4). |
| Next release, end of year, better on zero inflation (6) | **Dated external signal** | Add to the §15 re-test policy as a dated trigger in `docs/MODEL_VERSIONS.md`. |

Two points **contradict** current evidence and should not be adopted on authority alone:

- *Spend more time on fine-tuning* — this repo's measured verdict is that fine-tuning degrades or
  is negligible (§5, §14.16). His instruction is narrower than it first reads: regression
  fine-tuning specifically (line 16), which is also the unrun test.
- *Time-based splits underperform* — we cannot check this; no temporal split exists here (§6).

One line is unresolved: **`Positive roles`** (line 11) was not confirmed. Recorded verbatim, not
interpreted. If it matters, ask.

---

## 5. Provenance

- Source: live meeting notes, 2026-10-14, transcribed by the attending project member.
- §2 readings for lines 4, 10, 16 and 20 were confirmed with the note-taker after the meeting.
- Lines marked `[?]` were **not** confirmed and carry no interpretation.
- §4 cross-check performed against the repository as of `fccdb01` (`main`).
- Related prior external feedback: issue **#159**, recorded in
  `docs/archive/PRE_FINETUNING_INVESTIGATIONS.md`.
- This document is **not** project evidence and is version-independent: it records advice, not
  measurements. Every §4 claim is pinned to a file and section.
