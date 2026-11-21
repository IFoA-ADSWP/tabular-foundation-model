# Plan — #568: a kept instance re-emits its captures without re-fitting

**Status:** Current — issue #568 (parent #564, map #623).
**Scope:** the fair-test primary path only. Not the pilot, not the gate, not the transport framing.

## Why

`severity_french` was fitted and then lost. The box had finished and sealed its capture; the
launcher on this machine died of local fork exhaustion before it could pull, and the destroy
failed. A poller that attached afterwards could not order the payload, because the declaration
(`__ARTIFACTS_INFO__`) had rolled out of the log window. Under the repo's rule an unverifiable
capture is not evidence, so the attempt was recorded UNTESTED and `≈$1.26` was spent for nothing.

The ticket's premise was then corrected: there is no exec channel, because `vastai execute`
accepts only `ls`/`rm`/`du` and SSH keys are refused by the team context. That correction is
accurate about `execute` but it is not the whole story: the instance lifecycle is a second channel,
and it was never tested.

## What was measured before writing any code

One `$0.0285/hr` instance, an onstart writing a boot counter to `/workspace`, destroyed afterwards.
**Total cost `$0.0023`** (credit `$3.7052` → `$3.7029`).

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

- **`scripts/gpu_helpers/fairtest_run_ids.py`** (new) — the launch's run ids: the stamp, then one
  per second per target, which is the rule `run_fair_test.py --run-id-offset` already uses. The
  target loop, the on-box check and the driver share it so a sealed capture cannot go unrecognised.
- **`scripts/gpu_helpers/bootstrap_pilot.sh`** — the target loop names its run id through that
  helper, and a short primary-mode guard after the checkout calls `reemit_on_box.sh`.
- **`scripts/gpu_helpers/reemit_on_box.sh`** (new) — the on-box side. Requires the launch's identity
  (`TFM_RUN_STAMP` and `TFM_FAIRTEST_TARGETS`), derives its ids, and:
  - exit 0: every one of *this launch's* captures is sealed — emit each and exit without fitting;
  - exit 1: not all are sealed (silent on a first boot, `PARTIAL` when a restart finds some);
  - exit 2: an emission failed — the caller must **not** fit, because the box already has the
    captures.
  - It lives here, not in the bootstrap, because the bootstrap is inlined into the onstart field
    and gzipped to **15,730 of the 16,000-byte launcher ceiling**. The first cut inlined it and
    produced a 16,568-byte payload — over the API's 16,384 cap, which would have failed *every*
    launch at create. A test pins the headroom.
- **`scripts/gpu_helpers/reemit_captures.sh`** (new) — the driver behind `--fairtest reemit`:
  - checks the instance is a launch's (`tabpfn-pilot-*` label) before rebooting it;
  - refuses at $0 when the **tail** of the log carries no payload evidence — `__ART__`,
    `__ART_CHUNK__`, `__ARTIFACTS_INFO__`/`__ARTIFACTS_END__` or an `EMIT` marker;
  - reboots, merges chunks into a **persistent** per-instance state directory (a retry resumes
    rather than re-emitting), takes the capture count from the box's own `REEMIT: N sealed` line,
    verifies into a scratch tree and only then moves captures into `results/`;
  - sizes the ceiling from the target count (15 + 30/target minutes, like the launcher) and loops
    on elapsed seconds;
  - if the log shows the box fitting instead (an old onstart, or a partly-sealed launch), it
    **destroys** the box by default: leaving it would bill for a second full launch while the
    operator reads a "kept" message. `--keep-fitting` keeps it;
  - records `outputs/gpu-pilot/reemit_<id>_<stamp>.json` with wall time and estimated cost, so
    recovery spend is visible to the cost model.
- **`scripts/gpu_helpers/vast_run.sh`** — `--fairtest reemit --instance ID` is accepted, documented
  in the header, refused alongside frame-owning options, and delegated.
- **`scripts/gpu_helpers/mock_vastai.sh`** — models `reboot instance`, the `EMIT`/`REEMIT` markers,
  a box that emits nothing, and a box that starts fitting.

## Decisions

- **Reboot, not `update`.** `update` requires an image and recreates the container; `reboot` was
  measured to re-run the onstart with the disk intact, which is the whole requirement.
- **The launch is identified by its stamp, not by `results/`.** The first cut counted
  `results/*/capture.json`; a fresh clone carries the repository's own **37** committed captures,
  so every primary launch would have found a "full" set, skipped its fit and emitted 37 payloads
  the verifier then refused. The ids are derivable and the ticket asked for exactly that.
- **The pre-flight reads the tail.** `__ARTIFACTS_INFO__` and the `EMIT` markers are the *first*
  lines of an emission. Measured 2026-11-21: one 9.6 MB capture produced **109,897** log lines and
  its last 8,000 contained **no** INFO line and **no** EMIT marker — only chunk lines. The earlier
  draft of this plan claimed the opposite; the comment, the predicate and this paragraph are
  corrected against the measurement.
- **No `execute` pre-flight.** The CLI cannot print a successful execute result, so a pre-flight
  would have to reach around it to the API. The log gives the same answer through a channel the
  launcher already depends on.
- **Only text from the current boot is trusted.** The container log accumulates across restarts, so
  a `PARTIAL` or dependency-install line from an earlier boot can still be in the tail. The box
  writes a `REEMIT CHECK <epoch>` boot marker and the driver acts only on text after the newest
  marker whose stamp is later than the one it read before rebooting — monotonic within the box's
  own clock, so no comparison across two machines is needed.
- **Verification is retried, not assumed**, but it restores into a scratch tree: a partial or
  refused restore must not write into the tracked `results/` that `check.sh evidence` compares.

## Limits

- **Only a box whose onstart already carries section 2b can be recovered.** The onstart payload is
  frozen into the instance at create, so the box that motivated this ticket cannot use the new
  path; a reboot of it starts a full launch, which the driver detects and stops. Every future
  launch is recoverable.
- **A partly-sealed launch is not cheap.** Emitting three of four would be refused by the verifier,
  so the box fits the launch again. The driver treats that as a paid re-fit: it reports it and
  destroys the box unless `--keep-fitting`.
- **`--seeds` is optional, and then the seed range is not checked against the launch.** The
  captures are still hash-verified and citation-checked; the launch's own seed check is the
  launcher's, and its seeds are not readable from this side.
- No substitute for `caffeinate`. A suspended launcher still misses wholesale; this makes the miss
  recoverable, not impossible.

## Not in scope

- No change to the capture contract, the framing, or the registered matrix.
- No pilot-mode recovery: the pilot's payload fits one window, which is why it never needed this.
- Re-printing `__ARTIFACTS_INFO__` at the head of each chunk pass (so a late poller can rebuild the
  declaration without ever seeing the head) is a transport change and belongs in its own ticket.

## Verification

```bash
.venv/bin/pytest tests/test_reemit_captures.py -q
.venv/bin/pytest tests/test_fairtest_capture_launch.py tests/test_pilot2_seed_passthrough.py -q
./scripts/check.sh
```
