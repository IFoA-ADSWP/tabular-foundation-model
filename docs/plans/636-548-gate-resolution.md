# Plan — the gate resolves its own tools and tolerates a stale branch

**Status:** Current — implemented with this change, 2026-11-23.
**Origin:** #636 (tools resolved from `PATH`) and #548 (hook unusable on a stale branch), both hit while landing docs changes the same day.

## What was wrong

Two defects on the same seam — the local gate misreporting an environment problem as a problem with the change:

1. **`scripts/check.sh` resolved every tool from `PATH`.** AGENTS.md names `.venv/bin/pytest` as the canonical test command, so the repo has one environment and the gate ignored it. Measured today: an `AGENTS.md`-only commit was refused until `.venv/bin` was put on `PATH` by hand, and a subagent hit the same wall on a Markdown-only change.
2. **The pre-commit hook ran the *branch's own* `check.sh`.** A branch cut before `citation` existed has no such argument, so `check.sh` printed its usage line and exited 2 — and the hook reported `citation FAILED` on work that never touched citations. Rebasing two docs branches today needed `core.hooksPath=/dev/null` for exactly this.

## The fixes

**Tool resolution.** After `cd "$root"`, prepend `$root/.venv/bin` to `PATH` when that environment exists. One block, applied to every tool the gate needs (`ruff`, `pytest`, `python3`), not just the one that was reported.

**Stale branch.** The hook now reads `check.sh`'s **documented exit codes** instead of only its truthiness: `0` passes, `2` (usage) means *this branch's check.sh does not know that check* and is skipped with a message naming the ticket, anything else fails. No new subcommand, no probing, and it uses a contract the script already publishes.

This is better than the alternatives: a `--list` subcommand would itself be absent on the very branches that need the guard, and running `origin/main`'s script would gate a commit with checks the branch cannot satisfy.

## Verification

- `env PATH=/usr/bin:/bin ./scripts/check.sh ruff` → **All checks passed** (was: `required tool 'ruff' is not installed`).
- `bash -n` clean on both scripts; `shellcheck --severity=warning` clean on both.
- A stale branch's `citation` invocation exits 2 and is now skipped rather than fatal.

## Out of scope

Making `pytest` fast enough for the hook. The hook's comment records why it is excluded, and that reasoning has not changed.
