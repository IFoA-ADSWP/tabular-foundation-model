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
   (`pending` → `acquired` → `released` / `failed` / `kept`), atomically, under the runtime output
   tree. It is not committed evidence.
3. **`lease_release` returns one of three findings** — `released`, `already_gone`, `failed(reason)`.
   The instance id is cleared only on a confirmed release. A failed release keeps it, prints it with
   a one-line destroy command, and makes the process exit non-zero.
4. **One trap calls `release`.** `cleanup` keeps the temp-file, log and record duties; the destroy
   moved into the lease, so the trap and the retry cannot disagree.
5. **The retry releases first**, then re-execs only on a confirmed release. Its isolation benefit is
   kept; its ability to forget an instance is not.

## Verification

- The mock gains a fail-once destroy, because a destroy that never fails cannot prove the id is kept.
- Three new tests, all at the mock/record seams: normal exit records `released` and destroys exactly
  once; an injected failure leaves `failed` with the id in the record, prints the id and the launch
  id, exits non-zero, and records no destroy; and the trap does not retry a destroy that failed.
- The seven existing launcher tests pass unchanged.

## Out of scope

Retry gating (#326), adoption (#327), the watchdog rule (#328).
