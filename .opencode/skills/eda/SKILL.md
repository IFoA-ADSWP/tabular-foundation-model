---
name: eda
description: 'Systematic first pass over a dataset before modelling — shape and quality, leakage (identifiers, target proxies, post-outcome fields), time-ordering, distributions and relationships, ending in ranked findings written to one registered note. Use before fitting models, when asked to explore or understand a dataset, or to produce pre-modelling findings. For schema and target readiness checks before a TabPFN run, use tabpfn-explore.'
---

# EDA

A first pass whose product is **ranked findings**, not a tour. It sits between
`tabpfn-explore` (is this dataset runnable?) and modelling (what will bite us?).
The registry is the anti-sprawl gate: one note, registered, or nothing.

## Procedure

1. **Frame** — one line: what decision will this data feed? Findings are ranked by
   threat to *that* decision.
2. **Shape and quality** — rows, columns, dtypes; missingness as *which columns and in
   what pattern*, not just counts; duplicate rows.
3. **Leakage** — identifier-like columns; target proxies; post-outcome fields that would
   not be knowable at prediction time (the local example: post-claim fields kept as
   features leak the target, tracker #216).
4. **Time-ordering** — date columns and coverage window; drift between early and late
   periods; what that implies for the split strategy.
5. **Distributions and relationships** — outliers and skew in the key columns;
   correlation with the target; class balance or target skew.
6. **Rank the findings** — leakage > drift > imbalance > structural noise, adjusted by
   what step 1 said matters. Every finding carries evidence and a recommended action.
7. **Write the note** — `docs/experiments/<campaign>/eda_<dataset>.md`:
   - status banner in the first fifteen lines (the `docs/README.md` rule);
   - findings-first and ranked; raw dumps stay in the session, not the note;
   - dedup first: search `docs/REPORT_REGISTRY.md` topic keys — a matching topic gets the
     existing report updated instead of a sibling note being born;
   - register the row when done (registry Usage §4); `model_version` is `—`, since the
     note makes no model claim.

Done when: the note is registered, findings are ranked with evidence, and open questions
are listed.

## Audit-only runs

When the ask was "look at this data" with no note requested: report the ranked findings
in the conversation and say plainly that no note was written.
