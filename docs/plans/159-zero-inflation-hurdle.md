# Plan — hurdle models in the zero-inflation study (#159)

**Issue:** #159 (question 1, zero inflation). Protocol ticket for the TabPFN comparison: #662, which carries
the hypothesis, bar and falsifier (labelled `needs-decision` until a maintainer signs off the bar). Builds on
[`159-zero-inflation-port.md`](159-zero-inflation-port.md).
**Status:** Current — code only; no hurdle run has been made, so there is no result and no verdict.

## What and why

The study compared TabPFN with Poisson, ZIP and ZINB GLMs on mean-matched zero-inflated NB2 counts.
Prior Labs' 2026-10-14 meeting (`experiments/pilot2-phase2/PRIOR_LABS_MEETING_2026-10-14.md`, point 7)
said a two-stage (hurdle) formulation is usually best for zero-inflated targets; the repository never
tested it. This change adds the hurdle family to the existing sweep, as code, so that the claim can be
measured on the same cells as the five models already scored.

## What is added

| Model | Zero part | Count part | Role |
| --- | --- | --- | --- |
| `hurdle_poisson_glm` | logit in the full x | zero-truncated Poisson | misspecified tail, the hurdle counterpart of ZIP |
| `hurdle_nb_glm` | logit in the full x | zero-truncated NB2 | the DGP's own positive part, the hurdle counterpart of ZINB |
| `tabpfn_hurdle` | TabPFNClassifier on `y > 0` | TabPFNRegressor fit on the positive rows only | the formulation Prior Labs recommended |
| `tabpfn_recheck` | — | plain `tabpfn`, refitted | control: does the hosted `v3.5_default` still return what it returned in September? |

## Decisions, and why each went this way

1. **Both families, GLM and TabPFN.** A GLM hurdle alone says nothing about TabPFN, which is the question.
2. **Both count tails for the GLM**, so the hurdle pair mirrors ZIP/ZINB: one wrong tail, one right one.
3. **Logit zero part, built by hand** (`sm.Logit` + `TruncatedLF*`). statsmodels' `HurdleCountModel`
   uses a zero-censored count model for the zero part, not a logit; the logit is the actuarial standard
   and the counterpart of the TabPFN classifier.
4. **Full covariates in the zero part.** Under this DGP P(Y = 0 | x) = π₀ + (1 − π₀)·NB2(0 | x) depends
   on x, so an intercept-only hurdle would be wrong by construction. The logit in x is close but not
   exact — the hurdle is slightly misspecified in its zero part while exact in its count part. ZIP/ZINB
   keep their intercept-only inflation, which is exact for them; the asymmetry is the DGP's, not a choice
   of convenience, and is stated wherever the models are compared.
5. **Renormalised continuous count part for TabPFN.** P(k) = p·[F(k+½) − F(k−½)] / [1 − F(½)] for k ≥ 1:
   a regressor trained on y ≥ 1 can still put mass below ½, and without the denominator the distribution
   would not sum to one.
6. **No native NLL for `tabpfn_hurdle`.** The zero is a point mass; `native_nll_mean` and
   `native_nll_frac_nonfinite` are NaN, and only the continuity-corrected NLL is compared.
7. **Mean by the midpoint rule.** E[Y] = p·E[Z | Z > ½], the second factor averaged over 500 quantiles of
   the truncated distribution — deterministic, unlike the Monte Carlo mean of `tabpfn_log1p`, and unclipped
   because the raw-scale tail is not exponentiated.
8. **Regressor on y, not y − 1**, with no transform: the log1p arm already showed no gain.
9. **Same data, checked.** `dgp.draw_cells()` is now the one place that fixes the rng order; the sweep and
   `check_reproducible.py` both use it. Run before this change: 117 cells (α = 1, 2, 4; seeds 0, 5, 9;
   every arm) regenerate the committed data exactly and refit `poisson_glm` to the committed metrics.
10. **Own environment.** statsmodels is not in the lock, and the lock pins `tabpfn-client` 0.3.3; the
    sweep runs in its own venv with versions recorded in the run record, as the other v3.5 re-tests did.
11. **A drift control.** `tabpfn_recheck` refits plain TabPFN on a few seeds, so the paired comparison
    against the September `tabpfn` rows can show it is not comparing two different servers.
12. **Separate result file.** Hurdle rows go to `results/alpha_<α>/results_hurdle.csv`; the committed
    `results.csv` and the hashes in `figures/manifest.json` stay untouched.
13. **Results in their own document** in the campaign, once there are results; the current report gets
    a dated note only if the answer to its question changes.
14. **One-class fallback.** When the training rows hold no zeros or no positives (the Poisson baseline arm
    at λ ≈ 8 can have none) the binary part is a constant (n_pos + ½)/(n + 1), and the row records
    `hurdle_binary_fallback = True`.

## What is not decided here

The hypothesis, the bar and the falsifier for the TabPFN comparison belong to the protocol ticket, #662, and its
maintainer sign-off (`docs/agents/research-workflow.md`): an agent does not set them. The GLM hurdle rows are
descriptive — no verdict is attached to them unless a ticket of their own asks for one.

## Verification

- `tests/test_zero_inflation_hurdle.py`: the hurdle arithmetic sums to one and gives the truncated mean
  (numpy only, always runs); each hurdle GLM is a distribution whose P(0) and mean match its pmf; the
  one-class fallback; hurdle rows never reach `results.csv`. The GLM tests skip without statsmodels.
- `check_reproducible.py --alpha <α> --seeds 0 5 9`, all three α: 0 mismatched.
- The refactor does not move the original models: `fit_and_score` on α = 1 and 4, seeds 0 and 7, every
  cell, reproduces the committed `poisson_glm`, `zip_glm` and `zinb_glm` rows to rtol 1e-6 — 156 rows,
  0 differ (statsmodels 0.14.6). TabPFN rows are not re-checked here; that is `tabpfn_recheck`'s job.
- `figures/manifest.json` is not regenerated: its script hashes now match commit `ee73792`, not the edited
  `dgp.py`, `models.py` and `run_sweep.py`. The campaign README says so.
- `./scripts/check.sh` — all eight checks. Run locally: ruff, pytest, evidence, doclinks, docstatus,
  citation and verdict pass; shellcheck is not installed on this machine and no shell script is touched,
  so it is left to CI.

## Cost

GLM rows are local and free. `tabpfn_hurdle` is two hosted fits per cell — 130 cells per α, 780 fits over
three α. `tabpfn_recheck` on seeds 0–1 is 26 fits per α. No hosted call has been made by this change.
