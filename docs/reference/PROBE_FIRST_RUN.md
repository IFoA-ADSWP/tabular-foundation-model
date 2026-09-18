# The probe's first real run — what it took to get a container up

**This records the transport, not the result.** The launcher had been reviewed and unit-tested and had
never been executed. Its first real execution found three faults, all of which only a real run could
find, and all of which failed **before an instance existed**. Nothing here is a numerical result.

Three failures, in the order they appeared.

## 1. A key with no privileges for instance operations (401, 2FA)

    {"status_code": 401, "msg": "Your key lacks proper privileges ... as it requires you to have
     logged in using Two Factor Authentication"}

**Diagnosis, and the part that made it confusing:** the same key worked for identity and licence —
`keys.sh check` returned "key belongs to scottlhawes" and "licence ACCEPTED" — and failed for **listing**
and **creating** instances. A key can be valid and still lack the privilege for instance operations.

**It was not our supply path.** `keys.sh env` emits only `TABPFN_TOKEN`, no shell rc exported
`VAST_API_KEY`, and `vast_run.sh` documents the trap: supplying the key explicitly (env var or
`--api-key`) returns this same 401, so the CLI must read `~/.config/vastai/vast_api_key` itself.

**It was not a stale value.** The file was untouched since the last successful runs. What changed was on
the account side: the key predated, or was made without, a 2FA-verified session.

**Fix:** create a new key **in the console while 2FA is verified**, store it with
`bash scripts/gpu_helpers/keys.sh add vast`, then prove it before spending:

    bash scripts/gpu_helpers/keys.sh check     # identity + licence
    vastai show instances                      # the real test for this failure

## 2. The inlined bootstrap exceeded the API's payload cap (400/3471)

    {"status_code": 400, "msg": "error 400/3471: Invalid args: len(image) > 1024, or
     len(args) > 16384, or len(label) > 256"}

The three fields named are not the fields we set. Measured: `image` 45 chars (limit 1024), `label` 12
chars (limit 256), and the onstart file ~16.5 KB against a 16384-byte limit for `args`. The error names
`args` because the server files the onstart content under that name: **the CLI sends the onstart file's
*contents*, not its path.**

`vast_run.sh` inlined `bootstrap_pilot.sh` verbatim (16,267 bytes) plus the exports and header. The
comment above that line asserted *"length is not a concern"* because `--onstart` takes a filename. That
belief was the entire reason it was considered safe, it was never tested, and the first real run
disproved it.

**Fix:** gzip+base64 the bootstrap at build time and decode on the box.

| | bytes |
| --- | --- |
| bootstrap inlined verbatim | 16,267 |
| encoded payload now | 9,392 |
| generated onstart file | 9,532 (cap 16,384) |
| headroom | 6,852 |

The decode is verified byte-identical to the original script. A guard now fails **locally and for free**
if the generated file exceeds 16,000 bytes, so the next addition to the onstart file is caught before an
offer is picked rather than by a 400 from the API.

## 3. The launcher could not select a dataset

Found before the run, by asking what would happen: `--arms` was exposed and forwarded, `--dataset` was
not, anywhere. Firing the probe would therefore have run **all four registered datasets — roughly $0.23
instead of 9p — and answered a different question than the one approved**, with nothing erroring.

**Fix:** `--dataset` now passes through `vast_run.sh` (default, option, onstart environment, SSH
transport) and the bootstrap forwards it to the runner. An empty value preserves the previous behaviour
exactly, so no existing invocation changes meaning.

## A hazard found while diagnosing: `--explain` prints your API key

`vastai create instance ... --explain` prints the prepared request **including the full
`Authorization: Bearer` header** — the live key — into the terminal. It is the fastest way to see which
field is oversized, and it is not safe to run with scrollback that is shared, pasted, or recorded. If it
runs, treat the key as exposed and rotate it.

This one is recorded because it was a real mistake, not a hypothetical: the command was handed over
without that warning.

## Cost

**Zero.** Every one of the three failures was rejected before an instance existed, and offer selection
is free. Verified afterwards with `vastai show instances --raw` → `[]`. The probe's ceiling and its
single attempt were untouched.

## What this document does not say

**It says nothing about whether fine-tuning for longer than 3 epochs helps.** No probe run record is
present among the artifacts. The per-run records in `outputs/gpu-pilot/` are the first pilot's (arms
`A_raw,B_in_domain`, 12 Sep), and the newest ledger row is that same run. If the probe produced results,
they are not in the repository — and where they landed is the next thing to establish, before anything
is read or reported.
