# Plan — a run records its declared and resolved model version (#239)

**Status:** Current — issue #239 (parent #236, blocked-by #237, blocking #233).
**ADR:** `docs/adr/0001-experiment-spec-pins-version-and-guards-reuse.md`
**Glossary:** `GLOSSARY.md` — *model version*, *provenance*, *reuse*.

## Why

The registry pins `model_version` as a **literal**, while execution resolves it
**environment-first** (`src/model_version.py`: `TABPFN_MODEL_PATH`, then `.env`, then
`v3_default`). Both are deliberate: declaration is intent, execution is what the box
actually ran. The gap between them is the failure mode `docs/MODEL_VERSIONS.md` exists
to prevent, and until now a drifted run would have recorded only the resolved value, so
the artifact could not contradict itself — it could only quietly stop meaning what the
experiment declared.

#254 already records the **resolved** version (`model_version`) in the run manifest
beside `model_version_scope`. This ticket adds the **declared** literal and the
comparison. It does not restate the scope note.

## Two constraints from the #230 build

Both are load-bearing; a change that satisfies the acceptance criteria but breaks
either is the wrong change.

1. **This ticket returns a fact. It does not own reuse.** A drifted run must be
   *identifiable*, not *handled*. #233 owns the reuse predicate, and a second
   eligibility rule is the exact bug the registry work removed. So the mismatch is
   exposed as data — one boolean — and #233 consumes it.
2. **Absent is not false.** An ad-hoc run (`--data`, a positional dataset filter) has
   no declaration, so it can be neither matched nor mismatched. It records *absent*.
   "No experiment declared this" and "the declared and resolved versions agree" are
   different facts; collapsing them makes a legacy row look verified.

## What changes

- `src/model_version.py` — `version_mismatch(declared, resolved) -> bool | None`:
  the one definition of the comparison, returning the *mismatch* because that is the
  fact the artifact records (inverting an agreement at each call site would turn the
  absent `None` into a false flag). `resolve_model_path` and its env-first order are
  untouched; this function resolves nothing.
- `scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py` —
  - a module global `DECLARED_MODEL_VERSION`, set from `experiment.model_version` in
    `main()` (and reset to `None` on the ad-hoc path), beside the existing
    `EXPERIMENT_ID` global;
  - the run manifest gains `model_version_declared` and `model_version_mismatch`;
  - the capture manifest gains the same two fields, so the capture cannot be the one
    artifact that looks verified while the run it came from drifted.
- `tests/test_model_version.py` (new) — the tri-state contract of the comparison.
- `tests/test_frontier_cli.py` — both manifests for agree / differ / ad-hoc.
- `CHANGELOG.md`, `TASKS.md`, `docs/MODEL_VERSIONS.md` — pointers, per the repo's
  "tracked artifacts" rule.

## Decisions

- **Three states, spelled `true` / `false` / `null`.** `null` is this repo's existing
  JSON spelling for absent (`experiment_id` on an ad-hoc capture manifest); the key is
  always present so a reader can tell "absent" from "field predates the schema".
- **Flag, do not abort.** The ticket says the drift is *identifiable*; refusing the run
  would be *handling* it, and would make the flag unreachable for the exact case it
  describes. The run proceeds with the contradiction written down.
- **No reuse logic here.** The sweep reuse path keeps its current predicate. Criterion
  "a mismatched run's rows are never reused" is discharged by publishing the single
  input #233 must require to be exactly `false` — `null` is not false — and by adding
  no second rule that could disagree with it.
- **The registry still does not resolve.** `experiments.toml` and
  `src/experiment_spec.py` are untouched: `Experiment.model_version` stays the literal
  it declares, and the comparison happens where execution has already happened.
- **Both manifests, one definition.** The run manifest and the capture manifest call
  the same function, so they cannot disagree about the same run.
- **The declared literal is the run's, not the dataset's.** #231 (merged while this
  branch waited) made the all-datasets classification path run one declared experiment
  per dataset, but the run manifest names no single experiment on that path —
  `experiment_id` is `null` there too. So `model_version_declared` is recorded when the
  run names one experiment (`--experiment <id>`) and is `null` otherwise. Deriving "they
  all agreed" would be a second eligibility rule invented outside the ticket;
  per-dataset provenance is #233's.

## Evidence this works

- The gate, **measured on this worktree rather than inherited** from the plan docs:
  `./scripts/check.sh` before any edit. Baseline recorded in the PR/commit.
- After merging `main` (which landed #231's classification runner and #241's record
  contract): `./scripts/check.sh` exit 0, **336 passed**, ruff and shellcheck clean.
  `scripts/check.sh` runs three commands; the fourth CI check — doc links and doc status
  — runs inside pytest, so green pytest covers it.
- A run at `TABPFN_MODEL_PATH=v3.5_default` against an experiment declaring
  `v3_default` writes `model_version_mismatch: true` with both values named.
- An unexported run against the same experiment writes `false`.
- `--data` writes `null`, not `false`.
