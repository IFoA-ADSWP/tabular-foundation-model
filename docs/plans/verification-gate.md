# Plan — verification gate, slice 1: the local command

**Status:** Current — issue #257 (spec #252).
**Scope:** the shared entry point only. Not CI, not the lint debt, not the docs.

## Why

`AGENTS.md` tells every agent the gate is CI and names four checks. On `main` there
is no workflow at all: the only copy sits on an unmerged branch inside a conflicting
pull request, and 64 ruff errors have accumulated because no event reports them.

This slice builds the thing both CI and a human will call: `scripts/check.sh`, with one
subcommand per check and an all-in-one default. It is deliberately landed before CI so
that the gate's first act is to **report** the debt rather than hide it — and so that
the workflow (next slice) has something to invoke instead of restating commands.

## What changes

- `scripts/check.sh` — subcommands `ruff`, `pytest`, `shellcheck`, plus `all`.
  Exit codes: `0` passed, `1` a check failed, `2` usage, `3` a tool is missing.
- `tests/test_check_script.py` — the contract: a failing tool fails the check, a missing
  tool is named and never a silent pass, an unknown name is a usage error, `all` runs
  every check and any failure decides the result.

## Decisions

- **Shell, not Python.** `shellcheck` is one of the checks, so the wrapper is bash. It
  runs on macOS with no Linux-only tooling, which is where contributors actually work.
- **A missing tool exits 3 with the tool named.** Skipping a check because a binary is
  absent is the "gate that verifies nothing" failure in a different costume.
- **The shellcheck severity floor is carried over with its reason.** Four pre-existing
  SC2012/SC2016 findings in the GPU helpers are intentional; at default severity they
  fail every run on style, which is how a lint gate gets disabled.
- **`all` does not stop at the first failure.** One red check must not hide another;
  the overall status is the worst result.

## Evidence this slice works

- `./scripts/check.sh` on this tree exits `1` and reports the pre-existing ruff errors
  (and passes pytest and shellcheck). That red output is the proof the gate is real, and
  it is what #258 clears.
- `pytest tests/test_check_script.py -q` passes, including the planted-failure cases.

## Not in this slice

CI wiring and landing (#259), the lint debt and the legacy exclusion (#258), the
corrected instructions (#260), and retiring the duplicate workflow (#261).
