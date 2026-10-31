# tabular-foundation-model — Agent Instructions

## Canonical test command

pytest tests/ -q

Run it and iterate until it passes before reporting work as done. A failing gate
means the task is not finished — do not claim completion on an unverified change.

## Plans

Write docs/plans/<task>.md before non-trivial work: what you intend to change and
why. Commit it with the change.

## Conventions

Python research repo (TabPFN vs actuarial baselines). The gate is CI, and CI is
**six checks, not one** — a change that passes pytest can still fail the others:

- `ruff check scripts/ src/ tests/`
- `pytest tests/ -q`
- `shellcheck --severity=warning scripts/gpu_helpers/*.sh`
- `./scripts/check.sh evidence` — `outputs/` and `results/` unchanged, or the PR labelled
  `evidence-change`
- `./scripts/check.sh doclinks` — every reference in `docs/` resolves (plans and archives
  are citations, and the git-ignored run trees describe a shape)
- `./scripts/check.sh docstatus` — every report in the three tiers states whether it is
  current, historical or proposed

Run all six with `./scripts/check.sh`, or one with
`./scripts/check.sh ruff|pytest|shellcheck|evidence|doclinks|docstatus`. The script is the single definition;
`.github/workflows/ci.yml` calls it for each separate job. A missing tool exits non-zero
rather than skipping a check.

`scripts/gpu_helpers/*.sh` is the **paid-run path** — it runs on rented boxes, mid-run, at
cost. A syntax error there is expensive and happens away from your terminal. Run shellcheck
before touching it.

**Version pinning is load-bearing.** Legacy reports were produced against TabPFN v2 era;
current verdicts are pinned to `v3_default` (tabpfn-client 0.3.3). `docs/MODEL_VERSIONS.md`
records the timeline and what flipped. Never mix version eras in a claim — a number is only
meaningful against the version it was measured with.

`requirements.lock` exists alongside `requirements.txt`; use the lock.

Doc-heavy repo: `TASKS.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `docs/` with a roadmap and a
dashboard. Treat those as tracked artifacts — if a change makes one stale, update it.

**Data hygiene.** `data/`, `outputs/`, `catboost_info/`, `legacy/` and `notebooks/` hold
experiment outputs. Do not treat them as source; do not regenerate or delete them casually.

**Tests can reach the real runner.** Some tests call `main()` to prove a guard fires. When
one stops firing, the test does not fail: it fits a dataset for minutes and writes
`results/<timestamp>/`. `tests/conftest.py` now fails the session when run artifacts appear,
so trust it before `git status`.

**A PR body closes issues by substring.** "Does not close #304" closed #304: any
`close`/`closes`/`closed` keyword anywhere in the body, negation included, closes on merge. Write
`Refs #N` unless you mean it.

**Plans are claims.** If a plan names a verification command or an "empty diff", run it in the
same commit that carries the plan.

## Review

Every change is reviewed before merge, in a fresh context, against the plan and the
judgement calls in `CODING_STANDARDS.md`.

## Branch protection — admin, once

Two settings on `main`. A pull request cannot apply or verify either, so they stay a setup
step:

1. **Require status checks to pass before merging**, selecting the six jobs `ci.yml`
   schedules — ruff, pytest, shellcheck, evidence, doclinks, docstatus. A red run then keeps
   the merge button disabled.
2. **Require branches to be up to date before merging.** Without it a stale pull request
   reads `MERGEABLE/CLEAN` and the merge fails on conflicts instead; measured 2026-10-31 on
   #347, where `main` had advanced three commits and the squash-merge was refused. With it,
   the pull request shows `BEHIND` and waits for a refresh instead of failing late.

## Issue tracker

Config: docs/issue-tracker.md
