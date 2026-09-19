# Root-level pilot artifacts

Duplicate copies of `pilot_metrics.parquet` and other pilot outputs that are
canonical in `outputs/`. These are transient working copies from active runs.

Canonical locations:

- `outputs/finetune/pilot/` — fine-tuning pilot (CPU + GPU, 12 runs).
- `outputs/gpu-pilot/` — GPU execution era provenance (run manifests, ledger).

This directory is gitignored. Do not cite from here; use the canonical paths above.
