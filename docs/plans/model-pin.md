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

## What this changes about results

If `TABPFN_MODEL_PATH` is unset — every run to date — the loaded weights are the baseline the resolver
also names, so results are unchanged. If it **is** set, results can change, and that is the point: the
record and the run now agree. The anchor's acceptance already re-baselines in every run (D9), so a
different pin is absorbed by its in-run `A_raw` rather than compared across model eras.

## Verification

- Constructor kwargs are asserted against the resolver, with the library stubbed so no weights load.
- The env override is exercised: `TABPFN_MODEL_PATH=v3.5_default` reaches both constructors.
- `./scripts/check.sh` green.
