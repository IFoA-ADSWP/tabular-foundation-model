# Plan — the cold read, and what it found

**Status:** Current — delivered 2026-11-08.
**Origin:** #492 on map #484, the map's acceptance test.
**Design:** a reader who has not seen the repository states the answer and its caveats from the front door
alone; every stumble is logged against the page that caused it.

## The test

Run in a fresh context that had not seen this session, with the front door as its only entry point: follow
the links the front door gives you, do not search, then answer five questions — what did the programme
conclude, what are the caveats, what is the status of transfer, which datasets were measured and which were
not, and what could you not determine.

**It is a proxy, not a human.** A fresh model context shares the model's priors and reads more forgivingly
than a person, and it is more literal about instructions. Recorded as such; a human pass would still be
worth running.

## What it could state

The conclusion, the four cells, the three readings (gain, equivalence, stopped), the within-model framing,
the transfer status ("unexecuted, not failed, and not authorised") and the reason `coil2000` was not run. On
the comprehension question the package passes.

## What it found — five defects, four fixed here

1. **`coil2000` is not a lapse dataset.** Its target is `CARAVAN` — caravan-insurance take-up — and
   `scripts/run_pilot.py` declares it plainly. The report's first sentence called all four "lapse datasets",
   and the front door repeated it. Fixed in both, with a parenthetical naming the split, and the report's
   title changed from "on lapse data" to "on insurance data".
2. **The pre-registration still claimed a checkpoint pin.** It says `v3_default` "pinned by checkpoint
   path"; the result document says that claim "is false", because the launcher could not carry a pin and
   `auto` resolved to v3. Both were current-tier. Fixed with a dated amendment at the head of the
   pre-registration — the body is left alone, because a pre-registration that edits itself after the data is
   not a pre-registration.
3. **The door said "every finding is version-pinned".** The run was resolved by `auto`, not pinned. Softened
   to "names the model version it was measured under", which is what the documents actually establish.
4. **A doubled path in `MODEL_VERSIONS.md`** — `docs/archive/archive/papers/…` — which `doclinks` misses
   because the reference carries line numbers. Fixed.
5. **The report implied δ predated everything it judged.** It was agreed on 2026-11-03, before the
   replication and both breadth cells but *after* the anchor's first pass had failed, and it was calibrated
   from R1's observed range rather than from an actuarial decision. The sentence now dates it and says what
   it followed. Not fixed, and not fixable here: who agreed δ, and why an insurer should care about 0.002,
   is not recorded anywhere the reader can reach.

## Noted but out of scope

The reader also hit an empty sign-off block in the decision log, the ledger's acknowledged unreliability, and
the Spanish cell's missing capture — all already stated in the owning documents. Those are known limitations
of the programme, not defects in the presentation, and changing them is not this map's job.

## Verification

```sh
./scripts/check.sh
```

Run on 2026-11-08. The cold read is repeated in a second fresh context once these fixes land, and its result
is recorded on the ticket rather than assumed.

## What this does not do

It does not add the figure the report still lacks, move any document between tiers, or settle the pilot's
disposition. It does not substitute a model for a human reader, and says so in the resolution.
