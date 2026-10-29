# Plan — suite hygiene and the plan/ADR pointer

**Status:** Current — 2026-10-29.
**Origin:** the `/retro` on the #230 build. Findings 1 and 2.

Two environment defects cost this repo real time during that build, and neither was
tracked by any ticket.

## 1. Tests could reach the real runner

**What happened.** A test called `main()` to prove a CLI guard fires. Before the guard
existed, that test did not fail: it ran a full `coil2000` benchmark — 124 seconds of the
suite — and wrote `results/20261029-000756/` into the tree. It was noticed on `git status`,
not by the suite, which passed.

**Why it matters.** The same mistake on the paid-run path starts fitting models on a rented
box. `tests/conftest.py` did one thing (put `src/` on `sys.path`), so there was no
guardrail at all.

**What changes.** `tests/run_artifact_guard.py` snapshots the default run-output roots
(`results/`, `scripts/eval/insurance_benchmark_v1/predictions/`) and the session fixture in
`tests/conftest.py` fails the run when anything new appears, naming it. Tests in
`tests/test_suite_hygiene.py` pin the guard itself: a new directory fails it, an unchanged
tree passes it, and the roots it watches are the ones a real run writes.

**Limit, stated rather than hidden.** `--out-dir legacy` writes beside the script and is not
watched. The guard covers the default path — the one a mis-fired guard actually takes.

## 2. The documented entry path never reached `docs/plans/`

**What happened.** `AGENTS.md` (global) says to start at `docs/README.md`. The new global
rule says to read `docs/plans/` before building, because a plan outranks a fresh ticket. The
index named neither `docs/plans/` nor `docs/adr/` — zero matches — so the entry path an
agent is told to follow could not reach the material that rule depends on. The plan for
#230 was found only because the branch already carried it.

**What changes.** `docs/README.md` gains a short section naming both folders, with the
trigger written down: read them when the question is "should we build this, and how", not
"what did we measure". `CONTRIBUTING.md` already gained both in its layout during that
build.

## Verification

- `pytest tests/ -q` — green, with the three new tests.
- Deliberately proving the guard: create a directory under `results/`, run any test, and the
  session fails naming it.
- `ruff check scripts/ src/ tests/` — unchanged from `origin/main` (64 pre-existing).
