---
name: tabpfn-technical-report
description: "Draft technical TabPFN insurance research reports with reproducible evidence, metric tables, workbook references, and dedup checks against the report registry. Use for methods/results writeups, stability analyses, and engineering-facing conclusions."
argument-hint: "Objective, target dataset/task, source tables/logs, source notebooks, and report filename"
---

# TabPFN Technical Report

## When to Use
- Writing technical findings for data scientists or engineers
- Consolidating baseline vs fine-tuned results
- Summarizing regressor stability diagnostics and failure modes

## Pre-Write Checks
1. Read docs/reports/REPORT_REGISTRY.md.
2. Search docs/reports for overlapping topic/title.
3. If overlap exists, extend the existing report unless a new version is explicitly requested.

## Required Sections
1. Objective
2. Experimental Setup
3. Data and Targets
4. Results (with metric tables)
5. Stability/Viability Analysis (when regressor used)
6. Limitations and Risks
7. Recommendation
8. Source Workbooks
9. Evidence Files

## Source Workbooks Rule
- List notebook paths used to derive findings (for example under notebooks/adswp_project or notebooks/baseline_experiments).

## Evidence Files Rule
- List exact table/log paths used (for example outputs/current/tables/*.csv and outputs/current/logs/*.md or *.csv).

## Registry Update Rule
After writing/updating report, update docs/reports/REPORT_REGISTRY.md with:
- report path
- topic key
- audience
- status
- source workbooks
- evidence files
- last updated date

## Pre-Ship Check
- Run the `analysis-review` skill against the draft before calling the report done.
