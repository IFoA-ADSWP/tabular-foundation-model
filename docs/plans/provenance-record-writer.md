# Plan — one diagnostic record writer, so D1–D5 cannot diverge

**Issue:** #211 (part of the #208 umbrella; #240/#241 own the pilot's record shape).
**Status:** Current.

## What and why

`scripts/diagnostics/` does not exist, so the five funded diagnostics would each invent the
shape of their output, and the divergence would become permanent after the first commit.
`outputs/gpu-pilot/README.md` records what that costs: a `csv.DictWriter` header written by an
older schema shifted every ledger column, and a record split across two clones made three runs
invisible. Both were caught once, by hand, on one dataset; five producers make the same class
of error undetectable, because the whole point of the diagnostics is that their outputs are
comparable.

Two changes, in this order:

1. **Move** `dataset_fingerprint`, `inference_context_rows` and `assert_matched_context` out of
   `scripts/run_pilot.py` into `src/provenance.py`, so the pilot and the diagnostics compute
   provenance from one implementation. Pure move: same behaviour, same semantics, same tests.
2. **Add** one writer, `write_diagnostic_record`, and its first consumer,
   `scripts/diagnostics/d1_profiling.py`.

## The move, and where the pilot's config stays

The three helpers read the pilot's module globals (`DATASETS`, `DATA_DIR`, `DATA_REF`,
`FT_ARMS`, `BASELINE_TABPFN_ARM`, `_sha256_file`). Two do not need to be shared config:

- `FT_ARMS` / `BASELINE_TABPFN_ARM` **move** with the assertion — they define what "matched
  context" means, and two spellings of that set is the divergence this ticket exists to stop.
- `sha256_file` **moves** (public name; `run_pilot` keeps importing it as `_sha256_file`).

The dataset registry, the data directory and the source pin stay in `run_pilot.py`, because
they are the runner's declaration of *which file and which ref this run used*, not facts this
module can know. `run_pilot.dataset_fingerprint(name)` therefore remains a four-line adapter
that binds them and calls `provenance.dataset_fingerprint(...)` with explicit inputs. #240
already plans for this ("the shared helper must take the frame plus target and drop columns
instead, and the pilot's call site adapts"), so #241 replaces the adapter rather than the
module.

## The writer

`DiagnosticRecord` is a frozen dataclass and is the **only** field definition. `schema_version`,
`created_utc`, `git_sha`, `git_dirty` and the runtime versions are stamped by the writer, not by
the diagnostic, so no two diagnostics can stamp them differently; `measurements` is the one
free-form key, holding each diagnostic's own numbers under a fixed spelling. The pilot's
provenance vocabulary is carried as values — `seed`, the resolved `model_version`, the
`matched_context` assertion's own evidence — so #241 can fold them into its `provenance` block
without the diagnostics having to re-collect anything.

The two recorded failures are made structurally impossible:

| Failure | Why it cannot happen here |
| --- | --- |
| stale CSV header | the header is `DIAGNOSTIC_RECORD_FIELDS`, derived from the dataclass; the CSV is written fresh into a new `<diagnostic>/<run_id>/` directory, never appended to an older file |
| split record | one call writes `record.json` and `record.csv` into one directory whose path is derived from the diagnostic and the run id, not chosen by the caller |

An **existing record is refused, never replaced** — the same rule and message shape as
`run_pilot.write_arm_run`. Replacing the file would re-stamp `created_utc` and `git_sha`, so an
old record would claim it was produced now. A second run is a second record, under its own id.

`record.json` is the source of truth and `record.csv` is the one-row view of it, mirroring the
`outputs/gpu-pilot/README.md` rule that JSON is authoritative and CSV is derived.

Records land under `outputs/diagnostics/<diagnostic>/<run_id>/`, which is git-ignored: a run
cannot litter tracked status. Deliberately not `scripts/eval/insurance_benchmark_v1/`, which is
the frontier tree with its own record lineage (#208 gap 4) — D1 exposes no flag that could send
a record there.

## D1

`scripts/diagnostics/d1_profiling.py` profiles one CSV — class balance, feature type mix,
missingness, target shape, maximum absolute feature correlation, feature:row ratio — and emits
the result through the writer. D1's *content* is the diagnostics design's
(`docs/current/FINETUNING_DIAGNOSTICS_DESIGN.md`, #208); this ticket only requires that its
first output exists and goes through the shared writer, so D2–D5 inherit a shape instead of
inventing one.

## Boundary with #241

This ticket adds the diagnostics' record contract. It does **not** add the pilot's `provenance`
block, the verdict reader, or pilot schema 3 — those are #241's, and they extend this module
rather than replace it. The pilot's record shape is untouched: `SCHEMA_VERSION` stays 2 and no
committed record under `outputs/` is rewritten.

## Verification

- `pytest tests/` unchanged for the pilot's existing suites (pure move).
- `tests/test_provenance.py` asserts the record files on disk: the same field order and
  byte-identical CSV header for two diagnostics writing through one writer, a record read back,
  and a refusal to replace an existing record (the original bytes unchanged afterwards).
- `tests/test_d1_profiling.py` covers the profiling rule on a synthetic frame and the script
  emitting through the writer, including that the CLI has no flag naming a location.
- A real D1 run over `data/raw/coil2000.csv`, into the ignored `outputs/diagnostics/` tree, for
  evidence in the PR; no record is committed.
