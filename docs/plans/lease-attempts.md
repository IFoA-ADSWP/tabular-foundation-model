# Plan — a retry is a new attempt under one launch id (#326)

**Status:** Current — implementing 2026-10-31.
**Parent spec:** #324. **Origin:** #326, the second slice.

## The gap

#325 gave the launch one id and one record. The retry path still `exec`s the launcher, and
`lease_begin` minted a fresh id per process — so a failed attempt and its retry were two launches
that happened to look alike. Two instances, two records, no declared parent.

## The change

- `lease_begin` **reuses `LEASE_LAUNCH_ID` when it is inherited**, which it is: the variable is
  exported, and `exec` passes the environment. A retry therefore keeps its launch id and its label.
- The record gains an **`attempts` map**, keyed by `ATTEMPT`, with the instance id, state, outcome
  and timestamp of each attempt. One record per launch, one entry per try.
- A successful release still does not consume an attempt: `ATTEMPT` advances only in the retry path,
  as it did before.

## What is deliberately not changed

- **No new auto-retry inside the trap.** #325's teardown makes one destroy attempt and keeps the id;
  #326 is about identity across attempts, not about retrying teardown.
- **Adoption is still #327.** A kill mid-attempt leaves the record in `acquiring`; the label is how
  a successor finds it, and that is #327's job.

## Verification

- `tests/test_lease.py` gains a two-attempt test: same launch id and label across a simulated exec,
  distinct instance ids, both attempts present in one record, exactly one record file.
- The four existing lease tests pass unchanged.
- `./scripts/check.sh` green.
