# Plan — the metric registry, and a rescore that reproduces the recorded five

**Issue:** #361 (slice of #360; identity decided in #356, interface in #357).
**Status:** Current.

## What and why

A recorded number is identified only by the git sha of the code that produced it, and a number
that a run never recorded cannot be computed at all. This slice adds the two pieces that fix
that for the pilot:

1. **A committed registry**, `docs/analyses/METRIC_REGISTRY.md`: one row per metric with its
   version, a one-line definition, and the finding that motivated the current version. It starts
   with the recorded five — `auc/1`, `pr_auc/1`, `brier/1`, `log_loss/1`, `ece/1`.
2. **A rescore tool**, `scripts/analyses/rescore.py --run <dir>`. With no `--metric` it recomputes
   those five from the arrays and compares each to the record, writing a long-format CSV at
   `docs/analyses/data/<run_id>-rescore-<metricset>.csv`: one row per arm × seed × metric with
   `metric`, `metric_version`, `value`, `seed`, `arm`, `capture_sha`, `tool_version`, `source`,
   `recorded_value`, `agrees`.

`agrees` is the point of the default mode: it is a consistency check on the run's own record,
run before anyone cites the number.

## Judgement calls

1. **The five are defined once.** `compute_metrics` and `expected_calibration_error` move from
   `scripts/run_pilot.py` into `src/metrics.py`; the runner re-exports them, so every existing
   call site and `rp.compute_metrics` keeps working. The alternative — a second copy inside the
   rescore tool — would make the registry name two implementations, and the acceptance test
   would be the only thing keeping them equal.
2. **The generator and the reader share one notion of a slot and one hash.** `src/rescore.py`
   reuses `discover_slots` and `sha256_array` from `src/run_capture.py` (#362), so the two tools
   cannot disagree about what an arm × seed is or what a hash covers.
3. **Verification is fail-closed and has two sources.** With `capture.json` present, the
   manifest's `predictions_sha256` must equal the record's `predictions_sha256` and the hash of
   the array on disk; a disagreement refuses naming both hashes, and an entry with null hashes
   refuses with its own `reason`. Without a manifest, the record's `predictions_sha256` verifies
   the predictions array. The truth array has no independent hash without a manifest — that gap
   is stated in the tools' docstrings rather than implied by silence.
4. **`capture_sha` is the predictions hash that verified the row's slot**, so a row is traceable
   to bytes rather than to a run id; `source` names which artifact supplied it (`capture.json` or
   `record`). A row whose `capture_sha` cannot be resolved never exists: the tool refuses first.
5. **Agreement tolerance is `rel_tol=1e-6`, `abs_tol=1e-9`.** Measured on the anchor: recomputing
   the five from the committed arrays differs from the record by at most 3.4e-08 (seed 44,
   `B_ft10`), because the arrays are float32 and the record was computed from the same values
   without the round trip. A tolerance tighter than that would refuse an honest run.
6. **Metric-set name**: the default set is `recorded-five`; an explicit list is sorted
   `name-version` pairs joined with `+` (`auc-1+lift-1`), so the filename is a claim about what
   the rows contain.
7. **Output** defaults to `docs/analyses/data/` and takes `--out-dir` so tests write to a
   temporary directory. Rerunning overwrites with identical bytes; the file is one artifact per
   metric set, never appended to.
8. **`recorded_value` and `agrees` are empty when the record has no value** (the `lift/1` case
   #360 names). Empty means "the record makes no claim", which is different from a disagreement
   and must not read as one.
9. **`tool_version` is a constant in `src/rescore.py`**, bumped whenever a change could move a
   value — the same rule the registry applies to metrics.
10. **The registry is checked against the code.** A test parses `METRIC_REGISTRY.md` and asserts
    its rows are exactly the metrics `src/rescore.py` can compute, so a metric added to the tool
    without a registry row (or a row whose version drifted) fails the suite.

## Seams under test

1. **The rescore CSV on disk** — written, then read back; assertions are on rows, not on internal
   functions. The expected recorded value comes from the record file, not from recomputation.
2. **The refusal** — exit code plus a message naming the file, metric or version that caused it.
3. **The repository tree** — registry rows versus the tool's metric table.

## Verification

- `pytest tests/test_rescore_contract.py -q`
- `python scripts/analyses/rescore.py --run results/20261031T021845Z --out-dir <tmp>` twice, then
  compare the two files — identical bytes.
- `./scripts/check.sh` with `EVIDENCE_CHANGE_OK=1` (the branch still carries #362's manifest).
- The registry's five rows are exercised by the anchor test: every recorded value must reproduce.

## Out of scope

- `lift/1` and `calibration_slope/1` — the registry's next slice, per #360.
- The citation rule and its gate check (#364).
- Reporting recorded metrics and intervals (#353).
- Any change to what a run records at run time: the extraction in judgement call 1 is a move,
  and the anchor test is the proof that the numbers did not move with it.
