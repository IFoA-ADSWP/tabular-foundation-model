# Plan — the benchmark fit that sizes the fair test's spend

**Issue:** #526 (precondition 2 of the fair test; spec #501).
**Status:** Proposed.

## What and why

The pre-registration says the fair test is funded only if a measured benchmark sits inside the \$50
ceiling. Today that number does not exist: the cost page's anchors are the classifier pilot's, and
the regressor at 10,000 rows has never been timed. Without a measurement the ceiling is a guess, and
the spend ask is open-ended.

This builds the harness. **It does not authorise the spend.** The measurement mode rents a GPU and
is released separately; the estimate mode is free and is worthless until a measurement exists.

## Shape

Two pieces, split at a seam the tests can hold:

- `src/benchmark_cost.py` — the cost model only. A declared fit matrix, epoch/row scaling, the
  ceiling rule, and the JSON record. No `tabpfn`, no GPU, importable in CI.
- `scripts/benchmarks/benchmark_regressor_fit.py` — the CLI. `--measure` runs one fine-tune at
  10,000 rows × 30 epochs and writes a measurement record; `--estimate` turns that record into the
  full matrix and a dollars figure at a stated rate.

### The matrix

Fixed from the spec, with every assumption written into the output rather than implied:

| Arm | Targets | Folds | Seeds | Rows | Epochs |
|---|---|---|---|---|---|
| `A_raw` | 3 | 5 | 3 | 10,000 | in-context |
| `B_ft30` | 3 | 5 | 3 | 10,000 | 30 |
| `B_ft10` | 3 | 5 | 3 | 10,000 | 10 |
| `B_ft3` | 3 | 5 | 3 | 10,000 | 3 |
| `X_log1p` | 1 (ClaimNb) | 5 | 3 | 10,000 | 30 |
| `S_50k` | 3 | 5 | 3 | 50,000 | 30 |
| `D_exposure` | 1 (ClaimNb) | 5 | 3 | 10,000 | 30 |

That is 45 fits for each full-target arm and 15 for each single-target arm — 210 fine-tunes plus 45
in-context fits, 255 fits in total.

### Scaling, stated rather than hidden

The benchmark measures one point (10,000 rows, 30 epochs). The model separates a fixed share from a
per-epoch share:

```
seconds(fit) = fixed·measured + (1−fixed)·measured·(epochs/30)·(rows/10,000)
```

`fixed` defaults to 0.2: a three-epoch fit is costed at 28% of a thirty-epoch fit, not 10%, because
model load and inference do not scale with epochs. Linear row scaling is conservative — inference
context cost grows sublinearly in practice.

`A_raw` is costed at the **full** measured fine-tune rate. In-context inference is cheaper per row
than 30 epochs of training, so this over-estimates it: the upper bound is the safe direction.

Cold-start overhead (\$0.05 per cold attempt, from the cost page's measurement) is a separate line,
included in the total and reported apart from the science.

## Judgement calls

1. **No modelled default is allowed.** `--estimate` refuses without `--measurement`. A number that
   looks measured but is not is exactly the failure the cost page warns about ("measured or modelled,
   never implied").
2. **The epoch overhead is a stated assumption, not a measurement.** The spec asks for one fit at 30
   epochs; measuring a second at 3 epochs would buy a better curve for a few minutes of GPU, but it
   changes what was pre-registered. The assumption is printed with the estimate so a reader can
   re-derive it.
3. **`S_50k` is costed on all three targets.** The spec does not name the target(s) for the 50k
   sensitivity. Costing all three over-estimates; the output labels it as an assumption and the
   matrix is data, so narrowing it is a one-line change if the team decides otherwise.
4. **The ceiling is a parameter, not a constant.** Default \$50 (the spec), overridable, but the
   record always states which ceiling was applied.

## Verification

- `pytest tests/test_benchmark_cost.py -q` — matrix counts, epoch and row scaling, raw costing,
  the ceiling refusal, the estimate-without-measurement refusal, JSON round-trip.
- `ruff check scripts/ src/ tests/`.
- `./scripts/check.sh` — the eight-check gate.
- A dry run of `--estimate` over a synthetic measurement is **not** committed as evidence: only a
  real measurement may produce a number anyone quotes.
