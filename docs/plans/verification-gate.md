# Plan — verification gate, slice 1: the local command

**Status:** Current — issue #257 (spec #252).
**Scope:** the shared entry point only. Not CI, not the lint debt, not the docs.

## Why

`AGENTS.md` told every agent the gate is CI and named four checks at the time. On `main` there
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


## Slice 3 — CI invokes the gate and lands (#259)

The workflow is extracted from the pull request that has been carrying it since October,
and rewired so that each job runs `./scripts/check.sh <check>` rather than restating the
command. Jobs stay separate so a failure names which check broke and each keeps its own
timeout. Triggers and concurrency are kept as they were: pull requests, pushes to `main`,
manual dispatch, and cancelled superseded runs.

Three jobs, not four: ruff, pytest, shellcheck. The doc checks stay out until their own
backlog is addressed, and #260 corrects the instructions to say three.

**The proof is a red run, not a green one.** A branch is pushed with a deliberately planted
lint error and a deliberate shellcheck violation; the recorded outcome of that run is the
evidence that the gate is wired, not merely configured.

### Evidence: the runs

- **Green**, on #274: run `40798566228` — `ruff`, `pytest` and `shellcheck` all succeed.
- **Red**, on a throwaway branch (#276): run `40799041147` — the run **fails** with
  `ruff: failure` on `F401 os imported but unused` in the planted file, while `pytest` and
  `shellcheck` pass. The gate does what it claims: a bad pull request cannot go green.

That first red run also taught something worth keeping. The planted shellcheck violation
was `SC2086` (unquote this to prevent word splitting), which is **info** severity, and the
gate runs at `--severity=warning` — so the floor filtered it exactly as its comment says it
would. A floor that filters what it says it filters is working. The branch was re-planted
with a warning-level violation to prove the shellcheck half by a failure rather than by its
absence.

- **Red, both checks**, run `40799854243`: `ruff: failure` and `shellcheck: failure`, with
  `pytest: success`. The gate reports each check separately, and a bad pull request fails
  on more than one axis exactly as it should.



### Five gaps CI found that local runs could not

The first CI run failed, and every failure was a real defect rather than a wiring mistake.
This is the argument for landing the gate made in its own evidence.

1. **Ruff's default rule set is version-dependent.** 0.15.8 flagged 64 findings in this
   tree; 0.17.3, which `pip install ruff` resolved on the runner, flagged **255**. A gate
   that changes verdict when a tool upgrades is exactly the drift a single entry point is
   supposed to prevent. Fixed both ways: `select` pins the rule families explicitly in
   `ruff.toml`, and the workflow pins the version, so widening either is a deliberate
   change rather than something CI resolves.
2. **`test_pilot2_mock_run` was not hermetic.** It deliberately did not export a token and
   relied on the developer's `~/.config/tfm/keys.env`, so it passed on a workstation and
   aborted on a runner with `No TABPFN_TOKEN`. Fixed by writing a dummy token file into the
   test's tmp dir and pointing the launcher at it — the file path is still what is
   exercised, without the machine dependency.
3. **The licence preflight made a live API call.** The launcher verifies licence acceptance
   before renting, which is right for a rental and meaningless for a mock that provisions
   nothing. The test now sets the launcher's existing `SKIP_LICENSE_CHECK` escape hatch.
4. **The checkout was shallow.** After #271 landed, the mock-run fixture asks whether an
   injected commit is an ancestor of `origin/main`. `actions/checkout@v4` fetches one commit
   and creates no remote-tracking branch, so the ref a developer always has did not exist on
   the runner. The pytest job now fetches full history (`fetch-depth: 0`); the fix belongs in
   the workflow because it is the test's question, not the code under test, that needs it.
5. **The runner had no git identity.** The refusal test builds a real commit with
   `git commit-tree`, so the commit it rejects is genuinely absent from the remote rather
   than a fake sha. `commit-tree` refuses without `user.name`/`user.email`, which every
   development machine has and a fresh runner does not. The test now passes an explicit
   identity instead of depending on the machine's git config.

None of the first three could fail locally, because the machine had a token, a licence and
an older ruff. The last two need git state a developer has and a fresh runner does not.
Landing CI is what surfaced them.


## Follow-up — `all` and a missing tool (#257 review)

Review found that `need()` exits 3 from inside a function, so `all` stopped at the first
absent binary: a missing `ruff` hid `pytest` and `shellcheck` behind it. That is the inverse
of the slice-1 decision that one red check must not hide another.

`all` now runs each check in a subshell, records exit 3 as "missing", and continues. A real
failure outranks a missing tool (exit 1 before exit 3). Two tests pin it: every check still
runs when `ruff` is absent, and a failing `pytest` still reports failure when another tool
is missing. Their PATH contains only `bash`, `basename` and `git`, so "absent" is true even
on a machine with `ruff` installed — the old test skipped instead of asserting that case.


## Not in this slice

The corrected instructions (#260) and retiring the duplicate workflow still living on the
old pull request (#261).

**Update 2026-10-30:** #260 corrected `AGENTS.md` and `CONTRIBUTING.md` to name the then
three checks and `./scripts/check.sh`, and to state that the doc checks are not in the gate
yet. **Update 2026-10-31:** #319 added the `evidence` job, so the gate is now four checks;
the instructions and this count were reconciled.


## Follow-up — suppression reasons and the excluded lambdas (#258 review)

Review found the criterion "every remaining per-line suppression states its reason" unmet:
19 `# noqa` comments named a code but not why. Each now carries a short reason — the path
insert above for E402, a NaN-safe explicit compare for E712, and "the smoke test reports any
import failure" for BLE001. No suppression was added or removed.

The seven assigned lambdas (E731) are all inside `scripts/legacy_finetuning/`, which this
change deliberately excludes; there is no E731 in live code. The exclusion's comment says to
re-include the tree when it is next touched for real, so the lambdas are left untouched and
travel with that decision rather than being "fixed" in code nobody runs. Re-including the
tree will surface them along with the other 19 findings there, and that is when to fix them.
