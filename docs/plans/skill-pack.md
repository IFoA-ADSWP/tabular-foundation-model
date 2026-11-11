# Plan: skill-pack — `dataviz`, `eda`, `literature`

**Status:** agreed 2026-11-05, in progress. Branch: `chore/skill-pack`.
**Evidence for the gap:** `docs/analyses/skill_sets_for_ds_research.md` (reference tier, committed with this change).

## Why

The research found RunCell's six published data-science skills unobtainable (no verified
install path) and identified three genuine gaps here: journal-grade figures, a disciplined
first pass over data before modelling, and citation hygiene across literature docs. Each is
cheaper to write bent to this repo's governance (`REPORT_REGISTRY.md`, the pre-registered
SAP, `MODEL_VERSIONS.md`) than to install. This plan builds those three as one batch, plus
one dead-pointer fix.

## What

1. **`.opencode/skills/dataviz/`** — dual-mode figure skill:
   - **static mode:** matplotlib/seaborn + shared rcParams module `scripts/infra/figure_style.py`
     for docs/papers — column widths, ≥8 pt embedded fonts, Okabe-Ito palette, vector + 300 dpi
     export, caption draft, export checklist (the journal gap).
   - **HTML mode:** plotly (already in `requirements.txt`) + a shared theme, producing
     self-contained HTML figures agents can render and a human can open and inspect.
   - **new figures only** — committed figures under `docs/figures/` are cited evidence and
     are not touched.
2. **`.opencode/skills/eda/`** — first-pass analysis skill filling the space between
   `tabpfn-explore` (readiness) and a modelling run: leakage, time-ordering, ranked findings.
   Output is **one tight note in `docs/analyses/`, registered in `docs/REPORT_REGISTRY.md`**
   — registration is the dedup gate that stops it becoming a sprawling auto-report.
3. **`.opencode/skills/literature/`** — "no identifier, no citation" plus the
   verified/unverified/corrected statuses from `docs/current/FINETUNING_LITERATURE.md`,
   applied across **all** literature docs; capable of emitting the repo's first
   `references.bib`.
4. **Dead pointer fix:** `docs/README.md` "Outside docs/" points at `.github/skills/`,
   which does not exist; the real path is `.opencode/skills/`.

## Decisions (settled in grill-with-docs, 2026-11-05)

| Decision | Choice |
| --- | --- |
| Scope | all three skills as one batch, one session, `/code-review` at the end |
| Home | repo-local `.opencode/skills/` (travels with the repo, can cite governance by path) |
| Route | this plan + one session; no spec or tickets for the batch itself |
| Figure strategy | dual-mode: static rcParams **and** plotly HTML ("integrates well with html") |
| EDA artifact | `docs/analyses/` note + `REPORT_REGISTRY.md` entry |
| Literature blast radius | all literature docs, one convention |
| Validation | `skills-ref validate` manually now; CI check = follow-up ticket after landing |
| Acceptance | cheap smoke per skill (below) — no full first use in this batch |
| Batch type | chore — no ticket for the batch; exactly one tracker issue comes out of it |

## Acceptance (evidence appended below as it lands)

- [x] `skills-ref validate` passes on each of the three skills — `Valid skill` ×3 (2026-11-05,
      `uvx --from skills-ref agentskills validate`). **Deviation:** `argument-hint` was removed
      from all three frontmatters — the spec allows only
      `allowed-tools, compatibility, description, license, metadata, name`. Conformance was the
      settled decision; the eight pre-existing local skills keep their `argument-hint` untouched.
- [x] **dataviz smoke:** static — `outputs/skill-pack-smoke/smoke_static.pdf` (11.7 KB) +
      `.png` (58.6 KB, measured 300 dpi), series drawn from the Okabe-Ito cycle
      (`#E69F00`/`#56B4E9`, no ad-hoc hex); HTML — `smoke_interactive.html` (4.5 MB, the
      embedded plotly.js bundle) with **0 external `<script src>` tags**, so it opens offline.
      Checklist module exports 5 items.
- [x] **eda smoke** (report-only, nothing registered): `data/raw/fretelematic.csv`
      (1,177 × 16) walked the checklist. Ranked findings: **1.** no date/timestamp column —
      time-split and drift checks impossible, IID folds only; **2.** `Policy_ID` is unique —
      identifier, drop from features; **3.** `Acceleration`/`Brake`/`Corner` are lossy recodes
      of their score columns (201 rows labelled `Low` with score > 75) — keep one
      representation; **4.** 13.4% positive class — stratified splits; **5.** `Total_Distance`
      right-skewed (103–51,656). Open question: are the telematics scores measured pre- or
      post-claim (the #216 pattern)? Not answerable from the file — needs the data dictionary.
- [x] **literature smoke** (report-only, doc unedited): audit of
      `docs/archive/papers/FOLLOW_UP_ROUND2_JOURNAL_SHORT.md` — no reference section, zero
      citation markers (0 matches for et al / years / `[n]` / doi / arxiv across all 120 lines);
      the only "prior" claims are internal run-state notes, correctly not external citations.
      Violation list produced: the doc carries no identifiers anywhere; a submission version
      needs a reference list. Nothing edited.
- [x] `ruff check scripts/ src/ tests/` — `figure_style.py` clean; the 64 reported errors are
      pre-existing debt in untouched files (tracked by branch `feat/258-clear-lint-debt`),
      unchanged by this branch.
- [x] `pytest tests/ -q` — **247 passed** in 67 s (1 unrelated jupyter warning).
- [x] `shellcheck --severity=warning scripts/gpu_helpers/*.sh` — clean (no `.sh` touched).
- [x] doc link/doc-status checks — neither `skill_sets_for_ds_research.md`, `skill-pack.md`,
      the three SKILL.md files, nor the README edit appears in either failure list; the
      pre-existing failures (`docs/README.md:121 → docs/reports/…`, status backfill 11/38) are
      unchanged and existed before this branch (verified: `docs/reports/` does not exist;
      README diff is the single line-153 pointer fix).
- [x] `/code-review` against this plan and `CODING_STANDARDS.md` — **Standards:** 1 hard finding
      (missing `CHANGELOG.md` entry — CONTRIBUTING's checklist — fixed in this change) and 3
      judgement calls (figure outputs to `docs/figures/` follows current practice, not
      CONTRIBUTING's older `outputs/current/figures/` map; no committed test for the style
      module — the settled acceptance was the smoke; unused `OKABE_ITO["black"]` kept as the
      canonical 8-colour palette). **Spec:** no findings — every plan item and acceptance
      criterion holds against the files.

## Follow-up (not in this change)

- Tracker ticket when this lands: add `skills-ref validate` to CI (verify the tool installs
  cleanly in CI first — separate review, separate risk).

## Build order

dataviz (skill + module) → eda → literature → README fix → smokes → validate → review.
