# Plan — the Spanish lapse cell: leak-safe data, a pre-registered probe, and a resolution gate

**Status:** current — 2026-11-05. **Issue:** #444, the spec. **Branch:** `feat/444-spanish-cell` from
`main`. **Authorises:** nothing. No launch, no spend.

## What and why

The Spanish cell cannot be launched: the two post-outcome claim columns enter every arm, 1,000 test rows
fail the resolution floor, there is no dated pre-registration, and the balance does not cover the
replication. This change makes it **definable and gateable offline** — the data is leak-safe, the test
size is fixed by a measurement, and the probe is written down — while leaving the spend decision where
it belongs.

## The deviation the spec did not see

The spec's Implementation Decisions say `[pilot_datasets.spanish_motor_lapse]` gains the drop and "the
existing registry path already reads a dataset's `drop`". That is true for the **frontier benchmark**,
not for the fine-tuning pilot:

- `run_pilot.py` loads datasets from its own `DATASETS` table, not from the registry.
- `load_dataset()` drops the target only; it never applies a declaration's drop.
- `[pilot_datasets]` is a two-key registry section (`file`, `target`); its schema rejects a `drop` key,
  and its comment states "the pilot drops no columns".

So the fix lands where the runner reads: the runner's `DATASETS` table gains the two columns, and
`load_dataset()` applies whatever `drop` the table declares. Both the matrix and the record read that
declaration through one `declared_drop()` helper, so they cannot drift; the fingerprint's `columns` and
`n_cols` describe the source file, and `drop` names what the runner removed before encoding. The stale
TOML comment is corrected; the registry schema is unchanged. A test binds the registry's `file`/`target`
to the runner's table, so the two declarations cannot drift either.

`load_dataset()` now fails closed when a declared drop names a column the table does not have. That is
slightly beyond the spec, but it is the difference between a declared field and an enforced one.

## The resolution measurement (offline, no spend)

The floor is a paired 95% half-width of **≤ 0.006** at the cell's test size. The measurement is a
committed tool, so the number is reproducible rather than recalled:

```
python scripts/analyses/proxy_resolution.py --csv data/raw/spanish_motor_lapse.csv \
  --target LapseB --drop N_claims_year,Cost_claims_year \
  --train 10000 --test 10000 --seeds 42,43,44 --resamples 4000
```

It uses HistGradientBoosting at scikit-learn defaults, 10,000 training rows, a 90% training subsample as
the perturbation, and 4,000 paired bootstrap resamples, with the two leak columns dropped:

| Test rows | Seeds 42 / 43 / 44 half-width | Max |
|---|---|---|
| 1,000 (the rejected size) | 0.0163 (seed 42) | 0.0163 |
| 6,600 | 0.0057 / 0.0057 / 0.0061 | 0.0061 |
| **10,000** | **0.0047 / 0.0045 / 0.0051** | **0.0051** |

The 1/√n scaling from the 1,000-row figure implies `1000 × (0.0163 / 0.006)² ≈ 7,380` rows. The measured
6,600-row figure (max 0.0061) shows the scaling is optimistic, so `T = 10,000` is chosen for margin;
the extra inference rows cost little against 30-epoch training. Training stays at the 10,000-row cap;
the runner loads 20,500 rows and the remaining 33,002 are never read.

The 1,000-row check is 0.0163 here against the readiness study's 0.0154 — the same proxy family, not
the same code. The pre-registration quotes **this** measurement and carries the command, so the number
it relies on is reproducible from the committed CSV.

## What lands

1. **`run_pilot.DATASETS["spanish_motor_lapse"]`** declares the two drops, and **`load_dataset()`**
   applies them; both it and the fingerprint read `declared_drop()`.
2. **`scripts/analyses/proxy_resolution.py`**, the measurement above, with a CLI test.
3. **A pre-registration** in `docs/current/` fixing: drops, 10,000 train / 10,000 test, fresh probe
   seeds, the rung rule, `k = ceil((sd / 0.000714)²)`, the probe ceiling (**$0.50**), the replication
   ceiling (**$3.00**), the stop rule, the reading and the Brier veto. `k` is an amendment after the
   probe, as the anchor's was. A **decision-log entry** (D19) records that it authorises nothing.
4. **Tests**: the loader excludes the two columns while another dataset's width is unchanged; the
   fingerprint uses the same declaration; the registry and the runner name the same table; the
   pre-registration's 0.000714 equals `δ / (Z_ALPHA + Z_POWER)` and its reference `k` reproduces through
   `resolution()`.

## What does not land

The probe and the replication. At the 1,000-row unit price the replication projects at ≈$6.3 (D17) and
≈$18.8 per dataset (the breadth specification's pessimistic line); 10,000 test rows only add inference.
Both exceed the $3.00 ceiling, so the documented default outcome is a stop; only the owner can authorise
the probe, and #444's Out of Scope keeps that separate. The #428 hardening tickets are prerequisites in
time, not work here.

## Verification

- `pytest tests/ -q`, `ruff check scripts/ src/ tests/`, `shellcheck --severity=warning`
- `./scripts/check.sh doclinks`, `docstatus`, `citation`, `evidence` (no evidence tree changes here)
- The loader test computes the expected feature width independently from the CSV, not from the loader.
- The CLI test runs the proxy tool on a synthetic table, which is a third seam beyond the two agreed in
  the spec; it is what makes the half-width a cited measurement rather than a claim.
