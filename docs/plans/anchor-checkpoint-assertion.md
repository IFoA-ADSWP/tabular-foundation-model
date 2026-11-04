# Plan — refuse a launch whose weights are not the anchor's line

**Status:** Current — implementing 2026-11-04.
**Origin:** chore alongside #402 and the breadth probe (#412 · `D16`).
**Spec:** `docs/current/FINETUNING_BREADTH_SPEC.md` — "a cell that ran a different model line is not
comparable with the anchor and must say so."

## Scope

`TABPFN_PIN` in `scripts/gpu_helpers/bootstrap_pilot.sh` defaults to `tabpfn==8.5.0`, and that package
defaults `model_version` to `ModelVersion.V3`. So `auto` currently resolves to
`tabpfn-v3-classifier-v3_default.ckpt` on every launch — deterministically, because the package is
pinned.

The gap is what happens when the pin moves. Overriding `TABPFN_PIN` (an upgrade, a hotfix) changes what
`auto` loads, and **nothing refuses or notices**: the record says `version: auto` either way, so a
breadth cell run after a pin bump would be compared against the anchor as if it were the same line. D15
already had to correct a draft that claimed a pin the run did not have.

Three small changes:

1. **`src/model_version.py`** — `expected_checkpoint()` (env `TFM_EXPECT_CHECKPOINT`, empty means "no
   assertion requested") and `checkpoint_mismatch(found, expected)`, which returns the *reason* a
   checkpoint set does not carry the expected file, or `None`.
2. **`scripts/run_pilot.py`** — `_assert_expected_checkpoint()` before any arm runs, and
   `expected_checkpoint` in the manifest, so an unrequested assertion is visible as `null` rather than
   indistinguishable from a pass.
3. **`scripts/gpu_helpers/bootstrap_pilot.sh`** — export `TFM_EXPECT_CHECKPOINT` defaulting to the
   anchor's checkpoint, beside the existing `TFM_WEIGHTS_MANIFEST` export.

## Why an empty cache refuses

If an operator asked for the assertion, a cache with no `.ckpt` is not a pass: the weights have not
been fetched, so nothing was confirmed. Refusing names the fetch step; passing silently would be the
same class of bug the assertion exists to catch.

## What is deliberately not done

- **No default assertion in `run_pilot.py`.** The default lives in the bootstrap, which is the paid
  path. A local invocation that fits v2.5 for a diagnostic must not be forced to carry v3.
- **No hash comparison.** `_weights_provenance` already carries `weights_sha256` when the fetch step
  provides it; this guard answers "which line", which is the question a comparison depends on.
- **No change to #402.** A real pin is a launcher change; this is the assertion that makes its absence
  survivable in the meantime, and the ticket stays open.

## Verification

- `checkpoint_mismatch` unit-tested for present, absent and empty.
- The wiring tested through the run_pilot seam with `_checkpoints` patched: refuses with a message
  naming both the wanted file and what was on disk.
- `./scripts/check.sh` green, including shellcheck (the bootstrap is on the paid path).
