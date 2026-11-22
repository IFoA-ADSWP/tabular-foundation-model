# Zero Inflation

> **Status:** index — this campaign's reading order, not a report of its own.

Does TabPFN handle zero-inflated, overdispersed counts without being told? A synthetic study, issue #159
question 1: TabPFN `v3.5_default` against Poisson, ZIP and ZINB GLMs on mean-matched zero-inflated NB2
counts, π₀ swept 0 → 0.95 at three dispersion levels (α = 1, 2, 4), 10 seeds each.

**1 document.**

| Document | Status | What it holds |
| --- | --- | --- |
| [`ZERO_INFLATION_TABPFN.md`](ZERO_INFLATION_TABPFN.md) | current as of 2026-10-04 | Does TabPFN Handle Zero-Inflation? — the question, the design, the result |

The plan that placed this campaign on the current layout is
[`159-zero-inflation-port.md`](../../plans/159-zero-inflation-port.md). The hurdle extension — hurdle GLMs and
two-stage TabPFN, code only so far, no run and no result — is
[`159-zero-inflation-hurdle.md`](../../plans/159-zero-inflation-hurdle.md).

## Evidence

No run under `results/`. Like the rest of the benchmark line, the study keeps its committed CSVs beside its
runner, in `scripts/eval/zero_inflation/`:

- `results/alpha_1.0/`, `results/alpha_2.0/`, `results/alpha_4.0/` — one `results.csv` per α (650 scored rows
  each) with its diagnostic plots; all TabPFN rows `v3.5_default`.
- `results/alpha_1.0_v3/` — the superseded first α = 1.0 run, whose TabPFN rows came from v3; kept as the
  evidence for the report's version caveat.
- `figures/` — the report's four charts, and `manifest.json` with the producing commit and a sha256 per
  source script and results file. The script hashes match the versions at commit `ee73792` (PR #189's
  branch), not the current files: the hurdle extension edited `dgp.py`, `models.py` and `run_sweep.py`. It
  left the five original models' outputs unchanged — the current code reproduces their committed rows
  exactly (`check_reproducible.py`, and the check recorded in the hurdle plan) — but a byte-for-byte
  provenance check of the figures needs `ee73792`. The results hashes still match.

The cross-α analysis behind the numbers quoted in the report is the notebook
`notebooks/zero_inflation/zero_inflation_dispersion.ipynb`. It reads only the committed CSVs and spends nothing.
