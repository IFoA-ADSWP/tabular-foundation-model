# Plan — the severity estimand decision (#729)

**Status:** current — decisions recorded and the amendments applied, 2026-11-22.

The epoch ladder (#672) is complete and its result note is current. Its two severity verdicts sit on
different units, and the fair test still quotes a pooled severity figure. This ticket settles what a
severity verdict is a verdict about, and records the two ladder-rule decisions taken in the same pass
(#711, #712).

## Decisions

- **#729: A + C.** Drop the task-level severity claim; report each target on its own registered
  estimand; name the unit and weighting in every severity verdict. Option B (a like-for-like pair)
  is not taken and would be its own priced protocol.
- **#711:** CONFIRMED stands under the frozen rule. The shape is recorded as non-monotone; the next
  ladder freezes a monotonicity clause and its consequence before its run.
- **#712:** take both — a per-metric pre-run seed/MDE check and a required post-run
  `registered MDE vs observed half-width` field.

## What changes

- `docs/experiments/fair-test-freq-sev/freq_sev_fair_test_result.md` — headline answer, the task-row
  note, the unit naming on verdicts, the severity reading, the figure caption, the ladder limit and
  the closing ladder note.
- `docs/experiments/pilot2-phase2/EPOCH_LADDER_RESULT.md` — per-target framing, units, the #711 and
  #712 decisions, the observed-versus-registered MDE arithmetic, and the estimand reporting rule
  under Limits.
- `scripts/analyses/freq_sev_fair_test.py` — the severity task row's decision becomes **No claim**;
  its value is unchanged. `scripts/infra/verdict_figures.py` colours the new label,
  `tests/test_verdict_figures.py` pins it, and `docs/figures/freq_sev_forest.{pdf,png}` are
  regenerated.
- `scripts/analyses/finetuning_runs_ledger.py` plus the regenerated ledger — the title no longer
  claims to be exhaustive, and a scope paragraph names the row-scaling runs and the two ladder
  captures it does not carry.
- The two live documents that restated the old reading: `docs/shared/tfm_insurance_literature_frontier.md`
  and the fair-test `README.md`; `docs/REPORT_REGISTRY.md` follows.
- `CHANGELOG.md`, `docs/plans/README.md`.

No evidence, no per-target number and no per-target verdict changes; one task label becomes
**No claim**, and the figure is redrawn from the same captures.

## Verification

- `./scripts/check.sh doclinks`, `docstatus`, `citation`, `evidence` and `ruff` from this worktree,
  with the main clone's venv on `PATH`.
- `pytest tests/test_finetuning_runs_ledger.py tests/test_verdict_figures.py` for the byte-identical
  ledger render and the figure's decision labels.
- Full `pytest` in CI.

## Out of scope

- Re-reading the captures, or any new run.
- Building #712's checks (decided here, built under its own ticket).
- Option B's like-for-like protocol.
