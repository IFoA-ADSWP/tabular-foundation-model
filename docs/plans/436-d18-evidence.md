# Plan — commit the evidence D18 cites

**Issue:** #436 (a child of the paid-run hardening tracking issue #428). **Branch:** stacked on
`docs/414-breadth-result` (#435), which carries the result this evidence belongs to.

## What and why

`docs/analyses/finetuning_breadth_eudirectlapse_result.md` reports `equivalence` and points a reader at
`outputs/gpu-pilot/runs/`, which is runtime evidence and is not committed. The twenty run directories
the verdict used are therefore absent from a fresh clone, so the published finding cannot be checked
from the tree — the defect #407 names for the diagnostics, attached to a result.

The repo already has the pattern for committed arrays: the anchor's `results/20261031T021845Z/` carries
one `meta.json`, `predictions.npy` and `ground_truth.npy` per arm × seed plus a `capture.json`, and the
result document cites the directory. (The later replication, `results/20261104T123839Z/`, committed its
records without the arrays — the defect this change does not repeat.) This change does the same for
D18.

## What lands

- **Twenty run directories under `results/<run_id>/`**, one per paid launch, with the whole
  `eudirectlapse/` tree (`meta.json`, `predictions.npy`, `ground_truth.npy` per arm × seed), the
  launch manifests and the two parquet records, matching the anchor's shape.
- **One `capture.json` per run**, written by `scripts/analyses/make_capture.py` — not hand-written, so
  `verdict.py` and `rescore.py` verify the arrays instead of trusting the prose.
- **The result document cites the run ids** instead of describing an uncommitted path, and gains a
  Reproduction section with the pooled `verdict.py` invocation, as the anchor's document has.
- **A test** that reads the committed captures, pools them, and asserts the reading the document
  records is what the evidence produces. Evidence that only one machine can open is not evidence.

### Which twenty runs

The verdict used seeds 93–330: nineteen complete twelve-seed batches plus the final ten-seed batch
(238 seeds × 2 arms). Three ranges were launched more than once while #426 was live; one directory per
range is committed here so the pool stays seed-disjoint, and the duplicate directories remain runtime
evidence and are not committed. The run ids the document will cite are:

```
20261104T234013Z  20261105T001837Z  20261104T234127Z  20261104T234132Z  20261105T100533Z
20261105T005435Z  20261105T005447Z  20261105T124200Z  20261105T012925Z  20261105T013749Z
20261105T013755Z  20261105T124205Z  20261105T140236Z  20261105T103841Z  20261105T103937Z
20261105T103853Z  20261105T140242Z  20261105T111110Z  20261105T114320Z  20261105T114647Z
```

The probe and the August/September runs are not cited and are not committed here.

## The arithmetic the evidence produces

Recomputing from the twenty directories (per-seed ΔAUC against the same seed's `A_raw`, between-seed
SD, 95% interval) gives **mean +0.0007, SD 0.0082, interval [−0.0003, +0.0018], 134/238 seeds
positive, 132 seeds needed at this SD**. The committed document currently says +0.0009, SD 0.0081,
[−0.0001, +0.0019], 129 seeds.

Those recorded figures are consistent with the 228-seed pool that existed **before the final ten-seed
batch** (`93–320`: mean +0.0009, SD 0.0081, 129 seeds needed) while the positive count (`134/238`) was
taken after it. The summary statistics and the seed count were therefore read from two different
pools. The reading is unaffected — both pools sit inside δ — but the document must state the numbers
its committed evidence produces. This change corrects them and says so in the commit message; it is a
correction of a transcription, not a re-litigation of the verdict.

## Verification

- `python scripts/analyses/verdict.py --run results/<each of the twenty> --delta 0.002 --reps 5000`
  reproduces the interval and the `equivalence` reading.
- `./scripts/check.sh citation` passes with the run ids in the document (and fails if a capture is
  missing).
- `pytest tests/ -q`, `ruff check scripts/ src/ tests/`, `shellcheck --severity=warning
  scripts/gpu_helpers/*.sh`, doclinks and docstatus pass.
- `./scripts/check.sh evidence` fails by design unless `EVIDENCE_CHANGE_OK=1`; the PR carries the
  `evidence-change` label, which is the CI equivalent.

## Out of scope

- Regenerating or re-running anything on the paid path. The arrays already exist; this change commits
  them and re-computes from them.
- The other D18 datasets (`coil2000`, `spanish_motor_lapse`), which were never measured.
- #407's diagnostics export, which is the same pattern for a different record type.
