# Experiments — what this repository has actually run

One folder per line of work. Each holds the design, the pre-registration, the result notes and the decision
record for **one** campaign, so that "which files belong to this experiment" has an answer that is a
directory listing rather than a search.

Superseded documents live in `docs/archive/<campaign>/` — same grouping, different status — and the status
each document declares in its first lines says what it is worth now.

| Campaign | Documents | Runs | What it is |
| --- | --- | --- | --- |
| [`diagnostics`](experiments/diagnostics/README.md) | 2 live, 0 archived | 0 | D1–D5: the diagnostics design and D5's explanation. |
| [`fair-test-freq-sev`](experiments/fair-test-freq-sev/README.md) | 9 live, 0 archived | 7 | The 2026-11 frequency/severity fair test — four pre-registered targets, policy-grouped folds. |
| [`frontier-benchmark`](experiments/frontier-benchmark/README.md) | 8 live, 8 archived | 4 | The 2026-07→08 frontier suite: the benchmark that produced master report §14, its re-scores, and the v3.5 re-test. |
| [`lapse-students`](experiments/lapse-students/README.md) | 0 live, 0 archived | 1 | Measuring the lapse GBDTs on the teacher's own folds instead of estimating them (#377). |
| [`pilot2-phase2`](experiments/pilot2-phase2/README.md) | 26 live, 9 archived | 23 | The fine-tuning programme: design, pre-registrations, the replication and breadth cells, the decision log and the Phase 2 outcome. |
| [`probe`](experiments/probe/README.md) | 3 live, 0 archived | 0 | The 2026-09 budget probe: whether the paid path could measure anything at the smaller budget. |
| [`r1-pilot`](experiments/r1-pilot/README.md) | 1 live, 2 archived | 0 | The first fine-tuning pilot, 2026-09. |
| [`tabarena`](experiments/tabarena/README.md) | 4 live, 0 archived | 0 | The external TabArena harness: what it is, what was learned from it, and what runs without a GPU. |

## Shared

`docs/shared/` holds what belongs to no single campaign: the metric registry, the explainers, the model
catalog and the levers assessment. It is scanned for status like the campaigns are.

## Where the evidence is

Not every campaign's evidence is under `results/`. The benchmark line writes committed CSVs beside its
runner in `scripts/eval/`; the paid runs land in `outputs/gpu-pilot/`; the diagnostics export tables to
`docs/analyses/data/`. Each campaign README names the run ids it owns where it has them, and [`results/INDEX.md`](../results/INDEX.md) maps every committed run to its campaign. See
[EVIDENCE_MAP.md](EVIDENCE_MAP.md) for what each tree claims.

