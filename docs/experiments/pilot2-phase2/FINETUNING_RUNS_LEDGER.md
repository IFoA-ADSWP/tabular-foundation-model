# Fine-tuning runs ledger — every committed in-domain fine-tuning run

> **Status:** current — generated ledger, 2026-11-20. **Generated, not written:** rebuild it with
> `python scripts/analyses/finetuning_runs_ledger.py`; a hand edit is overwritten and a number
> typed here is a number with no evidence behind it.

**Question.** What did the fine-tuning programme run, and what did it score? One row per run ×
arm × seed, and a descriptive summary per dataset × arm underneath. This is a reference, not a
new verdict: it re-runs nothing, adds no interval, and changes no claim.

**Provenance.** Built for the map's ledger ticket (#663 → #665). The fields and the traps are
the research note's (#664): the epoch count that lies, the seed-disjoint evidence that makes
mechanical supersession impossible, the row budget that has to be in the key, and the model
version recorded as `auto`.

**Machine form.** [`finetuning_runs_ledger.csv`](../../analyses/data/finetuning_runs_ledger.csv)
carries the same rows, one line each, with the full source pointer. The tables below are
rendered from it, so they cannot disagree with it.

**Rows.** 602 across 4 experiment families: `pilot2-phase2` 580; `r1-pilot` 16; `gpu-pilot` 4; `pilot2-breadth-spanish` 2. Statuses present: `current`, `no-capture`, `superseded`.

## Sources, and what each one is

| family | rows | statuses | read from |
| --- | --- | --- | --- |
| `pilot2-phase2` | 580 | current 580 | `results/<run>/<dataset>/<arm>/seed<N>_foldNone/meta.json`, one directory per Run |
| `r1-pilot` | 16 | current 12, superseded 4 | `outputs/finetune/pilot/pilot_metrics.parquet` |
| `gpu-pilot` | 4 | no-capture 4 | `outputs/gpu-pilot/runs/<run>/<dataset>/<arm>/meta.json` |
| `pilot2-breadth-spanish` | 2 | no-capture 2 | `docs/experiments/pilot2-phase2/finetuning_breadth_spanish_result.md` |

The families are read from four places, and they are read **separately**:

- `pilot2-phase2` — the 23 Run directories this campaign's own `Runs` block names, each
  with a `capture.json`. Selected by campaign membership, never by "has an `ft` arm": six
  fair-test Run directories carry the same `A_raw` / `B_ft30` labels and belong to another
  campaign.
- `r1-pilot` — `outputs/finetune/pilot/pilot_metrics.parquet`, an aggregate of the 2,000-row
  pilot. It is not a Run and has no Capture, so its ids are synthetic and are never joined to
  a Run id.
- `gpu-pilot` — committed launch records under `outputs/gpu-pilot/runs/`, which have no
  `capture.json` and so cannot be cited as a Capture.
- `pilot2-breadth-spanish` — one curated cell whose per-seed records were never committed. It is
  listed so the absence is visible, with blank metrics rather than invented ones.

## The ledger

One row per run × arm × seed. `epochs` is blank where no epoch applies (the raw control, and
the comparator Methods) and where the source records no arm-level epoch count (the 2,000-row
pilot). `train_rows` is part of the key: `uslapseagent` seed 42 exists at 2,000 and at 10,000
rows, and they are two measurements, not a duplicate.

| run id | family | dataset | arm | arm kind | epochs | seed | train rows | ROC AUC | Brier | PR-AUC | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `20261104T234013Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 93 | 10000 | 0.614912 | 0.110327 | 0.176254 | current |
| `20261104T234013Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 94 | 10000 | 0.665397 | 0.107603 | 0.274502 | current |
| `20261104T234013Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 95 | 10000 | 0.651636 | 0.108556 | 0.213301 | current |
| `20261104T234013Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 96 | 10000 | 0.620252 | 0.109894 | 0.198503 | current |
| `20261104T234013Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 97 | 10000 | 0.626532 | 0.109945 | 0.186384 | current |
| `20261104T234013Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 98 | 10000 | 0.640741 | 0.109073 | 0.209708 | current |
| `20261104T234013Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 99 | 10000 | 0.621327 | 0.110018 | 0.180978 | current |
| `20261104T234013Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 100 | 10000 | 0.632418 | 0.109153 | 0.221063 | current |
| `20261104T234013Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 101 | 10000 | 0.586045 | 0.110965 | 0.173167 | current |
| `20261104T234013Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 102 | 10000 | 0.619150 | 0.109435 | 0.213613 | current |
| `20261104T234013Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 103 | 10000 | 0.585104 | 0.111088 | 0.164391 | current |
| `20261104T234013Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 104 | 10000 | 0.678129 | 0.107620 | 0.231122 | current |
| `20261105T001837Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 105 | 10000 | 0.638036 | 0.109441 | 0.196240 | current |
| `20261105T001837Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 106 | 10000 | 0.599305 | 0.110798 | 0.181867 | current |
| `20261105T001837Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 107 | 10000 | 0.635133 | 0.109359 | 0.193670 | current |
| `20261105T001837Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 108 | 10000 | 0.647380 | 0.108366 | 0.228412 | current |
| `20261105T001837Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 109 | 10000 | 0.604358 | 0.110208 | 0.182119 | current |
| `20261105T001837Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 110 | 10000 | 0.665200 | 0.107898 | 0.234811 | current |
| `20261105T001837Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 111 | 10000 | 0.610755 | 0.110441 | 0.180162 | current |
| `20261105T001837Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 112 | 10000 | 0.609895 | 0.109754 | 0.196352 | current |
| `20261105T001837Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 113 | 10000 | 0.633798 | 0.109335 | 0.199937 | current |
| `20261105T001837Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 114 | 10000 | 0.627303 | 0.109317 | 0.201137 | current |
| `20261105T001837Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 115 | 10000 | 0.583599 | 0.111107 | 0.170332 | current |
| `20261105T001837Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 116 | 10000 | 0.641888 | 0.108431 | 0.223888 | current |
| `20261104T234127Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 117 | 10000 | 0.637032 | 0.108987 | 0.213707 | current |
| `20261104T234127Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 118 | 10000 | 0.631298 | 0.108674 | 0.225690 | current |
| `20261104T234127Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 119 | 10000 | 0.615181 | 0.109894 | 0.191712 | current |
| `20261104T234127Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 120 | 10000 | 0.581055 | 0.111638 | 0.163847 | current |
| `20261104T234127Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 121 | 10000 | 0.626227 | 0.108907 | 0.235759 | current |
| `20261104T234127Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 122 | 10000 | 0.614992 | 0.109424 | 0.210623 | current |
| `20261104T234127Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 123 | 10000 | 0.650579 | 0.108177 | 0.246998 | current |
| `20261104T234127Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 124 | 10000 | 0.642130 | 0.108572 | 0.223226 | current |
| `20261104T234127Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 125 | 10000 | 0.588930 | 0.111351 | 0.172048 | current |
| `20261104T234127Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 126 | 10000 | 0.650140 | 0.108995 | 0.195561 | current |
| `20261104T234127Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 127 | 10000 | 0.603363 | 0.110454 | 0.179259 | current |
| `20261104T234127Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 128 | 10000 | 0.616641 | 0.109900 | 0.199487 | current |
| `20261104T234132Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 129 | 10000 | 0.609698 | 0.110034 | 0.189633 | current |
| `20261104T234132Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 130 | 10000 | 0.652424 | 0.108790 | 0.208795 | current |
| `20261104T234132Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 131 | 10000 | 0.634613 | 0.109521 | 0.192067 | current |
| `20261104T234132Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 132 | 10000 | 0.639156 | 0.109223 | 0.196940 | current |
| `20261104T234132Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 133 | 10000 | 0.666356 | 0.107680 | 0.233156 | current |
| `20261104T234132Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 134 | 10000 | 0.618191 | 0.109802 | 0.195782 | current |
| `20261104T234132Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 135 | 10000 | 0.645015 | 0.108720 | 0.212990 | current |
| `20261104T234132Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 136 | 10000 | 0.632562 | 0.109204 | 0.212837 | current |
| `20261104T234132Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 137 | 10000 | 0.596402 | 0.110662 | 0.184858 | current |
| `20261104T234132Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 138 | 10000 | 0.621398 | 0.109868 | 0.195347 | current |
| `20261104T234132Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 139 | 10000 | 0.598579 | 0.111081 | 0.175819 | current |
| `20261104T234132Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 140 | 10000 | 0.667521 | 0.108524 | 0.213989 | current |
| `20261105T100533Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 141 | 10000 | 0.633682 | 0.108719 | 0.223792 | current |
| `20261105T100533Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 142 | 10000 | 0.545200 | 0.112782 | 0.150006 | current |
| `20261105T100533Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 143 | 10000 | 0.636952 | 0.109532 | 0.197848 | current |
| `20261105T100533Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 144 | 10000 | 0.621210 | 0.110054 | 0.179362 | current |
| `20261105T100533Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 145 | 10000 | 0.648975 | 0.108118 | 0.231747 | current |
| `20261105T100533Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 146 | 10000 | 0.608004 | 0.109808 | 0.207101 | current |
| `20261105T100533Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 147 | 10000 | 0.611534 | 0.110026 | 0.186190 | current |
| `20261105T100533Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 148 | 10000 | 0.611024 | 0.109983 | 0.198530 | current |
| `20261105T100533Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 149 | 10000 | 0.606777 | 0.109889 | 0.202874 | current |
| `20261105T100533Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 150 | 10000 | 0.623593 | 0.110285 | 0.179105 | current |
| `20261105T100533Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 151 | 10000 | 0.599152 | 0.110816 | 0.177597 | current |
| `20261105T100533Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 152 | 10000 | 0.614679 | 0.110135 | 0.187678 | current |
| `20261105T005435Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 153 | 10000 | 0.640697 | 0.108537 | 0.240017 | current |
| `20261105T005435Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 154 | 10000 | 0.651887 | 0.108301 | 0.224039 | current |
| `20261105T005435Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 155 | 10000 | 0.601186 | 0.110620 | 0.181770 | current |
| `20261105T005435Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 156 | 10000 | 0.609536 | 0.110247 | 0.194056 | current |
| `20261105T005435Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 157 | 10000 | 0.657701 | 0.108132 | 0.225325 | current |
| `20261105T005435Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 158 | 10000 | 0.604851 | 0.109920 | 0.205454 | current |
| `20261105T005435Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 159 | 10000 | 0.602467 | 0.110184 | 0.185255 | current |
| `20261105T005435Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 160 | 10000 | 0.618388 | 0.110264 | 0.180160 | current |
| `20261105T005435Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 161 | 10000 | 0.647085 | 0.108471 | 0.222604 | current |
| `20261105T005435Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 162 | 10000 | 0.606777 | 0.110033 | 0.191070 | current |
| `20261105T005435Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 163 | 10000 | 0.646045 | 0.108761 | 0.203233 | current |
| `20261105T005435Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 164 | 10000 | 0.602172 | 0.110417 | 0.181527 | current |
| `20261105T005447Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 165 | 10000 | 0.621578 | 0.109223 | 0.214867 | current |
| `20261105T005447Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 166 | 10000 | 0.610181 | 0.109672 | 0.207521 | current |
| `20261105T005447Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 167 | 10000 | 0.600801 | 0.110767 | 0.172543 | current |
| `20261105T005447Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 168 | 10000 | 0.629220 | 0.109096 | 0.231302 | current |
| `20261105T005447Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 169 | 10000 | 0.614894 | 0.110351 | 0.178652 | current |
| `20261105T005447Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 170 | 10000 | 0.646735 | 0.108652 | 0.217807 | current |
| `20261105T005447Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 171 | 10000 | 0.635088 | 0.108665 | 0.234530 | current |
| `20261105T005447Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 172 | 10000 | 0.639487 | 0.108641 | 0.226896 | current |
| `20261105T005447Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 173 | 10000 | 0.645373 | 0.108878 | 0.205830 | current |
| `20261105T005447Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 174 | 10000 | 0.590256 | 0.110359 | 0.201830 | current |
| `20261105T005447Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 175 | 10000 | 0.629650 | 0.108947 | 0.218363 | current |
| `20261105T005447Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 176 | 10000 | 0.657029 | 0.108353 | 0.215311 | current |
| `20261105T124200Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 177 | 10000 | 0.641835 | 0.108660 | 0.234411 | current |
| `20261105T124200Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 178 | 10000 | 0.639407 | 0.109059 | 0.207803 | current |
| `20261105T124200Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 179 | 10000 | 0.615082 | 0.110043 | 0.185965 | current |
| `20261105T124200Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 180 | 10000 | 0.625108 | 0.109569 | 0.197034 | current |
| `20261105T124200Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 181 | 10000 | 0.654593 | 0.108573 | 0.214095 | current |
| `20261105T124200Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 182 | 10000 | 0.628861 | 0.109621 | 0.192111 | current |
| `20261105T124200Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 183 | 10000 | 0.622456 | 0.109572 | 0.211848 | current |
| `20261105T124200Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 184 | 10000 | 0.608246 | 0.110348 | 0.181231 | current |
| `20261105T124200Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 185 | 10000 | 0.661688 | 0.107968 | 0.239125 | current |
| `20261105T124200Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 186 | 10000 | 0.670764 | 0.107947 | 0.230676 | current |
| `20261105T124200Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 187 | 10000 | 0.594610 | 0.110621 | 0.184233 | current |
| `20261105T124200Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 188 | 10000 | 0.656608 | 0.107727 | 0.254518 | current |
| `20261105T012925Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 189 | 10000 | 0.598346 | 0.110298 | 0.188767 | current |
| `20261105T012925Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 190 | 10000 | 0.629623 | 0.109290 | 0.211085 | current |
| `20261105T012925Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 191 | 10000 | 0.603865 | 0.110408 | 0.186758 | current |
| `20261105T012925Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 192 | 10000 | 0.634282 | 0.109461 | 0.194706 | current |
| `20261105T012925Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 193 | 10000 | 0.619517 | 0.109582 | 0.197172 | current |
| `20261105T012925Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 194 | 10000 | 0.636127 | 0.108799 | 0.223133 | current |
| `20261105T012925Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 195 | 10000 | 0.656456 | 0.108173 | 0.232918 | current |
| `20261105T012925Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 196 | 10000 | 0.646601 | 0.108783 | 0.207215 | current |
| `20261105T012925Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 197 | 10000 | 0.650220 | 0.108625 | 0.214647 | current |
| `20261105T012925Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 198 | 10000 | 0.635124 | 0.108798 | 0.217269 | current |
| `20261105T012925Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 199 | 10000 | 0.623764 | 0.109984 | 0.185830 | current |
| `20261105T012925Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 200 | 10000 | 0.640267 | 0.109341 | 0.194608 | current |
| `20261105T013749Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 201 | 10000 | 0.615216 | 0.110026 | 0.189762 | current |
| `20261105T013749Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 202 | 10000 | 0.676229 | 0.107993 | 0.218165 | current |
| `20261105T013749Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 203 | 10000 | 0.633574 | 0.108835 | 0.224089 | current |
| `20261105T013749Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 204 | 10000 | 0.645938 | 0.109251 | 0.188685 | current |
| `20261105T013749Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 205 | 10000 | 0.622411 | 0.109479 | 0.198355 | current |
| `20261105T013749Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 206 | 10000 | 0.634389 | 0.109137 | 0.208843 | current |
| `20261105T013749Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 207 | 10000 | 0.644262 | 0.108372 | 0.222237 | current |
| `20261105T013749Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 208 | 10000 | 0.669322 | 0.107812 | 0.229046 | current |
| `20261105T013749Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 209 | 10000 | 0.647998 | 0.108741 | 0.222359 | current |
| `20261105T013749Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 210 | 10000 | 0.674366 | 0.108068 | 0.210141 | current |
| `20261105T013749Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 211 | 10000 | 0.604071 | 0.109497 | 0.238260 | current |
| `20261105T013749Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 212 | 10000 | 0.657012 | 0.108366 | 0.231361 | current |
| `20261105T013755Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 213 | 10000 | 0.598113 | 0.110466 | 0.177495 | current |
| `20261105T013755Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 214 | 10000 | 0.603516 | 0.110596 | 0.175112 | current |
| `20261105T013755Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 215 | 10000 | 0.615091 | 0.110074 | 0.186758 | current |
| `20261105T013755Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 216 | 10000 | 0.636871 | 0.109222 | 0.194761 | current |
| `20261105T013755Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 217 | 10000 | 0.627688 | 0.109043 | 0.209343 | current |
| `20261105T013755Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 218 | 10000 | 0.636226 | 0.108780 | 0.221835 | current |
| `20261105T013755Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 219 | 10000 | 0.646045 | 0.109077 | 0.196869 | current |
| `20261105T013755Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 220 | 10000 | 0.623486 | 0.109817 | 0.186252 | current |
| `20261105T013755Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 221 | 10000 | 0.584710 | 0.110964 | 0.191642 | current |
| `20261105T013755Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 222 | 10000 | 0.601527 | 0.110576 | 0.179394 | current |
| `20261105T013755Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 223 | 10000 | 0.598669 | 0.109930 | 0.203264 | current |
| `20261105T013755Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 224 | 10000 | 0.608936 | 0.109829 | 0.194386 | current |
| `20261105T124205Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 225 | 10000 | 0.658499 | 0.108252 | 0.222756 | current |
| `20261105T124205Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 226 | 10000 | 0.691657 | 0.106842 | 0.268582 | current |
| `20261105T124205Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 227 | 10000 | 0.623468 | 0.109266 | 0.204662 | current |
| `20261105T124205Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 228 | 10000 | 0.616533 | 0.109931 | 0.195075 | current |
| `20261105T124205Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 229 | 10000 | 0.607171 | 0.110023 | 0.187545 | current |
| `20261105T124205Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 230 | 10000 | 0.602530 | 0.109925 | 0.205048 | current |
| `20261105T124205Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 231 | 10000 | 0.613675 | 0.109738 | 0.211745 | current |
| `20261105T124205Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 232 | 10000 | 0.629739 | 0.109581 | 0.194243 | current |
| `20261105T124205Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 233 | 10000 | 0.573941 | 0.112154 | 0.154086 | current |
| `20261105T124205Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 234 | 10000 | 0.633171 | 0.109492 | 0.210133 | current |
| `20261105T124205Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 235 | 10000 | 0.641476 | 0.108877 | 0.211758 | current |
| `20261105T124205Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 236 | 10000 | 0.611803 | 0.109750 | 0.206120 | current |
| `20261105T140236Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 237 | 10000 | 0.641808 | 0.108720 | 0.216733 | current |
| `20261105T140236Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 238 | 10000 | 0.640007 | 0.108391 | 0.248129 | current |
| `20261105T140236Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 239 | 10000 | 0.632526 | 0.108972 | 0.226264 | current |
| `20261105T140236Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 240 | 10000 | 0.612573 | 0.109852 | 0.190536 | current |
| `20261105T140236Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 241 | 10000 | 0.634255 | 0.109315 | 0.200851 | current |
| `20261105T140236Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 242 | 10000 | 0.579684 | 0.111852 | 0.159367 | current |
| `20261105T140236Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 243 | 10000 | 0.600595 | 0.110579 | 0.188741 | current |
| `20261105T140236Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 244 | 10000 | 0.596509 | 0.110467 | 0.189875 | current |
| `20261105T140236Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 245 | 10000 | 0.698403 | 0.107289 | 0.243374 | current |
| `20261105T140236Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 246 | 10000 | 0.651376 | 0.108440 | 0.217958 | current |
| `20261105T140236Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 247 | 10000 | 0.640831 | 0.109018 | 0.204273 | current |
| `20261105T140236Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 248 | 10000 | 0.663355 | 0.108080 | 0.226257 | current |
| `20261105T103841Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 249 | 10000 | 0.640517 | 0.108740 | 0.219248 | current |
| `20261105T103841Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 250 | 10000 | 0.578860 | 0.111536 | 0.166771 | current |
| `20261105T103841Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 251 | 10000 | 0.622339 | 0.109745 | 0.197435 | current |
| `20261105T103841Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 252 | 10000 | 0.589190 | 0.110608 | 0.201885 | current |
| `20261105T103841Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 253 | 10000 | 0.618594 | 0.110070 | 0.185682 | current |
| `20261105T103841Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 254 | 10000 | 0.647998 | 0.108374 | 0.224201 | current |
| `20261105T103841Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 255 | 10000 | 0.649710 | 0.109256 | 0.193798 | current |
| `20261105T103841Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 256 | 10000 | 0.610549 | 0.109815 | 0.190799 | current |
| `20261105T103841Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 257 | 10000 | 0.635769 | 0.108911 | 0.204931 | current |
| `20261105T103841Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 258 | 10000 | 0.617394 | 0.109790 | 0.199760 | current |
| `20261105T103841Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 259 | 10000 | 0.608793 | 0.110165 | 0.191810 | current |
| `20261105T103841Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 260 | 10000 | 0.657800 | 0.108188 | 0.232445 | current |
| `20261105T103937Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 261 | 10000 | 0.614213 | 0.110281 | 0.180672 | current |
| `20261105T103937Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 262 | 10000 | 0.618137 | 0.109426 | 0.219171 | current |
| `20261105T103937Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 263 | 10000 | 0.601993 | 0.110480 | 0.184940 | current |
| `20261105T103937Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 264 | 10000 | 0.609715 | 0.110039 | 0.190441 | current |
| `20261105T103937Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 265 | 10000 | 0.595354 | 0.110207 | 0.198947 | current |
| `20261105T103937Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 266 | 10000 | 0.609626 | 0.109548 | 0.216314 | current |
| `20261105T103937Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 267 | 10000 | 0.636396 | 0.109067 | 0.201730 | current |
| `20261105T103937Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 268 | 10000 | 0.614795 | 0.110080 | 0.191598 | current |
| `20261105T103937Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 269 | 10000 | 0.619284 | 0.109632 | 0.201343 | current |
| `20261105T103937Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 270 | 10000 | 0.657657 | 0.108069 | 0.222642 | current |
| `20261105T103937Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 271 | 10000 | 0.658320 | 0.108805 | 0.199895 | current |
| `20261105T103937Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 272 | 10000 | 0.680037 | 0.107876 | 0.227592 | current |
| `20261105T103853Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 273 | 10000 | 0.611731 | 0.109634 | 0.210764 | current |
| `20261105T103853Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 274 | 10000 | 0.653356 | 0.108286 | 0.227181 | current |
| `20261105T103853Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 275 | 10000 | 0.599574 | 0.109928 | 0.217633 | current |
| `20261105T103853Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 276 | 10000 | 0.643770 | 0.109187 | 0.197900 | current |
| `20261105T103853Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 277 | 10000 | 0.598911 | 0.110139 | 0.197474 | current |
| `20261105T103853Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 278 | 10000 | 0.618549 | 0.110057 | 0.191542 | current |
| `20261105T103853Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 279 | 10000 | 0.664546 | 0.107850 | 0.234907 | current |
| `20261105T103853Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 280 | 10000 | 0.617205 | 0.110574 | 0.187074 | current |
| `20261105T103853Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 281 | 10000 | 0.616274 | 0.109580 | 0.203967 | current |
| `20261105T103853Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 282 | 10000 | 0.621246 | 0.109898 | 0.184106 | current |
| `20261105T103853Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 283 | 10000 | 0.664098 | 0.108534 | 0.210913 | current |
| `20261105T103853Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 284 | 10000 | 0.649772 | 0.108119 | 0.250840 | current |
| `20261105T140242Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 285 | 10000 | 0.642300 | 0.108772 | 0.213703 | current |
| `20261105T140242Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 286 | 10000 | 0.639308 | 0.109547 | 0.196364 | current |
| `20261105T140242Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 287 | 10000 | 0.649118 | 0.109113 | 0.199320 | current |
| `20261105T140242Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 288 | 10000 | 0.638224 | 0.108865 | 0.214944 | current |
| `20261105T140242Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 289 | 10000 | 0.576700 | 0.111685 | 0.166584 | current |
| `20261105T140242Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 290 | 10000 | 0.650113 | 0.108997 | 0.210381 | current |
| `20261105T140242Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 291 | 10000 | 0.666123 | 0.108243 | 0.213911 | current |
| `20261105T140242Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 292 | 10000 | 0.613899 | 0.109549 | 0.208648 | current |
| `20261105T140242Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 293 | 10000 | 0.607368 | 0.110117 | 0.185191 | current |
| `20261105T140242Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 294 | 10000 | 0.612063 | 0.109647 | 0.219124 | current |
| `20261105T140242Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 295 | 10000 | 0.612457 | 0.110333 | 0.183137 | current |
| `20261105T140242Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 296 | 10000 | 0.639209 | 0.109755 | 0.191228 | current |
| `20261105T111110Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 297 | 10000 | 0.657468 | 0.107578 | 0.252874 | current |
| `20261105T111110Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 298 | 10000 | 0.610369 | 0.109605 | 0.207589 | current |
| `20261105T111110Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 299 | 10000 | 0.671105 | 0.107570 | 0.250402 | current |
| `20261105T111110Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 300 | 10000 | 0.599842 | 0.110568 | 0.180748 | current |
| `20261105T111110Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 301 | 10000 | 0.575948 | 0.111783 | 0.159276 | current |
| `20261105T111110Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 302 | 10000 | 0.630017 | 0.109868 | 0.180377 | current |
| `20261105T111110Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 303 | 10000 | 0.634353 | 0.109034 | 0.210916 | current |
| `20261105T111110Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 304 | 10000 | 0.563907 | 0.111697 | 0.170209 | current |
| `20261105T111110Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 305 | 10000 | 0.559526 | 0.111826 | 0.175458 | current |
| `20261105T111110Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 306 | 10000 | 0.588589 | 0.111008 | 0.178213 | current |
| `20261105T111110Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 307 | 10000 | 0.594431 | 0.110350 | 0.195192 | current |
| `20261105T111110Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 308 | 10000 | 0.623853 | 0.109898 | 0.183602 | current |
| `20261105T114320Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 309 | 10000 | 0.661805 | 0.107645 | 0.243800 | current |
| `20261105T114320Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 310 | 10000 | 0.645992 | 0.108698 | 0.209297 | current |
| `20261105T114320Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 311 | 10000 | 0.611006 | 0.109957 | 0.194437 | current |
| `20261105T114320Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 312 | 10000 | 0.672350 | 0.107867 | 0.224418 | current |
| `20261105T114320Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 313 | 10000 | 0.631245 | 0.109380 | 0.197201 | current |
| `20261105T114320Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 314 | 10000 | 0.630178 | 0.109372 | 0.214022 | current |
| `20261105T114320Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 315 | 10000 | 0.586842 | 0.110750 | 0.178535 | current |
| `20261105T114320Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 316 | 10000 | 0.668444 | 0.108293 | 0.239422 | current |
| `20261105T114320Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 317 | 10000 | 0.593938 | 0.110502 | 0.193813 | current |
| `20261105T114320Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 318 | 10000 | 0.593607 | 0.110828 | 0.179134 | current |
| `20261105T114320Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 319 | 10000 | 0.637704 | 0.109321 | 0.188753 | current |
| `20261105T114320Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 320 | 10000 | 0.618549 | 0.110517 | 0.174949 | current |
| `20261105T114647Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 321 | 10000 | 0.645920 | 0.108910 | 0.204573 | current |
| `20261105T114647Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 322 | 10000 | 0.650615 | 0.107856 | 0.254458 | current |
| `20261105T114647Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 323 | 10000 | 0.630573 | 0.109056 | 0.209986 | current |
| `20261105T114647Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 324 | 10000 | 0.615109 | 0.110422 | 0.176013 | current |
| `20261105T114647Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 325 | 10000 | 0.660909 | 0.108237 | 0.228414 | current |
| `20261105T114647Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 326 | 10000 | 0.612565 | 0.110202 | 0.185142 | current |
| `20261105T114647Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 327 | 10000 | 0.602584 | 0.109877 | 0.207120 | current |
| `20261105T114647Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 328 | 10000 | 0.661527 | 0.108308 | 0.225792 | current |
| `20261105T114647Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 329 | 10000 | 0.652971 | 0.108673 | 0.201363 | current |
| `20261105T114647Z` | pilot2-phase2 | eudirectlapse | `A_raw` | raw | — | 330 | 10000 | 0.641996 | 0.109185 | 0.197402 | current |
| `20261104T234013Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 93 | 10000 | 0.614240 | 0.110468 | 0.173808 | current |
| `20261104T234013Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 94 | 10000 | 0.658974 | 0.108138 | 0.250593 | current |
| `20261104T234013Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 95 | 10000 | 0.645786 | 0.108894 | 0.205892 | current |
| `20261104T234013Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 96 | 10000 | 0.628655 | 0.110078 | 0.185499 | current |
| `20261104T234013Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 97 | 10000 | 0.628387 | 0.109754 | 0.191710 | current |
| `20261104T234013Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 98 | 10000 | 0.634909 | 0.109082 | 0.210557 | current |
| `20261104T234013Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 99 | 10000 | 0.621784 | 0.110155 | 0.179085 | current |
| `20261104T234013Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 100 | 10000 | 0.661572 | 0.108014 | 0.229623 | current |
| `20261104T234013Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 101 | 10000 | 0.593454 | 0.110840 | 0.170510 | current |
| `20261104T234013Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 102 | 10000 | 0.611579 | 0.109666 | 0.197886 | current |
| `20261104T234013Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 103 | 10000 | 0.587299 | 0.110968 | 0.166093 | current |
| `20261104T234013Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 104 | 10000 | 0.674536 | 0.107690 | 0.234932 | current |
| `20261105T001837Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 105 | 10000 | 0.647398 | 0.109374 | 0.196519 | current |
| `20261105T001837Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 106 | 10000 | 0.597871 | 0.111724 | 0.165054 | current |
| `20261105T001837Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 107 | 10000 | 0.624561 | 0.109860 | 0.185895 | current |
| `20261105T001837Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 108 | 10000 | 0.648948 | 0.108309 | 0.227093 | current |
| `20261105T001837Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 109 | 10000 | 0.600111 | 0.110197 | 0.187509 | current |
| `20261105T001837Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 110 | 10000 | 0.668381 | 0.107332 | 0.238765 | current |
| `20261105T001837Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 111 | 10000 | 0.609823 | 0.110365 | 0.180759 | current |
| `20261105T001837Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 112 | 10000 | 0.617582 | 0.109557 | 0.203085 | current |
| `20261105T001837Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 113 | 10000 | 0.634712 | 0.109283 | 0.199677 | current |
| `20261105T001837Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 114 | 10000 | 0.632848 | 0.109228 | 0.203361 | current |
| `20261105T001837Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 115 | 10000 | 0.599161 | 0.110622 | 0.179833 | current |
| `20261105T001837Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 116 | 10000 | 0.643591 | 0.108859 | 0.212811 | current |
| `20261104T234127Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 117 | 10000 | 0.627473 | 0.109537 | 0.206865 | current |
| `20261104T234127Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 118 | 10000 | 0.636414 | 0.108094 | 0.248872 | current |
| `20261104T234127Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 119 | 10000 | 0.608157 | 0.110074 | 0.190885 | current |
| `20261104T234127Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 120 | 10000 | 0.593239 | 0.111023 | 0.175731 | current |
| `20261104T234127Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 121 | 10000 | 0.624194 | 0.109170 | 0.228207 | current |
| `20261104T234127Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 122 | 10000 | 0.610074 | 0.109957 | 0.189288 | current |
| `20261104T234127Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 123 | 10000 | 0.649226 | 0.108716 | 0.225084 | current |
| `20261104T234127Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 124 | 10000 | 0.648805 | 0.108472 | 0.221652 | current |
| `20261104T234127Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 125 | 10000 | 0.594305 | 0.110998 | 0.182016 | current |
| `20261104T234127Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 126 | 10000 | 0.658544 | 0.108479 | 0.205271 | current |
| `20261104T234127Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 127 | 10000 | 0.607906 | 0.110305 | 0.180985 | current |
| `20261104T234127Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 128 | 10000 | 0.626774 | 0.109660 | 0.193244 | current |
| `20261104T234132Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 129 | 10000 | 0.610011 | 0.109943 | 0.190908 | current |
| `20261104T234132Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 130 | 10000 | 0.647819 | 0.108895 | 0.202983 | current |
| `20261104T234132Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 131 | 10000 | 0.636342 | 0.109288 | 0.192937 | current |
| `20261104T234132Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 132 | 10000 | 0.636988 | 0.109245 | 0.196666 | current |
| `20261104T234132Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 133 | 10000 | 0.670226 | 0.107677 | 0.236690 | current |
| `20261104T234132Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 134 | 10000 | 0.626183 | 0.110050 | 0.186867 | current |
| `20261104T234132Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 135 | 10000 | 0.633054 | 0.109339 | 0.204324 | current |
| `20261104T234132Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 136 | 10000 | 0.637794 | 0.109041 | 0.217727 | current |
| `20261104T234132Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 137 | 10000 | 0.594494 | 0.110872 | 0.170840 | current |
| `20261104T234132Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 138 | 10000 | 0.629148 | 0.109616 | 0.194758 | current |
| `20261104T234132Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 139 | 10000 | 0.586484 | 0.111763 | 0.163256 | current |
| `20261104T234132Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 140 | 10000 | 0.662584 | 0.108990 | 0.203256 | current |
| `20261105T100533Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 141 | 10000 | 0.636692 | 0.108839 | 0.211179 | current |
| `20261105T100533Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 142 | 10000 | 0.543963 | 0.113182 | 0.151576 | current |
| `20261105T100533Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 143 | 10000 | 0.633717 | 0.109656 | 0.191387 | current |
| `20261105T100533Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 144 | 10000 | 0.624767 | 0.109915 | 0.183528 | current |
| `20261105T100533Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 145 | 10000 | 0.642032 | 0.108773 | 0.211210 | current |
| `20261105T100533Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 146 | 10000 | 0.615611 | 0.109715 | 0.201490 | current |
| `20261105T100533Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 147 | 10000 | 0.625842 | 0.109322 | 0.200635 | current |
| `20261105T100533Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 148 | 10000 | 0.619526 | 0.109490 | 0.203648 | current |
| `20261105T100533Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 149 | 10000 | 0.607099 | 0.110139 | 0.186857 | current |
| `20261105T100533Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 150 | 10000 | 0.626353 | 0.110189 | 0.185491 | current |
| `20261105T100533Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 151 | 10000 | 0.609366 | 0.110255 | 0.193553 | current |
| `20261105T100533Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 152 | 10000 | 0.614930 | 0.110109 | 0.187719 | current |
| `20261105T005435Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 153 | 10000 | 0.637695 | 0.108941 | 0.213589 | current |
| `20261105T005435Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 154 | 10000 | 0.653446 | 0.108145 | 0.228225 | current |
| `20261105T005435Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 155 | 10000 | 0.604886 | 0.110672 | 0.171180 | current |
| `20261105T005435Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 156 | 10000 | 0.605263 | 0.110367 | 0.185219 | current |
| `20261105T005435Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 157 | 10000 | 0.667073 | 0.108026 | 0.223194 | current |
| `20261105T005435Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 158 | 10000 | 0.610755 | 0.109736 | 0.208823 | current |
| `20261105T005435Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 159 | 10000 | 0.609474 | 0.109927 | 0.187267 | current |
| `20261105T005435Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 160 | 10000 | 0.625511 | 0.109912 | 0.187850 | current |
| `20261105T005435Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 161 | 10000 | 0.646260 | 0.108310 | 0.220737 | current |
| `20261105T005435Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 162 | 10000 | 0.608631 | 0.109713 | 0.203124 | current |
| `20261105T005435Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 163 | 10000 | 0.633435 | 0.109641 | 0.185860 | current |
| `20261105T005435Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 164 | 10000 | 0.609572 | 0.110258 | 0.175795 | current |
| `20261105T005447Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 165 | 10000 | 0.631943 | 0.108953 | 0.212669 | current |
| `20261105T005447Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 166 | 10000 | 0.614984 | 0.109543 | 0.207569 | current |
| `20261105T005447Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 167 | 10000 | 0.609312 | 0.110396 | 0.181464 | current |
| `20261105T005447Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 168 | 10000 | 0.628010 | 0.109147 | 0.216968 | current |
| `20261105T005447Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 169 | 10000 | 0.610674 | 0.110685 | 0.174306 | current |
| `20261105T005447Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 170 | 10000 | 0.650507 | 0.108383 | 0.231820 | current |
| `20261105T005447Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 171 | 10000 | 0.640894 | 0.108525 | 0.215799 | current |
| `20261105T005447Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 172 | 10000 | 0.642560 | 0.108562 | 0.229541 | current |
| `20261105T005447Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 173 | 10000 | 0.636620 | 0.109579 | 0.184287 | current |
| `20261105T005447Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 174 | 10000 | 0.594350 | 0.110014 | 0.204861 | current |
| `20261105T005447Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 175 | 10000 | 0.629112 | 0.108848 | 0.216326 | current |
| `20261105T005447Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 176 | 10000 | 0.651107 | 0.108251 | 0.220026 | current |
| `20261105T124200Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 177 | 10000 | 0.641163 | 0.109020 | 0.207802 | current |
| `20261105T124200Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 178 | 10000 | 0.645060 | 0.108728 | 0.211570 | current |
| `20261105T124200Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 179 | 10000 | 0.613729 | 0.109617 | 0.203471 | current |
| `20261105T124200Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 180 | 10000 | 0.630429 | 0.109539 | 0.194683 | current |
| `20261105T124200Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 181 | 10000 | 0.633404 | 0.109085 | 0.206167 | current |
| `20261105T124200Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 182 | 10000 | 0.629874 | 0.109649 | 0.193084 | current |
| `20261105T124200Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 183 | 10000 | 0.629309 | 0.109513 | 0.194056 | current |
| `20261105T124200Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 184 | 10000 | 0.619123 | 0.110020 | 0.180362 | current |
| `20261105T124200Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 185 | 10000 | 0.653258 | 0.108363 | 0.232046 | current |
| `20261105T124200Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 186 | 10000 | 0.654584 | 0.108622 | 0.205200 | current |
| `20261105T124200Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 187 | 10000 | 0.587676 | 0.111252 | 0.169375 | current |
| `20261105T124200Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 188 | 10000 | 0.655954 | 0.107704 | 0.254383 | current |
| `20261105T012925Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 189 | 10000 | 0.598373 | 0.110605 | 0.181777 | current |
| `20261105T012925Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 190 | 10000 | 0.628279 | 0.109321 | 0.208757 | current |
| `20261105T012925Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 191 | 10000 | 0.614939 | 0.110173 | 0.188860 | current |
| `20261105T012925Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 192 | 10000 | 0.619454 | 0.109936 | 0.187101 | current |
| `20261105T012925Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 193 | 10000 | 0.621058 | 0.109871 | 0.187272 | current |
| `20261105T012925Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 194 | 10000 | 0.625457 | 0.109084 | 0.215127 | current |
| `20261105T012925Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 195 | 10000 | 0.664994 | 0.107804 | 0.233233 | current |
| `20261105T012925Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 196 | 10000 | 0.636271 | 0.109493 | 0.188928 | current |
| `20261105T012925Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 197 | 10000 | 0.659753 | 0.108304 | 0.214576 | current |
| `20261105T012925Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 198 | 10000 | 0.646753 | 0.108427 | 0.225299 | current |
| `20261105T012925Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 199 | 10000 | 0.629139 | 0.109592 | 0.201747 | current |
| `20261105T012925Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 200 | 10000 | 0.639595 | 0.109369 | 0.192770 | current |
| `20261105T013749Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 201 | 10000 | 0.603193 | 0.110799 | 0.174739 | current |
| `20261105T013749Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 202 | 10000 | 0.663597 | 0.108478 | 0.208128 | current |
| `20261105T013749Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 203 | 10000 | 0.632723 | 0.109179 | 0.213485 | current |
| `20261105T013749Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 204 | 10000 | 0.658785 | 0.109117 | 0.191691 | current |
| `20261105T013749Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 205 | 10000 | 0.624050 | 0.109700 | 0.192699 | current |
| `20261105T013749Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 206 | 10000 | 0.638546 | 0.109118 | 0.203374 | current |
| `20261105T013749Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 207 | 10000 | 0.657558 | 0.108674 | 0.207880 | current |
| `20261105T013749Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 208 | 10000 | 0.660730 | 0.107950 | 0.222531 | current |
| `20261105T013749Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 209 | 10000 | 0.650704 | 0.108775 | 0.222347 | current |
| `20261105T013749Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 210 | 10000 | 0.674778 | 0.108009 | 0.215842 | current |
| `20261105T013749Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 211 | 10000 | 0.600891 | 0.109720 | 0.205505 | current |
| `20261105T013749Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 212 | 10000 | 0.663785 | 0.107884 | 0.242677 | current |
| `20261105T013755Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 213 | 10000 | 0.601249 | 0.110434 | 0.176769 | current |
| `20261105T013755Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 214 | 10000 | 0.597889 | 0.110892 | 0.171267 | current |
| `20261105T013755Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 215 | 10000 | 0.612609 | 0.110373 | 0.179447 | current |
| `20261105T013755Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 216 | 10000 | 0.628629 | 0.109782 | 0.186707 | current |
| `20261105T013755Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 217 | 10000 | 0.630134 | 0.108846 | 0.218891 | current |
| `20261105T013755Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 218 | 10000 | 0.639989 | 0.108807 | 0.227088 | current |
| `20261105T013755Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 219 | 10000 | 0.648491 | 0.108899 | 0.206858 | current |
| `20261105T013755Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 220 | 10000 | 0.620252 | 0.110040 | 0.182859 | current |
| `20261105T013755Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 221 | 10000 | 0.595712 | 0.110517 | 0.190887 | current |
| `20261105T013755Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 222 | 10000 | 0.616999 | 0.110155 | 0.179307 | current |
| `20261105T013755Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 223 | 10000 | 0.613944 | 0.109783 | 0.201797 | current |
| `20261105T013755Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 224 | 10000 | 0.611140 | 0.109635 | 0.201754 | current |
| `20261105T124205Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 225 | 10000 | 0.649020 | 0.108901 | 0.211960 | current |
| `20261105T124205Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 226 | 10000 | 0.688853 | 0.106800 | 0.268391 | current |
| `20261105T124205Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 227 | 10000 | 0.633332 | 0.108872 | 0.207507 | current |
| `20261105T124205Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 228 | 10000 | 0.628772 | 0.109389 | 0.195658 | current |
| `20261105T124205Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 229 | 10000 | 0.593813 | 0.110662 | 0.178335 | current |
| `20261105T124205Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 230 | 10000 | 0.602010 | 0.109886 | 0.200256 | current |
| `20261105T124205Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 231 | 10000 | 0.623262 | 0.109430 | 0.214132 | current |
| `20261105T124205Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 232 | 10000 | 0.635303 | 0.109328 | 0.199197 | current |
| `20261105T124205Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 233 | 10000 | 0.580669 | 0.111713 | 0.162357 | current |
| `20261105T124205Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 234 | 10000 | 0.649083 | 0.108785 | 0.216567 | current |
| `20261105T124205Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 235 | 10000 | 0.628378 | 0.109276 | 0.206178 | current |
| `20261105T124205Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 236 | 10000 | 0.616489 | 0.109559 | 0.205616 | current |
| `20261105T140236Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 237 | 10000 | 0.648948 | 0.108348 | 0.226064 | current |
| `20261105T140236Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 238 | 10000 | 0.644908 | 0.108307 | 0.233364 | current |
| `20261105T140236Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 239 | 10000 | 0.637767 | 0.108462 | 0.244038 | current |
| `20261105T140236Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 240 | 10000 | 0.617967 | 0.109430 | 0.205092 | current |
| `20261105T140236Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 241 | 10000 | 0.625430 | 0.109724 | 0.187618 | current |
| `20261105T140236Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 242 | 10000 | 0.580454 | 0.112658 | 0.156751 | current |
| `20261105T140236Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 243 | 10000 | 0.611489 | 0.110094 | 0.193545 | current |
| `20261105T140236Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 244 | 10000 | 0.598077 | 0.110446 | 0.191319 | current |
| `20261105T140236Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 245 | 10000 | 0.691379 | 0.107865 | 0.228536 | current |
| `20261105T140236Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 246 | 10000 | 0.660981 | 0.108186 | 0.219631 | current |
| `20261105T140236Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 247 | 10000 | 0.645239 | 0.109246 | 0.197964 | current |
| `20261105T140236Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 248 | 10000 | 0.653338 | 0.108716 | 0.207113 | current |
| `20261105T103841Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 249 | 10000 | 0.629775 | 0.109379 | 0.207464 | current |
| `20261105T103841Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 250 | 10000 | 0.580481 | 0.111174 | 0.176308 | current |
| `20261105T103841Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 251 | 10000 | 0.608820 | 0.110447 | 0.179542 | current |
| `20261105T103841Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 252 | 10000 | 0.593616 | 0.110520 | 0.193035 | current |
| `20261105T103841Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 253 | 10000 | 0.618961 | 0.110246 | 0.179407 | current |
| `20261105T103841Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 254 | 10000 | 0.638529 | 0.108847 | 0.221117 | current |
| `20261105T103841Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 255 | 10000 | 0.638484 | 0.109417 | 0.193314 | current |
| `20261105T103841Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 256 | 10000 | 0.614401 | 0.109765 | 0.196584 | current |
| `20261105T103841Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 257 | 10000 | 0.639774 | 0.108786 | 0.214702 | current |
| `20261105T103841Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 258 | 10000 | 0.633861 | 0.108793 | 0.212143 | current |
| `20261105T103841Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 259 | 10000 | 0.606069 | 0.110058 | 0.191491 | current |
| `20261105T103841Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 260 | 10000 | 0.659198 | 0.108614 | 0.212278 | current |
| `20261105T103937Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 261 | 10000 | 0.610477 | 0.110163 | 0.186128 | current |
| `20261105T103937Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 262 | 10000 | 0.604600 | 0.109954 | 0.197314 | current |
| `20261105T103937Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 263 | 10000 | 0.602754 | 0.110653 | 0.180536 | current |
| `20261105T103937Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 264 | 10000 | 0.616309 | 0.109448 | 0.203463 | current |
| `20261105T103937Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 265 | 10000 | 0.599063 | 0.110067 | 0.203197 | current |
| `20261105T103937Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 266 | 10000 | 0.613801 | 0.109138 | 0.220508 | current |
| `20261105T103937Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 267 | 10000 | 0.639236 | 0.109362 | 0.198030 | current |
| `20261105T103937Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 268 | 10000 | 0.617161 | 0.110119 | 0.184702 | current |
| `20261105T103937Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 269 | 10000 | 0.605746 | 0.110258 | 0.191075 | current |
| `20261105T103937Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 270 | 10000 | 0.669178 | 0.107992 | 0.222753 | current |
| `20261105T103937Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 271 | 10000 | 0.657876 | 0.108818 | 0.204341 | current |
| `20261105T103937Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 272 | 10000 | 0.672072 | 0.108186 | 0.221801 | current |
| `20261105T103853Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 273 | 10000 | 0.616265 | 0.109692 | 0.199510 | current |
| `20261105T103853Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 274 | 10000 | 0.657764 | 0.107918 | 0.228423 | current |
| `20261105T103853Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 275 | 10000 | 0.605702 | 0.109725 | 0.211905 | current |
| `20261105T103853Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 276 | 10000 | 0.656116 | 0.109196 | 0.190210 | current |
| `20261105T103853Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 277 | 10000 | 0.611086 | 0.110141 | 0.188568 | current |
| `20261105T103853Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 278 | 10000 | 0.616354 | 0.110417 | 0.178040 | current |
| `20261105T103853Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 279 | 10000 | 0.652147 | 0.108370 | 0.220005 | current |
| `20261105T103853Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 280 | 10000 | 0.620081 | 0.110228 | 0.186628 | current |
| `20261105T103853Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 281 | 10000 | 0.624991 | 0.109585 | 0.211294 | current |
| `20261105T103853Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 282 | 10000 | 0.618952 | 0.110171 | 0.180020 | current |
| `20261105T103853Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 283 | 10000 | 0.671857 | 0.108380 | 0.220061 | current |
| `20261105T103853Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 284 | 10000 | 0.640464 | 0.108518 | 0.239218 | current |
| `20261105T140242Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 285 | 10000 | 0.637418 | 0.109111 | 0.205021 | current |
| `20261105T140242Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 286 | 10000 | 0.635572 | 0.109800 | 0.186477 | current |
| `20261105T140242Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 287 | 10000 | 0.641611 | 0.109219 | 0.194959 | current |
| `20261105T140242Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 288 | 10000 | 0.630358 | 0.109135 | 0.201946 | current |
| `20261105T140242Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 289 | 10000 | 0.575276 | 0.111642 | 0.168992 | current |
| `20261105T140242Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 290 | 10000 | 0.650158 | 0.108935 | 0.213333 | current |
| `20261105T140242Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 291 | 10000 | 0.684445 | 0.107892 | 0.223675 | current |
| `20261105T140242Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 292 | 10000 | 0.620843 | 0.109254 | 0.212999 | current |
| `20261105T140242Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 293 | 10000 | 0.604985 | 0.110203 | 0.183985 | current |
| `20261105T140242Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 294 | 10000 | 0.594736 | 0.110295 | 0.204860 | current |
| `20261105T140242Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 295 | 10000 | 0.609715 | 0.110682 | 0.176165 | current |
| `20261105T140242Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 296 | 10000 | 0.634201 | 0.109881 | 0.182545 | current |
| `20261105T111110Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 297 | 10000 | 0.646269 | 0.108130 | 0.234052 | current |
| `20261105T111110Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 298 | 10000 | 0.622214 | 0.109145 | 0.217620 | current |
| `20261105T111110Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 299 | 10000 | 0.658553 | 0.108034 | 0.244992 | current |
| `20261105T111110Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 300 | 10000 | 0.576476 | 0.111617 | 0.165858 | current |
| `20261105T111110Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 301 | 10000 | 0.573950 | 0.111781 | 0.158222 | current |
| `20261105T111110Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 302 | 10000 | 0.630671 | 0.109887 | 0.181942 | current |
| `20261105T111110Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 303 | 10000 | 0.621739 | 0.109700 | 0.196324 | current |
| `20261105T111110Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 304 | 10000 | 0.552358 | 0.111681 | 0.180359 | current |
| `20261105T111110Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 305 | 10000 | 0.574187 | 0.111132 | 0.181858 | current |
| `20261105T111110Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 306 | 10000 | 0.589933 | 0.111236 | 0.178357 | current |
| `20261105T111110Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 307 | 10000 | 0.597567 | 0.110361 | 0.191910 | current |
| `20261105T111110Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 308 | 10000 | 0.640311 | 0.109177 | 0.198064 | current |
| `20261105T114320Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 309 | 10000 | 0.662952 | 0.107768 | 0.237728 | current |
| `20261105T114320Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 310 | 10000 | 0.642614 | 0.108853 | 0.208165 | current |
| `20261105T114320Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 311 | 10000 | 0.627083 | 0.109388 | 0.201238 | current |
| `20261105T114320Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 312 | 10000 | 0.662530 | 0.108212 | 0.216786 | current |
| `20261105T114320Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 313 | 10000 | 0.630967 | 0.109712 | 0.192718 | current |
| `20261105T114320Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 314 | 10000 | 0.626666 | 0.109292 | 0.217591 | current |
| `20261105T114320Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 315 | 10000 | 0.593177 | 0.110629 | 0.179971 | current |
| `20261105T114320Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 316 | 10000 | 0.677681 | 0.108144 | 0.255629 | current |
| `20261105T114320Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 317 | 10000 | 0.590919 | 0.110557 | 0.190402 | current |
| `20261105T114320Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 318 | 10000 | 0.598050 | 0.110593 | 0.181532 | current |
| `20261105T114320Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 319 | 10000 | 0.637695 | 0.109718 | 0.180442 | current |
| `20261105T114320Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 320 | 10000 | 0.617223 | 0.110305 | 0.174913 | current |
| `20261105T114647Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 321 | 10000 | 0.644513 | 0.108964 | 0.202761 | current |
| `20261105T114647Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 322 | 10000 | 0.662271 | 0.107334 | 0.250594 | current |
| `20261105T114647Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 323 | 10000 | 0.606051 | 0.110087 | 0.191360 | current |
| `20261105T114647Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 324 | 10000 | 0.609276 | 0.110377 | 0.183772 | current |
| `20261105T114647Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 325 | 10000 | 0.662351 | 0.108109 | 0.234173 | current |
| `20261105T114647Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 326 | 10000 | 0.622375 | 0.109795 | 0.193268 | current |
| `20261105T114647Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 327 | 10000 | 0.599054 | 0.110024 | 0.195472 | current |
| `20261105T114647Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 328 | 10000 | 0.653706 | 0.109091 | 0.201724 | current |
| `20261105T114647Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 329 | 10000 | 0.653491 | 0.109263 | 0.189167 | current |
| `20261105T114647Z` | pilot2-phase2 | eudirectlapse | `B_ft30` | fine-tuned | 30 | 330 | 10000 | 0.637274 | 0.109278 | 0.199439 | current |
| `20261031T021845Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 43 | 10000 | 0.946119 | 0.081966 | 0.892155 | current |
| `20261031T021845Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 44 | 10000 | 0.945127 | 0.085596 | 0.888607 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 45 | 10000 | 0.947588 | 0.083166 | 0.887693 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 46 | 10000 | 0.945489 | 0.083827 | 0.891712 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 47 | 10000 | 0.941964 | 0.084347 | 0.870418 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 48 | 10000 | 0.936582 | 0.087933 | 0.864323 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 49 | 10000 | 0.938800 | 0.089039 | 0.858314 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 50 | 10000 | 0.927479 | 0.097529 | 0.840484 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 51 | 10000 | 0.933581 | 0.090152 | 0.857902 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 52 | 10000 | 0.947797 | 0.083396 | 0.891423 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 53 | 10000 | 0.933142 | 0.093951 | 0.853634 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 54 | 10000 | 0.942381 | 0.086750 | 0.878073 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 55 | 10000 | 0.952987 | 0.076038 | 0.894905 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 56 | 10000 | 0.952476 | 0.075067 | 0.897765 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 57 | 10000 | 0.940627 | 0.087173 | 0.874610 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 58 | 10000 | 0.939827 | 0.083619 | 0.871424 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 59 | 10000 | 0.950803 | 0.074933 | 0.893171 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 60 | 10000 | 0.959097 | 0.071840 | 0.914319 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 61 | 10000 | 0.948491 | 0.078370 | 0.898609 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 62 | 10000 | 0.940963 | 0.087002 | 0.870634 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 63 | 10000 | 0.940329 | 0.089677 | 0.883238 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 64 | 10000 | 0.937800 | 0.083695 | 0.860593 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 65 | 10000 | 0.934909 | 0.090847 | 0.861014 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 66 | 10000 | 0.937945 | 0.090935 | 0.865701 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 67 | 10000 | 0.940623 | 0.084826 | 0.872432 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 68 | 10000 | 0.948619 | 0.078247 | 0.882520 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 69 | 10000 | 0.943309 | 0.080109 | 0.875471 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 70 | 10000 | 0.943186 | 0.085160 | 0.887627 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 71 | 10000 | 0.945247 | 0.079190 | 0.873932 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 72 | 10000 | 0.945864 | 0.082415 | 0.886795 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 73 | 10000 | 0.948827 | 0.080102 | 0.888348 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 74 | 10000 | 0.941883 | 0.086506 | 0.875393 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 75 | 10000 | 0.930064 | 0.093807 | 0.847689 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 76 | 10000 | 0.932818 | 0.089719 | 0.845881 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 77 | 10000 | 0.951859 | 0.075166 | 0.895321 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 78 | 10000 | 0.953076 | 0.075470 | 0.897125 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 79 | 10000 | 0.942424 | 0.083079 | 0.871044 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 80 | 10000 | 0.947801 | 0.079332 | 0.897363 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 81 | 10000 | 0.946822 | 0.085433 | 0.891040 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `A_raw` | raw | — | 82 | 10000 | 0.938596 | 0.087525 | 0.873982 | current |
| `20261031T021845Z` | pilot2-phase2 | uslapseagent | `B_ft3` | fine-tuned | 3 | 43 | 10000 | 0.949185 | 0.080829 | 0.897365 | current |
| `20261031T021845Z` | pilot2-phase2 | uslapseagent | `B_ft3` | fine-tuned | 3 | 44 | 10000 | 0.946038 | 0.085810 | 0.893973 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `B_ft3` | fine-tuned | 3 | 45 | 10000 | 0.949862 | 0.081258 | 0.896203 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `B_ft3` | fine-tuned | 3 | 46 | 10000 | 0.947495 | 0.082411 | 0.899002 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `B_ft3` | fine-tuned | 3 | 47 | 10000 | 0.941593 | 0.084134 | 0.874424 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `B_ft3` | fine-tuned | 3 | 48 | 10000 | 0.936991 | 0.087687 | 0.864195 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `B_ft3` | fine-tuned | 3 | 49 | 10000 | 0.939226 | 0.088240 | 0.867847 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `B_ft3` | fine-tuned | 3 | 50 | 10000 | 0.934811 | 0.093173 | 0.855932 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `B_ft3` | fine-tuned | 3 | 51 | 10000 | 0.938715 | 0.087559 | 0.875284 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `B_ft3` | fine-tuned | 3 | 52 | 10000 | 0.946349 | 0.083153 | 0.887260 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `B_ft3` | fine-tuned | 3 | 53 | 10000 | 0.933329 | 0.093419 | 0.863876 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `B_ft3` | fine-tuned | 3 | 54 | 10000 | 0.941351 | 0.085926 | 0.875194 | current |
| `20261031T021845Z` | pilot2-phase2 | uslapseagent | `B_ft10` | fine-tuned | 10 | 43 | 10000 | 0.951097 | 0.080458 | 0.900992 | current |
| `20261031T021845Z` | pilot2-phase2 | uslapseagent | `B_ft10` | fine-tuned | 10 | 44 | 10000 | 0.946464 | 0.084983 | 0.893806 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `B_ft10` | fine-tuned | 10 | 45 | 10000 | 0.949755 | 0.082033 | 0.897619 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `B_ft10` | fine-tuned | 10 | 46 | 10000 | 0.948572 | 0.081779 | 0.902085 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `B_ft10` | fine-tuned | 10 | 47 | 10000 | 0.942266 | 0.083380 | 0.876675 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `B_ft10` | fine-tuned | 10 | 48 | 10000 | 0.937106 | 0.088269 | 0.866554 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `B_ft10` | fine-tuned | 10 | 49 | 10000 | 0.938179 | 0.088280 | 0.865499 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `B_ft10` | fine-tuned | 10 | 50 | 10000 | 0.937481 | 0.092949 | 0.861474 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `B_ft10` | fine-tuned | 10 | 51 | 10000 | 0.939069 | 0.087465 | 0.876470 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `B_ft10` | fine-tuned | 10 | 52 | 10000 | 0.947805 | 0.082150 | 0.891422 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `B_ft10` | fine-tuned | 10 | 53 | 10000 | 0.933845 | 0.092988 | 0.865667 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `B_ft10` | fine-tuned | 10 | 54 | 10000 | 0.942224 | 0.084699 | 0.872596 | current |
| `20261031T021845Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 43 | 10000 | 0.951833 | 0.078916 | 0.901214 | current |
| `20261031T021845Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 44 | 10000 | 0.946149 | 0.085267 | 0.893132 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 45 | 10000 | 0.950526 | 0.081398 | 0.897318 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 46 | 10000 | 0.950173 | 0.080752 | 0.903794 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 47 | 10000 | 0.944093 | 0.083504 | 0.880537 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 48 | 10000 | 0.939861 | 0.087237 | 0.873609 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 49 | 10000 | 0.937306 | 0.089099 | 0.865655 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 50 | 10000 | 0.937668 | 0.092126 | 0.862169 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 51 | 10000 | 0.941376 | 0.085799 | 0.879768 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 52 | 10000 | 0.949487 | 0.081215 | 0.898251 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 53 | 10000 | 0.933644 | 0.093878 | 0.864470 | current |
| `20261104T122235Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 54 | 10000 | 0.940959 | 0.084467 | 0.867825 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 55 | 10000 | 0.955669 | 0.074857 | 0.901503 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 56 | 10000 | 0.959054 | 0.071869 | 0.912900 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 57 | 10000 | 0.941398 | 0.087360 | 0.880915 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 58 | 10000 | 0.943471 | 0.081143 | 0.878915 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 59 | 10000 | 0.955980 | 0.071821 | 0.902930 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 60 | 10000 | 0.960642 | 0.070268 | 0.918796 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 61 | 10000 | 0.951931 | 0.075653 | 0.901019 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 62 | 10000 | 0.941568 | 0.087217 | 0.875309 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 63 | 10000 | 0.945221 | 0.088799 | 0.897023 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 64 | 10000 | 0.943028 | 0.081580 | 0.875954 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 65 | 10000 | 0.941960 | 0.087157 | 0.883234 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 66 | 10000 | 0.940231 | 0.088786 | 0.876287 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 67 | 10000 | 0.942598 | 0.084574 | 0.881611 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 68 | 10000 | 0.953587 | 0.074395 | 0.893868 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 69 | 10000 | 0.948355 | 0.076513 | 0.889699 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 70 | 10000 | 0.946860 | 0.082489 | 0.895292 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 71 | 10000 | 0.947954 | 0.078598 | 0.885785 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 72 | 10000 | 0.946830 | 0.081446 | 0.895076 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 73 | 10000 | 0.950207 | 0.078311 | 0.897594 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 74 | 10000 | 0.943505 | 0.085013 | 0.884651 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 75 | 10000 | 0.932835 | 0.092459 | 0.859421 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 76 | 10000 | 0.938975 | 0.086550 | 0.874227 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 77 | 10000 | 0.952344 | 0.075503 | 0.898923 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 78 | 10000 | 0.954831 | 0.073173 | 0.898040 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 79 | 10000 | 0.949044 | 0.079637 | 0.889540 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 80 | 10000 | 0.952272 | 0.077147 | 0.907250 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 81 | 10000 | 0.948682 | 0.083947 | 0.892872 | current |
| `20261104T123839Z` | pilot2-phase2 | uslapseagent | `B_ft30` | fine-tuned | 30 | 82 | 10000 | 0.946077 | 0.083108 | 0.886661 | current |
| `coil2000_A_raw_seed42` | r1-pilot | coil2000 | `A_raw` | raw | — | 42 | 2000 | 0.767530 | 0.050767 | 0.187545 | superseded |
| `coil2000_B_in_domain_seed42` | r1-pilot | coil2000 | `B_in_domain` | fine-tuned | — | 42 | 2000 | 0.768962 | 0.050912 | 0.193316 | superseded |
| `coil2000_E_glm_seed42` | r1-pilot | coil2000 | `E_glm` | comparator | — | 42 | 2000 | 0.683029 | 0.055922 | 0.130695 | superseded |
| `coil2000_F_catboost_seed42` | r1-pilot | coil2000 | `F_catboost` | comparator | — | 42 | 2000 | 0.699271 | 0.051626 | 0.175306 | superseded |
| `eudirectlapse_A_raw_seed42` | r1-pilot | eudirectlapse | `A_raw` | raw | — | 42 | 2000 | 0.588090 | 0.113679 | 0.194347 | current |
| `eudirectlapse_B_in_domain_seed42` | r1-pilot | eudirectlapse | `B_in_domain` | fine-tuned | — | 42 | 2000 | 0.597603 | 0.113328 | 0.198178 | current |
| `eudirectlapse_E_glm_seed42` | r1-pilot | eudirectlapse | `E_glm` | comparator | — | 42 | 2000 | 0.574352 | 0.116278 | 0.160071 | current |
| `eudirectlapse_F_catboost_seed42` | r1-pilot | eudirectlapse | `F_catboost` | comparator | — | 42 | 2000 | 0.573768 | 0.115089 | 0.183049 | current |
| `spanish_motor_lapse_A_raw_seed42` | r1-pilot | spanish_motor_lapse | `A_raw` | raw | — | 42 | 2000 | 0.723295 | 0.197776 | 0.570771 | current |
| `spanish_motor_lapse_B_in_domain_seed42` | r1-pilot | spanish_motor_lapse | `B_in_domain` | fine-tuned | — | 42 | 2000 | 0.727187 | 0.196739 | 0.579063 | current |
| `spanish_motor_lapse_E_glm_seed42` | r1-pilot | spanish_motor_lapse | `E_glm` | comparator | — | 42 | 2000 | 0.616563 | 0.222162 | 0.446904 | current |
| `spanish_motor_lapse_F_catboost_seed42` | r1-pilot | spanish_motor_lapse | `F_catboost` | comparator | — | 42 | 2000 | 0.711423 | 0.201455 | 0.541185 | current |
| `uslapseagent_A_raw_seed42` | r1-pilot | uslapseagent | `A_raw` | raw | — | 42 | 2000 | 0.936312 | 0.087321 | 0.834384 | current |
| `uslapseagent_B_in_domain_seed42` | r1-pilot | uslapseagent | `B_in_domain` | fine-tuned | — | 42 | 2000 | 0.935505 | 0.086968 | 0.837523 | current |
| `uslapseagent_E_glm_seed42` | r1-pilot | uslapseagent | `E_glm` | comparator | — | 42 | 2000 | 0.927057 | 0.091007 | 0.817249 | current |
| `uslapseagent_F_catboost_seed42` | r1-pilot | uslapseagent | `F_catboost` | comparator | — | 42 | 2000 | 0.929690 | 0.093386 | 0.829297 | current |
| `20260914T010247Z` | gpu-pilot | uslapseagent | `A_raw` | raw | — | 42 | 10000 | 0.945717 | 0.083267 | 0.885643 | no-capture |
| `20260914T010247Z` | gpu-pilot | uslapseagent | `B_ft3` | fine-tuned | 3 | 42 | 10000 | 0.947907 | 0.082211 | 0.890446 | no-capture |
| `20260914T010247Z` | gpu-pilot | uslapseagent | `B_ft10` | fine-tuned | 10 | 42 | 10000 | 0.948269 | 0.081252 | 0.890664 | no-capture |
| `20260914T010247Z` | gpu-pilot | uslapseagent | `B_ft30` | fine-tuned | 30 | 42 | 10000 | 0.949134 | 0.081390 | 0.892279 | no-capture |
| — | pilot2-breadth-spanish | spanish_motor_lapse | `A_raw` | raw | — | — | 10000 | — | — | — | no-capture |
| — | pilot2-breadth-spanish | spanish_motor_lapse | `B_ft30` | fine-tuned | 30 | — | 10000 | — | — | — | no-capture |

## The rows that are not plainly current

4 withdrawn and 6 without a Capture. Nothing was dropped: a
row that is not evidence a claim may rest on is still a record of what ran.

| run id | dataset | arm | seed | train rows | status | why |
| --- | --- | --- | --- | --- | --- | --- |
| `coil2000_A_raw_seed42` | coil2000 | `A_raw` | 42 | 2000 | superseded | D21 (amended by D22): coil2000 stopped on resolution — median half-width 0.0149 at the largest usable split against a 0.006 floor; D22 withdraws D21's seed-cost inference and leaves the stop resting on the P1 gate alone |
| `coil2000_B_in_domain_seed42` | coil2000 | `B_in_domain` | 42 | 2000 | superseded | D21 (amended by D22): coil2000 stopped on resolution — median half-width 0.0149 at the largest usable split against a 0.006 floor; D22 withdraws D21's seed-cost inference and leaves the stop resting on the P1 gate alone |
| `coil2000_E_glm_seed42` | coil2000 | `E_glm` | 42 | 2000 | superseded | D21 (amended by D22): coil2000 stopped on resolution — median half-width 0.0149 at the largest usable split against a 0.006 floor; D22 withdraws D21's seed-cost inference and leaves the stop resting on the P1 gate alone |
| `coil2000_F_catboost_seed42` | coil2000 | `F_catboost` | 42 | 2000 | superseded | D21 (amended by D22): coil2000 stopped on resolution — median half-width 0.0149 at the largest usable split against a 0.006 floor; D22 withdraws D21's seed-cost inference and leaves the stop resting on the P1 gate alone |
| `20260914T010247Z` | uslapseagent | `A_raw` | 42 | 10000 | no-capture | launch record with no capture.json — cite by description (outputs/gpu-pilot/runs/20260914T010247Z/uslapseagent/A_raw/meta.json), not a Capture |
| `20260914T010247Z` | uslapseagent | `B_ft3` | 42 | 10000 | no-capture | launch record with no capture.json — cite by description (outputs/gpu-pilot/runs/20260914T010247Z/uslapseagent/B_ft3/meta.json), not a Capture |
| `20260914T010247Z` | uslapseagent | `B_ft10` | 42 | 10000 | no-capture | launch record with no capture.json — cite by description (outputs/gpu-pilot/runs/20260914T010247Z/uslapseagent/B_ft10/meta.json), not a Capture |
| `20260914T010247Z` | uslapseagent | `B_ft30` | 42 | 10000 | no-capture | launch record with no capture.json — cite by description (outputs/gpu-pilot/runs/20260914T010247Z/uslapseagent/B_ft30/meta.json), not a Capture |
| — | spanish_motor_lapse | `A_raw` | — | 10000 | no-capture | breadth replication, seeds 341-356: no capture and no committed per-seed record — cite via finetuning_breadth_spanish_result.md, not a Capture |
| — | spanish_motor_lapse | `B_ft30` | — | 10000 | no-capture | breadth replication, seeds 341-356: no capture and no committed per-seed record — cite via finetuning_breadth_spanish_result.md, not a Capture |

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

## Summary — dataset × arm × training rows

`n`, mean and min–max across seeds (and instances, where a dataset has more than one Run).
**Descriptive only: no interval and no verdict**, so the ledger cannot contradict an analysis
that owns one. Current rows only — a withdrawn row would put a stopped cell inside a mean, and
a `no-capture` row would put a launch with no Capture inside a mean over captured Runs. The
2,000-row and 10,000-row cells are separate lines for the same reason `train_rows` is part of
the key.

| dataset | arm | train rows | n | ROC AUC mean (min–max) | Brier mean (min–max) | PR-AUC mean (min–max) |
| --- | --- | --- | --- | --- | --- | --- |
| eudirectlapse | `A_raw` | 2,000 | 1 | 0.5881 | 0.1137 | 0.1943 |
| eudirectlapse | `A_raw` | 10,000 | 238 | 0.6268 (0.5452–0.6984) | 0.1095 (0.1068–0.1128) | 0.2037 (0.1500–0.2745) |
| eudirectlapse | `B_ft30` | 10,000 | 238 | 0.6275 (0.5440–0.6914) | 0.1095 (0.1068–0.1132) | 0.2010 (0.1516–0.2684) |
| eudirectlapse | `B_in_domain` | 2,000 | 1 | 0.5976 | 0.1133 | 0.1982 |
| eudirectlapse | `E_glm` | 2,000 | 1 | 0.5744 | 0.1163 | 0.1601 |
| eudirectlapse | `F_catboost` | 2,000 | 1 | 0.5738 | 0.1151 | 0.1830 |
| spanish_motor_lapse | `A_raw` | 2,000 | 1 | 0.7233 | 0.1978 | 0.5708 |
| spanish_motor_lapse | `B_in_domain` | 2,000 | 1 | 0.7272 | 0.1967 | 0.5791 |
| spanish_motor_lapse | `E_glm` | 2,000 | 1 | 0.6166 | 0.2222 | 0.4469 |
| spanish_motor_lapse | `F_catboost` | 2,000 | 1 | 0.7114 | 0.2015 | 0.5412 |
| uslapseagent | `A_raw` | 2,000 | 1 | 0.9363 | 0.0873 | 0.8344 |
| uslapseagent | `A_raw` | 10,000 | 40 | 0.9431 (0.9275–0.9591) | 0.0841 (0.0718–0.0975) | 0.8781 (0.8405–0.9143) |
| uslapseagent | `B_ft3` | 10,000 | 12 | 0.9421 (0.9333–0.9499) | 0.0861 (0.0808–0.0934) | 0.8792 (0.8559–0.8990) |
| uslapseagent | `B_ft10` | 10,000 | 12 | 0.9428 (0.9338–0.9511) | 0.0858 (0.0805–0.0930) | 0.8809 (0.8615–0.9021) |
| uslapseagent | `B_ft30` | 10,000 | 40 | 0.9465 (0.9328–0.9606) | 0.0821 (0.0703–0.0939) | 0.8881 (0.8594–0.9188) |
| uslapseagent | `B_in_domain` | 2,000 | 1 | 0.9355 | 0.0870 | 0.8375 |
| uslapseagent | `E_glm` | 2,000 | 1 | 0.9271 | 0.0910 | 0.8172 |
| uslapseagent | `F_catboost` | 2,000 | 1 | 0.9297 | 0.0934 | 0.8293 |

## How to read a row

**`arm_kind` is derived, never recorded.** `A_raw` is the raw control (`raw`); `B_ft3`,
`B_ft10`, `B_ft30` and the pilot's `B_in_domain` are fine-tuned (`fine-tuned`); `E_glm` and
`F_catboost` are comparator Methods (`comparator`), not a fourth and fifth Arm of one kind.

**Epochs come from the record that trained, not from the config that launched.** The source is
each record's `effective_config.kwargs.epochs`. `config.epochs` — and every Run manifest —
reads `3` on every arm, including the 30-epoch one, so a generator reading either would call a
30-epoch arm a 3-epoch arm. The generator asserts the recorded count equals the number in the
`B_ftN` label and fails on a disagreement rather than smoothing it. The 2,000-row pilot records
no arm-level epoch count at all (`max_finetune_steps` is a different parameter, carried by the
comparator rows too), so its `epochs` column is blank, not `3`.

**The model version is printed as recorded.** `model_version` reads `auto` wherever a record names one —
a recorded value that names no version, so this ledger never prints `v3`. The checkpoint is
`tabpfn-v3-classifier-v3_default.ckpt` and the weights sha256 `d0d865d5...8f3988` on every row that records one.

**Three metrics, and no more.** ROC AUC, Brier and PR-AUC are recorded on every capture record;
`log_loss` and `ece` are recorded too and are deliberately outside this ledger (the map's
out-of-scope list, #663), not missing from it. A blank is "the source did not record it": no
cell here is backfilled from prose.

**`source` is the pointer to the bytes.** For a capture row it is the per-seed `meta.json`,
because `capture.json` holds hashes and the record holds the numbers; the Run id is in the
`run_id` column, taken from the directory. A per-seed record's own `run_id`
(`<dataset>_<arm>_seed<N>`) is **not** the Run id and is not used as one.

**A `no-capture` row cannot be cited as a Capture.** The Spanish breadth cell's per-seed records
were never committed, so its rows carry blank metrics and no seed at all — one row per arm,
because a per-seed row would be an invention — and a pointer to
[`finetuning_breadth_spanish_result.md`](finetuning_breadth_spanish_result.md) — cite the result,
not a Capture. The `gpu-pilot` rows do carry metrics, from committed launch records that are
not Captures; they are cited by description, the way `REPORT_REGISTRY.md` already handles them.

## Regenerating

```
python scripts/analyses/finetuning_runs_ledger.py
```

Two runs on the same tree write byte-identical files: rows are sorted on a total key and every
float is formatted to fixed precision (six decimal places per row, four in the summary, which is
computed from the CSV and therefore inherits that rounding). The generator writes both files or
neither — a disagreement in the evidence exits before either is written.

