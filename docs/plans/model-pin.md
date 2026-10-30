# Plan — pin the model version the pilot records (#285)

**Status:** Current — implementing 2026-10-30.
**Origin:** issue #285, filed from the record-contract review (#241).

## The defect

`run_arm_a_raw` constructs `TabPFNClassifier` with no `model_path`, so the library loads its own
default. The record states `resolve_model_path()` — the *resolver's* label. When `TABPFN_MODEL_PATH`
is unset the two agree by luck; when it is set, the record names a model the run did not load. That
is a declaration, not evidence, and it is the thing `docs/MODEL_VERSIONS.md` exists to prevent.

## The change

- `run_arm_a_raw` passes `model_path=resolve_model_path()`.
- `run_arm_b_in_domain` passes it through `extra_classifier_kwargs`, because the fine-tuner has no
  `model_path` of its own and forwards classifier kwargs.

Nothing else moves: the same resolver, the same default (`v3_default`), the same config.

## What this changes about results — and a correction

**This is not a no-op, and the first draft of this plan wrongly said it was.** The library default is
`model_path="auto"`, and `docs/MODEL_VERSIONS.md` records that the **server default became v3.5**, so an
unpinned call no longer resolves to v3. Two consequences:

- From this commit on, a pilot run loads the version the record states.
- **An unpinned pilot run made after that server-side change may have loaded v3.5 while its record said
  `v3_default`.** The probe and R1 numbers are re-read with that caveat; nothing here re-labels them.
  The anchor is unaffected structurally because it re-baselines in every run (D9), but it is the first
  pilot run that can state its version truthfully.

The 2,000-row probe and the 10,000-row anchor share this exposure; `docs/MODEL_VERSIONS.md` gains a note
so the next reader does not assume the old labels were pinned.

## Verification

- Constructor kwargs are asserted against the resolver, with the library stubbed so no weights load.
- The env override is exercised: `TABPFN_MODEL_PATH=v3.5_default` reaches both constructors.
- `./scripts/check.sh` green.
