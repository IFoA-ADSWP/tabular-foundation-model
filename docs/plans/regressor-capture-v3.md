# Plan — capture v3 and the regressor fair-test runner

**Issues:** contract #538, runner #539 (blocked by #538).
**Status:** Current — delivered (writer, reader, gate, rescore, registry); the runner is #539.

## What and why

A contributor who prefers a metric other than the pre-registered one cannot compute it. The capture
retains truth and predictions, so RMSE, MAE and count-scale Poisson deviance are possible; anything
needing a source column, a predictive distribution, or a fold-aware reader is not.

The pre-registration fixes the metric — Poisson deviance for `ClaimNb`, RMSE for severity and
VehValue — and this work does not reopen that. It widens what is retained and makes it rescorable.

## Shape

**#538 — the contract, testable with fixtures and no run:**

1. `schema_version: 3` in `src/run_capture.py`: `test_index.npy`, `quantiles.npy` in every slot;
   `exposure.npy` for freMTPL2freq only; no partial form.
2. Hashes in the manifest for every array; `scripts/check_citations.py` applies the v2 environment
   check to v3 and requires the array hashes.
3. `src/capture_reader.py` becomes version-aware and keys `(arm, seed, fold)`; `VerifiedSlot` gains
   `fold`. Without it a folded capture is unreadable — true of the v2 capture shipped in #501.
4. `src/rescore.py` gains a `fold` column and a regression metric set; six rows in
   `METRIC_REGISTRY.md` with definitions, and `tests/test_metric_registry.py` extended to both sets.
5. `meta.json` keys: `verdict_metric`, `verdict_metric_value`, `rmse`, `quantile_levels`.

**#539 — the runner:** Arm × fold × model seed over the pre-registration's design, writing v3
through `src/run_capture.py`.

## Judgement calls

1. **Raw CSV rows, not prepared-frame positions.** A reader must be able to `read_csv` and join
   without repository code; the index is absolute in that file, so no loader order has to be
   reconstructed.
2. **The index is the fold's, not the slot's.** Fifteen slots carry it; a disagreement is a bug, and
   a test asserts they agree rather than trusting the writer.
3. **Quantiles are stored pre-clip and on the trained scale.** A rescoring reader chooses its own
   treatment; the capture does not choose for it.
4. **`poisson_deviance/1` is the deviance of counts.** Exposure is a feature, not an offset. A
   rate-scale variant is a different name, and this is the sentence that stops two implementers
   producing two decision numbers under one name.
5. **The reader fix ships with the contract, not after it.** v3 lands on a reader that already
   cannot read v2; adding a version without fold keys would make the new schema unreadable too.

## Verification

- Fixture run in the v3 shape: hashes match, gate accepts; one doctored array is refused; a slot
  missing a required array is refused; a severity slot without `exposure.npy` is accepted.
- v1 and v2 fixtures are byte-identical and their existing tests pass unchanged.
- `rescore` recomputes the recorded values for a regression fixture and reports `agrees` per metric,
  with `fold` in the row.
- `tests/test_metric_registry.py` covers both metric sets.
- `./scripts/check.sh` — eight checks; the fixture capture lives under `tests/fixtures/`, so the
  evidence gate stays clean.
