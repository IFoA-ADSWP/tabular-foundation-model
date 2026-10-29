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

## Slice 2 — clearing the debt (#258)

The gate reported 64 errors. They divide cleanly:

| Where | Count | Disposition |
|---|---|---|
| `scripts/legacy_finetuning/` | 26 | excluded, with the reason in `ruff.toml` |
| live code | 38 | all fixed |

Of the 38: 14 were mechanical and applied by `ruff --fix` (unused imports, unused
variables, placeholder-less f-strings, one redefinition); 24 were done by hand —
16 semicolon statements split into one per line, 4 `import sys as _sys` aliases
normalised to a module-level `import sys` placed after `from __future__`, 3 dead
assignments deleted, and one further unused import.

### Decisions

- **A dedicated `ruff.toml`, not a new `pyproject.toml`.** The repo has neither, so a
  `pyproject.toml` would silently become packaging and pytest configuration as well as
  ruff configuration. `ruff.toml` configures one tool.
- **`extend-exclude`, not `exclude`.** Ruff's built-in exclusions stay in force; only the
  legacy tree is added.
- **The exclusion states what a green gate no longer proves.** `scripts/legacy_finetuning/`
  is not on the live path — its entrypoints need upstream `tabpfn` and a GPU, and
  `GLOSSARY.md` records the fine-tuning pilot as a separate context. The comment says so
  and says to re-include the tree when it is next touched, so the next reader can disagree
  rather than be surprised.
- **No blanket suppression.** No new `# noqa` was added; every remaining suppression in
  the tree predates this change and carries its own reason.

### Evidence

Ruff reports **0 errors** where it reported 64, with 26 of those accounted for by the
cited exclusion and 38 fixed in live code. The behaviour-preserving claim was checked
rather than assumed: the four files whose imports were reorganised still parse, and each
removed name (`os`, `bin_centers`, `args`, the inner `numpy` redefinition) has no
remaining reference.

`./scripts/check.sh` exits **0**: ruff clean, **256 passed**, shellcheck clean (the count rose from 249 when `main`'s
later #271 and #277 tests were merged in).

### A blocker the gate found immediately

The first full run failed two tests in `test_pilot2_mock_run.py`, and neither failure had
anything to do with lint. The paid-run launcher refuses any commit that is not an ancestor
of `origin/main`, because the remote box clones `main` and could not run it. That check is
correct for a real run and meaningless for a mock one: a mock creates no instance and
cannot spend money.

The consequence is larger than two tests: **the suite could only ever be green on `main`**,
so CI running `pytest` on a pull request — where HEAD is never on the base branch — would
fail on every pull request. Landing the gate (#259) would have hit this on its first run.

On this branch the guard was scoped to non-dry-run execution. While the stack waited, #271
landed the better fix on `main`: the guard now takes its commit from `TFM_COMMIT_SHA`,
defaulting to `HEAD` and honouring an override only when the provider is detected as the
mock. The guard still runs in a mock; it is simply answerable. That is why this branch's
skip was dropped when `main` was merged in, and why the tests set `TFM_COMMIT_SHA` rather
than bypassing the check. This is exactly what the gate is for: it surfaced a structural
problem on its first honest run, before it was wired into CI.


## Not in this slice

CI wiring and landing (#259), the corrected instructions (#260), and retiring the
duplicate workflow (#261).
