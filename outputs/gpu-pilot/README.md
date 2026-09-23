# GPU run records — the audit trail

Everything here is a **record of a provisioned run**, kept so that a cost, a failure or a
provenance question can be answered after the fact. Nothing here is a model artefact.

## The one rule

**The per-run `run_*.json` files are the source of truth. `run_ledger.csv` is derived from them.**

The ledger is regenerated, never hand-edited. It was silently corrupted once: adding fields to the
run record left the older, shorter CSV header in place, and `csv.DictWriter` only writes a header
when the file does not exist, so every row after that was written against a mismatched header and
the columns shifted. `run_ledger.csv.stale-20260912T230446Z` is the quarantined file from that
incident — kept as evidence, not as data.

The writer now enforces that the header matches the record fields and quarantines the old file on
mismatch (see `scripts/gpu_helpers/vast_run.sh`).

## Layout

| Path | What it is |
| --- | --- |
| `run_*.json` | one **real** provisioned run: instance, GPU, price, image, wall time, estimated cost |
| `dry-runs/run_*.json` | **mock** runs. `vastai` was `scripts/gpu_helpers/mock_vastai.sh`, so no instance existed and nothing was spent. Separated by directory rather than by a note because a mock record that looks real is exactly the confusion this directory exists to prevent |
| `run_ledger.csv` | the derived cost ledger over the real runs only |
| `run_ledger.csv.stale-*` | quarantined corrupt ledger from the header-mismatch incident |

**Identifying a mock record.** Mock runs carry the fixture instance id `12345678` and machine id
`424242`. Records written after the dry-run marking was added (see `PILOT_2_PREREQUISITES.md`) also
carry `dry_run: true`; the earlier ones predate that field and are identified by the fixture ids.

## Cost: three numbers, and the account is the authority

| Source | Value | Why it differs |
| --- | --- | --- |
| `run_ledger.csv` (`est_cost_usd`) | $0.5256 over 13 instances | computed as full create→end wall time × `dph_total`, so it charges time an instance existed but was **not** running |
| Account credit arithmetic | ~$0.4002 | credit 9.5998 against a $10 promotional balance. The account's own `total_spend` field reads `-0.40022`; the sign convention is unconfirmed |
| An earlier revision of `SMOKE_TEST_SCOPE.md` | $0.3382 | rebuilt from the per-run records present in **one clone**. The records were split across two clones and neither held the full set — an incomplete set, not a different measurement. The three records held only in the other clone add exactly $0.1874 |

`est_cost_usd` is an estimate produced by this repo's own model of billing. It is **not a bill**.
Anything quoting GPU cost from this repo should cite the account, not this column.

## Rebuilding the ledger

Read every `run_*.json` at the top level (never `dry-runs/`), and write the CSV with a header that
matches the fields exactly:

```
run_id, instance_id, gpu_name, dph_total, gpu_ram_gb, cpu_ram_gb, reliability, cuda_max_good,
image, transport, arms, machine_id, host_id, attempt, disk_requested_gb, t_create, t_running,
t_end, wall_seconds, wall_minutes, est_cost_usd, bootstrap_rc
```

Sort by `run_id`; skip any record whose `instance_id` is `12345678` or `machine_id` is `424242`.

## What is *not* here

The per-arm results (`meta.json`, `predictions.npy`) live under `outputs/finetune/pilot/`. Note
that this directory and that one are both **tracked**, so an ad-hoc run writing there can overwrite
committed records — which is why `run_pilot.py` now refuses to overwrite an existing record unless
`--overwrite` is given, and supports `--outdir` to write elsewhere entirely.
