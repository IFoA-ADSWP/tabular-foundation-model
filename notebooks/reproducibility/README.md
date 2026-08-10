# Reproducibility notebooks — the exact code behind the master report

Colleagues can see precisely what was run for each experiment, re-run it, and inspect the
evidence — without reimplementing anything. Each notebook calls the **exact script** that
produced the committed results (no forked code that can drift), then renders the evidence CSVs.

**All three notebooks ship with their evidence cells already executed** — every table and plot
you see as a cell output *is* the committed canonical result. You can follow the whole experiment
by reading the outputs alone, or re-run any cell: every non-optional cell reads only committed
files and reproduces its display instantly (no credits, no overwrites). The cells tagged
**`optional`** are the hosted-API "run the experiment" cells (plus 02's paired-stats layer) —
they are left unexecuted and are the only ones that cost money / minutes-to-hours and can
overwrite or append to the committed files (see the per-notebook warnings below).

| Notebook | Reproduces | Cost | Overwrites canonical files? |
|---|---|---|---|
| `01_frontier_classification_repro.ipynb` | Master report §14.11 — frontier benchmark, 9 methods × 5 folds × seed 42 on `coil2000` (log loss / AUC / Brier / PR-AUC / lift + D3 frontier) | ~minutes | ⚠ Yes — `frontier_results_coil2000.csv` + plot (use `--seed 7` for non-destructive runs) |
| `02_reframe_frequency_repro.ipynb` | §14.14 (issue #67) — Spanish motor counts as binary (seeds 42/7) + ordinal (seed 42) classification | 20–60 min (hosted API) | ⚠ Yes — `reframe_frequency_results.csv` (+ summary CSV if analysis cell runs) |
| `03_tuned_baselines_repro.ipynb` | §14.13 — finality test: 5 tuned/engineered baselines on the canonical folds (14 methods total) | **Tens of minutes per dataset**; full suite = hours | ⚠ Appends — duplicates accumulate in `frontier_tuned_baseline_results.csv` |

## Setup (once)

1. **Kernel:** these scripts run in the benchmark venv (Python 3.12, tabpfn-client 0.3.3 — the
   version every verdict is stamped to). Make it available to Jupyter:

   ```bash
   source /tmp/tabarena/.venv-ta/bin/activate
   pip install ipykernel
   python -m ipykernel install --user --name tabarena-ta
   ```

   For running the notebooks locally, the venv needs Jupyter's execution stack:
   `pip install jupyter ipykernel` (brings nbclient/nbconvert/nbformat). The repo-local
   `.venv-ta` is the venv that produced the committed outputs and is already set up this way.

   (If you built a fresh environment, pin `tabpfn-client` to 0.3.3 and re-read master-report §15
   before trusting comparisons — verdicts are version-sensitive.)

2. **Auth — browser login (easiest):** run the preflight cell of any repro notebook. It
   detects that no `TABPFN_API_KEY` is configured, opens the Prior Labs login page in your
   browser, and after sign-in saves the token to the repo-root `.env` (gitignored — no
   secrets in git) and exports it for the session. The scripts then pick it up via their
   usual env/`.env` lookup. Alternatively set `TABPFN_API_KEY` as an environment variable
   or in `.env` manually (scripts fail with a clear error if neither exists).

3. Launch Jupyter **from anywhere** — the notebooks locate the repo root themselves.

## Ground rules for re-runs

- **Seed 42 = canonical.** Re-running it overwrites committed evidence. Prefer `--seed 7`
  (writes `_seed7` files) or copy the CSVs aside first. Seed variation is itself part of the
  protocol (§14.12: seeds 7/42/123).
- **Version honesty:** record the `tabpfn_client` version the preflight cell prints (the client may
  not expose `__version__`) — the §15 re-test policy exists because results are stamped to
  `v3_default` / 0.3.3.
- **Full-suite scale-ups** are described in each notebook's final markdown cell.

## Where the evidence lands

- `scripts/eval/insurance_benchmark_v1/frontier_results_*.csv` (+ plots) — §14.11
- `scripts/eval/insurance_benchmark_v1/reframe_frequency_results.csv` / `_summary.csv` — §14.14
- `scripts/eval/insurance_benchmark_v1/frontier_tuned_baseline_results.csv` — §14.13

Context: master report `docs/analyses/tabpfn_vs_gbdt_baselines_finetuning.md`, digest
`docs/MASTER-REPORT-DIGEST.md`, knowledge path `docs/KNOWLEDGE-PATH.md` (Stage 4.5).
