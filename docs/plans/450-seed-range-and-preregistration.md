# Plan — a seed range, and a pre-registration the record names (#450)

**Status:** Current — implementing 2026-11-06.
**Origin:** ticket #450. **Blocks:** the Spanish lapse cell's probe (D19).
**Pre-registration:** `docs/current/FINETUNING_PREREGISTRATION_SPANISH_2026-11.md`.

## The three defects, restated as work

D19 fixes the Spanish cell at four arms × seeds **331–340**, 10,000 train / 10,000 test. The tree
cannot express that launch:

1. `PilotExperiment.seed` is a single `int`, and `resolve_invocation` refuses `--seeds` against a
   declaration, so the probe cannot run under `--experiment`.
2. No field anywhere names the pre-registration, so the document's *"a launch record must name this
   document"* is unexpressible and therefore unenforceable.
3. `vast_run.sh` refuses ten seeds at the default estimate (2600 s against a 2400 s poll), and the
   default is optimistic for four arms at 10,000 test rows.

This change fixes (1) and (2). (3) is a measurement, not code — see "What this does not do".

## Decision 1 — a seed list, with `seed` kept as an alias

`PilotExperiment.seed: int` becomes `seeds: tuple[int, ...]`. The TOML accepts `seed = 42` **or**
`seeds = [...]`, exactly one, so the four committed experiments are untouched and their meaning does
not change. Accepting both at once is refused: two spellings that could disagree is the drift #238
exists to remove.

## Decision 2 — a subset selects; an outside seed contradicts

`--seeds 331,332,333` against a declaration of 331–340 must be **accepted**, not refused. The
launcher batches a probe across several launches — it has to, because a ten-seed batch overruns the
poll window — so each launch carries a subset by design. This is the rule arms already use, and the
reason is identical: *"A subset SELECTS within the declaration; an arm the declaration does not name
is a contradiction, not a selection."*

A seed outside the declared range is still a contradiction and still refused, naming both.

## Decision 3 — `preregistration` is required when more than one seed is declared

A single-seed experiment is a reproduction of something already agreed; a multi-seed experiment is a
replication whose seed count decides its power, and choosing seeds after seeing the first result is
the failure D13/D19 exist to prevent. So:

- `preregistration` is optional in the schema;
- **required when `seeds` has more than one entry**, refused with the reason and the document it
  expected;
- written into the run manifest as `preregistration`, so a launch record names it.

No `kind = "cell"` field is added. A cell is exactly a pre-registered multi-seed design, and inventing
a second axis of classification would be a schema the ticket did not ask for and the next reader would
have to learn.

## What changes

| File | Change |
|---|---|
| `src/experiment_spec.py` | `PilotExperiment.seeds` + `.preregistration`; parse `seed`/`seeds` and refuse both; require `preregistration` for multi-seed; validate seeds are unique and non-negative |
| `scripts/run_pilot.py` | `--seeds` subset rule; return the declared seeds and pre-registration from `resolve_invocation`; manifest carries `preregistration` |
| `scripts/eval/insurance_benchmark_v1/experiments.toml` | `[pilot_experiments.spanish_motor_lapse_cell]` — the dataset, four arms, 10,000/10,000, `v3_default`, the pre-registration path |
| `tests/test_experiment_spec.py` | the parse rules |
| `tests/test_pilot_registry.py` (or the seed-passthrough suite) | the invocation rules and the manifest field |
| `CHANGELOG.md` | one entry |

## Wrongness checks

- A declaration with **both** `seed` and `seeds` is refused, not silently preferring one.
- A launch whose `--seeds` lies **outside** the declaration is refused, naming the declared range.
- A multi-seed declaration with **no** `preregistration` is refused — the rule that makes the field
  load-bearing rather than decorative.
- A **subset** is accepted and the manifest records the subset, not the whole range, so two launches of
  one cell cannot both claim all ten seeds.
- Existing single-seed experiments still resolve to exactly one seed, so `eudirectlapse_p1a` and its
  three siblings are unchanged.

## What this does not do

- **It does not measure the per-seed cost or decide the batching.** That needs a real launch at four
  arms and 10,000 test rows, which is spend. Until it exists, `vast_run.sh`'s 170 s default will refuse
  ten seeds — correctly, and that refusal is the evidence that the batching is unresolved. Recorded on
  the ticket rather than papered over with a bigger `--estimate-sec-per-seed`.
- **It does not authorise the probe.** D19's $0.50 ceiling is a separate decision.
- **It does not touch #438.** `requested_seeds` in the directory name is that ticket's; this one adds
  `preregistration` only, and the two fields are adjacent but not the same claim.

## Verification

- `./scripts/check.sh` green, all eight checks.
- `shellcheck` on the launcher, because the paid path is touched if any flag changes.
- The Spanish cell resolves: `--experiment spanish_motor_lapse_cell` reports 10,000 / 10,000, four arms,
  seeds 331–340, and the pre-registration path.
