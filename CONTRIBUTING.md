# Contributing

This is a research project comparing TabPFN against traditional actuarial models for insurance tasks. All contributions welcome.

## Branching & Merging Policy

`main` is protected: **force-pushes and deletions are blocked**, and **all changes land via pull request** — but with **zero required approvals**. A PR here is a ritual, not a gate: it gives every change a revertable unit, a visible diff, and a discussion thread without ever blocking solo work.

- Open a PR from your branch and **merge it yourself** when green.
- Admins retain direct-push rights strictly for emergencies.

### Branch naming

| Prefix | Use | Merged? |
|---|---|---|
| `feat/…` | New capability or analysis pipeline | yes |
| `docs/…` | Reports, specs, README changes | yes |
| `fix/…` | Bug fixes | yes |
| `chore/…` | Tooling, deps, repo hygiene | yes |
| `exp/<issue#>-<slug>` | Experiments | optional — may live long and never merge |

Put the issue number in the branch name (`exp/126-null-control`) so GitHub auto-links your PR to its board card; flip the card to **In review** when the PR opens.

### Merge style

Merge commits are allowed (we preserve commit SHAs as evidence anchors), squash is fine for small fixes. Head branches delete automatically on merge.

## Setup

```bash
# 1. Clone
git clone https://github.com/IFoA-ADSWP/tabular-foundation-model.git
cd tabular-foundation-model

# 2. Build the environment the tests are pinned to (Python 3.12)
./scripts/bootstrap_dev.sh

# 3. Run the gate
.venv/bin/pytest tests/ -q
```

`bootstrap_dev.sh` installs `requirements.lock` and asserts the pins; `README.md` also documents a
`uv` path. Creating a venv by hand and installing `requirements.txt` works for most scripts but can
resolve a different scientific stack, which changes test results — see
`docs/DEVELOPMENT_ENVIRONMENT.md`.

## Repository Layout

```
src/                    # Shared Python modules (data loading, metrics, baseline models)
notebooks/
  adswp_project/        # Domain-specific TabPFN applications (real insurance data)
  baseline_experiments/ # Head-to-head model comparisons (benchmarks)
data/raw/               # Datasets (eudirectlapse.csv, freMTPL2freq.csv, ...)
  processed/            # Intermediate benchmark results (CSV)
outputs/
  current/              # Latest figures, tables, logs (git-tracked)
  replication/          # Paper replication snapshots (git-tracked)
  archive/              # Historical experiment outputs (gitignored)
scripts/                # One-off experiment scripts (not notebooks)
docs/
  reports/              # Analysis reports (must register in REPORT_REGISTRY.md)
  analyses/             # Methodology notes (lighter than reports)
  papers/               # Paper content and LaTeX style files
  status/               # Project status and security record
  plans/                # One plan per task, written before non-trivial work
  adr/                  # Architecture decision records (accepted decisions)
tests/                  # Smoke tests and test-support helpers
```

## Running Notebooks

Notebooks are numbered in execution order within each directory:

```bash
# ADSWP project notebooks
jupyter notebook notebooks/adswp_project/01_TabPFN_classifier_eudirectlapse.ipynb

# Baseline experiments
jupyter notebook notebooks/baseline_experiments/01_claims_classification_baseline.ipynb
```

The main replication notebook is `notebooks/adswp_project/REPLICATION_There_Is_Life_in_the_Old_GLM_Yet.ipynb`.

## Contribution Map — Where Things Go

| If you want to... | Put it in... | Convention |
|---|---|---|
| Run a new experiment on real insurance data | `notebooks/adswp_project/NN_descriptive_name.ipynb` | Two-digit number, snake_case name |
| Run a head-to-head model comparison | `notebooks/baseline_experiments/NN_descriptive_name.ipynb` | Same |
| Write a reusable utility | `src/` as a Python module | Importable function/class, notebook-inline code does not belong here |
| Run a one-off analysis (not a notebook) | `scripts/descriptive_name.py` | snake_case, `if __name__ == "__main__":` guard |
| Write an analysis report | `docs/reports/DESCRIPTIVE_NAME.md` | ALL_CAPS snake_case, register in `docs/REPORT_REGISTRY.md` |
| Write a lightweight methodology note | `docs/analyses/descriptive_name.md` | snake_case, no registry entry needed |
| Update the paper | `docs/papers/` | Markdown or `.sty` as appropriate |
| Save output figures | `outputs/current/figures/` | Descriptive PNG name |
| Save output tables | `outputs/current/tables/` | Descriptive CSV name |
| Save run logs | `outputs/current/logs/` | Descriptive markdown name |
| Archive old outputs | `outputs/archive/` | Gitignored — not committed |
| Add a test | `tests/test_descriptive_name.py` | One test file per `src/` module |

## Standards Checklist

Every contribution should satisfy these before review:

- [ ] **Naming** — notebooks are two-digit numbered + snake_case; reports are ALL_CAPS snake_case; scripts and modules are snake_case
- [ ] **No code duplication** — import from `src/` rather than copying utility code into notebooks
- [ ] **Idempotent notebooks** — runs top-to-bottom without pre-existing state; outputs are regenerated, not committed (unless a deliberate reproducibility snapshot)
- [ ] **Reports registered** — any new file in `docs/reports/` must have a row in `docs/REPORT_REGISTRY.md` with topic_key, audience, source_workbooks, and evidence_files
- [ ] **Changelog updated** — user-facing changes get an entry in `CHANGELOG.md` under `[Unreleased]`
- [ ] **Pre-commit green** — see below
- [ ] **Gate green** — `./scripts/check.sh` (ruff, pytest, shellcheck, evidence, doclinks, docstatus, citation, verdict)
- [ ] **Smoke test passes** — `pytest tests/` after any change to `src/`
- [ ] **PR focused** — one experiment or fix per pull request

## Pre-commit Setup

**Option A — the pre-commit framework.** Install once after cloning:

```bash
pip install pre-commit
pre-commit install
```

This runs ruff (format + lint), commitizen (commit message convention), and other checks
automatically on every commit. Run against all files manually when first setting up:

```bash
pre-commit run --all-files
```

**Option B — the repo hook, when `core.hooksPath` is set.** A machine with a global
`core.hooksPath` (this one has `~/.config/git/hooks`) makes `pre-commit install` fight the
global configuration, so nothing gets installed and the config above silently never runs.
That is not hypothetical: on 2026-11-06 two pull requests failed in CI for faults — 146 files
staged from `outputs/`, and a run id cited with no capture — that a local gate would have
refused in about two seconds.

For that setup, install the repo's own hook, which the global hook chains to:

```bash
cp scripts/git-hooks/pre-commit.local "$(git rev-parse --git-common-dir)/hooks/pre-commit.local"
chmod +x "$(git rev-parse --git-common-dir)/hooks/pre-commit.local"
```

It runs `ruff`, `evidence` and `citation` only — the checks that can fail from a commit. It
deliberately does not run `pytest`: 667 tests take about 28 minutes locally (measured 2026-11-06),
so a local full run is not a gate. CI runs everything.

That exclusion was once justified here by "four of its tests abort sandboxed shells on macOS". It
was wrong, and the correction belongs where the claim lived: those four `test_pilot2_seed_passthrough`
tests are correct. The abort came from a machine-local `python3` wrapper that re-injected a
`$HOME`-relative `DYLD_INSERT_LIBRARIES` on every call — and the tests sandbox `HOME`, so dyld chased
a dylib that did not exist there. Run the same four with that wrapper off `PATH` and they pass. A
`Darwin skip` would have hidden four real tests on every Mac while CI stayed green, so: if a test
fails on your machine, check the machine before you skip the test.

`$(git rev-parse --git-common-dir)` and not `.git/hooks`, because in a worktree `.git` is a
file and that path never exists.

**Escapes.** `EVIDENCE_CHANGE_OK=1 git commit …` for a deliberate evidence change (runtime
artefacts under `outputs/` are exactly that). `git commit --no-verify` for anything else — and
say why in the message.

To run ruff directly:

```bash
ruff check src/ tests/
ruff format src/ tests/
```

## The gate

CI and a local run share one definition. `./scripts/check.sh` runs eight checks — ruff,
the test suite, shellcheck over the paid-run scripts, the evidence guard (`outputs/`
and `results/` unchanged, or the PR labelled `evidence-change`), the doc-link check
(every reference in `docs/` resolves), the doc-status check (every report says
whether it is current), and the citation check (every run id cited in `docs/` has a
capture) — and `./scripts/check.sh ruff` (or `pytest`,
`shellcheck`, `evidence`, `doclinks`, `docstatus`, `citation`, `verdict`) runs one. `.github/workflows/ci.yml` calls the same
script as six separate jobs on every pull request, every push to `main`, and on demand. A missing tool exits non-zero; it is never a
silent skip.

## Report Registration

If you add a file to `docs/reports/`, open `docs/REPORT_REGISTRY.md` and add a row with:

- `report_path` — relative path to your file
- `topic_key` — short kebab-case identifier (check for duplicates first)
- `audience` — `technical` or `non-technical`
- `status` — `active`, `draft`, or `archived`
- `source_workbooks` — semicolon-separated paths to source notebooks
- `evidence_files` — semicolon-separated paths to tables/figures/logs
- `last_updated` — ISO date

## Pull Requests

- Use the PR template
- Keep changes focused (one experiment or fix per PR)
- Update `CHANGELOG.md` for user-facing changes
- A pull request runs the four gate checks via `.github/workflows/ci.yml`; run `./scripts/check.sh` before you push
