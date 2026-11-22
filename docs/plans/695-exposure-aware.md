# Plan — exposure-aware GLM follow-up (#695)

§19.4 flagged, and never scheduled, a re-test of the six classification datasets against GLMs that
treat exposure the actuarial way. Until it ran, "AUC #1 on all six" was a known-unsupported claim.

## What

- `docs/experiments/frontier-benchmark/exposure_aware_glm_followup.md` — the analysis, with the
  anchor, the method, the 16 measured rows and the corrected claim.
- `scripts/eval/insurance_benchmark_v1/exposure_aware_glm_followup.csv` — the evidence table.
- Two surgical amendments: the §19.4 sentence that promised this follow-up, and the
  `KNOWLEDGE-PATH.md` verdict that asserted "all six".
- The campaign README lists the new document.

## Why

The claim appears in the current on-ramp and in the archived one-pager. A reader acting on it would
treat `norauto` as a win when an exposure-aware GLM beats it. The correction is small, measured and
cited; leaving it undone makes the conclusion depend on an assumption.

## Verification

- The anchor reproduces §19.4 to the published digits (0.17755 / 0.17433 against 0.17755 /
  0.17432), so the specification is not a new one.
- `./scripts/check.sh doclinks` and `./scripts/check.sh docstatus`.
- Numbers in the note are generated from the CSV, not typed.

## Out of scope

- `coil2000`: no exposure column, so the treatment cannot be applied. Excluded by construction and
  said so, rather than fitted without exposure and reported as comparable.
- Changing the adoption rule. §19.4 already recorded `norauto`; this shows it is the exception.
