---
name: tabpfn-nontechnical-report
description: "Draft non-technical TabPFN insurance summaries for business or stakeholder audiences with clear decisions, impact, risks, workbook references, and dedup checks against the report registry."
argument-hint: "Business question, source findings, source notebooks, evidence files, and target audience"
---

# TabPFN Non-Technical Report

## When to Use
- Writing summaries for non-technical stakeholders
- Converting model metrics into decision guidance
- Explaining fine-tuning value and risks in plain language

## Pre-Write Checks
1. Read docs/reports/REPORT_REGISTRY.md.
2. Avoid duplicating existing topics; update existing report where possible.

## Required Sections
1. Key Question
2. What Was Tested (plain language)
3. Main Findings
4. Business Implications
5. Risks and Confidence
6. Recommended Next Step
7. Source Workbooks
8. Evidence Files

## Language Rules
- Prefer plain English over technical jargon.
- If metric names are used, include one-line interpretation.
- Keep conclusions tied to evidence and avoid overclaiming.

## Source Traceability Rules
- Include notebook/workbook references.
- Include tables/logs used to support conclusions.

## Registry Update Rule
After writing/updating report, update docs/reports/REPORT_REGISTRY.md with metadata and links.

## Pre-Ship Check
- Run the `analysis-review` skill against the draft before calling the report done.
