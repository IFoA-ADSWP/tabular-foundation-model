# A launch id, and a spend gate that decides rather than acts

> **Status:** accepted, 2026-10-29

The paid-run path identifies a run with a launcher clock read (`RUN_STAMP`), which the box
records in its container block while the box separately mints its own stamp for the manifest
it writes. Nothing declares how the two relate, so a launch and its arm-runs join 1:N on
timestamps. At the same time the right to spend money is decided by six scattered refusals
inside a 755-line shell script, each of which prints and exits, and none of which leaves a
record. We therefore mint the identity before any spend, derive each run's id from it, and
make the spend gate a pure decision that a separate adapter feeds and the launcher renders.

The provider seam is part of the same contract, because both halves depend on it: the only
server-side handle a lost create can be found by is the provider's `label`, and the set of
calls the path may make is what the mock has to answer.

## Decisions

### Identity

- **Who mints.** The Python lifecycle entry point of the paid path, before any spend; the
  shell invokes it. The box records the id it was given and never invents its own.
- **Shape.** A UTC stamp plus six hex digits, e.g. `20261029T142530Z-a3f19c` — sortable, and
  collision-free for two launches in the same second, which a bare timestamp cannot promise.
- **Two levels.** A *launch* is one leased instance with one cost record. A *run* is the
  glossary's experiment execution inside it. A launch contains zero or more runs.
- **Derived run id.** `<launch>.<dataset>.<arm>.seed<seed>`. The box composes it from the
  launch id and what it already knows, so lineage is arithmetic rather than a join. Each
  record carries both the derived id and the launch id it came from.
- **Ad-hoc runs.** A run with no launcher mints a `local-` prefixed id, so a laptop or
  notebook run stays possible and can never be mistaken for a paid one.
- **Wire and record.** `TFM_LAUNCH_ID` replaces `TFM_RUN_STAMP`, and the container block's
  field is renamed to match: a reader still asking for the old name fails loudly instead of
  silently reading a stale stamp. The per-launch record `run_<stamp>.json` becomes
  `launch_<id>.json`; the artifact directory stays `runs/<launch>`; the ledger keeps being
  derived from the records rather than written independently.

### The spend gate

- **Shape.** A pure function over a gathered facts value. It returns allow or refuse plus
  reasons; it performs no I/O, prints nothing and never exits. A small adapter is the only
  component that reads git, configuration and the environment on its behalf.
- **The four checks.** Commit on the remote branch; image allow-listed and pinned; offer
  allow-listed and under the ceiling; token present and licence accepted. Weights are
  deliberately not checked — they are fetched on the box, so a local check would prove
  nothing about the bytes that run.
- **What is not a check.** An unavailable ssh key, an oversized onstart payload and a create
  that returns no id are not pre-spend facts; they happen at or after create and remain
  runtime failures. The gate's four are the ones that can be proven before an instance exists.
- **Refusal.** One exit code for a gate refusal, distinct from transport failures, listing
  **every** failed check at once rather than the first — so a refused launch is fixable in
  one edit instead of one edit per attempt.
- **Recording.** A refused launch writes a record too, naming the checks that failed and the
  facts they saw, under the launch id it would have used. "Why didn't it run" then has an
  answer in the same place as "what did it cost".

### The provider

- **Boundary.** The provider CLI. The mock is its second implementation, not a fixture: the
  interface is the argv it answers, which is how the zero-spend tests already work.
- **A closed operation set.** Search offers, create, list/show instances, logs, destroy, and
  execute — the calls the path makes today. Bulk copy is admitted only if the research open
  item confirms it works on this team-context account; until then the log channel is the only
  return path. A call outside the set is a design error rather than a shortcut.
- **Adoption handle.** The provider's `label` is the launch id, replacing the constant
  `tabpfn-pilot`. Adoption must then require **exactly one** match: zero or more than one is a
  refusal that reports what it saw, never a guess. The research found no idempotency token, so
  this is the only guard available.

## Considered Options

- **Let the box mint and the launcher adopt.** Matches what the box already writes, but the
  id only exists after money has been spent, so a refused or leaked create has none.
- **One id for everything.** Simpler to say, but an arm-run then needs a tuple to identify
  it, which is the join problem wearing a different shape.
- **Derive the id from the experiment (dataset, arms, seed, commit).** Reproducible and
  self-describing, but two deliberate reruns collide, and a rerun after an unrelated code
  change silently becomes a different identity.
- **A gate that performs its own I/O and exits.** Closer to today's code, but every test of it
  needs a repository, an offer fixture and a live token.
- **An HTTP client for the provider.** More explicit, but it re-implements offer selection and
  polling against an API this repository has only read about.

## Consequences

- Each run's lineage is computed, not joined: no consumer has to reconcile two clock reads.
- A launch that is refused still leaves evidence, and the evidence names the facts the gate saw.
- `docs/REPRODUCIBILITY_RUNBOOK.md`, the ledger and the committed `run_*.json` files call a
  rented machine a "run". They predate this decision and are not rewritten; new text uses
  *launch*, and the glossary's *launch* entry says so explicitly.
- Provider operations are enumerable, so an unlisted call can be refused in review.
- The word *gate* now names two different things in this repository. The one here is the
  **spend gate**; the gate that runs this repository's checks keeps its own name, and this ADR
  deliberately does not count its checks alongside the spend gate's four.
- Two research items stay open rather than assumed: whether bulk copy works on this account,
  and whether a rejected create can leave a billable instance behind.

## References

- `GLOSSARY.md` — *launch*, *launch id*, *arrival*, *spend gate*, and the unchanged *run*.
- `docs/MODEL_VERSIONS.md` — model identity is recorded, never inferred.
- `docs/REPRODUCIBILITY_RUNBOOK.md` — how the paid path is driven today.
- Issues #245 (the decisions), #246 (the provider research), #247–#253 (the seams this unblocks).
