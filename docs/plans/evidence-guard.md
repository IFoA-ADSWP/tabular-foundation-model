# Plan — guard the evidence trees (#317 retro)

**Status:** Current — implementing 2026-10-31.
**Origin:** the 2026-10-30 retrospective. The triggering error is on record: a commit deleted
seven tracked logs under `outputs/gpu-pilot/logs/` while its own plan asserted the diff was empty.

## Why a check and not a rule

`AGENTS.md` already said "do not delete them casually". It did not stop the deletion, and it could
not: the command that did it (`rm -f outputs/gpu-pilot/logs/*.log`) treats a directory holding
committed evidence and untracked test scratch as one thing. A rule no one reads at the moment of
the command is not a guardrail.

## What lands

1. **`./scripts/check.sh evidence`** — fails when `outputs/` or `results/` differ from the base
   commit, or when a *staged or unstaged* tracked change sits in either tree. Untracked files are
   excluded deliberately: mock runs write scratch there on every test run.
2. **An escape hatch with a name.** `EVIDENCE_CHANGE_OK=1` locally; the `evidence-change` label in
   CI. A deliberate evidence change is a decision, and the label is where the decision is recorded.
3. **A CI job**, so a pull request cannot land evidence drift unlabelled. Its base is the PR's base
   commit, and on a push the previous commit — not `origin/main`, which is the branch itself on
   `main` and would make the check vacuous.
4. **A coding standard for cost claims**, from the same retro: two signed documents said "models
   are already committed" and "analysis only, $0", and both were false. No guardrail can check a
   claim about the world; a reviewer can ask for the file.
5. **Three `AGENTS.md` traps**, including the one that closed #304 by writing "does not close #304".

## Failure modes considered

- **A base that does not exist** (fresh clone, shallow CI): reported as a failed check, not as a
  missing tool. `3` means "install something"; this is "fetch something".
- **Self-certification**: the CI job runs the branch's own `check.sh`. Acceptable here — the
  alternative is a second copy of the comparison in the workflow, which is the drift the shared
  script exists to prevent.
- **Noise from mock runs**: excluded, and #282 already keeps their logs out of the tree.

## Verification

- Both paths exercised against real history: `d5aebe7^` lists the arm artifacts and exits 1;
  with the override it lists them and exits 0.
- New tests in `tests/test_check_script.py` cover clean, committed drift, staged drift, the
  override, and a missing base.
