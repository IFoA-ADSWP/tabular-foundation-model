# Plan — the rescore verifies both hashes it was given

**Issue:** #384 (defect found in the review of #382).
**Status:** Current.

## What and why

`src/rescore.py:_verify` checked `predictions_sha256` against the manifest and the record and never
looked at `truth_sha256`. With a `capture.json` present, a mutated `ground_truth.npy` exited 0 and
wrote a cited CSV: the labels decide every value, and nothing verified them.

#361 requires that with a manifest present *both* hashes agree, and #355's decision is that a hash
mismatch refuses. The module docstring justified the gap only for the no-manifest case, where no
truth hash exists — not for the case where one is sitting in the file.

## The change

1. **Verify the truth hash** when a manifest entry exists: compare it to the array on disk; a
   mismatch refuses naming both hashes, and a null `truth_sha256` refuses with the entry's reason
   (the same rule the predictions hash already follows). Without a manifest the gap stays, and the
   docstring says so.
2. **Tests**: a mutated `ground_truth.npy` under a present manifest refuses; an entry with a null
   truth hash refuses with its reason; the anchor's positive case still passes.
3. **The drift test stops being tautological.** It compared the committed `capture.json` to
   `render_capture(build_capture(anchor))`, so a generator bug reproduced itself. It now reads the
   committed file and works each entry out from the arrays and the record — the way a reader would.
4. **One hash helper.** The pilot's `_sha256_array`, the generator's copy and the rescore tool's
   import were three spellings of the hash that decides whether a citation rests on the right
   bytes. They now share `provenance.sha256_array`, beside `sha256_file`.
5. **The metric-set name is computed once.** `select_metrics` returns a `MetricSet` (name plus
   metrics) that `rescore` uses directly, instead of the name being computed in one function,
   discarded, and recomputed in another. `Metric.identity` and `metrics.RECORDED_METRICS` had no
   callers and are deleted.

## Verification

- `pytest tests/test_capture_manifest.py tests/test_rescore_contract.py tests/test_metric_registry.py -q`
- `./scripts/check.sh` — all six checks; evidence unchanged (no file under `results/` moves).
- The anchor still reproduces: all 40 rows `agrees: true`, so the hash move changed no value.

## Out of scope

- A truth hash on the arm record. The record has never carried one, so a manifest-less run keeps
  the stated gap; adding it would change what a run records, which #361 excludes.
- The rest of the review's judgement calls: `docs/analyses/data/` as the output home (#357 decided
  it), the GLOSSARY *Capture* wording, and one-test-file-per-module.
