# Plan — the lease writes its record and reports its release (#325)

**Status:** Current — implementing 2026-10-31.
**Origin:** spec #324 under the paid-path map #244.

## The defect

Teardown had two owners and three opinions. The EXIT trap destroyed carefully; the retry path did
`vastai destroy ... || true`, cleared the id, and `exec`ed a fresh process. A destroy that failed at
the API was discarded, the id was forgotten, and the new process could not see the old instance. The
instance kept billing, and nothing in the repository said so.

## The change

1. **A launch id minted before provisioning**, `<utc>-<6 hex>`, used as the provider label. That is
   what makes the instance findable again after a lost response or a dead process.
2. **A lease record written before the create call** and updated on every transition
   (`pending` → `acquired` → `released` / `failed` / `kept`, plus `aborted` when nothing was ever
   rented and `unknown` when a create's response was lost), atomically, under the runtime output
   tree. It is not committed evidence.

**Scoped fields.** `instance_id`, `label` and `state` are read by the tests and by the watchdog.
`image`, `reason` and the timestamps are read by a human during an incident and by the watchdog rule
in #328 — no launcher code path reads them, and saying so is the difference between a record and
decoration (`CODING_STANDARDS.md`, rule 1).
3. **`lease_release` records one of three findings** — `released`, `already_gone`, `failed(reason)`
   — in `LEASE_OUTCOME` and returns success or failure. The instance id is cleared only on a
   confirmed release. A failed release keeps it, prints it with a one-line destroy command, and
   makes the process exit non-zero. **Teardown retries once** before reporting failure: a dropped
   connection at that moment is exactly what a second attempt fixes, and one attempt would strand
   the machine on a blip.
4. **One trap calls `release`.** `cleanup` keeps the temp-file, log and record duties; the destroy
   moved into the lease, so the trap and the retry cannot disagree.
5. **The retry releases first**, then re-execs only on a confirmed release. Its isolation benefit is
   kept; its ability to forget an instance is not.

## Known gaps, stated

- **Ordering is not asserted by a test.** The pre-create write sits immediately before the create
  call, but nothing compares the record's existence to the mock's create timestamp.
- **Idempotence is process-local.** `LEASE_RELEASED` guards a second release in one process; a
  successor process is #327's adoption problem, and the record it would read is not written back
  into memory here.

## Verification

- The mock gains a fail-once destroy, because a destroy that never fails cannot prove the id is kept.
- Three new tests, all at the mock/record seams: normal exit records `released` and destroys exactly
  once; an injected failure leaves `failed` with the id in the record, prints the id and the launch
  id, exits non-zero, and records no destroy; and the trap does not retry a destroy that failed.
- The seven existing launcher tests pass unchanged.

## Retry gating is in scope, deliberately

#325's own criteria include "failure mid-run → released, one destroy, **no retry**". That cannot be
met without gating the retry, so the gate lands here. #326 keeps the remaining work: recording both
attempts under one launch id, and a test that a second attempt reuses it. The launch id is exported
so an `exec` cannot re-mint it.

## Out of scope

Adoption (#327), the watchdog rule (#328), and per-attempt bookkeeping in the record (#326).

`--keep` writes the state `kept`. It is not a release and not a leak; #328 must treat it as
explicitly retained rather than stranded.
