# Plan — a reproducible local environment and a worktree that works

**Issue:** #530 (retro on #516 / #526).
**Status:** Proposed.

## What and why

Three failures in the last session had one cause: the environment was not written down anywhere
durable.

- `pytest` was not on `PATH` in the session's clone, and there was no `.venv`, so the canonical
  command in `AGENTS.md` could not run.
- The only working interpreter was a throwaway in the OS temp directory, outside the lock, and it
  produced eight test failures that were the environment (pandas 3.1, numpy 2.5, no matplotlib).
  Proving they were pre-existing took a `git archive origin/main` and a second run.
- A harness-created worktree arrived from a different clone at an unrelated commit, with no
  `tests/conftest.py`. `pytest` failed with `ModuleNotFoundError`, which reads as a missing module.

Each cost a diagnosis that a checked-in command removes.

## Shape

- `scripts/bootstrap_dev.sh` — build `.venv` from `requirements.lock` on Python 3.12, install
  pytest, assert the pinned versions import. Idempotent; `--recreate` for a clean build.
- `scripts/new_worktree.sh <branch> [base]` — `git worktree add ... -b <branch> origin/<base>`,
  then refuse to print a path whose `tests/conftest.py` or `AGENTS.md` is absent.
- `docs/DEVELOPMENT_ENVIRONMENT.md` — the durable facts: which checkouts exist, how to build, how
  to run the gate, targeted suites, the full suite's duration, the pins, and the four failures that
  look like bugs but are not.
- `AGENTS.md` — the canonical command names the bootstrap; a short worktree section; one pointer to
  the new page.
- The pre-registration's cost paragraph points at `FINETUNING_COST_AND_CONTROLS.md`, which owns the
  rate; the spec owns the ceiling.
- The PR template asks whether a fresh-context review ran, so the rule leaves a trace.

## Judgement calls

1. **The lock, not the ranges.** `requirements.txt` says `pandas>=2,<3`; a fresh resolve can leave
   that range, and did. The lock is the only thing that makes "the gate" mean the same locally as
   in CI.
2. **The worktree script checks for `conftest.py`.** The failure it prevents is invisible: an
   incomplete tree presents as a missing module, not as the wrong tree. The check is one line and
   converts a diagnosis into a refusal.
3. **The environment page records the clone ambiguity and does not resolve it.** Three checkouts
   were observed at three different commits. Naming one canonical is the owner's decision — only
   they know which are disposable — so the page teaches the check (`git rev-parse --show-toplevel`)
   instead of asserting an answer that may be wrong.
4. **`AGENTS.md` gets a command and a pointer, not the facts.** The facts cost context on every
   turn and change more often than the pointer does; the page is loaded when the branch fires.

## Verification

- `./scripts/bootstrap_dev.sh` run end to end: Python 3.12.2, `tabpfn 8.5.0`, numpy 1.26.4,
  pandas 2.3.3, scipy 1.17.1, sklearn 1.6.1 — the lock's versions.
- `.venv/bin/pytest tests/ -q` in the new environment — the full gate, not a targeted suite, because
  the point of the change is that the full gate becomes runnable.
- `shellcheck --severity=warning scripts/bootstrap_dev.sh scripts/new_worktree.sh` — clean.
- `./scripts/new_worktree.sh chore/530-script-smoke` created a complete tree at `origin/main`
  (conftest and `AGENTS.md` present); the worktree and branch were removed afterwards.
- `./scripts/check.sh` — the eight checks.
