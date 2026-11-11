# Plan — a pinned offer declares its CUDA, and the box kernel-tests torch

**Issue:** #528 (found on the two paid attempts; the probe itself is still unmeasured).
**Status:** Proposed.

## What and why

The first two attempts to run the benchmark probe spent $0.0423 and produced no measurement.
Both failed on the same seam — the image chosen for the card — and neither was the code path
PR #546 built.

1. **A pinned offer hardcoded the CUDA ceiling.** `vast_run.sh` did `CUDA="${CUDA:-12.4}"` for
   `--offer-id`. On a Blackwell RTX PRO 4000 (`sm_120`, host CUDA 13.0) that selected
   `pytorch/pytorch:2.5.1-cuda12.4` (torch 2.5.1+cu124), which carries kernels only for
   `sm_50`–`sm_90`. The fit reached epoch 1 and died with `CUDA error: no kernel image is
   available for execution on the device`.
2. **The bootstrap's GPU check could not see that.** `torch.cuda.is_available()` asks the
   driver, not whether the installed build has kernels for the card. The check printed the
   sm-compatibility warning and continued, so the failure arrived after the dependency install,
   the classifier checkpoint download and the start of training.

The image matrix already had the right tier (`pytorch/pytorch:2.7.0-cuda12.8`, torch 2.7.0,
which supports `sm_120`); the offer-id path simply could not reach it.

## Shape

- **`vast_run.sh`**: for a supplied offer, read `cuda_max_good` from the live offer list. If the
  offer is no longer listed, accept `CUDA=<host cuda>`; if neither, refuse before provisioning
  with the two ways out named. The selector path already reads the same field from the offer it
  picks, so both paths now answer the question the same way.
- **`bootstrap_pilot.sh`**: after `is_available()`, print the compute capability and the build's
  arch list, then launch one small real kernel (`8x8` matmul). If that fails, exit 2 with the
  card, the capability and the build in the message — before the weight fetch.

## Judgement calls

1. **Query, do not guess.** A hardcoded ceiling is a setting that cannot move and reads like
   one. The offer knows its CUDA; the launcher asks.
2. **Refuse when the offer is gone.** Falling back to a default is how this defect shipped. The
   operator can state `CUDA=` deliberately; silence is not an override.
3. **A kernel, not an arch-list string match.** `get_arch_list()` can include PTX-only entries,
   and whether a given kernel has a usable cubin is the thing that actually fails. One `8x8`
   matmul costs milliseconds on a paid box and is decisive.
4. **No retry logic change.** The two defects are fixed; the one-attempt discipline stays. The
   probe's authorisation is per attempt and is recorded on #528.

## Verification

- `pytest tests/test_benchmark_probe_path.py tests/test_pilot2_seed_passthrough.py -q` — a
  pinned offer with a readable ceiling selects the cu128 image; an unreadable offer refuses with
  `CUDA=<host cuda>` named; an explicit `CUDA` is honoured; the mock offers fixture carries the
  ceiling the launcher now reads.
- `shellcheck --severity=warning scripts/*.sh scripts/gpu_helpers/*.sh` — the kernel test is a
  double-quoted `python3 -c`, so the `$0` in its message is escaped; shellcheck is where that is
  checked.
- `./scripts/check.sh` — the eight-check gate.

## Not covered by tests

The kernel test itself cannot run in CI: it needs a GPU. The defence is that its failure mode is
loud and free (exit 2 before any download), and that its absence was measured, not theorised:
attempt 2's log is on #528.

## After this lands

Re-run the probe **without** pinning an offer, so the selector reads CUDA from its own choice,
or pin one and state `CUDA=<host cuda>`. The rate ceiling and one-attempt rule are unchanged.
