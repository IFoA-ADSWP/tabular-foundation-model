# Plan — let the paid path carry the benchmark measurement

**Issue:** #528 (the probe; harness #526, spec #501).
**Status:** Proposed.

## What and why

The regressor fair test is priced from one measured fine-tune: 10,000 rows, 30 epochs, on the GPU
class the rate was measured on. `scripts/benchmarks/benchmark_regressor_fit.py --measure` does
exactly that and writes a `benchmark_fit` record. It cannot be run on a rented box yet, because
`scripts/gpu_helpers/bootstrap_pilot.sh` only knows how to run `scripts/run_pilot.py`'s arms. The
probe is therefore implemented and unlaunchable — the same shape as #450: both ends correct, the
seam missing.

This change is the free half. It makes the measurement reachable through the existing paid path
and returns it through the existing artifact channel. **It spends nothing and authorises nothing**
— the probe itself is released separately on #528, and the fair test is not authorised by either.

## Shape

Three pieces, each at a seam the tests can hold:

1. **`BENCHMARK` is a mode on the box** (`bootstrap_pilot.sh`). Empty runs arms as today;
   `regressor-fit` runs one benchmark command instead. The GPU check, dependency pins, weight
   fetch and licence preflight still run first, because they are what makes the timing
   representative, and skipping them would measure a box nobody would run on.
2. **`--benchmark MODE` is the launcher's switch** (`vast_run.sh`). It forwards `BENCHMARK` into
   the onstart payload and the SSH invocation like every other operator setting, pulls
   `outputs/benchmark` on the SSH transport, and asks the verifier for a measurement.
3. **The verifier checks the measurement** (`verify_artifacts.py --expect-measurement`). The
   payload has no predictions, so the prediction hash check cannot run. Reporting
   `verified=0` would be a refusal dressed as a check; checking the record's own shape is the
   equivalent claim, and a missing record is exit 7 — a failed probe, not a warning.

The record rides `emit_artifacts.sh` unchanged: it already carries a directory's top-level
`*.json`, so `outputs/benchmark/regressor-fit-<run stamp>.json` is a file it emits today.

## Judgement calls

1. **A mode, not a `run_pilot.py` flag.** The benchmark is one command with its own frame,
   device and epoch budget. A flag on the pilot runner would make the runner know about
   benchmark config it never uses, and the two frames would drift.
2. **The mode owns the frame, and a mix is refused.** `--benchmark regressor-fit --arms A_raw`
   has two answers. The launcher refuses it before provisioning and the bootstrap refuses it
   again for direct runs, because silently dropping one is the seam failure #450 keeps closing.
3. **The regressor's checkpoint is warmed, untimed.** The bootstrap's licence preflight
   fetches the classifier's `tabpfn-v3-classifier-v3_default.ckpt`; the regressor has its own
   `tabpfn-v3-regressor-v3_default.ckpt`, which a cold box would have downloaded inside
   `fit()` — making the "fit time" mostly network. `--measure` now resolves the same cache path
   the fit will use and downloads first, and the record states `weights.downloaded` so a reader
   can tell the timer started clean. This was found before renting; it is the third blocker on
   #528, alongside funding and the missing mode. The record also carries the run stamp, commit
   and resolved GPU name, so a wall time is attributable to the card and launch it came from
   rather than to the string `cuda`.
4. **Verification checks the measurement rather than skipping the step.** A skipped check reads
   as a pass. The record must carry the fields the acceptance criterion names — `wall_seconds`,
   `rows`, `epochs`, `device`, `tabpfn_version`, `frame`, `seed` — a positive wall time, and
   the pre-registered point (10,000 rows × 30 epochs of `freMTPL2freq:ClaimNb`). Presence alone
   would accept a 3,000-row fit and price the whole matrix from it.
5. **Exactly one record per payload.** One capture carries one point. Two records mean a mixed
   launch or a duplicated emit; both are worth stopping on.
6. **An empty payload is a refusal in this mode.** For the pilot, no outputs can be an aborted
   arm; for a probe it means the run measured nothing and still cost money.
7. **The ledger is untouched.** `record_run` already writes wall time x rate, which is the
   probe's cost. Adding a field would change the ledger header and quarantine the existing file;
   the probe is identified by its run id and its measurement record on #528 instead.
8. **The record is not committed.** A record committed under `outputs/` would be evidence drift
   against `origin/main`; leaving it untracked and citing it on #528 keeps this PR
   code-and-tests. (The evidence check compares tracked changes, so an untracked file would not
   trip it — this is a discipline, not a gate.)

## Verification

- `pytest tests/test_benchmark_probe_path.py -q` — forwarding, both refusals, the bootstrap's
  measure-and-emit path, the verifier's five rejection cases, and one end-to-end mock launch
  (exit 0 with the record; exit 1 with none).
- `pytest tests/test_pilot2_seed_passthrough.py -q` — the environment seam audit still passes
  with `BENCHMARK` declared launcher-owned, and the passthrough list has no dead entries.
- `shellcheck --severity=warning scripts/*.sh scripts/gpu_helpers/*.sh`.
- `ruff check scripts/ src/ tests/`.
- `./scripts/check.sh` — the eight-check gate.

## What this does not do

- It does not top up the account. The launcher refuses below `MIN_CREDIT_USD`, and the balance is
  the owner's action.
- It does not run the probe, and it does not produce an estimate. `--estimate` is free but is
  worthless until a real measurement exists.

## After this lands

```bash
# topped up, one attempt, at or below the authorised rate.
bash scripts/gpu_helpers/vast_run.sh \
  --benchmark regressor-fit --gpu-allow "RTX PRO 4000" --max-dph 0.2893 \
  --max-attempts 1 --poll-minutes 20 --yes
```

The cost of the run is (provisioning + completion poll) × rate, not the poll alone: the poll
starts when the instance reaches `running`, while billing starts at create. Measured
provisioning is ~3 min warm and ~15 min slow, so 20 + 15 = 35 min worst case is **$0.169** at
$0.2893/hr, inside the $0.20 ceiling; the expected case (3 min boot + ~3 min fit) is about
$0.03. The launcher has no wall-clock cap, so a slow host can still exceed the poll; the poll is
what bounds it. A 40-minute default would put the worst case at $0.265, over the ceiling.

The record lands under `outputs/gpu-pilot/runs/<run stamp>/`. Then, free and local:

```bash
python scripts/benchmarks/benchmark_regressor_fit.py --estimate \
  --measurement outputs/gpu-pilot/runs/<run stamp>/regressor-fit-<run stamp>.json \
  --rate-per-hour <the offer's rate> --ceiling 50
```
