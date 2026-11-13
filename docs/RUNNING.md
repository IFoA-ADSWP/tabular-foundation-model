# Running the code — the route in

> This page is for the reader who wants to **run** something. If you want the **answer**, start at
> [`README.md`](../README.md). If you want to check a **number**, start at
> [`EVIDENCE_MAP.md`](EVIDENCE_MAP.md).

## Which environment?

There are **two** Python environments here, and using the wrong one is the most common way to lose an
afternoon. They hold different TabPFN versions on purpose: the benchmark verdicts were measured against the
hosted client, and the fine-tuning line runs the local package.

| Environment | Holds | Built by | Used for |
| --- | --- | --- | --- |
| `.venv` | Python 3.12, `tabpfn 8.5.0` from `requirements.lock` | `./scripts/bootstrap_dev.sh` | the tests, the diagnostics, `scripts/run_pilot.py`, `scripts/run_fair_test.py` |
| the TabArena venv | `tabpfn-client 0.3.3` (hosted API) | [`notebooks/reproducibility/README.md`](../notebooks/reproducibility/README.md) §Setup | `scripts/eval/`, `scripts/benchmarks/`, the repro notebooks |

`requirements.txt` holds loose ranges and is the file the lock is generated from — install the lock, never the
ranges. `requirements-legacy.txt` is the v2-era path for `scripts/legacy_finetuning/` only, and is never used
for new work. The bootstrap **asserts** the pins instead of printing them, because a venv that merely imports
can still be the wrong venv.

If you are new, build `.venv` and run the tests first. It proves your clone, your interpreter and your lock
agree before any experiment can fail for a less obvious reason.

```bash
./scripts/bootstrap_dev.sh && .venv/bin/pytest tests/ -q
```

## The four routes

| You want to… | Environment | Command | Output | Runbook |
| --- | --- | --- | --- | --- |
| Run the tests | `.venv` | `.venv/bin/pytest tests/ -q` | nothing | — |
| Reproduce a published number | any interpreter with `pandas` (`.venv` is fine); the TabArena venv only for the preflight | `jupyter lab notebooks/reproducibility/01_frontier_classification_repro.ipynb`, then run the read-only cells | nothing — they read committed files | §A.7–§A.9 |
| Run a benchmark yourself | TabArena venv | `python scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py --seed 7 coil2000` — `coil2000` is a dataset name | `results/<run id>/` with `--save-predictions`, else the CSV it names | §A.3, §A.7 |
| Run the fine-tuning pilot | `.venv` locally, the launcher's own pins when rented | `python scripts/run_pilot.py --dataset coil2000`, or `bash scripts/gpu_helpers/vast_run.sh` | `outputs/gpu-pilot/` | §C.2 |

**Start with the notebooks, not the scripts.** Their evidence cells are already executed and read committed
files, so they cost nothing and overwrite nothing. The one exception is the notebook's *preflight* cell, which
imports `tabpfn_client`, `xgboost`, `lightgbm` and `catboost` to prove you are in the benchmark environment —
skip it if all you want is a table. Only the cells tagged `optional` re-run an experiment, and those spend
credits and overwrite the committed results.

**The frontier runner is destructive by default.** With no arguments it overwrites its own committed CSVs.
Three ways to avoid that, in increasing order of isolation:

- `--seed 7` writes separate `_seed7` files and leaves the canonical `seed 42` results alone.
- `--data <csv> --target <col>` runs an arbitrary CSV and leaves the committed suite untouched.
- a branch, if you want the canonical command and intend to keep what it writes.

## The current result

The Phase 2 anchor — the run behind the programme's headline result — is `results/20261104T123839Z/`, cited by
[`current/FINETUNING_PHASE2_OUTCOME.md`](current/FINETUNING_PHASE2_OUTCOME.md). A run directory holds
`capture.json`, the launch manifests and the prediction tables, and [`EVIDENCE_MAP.md`](EVIDENCE_MAP.md) says
what each file claims — `capture.json` is the integrity anchor, because it hashes what was measured. Which run a
report cites is in [`REPORT_REGISTRY.md`](REPORT_REGISTRY.md); a run directory no document cites is not current.

## Before you commit

```bash
./scripts/check.sh            # all eight
./scripts/check.sh ruff       # or one, by name
```

The eight are `ruff`, `pytest`, `shellcheck`, `evidence`, `doclinks`, `docstatus`, `citation` and `verdict`.
`evidence` is the one that surprises people: it refuses a change to `outputs/` or `results/` unless the pull
request is labelled `evidence-change`.

## Where the detail is

[`REPRODUCIBILITY_RUNBOOK.md`](REPRODUCIBILITY_RUNBOOK.md) is 946 lines and opens with a task index. §0 is
setup for all three eras (periods, not environments); §A is the frontier line, §B the 2026-04 legacy line and
§C the rented GPU. The eras are how the programme happened, not something you are expected to know before you
start.
