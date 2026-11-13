# Skill Sets for Data-Science Research — RunCell vs. what is already installed

> **Status:** reference as of 2026-11-05. Tier: **reference** — a tooling decision document, not a
> measurement; it reports no experimental claim and earns no currency by age.
>
> **Purpose:** decide, in five minutes, which of RunCell's six published data-science skills (and any
> other verified skill collection) are worth adopting here, given the Matt Pocock workflow skills and
> the `.opencode/skills/` tabpfn-* + report skills already installed.

**Sources.** Every claim carries the page or file that owns it. Anything not verifiable from a
primary source is marked **unverified**. All URLs and file paths checked 2026-11-05.
**Scope.** Recommendation only — nothing was installed, and no installed skill file was modified.

---

## 1. What RunCell offers

Six skills, all published at <https://www.runcell.dev/skills>. Every one of the six skill pages
carries the same Information block: **Format** SKILL.md (Agent Skills) · **Works with** Claude Code,
Codex, Cursor, Runcell (Jupyter) · **Runs in** a live Jupyter kernel in Runcell, or your terminal
agent · **Maintained by** Runcell team · **Last updated** Sep 20, 2026 · **Price** Free
(<https://www.runcell.dev/skills/deep-research>, and identically on the other five pages).

The hub page states the set is "Written for Claude Code, Codex, Cursor, and Runcell inside Jupyter"
and that "Each skill is written to run inside a Jupyter notebook as well as in a terminal agent"
(<https://www.runcell.dev/skills>).

### 1.1 Deep Research — <https://www.runcell.dev/skills/deep-research>

- **Does.** "Break the question into a research plan with explicit sub-questions"; runs search, read
  and extract loops and "records every source with URL, date and quote"; "flags contradictions
  between sources instead of averaging them away"; "separates established findings from
  single-source claims"; produces "summary, findings, evidence table, open questions".
- **Produces.** "A cited research report in Markdown"; "a source ledger with URL, access date and key
  quote"; "an evidence table linking each finding to its sources"; "a list of open questions".
- **Checks.** Per-finding confidence levels; contradictions flagged rather than resolved by
  averaging (both from the same page).
- **Requires.** "Yes" to web access — "the skill expects a search or fetch tool. If the agent only
  has local files, it runs the same procedure over that corpus and says so in the report."

### 1.2 DataViz — <https://www.runcell.dev/skills/dataviz>

- **Does.** "Chooses the chart type from the question and the data shape, and says why"; applies a
  consistent style; **publication mode** = "column widths, 300 dpi or vector export, embedded fonts,
  colorblind-safe palettes"; presentation mode; "Exports PNG, SVG and PDF together with the code that
  produced them"; "Writes a draft caption".
- **Produces.** "Figures as PNG, SVG or PDF"; "a reusable style file: matplotlib rcParams or a
  seaborn theme"; "the plotting code in a cell you can rerun"; "a caption draft and an export
  checklist".
- **Checks.** An export checklist that travels with the figure (showcase: "Width: 3.5 in (single
  column) / Fonts: 8 pt minimum, embedded / Palette: colorblind-safe (Okabe-Ito) / Export:
  figure2.pdf (vector) + figure2.png (300 dpi) / Caption draft: written"). The FAQ adds the honest
  caveat: "Always check the final submission guidelines yourself."
- **Requires.** matplotlib + seaborn by default, plotly for interactivity; "The style rules are
  library-independent".

### 1.3 Statistical Test Selection — <https://www.runcell.dev/skills/statistical-test-selection>

- **Does.** "Walks a decision tree: outcome type, groups, pairing, sample size, assumptions";
  "Recommends a test and its non-parametric alternative"; "Checks assumptions with tests and plots
  and states which were violated"; "Runs the analysis in SciPy, statsmodels or pingouin"; "Reports
  statistic, p-value, effect size and confidence interval in APA style"; "Explains the result in
  plain language, including its limits".
- **Produces.** "A test recommendation with the reasoning"; "assumption check results"; "the test
  output with effect size and confidence interval"; "an APA-formatted sentence ready for a results
  section".
- **Checks.** Normality (Shapiro-Wilk) and equal variance (Levene) in the showcase; the FAQ states it
  "never silently runs the parametric test on data that fail the checks."
- **Requires.** Python with SciPy/statsmodels/pingouin. No web access claimed.

### 1.4 Excel Data Analysis — <https://www.runcell.dev/skills/excel-data-analysis>

- **Does.** "Loads multi-sheet workbooks and detects header rows, notes and footers"; "Normalizes
  dates, currencies, percentages and text-as-number columns"; "**Reconciles totals against the source
  sheet before reporting**"; pivots/groups/joins with pandas; "Exports a clean CSV or a formatted
  .xlsx summary when needed"; "Explains each step so a colleague can follow the notebook".
- **Produces.** "A cleaned DataFrame with a documented cleaning log"; answers with the code that
  produced them; "an optional summary workbook or CSV export"; "a notebook you can rerun when next
  month's file arrives".
- **Checks.** Totals reconciliation against the source sheet; a cleaning log that "records what
  changed and why".
- **Requires.** pandas/openpyxl; ".xlsx, .xls, .csv and .tsv, including the exports Google Sheets
  produces". Explicitly *not* Anthropic's xlsx skill: "Anthropic's xlsx skill focuses on creating and
  formatting workbooks. This skill focuses on analysis of existing files."

### 1.5 Academic Research — <https://www.runcell.dev/skills/academic-research>

- **Does.** "Searches arXiv, PubMed, Semantic Scholar and Crossref through available tools";
  "Verifies every citation against a DOI, arXiv ID or PubMed ID before using it"; "Extracts methods,
  datasets, metrics and results into a structured note per paper"; "Builds comparison tables across
  papers"; "Drafts related-work and background sections with in-text citations and a BibTeX file";
  "Flags retracted, preprint-only or unverifiable sources".
- **Produces.** "A verified reference list with identifiers and BibTeX"; per-paper structured notes;
  "a comparison table of methods and results"; draft sections with citations that resolve.
- **Checks.** The blunt rule stated in the page's own words: "**no identifier, no citation**" — the
  citation check runs "before drafting starts", and it "cannot verify content behind paywalls it
  cannot read, and it says so".
- **Requires.** Network fetch/search tools ("Database access depends on which fetch or search tools
  your agent has").

### 1.6 Exploratory Data Analysis — <https://www.runcell.dev/skills/exploratory-data-analysis>

- **Does.** "Profiles columns: types, cardinality, missing values, duplicates"; "Plots distributions
  and flags skew, outliers and impossible values"; "Computes correlations and highlights redundant or
  leaking features"; "Checks target balance and time ordering for modeling datasets"; "Writes a
  plain-language summary with the three to five findings that matter"; "Suggests cleaning and feature
  steps as a follow-up list".
- **Produces.** "A data quality summary"; "distribution and correlation plots in cells"; "a findings
  list ranked by impact"; "a suggested next-steps checklist".
- **Checks.** Leakage and time-ordering explicitly called out as "the ones that have saved models
  from looking better than they were"; on large data it "samples when needed and **says so**", and
  switches to chunked reads or Polars for files that do not fit in memory.
- **Requires.** pandas, matplotlib, seaborn.

### 1.7 Availability — the load-bearing caveat

All six pages say **Price: Free** and **Format: SKILL.md**, but **no primary source I could reach
gives an install path for the SKILL.md files themselves**. Verified 2026-11-05:

- The six skill pages and <https://www.runcell.dev/skills> carry only one outbound CTA,
  <https://www.runcell.dev/download> (the Runcell app). No "download SKILL.md", no git URL, no
  package name.
- <https://www.runcell.dev/docs> lists no skills page (its nav has setup/faq/releases/etc., no
  `skill` string in the page at all); <https://www.runcell.dev/docs/skills> returns 404.
- The Kanaries GitHub organisation (<https://github.com/Kanaries>, linked from the RunCell footer)
  lists no skills repository across its public repos.

**Conclusion: how to obtain these six skills is unverified.** Until that changes, the honest
options are "read the page and re-implement the procedure" or "wait for a published install path" —
not "install it".

---

## 2. The Agent Skills format — which spec is authoritative

- **Authoritative spec: <https://agentskills.io/specification.md>** (read in full 2026-11-05). A
  skill is a directory containing **at minimum `SKILL.md`**; optional `scripts/`, `references/`,
  `assets/`. Frontmatter requires `name` (≤64 chars, lowercase/digits/hyphens, "Must match the
  parent directory name") and `description` (≤1024 chars); optional `license`, `compatibility`
  (≤500 chars, environment requirements), `metadata`, `allowed-tools` (marked *Experimental*).
  The body is free-form Markdown; guidance is "< 5000 tokens recommended" and "Keep your main
  `SKILL.md` under 500 lines."
- **Progressive disclosure** is the load model: "~100 tokens" of metadata at startup, the full body
  on activation, referenced files only when required (same page).
- **Validation** is first-party: `skills-ref validate ./my-skill` from
  <https://github.com/agentskills/agentskills/tree/main/skills-ref>.
- **Provenance, from the spec's own home page:** "The Agent Skills format was originally developed
  by Anthropic, released as an open standard, and has been adopted by a growing number of agent
  products" — <https://agentskills.io/>. Development is at
  <https://github.com/agentskills/agentskills> (GitHub API 2026-11-05: **Apache-2.0**, pushed
  2026-11-04, 26,969 stars).
- **Why agentskills.io and not `anthropics/skills`:** that repo's README says outright — "For
  information about the Agent Skills standard, see agentskills.io" —
  <https://github.com/anthropics/skills>. So: `agentskills.io` owns the *format*;
  `anthropics/skills` is Anthropic's *implementation and examples*.
- **Compatibility with OpenCode:** the spec is client-agnostic and all six RunCell pages name Claude
  Code / Codex / Cursor / Runcell. **OpenCode is not named on any RunCell or agentskills.io page I
  read — unverified.** What is verified is local: OpenCode loads skills from
  `~/.config/opencode/skills/` and the repo's `.opencode/skills/`, both of which are
  plain `SKILL.md` frontmatter files (paths cited in §3).

---

## 3. What is already covered locally

### 3.1 Repo skills — `.opencode/skills/*/SKILL.md`

| Skill file | What it already owns |
| --- | --- |
| `.opencode/skills/tabpfn-explore/SKILL.md` | Schema check, target validation, missingness, task-type decision, stratified pilot subset, import-path check |
| `.opencode/skills/tabpfn-classify/SKILL.md` | Seeded pilot classification baselines; metric table; "one concrete next step" |
| `.opencode/skills/tabpfn-regress/SKILL.md` | Same for continuous targets, incl. target sanity |
| `.opencode/skills/tabpfn-finetune/SKILL.md` | Fine-tuning smoke tests, device readiness, save/load, upstream-path escape hatch |
| `.opencode/skills/tabpfn-benchmark/SKILL.md` | CPU/MPS/CUDA comparison, wall time + memory, "which setup to scale" |
| `.opencode/skills/tabpfn-technical-report/SKILL.md` | Required sections incl. Source Workbooks + Evidence Files; pre-write dedup against the report registry |
| `.opencode/skills/tabpfn-nontechnical-report/SKILL.md` | Same governance for stakeholder prose; plain-English metric glossing |
| `.opencode/skills/insurance-objective/SKILL.md` | The end-to-end objective: baseline vs fine-tuned, classifier + regressor tracks |

### 3.2 Globally installed workflow skills — `~/.config/opencode/skills/`

- `~/.config/opencode/skills/research/` — "Investigate a question against
  high-trust **primary sources** … and capture the findings as a Markdown file in the repo … Follow
  every claim back to the source that owns it."
- `~/.config/opencode/skills/code-review/`,
  `~/.config/opencode/skills/standards/`,
  `~/.config/opencode/skills/tdd/` — code gates.
- `ask-matt`, `to-spec`, `to-tickets`, `triage`, `wayfinder`, `implement`, `implement-spec`, `land`,
  `retro`, `grilling`, `prototype`, `codemap`, `domain-modeling`, `writing-for-agents` — the
  planning/delivery loop.

None of these is a data-science skill; they are delivery and writing skills. That is the point of
the split.

### 3.3 Repo conventions that already do the "skill" job

- `docs/REPORT_REGISTRY.md` — dedup and traceability: topic key → workbooks → evidence, with
  `model_version` + `last_updated` per row; "Before drafting a report, search this registry."
- `../experiments/pilot2-phase2/FINETUNING_LITERATURE.md` — external claims carry a verification status of
  `verified` / `unverified` / `corrected`, plus rule 2: "Do not tidy a claim into something stronger
  than its source says."
- `../experiments/pilot2-phase2/FINETUNING_STATISTICAL_ANALYSIS_PLAN.md` — the analysis is fixed **before** data
  exist, "so that the result cannot be chosen after seeing it"; departures are dated deviations (§10).
- `src/paired_analysis.py` — "Three primitives, and nothing else": paired bootstrap CI,
  inverse-variance summary, Holm adjustment; degenerate resamples "counted, not hidden".
- `scripts/check_doc_status.py` (WINDOW=15, status marker must lead a line) and
  `scripts/check_doc_links.py` — the doc gates.

**Note (stale pointer, not part of the recommendation):** `docs/README.md` "Outside docs/" points at
`.github/skills/`, which does not exist (`ls .github/skills` → No such file or directory,
2026-11-05); the real path is `.opencode/skills/`, as `docs/KNOWLEDGE-PATH-JUNIOR.md` line 50 says.

---

## 4. Gap analysis

| Candidate capability | Covered already? | Evidence |
| --- | --- | --- |
| TabPFN experiment procedure | **Fully** | all eight `.opencode/skills/*/SKILL.md` |
| Report drafting + registry dedup | **Fully** | `tabpfn-*-report/SKILL.md`, `docs/REPORT_REGISTRY.md` |
| Primary-source research with citations | **Largely** | `~/.config/opencode/skills/research/` |
| Literature claims with verification status | **Largely** | `../experiments/pilot2-phase2/FINETUNING_LITERATURE.md` |
| Which statistical test, and does it hold | **Partly — but by design** | The repo governs inference through a pre-registered SAP + three fixed primitives (`src/paired_analysis.py`), *not* through a per-question decision tree. A generic APA t-test tree would answer a question this repo has already answered "paired, bootstrap, Holm". |
| Dataset readiness / first look | **Partly** | `tabpfn-explore` covers schema, target, missingness, task type, pilot subset — but **not** distributions, outliers, correlation redundancy, leakage or time-ordering as a ranked findings list |
| Journal-ready figures | **No** | `docs/figures/` holds 4 PNGs; plotting is ad hoc per script (`scripts/infra/make_learning_path_charts.py` hard-codes `#4C72B0`, `fontsize=8`, `figsize=(8, 6.5)`; `scripts/eval/insurance_benchmark_v1/plot_money_chart.py` likewise). No shared rcParams style file, no export checklist, no caption draft anywhere in `scripts/` or `src/` |
| Spreadsheet intake / reconciliation | **No** | Nothing in `.opencode/skills/` or `scripts/` reads `.xlsx`; `data/README.md` + `data/raw` are the intake. **unverified** whether messy spreadsheets are actually a recurring input here |
| BibTeX / DOI-or-arXiv citation verification | **Partly** | `FINETUNING_LITERATURE.md` enforces *status* labels and holds arXiv IDs in prose; `docs/References/` holds two raw PDFs. No identifier-resolution or `.bib` step exists — **gap** for anything heading to `archive/papers/` |

---

## 5. Recommendation

| # | Candidate | Verdict | One-line reason | Source |
| --- | --- | --- | --- | --- |
| 1 | RunCell **DataViz** | **write our own** | The one unambiguous gap: journal figures. Re-implement the *procedure* (column widths, ≥8 pt embedded, Okabe-Ito, vector+300 dpi, caption draft, export checklist) as a local skill, because the SKILL.md itself has no verified install path and the repo already has hard-won figure conventions to encode. | <https://www.runcell.dev/skills/dataviz> · gap evidence `docs/figures/`, `scripts/infra/make_learning_path_charts.py` |
| 2 | RunCell **Exploratory Data Analysis** | **write our own** | Fills the real gap between `tabpfn-explore` (readiness) and a modelling run (leakage, time-ordering, ranked findings). Adopt the checklist, not the file — and pin its findings to `docs/REPORT_REGISTRY.md` so it cannot become a 40-page auto-report. | <https://www.runcell.dev/skills/exploratory-data-analysis> · `.opencode/skills/tabpfn-explore/SKILL.md` |
| 3 | RunCell **Statistical Test Selection** | **skip** | Duplicates a decision this repo already made in writing: paired comparisons only, three primitives, pre-registered SAP. A generic APA decision tree would invite post-hoc test shopping — the exact thing the SAP exists to prevent. | <https://www.runcell.dev/skills/statistical-test-selection> vs `../experiments/pilot2-phase2/FINETUNING_STATISTICAL_ANALYSIS_PLAN.md`, `src/paired_analysis.py` |
| 4 | RunCell **Deep Research** | **skip** | `~/.config/opencode/skills/research/` already mandates primary sources + per-claim citation into a single Markdown file. Overlap is near-total; adopting both would give two competing research procedures. | <https://www.runcell.dev/skills/deep-research> · same file as cited in §3.2 |
| 5 | RunCell **Academic Research** | **write our own (thin)** | The "no identifier, no citation" rule is the one genuinely new idea for us, and it is one paragraph. Write it into a small repo skill that emits `references.bib` for `archive/papers/` and applies `FINETUNING_LITERATURE.md`'s verified/unverified/corrected status. Rest is covered. | <https://www.runcell.dev/skills/academic-research> · `../experiments/pilot2-phase2/FINETUNING_LITERATURE.md` |
| 6 | RunCell **Excel Data Analysis** | **skip** (revisit if intake changes) | No `.xlsx` intake exists anywhere in `scripts/` or `.opencode/skills/` today. Re-open the question the first time a messy workbook actually arrives. | <https://www.runcell.dev/skills/excel-data-analysis> |
| 7 | `anthropics/skills` | **skip** | 19 skills, all creative/document/enterprise (docx, pdf, pptx, xlsx, frontend-design, mcp-builder, skill-creator …). **Zero** EDA, statistics or figure skills. Also mixed licensing: repo README says many are Apache 2.0, but docx/pdf/pptx/xlsx are source-available under Anthropic's terms — and we do not need document generation. | <https://github.com/anthropics/skills> |
| 8 | `agentskills/agentskills` | **adopt as reference only** | This is the spec we would write against. Apache-2.0, actively maintained (pushed 2026-11-04), and it ships `skills-ref validate` — the cheapest possible check that any skill we write conforms. Not a skill to install. | <https://github.com/agentskills/agentskills> · <https://agentskills.io/specification.md> |
| 9 | `openai/skills` | **skip** | Its own README opens "This repository is **deprecated**. For current Codex skill and plugin examples, use the OpenAI Plugins repository." A deprecated first-party catalog is not an adoption target. | <https://github.com/openai/skills> |
| 10 | `huggingface/skills` | **skip** | Apache-2.0 and actively pushed (2026-10-30), but scoped to Hub operations — `hf-cli`, dataset creation, model training, evaluation. We run TabPFN via `tabpfn-client` and a local upstream tree, not the Hub. | <https://github.com/huggingface/skills> |
| 11 | `microsoft/skills` | **skip** | 174 skills for Azure SDK / AI Foundry development; MIT; actively pushed (2026-11-05). Its own README warns: "Use skills selectively. Loading all skills causes context rot." Wrong domain. | <https://github.com/microsoft/skills> |
| 12 | `probabl-ai/skore-skills` | **skip for now — watch** | The closest structural analogue to our `tabpfn-*` set (BSD-3-Clause, pushed 2026-11-02, claims testing with Claude Code **and OpenCode**). But it is a whole skore/skrub/sklearn pipeline workflow — `explore-ml-data`, `frame-ml-problem`, `evaluate-ml-pipeline`, `audit-ml-pipeline` — which would *compete* with our skills rather than fill a gap. Worth reading for ideas; do not install. | <https://github.com/probabl-ai/skore-skills> |

### Bottom line

Adopt **nothing wholesale**. Three of RunCell's six skills name real gaps (figures, EDA findings,
citation identifiers) and all three are cheaper to write ourselves than to install — because
**no RunCell install path is verifiable** (§1.7), and because each must be bent to this repo's
governance: `docs/REPORT_REGISTRY.md` for dedup, `../experiments/pilot2-phase2/FINETUNING_STATISTICAL_ANALYSIS_PLAN.md`
for inference, `docs/MODEL_VERSIONS.md` for version-pinned claims.

The two things worth taking today, both free: the **agentskills.io spec + `skills-ref validate`**
(#8) as the conformance check for whatever we write, and the **"no identifier, no citation"** rule
(#5) as the seed of a thin literature skill.

---

### Verification log

- RunCell pages read 2026-11-05: `/skills`, `/skills/deep-research`, `/skills/dataviz`,
  `/skills/statistical-test-selection`, `/skills/excel-data-analysis`, `/skills/academic-research`,
  `/skills/exploratory-data-analysis`; plus `/docs` (no skills page) and `/docs/skills` (404).
- Spec read 2026-11-05: `https://agentskills.io/`, `https://agentskills.io/specification.md`,
  `https://agentskills.io/llms.txt`.
- GitHub metadata from `api.github.com/repos/…` on 2026-11-05 (license, `pushed_at`, stars) for:
  `anthropics/skills`, `agentskills/agentskills`, `openai/skills`, `huggingface/skills`,
  `microsoft/skills`, `probabl-ai/skore-skills`. Per-skill licenses verified from raw
  `LICENSE.txt` files in `anthropics/skills`.
- Local files read 2026-11-05: all eight `.opencode/skills/*/SKILL.md`,
  `~/.config/opencode/skills/research/`,
  `~/.config/opencode/skills/code-review/`,
  `~/.config/opencode/skills/standards/`, `docs/README.md`,
  `docs/KNOWLEDGE-PATH-JUNIOR.md`, `docs/REPORT_REGISTRY.md`,
  `../experiments/pilot2-phase2/FINETUNING_LITERATURE.md`, `../experiments/pilot2-phase2/FINETUNING_STATISTICAL_ANALYSIS_PLAN.md`,
  `src/paired_analysis.py`, `scripts/check_doc_status.py`, `scripts/infra/make_learning_path_charts.py`.
- **Unverified, stated as such:** (a) how to obtain RunCell's SKILL.md files; (b) whether RunCell or
  agentskills.io skills load in OpenCode — neither claims it; (c) whether spreadsheet intake is a
  recurring input in this repo.
