# Fine-tuning runs inventory — what the committed evidence records

> **Status:** current — field inventory, 2026-11-20. A reference for building the ledger (#665), not a
> new result and not a verdict. It re-derives nothing and adds no number of its own.

**Question.** Across the 23 `pilot2-phase2` Run directories and the early pilot's aggregate parquet,
which fields are actually recorded, which repeat, which were stopped, and which are missing? The
answer fixes what a ledger generator may read and what it must render as blank.

**Vocabulary** follows [`GLOSSARY.md`](../../../GLOSSARY.md): a **Run** is one execution producing one
output directory with its manifest; a **Capture** is that run's persisted evidence with hashes that
prove the arrays; an **Arm** is one training configuration; a baseline is a **Method**, never an arm;
**Model version** is recorded, never inferred; **Provenance** is dataset, seed, fold construction,
model version and git sha.

## What is in scope

| Source | What it is | Count |
| --- | --- | --- |
| `results/<id>/` on `main` | One **Run** directory each, with a `capture.json` and per-arm × seed records | 23 |
| `outputs/finetune/pilot/pilot_metrics.parquet` | An aggregate table of the 2,000-row pilot; **not** a Run and has no Capture | 16 rows |
| `outputs/gpu-pilot/runs/<one directory>/` | Records for a 10,000-row `uslapseagent` Run, but **no `capture.json`** — so not a Capture. Its records are schema 2 and carry no `provenance` block | 4 arm records |

The third row is excluded from the 23 by the directory rule, and it cannot satisfy the citation gate
(a run id in `docs/` needs a Capture under `results/`). It is cited here by description, the way
`REPORT_REGISTRY.md` already handles the Spanish breadth records.

## 1. Per-run field table

Every one of the 23 Runs carries `capture.json` schema 1 and records schema 4; 580 arm × seed records
in total, every one `status: success`. `—` under epochs is the raw method: no training epochs apply.

| Run (`results/<id>/`) | Dataset | Arms — recorded epochs | Seeds (n) | Train / test | ROC AUC | Brier | PR-AUC | Also recorded | Instance id |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `20261031T021845Z` | `uslapseagent` | `A_raw` —; `B_ft3` 3; `B_ft10` 10; `B_ft30` 30 | 43–44 (2) | 10,000 / 1,000 | ✓ | ✓ | ✓ | log_loss, ece | — |
| `20261104T122235Z` | `uslapseagent` | `A_raw` —; `B_ft3` 3; `B_ft10` 10; `B_ft30` 30 | 45–54 (10) | 10,000 / 1,000 | ✓ | ✓ | ✓ | log_loss, ece | — |
| `20261104T123839Z` | `uslapseagent` | `A_raw` —; `B_ft30` 30 | 55–82 (28) | 10,000 / 1,000 | ✓ | ✓ | ✓ | log_loss, ece | — |
| `20261104T234013Z` | `eudirectlapse` | `A_raw` —; `B_ft30` 30 | 93–104 (12) | 10,000 / 1,000 | ✓ | ✓ | ✓ | log_loss, ece | — |
| `20261104T234127Z` | `eudirectlapse` | `A_raw` —; `B_ft30` 30 | 117–128 (12) | 10,000 / 1,000 | ✓ | ✓ | ✓ | log_loss, ece | — |
| `20261104T234132Z` | `eudirectlapse` | `A_raw` —; `B_ft30` 30 | 129–140 (12) | 10,000 / 1,000 | ✓ | ✓ | ✓ | log_loss, ece | — |
| `20261105T001837Z` | `eudirectlapse` | `A_raw` —; `B_ft30` 30 | 105–116 (12) | 10,000 / 1,000 | ✓ | ✓ | ✓ | log_loss, ece | — |
| `20261105T005435Z` | `eudirectlapse` | `A_raw` —; `B_ft30` 30 | 153–164 (12) | 10,000 / 1,000 | ✓ | ✓ | ✓ | log_loss, ece | — |
| `20261105T005447Z` | `eudirectlapse` | `A_raw` —; `B_ft30` 30 | 165–176 (12) | 10,000 / 1,000 | ✓ | ✓ | ✓ | log_loss, ece | — |
| `20261105T012925Z` | `eudirectlapse` | `A_raw` —; `B_ft30` 30 | 189–200 (12) | 10,000 / 1,000 | ✓ | ✓ | ✓ | log_loss, ece | — |
| `20261105T013749Z` | `eudirectlapse` | `A_raw` —; `B_ft30` 30 | 201–212 (12) | 10,000 / 1,000 | ✓ | ✓ | ✓ | log_loss, ece | — |
| `20261105T013755Z` | `eudirectlapse` | `A_raw` —; `B_ft30` 30 | 213–224 (12) | 10,000 / 1,000 | ✓ | ✓ | ✓ | log_loss, ece | — |
| `20261105T100533Z` | `eudirectlapse` | `A_raw` —; `B_ft30` 30 | 141–152 (12) | 10,000 / 1,000 | ✓ | ✓ | ✓ | log_loss, ece | — |
| `20261105T103841Z` | `eudirectlapse` | `A_raw` —; `B_ft30` 30 | 249–260 (12) | 10,000 / 1,000 | ✓ | ✓ | ✓ | log_loss, ece | — |
| `20261105T103853Z` | `eudirectlapse` | `A_raw` —; `B_ft30` 30 | 273–284 (12) | 10,000 / 1,000 | ✓ | ✓ | ✓ | log_loss, ece | — |
| `20261105T103937Z` | `eudirectlapse` | `A_raw` —; `B_ft30` 30 | 261–272 (12) | 10,000 / 1,000 | ✓ | ✓ | ✓ | log_loss, ece | — |
| `20261105T111110Z` | `eudirectlapse` | `A_raw` —; `B_ft30` 30 | 297–308 (12) | 10,000 / 1,000 | ✓ | ✓ | ✓ | log_loss, ece | — |
| `20261105T114320Z` | `eudirectlapse` | `A_raw` —; `B_ft30` 30 | 309–320 (12) | 10,000 / 1,000 | ✓ | ✓ | ✓ | log_loss, ece | — |
| `20261105T114647Z` | `eudirectlapse` | `A_raw` —; `B_ft30` 30 | 321–330 (10) | 10,000 / 1,000 | ✓ | ✓ | ✓ | log_loss, ece | — |
| `20261105T124200Z` | `eudirectlapse` | `A_raw` —; `B_ft30` 30 | 177–188 (12) | 10,000 / 1,000 | ✓ | ✓ | ✓ | log_loss, ece | — |
| `20261105T124205Z` | `eudirectlapse` | `A_raw` —; `B_ft30` 30 | 225–236 (12) | 10,000 / 1,000 | ✓ | ✓ | ✓ | log_loss, ece | — |
| `20261105T140236Z` | `eudirectlapse` | `A_raw` —; `B_ft30` 30 | 237–248 (12) | 10,000 / 1,000 | ✓ | ✓ | ✓ | log_loss, ece | — |
| `20261105T140242Z` | `eudirectlapse` | `A_raw` —; `B_ft30` 30 | 285–296 (12) | 10,000 / 1,000 | ✓ | ✓ | ✓ | log_loss, ece | — |

**Where each field comes from, and the one that lies.**

- **Epochs.** The only correct source is the Arm × seed record's `effective_config.kwargs.epochs` —
  `null` for `A_raw`, and 3 / 10 / 30 for the fine-tuned arms. The sibling `config.epochs` is the
  job's *source* config and reads `3` on every record, including the 30-epoch arm. The Run's
  `manifest_*.json` also carries `"epochs": 3` on the `B_ft10` and `B_ft30` launches. A generator that
  reads either of those two fields will label a 30-epoch arm as 3 epochs.
- **Label agreement.** 580 / 580 records in the 23 Runs agree: the recorded epoch count equals the
  number in the `ftN` label, and `row_epochs == epochs × train_rows` holds on every fine-tuned record
  (`row_epochs` is `null` for `A_raw`). There is no drift to smooth over on the committed evidence.
- **Seeds.** Written per capture entry and per record; `uslapseagent` uses 43–82 and `eudirectlapse`
  93–330, contiguous per Run, disjoint between Runs, with `A_raw` and `B_ft30` sharing every seed.
- **Training and test rows.** `capture.json` records only the test-row count, as `rows` (1,000).
  Training rows (10,000) exist only in the records and in the Run manifest.
- **Metrics.** The Capture holds hashes, not numbers: `predictions_sha256` and `truth_sha256` per
  entry. `roc_auc`, `brier`, `pr_auc`, `log_loss` and `ece` are all present on all 580 records, along
  with a boolean `model_saved`. No other metric is recorded. `log_loss` and `ece` are the only ones
  outside the ledger's three, and both are present everywhere rather than occasionally.
- **Instance / launch id.** Not recorded anywhere in the tree. A Run manifest carries a per-launch
  `run_id` distinct from the directory id, plus `pid`, `host.hostname`, `host.gpu_name` and
  `container.run_stamp`; `container.machine_id` and `container.host_id` are `null` on every launch.
  The decision log cites a launch id (`20261031T021925Z-c24870`) and an instance (`58479781`) that no
  committed record contains. Per the glossary a **Launch** owns a launch id and contains zero or more
  Runs; that identity was never persisted here.
- **Model version.** Every one of the 580 `pilot2-phase2` records reads `model.version: "auto"` — a
  recorded value that names no version. The checkpoint (`tabpfn-v3-classifier-v3_default.ckpt`) and a
  single weights sha256 (`d0d865d5…f3988`) are identical across all 580 records and the gpu-pilot run,
  whose schema-2 records carry no version field at all. The ledger must print `auto` plus the
  checkpoint and sha, not infer "v3"; the replication result already records it as unpinned.
- **Provenance.** `provenance.dataset.sha256`, `split.sha256`, `split_fingerprint` and
  `code.git_sha` are present on every one of the 580 records. There are five distinct git shas across
  the 23 Runs, all clean, so a single global pin is not available. The gpu-pilot run has no
  `provenance` block, so it yields dataset and split fingerprints but no git sha.

**The 2,000-row pilot aggregate, for contrast.** 16 rows, one seed (42), 2,000 train / 1,000 test, four
datasets × four labels (`A_raw`, `E_glm`, `F_catboost`, `B_in_domain`), 17 columns spanning `run_id`
through `pr_auc`. It records `roc_auc`, `brier`, `pr_auc` and nothing else metric-like; `B_in_domain` is
the fine-tuned **Arm** and `E_glm` / `F_catboost` are comparator **Methods**, not arms. Its single
shared `config` reads `max_finetune_steps: 3` for all 16 rows — a different parameter name from
`epochs`, and one that the comparator rows also carry, so it cannot be read as an arm-level epoch count.

## 2. Replacement pairs

**Within the committed evidence there are none.** No `(dataset, arm, seed)` cell occurs twice across
the 23 Runs, and no cell occurs twice inside a Run. Every seed belongs to exactly one Run.

That is not because nothing was re-run. The breadth result records the opposite:

> Three seed ranges were launched more than once while #426 was live; only one directory per range is
> committed here, so the table names one and the pool stays seed-disjoint.
> — [`finetuning_breadth_eudirectlapse_result.md`](finetuning_breadth_eudirectlapse_result.md)

So three duplicate launches (36 seeds measured twice, per the same document) were **discarded before
commit**, and their run ids are not in the tree — nor in `results/` history, since no Run directory was
ever deleted from git. The superseded ids cannot be recovered, and there is no pair to name.

**What to build instead.** Mechanical replacement detection will return zero rows on this evidence and
should assert that (seed-disjointness) rather than silently succeed. Supersession in the ledger is
therefore a curated list from the decision log, not a diff of captures.

**Near-misses that are not replacements** — same dataset and arm, different seeds, deliberately
disjoint (the design keeps probe seeds out of the replication pool):

| Dataset | Run | Role | Seeds |
| --- | --- | --- | --- |
| `uslapseagent` | `20261031T021845Z` | anchor first pass, 4 arms | 43–44 |
| `uslapseagent` | `20261104T122235Z` | ladder probe, 4 arms | 45–54 |
| `uslapseagent` | `20261104T123839Z` | replication, `A_raw` + `B_ft30` | 55–82 |
| `eudirectlapse` | 20 Runs, `20261104T234013Z` first | replication batches, `A_raw` + `B_ft30` | 93–330 |

**One collision that looks like a pair and is not.** `uslapseagent` seed 42 is recorded twice at
different row budgets: the pilot aggregate's `B_in_domain` at 2,000 train rows, and the gpu-pilot run's
`B_ft3` / `B_ft10` / `B_ft30` at 10,000. The row budget differs, so these are different cells. A
supersession key of `(dataset, arm, seed)` would collapse them and mark real evidence superseded; the
ledger's key must include `train_rows`.

## 3. Withdrawn and stopped arms

There are **no arm withdrawals inside the 23 Runs** — every recorded arm is current. The stops are at
dataset and programme level, and they touch the pilot aggregate rather than `results/`:

| What | Where it appears | Decision | Status in the tree |
| --- | --- | --- | --- |
| `coil2000`, all four labels (`A_raw`, `E_glm`, `F_catboost`, `B_in_domain`) | Pilot aggregate only — 4 rows; **no `results/` Run** | D21, confirmed by D22 | Rows exist; dataset closed |
| `B_ft3` / `B_ft10` on `eudirectlapse` | Nowhere — never run at 10,000 rows | D22 recorded limitation: not funded | Absent, not withdrawn |
| The whole fine-tuning line | Historical | D11 | Reversed by D14 / D15; must not be applied |

> DECISION: **breadth closes — `coil2000` stopped on resolution (2026-11-06)** — median half-width
> 0.0149 at the largest usable split against a 0.006 floor and δ = 0.002; 586 positives, so no budget
> resolves it.
> — [`FINETUNING_DECISION_LOG.md`](FINETUNING_DECISION_LOG.md), D21

> DECISION: **Phase 2 closes (2026-11-07)** — … and D21's seed-cost inference is withdrawn as a
> resolution-for-variance substitution, leaving the `coil2000` stop resting on the P1 gate alone.
> — same log, D22

D22 withdraws the *reasoning* in D21, not the stop: the `coil2000` rows stay withdrawn on resolution
grounds. The superseded row for the four pilot `coil2000` rows should therefore cite D21, with D22 as
the amendment — not D22 alone.

The line stop is a trap for a reader who applies decisions in order:

> DECISION: **stop the fine-tuning line (2026-10-31)** — the anchor did not replicate under D9.
> — same log, D11

D11 is historical: D14 reopened once, D15's replication passed and published, D16 reopened breadth, and
D22 closed Phase 2. A ledger that marks every `B_ft*` row withdrawn on D11 would contradict the
campaign's own outcome.

## 4. Overlap guidance — which source the ledger reads

**The captures and the pilot aggregate never cover the same cell.** They differ in every dimension that
identifies one — dataset, arm, seed, training rows — and in the epoch field as well:

| | `results/` captures (23 Runs) | Pilot aggregate parquet | gpu-pilot run (no Capture) |
| --- | --- | --- | --- |
| Dataset | `uslapseagent`, `eudirectlapse` | four, incl. `coil2000`, `spanish_motor_lapse` | `uslapseagent` |
| Arm labels | `A_raw`, `B_ft3`, `B_ft10`, `B_ft30` | `A_raw`, `B_in_domain`, `E_glm`, `F_catboost` | `A_raw`, `B_ft3`, `B_ft10`, `B_ft30` |
| Seed | 43–330 | 42 | 42 |
| Train rows | 10,000 | 2,000 | 10,000 |
| Epoch field | `effective_config.kwargs.epochs` | none (`max_finetune_steps`) | `effective_config.kwargs.epochs` |

Therefore:

1. **Read the Run records for everything the 23 Runs own.** The `capture.json` proves the arrays; the
   Arm × seed `meta.json` holds the numbers and the provenance. Do not read the per-Run
   `pilot_metrics.parquet` copy — it has the same name and a *different* schema from the pilot
   aggregate (34 columns vs 17), which is a live filename collision.
2. **Read the pilot aggregate only for the 2,000-row pilot cells**, which no Run directory covers. Its
   rows are the only surviving record of that pilot.
3. **Do not prefer one over the other where they look similar.** No cell is duplicated, so there is no
   conflict to resolve. The gpu-pilot README's statement that the aggregate is stale and superseded by
   `runs/` is true of the *artifact*; at cell level it applies only to `uslapseagent` seed 42 at 10,000
   rows, which the aggregate does not contain.
4. **Do not join the two sources on `run_id`.** The aggregate's ids are synthetic
   (`<dataset>_<arm>_seed42`); Run ids are directory names. They are different namespaces and only
   collide by accident.

## 5. Coverage gaps the ledger must render blank

| Field | Missing in | What the ledger may write |
| --- | --- | --- |
| Epoch count | Pilot aggregate (only `max_finetune_steps`, shared with comparator rows) | blank, not 3 |
| `arm_kind` | Everywhere; never recorded | derived from the label, and declared as derived |
| Fold / `n_folds` | Pilot aggregate (no such column); all 23 Runs are `foldNone` | blank, not `0` |
| Training rows | `capture.json` (holds test rows only) | read from the record; never from the capture |
| `log_loss`, `ece` | Pilot aggregate | blank |
| Dataset sha256, split sha256 | Pilot aggregate (no provenance block) | blank |
| git sha, code image | Pilot aggregate, and the gpu-pilot Run (schema-2 records, no `provenance`) | blank |
| Weights sha256 | Pilot aggregate | blank |
| Predictions hash | Pilot aggregate | blank |
| Instance / launch id | Everywhere | blank; the column can exist but must never be filled by inference |
| Model version as a pin | Everywhere (`auto`) | `auto` plus checkpoint and weights sha |
| `eudirectlapse` three-rung probe, seeds 83–92 | Everywhere — cited by D17/D22, no committed records | absent; do not reconstruct from the prose |
| `coil2000` at any budget | `results/` — no Run exists at any budget | absent from the ledger's Run rows; the 2,000-row aggregate rows are the only record |

**Scope guards for a globbing generator.** Six further fine-tuning Run directories exist under
`results/` for `freMTPL2freq`, `freMTPL2sev`, `spanish_motor_freq` and `spanish_motor_severity`
(2026-11-12 onward, the fair-test campaign). They carry the same `A_raw` / `B_ft30` labels and are
outside this ledger. Unrelated captures from the same period exist with a `null` arm and a `null`
dataset, so a generator that assumes every capture names one will fail. Select by campaign and dataset,
not by "has an `ft` arm".

Two path traps, both already recorded elsewhere: `capture.json`'s `record` value omits the dataset
level — it names the arm and seed directory but not the dataset directory above it — while the record
actually sits under `results/<id>/<dataset>/<arm>/<seed>_foldNone/`; and the per-seed record's own
`run_id` (`<dataset>_<arm>_seed<N>`) is not the Run id — take the Run id from the directory and the
Capture.

## What this means for the generator

1. Epochs come from the record's `effective_config.kwargs.epochs`; the manifest and `config.epochs`
   both report 3 for every arm and must not be read.
2. The supersession column cannot be computed from capture diffs — the evidence is seed-disjoint by
   construction. Assert disjointness; curate withdrawals from D21/D22.
3. The ledger key is `(dataset, arm, seed, train_rows)`. Without `train_rows`, the 2,000-row pilot's
   `uslapseagent` seed-42 fine-tune collides with the 10,000-row run.
4. Epoch is blank for every pilot aggregate row, and `B_in_domain` stays its own label — it is not
   `B_ft3` under another name in the record, whatever the training configuration.
5. `E_glm` and `F_catboost` are comparator **Methods**, not arms; `A_raw` is the raw control and
   `B_ft*` the fine-tuned arms. The `arm_kind` column should make that distinction rather than
   presenting four arms of one kind.
