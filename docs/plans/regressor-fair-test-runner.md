# Plan — the regressor fair-test runner

**Issue:** #539 (contract: #538, delivered; spec: #501 + the 2026-11-10 amendment).
**Status:** Proposed.

## What and why

The contract is settled and the capture can carry everything the pre-registration asks for, but
nothing produces a fair-test run: no code loops over Arms × folds × model seeds, and
`src/run_capture.py` only writes the manifest. This builds that loop, at the sizes the
pre-registration fixes, and stops there — running it is a paid launch and a separate decision.

## Shape

Two modules and one CLI, with the model behind a seam so the matrix is testable without `tabpfn`:

- `src/regression_data.py` — load a target's frame from `data/raw/<dataset>.csv`, apply the drop
  list, encode categoricals, and split into folds. Shared with the benchmark script, which
  currently carries its own copy.
- `src/fair_test_runner.py` — the target/arm declarations, the slot matrix, the per-slot write,
  and the capture at the end.
- `scripts/run_fair_test.py` — the CLI: one run root, one declared configuration.

### The matrix, from the spec

| Target | Dataset | Target column | Drop | Metric | Arms |
|---|---|---|---|---|---|
| claimnb | freMTPL2freq | ClaimNb | IDpol | poisson_deviance | A_raw, B_ft30, B_ft10, B_ft3, X_log1p, S_50k |
| severity | spanish_motor_severity | Cost_claims_year | — | rmse | A_raw, B_ft30, B_ft10, B_ft3, S_50k |
| vehvalue | ausprivauto0405 | VehValue | ClaimOcc, Exposure | rmse | A_raw, B_ft30, B_ft10, B_ft3, S_50k |
| exposure | freMTPL2freq | Exposure | IDpol | rmse | D_exposure |

Folds: `KFold(5, shuffle=True, random_state=42)`. Seeds inside each fold: 0, 1, 2. Test rows: the
fold's rows, sampled to 10,000 with seed 42 — **identical for every Arm and seed of that fold**.
Train rows: the fold's remaining rows, sampled to 10,000 (50,000 for `S_50k`) per Arm and seed.

`X_log1p` fits on `log1p(y)` and **reports predictions on the count scale**: predictions are
back-transformed with `expm1` and clipped at 0 before they are stored or scored, so the count
deviance is computed on counts and the arm is comparable with `A_raw` — the comparison the decision
rule depends on. The record says `reported_scale: "count"`.

`quantiles.npy` stays on the scale the Arm trained on and unclipped, exactly as the 2026-11-10
amendment fixes it; `quantile_scale` records which scale that is, so a reader does not have to
infer it from `transform`.

### What a slot writes

`<run>/<dataset>/<arm>/seed<S>_fold<F>/` with `predictions.npy`, `ground_truth.npy`,
`test_index.npy`, `quantiles.npy`, `exposure.npy` (freMTPL2freq only), and `meta.json` carrying the
four v3 keys the gate requires plus the provenance block (`versions.tabpfn`, `versions.python`,
`weights.path`, `weights.sha256`). Then `build_capture` writes the manifest; the library is not
patched.

## Judgement calls

1. **The split is a function of the fold, not of the Arm.** Every Arm and seed of a fold sees the
   same test rows, and the run refuses if two slots of a fold disagree — the writer already checks
   that, and this makes it reachable rather than theoretical.
2. **Categorical encoding is a column property, not a target property.** Codes come from the whole
   column with a fixed ordering; nothing is fitted on the target, so the encoding cannot leak.
3. **`D_exposure` is raw, not fine-tuned.** The spec calls it a diagnostic and never names training
   for it; costing it as a fine-tune would misdescribe what was run.
4. **The record's verdict value is computed from the predictions this run produced.** That is what
   a record is — the run's own claim — and `rescore` exists to check it against the arrays rather
   than trust it.
5. **No GPU and no rental in this ticket.** The backend is behind a protocol; the tests use a stub;
   one tiny CPU smoke proves the wiring end to end.
6. **One run per target, not one run for the fair test.** A `capture.json` carries exactly one
   dataset (#362), and the fair test spans three. So the runner produces three runs plus the
   exposure diagnostic, each with a bare-timestamp run id — a suffixed directory would be read by
   the citation check as a run id that does not exist. The pre-registration already *proposes* three
   pilot experiments in its registry section; that block is proposal, not a declaration in
   `experiments.toml`, so the split is a choice this ticket makes and records.
7. **`S_50k` is 50,000 rows where the fold has them.** Severity's fold pool is 42,801 rows, so the
   arm runs on all of them and the record states the `train_rows` that ran; the name keeps the
   spec's label and the record keeps it honest.

## Verification

- `pytest tests/test_fair_test_runner.py tests/test_regression_data.py -q` — matrix counts, identical
  test rows, the capture round-trip through `read_run`, the four record keys, provenance present.
- One CPU smoke at tiny sizes (1 fold, 1 seed, 2 epochs, 128 rows), all targets: **1 min 43 s**,
  four runs (three targets plus the exposure diagnostic), each a v3 capture `read_run` accepts —
  quantiles `(9, 64)`, `test_index` holding raw CSV rows, the four record keys, the split block and
  the dataset fingerprint. The record's `weights.sha256` begins `311ce18d97e9`, the checkpoint the
  pre-registration pins, which is the check that the hash is of the weights that ran.
  CPU time says nothing about GPU cost.
- `./scripts/check.sh` — the eight checks.
