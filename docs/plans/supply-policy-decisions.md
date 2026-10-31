# Plan — record the supply policy (#253)

**Status:** Current — agreed 2026-10-31, documentation only.
**Origin:** issue #253 (the supply-policy seam of the paid-run path), closed with the
decisions below. This change is the durable record of them, and it follows the shape #275
used for the spine.
**Glossary:** `GLOSSARY.md` · **Map:** #244 · **Follow-ups:** #366, #367

## Scope

Documentation only. Two artifacts, no code:

1. `GLOSSARY.md` — *offer*, *host*, *machine class*, *supply policy*, *pin*, and an
   *instance* disambiguation, so the words the spec will use exist before it is written.
2. `CHANGELOG.md` — an `[Unreleased]` entry, since the vocabulary is user-facing for anyone
   reading a launch record.

No ADR. ADR 0002 already records the launch/gate contract this seam sits inside, and these
decisions are reachable from it in one step; the reasoning that is worth keeping is on #253
and summarised here.

## What was decided

**Identity.** `machine_id` is the host handle and the only thing matched across reruns; an
offer id is a per-rent detail, recorded and never compared, because offers expire and are
single-use. A *machine class* is the attribute tuple `gpu_name | gpu_ram | cuda_max_good`.
`dlperf` is recorded as observed throughput but is not part of identity: it is a per-host
marketplace measurement that drifts, and including it would make the same class
unsatisfiable within weeks.

**Claims.** A replication requires the same class, not the same host. The invocation names
its baseline (`--replicate <launch-id>`), the adapter reads that launch's record for the
class, and a missing or class-less baseline is a refusal. Selection prefers the baseline's
class; when no offer of that class clears the filters and ceiling it takes the best
allow-listed offer and the record states the deviation. Refusing outright was rejected: it
turns an availability fact into a failed overnight run.

**Image.** The image is still derived from the host's `cuda_max_good` through the verified
tier matrix (never above the driver ceiling, every tier torch >= 2.5). The matrix, the GPU
allow-list, the class table and the ceiling live in one `supply_policy.py`, so the launcher
and the spend gate's adapter read the same values instead of two shell constants that can
drift. Each tier tag carries a declared digest, verified against the registry before spend;
a mismatch refuses, and an unreachable registry refuses too, because an indeterminate check
is not a pass.

**Spend.** The policy owns one ceiling with a logged invocation override. The same rule —
policy default, logged override — applies to `--pick`, `--min-vram`, `--disk`, the
reliability floor and the extra query filters, and the effective value plus its source goes
into the pre-spend record. The CUDA floor, the excluded architectures and the arch
allow-list are narrow-only: an invocation may tighten, never widen. A pinned offer skips
ranking but not the gate.

**No offer.** It fails the gate's "offer allow-listed and under the ceiling" check, so it
takes the same refusal code as any other refusal, lists every failed reason at once, names
the near misses by price, and writes a record. It never auto-widens.

**The seam.** Two pure functions over one table: `choose(offers, intent)` — affinity,
ranking, narrow-only filters — and `classify(offer, intent)` — the gate's allow/refuse. The
launcher calls the first, the gate calls the second.

## Two things worth flagging to the implementer

- **A second ceiling had already appeared.** `vast_run.sh` carried `MAX_DPH=0.60` as a flag
  default *and* `dph<0.80` inside `DEFAULT_QUERY`. Two values, one of them invisible in any
  record, and the gate could only have seen whichever one it was told about. The query's
  copy goes; exactly one ceiling exists, the one the gate reads.
- **The pin is a pre-spend network call.** That is deliberate, and it is the only place in
  the gate that reaches the network. #366 establishes whether the anonymous manifest lookup
  works, what rate limit applies, and the four digests; if it does not work, the pin decision
  is the thing that reopens, not the gate's shape.

## What this does not decide

- What a ceiling breach, a timeout and a watchdog fire do mid-run, and who owns the
  watchdog — #367.
- The launch record's field shape — #240 owns it; this plan names only what the policy hands
  the gate.
- Anything about implementation: no `supply_policy.py` exists yet. The spec for the paid
  path is the next artifact, and it consumes this seam.
