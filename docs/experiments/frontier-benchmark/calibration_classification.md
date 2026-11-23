# Probability calibration — do the predicted probabilities mean what they say?

> **Status:** current — analysis, 2026-11-23 (#745). Reads committed captures; no fit, no capture, no
> spend. **Bar registered before the run** in #745: calibration slope in [0.90, 1.10] on every
> classification target.

**Question.** The benchmark compares models on log loss and Brier, and the paper calls TabPFN's
probabilities usable for pricing. Brier mixes calibration with refinement, so matching it does not show
that a 10 per cent prediction means ten in a hundred. Are the probabilities calibrated?

**Answer: yes, on every one of the six targets.** Slope 0.941 to 1.005, intercept −0.122 to +0.018, and
the mean prediction within 0.0007 of the base rate. **CONFIRMED.**

## Method

```bash
python scripts/analyses/calibration.py            # table
python scripts/analyses/calibration.py --json     # machine form
```

Reads `scripts/eval/insurance_benchmark_v1/predictions/<target>__seed42__v3.5_default.npz`, pools the
five folds, and fits a logistic recalibration of the outcome on `logit(p)`:

- **slope** — 1 is perfect; below 1 the probabilities are too extreme, above 1 too flat;
- **intercept** — 0 is perfect; a non-zero value is a constant bias in the log-odds;
- **deciles** — mean predicted against observed rate, by quantile bin, reported as a diagnostic and
  carrying no bar.

The bar was set on 2026-11-23, before the curve was seen (`DOCUMENT_AUTHORITY.md` records the tolerance
as previously unset; `PILOT_2_DESIGN.md` says an unset tolerance is not a pre-registration).

## Results

| Target | Rows | Base rate | Mean predicted | Slope | Intercept | Brier | Bar |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `coil2000` | 9,822 | 0.0597 | 0.0590 | 0.941 | −0.122 | 0.05232 | met |
| `uslapseagent` | 29,317 | 0.3786 | 0.3781 | 0.987 | +0.018 | 0.07954 | met |
| `bemtl16` | 58,723 | 0.3599 | 0.3599 | 0.997 | −0.002 | 0.20412 | met |
| `ausprivauto0405` | 67,856 | 0.0681 | 0.0683 | 0.997 | −0.009 | 0.06222 | met |
| `bemtl97` | 163,212 | 0.1120 | 0.1115 | 1.005 | +0.014 | 0.09739 | met |
| `norauto` | 183,999 | 0.0459 | 0.0456 | 0.978 | −0.053 | 0.04260 | met |

The largest decile gap is 0.011 (`coil2000`, where the slope is also furthest from 1 and the bins hold
≈1,000 rows); every other target stays within 0.008. The two mildest cases, `coil2000` and `norauto`, are
the two smallest base rates — 6.0 and 4.6 per cent — which is where a slope estimate is least stable.

## What it changes, and what it does not

- **It answers the calibration question for the classification targets**, which the archive had
  registered as unmeasured in `../baseline-conclusion-2026-11/CONCLUSION.md` §4.1. The paper need no longer
  offer a Brier score as evidence of calibration.
- **It does not cover the severity intervals.** A separate verdict (#744) tested coverage at nominal 0.9
  and was **REFUTED**: the fine-tuned arms cover 0.84–0.85, against 0.88 for the raw arms. Point
  probabilities are honest; the *interval* the fine-tuned severity model returns is not.
- **It does not cover the count and severity level.** Their predicted means are already reported in the
  benchmark (§3.1.4 of the paper: TabPFN's mean count prediction is about half the observed rate), and
  that gap is a level bias, not a reliability curve.
- **Scope.** One seed (42), random five-fold splits, `v3.5_default`. No out-of-time validation, no
  recalibration across releases. A calibration claim for another seed or release needs this script run
  on that capture.

## Record

- Issue #745 — the bar, its date, and the verdict. Related: #744 (severity intervals, REFUTED), #732
  (count intervals out of scope).
- Script and test: `scripts/analyses/calibration.py`, `tests/test_calibration.py`.
