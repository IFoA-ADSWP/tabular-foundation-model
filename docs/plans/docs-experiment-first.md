# Plan — group the documentation by experiment

**Status:** Proposed — awaiting sign-off.
**Origin:** the structure audit of 2026-11-13, and the report that "everything sits in one folder".
**Design:** a reader arrives asking *what happened in the fair test*, not *which document is current*. The
first axis becomes the experiment; status stays a declared marker and a second tree, not the primary sort.

## What is wrong

The three report trees sort by **status**, and status is not a topic:

| Tree | Contents |
| --- | --- |
| `docs/current/` | 18 files, 16 prefixed `FINETUNING_`, including two **regressor** pre-registrations and a diagnostics design |
| `docs/reference/` | 8 files — design alternatives, probe plans, a meeting note |
| `docs/archive/` | 21 files — every superseded document, whatever it was about |
| `docs/analyses/` | 32 files — specs, result notes, registries, explainers, one master report |

One experiment therefore spans four trees. The frequency/severity fair test is
`../experiments/fair-test-freq-sev/freq_sev_quantiles.md` + `../experiments/fair-test-freq-sev/REGRESSOR_FINETUNING_PREREGISTRATION_FREQ_SEV_2026-11.md`
+ four `results/` timestamps + a plan — five locations, and nothing but a name prefix relates them.

## The structure

```
docs/
  README.md  RUNNING.md  EVIDENCE_MAP.md  MODEL_VERSIONS.md
  DOCUMENT_AUTHORITY.md  REPORT_REGISTRY.md  DEVELOPMENT_ENVIRONMENT.md  issue-tracker.md
  experiments/
    frontier-benchmark/   r1-pilot/   probe/   pilot2-phase2/   fair-test-freq-sev/
    diagnostics/   tabarena/
  shared/                 # registries and explainers that belong to no campaign
  archive/<campaign>/     # superseded documents, still grouped by the campaign they served
  plans/  adr/  papers/  sessions/  status/
```

`docs/experiments/<campaign>/README.md` is the campaign's front door: the question it asked, its documents in
reading order, and the `results/` run ids it owns. That file is the deliverable — it is what answers "which
files belong to this experiment".

## Why `archive/` keeps its top-level name

`scripts/check_doc_links.py` skips `plans/` and `archive/` as **citation tiers**: a historical document may
cite a path that no longer exists, because the trail is the point. Moving archived documents into
`experiments/` would make their links enforceable and the gate would go red on purpose-built history.

So campaigns split by status: `experiments/<campaign>/` is live and checked; `archive/<campaign>/` keeps the
exemption. The cost is that a campaign still appears twice — but both times under its own name, which is the
part that was missing.

## The campaigns

Assignments below are validated against the tree: **77 documents, all assigned, none invented.**

| Campaign | Live | Archived | What it is |
| --- | ---: | ---: | --- |
| `frontier-benchmark` | 8 | 8 | The v3 frontier suite, the master report and its addenda |
| `pilot2-phase2` | 25 | 9 | The fine-tuning programme: design, pre-registrations, replication, breadth cells, decision log, outcome |
| `fair-test-freq-sev` | 7 | 0 | The 2026-11 frequency/severity fair test |
| `tabarena` | 4 | 0 | The external harness and what was learned from it |
| `probe` | 3 | 0 | The 2026-09 budget probe |
| `r1-pilot` | 1 | 2 | The first pilot, 2026-09 |
| `diagnostics` | 2 | 0 | D1–D5 design and D5's explanation |
| `reserving` | 0 | 1 | Reserving with foundational models |
| `shared` | 6 | 0 | Metric registry, explainers, catalog, levers assessment |

## What the migration touches

1. **77 `git mv`s**, per the mapping recorded in `.git/move-map.json` during the audit.
2. **Relative links** in every document that points at a moved one. `doclinks` resolves against the document's
   own directory, then `docs/`, then the root, so a link that was `../REPORT_REGISTRY.md` becomes
   `../../REPORT_REGISTRY.md` — the migration rewrites them and the check proves it.
3. **`docs/REPORT_REGISTRY.md`** — its `report_path` column names 30+ of these files.
4. **`scripts/check_doc_status.py`** — the three hard-coded tier directories become a recursive scan of
   `docs/experiments/` and `docs/shared/`, plus `docs/archive/` (which gains one level, so it recurses too,
   skipping the legacy `papers/`, `sessions/` and `status/` subdirectories that predate the status rule).
5. **`docs/README.md`** — the tier table, the role table's paths, and the "not tiered" paragraph.
6. **Nine campaign READMEs** — new, and the point of the change.

## Verification

```sh
./scripts/check.sh                 # all eight
python3 scripts/check_doc_links.py --dir docs --root . --include-citations
```

Plus the count that matters: every one of the 77 documents is reachable from its campaign README, and
`docs/EXPERIMENTS.md` lists the nine campaigns with their run ids.

## What this does not do

- Does not move `docs/plans/` (70 files, one per task) or `docs/adr/`.
- Does not move `results/`, `outputs/` or `scripts/`.
- Does not change any document's content beyond links, the registry paths and its status marker staying put.
- Does not delete anything.
