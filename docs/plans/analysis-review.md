# Plan: `analysis-review` skill

**Status:** agreed 2026-11-05 (grill), in progress. Branch: `chore/analysis-review`.

## Why

The Matt Pocock workflow is a software-delivery lifecycle; its review row — `code-review`
reviewing a diff against Standards and Spec — has no research analogue here. CI mechanises
the *artifact* gates (`evidence`, `citation`, `verdict`, `doclinks` in `./scripts/check.sh`),
but nothing judges whether a claim is supported by its evidence, or whether the inference
follows the pre-registered SAP. #440 added the craft skills (dataviz, eda, literature);
this closes the delivery-discipline gap: the report ships reviewed, the way code ships
reviewed.

## What

1. **`.opencode/skills/analysis-review/SKILL.md`** — model-invoked, standalone:
   - reviews a drafted report or `docs/analyses/` note **against its evidence**;
   - **hard findings** (block calling the report done): a claim with no evidence file, a
     missing or mixed version pin, a comparison outside the pre-registered SAP, a verdict
     contradicting the D3 / null-band rule, a missing or duplicated registry row;
   - **soft findings** (judgement): thin or stale evidence, unstated limitations,
     overclaiming language;
   - judgment only — CI owns the mechanical gates, no duplication;
   - evidence mapping is **inline**: every quantitative claim names its file; findings are
     **conversation-only** and the report gets fixed.
2. **One-line pre-ship pointers** in `tabpfn-technical-report` and
   `tabpfn-nontechnical-report`, so the review is reachable from the report flows.

## Decisions (settled in grill-with-docs, 2026-11-05)

| Decision | Choice |
| --- | --- |
| Review target | a drafted report / note against its evidence (not work-in-progress) |
| Enforcement | findings report, hard vs soft — hard blocks "done" |
| Depth | full: claim→evidence trace + SAP compliance + verdict rule |
| Evidence mapping | inline in the report; review validates path, run/dataset/version, number match |
| Findings output | conversation only; the report is fixed, nothing extra committed |
| Gate overlap | judgment only; CI owns evidence/citation/verdict/doclinks |
| Placement | standalone skill + one-line pre-ship pointers in the two report skills |
| Name | `analysis-review` |
| Batch type | chore — no ticket for the skill itself |

## Acceptance (evidence appended below as it lands)

- [x] `skills-ref validate` → `Valid skill` (2026-11-05)
- [x] **smoke:** the review procedure run on `docs/analyses/tabarena_insurance_benchmark_direction.md`
      (report-only, nothing edited). **0 hard findings** — registry row present and
      unduplicated, no own measurements so no version pin needed, no statistical tests so
      SAP/D3 are N/A. **4 soft findings:** the "38 method families / 51 + 142 datasets"
      numbers are not cited inline (the arXiv source sits in the Key links table);
      "leaderboard is read-only" and "TabPFN Client is the only tabular FM with a hosted API"
      are unverified observations; "most of this already exists … a packaging job" names no
      repo paths.
- [ ] `./scripts/check.sh` — all eight checks green
- [x] `CHANGELOG.md` `[Unreleased]` entry added
- [x] `/code-review` against this plan and `CODING_STANDARDS.md` — **Standards:** 0 hard
      findings; 2 judgement calls (the one-line pre-ship pointer is necessarily duplicated in
      the two report skills — each must stand alone; no committed test — the settled
      acceptance is the smoke). **Spec:** 0 findings — every plan item, decision and
      acceptance criterion holds against the files.

## Build order

skill → pointers → changelog → validate → smoke → gates → review.
