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
2. **Absent is not false.** An ad-hoc run (`--data`, a filter that matches nothing) has
   no declaration, so it can be neither matched nor mismatched. It records *absent*.
   "No experiment declared this" and "the declared and resolved versions agree" are
   different facts; collapsing them makes a legacy row look verified.

## What changes

- `src/model_version.py` — `version_mismatch(declared, resolved) -> bool | None`: the
  one definition of the comparison. `resolve_model_path` and its env-first order are
  untouched; this function resolves nothing.
- `run_frontier_benchmark.py`
  - `model_version_fields(declared, resolved)` returns the two manifest keys from the
    declarations an artifact covers, so the run manifest and the capture manifest cannot
    disagree about the comparison or its spelling.
  - The **run manifest** records the declarations of the experiments the run will
    actually execute (`RUN_DECLARED_VERSIONS`): one experiment under `--experiment`, the
    filtered sweep's experiments otherwise, none for `--data` or the regression path.
    `model_version_declared` names a literal only when they all agree; the flag is
    answerable either way — true when *any* covered declaration differs from what
    execution resolved. The sweep is the common run, and it can now flag drift.
  - The **capture manifest** takes the dataset's `Experiment` rather than the run's
    global, and records that experiment's literal. A capture covers one experiment, so it
    must not write "no experiment declared this" about a declaration that exists.
- `tests/test_model_version.py` (new) — the tri-state contract of the comparison.
- `tests/test_frontier_cli.py` — both manifests for agree / differ / ad-hoc, a sweep that
  agrees, a sweep that drifts, a filter that covers nothing, and a capture that keeps its
  own dataset's declaration.
- `CHANGELOG.md`, `TASKS.md`, `docs/MODEL_VERSIONS.md` — pointers, per the repo's
  "tracked artifacts" rule.

## Decisions

- **Three states, spelled `true` / `false` / `null`.** `null` is this repo's existing
  JSON spelling for absent (`experiment_id` on an ad-hoc capture manifest); the key is
  always present so a reader can tell "absent" from "field predates the schema".
- **Flag, do not abort.** The ticket says the drift is *identifiable*; refusing the run
  would be *handling* it, and would make the flag unreachable for the exact case it
  describes. The run proceeds with the contradiction written down.
- **No reuse logic here.** The sweep reuse path keeps its current predicate. The
  acceptance criterion "a mismatched run's rows are never reused" is discharged by
  publishing the single input #233 must require to be exactly `false` — `null` is not
  false — and by adding no second rule that could disagree with it.
- **A multi-experiment run invents no literal.** Six experiments that all declare
  `v3_default` give one nameable value; six that disagree give none, and the flag still
  says whether the run drifted. Deriving agreement by majority or by "close enough" would
  be the inference ADR 0001 distrusts.
- **The registry still does not resolve.** `experiments.toml` and
  `src/experiment_spec.py` are untouched: `Experiment.model_version` stays the literal it
  declares, and the comparison happens where execution has already happened.
- **The capture's two keys are top-level, beside `model_version`, not inside a
  `provenance` block.** #241's `verdict()` reads the capture's version through the legacy
  key map and does not know these two keys. #233 must read them directly; teaching the
  record contract about a declared/resolved pair is #241's schema to change, not this
  ticket's. Recorded here so the gap is visible rather than discovered later.

## Evidence

- The gate, **measured on this worktree rather than inherited** from the plan docs:
  `./scripts/check.sh` before any edit — exit 0, 270 passed.
- After the change: exit 0, 284 passed. After merging `main` (#231's classification
  runner, #241's record contract): exit 0, 336 passed. Final figure in the PR.
- `scripts/check.sh` runs three commands; the fourth CI check — doc links and doc status —
  runs inside pytest, so green pytest covers it.
- A run at `TABPFN_MODEL_PATH=v3.5_default` against experiments declaring `v3_default`
  writes `model_version_mismatch: true` with both values named — on the sweep path as
  well as under `--experiment`.
- An unexported run writes `false`; `--data` writes `null`, not `false`.
