# A launch id, and a spend gate that decides rather than acts

> **Status:** accepted, 2026-10-29

The paid-run path identifies a run with a launcher clock read (`RUN_STAMP`), which the box
records in its container block while the box separately mints its own stamp for the manifest
it writes. Nothing declares how the two relate, so a launch and its arm-runs join 1:N on
timestamps. At the same time the right to spend money is decided by six scattered refusals
inside a 755-line shell script — commit not on the remote branch, no usable offer, licence
not accepted, ssh key unavailable, onstart payload too large, create returned no id — each of
which prints and exits, and none of which leaves a record. We therefore mint the identity
before any spend, derive each run's id from it, and make the spend gate a pure decision that
a separate adapter feeds and the launcher renders.

## Considered Options

- **Let the box mint and the launcher adopt.** Matches what the box already writes, but the
  id only exists after money has been spent, so a refused or leaked create has none — the
  case that costs most to investigate.
- **One id for everything.** Simpler to say, but an arm-run then needs a tuple to identify
  it, which is the join problem wearing a different shape.
- **Derive the id from the experiment (dataset, arms, seed, commit).** Reproducible and
  self-describing, but two deliberate reruns of the same thing collide, and a rerun after an
  unrelated code change silently becomes a different identity.
- **A gate that performs its own I/O and exits.** Closer to today's code, but every test of
  it needs a repository, an offer fixture and a live token.
- **An HTTP client for the provider.** More explicit, but it re-implements offer selection
  and polling against an API this repository has only read about, and the zero-spend mock
  already implements the CLI's argv.

## Consequences

- A launch is one leased instance and one ledger row; a run is the glossary's experiment
  execution. A run's id is `<launch>.<dataset>.<arm>.seed<seed>`, so lineage is arithmetic
  rather than a join, and each record carries both ids.
- `TFM_LAUNCH_ID` replaces `TFM_RUN_STAMP` on the wire and in the container block. A reader
  still asking for the old name fails loudly instead of reading a stale stamp.
- The provider's `label` becomes the launch id, replacing the constant `tabpfn-pilot`. A
  create whose response was lost is findable, and a leaked instance is attributable to one
  launch rather than to every launch ever.
- A refused launch is recorded under the id it would have used, naming the checks that failed
  and the facts they saw. "Why didn't it run" then has an answer in the same place as "what
  did it cost".
- The gate checks four things and deliberately not a fifth: weights are fetched on the box,
  so a local check would prove nothing about the bytes that run.
- Provider operations are a closed set — the ones the path calls — so a call outside it is a
  design error rather than a shortcut.
- The word *gate* now names two different things in this repository. The one here is the
  **spend gate**; the gate that runs this repository's four checks keeps its own name.
