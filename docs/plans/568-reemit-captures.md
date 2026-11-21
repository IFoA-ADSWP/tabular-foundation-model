# Plan — #568: a kept instance re-emits its captures without re-fitting

**Status:** Current — issue #568 (parent #564, map #623).
**Scope:** the fair-test primary path only. Not the pilot, not the gate, not the transport framing.

## Why

`severity_french` was fitted and then lost. The box had finished and sealed its capture; the
launcher on this machine died of local fork exhaustion before it could pull, and the destroy
failed. A poller that attached afterwards could not order the payload, because the header
(`__ARTIFACTS_INFO__`) had rolled out of the log window. Under the repo's rule an unverifiable
capture is not evidence, so the attempt was recorded UNTESTED and `≈$1.26` was spent for nothing.

The ticket's premise was then corrected: there is no exec channel, because `vastai execute`
accepts only `ls`/`rm`/`du` and SSH keys are refused by the team context. That correction is
accurate about `execute` but it is not the whole story: the instance lifecycle is a second channel,
and it was never tested.

## What was measured before writing any code

One CPU-priced GPU instance (P2000, `$0.0285/hr`), onstart writing a boot counter to `/workspace`,
destroyed after the probe. **Total cost `$0.0023`** (credit `$3.7052` → `$3.7029`).

| Question | Measurement |
|---|---|
| Does `vastai reboot instance` re-run the onstart? | Yes — `PROBE_BOOT n=1` then `n=2`, `n=3`, `n=4` |
| Does the instance disk survive a restart? | Yes — the counter is read back and incremented each boot |
| Does the container log survive a restart? | Yes — every boot's line is visible after the restart, and `n=1` is still there at `n=4` |
| `stop` then `start` | Works; `actual_status` reads `exited` while stopped (`intended_status: stopped`) |
| `update instance --onstart` | Rejected without `--image` (`image must be a str, not NoneType`), so it recreates from an image. Not used. |
| `execute ls` | Works at the API (`ls /workspace/probe` → `count`), but the installed CLI crashes printing a SUCCESSFUL result (`'str' object has no attribute 'get'`). Not used. |
| `execute` on a running box | Refused: "only avail on stopped instances" |

So the recovery channel exists and is a `reboot`, and it is cheap: the onstart carries its own
environment (the token included), so nothing has to be re-supplied.

## What changes

- **`scripts/gpu_helpers/bootstrap_pilot.sh`** — a short primary-mode guard after the checkout:
  when `reemit_on_box.sh` reports the launch is fully sealed, emit and exit before the dependencies,
  weights or fit. It is deliberately automatic, because the box cannot be told after the fact.
- **`scripts/gpu_helpers/reemit_on_box.sh`** (new) — the on-box side. Counts sealed
  `results/*/capture.json` against the launch's targets; emits every one through the existing
  chunked transport when all are sealed, and otherwise declines (exit 1) with a PARTIAL line so the
  normal path runs.
  - The logic lives here, not in the bootstrap, because the bootstrap is inlined into the onstart
    field and **gzipped to 15,730 of the 16,000-byte launcher ceiling**. The first cut of this
    change put it at 16,568 — over the API's 16,384, which would have failed *every* launch at
    create. A test now pins the headroom.
  - A partly-sealed box is **not** re-emitted: emitting three of four would be refused by the
    verifier anyway. It falls through to a normal boot, which fits the launch again. That is the
    costly case this change does not make cheap, and the PARTIAL line says so.
- **`scripts/gpu_helpers/reemit_captures.sh`** (new) — the launcher-side driver.
  - Pre-flight from the log it can already read: it requires at least one
    `########## EMIT <target> (<id>)` marker — the bootstrap writes one per sealed capture, and
    they sit *ahead* of the payload, so demanding one per target would refuse on exactly the box
    whose window has scrolled past the payload. It refuses before rebooting when there is none.
  - `vastai reboot instance <id>`, then polls the log and merges chunks with the same
    `collect_chunks.py` the launch uses, retrying `verify_artifacts.py --expect-captures` until it
    passes or the poll ceiling expires.
  - The count handed to the verifier is the **box's own** `REEMIT: N sealed` line, not the local
    target list: a canary launch is one target, and the window may have scrolled past some markers.
  - It stops and keeps the box if the log shows the dependency install starting, which is what an
    old checkout or a partly-sealed box does when it takes the normal path — polling on would look
    like a slow transfer while a second full launch billed.
  - Restores into `results/<run id>/`; destroys the instance on success, keeps it (and prints the
    destroy command) on failure. It never creates an instance and never fits anything.
- **`scripts/gpu_helpers/vast_run.sh`** — `--fairtest reemit` is accepted and delegates to the
  driver, so the mode is discoverable and its arguments are validated in one place.
- **`scripts/gpu_helpers/mock_vastai.sh`** — models `reboot instance` and re-emits the box tree
  from the mock log, so the whole path is exercised at $0.

## Decisions

- **Reboot, not `update`.** `update` requires an image and recreates the container; `reboot` was
  measured to re-run the onstart with the disk intact, which is the whole requirement.
- **No `execute` pre-flight.** The CLI cannot print a successful execute result, so a pre-flight
  would have to reach around it to the API. The log markers give the same answer through a channel
  the launcher already depends on.
- **The box decides whether it has anything to re-emit.** Its sealed-directory check is the
  authoritative test; the launcher's log pre-flight only stops a pointless reboot.
- **Verification is retried, not assumed.** The loop keeps merging and re-verifying until the
  verifier is satisfied, so a slow chunk stream cannot be mistaken for a complete transfer.

## Not in scope

- No change to the capture contract, the framing, or the registered matrix.
- No substitute for `caffeinate`. A suspended launcher still misses wholesale; this makes the
  miss recoverable, not impossible.
- No pilot-mode recovery: the pilot's payload fits one window, which is why it never needed this.

## Verification

```bash
.venv/bin/pytest tests/test_reemit_captures.py -q
.venv/bin/pytest tests/test_fairtest_capture_launch.py -q
./scripts/check.sh
```
