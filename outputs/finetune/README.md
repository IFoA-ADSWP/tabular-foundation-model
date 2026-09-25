# Fine-tuning pilot — root artifacts

This directory holds duplicate copies of pilot artifacts that are canonical
elsewhere. They are kept here only during active runs and are gitignored
after commit. Do not cite from this location.

Canonical locations (what the reports cite):

- `outputs/finetune/pilot/pilot_metrics.parquet` — aggregate metrics (12 runs).
- `outputs/finetune/pilot/pilot_predictions.parquet` — per-row predictions (12,000 rows).
- `outputs/finetune/pilot/<dataset>/<arm>/meta.json` — per-run config/versions/device.

This directory's copies are duplicates and may drift. Use the canonical paths.
