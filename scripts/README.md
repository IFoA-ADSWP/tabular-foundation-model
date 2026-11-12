# Scripts

One-off experiment scripts, infrastructure and debug tools. Read this before `ls`-ing the directory: the
tree is organised by **what a script is for**, not by when it was written, and two of the directories hold
most of the weight.

**If you are new, start with [`docs/RUNNING.md`](../docs/RUNNING.md)** — it says which environment and which
route. This page is the index of the tree itself.

## Start here by task

| I want to… | Go to |
| --- | --- |
| Run the tests, or the gate | [`../scripts/check.sh`](check.sh), [`bootstrap_dev.sh`](bootstrap_dev.sh) |
| Run the current fine-tuning experiment | [`run_pilot.py`](run_pilot.py) locally, [`gpu_helpers/`](gpu_helpers/) when rented |
| Run the regressor fair test | [`run_fair_test.py`](run_fair_test.py) |
| Run a published benchmark | [`eval/`](eval/) — the frontier, lapse and imbalance suites |
| Run a diagnostic | [`diagnostics/`](diagnostics/) — D1, D2, D3, D5 |
| Build, rescore or check a capture | [`analyses/`](analyses/) |
| Work on a dataset or the wiki | [`infra/`](infra/) |

## The root entry points

| Script | Purpose |
| --- | --- |
| `run_pilot.py` | The fine-tuning pilot: arms, rungs, seeds and folds against the four anchor datasets. Writes a schema-v2 record with dataset and split fingerprints. Runbook §C.2. |
| `run_fair_test.py` | The regressor fair test — four pre-registered frequency/severity targets, policy-grouped folds, capture v4. `--smoke` proves the wiring on CPU and is never a result to quote. Rents nothing by itself. |
| `check.sh` | **The single definition of this repository's checks.** `./scripts/check.sh` runs all eight; `./scripts/check.sh ruff` runs one. CI calls this script per job rather than restating a command. |
| `bootstrap_dev.sh` | Builds `.venv` from `requirements.lock` and asserts the pins (#530). The canonical first command. |
| `new_worktree.sh` | Creates a worktree that actually contains the repository, and removes its own leftovers if the check fails. |
| `check_citations.py` | A bare run id in `docs/` must resolve to `results/<id>/capture.json` with hashes. Run as `./scripts/check.sh citation`. |
| `check_doc_links.py` | Every reference under `docs/` resolves. `plans/` and `archive/` are citations and are skipped. |
| `check_doc_status.py` | Every report in the three tiers states what it is in its first fifteen lines; also enforces the findings registry's shape. |
| `diagnostic_complexity.py`, `analyse_pilot.py` | One-off analysis helpers; see their own docstrings. |

## Subdirectories

| Directory | Files | What lives there |
| --- | --- | --- |
| `eval/` | 106 | The benchmark suites: `insurance_benchmark_v1/` (frontier D1–D5), `lapse_benchmark_v1/`, `insurance_imbalance_pilot/`, `smoke_test/`. Each holds committed result CSVs and logs beside its runners. Hosted client, `tabpfn-client 0.3.3`. |
| `gpu_helpers/` | 18 | **The paid-run path.** `vast_run.sh` rents, bootstraps, polls, pulls and destroys; `bootstrap_pilot.sh` is the on-box installer; `verify_artifacts.py` refuses a run that measured nothing. Shell-checked at `warning` in CI because a syntax error here costs money. |
| `legacy_finetuning/` | 17 | The v2-era fine-tuning line, 2026-04. **Provenance, not canonical**: these do not run on `tabpfn 8.5.0`, whose `finetune_utils` and `get_preprocessed_datasets` were removed. |
| `benchmarks/` | 8 | TabArena-harness runners: the 7-dataset insurance benchmark, the lapse and imbalance pilots, the home-turf size sweep, the regressor-fit measurement. |
| `analyses/` | 7 | Capture and analysis tooling: `make_capture.py`, `rescore.py`, `verdict.py`, `freq_sev_*`, `proxy_resolution.py`. `verdict.py` reproduces the null band the decision log cites (#398). |
| `diagnostics/` | 5 | D1 profiling, D2 importance, D3 reframe, D5 eudirectlapse, and `export_records.py`, which writes the committed table under `docs/analyses/data/`. |
| `infra/` | 7 | Dataset preparation (`prepare_insurance_datasets.py`, `download_datasets.py`) and the wiki push. |
| `colab_helpers/` | 3 | Superseded R1 launcher path, kept for provenance. |
| `git-hooks/` | 1 | `pre-commit.local`. |

## Conventions

- A script that writes evidence writes it under `outputs/` (git-ignored, runtime) or `results/<run id>/`
  (committed, and a citation). `./scripts/check.sh evidence` refuses a change to either without the
  `evidence-change` label.
- A new top-level script is a new entry point: add it to the table above in the same change.
- Version era is load-bearing. A number is only meaningful against the environment it was measured in — see
  [`docs/MODEL_VERSIONS.md`](../docs/MODEL_VERSIONS.md).
