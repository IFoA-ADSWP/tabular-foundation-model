# Plan — the balance is checked, not assumed (#348)

**Status:** Current — implementing 2026-10-31.
**Origin:** "are we checking the account balance before starting these experiments?"

## The gap

The launcher's only balance-related call was `vastai show user >/dev/null` — an auth probe that
discarded the value. The price ceiling bounds the **rate**; nothing bounded the **balance**. A run
could start with nothing left and fail after paying for provisioning.

## Why thresholds, not a projection

Cost is wall time × rate, and wall time is dominated by provisioning. The 2026-10-31 smoke was
estimated at 2.5p and cost 4.8p — 92% low. A projection that wrong would either block safe runs or
bless unsafe ones. The measured balance is a fact; a projection is a guess with a number.

## What lands

- `MIN_CREDIT_USD` (default 1.00): **refuse before creating**, naming the amount and the floor.
- `WARN_CREDIT_USD` (default 2.00): **warn and continue** — a thin balance is a decision.
- An unreadable balance **warns and continues**, because the ceiling still bounds the run, but the
  gap is stated rather than assumed.
- `credit_before_usd` is recorded in the per-run ledger, so "how close were we?" is answerable from
  evidence.

## Verification

- Mock takes `MOCK_CREDIT`; tests cover refuse-before-create (asserting `created.txt` is absent),
  warn-and-run, and the recorded value.
