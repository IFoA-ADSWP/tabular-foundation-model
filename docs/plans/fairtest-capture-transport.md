# Plan — the fair test ships its captures (#564)

> **Status:** proposed 2026-11-12. No spend: this plan ends with a transport exercised locally against
> a mock launch. The launch itself is a separate, owner-approved decision.

## Why

The resolution gate ran the fair test's primary comparison — `A_raw` vs `B_ft30`, four targets, five
folds, three seeds, 120 fits, 58.9 min, \$0.2629 — and returned only its 1 KB summary:
`__ARTIFACTS_INFO__ bytes=529 ... files=1` inside a 999-line log. The captures were written on the box
under `results/<id>/` and destroyed with it. So the gate bought the floors (2% frequency pooled, 4%
Spanish frequency per target, 2% severity) and produced nothing citable: the citation check needs
`results/<id>/capture.json`, and the pre-registration says the gate's point estimates are a preview.

Four gaps stand between here and a verdict, and only the first is about bytes on the wire:

| # | Gap | Evidence |
|---|---|---|
| 1 | No launch path runs the registered matrix | `bootstrap_pilot.sh:99-102` refuses any `FAIRTEST` other than `gate`; `:415` copies only the summary JSON |
| 2 | The log channel carries ~6.6 MB, captures are ~120 MB | `vast_run.sh:952` (`--tail 20000` × 440 chars); `--transport ssh` unavailable — team account `tfm_adswp`, `show ssh-keys` is `[]` |
| 3 | The citation check refuses schema v4 | `check_citations.py:183` accepts 1–3; #557 writes v4 |
| 4 | Captures land nowhere the check looks | launcher pulls to `outputs/gpu-pilot/runs/<stamp>/`; the check reads `results/<id>/` |

## Scope

The registered run is the **primary pair only** — 120 fits, ~1 h, ~\$0.26 compute. The `B_ft10` /
`B_ft3` epoch ladder is a follow-up, not part of this run: no floor is registered for those arms, so
they cannot move a verdict. A dated amendment records the narrowing (this PR, docs commit).

## Design

### 1. One process per target, sealed and emitted as it completes

`bootstrap_pilot.sh` gains `FAIRTEST=primary`: for each of the four targets, one
`run_fair_test.py --targets <t> --arms A_raw,B_ft30 --out-root results --run-id <stamp+index>` process,
then that target's run directory is emitted before the next starts. A failure late in the matrix
therefore forfeits one target, not four, and the payload per transfer is ~30 MB rather than ~120 MB.

Run ids keep the runner's own scheme (`_run_ids` offsets the base by one second per target), so a
`--run-id-offset` flag on the CLI is enough; no date arithmetic in shell.

### 2. Chunked, paced log transport

Same framing as today — `__ARTIFACTS_INFO__`, `__ARTIFACTS_BEGIN__`, `__ART__` lines, `__ARTIFACTS_END__`
— with two additions: a `chunks=` count and the `payload=<run id>` on the INFO line, and per-chunk
markers

```
__ART_CHUNK__ seq=3/16 payload=<run id> lines=4500
__ART__<440 chars>
...
__ART_CHUNK_END__
```

The emitter pauses between chunks (`TFM_CHUNK_PAUSE`, default 45 s) so that a chunk stays inside the
20 s poll window for about four chunks' worth of log, i.e. several polls. The invariant that makes
this safe is `chunk_lines < window_lines`: a chunk is then always wholly inside any window that
contains its start, and the emitter refuses a `TFM_CHUNK_LINES` above 18,000 because that leaves no
slack for the lines that arrive while a poll is in flight. `scripts/gpu_helpers/collect_chunks.py`
merges each poll's window into an accumulator keyed by `(payload, seq)`, seals a chunk only on
`__ART_CHUNK_END__` (a half-printed chunk is never sealed), and reports any missing `seq` by number.
Without `chunks=` on the INFO line the launch behaves exactly as today — the pilot path is untouched.
Chunk-level checksums are deliberately *not* part of the protocol: the payload's own sha256 on the
INFO line covers the whole archive end to end, and a second, weaker checksum would add a way for the
transfer to refuse a payload that is intact.

### 3. Captures land at `results/<id>/`

The collector writes the reassembled payload under the run's tree, and `--expect-captures 4` restores
each payload into `results/`, then calls `check_citations.check_run` on the restored id. Integrity comes
from the tarball sha (end to end); structure and coverage come from the citation check's own rules, so
the transport and the gate cannot disagree about what a usable capture is.

### 4. The citation check reads v4

`check_citations.py` accepts 4 and applies v4's rules: the v3 keys as before, plus `weights_sha256` and
`cluster_sha256` for slots whose `meta.json` records `task: severity` (and refuses them on frequency, as
the writer does). The French severity dataset block naming both files is **not** checked here — it is a
dataset-provenance claim, and this check is about the run's entries.

### 5. A failed transfer does not destroy the compute

In fair-test mode, a verification failure keeps the instance and prints the one-line destroy command,
plus the missing chunk seqs. Today the `EXIT` trap destroys unconditionally, so a transfer fault on the
last chunk would also destroy an hour of paid fits.

## Cost and runtime

120 fits ≈ 1 h at the measured 41.7 s/fit card time. Pacing adds roughly 45 s per ~2 MB chunk: four
targets at ~30 MB each, gzip ~20 MB and base64 ~27 MB per target ≈ 13 chunks ≈ 10 min per target, so
~40 min of transfer, ~\$0.18. Total ≈ \$0.45 against \$12.30 credit. The estimate the harness prints
before launch remains the release gate.

## Acceptance

- A mock launch carrying a multi-chunk payload reassembles byte-exactly; the restored v4 capture passes
  `python scripts/check_citations.py`.
- A dropped chunk fails loudly, names the missing `seq`, and does not exit 0 — proven locally by
  deleting a chunk from a synthetic log.
- The pilot path's single-payload transfer still round-trips (existing tests unchanged and green).
- `./scripts/check.sh` green: ruff, pytest, shellcheck, evidence, doclinks, docstatus, citation,
  verdict.

## Risks

- **Pacing is a heuristic, not a guarantee.** A stalled poller (laptop asleep, server restart) loses
  chunks. Mitigated by per-target emission (one target re-runnable) and by keeping the instance.
- **`--poll-minutes` default is 40.** A primary launch refuses a ceiling below 120 min rather than
  paying for fits and destroying the box mid-emit; the run needs ~160 (`--poll-minutes 180`).
- **The evidence check** compares `outputs/` and `results/`; a PR that lands captures needs the
  `evidence-change` label. This ticket lands none.

## Not in this plan

- No launch, no spend.
- No change to targets, folds, seeds, floors, the trainer, or the model pin.
- The epoch ladder, and any rescorer over the captures.
