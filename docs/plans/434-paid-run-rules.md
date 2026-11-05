# Plan — the rules for running many paid launches (#434)

**Status:** Current — 2026-11-05.
**Origin:** #434, with the two rules carried from #443's retro. Parent: #428.

## What this changes

One new section in `docs/current/FINETUNING_EXECUTION_RUNBOOK.md`, "Running many
launches", carrying twelve numbered rules. Each rule states the practice, the cost that
bought it, and — where one exists — the mechanism or ticket that enforces it. Nothing
executable changes.

The runbook is the "next-run appendix": it already holds the commands and the acceptance
procedure for a single run. This section is the sibling of watching one launch: what to
do when the unit of work is a batch and the queue outlives several launches.

## Placement and shape

After "Watching a launch, and not leaking one" and before "Evidence obligations, unchanged",
because the rules govern the launch path that produces those obligations, not the
obligations themselves. The section opens by pointing at the single-launch section above
instead of restating it, and refers to `batch_run.sh` (#430) and `watch_run.sh --plan`
(#432) by name instead of restating their behaviour — neither exists yet, so the text names
the ticket that builds each. Rules 1 and 2 point back at the measured sizing paragraphs
already in the runbook rather than repeating their figures a second time; what the new text
adds is that both inputs must come from a run that completed.

## Content, and where each rule's evidence comes from

| Rule | Evidence |
| --- | --- |
| 1. Measure per-seed time and boot before sizing | `vast_run.sh` defaults (170 s, 900 s), the 46 min run against a 40 min ceiling, #414 |
| 2. Pin a GPU class whose timing was measured | 753–837 s vs 158 s on the 30-epoch fit |
| 3. The missing set is the queue | #430; a fixed queue skipped a dead range |
| 4. Concurrency only after the smoke test | #426, `/tmp/vast_run_out.txt`, #431 |
| 5. Never edit a running script | `line 863: $'in. >&2…': command not found` in a live launcher |
| 6. Range lists go in a file | zsh does not split `$RANGES`; `FATAL: --seeds was given an empty value` |
| 7. Trust `meta.json`, not log lines | #429, #432; `for f in */meta.json` matched nothing |
| 8. `--yes` does not skip the leak preflight | #423; the prompt is unconditional in `vast_run.sh` |
| 9. Reproduce under the mock before blaming the provider | #426; four hours of misdiagnosis |
| 10. Append CHANGELOG entries at the bottom | five same-anchor conflicts in one session |
| 11. Evidence committed before a result ships | #436; 476 arrays absent in a fresh clone |
| 12. A healthy-looking failure stops the set | #426's `verified=24` from another launch's seeds |

## The one mechanical follow-on, scoped not built

Rule 11 names an extension this change does **not** make: `scripts/check_citations.py`
verifies that a cited run has a `capture.json` whose entries carry non-null hashes, but it
does not resolve the arrays those hashes describe. The rule is written with its scope
attached — hash each arm × seed array named by the capture, fail on a missing file or a
mismatch — so the follow-on ticket inherits a specification rather than a sentence. Rule
12's enforcement is #429–#433 and is attributed to them.

## Verification

- `python3 scripts/check_doc_links.py --dir docs/current --root .` adds no broken reference
- `python3 scripts/check_doc_status.py --dir docs/current` still passes the runbook
- `pytest tests/ -q` once at the end (docs-only change, but the gate is the gate)
