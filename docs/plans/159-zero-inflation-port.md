# Plan — the zero-inflation study lands on the current layout (#159)

**Issue:** #159 (question 1, zero inflation). Supersedes the unmerged branch of PR #189.
**Status:** Current.

## What and why

The zero-inflation study — TabPFN `v3.5_default` against Poisson, ZIP and ZINB GLMs on synthetic
zero-inflated NB2 counts at three dispersion levels — was written on `feat/issue-159-zero-inflation`
(commit `ee73792`, 2026-09-17) and never merged. Since then `main` reorganised its documentation by
experiment (#595): `docs/current/` no longer exists, every report lives in a campaign directory under
`docs/experiments/<campaign>/` with a README index, and `notebooks/baseline_experiments/` is the
legacy v2 notebook era. The branch cannot be merged as it stands, and its notebook on its own cannot
run, because the results it reads are on the branch only.

This change carries the study over unchanged in substance and placed where the current layout puts it.
No run is repeated and no number changes.

## Where each piece goes

| Piece | Branch path | New path | Why |
| --- | --- | --- | --- |
| Code, results CSVs, figures, manifest | `scripts/eval/zero_inflation/` | unchanged | the benchmark line keeps its committed CSVs beside its runner in `scripts/eval/` (`EXPERIMENTS.md`, "Where the evidence is"); the figure manifest hashes these exact paths |
| Report | `docs/current/ZERO_INFLATION_TABPFN.md` | `docs/experiments/zero-inflation/ZERO_INFLATION_TABPFN.md` | a campaign directory, with its own README |
| Notebook | `notebooks/baseline_experiments/09_zero_inflation_dispersion.ipynb` | `notebooks/zero_inflation/zero_inflation_dispersion.ipynb` | `baseline_experiments/` is the v2 era; a v3.5 notebook there would mix version eras |

The notebook's results path now resolves from the repository root rather than from a fixed `../../`,
so it runs from wherever Jupyter is started. Its prose names the new report and its own new location.

## Indexes updated

`EXPERIMENTS.md` (a new campaign row), `REPORT_REGISTRY.md`, `MODEL_VERSIONS.md` (the 2026-09-17 v3.5
row for this study), `docs/plans/README.md`, `scripts/README.md`, the root `README.md` notebook list and
`CHANGELOG.md`.

## Not changed

- `requirements.txt` / `requirements.lock`. The branch added `statsmodels` to the ranges; the lock is
  now the authority, and the sweep needs `tabpfn-client` 0.5.3 for `v3.5_default` while the lock pins
  0.3.3. Re-running the sweep therefore needs its own environment, as the other v3.5 re-tests did;
  `scripts/README.md` says so. The analysis notebook and the chart script need only pandas and
  matplotlib, which the lock has.
- `outputs/` and `results/` — untouched; the study's evidence is under `scripts/eval/`.

## Verification

- The three `results.csv` files hash to the values in `figures/manifest.json` (checked before porting).
- The notebook executes end to end in `.venv` from its new location.
- `./scripts/check.sh` — all eight checks. Run locally: ruff, pytest, evidence, doclinks, docstatus,
  citation and verdict pass; shellcheck is not installed on this machine and no shell script is touched,
  so it is left to CI.
