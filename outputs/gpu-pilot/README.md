# Pilot artifacts — what's committed and what isn't

This directory holds the R1 GPU pilot outputs. The committed files are the
**provenance metadata** — enough to verify the runs referenced in
`docs/reports/FINE_TUNING_PILOT_RESULTS.md` and `docs/reports/SMOKE_TEST_SCOPE.md`.

## Committed

- `run_ledger.csv` — per-run cost and device ledger (13 runs).
- `run_*.json` — per-run manifests (config, versions, device, timings, 13 runs).
- `README.md` — this file.

## Not committed (gitignored)

- `pilot_metrics.parquet` — aggregate metrics; the same data is committed at
  `outputs/finetune/pilot/pilot_metrics.parquet` (the canonical copy which the
  reports cite). This copy is a duplicate and is ignored to avoid drift.
- `pilot_predictions.parquet` — per-row predictions; committed at the canonical
  location `outputs/finetune/pilot/pilot_predictions.parquet`.
- `dry-runs/` — dry-run artifacts, not part of the reported results.
- `run_ledger.csv.corrupt-bak` — backup of a corrupt file, not evidence.

## How to re-run

The runner is `scripts/run_pilot.py`; the box bootstrap is
`scripts/gpu_helpers/bootstrap_pilot.sh`. See `docs/REPRODUCIBILITY_RUNBOOK.md`
§C for the full replication path and the environment deviation note
(tabpfn==8.5.0, v3_default weights — the repo pin is `tabpfn>=6,<7`).
