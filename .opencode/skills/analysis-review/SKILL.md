---
name: analysis-review
description: 'Review a drafted report or docs/analyses note before it ships — the research analogue of code-review. Hard findings: a claim with no evidence file, a missing or mixed version pin, a comparison outside the pre-registered SAP, a verdict contradicting the D3 or null-band rule, a missing or duplicated registry row. Soft findings: thin or stale evidence, unstated limitations, overclaiming language. Use before calling a report done, when asked to review a report or analysis note, or when checking claims against evidence.'
---

# Analysis Review

CI owns the mechanical gates (`evidence`, `citation`, `verdict`, `doclinks` in
`./scripts/check.sh`). This skill owns the **judgment**: is each claim supported by its
evidence, and was the inference pre-registered? Findings are conversation-only; hard ones
block "done".

## What you review

A drafted report or analysis note about to ship — `docs/experiments/<campaign>/` or
`docs/archive/` —
not work in progress. Name the file and its registry row first.

## Hard findings (block "done")

1. **Claim with no evidence file.** Every quantitative claim names its evidence file inline
   — path, run or dataset id, model version. A claim with no file, or one whose file does
   not contain the number, is hard.
2. **Version pin missing or mixed.** Every number carries the model version it was measured
   under (`docs/MODEL_VERSIONS.md`). An unpinned number, or a claim mixing version eras, is
   meaningless and hard.
3. **Comparison outside the SAP.** The pre-registered design
   (`../../../docs/experiments/pilot2-phase2/FINETUNING_STATISTICAL_ANALYSIS_PLAN.md`) permits paired comparisons only:
   primaries are paired log loss and ROC AUC; transfer is against `T_RAW` and
   `T_RANDOM_LABELS`; interactions are off-ramp only. A test outside that set — or a test
   chosen after seeing the data — is hard.
4. **Verdict contradicting the rule.** Frontier membership is decided by the D3 rule only
   (`GLOSSARY.md`); a verdict's null band must be reproduced by the verdict tool, not
   asserted. A "winner" claim built on a point-estimate comparison is hard.
5. **Registry row missing or duplicated.** Every report has exactly one row in
   `docs/REPORT_REGISTRY.md`. A matching topic key means the existing report is updated,
   never forked into a sibling.

## Soft findings (judgement)

- Evidence exists but is thin or stale: an older run than the claim, arms or seeds missing.
- Limitations unstated: drift, imbalance, leakage risk, single-dataset scope.
- Language overclaims: "proves", "dominant", "universal" where the evidence is a paired
  difference on one dataset at one seed.

## Procedure

1. Read the report and its registry row; list every quantitative claim.
2. For each claim: resolve its evidence file, confirm the number appears in it, and record
   the run id and version pin.
3. Check the inference against the SAP: paired? pre-registered? off-ramp only?
4. Check verdicts against D3 and the null band.
5. Report findings — hard first, each quoting the claim, naming the file, and stating the
   fix; soft second.

Done when: every quantitative claim has a verdict (supported / unsupported / unverified),
the hard findings are listed with their fixes, and the author knows exactly what to change.

## Audit-only runs

When the ask was "review this" with no fix intended: report the findings and say plainly
that nothing was edited.
