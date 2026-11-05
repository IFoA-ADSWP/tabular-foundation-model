# Plan — a batch verifies the seeds it actually wrote (#429)

**Status:** Current — 2026-11-05. **Issue:** #429 (a child of the paid-run hardening tracking
issue #428). **Branch:** `feat/429-verify-seeds` from `origin/main` @ `2e28cdf`. **Scope:**
one flag on `verify_artifacts.py`, one call site in `vast_run.sh`, tests. No launch, no spend.

## What happened

`VERIFY predictions verified=24 mismatched=0 missing=0` answers "these records are internally
consistent". It does not answer "these are the seeds the launch asked for". On 2026-11-05 two
launches (`waveC-3` asked 225–236, `waveC-4` asked 237–248) each wrote **141–152** and each
reported `verified=24`: the count was right, the hashes were right, the range was wrong.

## What changes

`scripts/gpu_helpers/verify_artifacts.py` gains `--expect-seeds LIST` (comma-separated ints and
`a-b` ranges, so the launcher can pass `$SEEDS` verbatim and a human can pass `225-236`).
After a successful unpack it walks the restored tree's `meta.json` files, collects every
`seed` **per `(dataset, arm)`**, and compares each group with the requested one:

- missing seeds (requested, never written) → refuse
- unexpected seeds (written, never requested) → refuse
- a partial run (fewer seeds than requested) is the missing case, and is refused too
- an arm that is short while the union looks complete is its own refusal (`INCOMPLETE`),
  because "partial" is a property of an arm as much as of a batch

The refusal names **both** sets, compressed to ranges, and exits `6` — a new code beside
`3`/`4`/`5`. Duplicate seeds across folds collapse: the unit compared is a seed, not a
record. A seed recorded as a string is read as that seed rather than as an absent one.

`--expect-seeds` is applied on **both transports**: onstart unpacks the log payload as
before, and the ssh pull — which had no verification at all — runs `--verify-only` over the
files it just copied.

`scripts/gpu_helpers/emit_artifacts.sh` also needed a fix, found while making the wrong-tree
test reliable. It declared `lines=` by arithmetic rather than by counting what it sends, and
was wrong in both directions: dividing the base64 byte count declared one line too many when
the payload length was an exact multiple of the fold width, and `fold | wc -l` declared one
too few when the final line had no trailing newline. Either way the receiver refuses a good
batch as truncated — the first roughly once in 440 runs, the second on whichever platform
leaves the last line unterminated. The emitter now materialises the folded lines once and
declares their count, so declaration and transmission cannot disagree.

`vast_run.sh` passes `--expect-seeds "$SEEDS"` only when the launch was given seeds, so an
unseeded launch is unchanged. On exit `6` it prints `REFUSING` to stderr, names the evidence
directory, and sets `RUN_RC=1`; exit `5` (predictions arrived but do not match their hashes)
refuses the same way, since a batch whose evidence cannot be trusted must not read as a
success. The script now ends with `exit "$RUN_RC"` instead of inheriting `ls`'s status, so
either refusal is visible to the caller and to #430's harness. The pull has already happened,
so the wrong tree stays on disk for inspection.

## Scope note

"Batch" here means what the issue and #430 mean by it: **one launch over a seed range**, not
the queue of them. `GLOSSARY.md` prefers *launch* and lists *batch* under "avoid" for
*sweep*; the issue's wording is kept because #430's harness and the runbook's rules already
use it in this sense.

## Seams

1. **`verify_artifacts.py --expect-seeds` on an unpacked tree.** Catches a wrong, partial or
   unexpected seed set; misses whether the bytes came from *this* launch rather than a
   concurrent one (#431).
2. **The real launcher against `mock_vastai.sh` with a deliberately wrong tree.** Catches a
   verifier that refuses but a launcher that still exits 0. Misses cross-launch contamination.

## Tests

- wrong tree (asked 225–236, tree holds 141–152) → launcher non-zero, both sets named, evidence
  kept
- correct tree → launcher 0, unchanged
- partial tree (asked 141–143, tree holds 141–142) → refused, `143` named as missing
- one arm short while the union is complete (A 141–143, B 141–142) → refused as `INCOMPLETE`
- unit: range parsing and rendering (`225-236`, `141,143,150-152`), a string seed, and a tree
  whose metas carry no `seed` at all is a mismatch rather than a pass
- the ssh pull branch reaches the verifier too (`--verify-only`), which it previously did not

## Verification

- `./scripts/check.sh ruff` and `./scripts/check.sh shellcheck` (the paid-run path moved)
- `python -m pytest tests/test_pilot2_seed_passthrough.py -q`
- `./scripts/check.sh` (all eight) before the PR
