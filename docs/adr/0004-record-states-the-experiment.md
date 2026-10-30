# A record states the experiment it ran, declared beside resolved

> **Status:** accepted, 2026-10-30 · issue #238 · amends the contract in
> `docs/adr/0003-record-contract-and-model-version.md` (#241)

The pilot is about to take its experiment from the registry (#238). A record must then say
*which* experiment was named, what that experiment declared, and what the run actually
resolved — otherwise a drifted default is discovered later, or not at all.

The record contract (#241) says a record carries exactly one top-level `provenance` block
with fixed sections: dataset, split, model, code. We need a fourth kind of fact that is
none of those four: the declaration the run was asked to honour, beside the configuration
it executed.

## Decision

`provenance` gains an **optional** `experiment` section:

```json
"experiment": {"id": "coil2000_p1a", "declared": {...}, "resolved": {...}}
```

- `id` is the registry id the run named.
- `declared` is that experiment's base config, exactly as the registry states it.
- `resolved` is the config the arms executed, which may differ if a flag contradicted the
  declaration — except that #238 refuses a contradiction, so today the two agree; the pair
  exists so that cannot happen silently tomorrow.

The arm-record schema moves to **4**. The reader keeps 1, 2 and 3: `verdict` ignores
sections it does not know, so a v3 record still reads exactly as before, and a v4 record
without a named experiment omits the section rather than filling it with nulls.

## Considered options

- **A top-level `config_declared` beside `config`.** Smaller, but it puts a second
  structural exception beside the block that #240/#241 spent two tickets reducing to one.
  The next producer would then have two precedents to copy.
- **A separate record kind for declared runs.** Splits one run across two records, and a
  reader would have to join them to answer "what ran".
- **Make `experiment` required.** Refused: a run without an id has no declaration, and
  inventing nulls would state an absence as a fact. Absence is already this repo's
  vocabulary for "nothing was declared" (ADR 0001, #239).

## Consequences

- A v4 arm record can answer "declared vs resolved" without reading code, and the registry
  is the only place the declared values live.
- `verdict` is unchanged: the section is evidence, not a criterion, so it cannot move a
  record between comparable/partial/unusable.
- The frontier manifest (#243) can adopt the same section without a second decision.
- A reader that predates this ADR must tolerate the new key, which the frozen `verdict`
  already does; nothing is rewritten in place.
