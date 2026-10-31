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
**four checks, not one** — a change that passes pytest can still fail the others:

- `ruff check scripts/ src/ tests/`
- `pytest tests/ -q`
- `shellcheck --severity=warning scripts/gpu_helpers/*.sh`
- `./scripts/check.sh evidence` — `outputs/` and `results/` unchanged, or the PR labelled
  `evidence-change`

Run all four with `./scripts/check.sh`, or one with
`./scripts/check.sh ruff|pytest|shellcheck|evidence`. The script is the single definition;
`.github/workflows/ci.yml` calls it for each separate job. A missing tool exits non-zero
rather than skipping a check.

**What the gate does not cover yet:** the doc link and doc-status checks. They are red on
`main` against a pre-existing backlog and are not in `ci.yml`, so a green gate says
nothing about them. Adding them is its own work against that backlog.

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

## Issue tracker

Config: docs/issue-tracker.md
