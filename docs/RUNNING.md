# Running the code — the route in

> This page is for the reader who wants to **run** something. If you want the **answer**, start at
> [`README.md`](../README.md). If you want to check a **number**, start at
> [`EVIDENCE_MAP.md`](EVIDENCE_MAP.md).

## Which environment?

There is **one** environment, and it is the lock: `./scripts/bootstrap_dev.sh` builds `.venv` from
`requirements.lock`, and that single environment covers both lines. It holds `tabpfn 8.5.0` for the fine-tuning
line **and** `tabpfn-client 0.3.3` for the benchmark line, because the lock pins both — the verdicts were
measured against the hosted client and the fine-tuning runs the local package, from one interpreter.

| Environment | Holds | Built by | Used for |
| --- | --- | --- | --- |
| `.venv` | Python 3.12, `tabpfn 8.5.0` **and** `tabpfn-client 0.3.3`, plus the GBDT baselines | `./scripts/bootstrap_dev.sh` | everything in this repository: the tests, the diagnostics, `scripts/eval/`, the repro notebooks, `scripts/run_pilot.py`, `scripts/run_fair_test.py` |

The one exception is external: the four `scripts/benchmarks/run_tabarena_*.py` runners import the third-party
`tabarena` package from a checkout at `/tmp/tabarena` with its own venv. That is optional tooling for the
harness, not a second environment for this repo — nothing here needs it to reproduce a published number.

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
| Reproduce a published number | `.venv` | `jupyter lab notebooks/reproducibility/01_frontier_classification_repro.ipynb`, then run the read-only cells | nothing — they read committed files | §A.7–§A.9 |
| Run a benchmark yourself | `.venv` | `python scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py --seed 7 coil2000` — `coil2000` is a dataset name | `results/<YYYYmmdd-HHMMSS>/` by default; `--save-predictions` adds `predictions/` inside it, and `--out-dir legacy` writes beside the script | §A.3, §A.7 |
| Run the fine-tuning pilot | `.venv` locally, the launcher's own pins when rented | `python scripts/run_pilot.py --dataset coil2000`, or `bash scripts/gpu_helpers/vast_run.sh` | `outputs/finetune/pilot/` run locally; `outputs/gpu-pilot/` when the launcher runs it | §C.2 |

**Start with the notebooks, not the scripts.** Their evidence cells are already executed and read committed
files, so they cost nothing and overwrite nothing. The one exception is the notebook's *preflight* cell, which
imports `tabpfn_client`, `xgboost`, `lightgbm` and `catboost` to prove the stack is installed — all four are in
the lock, so `.venv` satisfies it, and you can skip it if all you want is a table. Only the cells tagged `optional` re-run an experiment, and those spend
credits and overwrite the committed results.

**The frontier runner is destructive by default.** With no arguments it overwrites its own committed CSVs.
Three ways to avoid that, in increasing order of isolation:

- `--seed 7` writes separate `_seed7` files and leaves the canonical `seed 42` results alone.
- `--data <csv> --target <col>` runs an arbitrary CSV and leaves the committed suite untouched.
- a branch, if you want the canonical command and intend to keep what it writes.

## The current result

The Phase 2 anchor — the run behind the programme's headline result — is `results/20261104T123839Z/`. A run
directory holds `capture.json`, the launch manifests and the prediction tables; [`EVIDENCE_MAP.md`](EVIDENCE_MAP.md)
says what each file claims, and `capture.json` is the integrity anchor because it hashes what was measured.

The run ids a current-tier document cites, and that resolve to a capture:

| Run id | What it is | Cited by |
| --- | --- | --- |
| `20261104T123839Z` | Phase 2 anchor — the replication the outcome rests on | `experiments/pilot2-phase2/FINETUNING_PHASE2_OUTCOME.md` |
| `20261031T021845Z` | Anchor power diagnosis (D11) | `experiments/pilot2-phase2/anchor_power_diagnosis.md` |

A bare `YYYYMMDDTHHMMSSZ` id is a citation and must resolve to `results/<id>/capture.json`; an id with a `-`
suffix is a record name and is not scanned. Which run a report cites, and which runs are superseded, is in
[`REPORT_REGISTRY.md`](REPORT_REGISTRY.md) — a run directory no document cites is not current.

## Before you commit

```bash
./scripts/check.sh            # all eight
./scripts/check.sh ruff       # or one, by name
```

The eight are `ruff`, `pytest`, `shellcheck`, `evidence`, `doclinks`, `docstatus`, `citation` and `verdict`.
`evidence` is the one that surprises people: it refuses a change to `outputs/` or `results/` unless the pull
request is labelled `evidence-change`.

## Where the detail is

[`REPRODUCIBILITY_RUNBOOK.md`](REPRODUCIBILITY_RUNBOOK.md) is long and opens with a task index. §0 is setup for
all three eras (periods, not environments); §A is the frontier line, §B the 2026-04 legacy line and §C the rented
GPU. The eras are how the programme happened, not something you are expected to know before you start.

[`DEVELOPMENT_ENVIRONMENT.md`](DEVELOPMENT_ENVIRONMENT.md) is the other half of this page: which checkout you are
in, how the environment is built on this machine, and the failures that look like bugs but are not.
