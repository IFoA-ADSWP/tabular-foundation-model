# Runs ledger — every committed fine-tuning and fair-test run, classification and regression

> **Status:** current — generated ledger, 2026-11-20. **Generated, not written:** rebuild it
> with `python scripts/analyses/finetuning_runs_ledger.py`; a hand edit is overwritten and a
> number typed here is a number with no evidence behind it.

**Question.** What did the programme run, and what did it score — for lapse classification and
for frequency/severity regression? One row per run × arm × seed (classification) or
run × arm × seed × fold (regression), and a descriptive summary per task underneath. This is a
reference, not a new verdict: it re-runs nothing, adds no interval, and changes no claim.

**Provenance.** Built for the map's ledger tickets (#663 → #665 → #668). The classification
fields and traps are the research note's (#664); the regression records add `task`, `fold`,
`n_folds` and a verdict metric. Every row states its problem type, task and era, so a
classification AUC and a regression RMSE cannot be read as the same kind of number.

**Machine form.** [`finetuning_runs_ledger.csv`](../../analyses/data/finetuning_runs_ledger.csv)
carries the same rows, one line each, with the full source pointer. The tables below are
rendered from it, so they cannot disagree with it.

**Rows.** 1082 (602 classification, 480 regression) across 7 experiment families: `pilot2-phase2` 580; `r1-pilot` 16; `gpu-pilot` 4; `pilot2-breadth-spanish` 2; `fair-test-freq-sev` 120; `actuarial-baseline-full` 180; `actuarial-baseline-matched` 180. Statuses present: `current`, `no-capture`, `superseded`.

## Sources, and what each one is

| family | problem type | rows | statuses | read from |
| --- | --- | --- | --- | --- |
| `pilot2-phase2` | classification | 580 | current 580 | `results/<run>/<dataset>/<arm>/seed<N>_foldNone/meta.json` |
| `r1-pilot` | classification | 16 | current 12, superseded 4 | `outputs/finetune/pilot/pilot_metrics.parquet` |
| `gpu-pilot` | classification | 4 | no-capture 4 | `outputs/gpu-pilot/runs/<run>/<dataset>/<arm>/meta.json` |
| `pilot2-breadth-spanish` | classification | 2 | no-capture 2 | `docs/experiments/pilot2-phase2/finetuning_breadth_spanish_result.md` |
| `fair-test-freq-sev` | regression | 120 | current 120 | `results/<run>/<dataset>/<arm>/seed<N>_fold<K>/meta.json` |
| `actuarial-baseline-full` | regression | 180 | current 180 | `results/<run>/<dataset>/<arm>/seed<N>_fold<K>/meta.json` |
| `actuarial-baseline-matched` | regression | 180 | current 180 | `results/<run>/<dataset>/<arm>/seed<N>_fold<K>/meta.json` |

Each family is read from the place the table names, and selected by **campaign membership and
dataset**, never by "has an `ft` arm": the fair test, the baselines and the pilot all carry
the same `A_raw` / `B_ft30` labels. In short:

- `pilot2-phase2` — the Run directories this campaign's own `Runs` block names, each with a `capture.json`.
- `r1-pilot` — the 2,000-row R1 pilot aggregate, one seed (42), no Capture.
- `gpu-pilot` — committed launch records with no `capture.json`.
- `pilot2-breadth-spanish` — one curated cell whose per-seed records were never committed.
- `fair-test-freq-sev` — the four registered fair-test targets, policy-grouped folds; the #572 row-scaling runs `20261113T003320Z` and `20261113T095502Z` belong to the same campaign and are reported by the fair-test result, not this ledger.
- `actuarial-baseline-full` — the registered primary baseline arm, trained on the whole fold pool.
- `actuarial-baseline-matched` — the registered 10,000-row baseline sensitivity arm; on `spanish_motor_severity` the two arms are the same fit, captured under both run ids.

## What each dataset is, and which task it serves

The gap a reader hit: a row's dataset did not say whether it was a lapse classifier or a
frequency/severity regressor, or what the data was. The dataset, task and problem type are
read from the CSV; the description is curated from the campaigns' own target tables.

| dataset | task | problem type | eligible rows | unit | what it is | campaigns |
| --- | --- | --- | --- | --- | --- | --- |
| coil2000 | lapse | classification | 9,822 | policy | CoIL 2000: caravan-policy purchase (5.97% positive, NL) | `r1-pilot` |
| eudirectlapse | lapse | classification | 23,060 | policy | EU direct motor: policy lapse (12.81% positive) — the known TabPFN exception | `pilot2-phase2`, `r1-pilot` |
| freMTPL2freq | frequency | regression | 678,013 | policy | French motor third-party liability: claims per policy (`ClaimNb`, unit policy) | `fair-test-freq-sev`, `actuarial-baseline-full`, `actuarial-baseline-matched` |
| freMTPL2sev | severity | regression | 26,444 | claim — the 26,444 claims sit on 24,944 policies | French motor third-party liability: claim amount per claim (`ClaimAmount`, on the log scale; unweighted RMSE, weight exactly 1) | `fair-test-freq-sev`, `actuarial-baseline-full`, `actuarial-baseline-matched` |
| spanish_motor_freq | frequency | regression | 53,502 | policy | Spanish motor: claims per policy year (`N_claims_year`, unit policy) | `fair-test-freq-sev`, `actuarial-baseline-full`, `actuarial-baseline-matched` |
| spanish_motor_lapse | lapse | classification | 53,502 | policy | Spanish motor: policy lapse | `r1-pilot`, `pilot2-breadth-spanish` |
| spanish_motor_severity | severity | regression | 5,950 | claiming policy — 11,167 claim-equivalents carry the claim weight | Spanish motor: cost per claim, weighted by the claim count (`Cost_claims_year / N_claims_year`, log scale) | `fair-test-freq-sev`, `actuarial-baseline-full`, `actuarial-baseline-matched` |
| uslapseagent | lapse | classification | 29,317 | policy | US lapse agent: policy surrender (37.9% positive) | `pilot2-phase2`, `r1-pilot`, `gpu-pilot` |

**The eligible-row count is curated from the pre-registrations' own dataset tables**, not
derived from the captures: a capture covers the arms that ran, not the prepared dataset that
existed. Each count's source is the dataset table in
`FINETUNING_EXPERIMENT_REFERENCE.md` (the lapse datasets), `regime_characterization.md`
(Spanish motor) or
`REGRESSOR_FINETUNING_PREREGISTRATION_FREQ_SEV_2026-11.md` (frequency and severity), and the
unit is the one the ledger's `train_rows` is counted in. The share is **per row**, not per
dataset: `train_rows / eligible_rows`, because `freMTPL2freq` carries a 10,000-row TabPFN line
and a 542,410-row full-pool baseline, and one share for the dataset would be wrong for one of
them.

## The ledger

One row per run × arm × seed, or per run × arm × seed × fold where the evidence has folds.
`epochs` is blank where no epoch applies (the comparator Methods) and where the source records
no arm-level epoch count (the 2,000-row pilot) or no record at all (the curated Spanish cell);
`epochs = 0` on a regression raw control is a recorded count, not a blank. `train_rows` and
`fold` are part of the key: `uslapseagent` seed 42 exists at 2,000 and at 10,000 rows, and a
five-fold regression cell is five measurements. `eligible_rows` is the dataset's curated
prepared size in the row's own unit, and `share_of_eligible` is `train_rows / eligible_rows`,
computed per row. A blank `train_rows` gives a blank share — the curated Spanish `no-capture`
cell — while its `eligible_rows` still states the dataset's size, which does not depend on
whether a capture exists.

| run id | family | type | task | era | dataset | arm | arm kind | epochs | seed | fold | train rows | eligible rows | share of eligible | ROC AUC | Brier | PR-AUC | RMSE | verdict metric | verdict value | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `20261104T234013Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 93 | — | 10,000 | 23,060 | 0.4337 | 0.614912 | 0.110327 | 0.176254 | — | — | — | current |
| `20261104T234013Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 94 | — | 10,000 | 23,060 | 0.4337 | 0.665397 | 0.107603 | 0.274502 | — | — | — | current |
| `20261104T234013Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 95 | — | 10,000 | 23,060 | 0.4337 | 0.651636 | 0.108556 | 0.213301 | — | — | — | current |
| `20261104T234013Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 96 | — | 10,000 | 23,060 | 0.4337 | 0.620252 | 0.109894 | 0.198503 | — | — | — | current |
| `20261104T234013Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 97 | — | 10,000 | 23,060 | 0.4337 | 0.626532 | 0.109945 | 0.186384 | — | — | — | current |
| `20261104T234013Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 98 | — | 10,000 | 23,060 | 0.4337 | 0.640741 | 0.109073 | 0.209708 | — | — | — | current |
| `20261104T234013Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 99 | — | 10,000 | 23,060 | 0.4337 | 0.621327 | 0.110018 | 0.180978 | — | — | — | current |
| `20261104T234013Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 100 | — | 10,000 | 23,060 | 0.4337 | 0.632418 | 0.109153 | 0.221063 | — | — | — | current |
| `20261104T234013Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 101 | — | 10,000 | 23,060 | 0.4337 | 0.586045 | 0.110965 | 0.173167 | — | — | — | current |
| `20261104T234013Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 102 | — | 10,000 | 23,060 | 0.4337 | 0.619150 | 0.109435 | 0.213613 | — | — | — | current |
| `20261104T234013Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 103 | — | 10,000 | 23,060 | 0.4337 | 0.585104 | 0.111088 | 0.164391 | — | — | — | current |
| `20261104T234013Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 104 | — | 10,000 | 23,060 | 0.4337 | 0.678129 | 0.107620 | 0.231122 | — | — | — | current |
| `20261105T001837Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 105 | — | 10,000 | 23,060 | 0.4337 | 0.638036 | 0.109441 | 0.196240 | — | — | — | current |
| `20261105T001837Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 106 | — | 10,000 | 23,060 | 0.4337 | 0.599305 | 0.110798 | 0.181867 | — | — | — | current |
| `20261105T001837Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 107 | — | 10,000 | 23,060 | 0.4337 | 0.635133 | 0.109359 | 0.193670 | — | — | — | current |
| `20261105T001837Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 108 | — | 10,000 | 23,060 | 0.4337 | 0.647380 | 0.108366 | 0.228412 | — | — | — | current |
| `20261105T001837Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 109 | — | 10,000 | 23,060 | 0.4337 | 0.604358 | 0.110208 | 0.182119 | — | — | — | current |
| `20261105T001837Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 110 | — | 10,000 | 23,060 | 0.4337 | 0.665200 | 0.107898 | 0.234811 | — | — | — | current |
| `20261105T001837Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 111 | — | 10,000 | 23,060 | 0.4337 | 0.610755 | 0.110441 | 0.180162 | — | — | — | current |
| `20261105T001837Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 112 | — | 10,000 | 23,060 | 0.4337 | 0.609895 | 0.109754 | 0.196352 | — | — | — | current |
| `20261105T001837Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 113 | — | 10,000 | 23,060 | 0.4337 | 0.633798 | 0.109335 | 0.199937 | — | — | — | current |
| `20261105T001837Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 114 | — | 10,000 | 23,060 | 0.4337 | 0.627303 | 0.109317 | 0.201137 | — | — | — | current |
| `20261105T001837Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 115 | — | 10,000 | 23,060 | 0.4337 | 0.583599 | 0.111107 | 0.170332 | — | — | — | current |
| `20261105T001837Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 116 | — | 10,000 | 23,060 | 0.4337 | 0.641888 | 0.108431 | 0.223888 | — | — | — | current |
| `20261104T234127Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 117 | — | 10,000 | 23,060 | 0.4337 | 0.637032 | 0.108987 | 0.213707 | — | — | — | current |
| `20261104T234127Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 118 | — | 10,000 | 23,060 | 0.4337 | 0.631298 | 0.108674 | 0.225690 | — | — | — | current |
| `20261104T234127Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 119 | — | 10,000 | 23,060 | 0.4337 | 0.615181 | 0.109894 | 0.191712 | — | — | — | current |
| `20261104T234127Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 120 | — | 10,000 | 23,060 | 0.4337 | 0.581055 | 0.111638 | 0.163847 | — | — | — | current |
| `20261104T234127Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 121 | — | 10,000 | 23,060 | 0.4337 | 0.626227 | 0.108907 | 0.235759 | — | — | — | current |
| `20261104T234127Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 122 | — | 10,000 | 23,060 | 0.4337 | 0.614992 | 0.109424 | 0.210623 | — | — | — | current |
| `20261104T234127Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 123 | — | 10,000 | 23,060 | 0.4337 | 0.650579 | 0.108177 | 0.246998 | — | — | — | current |
| `20261104T234127Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 124 | — | 10,000 | 23,060 | 0.4337 | 0.642130 | 0.108572 | 0.223226 | — | — | — | current |
| `20261104T234127Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 125 | — | 10,000 | 23,060 | 0.4337 | 0.588930 | 0.111351 | 0.172048 | — | — | — | current |
| `20261104T234127Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 126 | — | 10,000 | 23,060 | 0.4337 | 0.650140 | 0.108995 | 0.195561 | — | — | — | current |
| `20261104T234127Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 127 | — | 10,000 | 23,060 | 0.4337 | 0.603363 | 0.110454 | 0.179259 | — | — | — | current |
| `20261104T234127Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 128 | — | 10,000 | 23,060 | 0.4337 | 0.616641 | 0.109900 | 0.199487 | — | — | — | current |
| `20261104T234132Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 129 | — | 10,000 | 23,060 | 0.4337 | 0.609698 | 0.110034 | 0.189633 | — | — | — | current |
| `20261104T234132Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 130 | — | 10,000 | 23,060 | 0.4337 | 0.652424 | 0.108790 | 0.208795 | — | — | — | current |
| `20261104T234132Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 131 | — | 10,000 | 23,060 | 0.4337 | 0.634613 | 0.109521 | 0.192067 | — | — | — | current |
| `20261104T234132Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 132 | — | 10,000 | 23,060 | 0.4337 | 0.639156 | 0.109223 | 0.196940 | — | — | — | current |
| `20261104T234132Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 133 | — | 10,000 | 23,060 | 0.4337 | 0.666356 | 0.107680 | 0.233156 | — | — | — | current |
| `20261104T234132Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 134 | — | 10,000 | 23,060 | 0.4337 | 0.618191 | 0.109802 | 0.195782 | — | — | — | current |
| `20261104T234132Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 135 | — | 10,000 | 23,060 | 0.4337 | 0.645015 | 0.108720 | 0.212990 | — | — | — | current |
| `20261104T234132Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 136 | — | 10,000 | 23,060 | 0.4337 | 0.632562 | 0.109204 | 0.212837 | — | — | — | current |
| `20261104T234132Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 137 | — | 10,000 | 23,060 | 0.4337 | 0.596402 | 0.110662 | 0.184858 | — | — | — | current |
| `20261104T234132Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 138 | — | 10,000 | 23,060 | 0.4337 | 0.621398 | 0.109868 | 0.195347 | — | — | — | current |
| `20261104T234132Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 139 | — | 10,000 | 23,060 | 0.4337 | 0.598579 | 0.111081 | 0.175819 | — | — | — | current |
| `20261104T234132Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 140 | — | 10,000 | 23,060 | 0.4337 | 0.667521 | 0.108524 | 0.213989 | — | — | — | current |
| `20261105T100533Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 141 | — | 10,000 | 23,060 | 0.4337 | 0.633682 | 0.108719 | 0.223792 | — | — | — | current |
| `20261105T100533Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 142 | — | 10,000 | 23,060 | 0.4337 | 0.545200 | 0.112782 | 0.150006 | — | — | — | current |
| `20261105T100533Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 143 | — | 10,000 | 23,060 | 0.4337 | 0.636952 | 0.109532 | 0.197848 | — | — | — | current |
| `20261105T100533Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 144 | — | 10,000 | 23,060 | 0.4337 | 0.621210 | 0.110054 | 0.179362 | — | — | — | current |
| `20261105T100533Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 145 | — | 10,000 | 23,060 | 0.4337 | 0.648975 | 0.108118 | 0.231747 | — | — | — | current |
| `20261105T100533Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 146 | — | 10,000 | 23,060 | 0.4337 | 0.608004 | 0.109808 | 0.207101 | — | — | — | current |
| `20261105T100533Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 147 | — | 10,000 | 23,060 | 0.4337 | 0.611534 | 0.110026 | 0.186190 | — | — | — | current |
| `20261105T100533Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 148 | — | 10,000 | 23,060 | 0.4337 | 0.611024 | 0.109983 | 0.198530 | — | — | — | current |
| `20261105T100533Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 149 | — | 10,000 | 23,060 | 0.4337 | 0.606777 | 0.109889 | 0.202874 | — | — | — | current |
| `20261105T100533Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 150 | — | 10,000 | 23,060 | 0.4337 | 0.623593 | 0.110285 | 0.179105 | — | — | — | current |
| `20261105T100533Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 151 | — | 10,000 | 23,060 | 0.4337 | 0.599152 | 0.110816 | 0.177597 | — | — | — | current |
| `20261105T100533Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 152 | — | 10,000 | 23,060 | 0.4337 | 0.614679 | 0.110135 | 0.187678 | — | — | — | current |
| `20261105T005435Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 153 | — | 10,000 | 23,060 | 0.4337 | 0.640697 | 0.108537 | 0.240017 | — | — | — | current |
| `20261105T005435Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 154 | — | 10,000 | 23,060 | 0.4337 | 0.651887 | 0.108301 | 0.224039 | — | — | — | current |
| `20261105T005435Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 155 | — | 10,000 | 23,060 | 0.4337 | 0.601186 | 0.110620 | 0.181770 | — | — | — | current |
| `20261105T005435Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 156 | — | 10,000 | 23,060 | 0.4337 | 0.609536 | 0.110247 | 0.194056 | — | — | — | current |
| `20261105T005435Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 157 | — | 10,000 | 23,060 | 0.4337 | 0.657701 | 0.108132 | 0.225325 | — | — | — | current |
| `20261105T005435Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 158 | — | 10,000 | 23,060 | 0.4337 | 0.604851 | 0.109920 | 0.205454 | — | — | — | current |
| `20261105T005435Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 159 | — | 10,000 | 23,060 | 0.4337 | 0.602467 | 0.110184 | 0.185255 | — | — | — | current |
| `20261105T005435Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 160 | — | 10,000 | 23,060 | 0.4337 | 0.618388 | 0.110264 | 0.180160 | — | — | — | current |
| `20261105T005435Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 161 | — | 10,000 | 23,060 | 0.4337 | 0.647085 | 0.108471 | 0.222604 | — | — | — | current |
| `20261105T005435Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 162 | — | 10,000 | 23,060 | 0.4337 | 0.606777 | 0.110033 | 0.191070 | — | — | — | current |
| `20261105T005435Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 163 | — | 10,000 | 23,060 | 0.4337 | 0.646045 | 0.108761 | 0.203233 | — | — | — | current |
| `20261105T005435Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 164 | — | 10,000 | 23,060 | 0.4337 | 0.602172 | 0.110417 | 0.181527 | — | — | — | current |
| `20261105T005447Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 165 | — | 10,000 | 23,060 | 0.4337 | 0.621578 | 0.109223 | 0.214867 | — | — | — | current |
| `20261105T005447Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 166 | — | 10,000 | 23,060 | 0.4337 | 0.610181 | 0.109672 | 0.207521 | — | — | — | current |
| `20261105T005447Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 167 | — | 10,000 | 23,060 | 0.4337 | 0.600801 | 0.110767 | 0.172543 | — | — | — | current |
| `20261105T005447Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 168 | — | 10,000 | 23,060 | 0.4337 | 0.629220 | 0.109096 | 0.231302 | — | — | — | current |
| `20261105T005447Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 169 | — | 10,000 | 23,060 | 0.4337 | 0.614894 | 0.110351 | 0.178652 | — | — | — | current |
| `20261105T005447Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 170 | — | 10,000 | 23,060 | 0.4337 | 0.646735 | 0.108652 | 0.217807 | — | — | — | current |
| `20261105T005447Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 171 | — | 10,000 | 23,060 | 0.4337 | 0.635088 | 0.108665 | 0.234530 | — | — | — | current |
| `20261105T005447Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 172 | — | 10,000 | 23,060 | 0.4337 | 0.639487 | 0.108641 | 0.226896 | — | — | — | current |
| `20261105T005447Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 173 | — | 10,000 | 23,060 | 0.4337 | 0.645373 | 0.108878 | 0.205830 | — | — | — | current |
| `20261105T005447Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 174 | — | 10,000 | 23,060 | 0.4337 | 0.590256 | 0.110359 | 0.201830 | — | — | — | current |
| `20261105T005447Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 175 | — | 10,000 | 23,060 | 0.4337 | 0.629650 | 0.108947 | 0.218363 | — | — | — | current |
| `20261105T005447Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 176 | — | 10,000 | 23,060 | 0.4337 | 0.657029 | 0.108353 | 0.215311 | — | — | — | current |
| `20261105T124200Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 177 | — | 10,000 | 23,060 | 0.4337 | 0.641835 | 0.108660 | 0.234411 | — | — | — | current |
| `20261105T124200Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 178 | — | 10,000 | 23,060 | 0.4337 | 0.639407 | 0.109059 | 0.207803 | — | — | — | current |
| `20261105T124200Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 179 | — | 10,000 | 23,060 | 0.4337 | 0.615082 | 0.110043 | 0.185965 | — | — | — | current |
| `20261105T124200Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 180 | — | 10,000 | 23,060 | 0.4337 | 0.625108 | 0.109569 | 0.197034 | — | — | — | current |
| `20261105T124200Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 181 | — | 10,000 | 23,060 | 0.4337 | 0.654593 | 0.108573 | 0.214095 | — | — | — | current |
| `20261105T124200Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 182 | — | 10,000 | 23,060 | 0.4337 | 0.628861 | 0.109621 | 0.192111 | — | — | — | current |
| `20261105T124200Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 183 | — | 10,000 | 23,060 | 0.4337 | 0.622456 | 0.109572 | 0.211848 | — | — | — | current |
| `20261105T124200Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 184 | — | 10,000 | 23,060 | 0.4337 | 0.608246 | 0.110348 | 0.181231 | — | — | — | current |
| `20261105T124200Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 185 | — | 10,000 | 23,060 | 0.4337 | 0.661688 | 0.107968 | 0.239125 | — | — | — | current |
| `20261105T124200Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 186 | — | 10,000 | 23,060 | 0.4337 | 0.670764 | 0.107947 | 0.230676 | — | — | — | current |
| `20261105T124200Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 187 | — | 10,000 | 23,060 | 0.4337 | 0.594610 | 0.110621 | 0.184233 | — | — | — | current |
| `20261105T124200Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 188 | — | 10,000 | 23,060 | 0.4337 | 0.656608 | 0.107727 | 0.254518 | — | — | — | current |
| `20261105T012925Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 189 | — | 10,000 | 23,060 | 0.4337 | 0.598346 | 0.110298 | 0.188767 | — | — | — | current |
| `20261105T012925Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 190 | — | 10,000 | 23,060 | 0.4337 | 0.629623 | 0.109290 | 0.211085 | — | — | — | current |
| `20261105T012925Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 191 | — | 10,000 | 23,060 | 0.4337 | 0.603865 | 0.110408 | 0.186758 | — | — | — | current |
| `20261105T012925Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 192 | — | 10,000 | 23,060 | 0.4337 | 0.634282 | 0.109461 | 0.194706 | — | — | — | current |
| `20261105T012925Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 193 | — | 10,000 | 23,060 | 0.4337 | 0.619517 | 0.109582 | 0.197172 | — | — | — | current |
| `20261105T012925Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 194 | — | 10,000 | 23,060 | 0.4337 | 0.636127 | 0.108799 | 0.223133 | — | — | — | current |
| `20261105T012925Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 195 | — | 10,000 | 23,060 | 0.4337 | 0.656456 | 0.108173 | 0.232918 | — | — | — | current |
| `20261105T012925Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 196 | — | 10,000 | 23,060 | 0.4337 | 0.646601 | 0.108783 | 0.207215 | — | — | — | current |
| `20261105T012925Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 197 | — | 10,000 | 23,060 | 0.4337 | 0.650220 | 0.108625 | 0.214647 | — | — | — | current |
| `20261105T012925Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 198 | — | 10,000 | 23,060 | 0.4337 | 0.635124 | 0.108798 | 0.217269 | — | — | — | current |
| `20261105T012925Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 199 | — | 10,000 | 23,060 | 0.4337 | 0.623764 | 0.109984 | 0.185830 | — | — | — | current |
| `20261105T012925Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 200 | — | 10,000 | 23,060 | 0.4337 | 0.640267 | 0.109341 | 0.194608 | — | — | — | current |
| `20261105T013749Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 201 | — | 10,000 | 23,060 | 0.4337 | 0.615216 | 0.110026 | 0.189762 | — | — | — | current |
| `20261105T013749Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 202 | — | 10,000 | 23,060 | 0.4337 | 0.676229 | 0.107993 | 0.218165 | — | — | — | current |
| `20261105T013749Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 203 | — | 10,000 | 23,060 | 0.4337 | 0.633574 | 0.108835 | 0.224089 | — | — | — | current |
| `20261105T013749Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 204 | — | 10,000 | 23,060 | 0.4337 | 0.645938 | 0.109251 | 0.188685 | — | — | — | current |
| `20261105T013749Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 205 | — | 10,000 | 23,060 | 0.4337 | 0.622411 | 0.109479 | 0.198355 | — | — | — | current |
| `20261105T013749Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 206 | — | 10,000 | 23,060 | 0.4337 | 0.634389 | 0.109137 | 0.208843 | — | — | — | current |
| `20261105T013749Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 207 | — | 10,000 | 23,060 | 0.4337 | 0.644262 | 0.108372 | 0.222237 | — | — | — | current |
| `20261105T013749Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 208 | — | 10,000 | 23,060 | 0.4337 | 0.669322 | 0.107812 | 0.229046 | — | — | — | current |
| `20261105T013749Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 209 | — | 10,000 | 23,060 | 0.4337 | 0.647998 | 0.108741 | 0.222359 | — | — | — | current |
| `20261105T013749Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 210 | — | 10,000 | 23,060 | 0.4337 | 0.674366 | 0.108068 | 0.210141 | — | — | — | current |
| `20261105T013749Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 211 | — | 10,000 | 23,060 | 0.4337 | 0.604071 | 0.109497 | 0.238260 | — | — | — | current |
| `20261105T013749Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 212 | — | 10,000 | 23,060 | 0.4337 | 0.657012 | 0.108366 | 0.231361 | — | — | — | current |
| `20261105T013755Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 213 | — | 10,000 | 23,060 | 0.4337 | 0.598113 | 0.110466 | 0.177495 | — | — | — | current |
| `20261105T013755Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 214 | — | 10,000 | 23,060 | 0.4337 | 0.603516 | 0.110596 | 0.175112 | — | — | — | current |
| `20261105T013755Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 215 | — | 10,000 | 23,060 | 0.4337 | 0.615091 | 0.110074 | 0.186758 | — | — | — | current |
| `20261105T013755Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 216 | — | 10,000 | 23,060 | 0.4337 | 0.636871 | 0.109222 | 0.194761 | — | — | — | current |
| `20261105T013755Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 217 | — | 10,000 | 23,060 | 0.4337 | 0.627688 | 0.109043 | 0.209343 | — | — | — | current |
| `20261105T013755Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 218 | — | 10,000 | 23,060 | 0.4337 | 0.636226 | 0.108780 | 0.221835 | — | — | — | current |
| `20261105T013755Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 219 | — | 10,000 | 23,060 | 0.4337 | 0.646045 | 0.109077 | 0.196869 | — | — | — | current |
| `20261105T013755Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 220 | — | 10,000 | 23,060 | 0.4337 | 0.623486 | 0.109817 | 0.186252 | — | — | — | current |
| `20261105T013755Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 221 | — | 10,000 | 23,060 | 0.4337 | 0.584710 | 0.110964 | 0.191642 | — | — | — | current |
| `20261105T013755Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 222 | — | 10,000 | 23,060 | 0.4337 | 0.601527 | 0.110576 | 0.179394 | — | — | — | current |
| `20261105T013755Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 223 | — | 10,000 | 23,060 | 0.4337 | 0.598669 | 0.109930 | 0.203264 | — | — | — | current |
| `20261105T013755Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 224 | — | 10,000 | 23,060 | 0.4337 | 0.608936 | 0.109829 | 0.194386 | — | — | — | current |
| `20261105T124205Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 225 | — | 10,000 | 23,060 | 0.4337 | 0.658499 | 0.108252 | 0.222756 | — | — | — | current |
| `20261105T124205Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 226 | — | 10,000 | 23,060 | 0.4337 | 0.691657 | 0.106842 | 0.268582 | — | — | — | current |
| `20261105T124205Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 227 | — | 10,000 | 23,060 | 0.4337 | 0.623468 | 0.109266 | 0.204662 | — | — | — | current |
| `20261105T124205Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 228 | — | 10,000 | 23,060 | 0.4337 | 0.616533 | 0.109931 | 0.195075 | — | — | — | current |
| `20261105T124205Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 229 | — | 10,000 | 23,060 | 0.4337 | 0.607171 | 0.110023 | 0.187545 | — | — | — | current |
| `20261105T124205Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 230 | — | 10,000 | 23,060 | 0.4337 | 0.602530 | 0.109925 | 0.205048 | — | — | — | current |
| `20261105T124205Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 231 | — | 10,000 | 23,060 | 0.4337 | 0.613675 | 0.109738 | 0.211745 | — | — | — | current |
| `20261105T124205Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 232 | — | 10,000 | 23,060 | 0.4337 | 0.629739 | 0.109581 | 0.194243 | — | — | — | current |
| `20261105T124205Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 233 | — | 10,000 | 23,060 | 0.4337 | 0.573941 | 0.112154 | 0.154086 | — | — | — | current |
| `20261105T124205Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 234 | — | 10,000 | 23,060 | 0.4337 | 0.633171 | 0.109492 | 0.210133 | — | — | — | current |
| `20261105T124205Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 235 | — | 10,000 | 23,060 | 0.4337 | 0.641476 | 0.108877 | 0.211758 | — | — | — | current |
| `20261105T124205Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 236 | — | 10,000 | 23,060 | 0.4337 | 0.611803 | 0.109750 | 0.206120 | — | — | — | current |
| `20261105T140236Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 237 | — | 10,000 | 23,060 | 0.4337 | 0.641808 | 0.108720 | 0.216733 | — | — | — | current |
| `20261105T140236Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 238 | — | 10,000 | 23,060 | 0.4337 | 0.640007 | 0.108391 | 0.248129 | — | — | — | current |
| `20261105T140236Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 239 | — | 10,000 | 23,060 | 0.4337 | 0.632526 | 0.108972 | 0.226264 | — | — | — | current |
| `20261105T140236Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 240 | — | 10,000 | 23,060 | 0.4337 | 0.612573 | 0.109852 | 0.190536 | — | — | — | current |
| `20261105T140236Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 241 | — | 10,000 | 23,060 | 0.4337 | 0.634255 | 0.109315 | 0.200851 | — | — | — | current |
| `20261105T140236Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 242 | — | 10,000 | 23,060 | 0.4337 | 0.579684 | 0.111852 | 0.159367 | — | — | — | current |
| `20261105T140236Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 243 | — | 10,000 | 23,060 | 0.4337 | 0.600595 | 0.110579 | 0.188741 | — | — | — | current |
| `20261105T140236Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 244 | — | 10,000 | 23,060 | 0.4337 | 0.596509 | 0.110467 | 0.189875 | — | — | — | current |
| `20261105T140236Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 245 | — | 10,000 | 23,060 | 0.4337 | 0.698403 | 0.107289 | 0.243374 | — | — | — | current |
| `20261105T140236Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 246 | — | 10,000 | 23,060 | 0.4337 | 0.651376 | 0.108440 | 0.217958 | — | — | — | current |
| `20261105T140236Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 247 | — | 10,000 | 23,060 | 0.4337 | 0.640831 | 0.109018 | 0.204273 | — | — | — | current |
| `20261105T140236Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 248 | — | 10,000 | 23,060 | 0.4337 | 0.663355 | 0.108080 | 0.226257 | — | — | — | current |
| `20261105T103841Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 249 | — | 10,000 | 23,060 | 0.4337 | 0.640517 | 0.108740 | 0.219248 | — | — | — | current |
| `20261105T103841Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 250 | — | 10,000 | 23,060 | 0.4337 | 0.578860 | 0.111536 | 0.166771 | — | — | — | current |
| `20261105T103841Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 251 | — | 10,000 | 23,060 | 0.4337 | 0.622339 | 0.109745 | 0.197435 | — | — | — | current |
| `20261105T103841Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 252 | — | 10,000 | 23,060 | 0.4337 | 0.589190 | 0.110608 | 0.201885 | — | — | — | current |
| `20261105T103841Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 253 | — | 10,000 | 23,060 | 0.4337 | 0.618594 | 0.110070 | 0.185682 | — | — | — | current |
| `20261105T103841Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 254 | — | 10,000 | 23,060 | 0.4337 | 0.647998 | 0.108374 | 0.224201 | — | — | — | current |
| `20261105T103841Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 255 | — | 10,000 | 23,060 | 0.4337 | 0.649710 | 0.109256 | 0.193798 | — | — | — | current |
| `20261105T103841Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 256 | — | 10,000 | 23,060 | 0.4337 | 0.610549 | 0.109815 | 0.190799 | — | — | — | current |
| `20261105T103841Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 257 | — | 10,000 | 23,060 | 0.4337 | 0.635769 | 0.108911 | 0.204931 | — | — | — | current |
| `20261105T103841Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 258 | — | 10,000 | 23,060 | 0.4337 | 0.617394 | 0.109790 | 0.199760 | — | — | — | current |
| `20261105T103841Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 259 | — | 10,000 | 23,060 | 0.4337 | 0.608793 | 0.110165 | 0.191810 | — | — | — | current |
| `20261105T103841Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 260 | — | 10,000 | 23,060 | 0.4337 | 0.657800 | 0.108188 | 0.232445 | — | — | — | current |
| `20261105T103937Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 261 | — | 10,000 | 23,060 | 0.4337 | 0.614213 | 0.110281 | 0.180672 | — | — | — | current |
| `20261105T103937Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 262 | — | 10,000 | 23,060 | 0.4337 | 0.618137 | 0.109426 | 0.219171 | — | — | — | current |
| `20261105T103937Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 263 | — | 10,000 | 23,060 | 0.4337 | 0.601993 | 0.110480 | 0.184940 | — | — | — | current |
| `20261105T103937Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 264 | — | 10,000 | 23,060 | 0.4337 | 0.609715 | 0.110039 | 0.190441 | — | — | — | current |
| `20261105T103937Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 265 | — | 10,000 | 23,060 | 0.4337 | 0.595354 | 0.110207 | 0.198947 | — | — | — | current |
| `20261105T103937Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 266 | — | 10,000 | 23,060 | 0.4337 | 0.609626 | 0.109548 | 0.216314 | — | — | — | current |
| `20261105T103937Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 267 | — | 10,000 | 23,060 | 0.4337 | 0.636396 | 0.109067 | 0.201730 | — | — | — | current |
| `20261105T103937Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 268 | — | 10,000 | 23,060 | 0.4337 | 0.614795 | 0.110080 | 0.191598 | — | — | — | current |
| `20261105T103937Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 269 | — | 10,000 | 23,060 | 0.4337 | 0.619284 | 0.109632 | 0.201343 | — | — | — | current |
| `20261105T103937Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 270 | — | 10,000 | 23,060 | 0.4337 | 0.657657 | 0.108069 | 0.222642 | — | — | — | current |
| `20261105T103937Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 271 | — | 10,000 | 23,060 | 0.4337 | 0.658320 | 0.108805 | 0.199895 | — | — | — | current |
| `20261105T103937Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 272 | — | 10,000 | 23,060 | 0.4337 | 0.680037 | 0.107876 | 0.227592 | — | — | — | current |
| `20261105T103853Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 273 | — | 10,000 | 23,060 | 0.4337 | 0.611731 | 0.109634 | 0.210764 | — | — | — | current |
| `20261105T103853Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 274 | — | 10,000 | 23,060 | 0.4337 | 0.653356 | 0.108286 | 0.227181 | — | — | — | current |
| `20261105T103853Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 275 | — | 10,000 | 23,060 | 0.4337 | 0.599574 | 0.109928 | 0.217633 | — | — | — | current |
| `20261105T103853Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 276 | — | 10,000 | 23,060 | 0.4337 | 0.643770 | 0.109187 | 0.197900 | — | — | — | current |
| `20261105T103853Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 277 | — | 10,000 | 23,060 | 0.4337 | 0.598911 | 0.110139 | 0.197474 | — | — | — | current |
| `20261105T103853Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 278 | — | 10,000 | 23,060 | 0.4337 | 0.618549 | 0.110057 | 0.191542 | — | — | — | current |
| `20261105T103853Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 279 | — | 10,000 | 23,060 | 0.4337 | 0.664546 | 0.107850 | 0.234907 | — | — | — | current |
| `20261105T103853Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 280 | — | 10,000 | 23,060 | 0.4337 | 0.617205 | 0.110574 | 0.187074 | — | — | — | current |
| `20261105T103853Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 281 | — | 10,000 | 23,060 | 0.4337 | 0.616274 | 0.109580 | 0.203967 | — | — | — | current |
| `20261105T103853Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 282 | — | 10,000 | 23,060 | 0.4337 | 0.621246 | 0.109898 | 0.184106 | — | — | — | current |
| `20261105T103853Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 283 | — | 10,000 | 23,060 | 0.4337 | 0.664098 | 0.108534 | 0.210913 | — | — | — | current |
| `20261105T103853Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 284 | — | 10,000 | 23,060 | 0.4337 | 0.649772 | 0.108119 | 0.250840 | — | — | — | current |
| `20261105T140242Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 285 | — | 10,000 | 23,060 | 0.4337 | 0.642300 | 0.108772 | 0.213703 | — | — | — | current |
| `20261105T140242Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 286 | — | 10,000 | 23,060 | 0.4337 | 0.639308 | 0.109547 | 0.196364 | — | — | — | current |
| `20261105T140242Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 287 | — | 10,000 | 23,060 | 0.4337 | 0.649118 | 0.109113 | 0.199320 | — | — | — | current |
| `20261105T140242Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 288 | — | 10,000 | 23,060 | 0.4337 | 0.638224 | 0.108865 | 0.214944 | — | — | — | current |
| `20261105T140242Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 289 | — | 10,000 | 23,060 | 0.4337 | 0.576700 | 0.111685 | 0.166584 | — | — | — | current |
| `20261105T140242Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 290 | — | 10,000 | 23,060 | 0.4337 | 0.650113 | 0.108997 | 0.210381 | — | — | — | current |
| `20261105T140242Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 291 | — | 10,000 | 23,060 | 0.4337 | 0.666123 | 0.108243 | 0.213911 | — | — | — | current |
| `20261105T140242Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 292 | — | 10,000 | 23,060 | 0.4337 | 0.613899 | 0.109549 | 0.208648 | — | — | — | current |
| `20261105T140242Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 293 | — | 10,000 | 23,060 | 0.4337 | 0.607368 | 0.110117 | 0.185191 | — | — | — | current |
| `20261105T140242Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 294 | — | 10,000 | 23,060 | 0.4337 | 0.612063 | 0.109647 | 0.219124 | — | — | — | current |
| `20261105T140242Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 295 | — | 10,000 | 23,060 | 0.4337 | 0.612457 | 0.110333 | 0.183137 | — | — | — | current |
| `20261105T140242Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 296 | — | 10,000 | 23,060 | 0.4337 | 0.639209 | 0.109755 | 0.191228 | — | — | — | current |
| `20261105T111110Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 297 | — | 10,000 | 23,060 | 0.4337 | 0.657468 | 0.107578 | 0.252874 | — | — | — | current |
| `20261105T111110Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 298 | — | 10,000 | 23,060 | 0.4337 | 0.610369 | 0.109605 | 0.207589 | — | — | — | current |
| `20261105T111110Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 299 | — | 10,000 | 23,060 | 0.4337 | 0.671105 | 0.107570 | 0.250402 | — | — | — | current |
| `20261105T111110Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 300 | — | 10,000 | 23,060 | 0.4337 | 0.599842 | 0.110568 | 0.180748 | — | — | — | current |
| `20261105T111110Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 301 | — | 10,000 | 23,060 | 0.4337 | 0.575948 | 0.111783 | 0.159276 | — | — | — | current |
| `20261105T111110Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 302 | — | 10,000 | 23,060 | 0.4337 | 0.630017 | 0.109868 | 0.180377 | — | — | — | current |
| `20261105T111110Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 303 | — | 10,000 | 23,060 | 0.4337 | 0.634353 | 0.109034 | 0.210916 | — | — | — | current |
| `20261105T111110Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 304 | — | 10,000 | 23,060 | 0.4337 | 0.563907 | 0.111697 | 0.170209 | — | — | — | current |
| `20261105T111110Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 305 | — | 10,000 | 23,060 | 0.4337 | 0.559526 | 0.111826 | 0.175458 | — | — | — | current |
| `20261105T111110Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 306 | — | 10,000 | 23,060 | 0.4337 | 0.588589 | 0.111008 | 0.178213 | — | — | — | current |
| `20261105T111110Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 307 | — | 10,000 | 23,060 | 0.4337 | 0.594431 | 0.110350 | 0.195192 | — | — | — | current |
| `20261105T111110Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 308 | — | 10,000 | 23,060 | 0.4337 | 0.623853 | 0.109898 | 0.183602 | — | — | — | current |
| `20261105T114320Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 309 | — | 10,000 | 23,060 | 0.4337 | 0.661805 | 0.107645 | 0.243800 | — | — | — | current |
| `20261105T114320Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 310 | — | 10,000 | 23,060 | 0.4337 | 0.645992 | 0.108698 | 0.209297 | — | — | — | current |
| `20261105T114320Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 311 | — | 10,000 | 23,060 | 0.4337 | 0.611006 | 0.109957 | 0.194437 | — | — | — | current |
| `20261105T114320Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 312 | — | 10,000 | 23,060 | 0.4337 | 0.672350 | 0.107867 | 0.224418 | — | — | — | current |
| `20261105T114320Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 313 | — | 10,000 | 23,060 | 0.4337 | 0.631245 | 0.109380 | 0.197201 | — | — | — | current |
| `20261105T114320Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 314 | — | 10,000 | 23,060 | 0.4337 | 0.630178 | 0.109372 | 0.214022 | — | — | — | current |
| `20261105T114320Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 315 | — | 10,000 | 23,060 | 0.4337 | 0.586842 | 0.110750 | 0.178535 | — | — | — | current |
| `20261105T114320Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 316 | — | 10,000 | 23,060 | 0.4337 | 0.668444 | 0.108293 | 0.239422 | — | — | — | current |
| `20261105T114320Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 317 | — | 10,000 | 23,060 | 0.4337 | 0.593938 | 0.110502 | 0.193813 | — | — | — | current |
| `20261105T114320Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 318 | — | 10,000 | 23,060 | 0.4337 | 0.593607 | 0.110828 | 0.179134 | — | — | — | current |
| `20261105T114320Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 319 | — | 10,000 | 23,060 | 0.4337 | 0.637704 | 0.109321 | 0.188753 | — | — | — | current |
| `20261105T114320Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 320 | — | 10,000 | 23,060 | 0.4337 | 0.618549 | 0.110517 | 0.174949 | — | — | — | current |
| `20261105T114647Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 321 | — | 10,000 | 23,060 | 0.4337 | 0.645920 | 0.108910 | 0.204573 | — | — | — | current |
| `20261105T114647Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 322 | — | 10,000 | 23,060 | 0.4337 | 0.650615 | 0.107856 | 0.254458 | — | — | — | current |
| `20261105T114647Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 323 | — | 10,000 | 23,060 | 0.4337 | 0.630573 | 0.109056 | 0.209986 | — | — | — | current |
| `20261105T114647Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 324 | — | 10,000 | 23,060 | 0.4337 | 0.615109 | 0.110422 | 0.176013 | — | — | — | current |
| `20261105T114647Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 325 | — | 10,000 | 23,060 | 0.4337 | 0.660909 | 0.108237 | 0.228414 | — | — | — | current |
| `20261105T114647Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 326 | — | 10,000 | 23,060 | 0.4337 | 0.612565 | 0.110202 | 0.185142 | — | — | — | current |
| `20261105T114647Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 327 | — | 10,000 | 23,060 | 0.4337 | 0.602584 | 0.109877 | 0.207120 | — | — | — | current |
| `20261105T114647Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 328 | — | 10,000 | 23,060 | 0.4337 | 0.661527 | 0.108308 | 0.225792 | — | — | — | current |
| `20261105T114647Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 329 | — | 10,000 | 23,060 | 0.4337 | 0.652971 | 0.108673 | 0.201363 | — | — | — | current |
| `20261105T114647Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 330 | — | 10,000 | 23,060 | 0.4337 | 0.641996 | 0.109185 | 0.197402 | — | — | — | current |
| `20261104T234013Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 93 | — | 10,000 | 23,060 | 0.4337 | 0.614240 | 0.110468 | 0.173808 | — | — | — | current |
| `20261104T234013Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 94 | — | 10,000 | 23,060 | 0.4337 | 0.658974 | 0.108138 | 0.250593 | — | — | — | current |
| `20261104T234013Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 95 | — | 10,000 | 23,060 | 0.4337 | 0.645786 | 0.108894 | 0.205892 | — | — | — | current |
| `20261104T234013Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 96 | — | 10,000 | 23,060 | 0.4337 | 0.628655 | 0.110078 | 0.185499 | — | — | — | current |
| `20261104T234013Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 97 | — | 10,000 | 23,060 | 0.4337 | 0.628387 | 0.109754 | 0.191710 | — | — | — | current |
| `20261104T234013Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 98 | — | 10,000 | 23,060 | 0.4337 | 0.634909 | 0.109082 | 0.210557 | — | — | — | current |
| `20261104T234013Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 99 | — | 10,000 | 23,060 | 0.4337 | 0.621784 | 0.110155 | 0.179085 | — | — | — | current |
| `20261104T234013Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 100 | — | 10,000 | 23,060 | 0.4337 | 0.661572 | 0.108014 | 0.229623 | — | — | — | current |
| `20261104T234013Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 101 | — | 10,000 | 23,060 | 0.4337 | 0.593454 | 0.110840 | 0.170510 | — | — | — | current |
| `20261104T234013Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 102 | — | 10,000 | 23,060 | 0.4337 | 0.611579 | 0.109666 | 0.197886 | — | — | — | current |
| `20261104T234013Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 103 | — | 10,000 | 23,060 | 0.4337 | 0.587299 | 0.110968 | 0.166093 | — | — | — | current |
| `20261104T234013Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 104 | — | 10,000 | 23,060 | 0.4337 | 0.674536 | 0.107690 | 0.234932 | — | — | — | current |
| `20261105T001837Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 105 | — | 10,000 | 23,060 | 0.4337 | 0.647398 | 0.109374 | 0.196519 | — | — | — | current |
| `20261105T001837Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 106 | — | 10,000 | 23,060 | 0.4337 | 0.597871 | 0.111724 | 0.165054 | — | — | — | current |
| `20261105T001837Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 107 | — | 10,000 | 23,060 | 0.4337 | 0.624561 | 0.109860 | 0.185895 | — | — | — | current |
| `20261105T001837Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 108 | — | 10,000 | 23,060 | 0.4337 | 0.648948 | 0.108309 | 0.227093 | — | — | — | current |
| `20261105T001837Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 109 | — | 10,000 | 23,060 | 0.4337 | 0.600111 | 0.110197 | 0.187509 | — | — | — | current |
| `20261105T001837Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 110 | — | 10,000 | 23,060 | 0.4337 | 0.668381 | 0.107332 | 0.238765 | — | — | — | current |
| `20261105T001837Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 111 | — | 10,000 | 23,060 | 0.4337 | 0.609823 | 0.110365 | 0.180759 | — | — | — | current |
| `20261105T001837Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 112 | — | 10,000 | 23,060 | 0.4337 | 0.617582 | 0.109557 | 0.203085 | — | — | — | current |
| `20261105T001837Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 113 | — | 10,000 | 23,060 | 0.4337 | 0.634712 | 0.109283 | 0.199677 | — | — | — | current |
| `20261105T001837Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 114 | — | 10,000 | 23,060 | 0.4337 | 0.632848 | 0.109228 | 0.203361 | — | — | — | current |
| `20261105T001837Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 115 | — | 10,000 | 23,060 | 0.4337 | 0.599161 | 0.110622 | 0.179833 | — | — | — | current |
| `20261105T001837Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 116 | — | 10,000 | 23,060 | 0.4337 | 0.643591 | 0.108859 | 0.212811 | — | — | — | current |
| `20261104T234127Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 117 | — | 10,000 | 23,060 | 0.4337 | 0.627473 | 0.109537 | 0.206865 | — | — | — | current |
| `20261104T234127Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 118 | — | 10,000 | 23,060 | 0.4337 | 0.636414 | 0.108094 | 0.248872 | — | — | — | current |
| `20261104T234127Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 119 | — | 10,000 | 23,060 | 0.4337 | 0.608157 | 0.110074 | 0.190885 | — | — | — | current |
| `20261104T234127Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 120 | — | 10,000 | 23,060 | 0.4337 | 0.593239 | 0.111023 | 0.175731 | — | — | — | current |
| `20261104T234127Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 121 | — | 10,000 | 23,060 | 0.4337 | 0.624194 | 0.109170 | 0.228207 | — | — | — | current |
| `20261104T234127Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 122 | — | 10,000 | 23,060 | 0.4337 | 0.610074 | 0.109957 | 0.189288 | — | — | — | current |
| `20261104T234127Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 123 | — | 10,000 | 23,060 | 0.4337 | 0.649226 | 0.108716 | 0.225084 | — | — | — | current |
| `20261104T234127Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 124 | — | 10,000 | 23,060 | 0.4337 | 0.648805 | 0.108472 | 0.221652 | — | — | — | current |
| `20261104T234127Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 125 | — | 10,000 | 23,060 | 0.4337 | 0.594305 | 0.110998 | 0.182016 | — | — | — | current |
| `20261104T234127Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 126 | — | 10,000 | 23,060 | 0.4337 | 0.658544 | 0.108479 | 0.205271 | — | — | — | current |
| `20261104T234127Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 127 | — | 10,000 | 23,060 | 0.4337 | 0.607906 | 0.110305 | 0.180985 | — | — | — | current |
| `20261104T234127Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 128 | — | 10,000 | 23,060 | 0.4337 | 0.626774 | 0.109660 | 0.193244 | — | — | — | current |
| `20261104T234132Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 129 | — | 10,000 | 23,060 | 0.4337 | 0.610011 | 0.109943 | 0.190908 | — | — | — | current |
| `20261104T234132Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 130 | — | 10,000 | 23,060 | 0.4337 | 0.647819 | 0.108895 | 0.202983 | — | — | — | current |
| `20261104T234132Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 131 | — | 10,000 | 23,060 | 0.4337 | 0.636342 | 0.109288 | 0.192937 | — | — | — | current |
| `20261104T234132Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 132 | — | 10,000 | 23,060 | 0.4337 | 0.636988 | 0.109245 | 0.196666 | — | — | — | current |
| `20261104T234132Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 133 | — | 10,000 | 23,060 | 0.4337 | 0.670226 | 0.107677 | 0.236690 | — | — | — | current |
| `20261104T234132Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 134 | — | 10,000 | 23,060 | 0.4337 | 0.626183 | 0.110050 | 0.186867 | — | — | — | current |
| `20261104T234132Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 135 | — | 10,000 | 23,060 | 0.4337 | 0.633054 | 0.109339 | 0.204324 | — | — | — | current |
| `20261104T234132Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 136 | — | 10,000 | 23,060 | 0.4337 | 0.637794 | 0.109041 | 0.217727 | — | — | — | current |
| `20261104T234132Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 137 | — | 10,000 | 23,060 | 0.4337 | 0.594494 | 0.110872 | 0.170840 | — | — | — | current |
| `20261104T234132Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 138 | — | 10,000 | 23,060 | 0.4337 | 0.629148 | 0.109616 | 0.194758 | — | — | — | current |
| `20261104T234132Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 139 | — | 10,000 | 23,060 | 0.4337 | 0.586484 | 0.111763 | 0.163256 | — | — | — | current |
| `20261104T234132Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 140 | — | 10,000 | 23,060 | 0.4337 | 0.662584 | 0.108990 | 0.203256 | — | — | — | current |
| `20261105T100533Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 141 | — | 10,000 | 23,060 | 0.4337 | 0.636692 | 0.108839 | 0.211179 | — | — | — | current |
| `20261105T100533Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 142 | — | 10,000 | 23,060 | 0.4337 | 0.543963 | 0.113182 | 0.151576 | — | — | — | current |
| `20261105T100533Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 143 | — | 10,000 | 23,060 | 0.4337 | 0.633717 | 0.109656 | 0.191387 | — | — | — | current |
| `20261105T100533Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 144 | — | 10,000 | 23,060 | 0.4337 | 0.624767 | 0.109915 | 0.183528 | — | — | — | current |
| `20261105T100533Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 145 | — | 10,000 | 23,060 | 0.4337 | 0.642032 | 0.108773 | 0.211210 | — | — | — | current |
| `20261105T100533Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 146 | — | 10,000 | 23,060 | 0.4337 | 0.615611 | 0.109715 | 0.201490 | — | — | — | current |
| `20261105T100533Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 147 | — | 10,000 | 23,060 | 0.4337 | 0.625842 | 0.109322 | 0.200635 | — | — | — | current |
| `20261105T100533Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 148 | — | 10,000 | 23,060 | 0.4337 | 0.619526 | 0.109490 | 0.203648 | — | — | — | current |
| `20261105T100533Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 149 | — | 10,000 | 23,060 | 0.4337 | 0.607099 | 0.110139 | 0.186857 | — | — | — | current |
| `20261105T100533Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 150 | — | 10,000 | 23,060 | 0.4337 | 0.626353 | 0.110189 | 0.185491 | — | — | — | current |
| `20261105T100533Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 151 | — | 10,000 | 23,060 | 0.4337 | 0.609366 | 0.110255 | 0.193553 | — | — | — | current |
| `20261105T100533Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 152 | — | 10,000 | 23,060 | 0.4337 | 0.614930 | 0.110109 | 0.187719 | — | — | — | current |
| `20261105T005435Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 153 | — | 10,000 | 23,060 | 0.4337 | 0.637695 | 0.108941 | 0.213589 | — | — | — | current |
| `20261105T005435Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 154 | — | 10,000 | 23,060 | 0.4337 | 0.653446 | 0.108145 | 0.228225 | — | — | — | current |
| `20261105T005435Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 155 | — | 10,000 | 23,060 | 0.4337 | 0.604886 | 0.110672 | 0.171180 | — | — | — | current |
| `20261105T005435Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 156 | — | 10,000 | 23,060 | 0.4337 | 0.605263 | 0.110367 | 0.185219 | — | — | — | current |
| `20261105T005435Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 157 | — | 10,000 | 23,060 | 0.4337 | 0.667073 | 0.108026 | 0.223194 | — | — | — | current |
| `20261105T005435Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 158 | — | 10,000 | 23,060 | 0.4337 | 0.610755 | 0.109736 | 0.208823 | — | — | — | current |
| `20261105T005435Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 159 | — | 10,000 | 23,060 | 0.4337 | 0.609474 | 0.109927 | 0.187267 | — | — | — | current |
| `20261105T005435Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 160 | — | 10,000 | 23,060 | 0.4337 | 0.625511 | 0.109912 | 0.187850 | — | — | — | current |
| `20261105T005435Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 161 | — | 10,000 | 23,060 | 0.4337 | 0.646260 | 0.108310 | 0.220737 | — | — | — | current |
| `20261105T005435Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 162 | — | 10,000 | 23,060 | 0.4337 | 0.608631 | 0.109713 | 0.203124 | — | — | — | current |
| `20261105T005435Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 163 | — | 10,000 | 23,060 | 0.4337 | 0.633435 | 0.109641 | 0.185860 | — | — | — | current |
| `20261105T005435Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 164 | — | 10,000 | 23,060 | 0.4337 | 0.609572 | 0.110258 | 0.175795 | — | — | — | current |
| `20261105T005447Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 165 | — | 10,000 | 23,060 | 0.4337 | 0.631943 | 0.108953 | 0.212669 | — | — | — | current |
| `20261105T005447Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 166 | — | 10,000 | 23,060 | 0.4337 | 0.614984 | 0.109543 | 0.207569 | — | — | — | current |
| `20261105T005447Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 167 | — | 10,000 | 23,060 | 0.4337 | 0.609312 | 0.110396 | 0.181464 | — | — | — | current |
| `20261105T005447Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 168 | — | 10,000 | 23,060 | 0.4337 | 0.628010 | 0.109147 | 0.216968 | — | — | — | current |
| `20261105T005447Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 169 | — | 10,000 | 23,060 | 0.4337 | 0.610674 | 0.110685 | 0.174306 | — | — | — | current |
| `20261105T005447Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 170 | — | 10,000 | 23,060 | 0.4337 | 0.650507 | 0.108383 | 0.231820 | — | — | — | current |
| `20261105T005447Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 171 | — | 10,000 | 23,060 | 0.4337 | 0.640894 | 0.108525 | 0.215799 | — | — | — | current |
| `20261105T005447Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 172 | — | 10,000 | 23,060 | 0.4337 | 0.642560 | 0.108562 | 0.229541 | — | — | — | current |
| `20261105T005447Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 173 | — | 10,000 | 23,060 | 0.4337 | 0.636620 | 0.109579 | 0.184287 | — | — | — | current |
| `20261105T005447Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 174 | — | 10,000 | 23,060 | 0.4337 | 0.594350 | 0.110014 | 0.204861 | — | — | — | current |
| `20261105T005447Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 175 | — | 10,000 | 23,060 | 0.4337 | 0.629112 | 0.108848 | 0.216326 | — | — | — | current |
| `20261105T005447Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 176 | — | 10,000 | 23,060 | 0.4337 | 0.651107 | 0.108251 | 0.220026 | — | — | — | current |
| `20261105T124200Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 177 | — | 10,000 | 23,060 | 0.4337 | 0.641163 | 0.109020 | 0.207802 | — | — | — | current |
| `20261105T124200Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 178 | — | 10,000 | 23,060 | 0.4337 | 0.645060 | 0.108728 | 0.211570 | — | — | — | current |
| `20261105T124200Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 179 | — | 10,000 | 23,060 | 0.4337 | 0.613729 | 0.109617 | 0.203471 | — | — | — | current |
| `20261105T124200Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 180 | — | 10,000 | 23,060 | 0.4337 | 0.630429 | 0.109539 | 0.194683 | — | — | — | current |
| `20261105T124200Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 181 | — | 10,000 | 23,060 | 0.4337 | 0.633404 | 0.109085 | 0.206167 | — | — | — | current |
| `20261105T124200Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 182 | — | 10,000 | 23,060 | 0.4337 | 0.629874 | 0.109649 | 0.193084 | — | — | — | current |
| `20261105T124200Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 183 | — | 10,000 | 23,060 | 0.4337 | 0.629309 | 0.109513 | 0.194056 | — | — | — | current |
| `20261105T124200Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 184 | — | 10,000 | 23,060 | 0.4337 | 0.619123 | 0.110020 | 0.180362 | — | — | — | current |
| `20261105T124200Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 185 | — | 10,000 | 23,060 | 0.4337 | 0.653258 | 0.108363 | 0.232046 | — | — | — | current |
| `20261105T124200Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 186 | — | 10,000 | 23,060 | 0.4337 | 0.654584 | 0.108622 | 0.205200 | — | — | — | current |
| `20261105T124200Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 187 | — | 10,000 | 23,060 | 0.4337 | 0.587676 | 0.111252 | 0.169375 | — | — | — | current |
| `20261105T124200Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 188 | — | 10,000 | 23,060 | 0.4337 | 0.655954 | 0.107704 | 0.254383 | — | — | — | current |
| `20261105T012925Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 189 | — | 10,000 | 23,060 | 0.4337 | 0.598373 | 0.110605 | 0.181777 | — | — | — | current |
| `20261105T012925Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 190 | — | 10,000 | 23,060 | 0.4337 | 0.628279 | 0.109321 | 0.208757 | — | — | — | current |
| `20261105T012925Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 191 | — | 10,000 | 23,060 | 0.4337 | 0.614939 | 0.110173 | 0.188860 | — | — | — | current |
| `20261105T012925Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 192 | — | 10,000 | 23,060 | 0.4337 | 0.619454 | 0.109936 | 0.187101 | — | — | — | current |
| `20261105T012925Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 193 | — | 10,000 | 23,060 | 0.4337 | 0.621058 | 0.109871 | 0.187272 | — | — | — | current |
| `20261105T012925Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 194 | — | 10,000 | 23,060 | 0.4337 | 0.625457 | 0.109084 | 0.215127 | — | — | — | current |
| `20261105T012925Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 195 | — | 10,000 | 23,060 | 0.4337 | 0.664994 | 0.107804 | 0.233233 | — | — | — | current |
| `20261105T012925Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 196 | — | 10,000 | 23,060 | 0.4337 | 0.636271 | 0.109493 | 0.188928 | — | — | — | current |
| `20261105T012925Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 197 | — | 10,000 | 23,060 | 0.4337 | 0.659753 | 0.108304 | 0.214576 | — | — | — | current |
| `20261105T012925Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 198 | — | 10,000 | 23,060 | 0.4337 | 0.646753 | 0.108427 | 0.225299 | — | — | — | current |
| `20261105T012925Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 199 | — | 10,000 | 23,060 | 0.4337 | 0.629139 | 0.109592 | 0.201747 | — | — | — | current |
| `20261105T012925Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 200 | — | 10,000 | 23,060 | 0.4337 | 0.639595 | 0.109369 | 0.192770 | — | — | — | current |
| `20261105T013749Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 201 | — | 10,000 | 23,060 | 0.4337 | 0.603193 | 0.110799 | 0.174739 | — | — | — | current |
| `20261105T013749Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 202 | — | 10,000 | 23,060 | 0.4337 | 0.663597 | 0.108478 | 0.208128 | — | — | — | current |
| `20261105T013749Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 203 | — | 10,000 | 23,060 | 0.4337 | 0.632723 | 0.109179 | 0.213485 | — | — | — | current |
| `20261105T013749Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 204 | — | 10,000 | 23,060 | 0.4337 | 0.658785 | 0.109117 | 0.191691 | — | — | — | current |
| `20261105T013749Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 205 | — | 10,000 | 23,060 | 0.4337 | 0.624050 | 0.109700 | 0.192699 | — | — | — | current |
| `20261105T013749Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 206 | — | 10,000 | 23,060 | 0.4337 | 0.638546 | 0.109118 | 0.203374 | — | — | — | current |
| `20261105T013749Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 207 | — | 10,000 | 23,060 | 0.4337 | 0.657558 | 0.108674 | 0.207880 | — | — | — | current |
| `20261105T013749Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 208 | — | 10,000 | 23,060 | 0.4337 | 0.660730 | 0.107950 | 0.222531 | — | — | — | current |
| `20261105T013749Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 209 | — | 10,000 | 23,060 | 0.4337 | 0.650704 | 0.108775 | 0.222347 | — | — | — | current |
| `20261105T013749Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 210 | — | 10,000 | 23,060 | 0.4337 | 0.674778 | 0.108009 | 0.215842 | — | — | — | current |
| `20261105T013749Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 211 | — | 10,000 | 23,060 | 0.4337 | 0.600891 | 0.109720 | 0.205505 | — | — | — | current |
| `20261105T013749Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 212 | — | 10,000 | 23,060 | 0.4337 | 0.663785 | 0.107884 | 0.242677 | — | — | — | current |
| `20261105T013755Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 213 | — | 10,000 | 23,060 | 0.4337 | 0.601249 | 0.110434 | 0.176769 | — | — | — | current |
| `20261105T013755Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 214 | — | 10,000 | 23,060 | 0.4337 | 0.597889 | 0.110892 | 0.171267 | — | — | — | current |
| `20261105T013755Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 215 | — | 10,000 | 23,060 | 0.4337 | 0.612609 | 0.110373 | 0.179447 | — | — | — | current |
| `20261105T013755Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 216 | — | 10,000 | 23,060 | 0.4337 | 0.628629 | 0.109782 | 0.186707 | — | — | — | current |
| `20261105T013755Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 217 | — | 10,000 | 23,060 | 0.4337 | 0.630134 | 0.108846 | 0.218891 | — | — | — | current |
| `20261105T013755Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 218 | — | 10,000 | 23,060 | 0.4337 | 0.639989 | 0.108807 | 0.227088 | — | — | — | current |
| `20261105T013755Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 219 | — | 10,000 | 23,060 | 0.4337 | 0.648491 | 0.108899 | 0.206858 | — | — | — | current |
| `20261105T013755Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 220 | — | 10,000 | 23,060 | 0.4337 | 0.620252 | 0.110040 | 0.182859 | — | — | — | current |
| `20261105T013755Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 221 | — | 10,000 | 23,060 | 0.4337 | 0.595712 | 0.110517 | 0.190887 | — | — | — | current |
| `20261105T013755Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 222 | — | 10,000 | 23,060 | 0.4337 | 0.616999 | 0.110155 | 0.179307 | — | — | — | current |
| `20261105T013755Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 223 | — | 10,000 | 23,060 | 0.4337 | 0.613944 | 0.109783 | 0.201797 | — | — | — | current |
| `20261105T013755Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 224 | — | 10,000 | 23,060 | 0.4337 | 0.611140 | 0.109635 | 0.201754 | — | — | — | current |
| `20261105T124205Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 225 | — | 10,000 | 23,060 | 0.4337 | 0.649020 | 0.108901 | 0.211960 | — | — | — | current |
| `20261105T124205Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 226 | — | 10,000 | 23,060 | 0.4337 | 0.688853 | 0.106800 | 0.268391 | — | — | — | current |
| `20261105T124205Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 227 | — | 10,000 | 23,060 | 0.4337 | 0.633332 | 0.108872 | 0.207507 | — | — | — | current |
| `20261105T124205Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 228 | — | 10,000 | 23,060 | 0.4337 | 0.628772 | 0.109389 | 0.195658 | — | — | — | current |
| `20261105T124205Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 229 | — | 10,000 | 23,060 | 0.4337 | 0.593813 | 0.110662 | 0.178335 | — | — | — | current |
| `20261105T124205Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 230 | — | 10,000 | 23,060 | 0.4337 | 0.602010 | 0.109886 | 0.200256 | — | — | — | current |
| `20261105T124205Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 231 | — | 10,000 | 23,060 | 0.4337 | 0.623262 | 0.109430 | 0.214132 | — | — | — | current |
| `20261105T124205Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 232 | — | 10,000 | 23,060 | 0.4337 | 0.635303 | 0.109328 | 0.199197 | — | — | — | current |
| `20261105T124205Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 233 | — | 10,000 | 23,060 | 0.4337 | 0.580669 | 0.111713 | 0.162357 | — | — | — | current |
| `20261105T124205Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 234 | — | 10,000 | 23,060 | 0.4337 | 0.649083 | 0.108785 | 0.216567 | — | — | — | current |
| `20261105T124205Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 235 | — | 10,000 | 23,060 | 0.4337 | 0.628378 | 0.109276 | 0.206178 | — | — | — | current |
| `20261105T124205Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 236 | — | 10,000 | 23,060 | 0.4337 | 0.616489 | 0.109559 | 0.205616 | — | — | — | current |
| `20261105T140236Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 237 | — | 10,000 | 23,060 | 0.4337 | 0.648948 | 0.108348 | 0.226064 | — | — | — | current |
| `20261105T140236Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 238 | — | 10,000 | 23,060 | 0.4337 | 0.644908 | 0.108307 | 0.233364 | — | — | — | current |
| `20261105T140236Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 239 | — | 10,000 | 23,060 | 0.4337 | 0.637767 | 0.108462 | 0.244038 | — | — | — | current |
| `20261105T140236Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 240 | — | 10,000 | 23,060 | 0.4337 | 0.617967 | 0.109430 | 0.205092 | — | — | — | current |
| `20261105T140236Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 241 | — | 10,000 | 23,060 | 0.4337 | 0.625430 | 0.109724 | 0.187618 | — | — | — | current |
| `20261105T140236Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 242 | — | 10,000 | 23,060 | 0.4337 | 0.580454 | 0.112658 | 0.156751 | — | — | — | current |
| `20261105T140236Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 243 | — | 10,000 | 23,060 | 0.4337 | 0.611489 | 0.110094 | 0.193545 | — | — | — | current |
| `20261105T140236Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 244 | — | 10,000 | 23,060 | 0.4337 | 0.598077 | 0.110446 | 0.191319 | — | — | — | current |
| `20261105T140236Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 245 | — | 10,000 | 23,060 | 0.4337 | 0.691379 | 0.107865 | 0.228536 | — | — | — | current |
| `20261105T140236Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 246 | — | 10,000 | 23,060 | 0.4337 | 0.660981 | 0.108186 | 0.219631 | — | — | — | current |
| `20261105T140236Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 247 | — | 10,000 | 23,060 | 0.4337 | 0.645239 | 0.109246 | 0.197964 | — | — | — | current |
| `20261105T140236Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 248 | — | 10,000 | 23,060 | 0.4337 | 0.653338 | 0.108716 | 0.207113 | — | — | — | current |
| `20261105T103841Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 249 | — | 10,000 | 23,060 | 0.4337 | 0.629775 | 0.109379 | 0.207464 | — | — | — | current |
| `20261105T103841Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 250 | — | 10,000 | 23,060 | 0.4337 | 0.580481 | 0.111174 | 0.176308 | — | — | — | current |
| `20261105T103841Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 251 | — | 10,000 | 23,060 | 0.4337 | 0.608820 | 0.110447 | 0.179542 | — | — | — | current |
| `20261105T103841Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 252 | — | 10,000 | 23,060 | 0.4337 | 0.593616 | 0.110520 | 0.193035 | — | — | — | current |
| `20261105T103841Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 253 | — | 10,000 | 23,060 | 0.4337 | 0.618961 | 0.110246 | 0.179407 | — | — | — | current |
| `20261105T103841Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 254 | — | 10,000 | 23,060 | 0.4337 | 0.638529 | 0.108847 | 0.221117 | — | — | — | current |
| `20261105T103841Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 255 | — | 10,000 | 23,060 | 0.4337 | 0.638484 | 0.109417 | 0.193314 | — | — | — | current |
| `20261105T103841Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 256 | — | 10,000 | 23,060 | 0.4337 | 0.614401 | 0.109765 | 0.196584 | — | — | — | current |
| `20261105T103841Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 257 | — | 10,000 | 23,060 | 0.4337 | 0.639774 | 0.108786 | 0.214702 | — | — | — | current |
| `20261105T103841Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 258 | — | 10,000 | 23,060 | 0.4337 | 0.633861 | 0.108793 | 0.212143 | — | — | — | current |
| `20261105T103841Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 259 | — | 10,000 | 23,060 | 0.4337 | 0.606069 | 0.110058 | 0.191491 | — | — | — | current |
| `20261105T103841Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 260 | — | 10,000 | 23,060 | 0.4337 | 0.659198 | 0.108614 | 0.212278 | — | — | — | current |
| `20261105T103937Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 261 | — | 10,000 | 23,060 | 0.4337 | 0.610477 | 0.110163 | 0.186128 | — | — | — | current |
| `20261105T103937Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 262 | — | 10,000 | 23,060 | 0.4337 | 0.604600 | 0.109954 | 0.197314 | — | — | — | current |
| `20261105T103937Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 263 | — | 10,000 | 23,060 | 0.4337 | 0.602754 | 0.110653 | 0.180536 | — | — | — | current |
| `20261105T103937Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 264 | — | 10,000 | 23,060 | 0.4337 | 0.616309 | 0.109448 | 0.203463 | — | — | — | current |
| `20261105T103937Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 265 | — | 10,000 | 23,060 | 0.4337 | 0.599063 | 0.110067 | 0.203197 | — | — | — | current |
| `20261105T103937Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 266 | — | 10,000 | 23,060 | 0.4337 | 0.613801 | 0.109138 | 0.220508 | — | — | — | current |
| `20261105T103937Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 267 | — | 10,000 | 23,060 | 0.4337 | 0.639236 | 0.109362 | 0.198030 | — | — | — | current |
| `20261105T103937Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 268 | — | 10,000 | 23,060 | 0.4337 | 0.617161 | 0.110119 | 0.184702 | — | — | — | current |
| `20261105T103937Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 269 | — | 10,000 | 23,060 | 0.4337 | 0.605746 | 0.110258 | 0.191075 | — | — | — | current |
| `20261105T103937Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 270 | — | 10,000 | 23,060 | 0.4337 | 0.669178 | 0.107992 | 0.222753 | — | — | — | current |
| `20261105T103937Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 271 | — | 10,000 | 23,060 | 0.4337 | 0.657876 | 0.108818 | 0.204341 | — | — | — | current |
| `20261105T103937Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 272 | — | 10,000 | 23,060 | 0.4337 | 0.672072 | 0.108186 | 0.221801 | — | — | — | current |
| `20261105T103853Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 273 | — | 10,000 | 23,060 | 0.4337 | 0.616265 | 0.109692 | 0.199510 | — | — | — | current |
| `20261105T103853Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 274 | — | 10,000 | 23,060 | 0.4337 | 0.657764 | 0.107918 | 0.228423 | — | — | — | current |
| `20261105T103853Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 275 | — | 10,000 | 23,060 | 0.4337 | 0.605702 | 0.109725 | 0.211905 | — | — | — | current |
| `20261105T103853Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 276 | — | 10,000 | 23,060 | 0.4337 | 0.656116 | 0.109196 | 0.190210 | — | — | — | current |
| `20261105T103853Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 277 | — | 10,000 | 23,060 | 0.4337 | 0.611086 | 0.110141 | 0.188568 | — | — | — | current |
| `20261105T103853Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 278 | — | 10,000 | 23,060 | 0.4337 | 0.616354 | 0.110417 | 0.178040 | — | — | — | current |
| `20261105T103853Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 279 | — | 10,000 | 23,060 | 0.4337 | 0.652147 | 0.108370 | 0.220005 | — | — | — | current |
| `20261105T103853Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 280 | — | 10,000 | 23,060 | 0.4337 | 0.620081 | 0.110228 | 0.186628 | — | — | — | current |
| `20261105T103853Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 281 | — | 10,000 | 23,060 | 0.4337 | 0.624991 | 0.109585 | 0.211294 | — | — | — | current |
| `20261105T103853Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 282 | — | 10,000 | 23,060 | 0.4337 | 0.618952 | 0.110171 | 0.180020 | — | — | — | current |
| `20261105T103853Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 283 | — | 10,000 | 23,060 | 0.4337 | 0.671857 | 0.108380 | 0.220061 | — | — | — | current |
| `20261105T103853Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 284 | — | 10,000 | 23,060 | 0.4337 | 0.640464 | 0.108518 | 0.239218 | — | — | — | current |
| `20261105T140242Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 285 | — | 10,000 | 23,060 | 0.4337 | 0.637418 | 0.109111 | 0.205021 | — | — | — | current |
| `20261105T140242Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 286 | — | 10,000 | 23,060 | 0.4337 | 0.635572 | 0.109800 | 0.186477 | — | — | — | current |
| `20261105T140242Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 287 | — | 10,000 | 23,060 | 0.4337 | 0.641611 | 0.109219 | 0.194959 | — | — | — | current |
| `20261105T140242Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 288 | — | 10,000 | 23,060 | 0.4337 | 0.630358 | 0.109135 | 0.201946 | — | — | — | current |
| `20261105T140242Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 289 | — | 10,000 | 23,060 | 0.4337 | 0.575276 | 0.111642 | 0.168992 | — | — | — | current |
| `20261105T140242Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 290 | — | 10,000 | 23,060 | 0.4337 | 0.650158 | 0.108935 | 0.213333 | — | — | — | current |
| `20261105T140242Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 291 | — | 10,000 | 23,060 | 0.4337 | 0.684445 | 0.107892 | 0.223675 | — | — | — | current |
| `20261105T140242Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 292 | — | 10,000 | 23,060 | 0.4337 | 0.620843 | 0.109254 | 0.212999 | — | — | — | current |
| `20261105T140242Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 293 | — | 10,000 | 23,060 | 0.4337 | 0.604985 | 0.110203 | 0.183985 | — | — | — | current |
| `20261105T140242Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 294 | — | 10,000 | 23,060 | 0.4337 | 0.594736 | 0.110295 | 0.204860 | — | — | — | current |
| `20261105T140242Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 295 | — | 10,000 | 23,060 | 0.4337 | 0.609715 | 0.110682 | 0.176165 | — | — | — | current |
| `20261105T140242Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 296 | — | 10,000 | 23,060 | 0.4337 | 0.634201 | 0.109881 | 0.182545 | — | — | — | current |
| `20261105T111110Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 297 | — | 10,000 | 23,060 | 0.4337 | 0.646269 | 0.108130 | 0.234052 | — | — | — | current |
| `20261105T111110Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 298 | — | 10,000 | 23,060 | 0.4337 | 0.622214 | 0.109145 | 0.217620 | — | — | — | current |
| `20261105T111110Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 299 | — | 10,000 | 23,060 | 0.4337 | 0.658553 | 0.108034 | 0.244992 | — | — | — | current |
| `20261105T111110Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 300 | — | 10,000 | 23,060 | 0.4337 | 0.576476 | 0.111617 | 0.165858 | — | — | — | current |
| `20261105T111110Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 301 | — | 10,000 | 23,060 | 0.4337 | 0.573950 | 0.111781 | 0.158222 | — | — | — | current |
| `20261105T111110Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 302 | — | 10,000 | 23,060 | 0.4337 | 0.630671 | 0.109887 | 0.181942 | — | — | — | current |
| `20261105T111110Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 303 | — | 10,000 | 23,060 | 0.4337 | 0.621739 | 0.109700 | 0.196324 | — | — | — | current |
| `20261105T111110Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 304 | — | 10,000 | 23,060 | 0.4337 | 0.552358 | 0.111681 | 0.180359 | — | — | — | current |
| `20261105T111110Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 305 | — | 10,000 | 23,060 | 0.4337 | 0.574187 | 0.111132 | 0.181858 | — | — | — | current |
| `20261105T111110Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 306 | — | 10,000 | 23,060 | 0.4337 | 0.589933 | 0.111236 | 0.178357 | — | — | — | current |
| `20261105T111110Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 307 | — | 10,000 | 23,060 | 0.4337 | 0.597567 | 0.110361 | 0.191910 | — | — | — | current |
| `20261105T111110Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 308 | — | 10,000 | 23,060 | 0.4337 | 0.640311 | 0.109177 | 0.198064 | — | — | — | current |
| `20261105T114320Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 309 | — | 10,000 | 23,060 | 0.4337 | 0.662952 | 0.107768 | 0.237728 | — | — | — | current |
| `20261105T114320Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 310 | — | 10,000 | 23,060 | 0.4337 | 0.642614 | 0.108853 | 0.208165 | — | — | — | current |
| `20261105T114320Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 311 | — | 10,000 | 23,060 | 0.4337 | 0.627083 | 0.109388 | 0.201238 | — | — | — | current |
| `20261105T114320Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 312 | — | 10,000 | 23,060 | 0.4337 | 0.662530 | 0.108212 | 0.216786 | — | — | — | current |
| `20261105T114320Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 313 | — | 10,000 | 23,060 | 0.4337 | 0.630967 | 0.109712 | 0.192718 | — | — | — | current |
| `20261105T114320Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 314 | — | 10,000 | 23,060 | 0.4337 | 0.626666 | 0.109292 | 0.217591 | — | — | — | current |
| `20261105T114320Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 315 | — | 10,000 | 23,060 | 0.4337 | 0.593177 | 0.110629 | 0.179971 | — | — | — | current |
| `20261105T114320Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 316 | — | 10,000 | 23,060 | 0.4337 | 0.677681 | 0.108144 | 0.255629 | — | — | — | current |
| `20261105T114320Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 317 | — | 10,000 | 23,060 | 0.4337 | 0.590919 | 0.110557 | 0.190402 | — | — | — | current |
| `20261105T114320Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 318 | — | 10,000 | 23,060 | 0.4337 | 0.598050 | 0.110593 | 0.181532 | — | — | — | current |
| `20261105T114320Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 319 | — | 10,000 | 23,060 | 0.4337 | 0.637695 | 0.109718 | 0.180442 | — | — | — | current |
| `20261105T114320Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 320 | — | 10,000 | 23,060 | 0.4337 | 0.617223 | 0.110305 | 0.174913 | — | — | — | current |
| `20261105T114647Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 321 | — | 10,000 | 23,060 | 0.4337 | 0.644513 | 0.108964 | 0.202761 | — | — | — | current |
| `20261105T114647Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 322 | — | 10,000 | 23,060 | 0.4337 | 0.662271 | 0.107334 | 0.250594 | — | — | — | current |
| `20261105T114647Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 323 | — | 10,000 | 23,060 | 0.4337 | 0.606051 | 0.110087 | 0.191360 | — | — | — | current |
| `20261105T114647Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 324 | — | 10,000 | 23,060 | 0.4337 | 0.609276 | 0.110377 | 0.183772 | — | — | — | current |
| `20261105T114647Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 325 | — | 10,000 | 23,060 | 0.4337 | 0.662351 | 0.108109 | 0.234173 | — | — | — | current |
| `20261105T114647Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 326 | — | 10,000 | 23,060 | 0.4337 | 0.622375 | 0.109795 | 0.193268 | — | — | — | current |
| `20261105T114647Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 327 | — | 10,000 | 23,060 | 0.4337 | 0.599054 | 0.110024 | 0.195472 | — | — | — | current |
| `20261105T114647Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 328 | — | 10,000 | 23,060 | 0.4337 | 0.653706 | 0.109091 | 0.201724 | — | — | — | current |
| `20261105T114647Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 329 | — | 10,000 | 23,060 | 0.4337 | 0.653491 | 0.109263 | 0.189167 | — | — | — | current |
| `20261105T114647Z` | pilot2-phase2 | classification | lapse | auto | eudirectlapse | `B_ft30` | fine-tuned | 30 | 330 | — | 10,000 | 23,060 | 0.4337 | 0.637274 | 0.109278 | 0.199439 | — | — | — | current |
| `20261031T021845Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 43 | — | 10,000 | 29,317 | 0.3411 | 0.946119 | 0.081966 | 0.892155 | — | — | — | current |
| `20261031T021845Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 44 | — | 10,000 | 29,317 | 0.3411 | 0.945127 | 0.085596 | 0.888607 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 45 | — | 10,000 | 29,317 | 0.3411 | 0.947588 | 0.083166 | 0.887693 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 46 | — | 10,000 | 29,317 | 0.3411 | 0.945489 | 0.083827 | 0.891712 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 47 | — | 10,000 | 29,317 | 0.3411 | 0.941964 | 0.084347 | 0.870418 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 48 | — | 10,000 | 29,317 | 0.3411 | 0.936582 | 0.087933 | 0.864323 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 49 | — | 10,000 | 29,317 | 0.3411 | 0.938800 | 0.089039 | 0.858314 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 50 | — | 10,000 | 29,317 | 0.3411 | 0.927479 | 0.097529 | 0.840484 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 51 | — | 10,000 | 29,317 | 0.3411 | 0.933581 | 0.090152 | 0.857902 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 52 | — | 10,000 | 29,317 | 0.3411 | 0.947797 | 0.083396 | 0.891423 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 53 | — | 10,000 | 29,317 | 0.3411 | 0.933142 | 0.093951 | 0.853634 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 54 | — | 10,000 | 29,317 | 0.3411 | 0.942381 | 0.086750 | 0.878073 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 55 | — | 10,000 | 29,317 | 0.3411 | 0.952987 | 0.076038 | 0.894905 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 56 | — | 10,000 | 29,317 | 0.3411 | 0.952476 | 0.075067 | 0.897765 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 57 | — | 10,000 | 29,317 | 0.3411 | 0.940627 | 0.087173 | 0.874610 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 58 | — | 10,000 | 29,317 | 0.3411 | 0.939827 | 0.083619 | 0.871424 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 59 | — | 10,000 | 29,317 | 0.3411 | 0.950803 | 0.074933 | 0.893171 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 60 | — | 10,000 | 29,317 | 0.3411 | 0.959097 | 0.071840 | 0.914319 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 61 | — | 10,000 | 29,317 | 0.3411 | 0.948491 | 0.078370 | 0.898609 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 62 | — | 10,000 | 29,317 | 0.3411 | 0.940963 | 0.087002 | 0.870634 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 63 | — | 10,000 | 29,317 | 0.3411 | 0.940329 | 0.089677 | 0.883238 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 64 | — | 10,000 | 29,317 | 0.3411 | 0.937800 | 0.083695 | 0.860593 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 65 | — | 10,000 | 29,317 | 0.3411 | 0.934909 | 0.090847 | 0.861014 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 66 | — | 10,000 | 29,317 | 0.3411 | 0.937945 | 0.090935 | 0.865701 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 67 | — | 10,000 | 29,317 | 0.3411 | 0.940623 | 0.084826 | 0.872432 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 68 | — | 10,000 | 29,317 | 0.3411 | 0.948619 | 0.078247 | 0.882520 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 69 | — | 10,000 | 29,317 | 0.3411 | 0.943309 | 0.080109 | 0.875471 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 70 | — | 10,000 | 29,317 | 0.3411 | 0.943186 | 0.085160 | 0.887627 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 71 | — | 10,000 | 29,317 | 0.3411 | 0.945247 | 0.079190 | 0.873932 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 72 | — | 10,000 | 29,317 | 0.3411 | 0.945864 | 0.082415 | 0.886795 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 73 | — | 10,000 | 29,317 | 0.3411 | 0.948827 | 0.080102 | 0.888348 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 74 | — | 10,000 | 29,317 | 0.3411 | 0.941883 | 0.086506 | 0.875393 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 75 | — | 10,000 | 29,317 | 0.3411 | 0.930064 | 0.093807 | 0.847689 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 76 | — | 10,000 | 29,317 | 0.3411 | 0.932818 | 0.089719 | 0.845881 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 77 | — | 10,000 | 29,317 | 0.3411 | 0.951859 | 0.075166 | 0.895321 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 78 | — | 10,000 | 29,317 | 0.3411 | 0.953076 | 0.075470 | 0.897125 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 79 | — | 10,000 | 29,317 | 0.3411 | 0.942424 | 0.083079 | 0.871044 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 80 | — | 10,000 | 29,317 | 0.3411 | 0.947801 | 0.079332 | 0.897363 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 81 | — | 10,000 | 29,317 | 0.3411 | 0.946822 | 0.085433 | 0.891040 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 82 | — | 10,000 | 29,317 | 0.3411 | 0.938596 | 0.087525 | 0.873982 | — | — | — | current |
| `20261031T021845Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft3` | fine-tuned | 3 | 43 | — | 10,000 | 29,317 | 0.3411 | 0.949185 | 0.080829 | 0.897365 | — | — | — | current |
| `20261031T021845Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft3` | fine-tuned | 3 | 44 | — | 10,000 | 29,317 | 0.3411 | 0.946038 | 0.085810 | 0.893973 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft3` | fine-tuned | 3 | 45 | — | 10,000 | 29,317 | 0.3411 | 0.949862 | 0.081258 | 0.896203 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft3` | fine-tuned | 3 | 46 | — | 10,000 | 29,317 | 0.3411 | 0.947495 | 0.082411 | 0.899002 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft3` | fine-tuned | 3 | 47 | — | 10,000 | 29,317 | 0.3411 | 0.941593 | 0.084134 | 0.874424 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft3` | fine-tuned | 3 | 48 | — | 10,000 | 29,317 | 0.3411 | 0.936991 | 0.087687 | 0.864195 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft3` | fine-tuned | 3 | 49 | — | 10,000 | 29,317 | 0.3411 | 0.939226 | 0.088240 | 0.867847 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft3` | fine-tuned | 3 | 50 | — | 10,000 | 29,317 | 0.3411 | 0.934811 | 0.093173 | 0.855932 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft3` | fine-tuned | 3 | 51 | — | 10,000 | 29,317 | 0.3411 | 0.938715 | 0.087559 | 0.875284 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft3` | fine-tuned | 3 | 52 | — | 10,000 | 29,317 | 0.3411 | 0.946349 | 0.083153 | 0.887260 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft3` | fine-tuned | 3 | 53 | — | 10,000 | 29,317 | 0.3411 | 0.933329 | 0.093419 | 0.863876 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft3` | fine-tuned | 3 | 54 | — | 10,000 | 29,317 | 0.3411 | 0.941351 | 0.085926 | 0.875194 | — | — | — | current |
| `20261031T021845Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft10` | fine-tuned | 10 | 43 | — | 10,000 | 29,317 | 0.3411 | 0.951097 | 0.080458 | 0.900992 | — | — | — | current |
| `20261031T021845Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft10` | fine-tuned | 10 | 44 | — | 10,000 | 29,317 | 0.3411 | 0.946464 | 0.084983 | 0.893806 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft10` | fine-tuned | 10 | 45 | — | 10,000 | 29,317 | 0.3411 | 0.949755 | 0.082033 | 0.897619 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft10` | fine-tuned | 10 | 46 | — | 10,000 | 29,317 | 0.3411 | 0.948572 | 0.081779 | 0.902085 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft10` | fine-tuned | 10 | 47 | — | 10,000 | 29,317 | 0.3411 | 0.942266 | 0.083380 | 0.876675 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft10` | fine-tuned | 10 | 48 | — | 10,000 | 29,317 | 0.3411 | 0.937106 | 0.088269 | 0.866554 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft10` | fine-tuned | 10 | 49 | — | 10,000 | 29,317 | 0.3411 | 0.938179 | 0.088280 | 0.865499 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft10` | fine-tuned | 10 | 50 | — | 10,000 | 29,317 | 0.3411 | 0.937481 | 0.092949 | 0.861474 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft10` | fine-tuned | 10 | 51 | — | 10,000 | 29,317 | 0.3411 | 0.939069 | 0.087465 | 0.876470 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft10` | fine-tuned | 10 | 52 | — | 10,000 | 29,317 | 0.3411 | 0.947805 | 0.082150 | 0.891422 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft10` | fine-tuned | 10 | 53 | — | 10,000 | 29,317 | 0.3411 | 0.933845 | 0.092988 | 0.865667 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft10` | fine-tuned | 10 | 54 | — | 10,000 | 29,317 | 0.3411 | 0.942224 | 0.084699 | 0.872596 | — | — | — | current |
| `20261031T021845Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 43 | — | 10,000 | 29,317 | 0.3411 | 0.951833 | 0.078916 | 0.901214 | — | — | — | current |
| `20261031T021845Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 44 | — | 10,000 | 29,317 | 0.3411 | 0.946149 | 0.085267 | 0.893132 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 45 | — | 10,000 | 29,317 | 0.3411 | 0.950526 | 0.081398 | 0.897318 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 46 | — | 10,000 | 29,317 | 0.3411 | 0.950173 | 0.080752 | 0.903794 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 47 | — | 10,000 | 29,317 | 0.3411 | 0.944093 | 0.083504 | 0.880537 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 48 | — | 10,000 | 29,317 | 0.3411 | 0.939861 | 0.087237 | 0.873609 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 49 | — | 10,000 | 29,317 | 0.3411 | 0.937306 | 0.089099 | 0.865655 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 50 | — | 10,000 | 29,317 | 0.3411 | 0.937668 | 0.092126 | 0.862169 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 51 | — | 10,000 | 29,317 | 0.3411 | 0.941376 | 0.085799 | 0.879768 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 52 | — | 10,000 | 29,317 | 0.3411 | 0.949487 | 0.081215 | 0.898251 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 53 | — | 10,000 | 29,317 | 0.3411 | 0.933644 | 0.093878 | 0.864470 | — | — | — | current |
| `20261104T122235Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 54 | — | 10,000 | 29,317 | 0.3411 | 0.940959 | 0.084467 | 0.867825 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 55 | — | 10,000 | 29,317 | 0.3411 | 0.955669 | 0.074857 | 0.901503 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 56 | — | 10,000 | 29,317 | 0.3411 | 0.959054 | 0.071869 | 0.912900 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 57 | — | 10,000 | 29,317 | 0.3411 | 0.941398 | 0.087360 | 0.880915 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 58 | — | 10,000 | 29,317 | 0.3411 | 0.943471 | 0.081143 | 0.878915 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 59 | — | 10,000 | 29,317 | 0.3411 | 0.955980 | 0.071821 | 0.902930 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 60 | — | 10,000 | 29,317 | 0.3411 | 0.960642 | 0.070268 | 0.918796 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 61 | — | 10,000 | 29,317 | 0.3411 | 0.951931 | 0.075653 | 0.901019 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 62 | — | 10,000 | 29,317 | 0.3411 | 0.941568 | 0.087217 | 0.875309 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 63 | — | 10,000 | 29,317 | 0.3411 | 0.945221 | 0.088799 | 0.897023 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 64 | — | 10,000 | 29,317 | 0.3411 | 0.943028 | 0.081580 | 0.875954 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 65 | — | 10,000 | 29,317 | 0.3411 | 0.941960 | 0.087157 | 0.883234 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 66 | — | 10,000 | 29,317 | 0.3411 | 0.940231 | 0.088786 | 0.876287 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 67 | — | 10,000 | 29,317 | 0.3411 | 0.942598 | 0.084574 | 0.881611 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 68 | — | 10,000 | 29,317 | 0.3411 | 0.953587 | 0.074395 | 0.893868 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 69 | — | 10,000 | 29,317 | 0.3411 | 0.948355 | 0.076513 | 0.889699 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 70 | — | 10,000 | 29,317 | 0.3411 | 0.946860 | 0.082489 | 0.895292 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 71 | — | 10,000 | 29,317 | 0.3411 | 0.947954 | 0.078598 | 0.885785 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 72 | — | 10,000 | 29,317 | 0.3411 | 0.946830 | 0.081446 | 0.895076 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 73 | — | 10,000 | 29,317 | 0.3411 | 0.950207 | 0.078311 | 0.897594 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 74 | — | 10,000 | 29,317 | 0.3411 | 0.943505 | 0.085013 | 0.884651 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 75 | — | 10,000 | 29,317 | 0.3411 | 0.932835 | 0.092459 | 0.859421 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 76 | — | 10,000 | 29,317 | 0.3411 | 0.938975 | 0.086550 | 0.874227 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 77 | — | 10,000 | 29,317 | 0.3411 | 0.952344 | 0.075503 | 0.898923 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 78 | — | 10,000 | 29,317 | 0.3411 | 0.954831 | 0.073173 | 0.898040 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 79 | — | 10,000 | 29,317 | 0.3411 | 0.949044 | 0.079637 | 0.889540 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 80 | — | 10,000 | 29,317 | 0.3411 | 0.952272 | 0.077147 | 0.907250 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 81 | — | 10,000 | 29,317 | 0.3411 | 0.948682 | 0.083947 | 0.892872 | — | — | — | current |
| `20261104T123839Z` | pilot2-phase2 | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 82 | — | 10,000 | 29,317 | 0.3411 | 0.946077 | 0.083108 | 0.886661 | — | — | — | current |
| `coil2000_A_raw_seed42` | r1-pilot | classification | lapse | auto | coil2000 | `A_raw` | raw | — | 42 | — | 2,000 | 9,822 | 0.2036 | 0.767530 | 0.050767 | 0.187545 | — | — | — | superseded |
| `coil2000_B_in_domain_seed42` | r1-pilot | classification | lapse | auto | coil2000 | `B_in_domain` | fine-tuned | — | 42 | — | 2,000 | 9,822 | 0.2036 | 0.768962 | 0.050912 | 0.193316 | — | — | — | superseded |
| `coil2000_E_glm_seed42` | r1-pilot | classification | lapse | auto | coil2000 | `E_glm` | comparator | — | 42 | — | 2,000 | 9,822 | 0.2036 | 0.683029 | 0.055922 | 0.130695 | — | — | — | superseded |
| `coil2000_F_catboost_seed42` | r1-pilot | classification | lapse | auto | coil2000 | `F_catboost` | comparator | — | 42 | — | 2,000 | 9,822 | 0.2036 | 0.699271 | 0.051626 | 0.175306 | — | — | — | superseded |
| `eudirectlapse_A_raw_seed42` | r1-pilot | classification | lapse | auto | eudirectlapse | `A_raw` | raw | — | 42 | — | 2,000 | 23,060 | 0.0867 | 0.588090 | 0.113679 | 0.194347 | — | — | — | current |
| `eudirectlapse_B_in_domain_seed42` | r1-pilot | classification | lapse | auto | eudirectlapse | `B_in_domain` | fine-tuned | — | 42 | — | 2,000 | 23,060 | 0.0867 | 0.597603 | 0.113328 | 0.198178 | — | — | — | current |
| `eudirectlapse_E_glm_seed42` | r1-pilot | classification | lapse | auto | eudirectlapse | `E_glm` | comparator | — | 42 | — | 2,000 | 23,060 | 0.0867 | 0.574352 | 0.116278 | 0.160071 | — | — | — | current |
| `eudirectlapse_F_catboost_seed42` | r1-pilot | classification | lapse | auto | eudirectlapse | `F_catboost` | comparator | — | 42 | — | 2,000 | 23,060 | 0.0867 | 0.573768 | 0.115089 | 0.183049 | — | — | — | current |
| `spanish_motor_lapse_A_raw_seed42` | r1-pilot | classification | lapse | auto | spanish_motor_lapse | `A_raw` | raw | — | 42 | — | 2,000 | 53,502 | 0.0374 | 0.723295 | 0.197776 | 0.570771 | — | — | — | current |
| `spanish_motor_lapse_B_in_domain_seed42` | r1-pilot | classification | lapse | auto | spanish_motor_lapse | `B_in_domain` | fine-tuned | — | 42 | — | 2,000 | 53,502 | 0.0374 | 0.727187 | 0.196739 | 0.579063 | — | — | — | current |
| `spanish_motor_lapse_E_glm_seed42` | r1-pilot | classification | lapse | auto | spanish_motor_lapse | `E_glm` | comparator | — | 42 | — | 2,000 | 53,502 | 0.0374 | 0.616563 | 0.222162 | 0.446904 | — | — | — | current |
| `spanish_motor_lapse_F_catboost_seed42` | r1-pilot | classification | lapse | auto | spanish_motor_lapse | `F_catboost` | comparator | — | 42 | — | 2,000 | 53,502 | 0.0374 | 0.711423 | 0.201455 | 0.541185 | — | — | — | current |
| `uslapseagent_A_raw_seed42` | r1-pilot | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 42 | — | 2,000 | 29,317 | 0.0682 | 0.936312 | 0.087321 | 0.834384 | — | — | — | current |
| `uslapseagent_B_in_domain_seed42` | r1-pilot | classification | lapse | auto | uslapseagent | `B_in_domain` | fine-tuned | — | 42 | — | 2,000 | 29,317 | 0.0682 | 0.935505 | 0.086968 | 0.837523 | — | — | — | current |
| `uslapseagent_E_glm_seed42` | r1-pilot | classification | lapse | auto | uslapseagent | `E_glm` | comparator | — | 42 | — | 2,000 | 29,317 | 0.0682 | 0.927057 | 0.091007 | 0.817249 | — | — | — | current |
| `uslapseagent_F_catboost_seed42` | r1-pilot | classification | lapse | auto | uslapseagent | `F_catboost` | comparator | — | 42 | — | 2,000 | 29,317 | 0.0682 | 0.929690 | 0.093386 | 0.829297 | — | — | — | current |
| `20260914T010247Z` | gpu-pilot | classification | lapse | auto | uslapseagent | `A_raw` | raw | — | 42 | — | 10,000 | 29,317 | 0.3411 | 0.945717 | 0.083267 | 0.885643 | — | — | — | no-capture |
| `20260914T010247Z` | gpu-pilot | classification | lapse | auto | uslapseagent | `B_ft3` | fine-tuned | 3 | 42 | — | 10,000 | 29,317 | 0.3411 | 0.947907 | 0.082211 | 0.890446 | — | — | — | no-capture |
| `20260914T010247Z` | gpu-pilot | classification | lapse | auto | uslapseagent | `B_ft10` | fine-tuned | 10 | 42 | — | 10,000 | 29,317 | 0.3411 | 0.948269 | 0.081252 | 0.890664 | — | — | — | no-capture |
| `20260914T010247Z` | gpu-pilot | classification | lapse | auto | uslapseagent | `B_ft30` | fine-tuned | 30 | 42 | — | 10,000 | 29,317 | 0.3411 | 0.949134 | 0.081390 | 0.892279 | — | — | — | no-capture |
| — | pilot2-breadth-spanish | classification | lapse | auto | spanish_motor_lapse | `A_raw` | raw | — | — | — | — | 53,502 | — | — | — | — | — | — | — | no-capture |
| — | pilot2-breadth-spanish | classification | lapse | auto | spanish_motor_lapse | `B_ft30` | fine-tuned | — | — | — | — | 53,502 | — | — | — | — | — | — | — | no-capture |
| `20261112T164543Z` | fair-test-freq-sev | regression | frequency | v3_default | freMTPL2freq | `A_raw` | raw | 0 | 0 | 0 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.236845 | poisson_deviance | 3298.804699 | current |
| `20261112T164543Z` | fair-test-freq-sev | regression | frequency | v3_default | freMTPL2freq | `A_raw` | raw | 0 | 0 | 1 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.231474 | poisson_deviance | 3408.723228 | current |
| `20261112T164543Z` | fair-test-freq-sev | regression | frequency | v3_default | freMTPL2freq | `A_raw` | raw | 0 | 0 | 2 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.249042 | poisson_deviance | 3529.733713 | current |
| `20261112T164543Z` | fair-test-freq-sev | regression | frequency | v3_default | freMTPL2freq | `A_raw` | raw | 0 | 0 | 3 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.228446 | poisson_deviance | 3265.848208 | current |
| `20261112T164543Z` | fair-test-freq-sev | regression | frequency | v3_default | freMTPL2freq | `A_raw` | raw | 0 | 0 | 4 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.256012 | poisson_deviance | 3957.971837 | current |
| `20261112T164543Z` | fair-test-freq-sev | regression | frequency | v3_default | freMTPL2freq | `A_raw` | raw | 0 | 1 | 0 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.237048 | poisson_deviance | 3532.406676 | current |
| `20261112T164543Z` | fair-test-freq-sev | regression | frequency | v3_default | freMTPL2freq | `A_raw` | raw | 0 | 1 | 1 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.231254 | poisson_deviance | 3435.363587 | current |
| `20261112T164543Z` | fair-test-freq-sev | regression | frequency | v3_default | freMTPL2freq | `A_raw` | raw | 0 | 1 | 2 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.249326 | poisson_deviance | 3731.044925 | current |
| `20261112T164543Z` | fair-test-freq-sev | regression | frequency | v3_default | freMTPL2freq | `A_raw` | raw | 0 | 1 | 3 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.228621 | poisson_deviance | 3349.461024 | current |
| `20261112T164543Z` | fair-test-freq-sev | regression | frequency | v3_default | freMTPL2freq | `A_raw` | raw | 0 | 1 | 4 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.256131 | poisson_deviance | 4040.856783 | current |
| `20261112T164543Z` | fair-test-freq-sev | regression | frequency | v3_default | freMTPL2freq | `A_raw` | raw | 0 | 2 | 0 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.238043 | poisson_deviance | 3607.408746 | current |
| `20261112T164543Z` | fair-test-freq-sev | regression | frequency | v3_default | freMTPL2freq | `A_raw` | raw | 0 | 2 | 1 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.232401 | poisson_deviance | 3603.669405 | current |
| `20261112T164543Z` | fair-test-freq-sev | regression | frequency | v3_default | freMTPL2freq | `A_raw` | raw | 0 | 2 | 2 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.248950 | poisson_deviance | 3547.765850 | current |
| `20261112T164543Z` | fair-test-freq-sev | regression | frequency | v3_default | freMTPL2freq | `A_raw` | raw | 0 | 2 | 3 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.229427 | poisson_deviance | 3585.350219 | current |
| `20261112T164543Z` | fair-test-freq-sev | regression | frequency | v3_default | freMTPL2freq | `A_raw` | raw | 0 | 2 | 4 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.256071 | poisson_deviance | 3991.657987 | current |
| `20261112T164543Z` | fair-test-freq-sev | regression | frequency | v3_default | freMTPL2freq | `B_ft30` | fine-tuned | 30 | 0 | 0 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.235685 | poisson_deviance | 3125.437545 | current |
| `20261112T164543Z` | fair-test-freq-sev | regression | frequency | v3_default | freMTPL2freq | `B_ft30` | fine-tuned | 30 | 0 | 1 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.231297 | poisson_deviance | 3293.666096 | current |
| `20261112T164543Z` | fair-test-freq-sev | regression | frequency | v3_default | freMTPL2freq | `B_ft30` | fine-tuned | 30 | 0 | 2 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.248179 | poisson_deviance | 3276.886982 | current |
| `20261112T164543Z` | fair-test-freq-sev | regression | frequency | v3_default | freMTPL2freq | `B_ft30` | fine-tuned | 30 | 0 | 3 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.226856 | poisson_deviance | 3029.071336 | current |
| `20261112T164543Z` | fair-test-freq-sev | regression | frequency | v3_default | freMTPL2freq | `B_ft30` | fine-tuned | 30 | 0 | 4 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.254429 | poisson_deviance | 3576.050619 | current |
| `20261112T164543Z` | fair-test-freq-sev | regression | frequency | v3_default | freMTPL2freq | `B_ft30` | fine-tuned | 30 | 1 | 0 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.235368 | poisson_deviance | 3124.624093 | current |
| `20261112T164543Z` | fair-test-freq-sev | regression | frequency | v3_default | freMTPL2freq | `B_ft30` | fine-tuned | 30 | 1 | 1 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.229885 | poisson_deviance | 3038.666061 | current |
| `20261112T164543Z` | fair-test-freq-sev | regression | frequency | v3_default | freMTPL2freq | `B_ft30` | fine-tuned | 30 | 1 | 2 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.247396 | poisson_deviance | 3209.507943 | current |
| `20261112T164543Z` | fair-test-freq-sev | regression | frequency | v3_default | freMTPL2freq | `B_ft30` | fine-tuned | 30 | 1 | 3 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.228190 | poisson_deviance | 3175.972730 | current |
| `20261112T164543Z` | fair-test-freq-sev | regression | frequency | v3_default | freMTPL2freq | `B_ft30` | fine-tuned | 30 | 1 | 4 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.254436 | poisson_deviance | 3477.865503 | current |
| `20261112T164543Z` | fair-test-freq-sev | regression | frequency | v3_default | freMTPL2freq | `B_ft30` | fine-tuned | 30 | 2 | 0 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.236324 | poisson_deviance | 3147.816116 | current |
| `20261112T164543Z` | fair-test-freq-sev | regression | frequency | v3_default | freMTPL2freq | `B_ft30` | fine-tuned | 30 | 2 | 1 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.230881 | poisson_deviance | 3127.902372 | current |
| `20261112T164543Z` | fair-test-freq-sev | regression | frequency | v3_default | freMTPL2freq | `B_ft30` | fine-tuned | 30 | 2 | 2 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.247795 | poisson_deviance | 3365.880188 | current |
| `20261112T164543Z` | fair-test-freq-sev | regression | frequency | v3_default | freMTPL2freq | `B_ft30` | fine-tuned | 30 | 2 | 3 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.228054 | poisson_deviance | 3189.069326 | current |
| `20261112T164543Z` | fair-test-freq-sev | regression | frequency | v3_default | freMTPL2freq | `B_ft30` | fine-tuned | 30 | 2 | 4 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.254312 | poisson_deviance | 3418.033885 | current |
| `20261112T210029Z` | fair-test-freq-sev | regression | severity | v3_default | freMTPL2sev | `A_raw` | raw | 0 | 0 | 0 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.104350 | rmse | 1.104350 | current |
| `20261112T210029Z` | fair-test-freq-sev | regression | severity | v3_default | freMTPL2sev | `A_raw` | raw | 0 | 0 | 1 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.127278 | rmse | 1.127278 | current |
| `20261112T210029Z` | fair-test-freq-sev | regression | severity | v3_default | freMTPL2sev | `A_raw` | raw | 0 | 0 | 2 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.133119 | rmse | 1.133119 | current |
| `20261112T210029Z` | fair-test-freq-sev | regression | severity | v3_default | freMTPL2sev | `A_raw` | raw | 0 | 0 | 3 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.101188 | rmse | 1.101188 | current |
| `20261112T210029Z` | fair-test-freq-sev | regression | severity | v3_default | freMTPL2sev | `A_raw` | raw | 0 | 0 | 4 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.132815 | rmse | 1.132815 | current |
| `20261112T210029Z` | fair-test-freq-sev | regression | severity | v3_default | freMTPL2sev | `A_raw` | raw | 0 | 1 | 0 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.104307 | rmse | 1.104307 | current |
| `20261112T210029Z` | fair-test-freq-sev | regression | severity | v3_default | freMTPL2sev | `A_raw` | raw | 0 | 1 | 1 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.126382 | rmse | 1.126382 | current |
| `20261112T210029Z` | fair-test-freq-sev | regression | severity | v3_default | freMTPL2sev | `A_raw` | raw | 0 | 1 | 2 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.133267 | rmse | 1.133267 | current |
| `20261112T210029Z` | fair-test-freq-sev | regression | severity | v3_default | freMTPL2sev | `A_raw` | raw | 0 | 1 | 3 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.100143 | rmse | 1.100143 | current |
| `20261112T210029Z` | fair-test-freq-sev | regression | severity | v3_default | freMTPL2sev | `A_raw` | raw | 0 | 1 | 4 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.134226 | rmse | 1.134226 | current |
| `20261112T210029Z` | fair-test-freq-sev | regression | severity | v3_default | freMTPL2sev | `A_raw` | raw | 0 | 2 | 0 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.104446 | rmse | 1.104446 | current |
| `20261112T210029Z` | fair-test-freq-sev | regression | severity | v3_default | freMTPL2sev | `A_raw` | raw | 0 | 2 | 1 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.132231 | rmse | 1.132231 | current |
| `20261112T210029Z` | fair-test-freq-sev | regression | severity | v3_default | freMTPL2sev | `A_raw` | raw | 0 | 2 | 2 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.132938 | rmse | 1.132938 | current |
| `20261112T210029Z` | fair-test-freq-sev | regression | severity | v3_default | freMTPL2sev | `A_raw` | raw | 0 | 2 | 3 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.100065 | rmse | 1.100065 | current |
| `20261112T210029Z` | fair-test-freq-sev | regression | severity | v3_default | freMTPL2sev | `A_raw` | raw | 0 | 2 | 4 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.134851 | rmse | 1.134851 | current |
| `20261112T210029Z` | fair-test-freq-sev | regression | severity | v3_default | freMTPL2sev | `B_ft30` | fine-tuned | 30 | 0 | 0 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.128473 | rmse | 1.128473 | current |
| `20261112T210029Z` | fair-test-freq-sev | regression | severity | v3_default | freMTPL2sev | `B_ft30` | fine-tuned | 30 | 0 | 1 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.133935 | rmse | 1.133935 | current |
| `20261112T210029Z` | fair-test-freq-sev | regression | severity | v3_default | freMTPL2sev | `B_ft30` | fine-tuned | 30 | 0 | 2 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.139615 | rmse | 1.139615 | current |
| `20261112T210029Z` | fair-test-freq-sev | regression | severity | v3_default | freMTPL2sev | `B_ft30` | fine-tuned | 30 | 0 | 3 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.101405 | rmse | 1.101405 | current |
| `20261112T210029Z` | fair-test-freq-sev | regression | severity | v3_default | freMTPL2sev | `B_ft30` | fine-tuned | 30 | 0 | 4 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.153342 | rmse | 1.153342 | current |
| `20261112T210029Z` | fair-test-freq-sev | regression | severity | v3_default | freMTPL2sev | `B_ft30` | fine-tuned | 30 | 1 | 0 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.107560 | rmse | 1.107560 | current |
| `20261112T210029Z` | fair-test-freq-sev | regression | severity | v3_default | freMTPL2sev | `B_ft30` | fine-tuned | 30 | 1 | 1 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.131869 | rmse | 1.131869 | current |
| `20261112T210029Z` | fair-test-freq-sev | regression | severity | v3_default | freMTPL2sev | `B_ft30` | fine-tuned | 30 | 1 | 2 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.150114 | rmse | 1.150114 | current |
| `20261112T210029Z` | fair-test-freq-sev | regression | severity | v3_default | freMTPL2sev | `B_ft30` | fine-tuned | 30 | 1 | 3 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.127392 | rmse | 1.127392 | current |
| `20261112T210029Z` | fair-test-freq-sev | regression | severity | v3_default | freMTPL2sev | `B_ft30` | fine-tuned | 30 | 1 | 4 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.134015 | rmse | 1.134015 | current |
| `20261112T210029Z` | fair-test-freq-sev | regression | severity | v3_default | freMTPL2sev | `B_ft30` | fine-tuned | 30 | 2 | 0 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.112120 | rmse | 1.112120 | current |
| `20261112T210029Z` | fair-test-freq-sev | regression | severity | v3_default | freMTPL2sev | `B_ft30` | fine-tuned | 30 | 2 | 1 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.145289 | rmse | 1.145289 | current |
| `20261112T210029Z` | fair-test-freq-sev | regression | severity | v3_default | freMTPL2sev | `B_ft30` | fine-tuned | 30 | 2 | 2 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.137151 | rmse | 1.137151 | current |
| `20261112T210029Z` | fair-test-freq-sev | regression | severity | v3_default | freMTPL2sev | `B_ft30` | fine-tuned | 30 | 2 | 3 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.111674 | rmse | 1.111674 | current |
| `20261112T210029Z` | fair-test-freq-sev | regression | severity | v3_default | freMTPL2sev | `B_ft30` | fine-tuned | 30 | 2 | 4 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.141757 | rmse | 1.141757 | current |
| `20261112T184155Z` | fair-test-freq-sev | regression | frequency | v3_default | spanish_motor_freq | `A_raw` | raw | 0 | 0 | 0 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.718442 | poisson_deviance | 9596.613595 | current |
| `20261112T184155Z` | fair-test-freq-sev | regression | frequency | v3_default | spanish_motor_freq | `A_raw` | raw | 0 | 0 | 1 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.747242 | poisson_deviance | 9508.845876 | current |
| `20261112T184155Z` | fair-test-freq-sev | regression | frequency | v3_default | spanish_motor_freq | `A_raw` | raw | 0 | 0 | 2 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.804667 | poisson_deviance | 10108.663272 | current |
| `20261112T184155Z` | fair-test-freq-sev | regression | frequency | v3_default | spanish_motor_freq | `A_raw` | raw | 0 | 0 | 3 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.806714 | poisson_deviance | 10865.261753 | current |
| `20261112T184155Z` | fair-test-freq-sev | regression | frequency | v3_default | spanish_motor_freq | `A_raw` | raw | 0 | 0 | 4 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.768948 | poisson_deviance | 9523.444357 | current |
| `20261112T184155Z` | fair-test-freq-sev | regression | frequency | v3_default | spanish_motor_freq | `A_raw` | raw | 0 | 1 | 0 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.721344 | poisson_deviance | 10452.522757 | current |
| `20261112T184155Z` | fair-test-freq-sev | regression | frequency | v3_default | spanish_motor_freq | `A_raw` | raw | 0 | 1 | 1 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.741959 | poisson_deviance | 9462.187054 | current |
| `20261112T184155Z` | fair-test-freq-sev | regression | frequency | v3_default | spanish_motor_freq | `A_raw` | raw | 0 | 1 | 2 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.806382 | poisson_deviance | 10289.990827 | current |
| `20261112T184155Z` | fair-test-freq-sev | regression | frequency | v3_default | spanish_motor_freq | `A_raw` | raw | 0 | 1 | 3 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.810013 | poisson_deviance | 10711.074550 | current |
| `20261112T184155Z` | fair-test-freq-sev | regression | frequency | v3_default | spanish_motor_freq | `A_raw` | raw | 0 | 1 | 4 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.772244 | poisson_deviance | 9815.092301 | current |
| `20261112T184155Z` | fair-test-freq-sev | regression | frequency | v3_default | spanish_motor_freq | `A_raw` | raw | 0 | 2 | 0 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.718696 | poisson_deviance | 9911.949897 | current |
| `20261112T184155Z` | fair-test-freq-sev | regression | frequency | v3_default | spanish_motor_freq | `A_raw` | raw | 0 | 2 | 1 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.747853 | poisson_deviance | 9559.834805 | current |
| `20261112T184155Z` | fair-test-freq-sev | regression | frequency | v3_default | spanish_motor_freq | `A_raw` | raw | 0 | 2 | 2 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.803102 | poisson_deviance | 9937.872993 | current |
| `20261112T184155Z` | fair-test-freq-sev | regression | frequency | v3_default | spanish_motor_freq | `A_raw` | raw | 0 | 2 | 3 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.808775 | poisson_deviance | 10690.374713 | current |
| `20261112T184155Z` | fair-test-freq-sev | regression | frequency | v3_default | spanish_motor_freq | `A_raw` | raw | 0 | 2 | 4 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.773032 | poisson_deviance | 9852.082910 | current |
| `20261112T184155Z` | fair-test-freq-sev | regression | frequency | v3_default | spanish_motor_freq | `B_ft30` | fine-tuned | 30 | 0 | 0 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.724671 | poisson_deviance | 10076.026667 | current |
| `20261112T184155Z` | fair-test-freq-sev | regression | frequency | v3_default | spanish_motor_freq | `B_ft30` | fine-tuned | 30 | 0 | 1 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.740128 | poisson_deviance | 8819.087255 | current |
| `20261112T184155Z` | fair-test-freq-sev | regression | frequency | v3_default | spanish_motor_freq | `B_ft30` | fine-tuned | 30 | 0 | 2 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.809366 | poisson_deviance | 10629.744185 | current |
| `20261112T184155Z` | fair-test-freq-sev | regression | frequency | v3_default | spanish_motor_freq | `B_ft30` | fine-tuned | 30 | 0 | 3 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.797125 | poisson_deviance | 10039.339996 | current |
| `20261112T184155Z` | fair-test-freq-sev | regression | frequency | v3_default | spanish_motor_freq | `B_ft30` | fine-tuned | 30 | 0 | 4 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.763471 | poisson_deviance | 9293.744837 | current |
| `20261112T184155Z` | fair-test-freq-sev | regression | frequency | v3_default | spanish_motor_freq | `B_ft30` | fine-tuned | 30 | 1 | 0 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.713979 | poisson_deviance | 9167.406264 | current |
| `20261112T184155Z` | fair-test-freq-sev | regression | frequency | v3_default | spanish_motor_freq | `B_ft30` | fine-tuned | 30 | 1 | 1 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.736475 | poisson_deviance | 8973.467958 | current |
| `20261112T184155Z` | fair-test-freq-sev | regression | frequency | v3_default | spanish_motor_freq | `B_ft30` | fine-tuned | 30 | 1 | 2 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.800218 | poisson_deviance | 9534.867073 | current |
| `20261112T184155Z` | fair-test-freq-sev | regression | frequency | v3_default | spanish_motor_freq | `B_ft30` | fine-tuned | 30 | 1 | 3 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.802926 | poisson_deviance | 9805.103632 | current |
| `20261112T184155Z` | fair-test-freq-sev | regression | frequency | v3_default | spanish_motor_freq | `B_ft30` | fine-tuned | 30 | 1 | 4 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.766325 | poisson_deviance | 9183.531693 | current |
| `20261112T184155Z` | fair-test-freq-sev | regression | frequency | v3_default | spanish_motor_freq | `B_ft30` | fine-tuned | 30 | 2 | 0 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.713140 | poisson_deviance | 9308.577326 | current |
| `20261112T184155Z` | fair-test-freq-sev | regression | frequency | v3_default | spanish_motor_freq | `B_ft30` | fine-tuned | 30 | 2 | 1 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.744188 | poisson_deviance | 9007.908842 | current |
| `20261112T184155Z` | fair-test-freq-sev | regression | frequency | v3_default | spanish_motor_freq | `B_ft30` | fine-tuned | 30 | 2 | 2 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.798864 | poisson_deviance | 9371.790241 | current |
| `20261112T184155Z` | fair-test-freq-sev | regression | frequency | v3_default | spanish_motor_freq | `B_ft30` | fine-tuned | 30 | 2 | 3 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.794410 | poisson_deviance | 9717.443597 | current |
| `20261112T184155Z` | fair-test-freq-sev | regression | frequency | v3_default | spanish_motor_freq | `B_ft30` | fine-tuned | 30 | 2 | 4 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.783091 | poisson_deviance | 11171.829258 | current |
| `20261112T220641Z` | fair-test-freq-sev | regression | severity | v3_default | spanish_motor_severity | `A_raw` | raw | 0 | 0 | 0 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.498623 | weighted_rmse | 0.694995 | current |
| `20261112T220641Z` | fair-test-freq-sev | regression | severity | v3_default | spanish_motor_severity | `A_raw` | raw | 0 | 0 | 1 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.506556 | weighted_rmse | 0.669337 | current |
| `20261112T220641Z` | fair-test-freq-sev | regression | severity | v3_default | spanish_motor_severity | `A_raw` | raw | 0 | 0 | 2 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.489356 | weighted_rmse | 0.643606 | current |
| `20261112T220641Z` | fair-test-freq-sev | regression | severity | v3_default | spanish_motor_severity | `A_raw` | raw | 0 | 0 | 3 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.470423 | weighted_rmse | 0.601799 | current |
| `20261112T220641Z` | fair-test-freq-sev | regression | severity | v3_default | spanish_motor_severity | `A_raw` | raw | 0 | 0 | 4 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.489297 | weighted_rmse | 0.640049 | current |
| `20261112T220641Z` | fair-test-freq-sev | regression | severity | v3_default | spanish_motor_severity | `A_raw` | raw | 0 | 1 | 0 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.499141 | weighted_rmse | 0.697067 | current |
| `20261112T220641Z` | fair-test-freq-sev | regression | severity | v3_default | spanish_motor_severity | `A_raw` | raw | 0 | 1 | 1 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.506360 | weighted_rmse | 0.668652 | current |
| `20261112T220641Z` | fair-test-freq-sev | regression | severity | v3_default | spanish_motor_severity | `A_raw` | raw | 0 | 1 | 2 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.489448 | weighted_rmse | 0.644204 | current |
| `20261112T220641Z` | fair-test-freq-sev | regression | severity | v3_default | spanish_motor_severity | `A_raw` | raw | 0 | 1 | 3 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.470445 | weighted_rmse | 0.601539 | current |
| `20261112T220641Z` | fair-test-freq-sev | regression | severity | v3_default | spanish_motor_severity | `A_raw` | raw | 0 | 1 | 4 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.489003 | weighted_rmse | 0.639641 | current |
| `20261112T220641Z` | fair-test-freq-sev | regression | severity | v3_default | spanish_motor_severity | `A_raw` | raw | 0 | 2 | 0 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.498956 | weighted_rmse | 0.696672 | current |
| `20261112T220641Z` | fair-test-freq-sev | regression | severity | v3_default | spanish_motor_severity | `A_raw` | raw | 0 | 2 | 1 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.506745 | weighted_rmse | 0.669249 | current |
| `20261112T220641Z` | fair-test-freq-sev | regression | severity | v3_default | spanish_motor_severity | `A_raw` | raw | 0 | 2 | 2 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.489520 | weighted_rmse | 0.644480 | current |
| `20261112T220641Z` | fair-test-freq-sev | regression | severity | v3_default | spanish_motor_severity | `A_raw` | raw | 0 | 2 | 3 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.470703 | weighted_rmse | 0.602954 | current |
| `20261112T220641Z` | fair-test-freq-sev | regression | severity | v3_default | spanish_motor_severity | `A_raw` | raw | 0 | 2 | 4 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.489230 | weighted_rmse | 0.640694 | current |
| `20261112T220641Z` | fair-test-freq-sev | regression | severity | v3_default | spanish_motor_severity | `B_ft30` | fine-tuned | 30 | 0 | 0 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.497153 | weighted_rmse | 0.670717 | current |
| `20261112T220641Z` | fair-test-freq-sev | regression | severity | v3_default | spanish_motor_severity | `B_ft30` | fine-tuned | 30 | 0 | 1 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.508753 | weighted_rmse | 0.669019 | current |
| `20261112T220641Z` | fair-test-freq-sev | regression | severity | v3_default | spanish_motor_severity | `B_ft30` | fine-tuned | 30 | 0 | 2 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.484653 | weighted_rmse | 0.631862 | current |
| `20261112T220641Z` | fair-test-freq-sev | regression | severity | v3_default | spanish_motor_severity | `B_ft30` | fine-tuned | 30 | 0 | 3 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.469667 | weighted_rmse | 0.604178 | current |
| `20261112T220641Z` | fair-test-freq-sev | regression | severity | v3_default | spanish_motor_severity | `B_ft30` | fine-tuned | 30 | 0 | 4 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.489337 | weighted_rmse | 0.640766 | current |
| `20261112T220641Z` | fair-test-freq-sev | regression | severity | v3_default | spanish_motor_severity | `B_ft30` | fine-tuned | 30 | 1 | 0 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.493172 | weighted_rmse | 0.672985 | current |
| `20261112T220641Z` | fair-test-freq-sev | regression | severity | v3_default | spanish_motor_severity | `B_ft30` | fine-tuned | 30 | 1 | 1 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.562549 | weighted_rmse | 0.649558 | current |
| `20261112T220641Z` | fair-test-freq-sev | regression | severity | v3_default | spanish_motor_severity | `B_ft30` | fine-tuned | 30 | 1 | 2 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.490006 | weighted_rmse | 0.648943 | current |
| `20261112T220641Z` | fair-test-freq-sev | regression | severity | v3_default | spanish_motor_severity | `B_ft30` | fine-tuned | 30 | 1 | 3 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.466924 | weighted_rmse | 0.581142 | current |
| `20261112T220641Z` | fair-test-freq-sev | regression | severity | v3_default | spanish_motor_severity | `B_ft30` | fine-tuned | 30 | 1 | 4 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.483303 | weighted_rmse | 0.633852 | current |
| `20261112T220641Z` | fair-test-freq-sev | regression | severity | v3_default | spanish_motor_severity | `B_ft30` | fine-tuned | 30 | 2 | 0 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.497386 | weighted_rmse | 0.686378 | current |
| `20261112T220641Z` | fair-test-freq-sev | regression | severity | v3_default | spanish_motor_severity | `B_ft30` | fine-tuned | 30 | 2 | 1 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.509178 | weighted_rmse | 0.647171 | current |
| `20261112T220641Z` | fair-test-freq-sev | regression | severity | v3_default | spanish_motor_severity | `B_ft30` | fine-tuned | 30 | 2 | 2 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.491352 | weighted_rmse | 0.634602 | current |
| `20261112T220641Z` | fair-test-freq-sev | regression | severity | v3_default | spanish_motor_severity | `B_ft30` | fine-tuned | 30 | 2 | 3 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.465540 | weighted_rmse | 0.577898 | current |
| `20261112T220641Z` | fair-test-freq-sev | regression | severity | v3_default | spanish_motor_severity | `B_ft30` | fine-tuned | 30 | 2 | 4 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.490831 | weighted_rmse | 0.644217 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `E_glm` | comparator | — | 0 | 0 | 542,410 | 678,013 | 0.8000 | — | — | — | 0.235525 | poisson_deviance | 3098.731410 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `E_glm` | comparator | — | 0 | 1 | 542,410 | 678,013 | 0.8000 | — | — | — | 0.229466 | poisson_deviance | 2978.811012 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `E_glm` | comparator | — | 0 | 2 | 542,410 | 678,013 | 0.8000 | — | — | — | 0.246681 | poisson_deviance | 3173.370036 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `E_glm` | comparator | — | 1 | 0 | 542,410 | 678,013 | 0.8000 | — | — | — | 0.235525 | poisson_deviance | 3098.731410 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `E_glm` | comparator | — | 1 | 1 | 542,410 | 678,013 | 0.8000 | — | — | — | 0.229466 | poisson_deviance | 2978.811012 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `E_glm` | comparator | — | 1 | 2 | 542,410 | 678,013 | 0.8000 | — | — | — | 0.246681 | poisson_deviance | 3173.370036 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `E_glm` | comparator | — | 2 | 0 | 542,410 | 678,013 | 0.8000 | — | — | — | 0.235525 | poisson_deviance | 3098.731410 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `E_glm` | comparator | — | 2 | 1 | 542,410 | 678,013 | 0.8000 | — | — | — | 0.229466 | poisson_deviance | 2978.811012 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `E_glm` | comparator | — | 2 | 2 | 542,410 | 678,013 | 0.8000 | — | — | — | 0.246681 | poisson_deviance | 3173.370036 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `E_glm` | comparator | — | 0 | 3 | 542,411 | 678,013 | 0.8000 | — | — | — | 0.226085 | poisson_deviance | 2994.915422 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `E_glm` | comparator | — | 0 | 4 | 542,411 | 678,013 | 0.8000 | — | — | — | 0.252705 | poisson_deviance | 3303.867334 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `E_glm` | comparator | — | 1 | 3 | 542,411 | 678,013 | 0.8000 | — | — | — | 0.226085 | poisson_deviance | 2994.915422 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `E_glm` | comparator | — | 1 | 4 | 542,411 | 678,013 | 0.8000 | — | — | — | 0.252705 | poisson_deviance | 3303.867334 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `E_glm` | comparator | — | 2 | 3 | 542,411 | 678,013 | 0.8000 | — | — | — | 0.226085 | poisson_deviance | 2994.915422 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `E_glm` | comparator | — | 2 | 4 | 542,411 | 678,013 | 0.8000 | — | — | — | 0.252705 | poisson_deviance | 3303.867334 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `F_catboost` | comparator | — | 0 | 0 | 542,410 | 678,013 | 0.8000 | — | — | — | 0.234464 | poisson_deviance | 3016.481307 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `F_catboost` | comparator | — | 0 | 1 | 542,410 | 678,013 | 0.8000 | — | — | — | 0.227813 | poisson_deviance | 2866.071758 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `F_catboost` | comparator | — | 0 | 2 | 542,410 | 678,013 | 0.8000 | — | — | — | 0.244185 | poisson_deviance | 3021.720566 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `F_catboost` | comparator | — | 1 | 0 | 542,410 | 678,013 | 0.8000 | — | — | — | 0.234393 | poisson_deviance | 3019.373279 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `F_catboost` | comparator | — | 1 | 1 | 542,410 | 678,013 | 0.8000 | — | — | — | 0.227898 | poisson_deviance | 2866.192194 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `F_catboost` | comparator | — | 1 | 2 | 542,410 | 678,013 | 0.8000 | — | — | — | 0.244186 | poisson_deviance | 3025.937693 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `F_catboost` | comparator | — | 2 | 0 | 542,410 | 678,013 | 0.8000 | — | — | — | 0.234259 | poisson_deviance | 3013.489098 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `F_catboost` | comparator | — | 2 | 1 | 542,410 | 678,013 | 0.8000 | — | — | — | 0.227698 | poisson_deviance | 2861.416687 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `F_catboost` | comparator | — | 2 | 2 | 542,410 | 678,013 | 0.8000 | — | — | — | 0.244052 | poisson_deviance | 3017.334635 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `F_catboost` | comparator | — | 0 | 3 | 542,411 | 678,013 | 0.8000 | — | — | — | 0.224449 | poisson_deviance | 2912.222844 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `F_catboost` | comparator | — | 0 | 4 | 542,411 | 678,013 | 0.8000 | — | — | — | 0.250676 | poisson_deviance | 3185.701965 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `F_catboost` | comparator | — | 1 | 3 | 542,411 | 678,013 | 0.8000 | — | — | — | 0.224430 | poisson_deviance | 2911.946677 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `F_catboost` | comparator | — | 1 | 4 | 542,411 | 678,013 | 0.8000 | — | — | — | 0.250715 | poisson_deviance | 3191.263316 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `F_catboost` | comparator | — | 2 | 3 | 542,411 | 678,013 | 0.8000 | — | — | — | 0.224461 | poisson_deviance | 2911.555429 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `F_catboost` | comparator | — | 2 | 4 | 542,411 | 678,013 | 0.8000 | — | — | — | 0.250591 | poisson_deviance | 3189.524522 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `M_intercept` | comparator | — | 0 | 0 | 542,410 | 678,013 | 0.8000 | — | — | — | 0.237013 | poisson_deviance | 3247.315724 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `M_intercept` | comparator | — | 0 | 1 | 542,410 | 678,013 | 0.8000 | — | — | — | 0.230726 | poisson_deviance | 3130.397173 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `M_intercept` | comparator | — | 0 | 2 | 542,410 | 678,013 | 0.8000 | — | — | — | 0.248644 | poisson_deviance | 3359.925823 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `M_intercept` | comparator | — | 1 | 0 | 542,410 | 678,013 | 0.8000 | — | — | — | 0.237013 | poisson_deviance | 3247.315724 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `M_intercept` | comparator | — | 1 | 1 | 542,410 | 678,013 | 0.8000 | — | — | — | 0.230726 | poisson_deviance | 3130.397173 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `M_intercept` | comparator | — | 1 | 2 | 542,410 | 678,013 | 0.8000 | — | — | — | 0.248644 | poisson_deviance | 3359.925823 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `M_intercept` | comparator | — | 2 | 0 | 542,410 | 678,013 | 0.8000 | — | — | — | 0.237013 | poisson_deviance | 3247.315724 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `M_intercept` | comparator | — | 2 | 1 | 542,410 | 678,013 | 0.8000 | — | — | — | 0.230726 | poisson_deviance | 3130.397173 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `M_intercept` | comparator | — | 2 | 2 | 542,410 | 678,013 | 0.8000 | — | — | — | 0.248644 | poisson_deviance | 3359.925823 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `M_intercept` | comparator | — | 0 | 3 | 542,411 | 678,013 | 0.8000 | — | — | — | 0.228571 | poisson_deviance | 3179.257770 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `M_intercept` | comparator | — | 0 | 4 | 542,411 | 678,013 | 0.8000 | — | — | — | 0.254703 | poisson_deviance | 3475.009234 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `M_intercept` | comparator | — | 1 | 3 | 542,411 | 678,013 | 0.8000 | — | — | — | 0.228571 | poisson_deviance | 3179.257770 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `M_intercept` | comparator | — | 1 | 4 | 542,411 | 678,013 | 0.8000 | — | — | — | 0.254703 | poisson_deviance | 3475.009234 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `M_intercept` | comparator | — | 2 | 3 | 542,411 | 678,013 | 0.8000 | — | — | — | 0.228571 | poisson_deviance | 3179.257770 | current |
| `20261113T223000Z` | actuarial-baseline-full | regression | frequency | v3_default | freMTPL2freq | `M_intercept` | comparator | — | 2 | 4 | 542,411 | 678,013 | 0.8000 | — | — | — | 0.254703 | poisson_deviance | 3475.009234 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `E_glm` | comparator | — | 0 | 3 | 21,131 | 26,444 | 0.7991 | — | — | — | 1.101795 | rmse | 1.101795 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `E_glm` | comparator | — | 1 | 3 | 21,131 | 26,444 | 0.7991 | — | — | — | 1.101795 | rmse | 1.101795 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `E_glm` | comparator | — | 2 | 3 | 21,131 | 26,444 | 0.7991 | — | — | — | 1.101795 | rmse | 1.101795 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `E_glm` | comparator | — | 0 | 2 | 21,143 | 26,444 | 0.7995 | — | — | — | 1.135457 | rmse | 1.135457 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `E_glm` | comparator | — | 1 | 2 | 21,143 | 26,444 | 0.7995 | — | — | — | 1.135457 | rmse | 1.135457 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `E_glm` | comparator | — | 2 | 2 | 21,143 | 26,444 | 0.7995 | — | — | — | 1.135457 | rmse | 1.135457 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `E_glm` | comparator | — | 0 | 4 | 21,157 | 26,444 | 0.8001 | — | — | — | 1.136758 | rmse | 1.136758 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `E_glm` | comparator | — | 1 | 4 | 21,157 | 26,444 | 0.8001 | — | — | — | 1.136758 | rmse | 1.136758 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `E_glm` | comparator | — | 2 | 4 | 21,157 | 26,444 | 0.8001 | — | — | — | 1.136758 | rmse | 1.136758 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `E_glm` | comparator | — | 0 | 1 | 21,168 | 26,444 | 0.8005 | — | — | — | 1.130344 | rmse | 1.130344 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `E_glm` | comparator | — | 1 | 1 | 21,168 | 26,444 | 0.8005 | — | — | — | 1.130344 | rmse | 1.130344 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `E_glm` | comparator | — | 2 | 1 | 21,168 | 26,444 | 0.8005 | — | — | — | 1.130344 | rmse | 1.130344 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `E_glm` | comparator | — | 0 | 0 | 21,177 | 26,444 | 0.8008 | — | — | — | 1.108004 | rmse | 1.108004 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `E_glm` | comparator | — | 1 | 0 | 21,177 | 26,444 | 0.8008 | — | — | — | 1.108004 | rmse | 1.108004 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `E_glm` | comparator | — | 2 | 0 | 21,177 | 26,444 | 0.8008 | — | — | — | 1.108004 | rmse | 1.108004 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `F_catboost` | comparator | — | 0 | 3 | 21,131 | 26,444 | 0.7991 | — | — | — | 1.103604 | rmse | 1.103604 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `F_catboost` | comparator | — | 1 | 3 | 21,131 | 26,444 | 0.7991 | — | — | — | 1.102826 | rmse | 1.102826 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `F_catboost` | comparator | — | 2 | 3 | 21,131 | 26,444 | 0.7991 | — | — | — | 1.103844 | rmse | 1.103844 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `F_catboost` | comparator | — | 0 | 2 | 21,143 | 26,444 | 0.7995 | — | — | — | 1.135420 | rmse | 1.135420 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `F_catboost` | comparator | — | 1 | 2 | 21,143 | 26,444 | 0.7995 | — | — | — | 1.135418 | rmse | 1.135418 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `F_catboost` | comparator | — | 2 | 2 | 21,143 | 26,444 | 0.7995 | — | — | — | 1.135513 | rmse | 1.135513 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `F_catboost` | comparator | — | 0 | 4 | 21,157 | 26,444 | 0.8001 | — | — | — | 1.135124 | rmse | 1.135124 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `F_catboost` | comparator | — | 1 | 4 | 21,157 | 26,444 | 0.8001 | — | — | — | 1.135941 | rmse | 1.135941 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `F_catboost` | comparator | — | 2 | 4 | 21,157 | 26,444 | 0.8001 | — | — | — | 1.135226 | rmse | 1.135226 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `F_catboost` | comparator | — | 0 | 1 | 21,168 | 26,444 | 0.8005 | — | — | — | 1.129042 | rmse | 1.129042 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `F_catboost` | comparator | — | 1 | 1 | 21,168 | 26,444 | 0.8005 | — | — | — | 1.129384 | rmse | 1.129384 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `F_catboost` | comparator | — | 2 | 1 | 21,168 | 26,444 | 0.8005 | — | — | — | 1.128800 | rmse | 1.128800 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `F_catboost` | comparator | — | 0 | 0 | 21,177 | 26,444 | 0.8008 | — | — | — | 1.104912 | rmse | 1.104912 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `F_catboost` | comparator | — | 1 | 0 | 21,177 | 26,444 | 0.8008 | — | — | — | 1.104067 | rmse | 1.104067 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `F_catboost` | comparator | — | 2 | 0 | 21,177 | 26,444 | 0.8008 | — | — | — | 1.104805 | rmse | 1.104805 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `M_intercept` | comparator | — | 0 | 3 | 21,131 | 26,444 | 0.7991 | — | — | — | 1.109933 | rmse | 1.109933 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `M_intercept` | comparator | — | 1 | 3 | 21,131 | 26,444 | 0.7991 | — | — | — | 1.109933 | rmse | 1.109933 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `M_intercept` | comparator | — | 2 | 3 | 21,131 | 26,444 | 0.7991 | — | — | — | 1.109933 | rmse | 1.109933 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `M_intercept` | comparator | — | 0 | 2 | 21,143 | 26,444 | 0.7995 | — | — | — | 1.143798 | rmse | 1.143798 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `M_intercept` | comparator | — | 1 | 2 | 21,143 | 26,444 | 0.7995 | — | — | — | 1.143798 | rmse | 1.143798 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `M_intercept` | comparator | — | 2 | 2 | 21,143 | 26,444 | 0.7995 | — | — | — | 1.143798 | rmse | 1.143798 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `M_intercept` | comparator | — | 0 | 4 | 21,157 | 26,444 | 0.8001 | — | — | — | 1.143826 | rmse | 1.143826 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `M_intercept` | comparator | — | 1 | 4 | 21,157 | 26,444 | 0.8001 | — | — | — | 1.143826 | rmse | 1.143826 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `M_intercept` | comparator | — | 2 | 4 | 21,157 | 26,444 | 0.8001 | — | — | — | 1.143826 | rmse | 1.143826 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `M_intercept` | comparator | — | 0 | 1 | 21,168 | 26,444 | 0.8005 | — | — | — | 1.139349 | rmse | 1.139349 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `M_intercept` | comparator | — | 1 | 1 | 21,168 | 26,444 | 0.8005 | — | — | — | 1.139349 | rmse | 1.139349 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `M_intercept` | comparator | — | 2 | 1 | 21,168 | 26,444 | 0.8005 | — | — | — | 1.139349 | rmse | 1.139349 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `M_intercept` | comparator | — | 0 | 0 | 21,177 | 26,444 | 0.8008 | — | — | — | 1.112775 | rmse | 1.112775 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `M_intercept` | comparator | — | 1 | 0 | 21,177 | 26,444 | 0.8008 | — | — | — | 1.112775 | rmse | 1.112775 | current |
| `20261113T223002Z` | actuarial-baseline-full | regression | severity | v3_default | freMTPL2sev | `M_intercept` | comparator | — | 2 | 0 | 21,177 | 26,444 | 0.8008 | — | — | — | 1.112775 | rmse | 1.112775 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `E_glm` | comparator | — | 0 | 0 | 42,801 | 53,502 | 0.8000 | — | — | — | 0.706607 | poisson_deviance | 8653.117154 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `E_glm` | comparator | — | 0 | 1 | 42,801 | 53,502 | 0.8000 | — | — | — | 0.853187 | poisson_deviance | 8747.312868 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `E_glm` | comparator | — | 1 | 0 | 42,801 | 53,502 | 0.8000 | — | — | — | 0.706607 | poisson_deviance | 8653.117154 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `E_glm` | comparator | — | 1 | 1 | 42,801 | 53,502 | 0.8000 | — | — | — | 0.853187 | poisson_deviance | 8747.312868 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `E_glm` | comparator | — | 2 | 0 | 42,801 | 53,502 | 0.8000 | — | — | — | 0.706607 | poisson_deviance | 8653.117154 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `E_glm` | comparator | — | 2 | 1 | 42,801 | 53,502 | 0.8000 | — | — | — | 0.853187 | poisson_deviance | 8747.312868 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `E_glm` | comparator | — | 0 | 2 | 42,802 | 53,502 | 0.8000 | — | — | — | 0.830266 | poisson_deviance | 8887.514622 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `E_glm` | comparator | — | 0 | 3 | 42,802 | 53,502 | 0.8000 | — | — | — | 0.840348 | poisson_deviance | 9253.696185 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `E_glm` | comparator | — | 0 | 4 | 42,802 | 53,502 | 0.8000 | — | — | — | 0.780317 | poisson_deviance | 8903.171187 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `E_glm` | comparator | — | 1 | 2 | 42,802 | 53,502 | 0.8000 | — | — | — | 0.830266 | poisson_deviance | 8887.514622 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `E_glm` | comparator | — | 1 | 3 | 42,802 | 53,502 | 0.8000 | — | — | — | 0.840348 | poisson_deviance | 9253.696185 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `E_glm` | comparator | — | 1 | 4 | 42,802 | 53,502 | 0.8000 | — | — | — | 0.780317 | poisson_deviance | 8903.171187 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `E_glm` | comparator | — | 2 | 2 | 42,802 | 53,502 | 0.8000 | — | — | — | 0.830266 | poisson_deviance | 8887.514622 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `E_glm` | comparator | — | 2 | 3 | 42,802 | 53,502 | 0.8000 | — | — | — | 0.840348 | poisson_deviance | 9253.696185 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `E_glm` | comparator | — | 2 | 4 | 42,802 | 53,502 | 0.8000 | — | — | — | 0.780317 | poisson_deviance | 8903.171187 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `F_catboost` | comparator | — | 0 | 0 | 42,801 | 53,502 | 0.8000 | — | — | — | 0.695733 | poisson_deviance | 8364.811918 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `F_catboost` | comparator | — | 0 | 1 | 42,801 | 53,502 | 0.8000 | — | — | — | 0.714742 | poisson_deviance | 8267.086183 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `F_catboost` | comparator | — | 1 | 0 | 42,801 | 53,502 | 0.8000 | — | — | — | 0.699281 | poisson_deviance | 8370.895425 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `F_catboost` | comparator | — | 1 | 1 | 42,801 | 53,502 | 0.8000 | — | — | — | 0.712219 | poisson_deviance | 8246.634568 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `F_catboost` | comparator | — | 2 | 0 | 42,801 | 53,502 | 0.8000 | — | — | — | 0.699338 | poisson_deviance | 8379.348974 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `F_catboost` | comparator | — | 2 | 1 | 42,801 | 53,502 | 0.8000 | — | — | — | 0.714439 | poisson_deviance | 8270.727419 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `F_catboost` | comparator | — | 0 | 2 | 42,802 | 53,502 | 0.8000 | — | — | — | 0.756053 | poisson_deviance | 8455.375628 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `F_catboost` | comparator | — | 0 | 3 | 42,802 | 53,502 | 0.8000 | — | — | — | 0.767151 | poisson_deviance | 8762.589138 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `F_catboost` | comparator | — | 0 | 4 | 42,802 | 53,502 | 0.8000 | — | — | — | 0.741026 | poisson_deviance | 8378.266460 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `F_catboost` | comparator | — | 1 | 2 | 42,802 | 53,502 | 0.8000 | — | — | — | 0.755147 | poisson_deviance | 8463.047579 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `F_catboost` | comparator | — | 1 | 3 | 42,802 | 53,502 | 0.8000 | — | — | — | 0.766963 | poisson_deviance | 8761.503714 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `F_catboost` | comparator | — | 1 | 4 | 42,802 | 53,502 | 0.8000 | — | — | — | 0.743967 | poisson_deviance | 8421.900791 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `F_catboost` | comparator | — | 2 | 2 | 42,802 | 53,502 | 0.8000 | — | — | — | 0.757433 | poisson_deviance | 8463.393364 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `F_catboost` | comparator | — | 2 | 3 | 42,802 | 53,502 | 0.8000 | — | — | — | 0.767262 | poisson_deviance | 8757.015030 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `F_catboost` | comparator | — | 2 | 4 | 42,802 | 53,502 | 0.8000 | — | — | — | 0.741479 | poisson_deviance | 8407.407588 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `M_intercept` | comparator | — | 0 | 0 | 42,801 | 53,502 | 0.8000 | — | — | — | 0.728468 | poisson_deviance | 9688.556160 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `M_intercept` | comparator | — | 0 | 1 | 42,801 | 53,502 | 0.8000 | — | — | — | 0.760452 | poisson_deviance | 9909.244017 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `M_intercept` | comparator | — | 1 | 0 | 42,801 | 53,502 | 0.8000 | — | — | — | 0.728468 | poisson_deviance | 9688.556160 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `M_intercept` | comparator | — | 1 | 1 | 42,801 | 53,502 | 0.8000 | — | — | — | 0.760452 | poisson_deviance | 9909.244017 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `M_intercept` | comparator | — | 2 | 0 | 42,801 | 53,502 | 0.8000 | — | — | — | 0.728468 | poisson_deviance | 9688.556160 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `M_intercept` | comparator | — | 2 | 1 | 42,801 | 53,502 | 0.8000 | — | — | — | 0.760452 | poisson_deviance | 9909.244017 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `M_intercept` | comparator | — | 0 | 2 | 42,802 | 53,502 | 0.8000 | — | — | — | 0.818128 | poisson_deviance | 10406.941019 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `M_intercept` | comparator | — | 0 | 3 | 42,802 | 53,502 | 0.8000 | — | — | — | 0.819831 | poisson_deviance | 10665.512241 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `M_intercept` | comparator | — | 0 | 4 | 42,802 | 53,502 | 0.8000 | — | — | — | 0.783999 | poisson_deviance | 10124.201510 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `M_intercept` | comparator | — | 1 | 2 | 42,802 | 53,502 | 0.8000 | — | — | — | 0.818128 | poisson_deviance | 10406.941019 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `M_intercept` | comparator | — | 1 | 3 | 42,802 | 53,502 | 0.8000 | — | — | — | 0.819831 | poisson_deviance | 10665.512241 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `M_intercept` | comparator | — | 1 | 4 | 42,802 | 53,502 | 0.8000 | — | — | — | 0.783999 | poisson_deviance | 10124.201510 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `M_intercept` | comparator | — | 2 | 2 | 42,802 | 53,502 | 0.8000 | — | — | — | 0.818128 | poisson_deviance | 10406.941019 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `M_intercept` | comparator | — | 2 | 3 | 42,802 | 53,502 | 0.8000 | — | — | — | 0.819831 | poisson_deviance | 10665.512241 | current |
| `20261113T223001Z` | actuarial-baseline-full | regression | frequency | v3_default | spanish_motor_freq | `M_intercept` | comparator | — | 2 | 4 | 42,802 | 53,502 | 0.8000 | — | — | — | 0.783999 | poisson_deviance | 10124.201510 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `E_glm` | comparator | — | 0 | 0 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.578315 | weighted_rmse | 0.615697 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `E_glm` | comparator | — | 0 | 1 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.606597 | weighted_rmse | 0.616322 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `E_glm` | comparator | — | 0 | 2 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.582495 | weighted_rmse | 0.588615 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `E_glm` | comparator | — | 0 | 3 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.567561 | weighted_rmse | 0.560093 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `E_glm` | comparator | — | 0 | 4 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.588036 | weighted_rmse | 0.585084 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `E_glm` | comparator | — | 1 | 0 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.578315 | weighted_rmse | 0.615697 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `E_glm` | comparator | — | 1 | 1 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.606597 | weighted_rmse | 0.616322 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `E_glm` | comparator | — | 1 | 2 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.582495 | weighted_rmse | 0.588615 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `E_glm` | comparator | — | 1 | 3 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.567561 | weighted_rmse | 0.560093 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `E_glm` | comparator | — | 1 | 4 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.588036 | weighted_rmse | 0.585084 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `E_glm` | comparator | — | 2 | 0 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.578315 | weighted_rmse | 0.615697 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `E_glm` | comparator | — | 2 | 1 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.606597 | weighted_rmse | 0.616322 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `E_glm` | comparator | — | 2 | 2 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.582495 | weighted_rmse | 0.588615 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `E_glm` | comparator | — | 2 | 3 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.567561 | weighted_rmse | 0.560093 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `E_glm` | comparator | — | 2 | 4 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.588036 | weighted_rmse | 0.585084 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `F_catboost` | comparator | — | 0 | 0 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.536638 | weighted_rmse | 0.613448 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `F_catboost` | comparator | — | 0 | 1 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.555083 | weighted_rmse | 0.590316 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `F_catboost` | comparator | — | 0 | 2 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.536007 | weighted_rmse | 0.573454 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `F_catboost` | comparator | — | 0 | 3 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.519843 | weighted_rmse | 0.540739 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `F_catboost` | comparator | — | 0 | 4 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.550792 | weighted_rmse | 0.585187 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `F_catboost` | comparator | — | 1 | 0 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.536194 | weighted_rmse | 0.613356 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `F_catboost` | comparator | — | 1 | 1 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.555418 | weighted_rmse | 0.590722 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `F_catboost` | comparator | — | 1 | 2 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.537007 | weighted_rmse | 0.573763 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `F_catboost` | comparator | — | 1 | 3 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.520265 | weighted_rmse | 0.537591 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `F_catboost` | comparator | — | 1 | 4 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.547072 | weighted_rmse | 0.589943 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `F_catboost` | comparator | — | 2 | 0 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.538227 | weighted_rmse | 0.610326 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `F_catboost` | comparator | — | 2 | 1 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.556817 | weighted_rmse | 0.591006 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `F_catboost` | comparator | — | 2 | 2 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.533982 | weighted_rmse | 0.571387 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `F_catboost` | comparator | — | 2 | 3 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.519129 | weighted_rmse | 0.538906 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `F_catboost` | comparator | — | 2 | 4 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.551623 | weighted_rmse | 0.590839 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `M_intercept` | comparator | — | 0 | 0 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.663264 | weighted_rmse | 0.740833 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `M_intercept` | comparator | — | 0 | 1 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.660979 | weighted_rmse | 0.709160 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `M_intercept` | comparator | — | 0 | 2 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.657217 | weighted_rmse | 0.685163 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `M_intercept` | comparator | — | 0 | 3 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.647711 | weighted_rmse | 0.648193 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `M_intercept` | comparator | — | 0 | 4 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.650557 | weighted_rmse | 0.669011 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `M_intercept` | comparator | — | 1 | 0 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.663264 | weighted_rmse | 0.740833 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `M_intercept` | comparator | — | 1 | 1 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.660979 | weighted_rmse | 0.709160 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `M_intercept` | comparator | — | 1 | 2 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.657217 | weighted_rmse | 0.685163 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `M_intercept` | comparator | — | 1 | 3 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.647711 | weighted_rmse | 0.648193 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `M_intercept` | comparator | — | 1 | 4 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.650557 | weighted_rmse | 0.669011 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `M_intercept` | comparator | — | 2 | 0 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.663264 | weighted_rmse | 0.740833 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `M_intercept` | comparator | — | 2 | 1 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.660979 | weighted_rmse | 0.709160 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `M_intercept` | comparator | — | 2 | 2 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.657217 | weighted_rmse | 0.685163 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `M_intercept` | comparator | — | 2 | 3 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.647711 | weighted_rmse | 0.648193 | current |
| `20261113T223003Z` | actuarial-baseline-full | regression | severity | v3_default | spanish_motor_severity | `M_intercept` | comparator | — | 2 | 4 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.650557 | weighted_rmse | 0.669011 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `E_glm` | comparator | — | 0 | 0 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.237089 | poisson_deviance | 3253.379009 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `E_glm` | comparator | — | 0 | 1 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.231046 | poisson_deviance | 3044.820428 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `E_glm` | comparator | — | 0 | 2 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.247981 | poisson_deviance | 3241.750805 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `E_glm` | comparator | — | 0 | 3 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.227674 | poisson_deviance | 3049.181886 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `E_glm` | comparator | — | 0 | 4 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.254254 | poisson_deviance | 3458.746146 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `E_glm` | comparator | — | 1 | 0 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.236309 | poisson_deviance | 3146.260654 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `E_glm` | comparator | — | 1 | 1 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.230385 | poisson_deviance | 3048.738930 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `E_glm` | comparator | — | 1 | 2 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.248656 | poisson_deviance | 3539.515849 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `E_glm` | comparator | — | 1 | 3 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.226675 | poisson_deviance | 3092.062790 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `E_glm` | comparator | — | 1 | 4 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.253771 | poisson_deviance | 3395.088404 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `E_glm` | comparator | — | 2 | 0 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.236614 | poisson_deviance | 3259.129149 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `E_glm` | comparator | — | 2 | 1 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.230086 | poisson_deviance | 3033.708861 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `E_glm` | comparator | — | 2 | 2 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.248542 | poisson_deviance | 3249.658313 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `E_glm` | comparator | — | 2 | 3 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.227829 | poisson_deviance | 3052.923341 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `E_glm` | comparator | — | 2 | 4 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.254245 | poisson_deviance | 3453.335560 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `F_catboost` | comparator | — | 0 | 0 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.237720 | poisson_deviance | 3153.055132 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `F_catboost` | comparator | — | 0 | 1 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.233751 | poisson_deviance | 3039.298204 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `F_catboost` | comparator | — | 0 | 2 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.248235 | poisson_deviance | 3192.857030 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `F_catboost` | comparator | — | 0 | 3 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.230236 | poisson_deviance | 3149.685464 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `F_catboost` | comparator | — | 0 | 4 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.255904 | poisson_deviance | 3397.358577 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `F_catboost` | comparator | — | 1 | 0 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.238206 | poisson_deviance | 3167.068487 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `F_catboost` | comparator | — | 1 | 1 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.231466 | poisson_deviance | 3023.540826 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `F_catboost` | comparator | — | 1 | 2 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.247982 | poisson_deviance | 3280.404054 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `F_catboost` | comparator | — | 1 | 3 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.228238 | poisson_deviance | 3065.284670 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `F_catboost` | comparator | — | 1 | 4 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.255535 | poisson_deviance | 3428.145425 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `F_catboost` | comparator | — | 2 | 0 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.237652 | poisson_deviance | 3268.186525 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `F_catboost` | comparator | — | 2 | 1 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.231683 | poisson_deviance | 3110.936508 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `F_catboost` | comparator | — | 2 | 2 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.247989 | poisson_deviance | 3232.081559 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `F_catboost` | comparator | — | 2 | 3 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.228770 | poisson_deviance | 3076.027417 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `F_catboost` | comparator | — | 2 | 4 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.257582 | poisson_deviance | 3478.487195 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `M_intercept` | comparator | — | 0 | 0 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.237187 | poisson_deviance | 3249.876251 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `M_intercept` | comparator | — | 0 | 1 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.230780 | poisson_deviance | 3131.439308 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `M_intercept` | comparator | — | 0 | 2 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.248685 | poisson_deviance | 3360.082115 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `M_intercept` | comparator | — | 0 | 3 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.228843 | poisson_deviance | 3184.022513 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `M_intercept` | comparator | — | 0 | 4 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.254704 | poisson_deviance | 3474.983039 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `M_intercept` | comparator | — | 1 | 0 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.237017 | poisson_deviance | 3247.354563 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `M_intercept` | comparator | — | 1 | 1 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.230641 | poisson_deviance | 3129.006882 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `M_intercept` | comparator | — | 1 | 2 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.248705 | poisson_deviance | 3360.205603 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `M_intercept` | comparator | — | 1 | 3 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.228747 | poisson_deviance | 3182.111566 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `M_intercept` | comparator | — | 1 | 4 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.254638 | poisson_deviance | 3477.489030 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `M_intercept` | comparator | — | 2 | 0 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.236717 | poisson_deviance | 3248.840454 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `M_intercept` | comparator | — | 2 | 1 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.230662 | poisson_deviance | 3129.317887 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `M_intercept` | comparator | — | 2 | 2 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.248740 | poisson_deviance | 3360.480496 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `M_intercept` | comparator | — | 2 | 3 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.228299 | poisson_deviance | 3178.118336 | current |
| `20261114T003000Z` | actuarial-baseline-matched | regression | frequency | v3_default | freMTPL2freq | `M_intercept` | comparator | — | 2 | 4 | 10,000 | 678,013 | 0.0147 | — | — | — | 0.254656 | poisson_deviance | 3476.639129 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `E_glm` | comparator | — | 0 | 0 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.109146 | rmse | 1.109146 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `E_glm` | comparator | — | 0 | 1 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.131060 | rmse | 1.131060 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `E_glm` | comparator | — | 0 | 2 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.137186 | rmse | 1.137186 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `E_glm` | comparator | — | 0 | 3 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.104095 | rmse | 1.104095 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `E_glm` | comparator | — | 0 | 4 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.138708 | rmse | 1.138708 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `E_glm` | comparator | — | 1 | 0 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.109291 | rmse | 1.109291 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `E_glm` | comparator | — | 1 | 1 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.131044 | rmse | 1.131044 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `E_glm` | comparator | — | 1 | 2 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.136907 | rmse | 1.136907 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `E_glm` | comparator | — | 1 | 3 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.103312 | rmse | 1.103312 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `E_glm` | comparator | — | 1 | 4 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.138231 | rmse | 1.138231 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `E_glm` | comparator | — | 2 | 0 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.108911 | rmse | 1.108911 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `E_glm` | comparator | — | 2 | 1 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.132535 | rmse | 1.132535 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `E_glm` | comparator | — | 2 | 2 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.137214 | rmse | 1.137214 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `E_glm` | comparator | — | 2 | 3 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.102753 | rmse | 1.102753 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `E_glm` | comparator | — | 2 | 4 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.138436 | rmse | 1.138436 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `F_catboost` | comparator | — | 0 | 0 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.108094 | rmse | 1.108094 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `F_catboost` | comparator | — | 0 | 1 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.131975 | rmse | 1.131975 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `F_catboost` | comparator | — | 0 | 2 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.138705 | rmse | 1.138705 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `F_catboost` | comparator | — | 0 | 3 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.101911 | rmse | 1.101911 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `F_catboost` | comparator | — | 0 | 4 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.137284 | rmse | 1.137284 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `F_catboost` | comparator | — | 1 | 0 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.108612 | rmse | 1.108612 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `F_catboost` | comparator | — | 1 | 1 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.130464 | rmse | 1.130464 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `F_catboost` | comparator | — | 1 | 2 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.136153 | rmse | 1.136153 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `F_catboost` | comparator | — | 1 | 3 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.104987 | rmse | 1.104987 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `F_catboost` | comparator | — | 1 | 4 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.138274 | rmse | 1.138274 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `F_catboost` | comparator | — | 2 | 0 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.105509 | rmse | 1.105509 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `F_catboost` | comparator | — | 2 | 1 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.129774 | rmse | 1.129774 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `F_catboost` | comparator | — | 2 | 2 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.137183 | rmse | 1.137183 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `F_catboost` | comparator | — | 2 | 3 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.104014 | rmse | 1.104014 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `F_catboost` | comparator | — | 2 | 4 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.137979 | rmse | 1.137979 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `M_intercept` | comparator | — | 0 | 0 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.112825 | rmse | 1.112825 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `M_intercept` | comparator | — | 0 | 1 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.139330 | rmse | 1.139330 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `M_intercept` | comparator | — | 0 | 2 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.143792 | rmse | 1.143792 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `M_intercept` | comparator | — | 0 | 3 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.109934 | rmse | 1.109934 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `M_intercept` | comparator | — | 0 | 4 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.143961 | rmse | 1.143961 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `M_intercept` | comparator | — | 1 | 0 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.112801 | rmse | 1.112801 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `M_intercept` | comparator | — | 1 | 1 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.139667 | rmse | 1.139667 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `M_intercept` | comparator | — | 1 | 2 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.143832 | rmse | 1.143832 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `M_intercept` | comparator | — | 1 | 3 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.109980 | rmse | 1.109980 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `M_intercept` | comparator | — | 1 | 4 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.144215 | rmse | 1.144215 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `M_intercept` | comparator | — | 2 | 0 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.112775 | rmse | 1.112775 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `M_intercept` | comparator | — | 2 | 1 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.139281 | rmse | 1.139281 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `M_intercept` | comparator | — | 2 | 2 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.143877 | rmse | 1.143877 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `M_intercept` | comparator | — | 2 | 3 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.109945 | rmse | 1.109945 | current |
| `20261114T003002Z` | actuarial-baseline-matched | regression | severity | v3_default | freMTPL2sev | `M_intercept` | comparator | — | 2 | 4 | 10,000 | 26,444 | 0.3782 | — | — | — | 1.143994 | rmse | 1.143994 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `E_glm` | comparator | — | 0 | 0 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.715718 | poisson_deviance | 8699.213293 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `E_glm` | comparator | — | 0 | 1 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.781377 | poisson_deviance | 8783.476731 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `E_glm` | comparator | — | 0 | 2 | 10,000 | 53,502 | 0.1869 | — | — | — | 1.168039 | poisson_deviance | 9051.388997 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `E_glm` | comparator | — | 0 | 3 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.832464 | poisson_deviance | 9269.042096 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `E_glm` | comparator | — | 0 | 4 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.807537 | poisson_deviance | 8914.167956 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `E_glm` | comparator | — | 1 | 0 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.707952 | poisson_deviance | 8739.546562 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `E_glm` | comparator | — | 1 | 1 | 10,000 | 53,502 | 0.1869 | — | — | — | 1.322691 | poisson_deviance | 8958.284457 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `E_glm` | comparator | — | 1 | 2 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.918839 | poisson_deviance | 9017.831041 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `E_glm` | comparator | — | 1 | 3 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.823387 | poisson_deviance | 9281.144926 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `E_glm` | comparator | — | 1 | 4 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.774139 | poisson_deviance | 8933.965248 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `E_glm` | comparator | — | 2 | 0 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.710277 | poisson_deviance | 8753.487462 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `E_glm` | comparator | — | 2 | 1 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.821604 | poisson_deviance | 8786.613845 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `E_glm` | comparator | — | 2 | 2 | 10,000 | 53,502 | 0.1869 | — | — | — | 1.086104 | poisson_deviance | 9054.753169 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `E_glm` | comparator | — | 2 | 3 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.822388 | poisson_deviance | 9263.356203 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `E_glm` | comparator | — | 2 | 4 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.775070 | poisson_deviance | 8920.411609 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `F_catboost` | comparator | — | 0 | 0 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.709551 | poisson_deviance | 8790.430389 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `F_catboost` | comparator | — | 0 | 1 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.736937 | poisson_deviance | 8732.320405 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `F_catboost` | comparator | — | 0 | 2 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.795380 | poisson_deviance | 9032.658891 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `F_catboost` | comparator | — | 0 | 3 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.791434 | poisson_deviance | 9434.307946 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `F_catboost` | comparator | — | 0 | 4 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.757780 | poisson_deviance | 8927.036084 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `F_catboost` | comparator | — | 1 | 0 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.715428 | poisson_deviance | 8863.732812 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `F_catboost` | comparator | — | 1 | 1 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.726205 | poisson_deviance | 8725.643582 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `F_catboost` | comparator | — | 1 | 2 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.797418 | poisson_deviance | 9248.543395 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `F_catboost` | comparator | — | 1 | 3 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.797715 | poisson_deviance | 9495.607144 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `F_catboost` | comparator | — | 1 | 4 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.757262 | poisson_deviance | 8805.840601 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `F_catboost` | comparator | — | 2 | 0 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.712048 | poisson_deviance | 8850.552533 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `F_catboost` | comparator | — | 2 | 1 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.737396 | poisson_deviance | 8771.250590 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `F_catboost` | comparator | — | 2 | 2 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.788262 | poisson_deviance | 8986.041080 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `F_catboost` | comparator | — | 2 | 3 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.791550 | poisson_deviance | 9288.277704 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `F_catboost` | comparator | — | 2 | 4 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.761734 | poisson_deviance | 8997.525587 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `M_intercept` | comparator | — | 0 | 0 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.728557 | poisson_deviance | 9694.650009 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `M_intercept` | comparator | — | 0 | 1 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.760530 | poisson_deviance | 9914.772527 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `M_intercept` | comparator | — | 0 | 2 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.818111 | poisson_deviance | 10405.678287 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `M_intercept` | comparator | — | 0 | 3 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.819898 | poisson_deviance | 10670.901703 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `M_intercept` | comparator | — | 0 | 4 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.784035 | poisson_deviance | 10126.858016 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `M_intercept` | comparator | — | 1 | 0 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.728407 | poisson_deviance | 9684.312805 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `M_intercept` | comparator | — | 1 | 1 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.760652 | poisson_deviance | 9923.220152 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `M_intercept` | comparator | — | 1 | 2 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.818151 | poisson_deviance | 10408.780222 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `M_intercept` | comparator | — | 1 | 3 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.819866 | poisson_deviance | 10668.367696 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `M_intercept` | comparator | — | 1 | 4 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.784046 | poisson_deviance | 10127.686720 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `M_intercept` | comparator | — | 2 | 0 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.728673 | poisson_deviance | 9702.362744 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `M_intercept` | comparator | — | 2 | 1 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.760451 | poisson_deviance | 9909.129629 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `M_intercept` | comparator | — | 2 | 2 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.818101 | poisson_deviance | 10404.898646 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `M_intercept` | comparator | — | 2 | 3 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.820039 | poisson_deviance | 10682.530874 | current |
| `20261114T003001Z` | actuarial-baseline-matched | regression | frequency | v3_default | spanish_motor_freq | `M_intercept` | comparator | — | 2 | 4 | 10,000 | 53,502 | 0.1869 | — | — | — | 0.784010 | poisson_deviance | 10125.066456 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `E_glm` | comparator | — | 0 | 0 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.578315 | weighted_rmse | 0.615697 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `E_glm` | comparator | — | 0 | 1 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.606597 | weighted_rmse | 0.616322 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `E_glm` | comparator | — | 0 | 2 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.582495 | weighted_rmse | 0.588615 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `E_glm` | comparator | — | 0 | 3 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.567561 | weighted_rmse | 0.560093 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `E_glm` | comparator | — | 0 | 4 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.588036 | weighted_rmse | 0.585084 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `E_glm` | comparator | — | 1 | 0 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.578315 | weighted_rmse | 0.615697 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `E_glm` | comparator | — | 1 | 1 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.606597 | weighted_rmse | 0.616322 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `E_glm` | comparator | — | 1 | 2 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.582495 | weighted_rmse | 0.588615 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `E_glm` | comparator | — | 1 | 3 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.567561 | weighted_rmse | 0.560093 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `E_glm` | comparator | — | 1 | 4 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.588036 | weighted_rmse | 0.585084 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `E_glm` | comparator | — | 2 | 0 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.578315 | weighted_rmse | 0.615697 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `E_glm` | comparator | — | 2 | 1 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.606597 | weighted_rmse | 0.616322 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `E_glm` | comparator | — | 2 | 2 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.582495 | weighted_rmse | 0.588615 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `E_glm` | comparator | — | 2 | 3 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.567561 | weighted_rmse | 0.560093 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `E_glm` | comparator | — | 2 | 4 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.588036 | weighted_rmse | 0.585084 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `F_catboost` | comparator | — | 0 | 0 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.536638 | weighted_rmse | 0.613448 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `F_catboost` | comparator | — | 0 | 1 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.555083 | weighted_rmse | 0.590316 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `F_catboost` | comparator | — | 0 | 2 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.536007 | weighted_rmse | 0.573454 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `F_catboost` | comparator | — | 0 | 3 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.519843 | weighted_rmse | 0.540739 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `F_catboost` | comparator | — | 0 | 4 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.550792 | weighted_rmse | 0.585187 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `F_catboost` | comparator | — | 1 | 0 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.536194 | weighted_rmse | 0.613356 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `F_catboost` | comparator | — | 1 | 1 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.555418 | weighted_rmse | 0.590722 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `F_catboost` | comparator | — | 1 | 2 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.537007 | weighted_rmse | 0.573763 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `F_catboost` | comparator | — | 1 | 3 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.520265 | weighted_rmse | 0.537591 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `F_catboost` | comparator | — | 1 | 4 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.547072 | weighted_rmse | 0.589943 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `F_catboost` | comparator | — | 2 | 0 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.538227 | weighted_rmse | 0.610326 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `F_catboost` | comparator | — | 2 | 1 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.556817 | weighted_rmse | 0.591006 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `F_catboost` | comparator | — | 2 | 2 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.533982 | weighted_rmse | 0.571387 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `F_catboost` | comparator | — | 2 | 3 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.519129 | weighted_rmse | 0.538906 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `F_catboost` | comparator | — | 2 | 4 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.551623 | weighted_rmse | 0.590839 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `M_intercept` | comparator | — | 0 | 0 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.663264 | weighted_rmse | 0.740833 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `M_intercept` | comparator | — | 0 | 1 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.660979 | weighted_rmse | 0.709160 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `M_intercept` | comparator | — | 0 | 2 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.657217 | weighted_rmse | 0.685163 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `M_intercept` | comparator | — | 0 | 3 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.647711 | weighted_rmse | 0.648193 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `M_intercept` | comparator | — | 0 | 4 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.650557 | weighted_rmse | 0.669011 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `M_intercept` | comparator | — | 1 | 0 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.663264 | weighted_rmse | 0.740833 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `M_intercept` | comparator | — | 1 | 1 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.660979 | weighted_rmse | 0.709160 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `M_intercept` | comparator | — | 1 | 2 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.657217 | weighted_rmse | 0.685163 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `M_intercept` | comparator | — | 1 | 3 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.647711 | weighted_rmse | 0.648193 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `M_intercept` | comparator | — | 1 | 4 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.650557 | weighted_rmse | 0.669011 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `M_intercept` | comparator | — | 2 | 0 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.663264 | weighted_rmse | 0.740833 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `M_intercept` | comparator | — | 2 | 1 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.660979 | weighted_rmse | 0.709160 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `M_intercept` | comparator | — | 2 | 2 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.657217 | weighted_rmse | 0.685163 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `M_intercept` | comparator | — | 2 | 3 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.647711 | weighted_rmse | 0.648193 | current |
| `20261114T003003Z` | actuarial-baseline-matched | regression | severity | v3_default | spanish_motor_severity | `M_intercept` | comparator | — | 2 | 4 | 4,760 | 5,950 | 0.8000 | — | — | — | 0.650557 | weighted_rmse | 0.669011 | current |

## The rows that are not plainly current

4 withdrawn and 6 without a Capture. Nothing was dropped: a
row that is not evidence a claim may rest on is still a record of what ran.

| run id | dataset | arm | seed | fold | train rows | status | withdrawn by | why |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `coil2000_A_raw_seed42` | coil2000 | `A_raw` | 42 | — | 2000 | superseded | D21 (amended by D22) | coil2000 stopped on resolution — median half-width 0.0149 at the largest usable split against a 0.006 floor; D22 withdraws D21's seed-cost inference and leaves the stop resting on the P1 gate alone |
| `coil2000_B_in_domain_seed42` | coil2000 | `B_in_domain` | 42 | — | 2000 | superseded | D21 (amended by D22) | coil2000 stopped on resolution — median half-width 0.0149 at the largest usable split against a 0.006 floor; D22 withdraws D21's seed-cost inference and leaves the stop resting on the P1 gate alone |
| `coil2000_E_glm_seed42` | coil2000 | `E_glm` | 42 | — | 2000 | superseded | D21 (amended by D22) | coil2000 stopped on resolution — median half-width 0.0149 at the largest usable split against a 0.006 floor; D22 withdraws D21's seed-cost inference and leaves the stop resting on the P1 gate alone |
| `coil2000_F_catboost_seed42` | coil2000 | `F_catboost` | 42 | — | 2000 | superseded | D21 (amended by D22) | coil2000 stopped on resolution — median half-width 0.0149 at the largest usable split against a 0.006 floor; D22 withdraws D21's seed-cost inference and leaves the stop resting on the P1 gate alone |
| `20260914T010247Z` | uslapseagent | `A_raw` | 42 | — | 10000 | no-capture | — | launch record with no capture.json — cite by description (outputs/gpu-pilot/runs/20260914T010247Z/uslapseagent/A_raw/meta.json), not a Capture |
| `20260914T010247Z` | uslapseagent | `B_ft3` | 42 | — | 10000 | no-capture | — | launch record with no capture.json — cite by description (outputs/gpu-pilot/runs/20260914T010247Z/uslapseagent/B_ft3/meta.json), not a Capture |
| `20260914T010247Z` | uslapseagent | `B_ft10` | 42 | — | 10000 | no-capture | — | launch record with no capture.json — cite by description (outputs/gpu-pilot/runs/20260914T010247Z/uslapseagent/B_ft10/meta.json), not a Capture |
| `20260914T010247Z` | uslapseagent | `B_ft30` | 42 | — | 10000 | no-capture | — | launch record with no capture.json — cite by description (outputs/gpu-pilot/runs/20260914T010247Z/uslapseagent/B_ft30/meta.json), not a Capture |
| — | spanish_motor_lapse | `A_raw` | — | — | — | no-capture | — | breadth replication, seeds 341-356: curated pointer, no capture and no committed per-seed record — the breadth result owns the 10,000-row, 30-epoch description, so the epoch and row fields are blank and the numbers are cited via finetuning_breadth_spanish_result.md, not a Capture |
| — | spanish_motor_lapse | `B_ft30` | — | — | — | no-capture | — | breadth replication, seeds 341-356: curated pointer, no capture and no committed per-seed record — the breadth result owns the 10,000-row, 30-epoch description, so the epoch and row fields are blank and the numbers are cited via finetuning_breadth_spanish_result.md, not a Capture |

The withdrawal is a **curated** list, not a diff of captures. The committed evidence is
seed-disjoint by construction — three duplicate launches were discarded before commit and
their run ids are not in the tree — so mechanical replacement detection returns zero rows and
the generator asserts that instead of reporting an empty result as a finding. The four
`coil2000` pilot rows are withdrawn by **D21**, whose stop stands, and **D22** amends it: it
withdraws D21's seed-cost inference, not the stop, which rests on the P1 resolution gate.
Every `coil2000` row here is withdrawn and the dataset is closed, so the summary below carries
no `coil2000` line at all — an absent line is the honest form of a closed dataset.

D11 ("stop the fine-tuning line") is **not** applied to these rows: it is historical, and D14,
D15 and D16 reopened and published the line it stopped. A ledger that marked every `B_ft*` row
withdrawn under D11 would contradict the campaign's own outcome.

## The 2,000-row pilot, recorded twice

12 of the aggregate's 16 cells are also committed as per-arm records under
`outputs/gpu-pilot/<dataset>/<arm>/meta.json`.
8 of them agree to six decimal places and 4 do not:

| dataset | arm | metric | aggregate | record | device (aggregate → record) |
| --- | --- | --- | --- | --- | --- |
| coil2000 | `A_raw` | roc_auc | 0.767530 | 0.767902 | NVIDIA L40S → cpu |
| coil2000 | `A_raw` | brier | 0.050767 | 0.050738 | NVIDIA L40S → cpu |
| coil2000 | `A_raw` | pr_auc | 0.187545 | 0.188188 | NVIDIA L40S → cpu |
| eudirectlapse | `A_raw` | roc_auc | 0.588090 | 0.587907 | NVIDIA L40S → cpu |
| eudirectlapse | `A_raw` | brier | 0.113679 | 0.113686 | NVIDIA L40S → cpu |
| eudirectlapse | `A_raw` | pr_auc | 0.194347 | 0.193911 | NVIDIA L40S → cpu |
| spanish_motor_lapse | `A_raw` | roc_auc | 0.723295 | 0.723028 | NVIDIA L40S → cpu |
| spanish_motor_lapse | `A_raw` | brier | 0.197776 | 0.197951 | NVIDIA L40S → cpu |
| spanish_motor_lapse | `A_raw` | pr_auc | 0.570771 | 0.569868 | NVIDIA L40S → cpu |
| uslapseagent | `A_raw` | roc_auc | 0.936312 | 0.936261 | NVIDIA L40S → NVIDIA RTX PRO 4000 Blackwell |
| uslapseagent | `A_raw` | brier | 0.087321 | 0.086800 | NVIDIA L40S → NVIDIA RTX PRO 4000 Blackwell |
| uslapseagent | `A_raw` | pr_auc | 0.834384 | 0.836706 | NVIDIA L40S → NVIDIA RTX PRO 4000 Blackwell |

**Both forms are experiment output, and neither carries a `provenance` block.** The records
are an older schema: `versions` and a weights block, which name libraries and bytes, not a
capture. So `DOCUMENT_AUTHORITY.md`'s "a number resolves to the capture" chooses neither,
and there is no Capture for these cells at all. **This ledger reads the aggregate for every
cell.** It is the only form that covers all 16 — the 4 cells
with no per-arm record exist nowhere else — and splitting one pilot's metrics across two
files would leave no rule for which file wins. Every differing cell above is on arm
`A_raw`, and the device column shows why: the aggregate holds a GPU re-run
where the record may hold the CPU run. The R1 results report states that device variance
itself (§4b) and warns that the aggregate mixes provenance; the ledger quotes the
aggregate's device for every cell rather than switching sources cell by cell.

This table is the one part of this document not rendered from the CSV: it compares the
chosen form with the rejected one, so it reads both.

## Summary — dataset × arm × training rows

`n`, mean and min–max across seeds (and folds, where the evidence has them, and instances,
where a dataset has more than one Run). **Descriptive only: no interval and no verdict**, so
the ledger cannot contradict an analysis that owns one. Current rows only — a withdrawn row
would put a stopped cell inside a mean, and a `no-capture` row would put a launch with no
Capture inside a mean over captured Runs. A line with `n = 1` prints the value and `single
run`: an absent range is not a zero-width one. The 2,000-row and 10,000-row cells are separate
lines for the same reason `train_rows` is part of the key.

### Classification — ROC AUC, Brier and PR-AUC

| family | type | task | dataset | arm | train rows | n | ROC AUC mean (min–max) | Brier mean (min–max) | PR-AUC mean (min–max) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `pilot2-phase2` | classification | lapse | eudirectlapse | `A_raw` | 10,000 | 238 | 0.6268 (0.5452–0.6984) | 0.1095 (0.1068–0.1128) | 0.2037 (0.1500–0.2745) |
| `pilot2-phase2` | classification | lapse | eudirectlapse | `B_ft30` | 10,000 | 238 | 0.6275 (0.5440–0.6914) | 0.1095 (0.1068–0.1132) | 0.2010 (0.1516–0.2684) |
| `pilot2-phase2` | classification | lapse | uslapseagent | `A_raw` | 10,000 | 40 | 0.9431 (0.9275–0.9591) | 0.0841 (0.0718–0.0975) | 0.8781 (0.8405–0.9143) |
| `pilot2-phase2` | classification | lapse | uslapseagent | `B_ft3` | 10,000 | 12 | 0.9421 (0.9333–0.9499) | 0.0861 (0.0808–0.0934) | 0.8792 (0.8559–0.8990) |
| `pilot2-phase2` | classification | lapse | uslapseagent | `B_ft10` | 10,000 | 12 | 0.9428 (0.9338–0.9511) | 0.0858 (0.0805–0.0930) | 0.8809 (0.8615–0.9021) |
| `pilot2-phase2` | classification | lapse | uslapseagent | `B_ft30` | 10,000 | 40 | 0.9465 (0.9328–0.9606) | 0.0821 (0.0703–0.0939) | 0.8881 (0.8594–0.9188) |
| `r1-pilot` | classification | lapse | eudirectlapse | `A_raw` | 2,000 | 1 | 0.5881 — single run | 0.1137 — single run | 0.1943 — single run |
| `r1-pilot` | classification | lapse | eudirectlapse | `B_in_domain` | 2,000 | 1 | 0.5976 — single run | 0.1133 — single run | 0.1982 — single run |
| `r1-pilot` | classification | lapse | eudirectlapse | `E_glm` | 2,000 | 1 | 0.5744 — single run | 0.1163 — single run | 0.1601 — single run |
| `r1-pilot` | classification | lapse | eudirectlapse | `F_catboost` | 2,000 | 1 | 0.5738 — single run | 0.1151 — single run | 0.1830 — single run |
| `r1-pilot` | classification | lapse | spanish_motor_lapse | `A_raw` | 2,000 | 1 | 0.7233 — single run | 0.1978 — single run | 0.5708 — single run |
| `r1-pilot` | classification | lapse | spanish_motor_lapse | `B_in_domain` | 2,000 | 1 | 0.7272 — single run | 0.1967 — single run | 0.5791 — single run |
| `r1-pilot` | classification | lapse | spanish_motor_lapse | `E_glm` | 2,000 | 1 | 0.6166 — single run | 0.2222 — single run | 0.4469 — single run |
| `r1-pilot` | classification | lapse | spanish_motor_lapse | `F_catboost` | 2,000 | 1 | 0.7114 — single run | 0.2015 — single run | 0.5412 — single run |
| `r1-pilot` | classification | lapse | uslapseagent | `A_raw` | 2,000 | 1 | 0.9363 — single run | 0.0873 — single run | 0.8344 — single run |
| `r1-pilot` | classification | lapse | uslapseagent | `B_in_domain` | 2,000 | 1 | 0.9355 — single run | 0.0870 — single run | 0.8375 — single run |
| `r1-pilot` | classification | lapse | uslapseagent | `E_glm` | 2,000 | 1 | 0.9271 — single run | 0.0910 — single run | 0.8172 — single run |
| `r1-pilot` | classification | lapse | uslapseagent | `F_catboost` | 2,000 | 1 | 0.9297 — single run | 0.0934 — single run | 0.8293 — single run |

### Regression — RMSE and the record's verdict metric

The verdict metric is named per line because it is the record's, not a global choice: French
severity records unweighted RMSE, Spanish severity the claim-weighted RMSE.

| family | type | task | dataset | arm | train rows | n | RMSE mean (min–max) | verdict metric | verdict metric mean (min–max) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `fair-test-freq-sev` | regression | frequency | freMTPL2freq | `A_raw` | 10,000 | 15 | 0.2406 (0.2284–0.2561) | `poisson_deviance` | 3592.4045 (3265.8482–4040.8568) |
| `fair-test-freq-sev` | regression | frequency | freMTPL2freq | `B_ft30` | 10,000 | 15 | 0.2393 (0.2269–0.2544) | `poisson_deviance` | 3238.4301 (3029.0713–3576.0506) |
| `fair-test-freq-sev` | regression | severity | freMTPL2sev | `A_raw` | 10,000 | 15 | 1.1201 (1.1001–1.1349) | `rmse` | 1.1201 (1.1001–1.1349) |
| `fair-test-freq-sev` | regression | severity | freMTPL2sev | `B_ft30` | 10,000 | 15 | 1.1304 (1.1014–1.1533) | `rmse` | 1.1304 (1.1014–1.1533) |
| `fair-test-freq-sev` | regression | frequency | spanish_motor_freq | `A_raw` | 10,000 | 15 | 0.7700 (0.7184–0.8100) | `poisson_deviance` | 10019.0541 (9462.1871–10865.2618) |
| `fair-test-freq-sev` | regression | frequency | spanish_motor_freq | `B_ft30` | 10,000 | 15 | 0.7659 (0.7131–0.8094) | `poisson_deviance` | 9606.6579 (8819.0873–11171.8293) |
| `fair-test-freq-sev` | regression | severity | spanish_motor_severity | `A_raw` | 4,760 | 15 | 0.4909 (0.4704–0.5067) | `weighted_rmse` | 0.6503 (0.6015–0.6971) |
| `fair-test-freq-sev` | regression | severity | spanish_motor_severity | `B_ft30` | 4,760 | 15 | 0.4933 (0.4655–0.5625) | `weighted_rmse` | 0.6396 (0.5779–0.6864) |
| `actuarial-baseline-full` | regression | frequency | freMTPL2freq | `E_glm` | 542,410 | 9 | 0.2372 (0.2295–0.2467) | `poisson_deviance` | 3083.6375 (2978.8110–3173.3700) |
| `actuarial-baseline-full` | regression | frequency | freMTPL2freq | `E_glm` | 542,411 | 6 | 0.2394 (0.2261–0.2527) | `poisson_deviance` | 3149.3914 (2994.9154–3303.8673) |
| `actuarial-baseline-full` | regression | frequency | freMTPL2freq | `F_catboost` | 542,410 | 9 | 0.2354 (0.2277–0.2442) | `poisson_deviance` | 2967.5575 (2861.4167–3025.9377) |
| `actuarial-baseline-full` | regression | frequency | freMTPL2freq | `F_catboost` | 542,411 | 6 | 0.2376 (0.2244–0.2507) | `poisson_deviance` | 3050.3691 (2911.5554–3191.2633) |
| `actuarial-baseline-full` | regression | frequency | freMTPL2freq | `M_intercept` | 542,410 | 9 | 0.2388 (0.2307–0.2486) | `poisson_deviance` | 3245.8796 (3130.3972–3359.9258) |
| `actuarial-baseline-full` | regression | frequency | freMTPL2freq | `M_intercept` | 542,411 | 6 | 0.2416 (0.2286–0.2547) | `poisson_deviance` | 3327.1335 (3179.2578–3475.0092) |
| `actuarial-baseline-full` | regression | severity | freMTPL2sev | `E_glm` | 21,131 | 3 | 1.1018 (1.1018–1.1018) | `rmse` | 1.1018 (1.1018–1.1018) |
| `actuarial-baseline-full` | regression | severity | freMTPL2sev | `E_glm` | 21,143 | 3 | 1.1355 (1.1355–1.1355) | `rmse` | 1.1355 (1.1355–1.1355) |
| `actuarial-baseline-full` | regression | severity | freMTPL2sev | `E_glm` | 21,157 | 3 | 1.1368 (1.1368–1.1368) | `rmse` | 1.1368 (1.1368–1.1368) |
| `actuarial-baseline-full` | regression | severity | freMTPL2sev | `E_glm` | 21,168 | 3 | 1.1303 (1.1303–1.1303) | `rmse` | 1.1303 (1.1303–1.1303) |
| `actuarial-baseline-full` | regression | severity | freMTPL2sev | `E_glm` | 21,177 | 3 | 1.1080 (1.1080–1.1080) | `rmse` | 1.1080 (1.1080–1.1080) |
| `actuarial-baseline-full` | regression | severity | freMTPL2sev | `F_catboost` | 21,131 | 3 | 1.1034 (1.1028–1.1038) | `rmse` | 1.1034 (1.1028–1.1038) |
| `actuarial-baseline-full` | regression | severity | freMTPL2sev | `F_catboost` | 21,143 | 3 | 1.1355 (1.1354–1.1355) | `rmse` | 1.1355 (1.1354–1.1355) |
| `actuarial-baseline-full` | regression | severity | freMTPL2sev | `F_catboost` | 21,157 | 3 | 1.1354 (1.1351–1.1359) | `rmse` | 1.1354 (1.1351–1.1359) |
| `actuarial-baseline-full` | regression | severity | freMTPL2sev | `F_catboost` | 21,168 | 3 | 1.1291 (1.1288–1.1294) | `rmse` | 1.1291 (1.1288–1.1294) |
| `actuarial-baseline-full` | regression | severity | freMTPL2sev | `F_catboost` | 21,177 | 3 | 1.1046 (1.1041–1.1049) | `rmse` | 1.1046 (1.1041–1.1049) |
| `actuarial-baseline-full` | regression | severity | freMTPL2sev | `M_intercept` | 21,131 | 3 | 1.1099 (1.1099–1.1099) | `rmse` | 1.1099 (1.1099–1.1099) |
| `actuarial-baseline-full` | regression | severity | freMTPL2sev | `M_intercept` | 21,143 | 3 | 1.1438 (1.1438–1.1438) | `rmse` | 1.1438 (1.1438–1.1438) |
| `actuarial-baseline-full` | regression | severity | freMTPL2sev | `M_intercept` | 21,157 | 3 | 1.1438 (1.1438–1.1438) | `rmse` | 1.1438 (1.1438–1.1438) |
| `actuarial-baseline-full` | regression | severity | freMTPL2sev | `M_intercept` | 21,168 | 3 | 1.1393 (1.1393–1.1393) | `rmse` | 1.1393 (1.1393–1.1393) |
| `actuarial-baseline-full` | regression | severity | freMTPL2sev | `M_intercept` | 21,177 | 3 | 1.1128 (1.1128–1.1128) | `rmse` | 1.1128 (1.1128–1.1128) |
| `actuarial-baseline-full` | regression | frequency | spanish_motor_freq | `E_glm` | 42,801 | 6 | 0.7799 (0.7066–0.8532) | `poisson_deviance` | 8700.2150 (8653.1172–8747.3129) |
| `actuarial-baseline-full` | regression | frequency | spanish_motor_freq | `E_glm` | 42,802 | 9 | 0.8170 (0.7803–0.8403) | `poisson_deviance` | 9014.7940 (8887.5146–9253.6962) |
| `actuarial-baseline-full` | regression | frequency | spanish_motor_freq | `F_catboost` | 42,801 | 6 | 0.7060 (0.6957–0.7147) | `poisson_deviance` | 8316.5841 (8246.6346–8379.3490) |
| `actuarial-baseline-full` | regression | frequency | spanish_motor_freq | `F_catboost` | 42,802 | 9 | 0.7552 (0.7410–0.7673) | `poisson_deviance` | 8541.1666 (8378.2665–8762.5891) |
| `actuarial-baseline-full` | regression | frequency | spanish_motor_freq | `M_intercept` | 42,801 | 6 | 0.7445 (0.7285–0.7605) | `poisson_deviance` | 9798.9001 (9688.5562–9909.2440) |
| `actuarial-baseline-full` | regression | frequency | spanish_motor_freq | `M_intercept` | 42,802 | 9 | 0.8073 (0.7840–0.8198) | `poisson_deviance` | 10398.8849 (10124.2015–10665.5122) |
| `actuarial-baseline-full` | regression | severity | spanish_motor_severity | `E_glm` | 4,760 | 15 | 0.5846 (0.5676–0.6066) | `weighted_rmse` | 0.5932 (0.5601–0.6163) |
| `actuarial-baseline-full` | regression | severity | spanish_motor_severity | `F_catboost` | 4,760 | 15 | 0.5396 (0.5191–0.5568) | `weighted_rmse` | 0.5807 (0.5376–0.6134) |
| `actuarial-baseline-full` | regression | severity | spanish_motor_severity | `M_intercept` | 4,760 | 15 | 0.6559 (0.6477–0.6633) | `weighted_rmse` | 0.6905 (0.6482–0.7408) |
| `actuarial-baseline-matched` | regression | frequency | freMTPL2freq | `E_glm` | 10,000 | 15 | 0.2394 (0.2267–0.2543) | `poisson_deviance` | 3221.2200 (3033.7089–3539.5158) |
| `actuarial-baseline-matched` | regression | frequency | freMTPL2freq | `F_catboost` | 10,000 | 15 | 0.2407 (0.2282–0.2576) | `poisson_deviance` | 3204.1611 (3023.5408–3478.4872) |
| `actuarial-baseline-matched` | regression | frequency | freMTPL2freq | `M_intercept` | 10,000 | 15 | 0.2399 (0.2283–0.2547) | `poisson_deviance` | 3279.3311 (3129.0069–3477.4890) |
| `actuarial-baseline-matched` | regression | severity | freMTPL2sev | `E_glm` | 10,000 | 15 | 1.1239 (1.1028–1.1387) | `rmse` | 1.1239 (1.1028–1.1387) |
| `actuarial-baseline-matched` | regression | severity | freMTPL2sev | `F_catboost` | 10,000 | 15 | 1.1234 (1.1019–1.1387) | `rmse` | 1.1234 (1.1019–1.1387) |
| `actuarial-baseline-matched` | regression | severity | freMTPL2sev | `M_intercept` | 10,000 | 15 | 1.1300 (1.1099–1.1442) | `rmse` | 1.1300 (1.1099–1.1442) |
| `actuarial-baseline-matched` | regression | frequency | spanish_motor_freq | `E_glm` | 10,000 | 15 | 0.8712 (0.7080–1.3227) | `poisson_deviance` | 8961.7789 (8699.2133–9281.1449) |
| `actuarial-baseline-matched` | regression | frequency | spanish_motor_freq | `F_catboost` | 10,000 | 15 | 0.7584 (0.7096–0.7977) | `poisson_deviance` | 8996.6512 (8725.6436–9495.6071) |
| `actuarial-baseline-matched` | regression | frequency | spanish_motor_freq | `M_intercept` | 10,000 | 15 | 0.7822 (0.7284–0.8200) | `poisson_deviance` | 10163.2811 (9684.3128–10682.5309) |
| `actuarial-baseline-matched` | regression | severity | spanish_motor_severity | `E_glm` | 4,760 | 15 | 0.5846 (0.5676–0.6066) | `weighted_rmse` | 0.5932 (0.5601–0.6163) |
| `actuarial-baseline-matched` | regression | severity | spanish_motor_severity | `F_catboost` | 4,760 | 15 | 0.5396 (0.5191–0.5568) | `weighted_rmse` | 0.5807 (0.5376–0.6134) |
| `actuarial-baseline-matched` | regression | severity | spanish_motor_severity | `M_intercept` | 4,760 | 15 | 0.6559 (0.6477–0.6633) | `weighted_rmse` | 0.6905 (0.6482–0.7408) |

The campaign is in this key because it is in the ledger's identity key: the two baseline
budgets capture one Spanish severity fit under two run ids, and merging them would count the
same fit twice. Grouping by training rows splits a full-pool baseline across the fold pool's
one-row differences; that is the recorded per-fold budget, not a design arm.


## How to read a row

**`arm_kind` is derived, never recorded.** `A_raw` is the raw control (`raw`); `B_ft3`,
`B_ft10`, `B_ft30` and the pilot's `B_in_domain` are fine-tuned (`fine-tuned`); `E_glm`,
`F_catboost` and `M_intercept` are comparator Methods (`comparator`), not Arms of the
programme. The baseline records carry `arm: null` and name the method in `method`; the
generator takes the label from the record and asserts it against the directory name.

**Epochs come from the record that trained, not from the config that launched.** For a
classification record the source is `effective_config.kwargs.epochs`; `config.epochs` — and
every Run manifest — reads `3` on every arm, including the 30-epoch one. A regression record
names its count at the top level instead, where the raw control records `0` and a comparator
records none. The generator asserts the recorded count equals the number in the `B_ftN` label
and fails on a disagreement rather than smoothing it. The 2,000-row pilot records no
arm-level epoch count at all (`max_finetune_steps` is a different parameter, carried by the
comparator rows too), so its `epochs` column is blank, not `3`. The curated Spanish cell is
blank for a stronger reason: there is no record to read one from.

**Two metric blocks, and a blank is "not applicable".** A classification row records ROC
AUC, Brier and PR-AUC; a regression row records RMSE and its verdict metric with the value.
The other block is blank on that row, and a blank is never rendered as `0`: the evidence
records no such number, and inventing one would make two tasks look comparable when they are
not. `log_loss` and `ece` are recorded on the classification captures and are deliberately
outside this ledger (the map's out-of-scope list, #663), not missing from it.

**A superseded row names what withdrew it.** `superseded_by_or_decision` holds the replacing
run id when a replacement was detected, or the decision that withdrew the row when one was
curated; `superseded_reason` holds the prose. On this evidence replacement detection returns
zero rows, so the four `coil2000` rows read `D21 (amended by D22)` and the column is not empty
on any row whose status is `superseded`.

**The model is named by its record, and the version is never inferred.** No row here is
described as v3.5: a version is printed only where a record names one, and `auto` is never
re-described as a version. No table subtracts one era or one model family from another.

- Classification rows that record a version name `model_version` `auto` — a value that names no version — beside the checkpoint `tabpfn-v3-classifier-v3_default.ckpt` and weights sha256 `d0d865d5...8f3988`; `era` reads `auto`. The other 22 of the 602 classification rows record none (`gpu-pilot`, `pilot2-breadth-spanish`, `r1-pilot`).
- Regression rows record no `model_version`; their weights block names the checkpoint `tabpfn-v3-regressor-v3_default.ckpt` and weights sha256 `311ce18d...7a7301`, so `era` reads `v3_default`.

**`source` is the pointer to the bytes.** For a capture row it is the per-`meta.json` record,
because `capture.json` holds hashes and the record holds the numbers; the Run id is in the
`run_id` column, taken from the directory. A per-seed record's own `run_id`
(`<dataset>_<arm>_seed<N>`) is **not** the Run id and is not used as one.

**A `no-capture` row cannot be cited as a Capture.** The Spanish breadth cell's per-seed records
were never committed, so its rows carry blank metrics, no seed and blank `epochs` /
`train_rows` — one row per arm, because a per-seed row would be an invention — and a pointer to
[`finetuning_breadth_spanish_result.md`](finetuning_breadth_spanish_result.md). The breadth
result owns the design's 10,000-row, 30-epoch description; this row is a pointer to it, and a
label-derived epoch in an `epochs` column would be presented as a recorded one. Cite the
result, not a Capture. The `gpu-pilot` rows do carry metrics, from committed launch records
that are not Captures; they are cited by description, the way `REPORT_REGISTRY.md` already
handles them.

## Regenerating

```
python scripts/analyses/finetuning_runs_ledger.py
```

Two runs on the same tree write byte-identical files: rows are sorted on a total key and every
float is formatted to fixed precision (six decimal places per row, four in the summary, which is
computed from the CSV and therefore inherits that rounding). The generator writes both files or
neither — a disagreement in the evidence exits before either is written.

