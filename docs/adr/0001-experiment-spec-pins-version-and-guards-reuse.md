# Experiment spec pins the model version and guards reuse on provenance

> **Status:** accepted, 2026-10-28

An experiment's identity — dataset, seed and folds, methods, metrics, model version — is
currently declared in six code sites, and the frontier runner reuses rows from
`home_turf_sweep_results.csv` on `dataset`, `n_rows` and `n_estimators` alone: no seed, no
model version. Meanwhile `src/model_version.py` resolves the model **env-first**, so a spec
that merely called the resolver would describe a different experiment than the one it ran.
We therefore record `model_version` as a literal in the committed spec and let each run's
manifest record the value actually used, and we reuse a sweep row only when the row carries
`seed` and `model_version` matching the experiment being run.

## Considered Options

- **Reference the resolver, record the result in the manifest.** Flexible across the §15
  version re-test, but a forgotten `export` silently changes what a committed spec means —
  the failure mode `docs/MODEL_VERSIONS.md` exists to prevent.
- **Treat legacy sweep rows as seed 42 / `v3_default`.** Free reuse of all 220 existing rows,
  but it is the same class of unverified assumption that produced the bug.

## Consequences

- The first post-spec frontier run refits every method once, because the committed sweep
  rows cannot be attributed; afterwards reuse works as before.
- A version re-test means editing a committed file rather than exporting a variable. The
  edit is visible in review, which is the point.
- A row whose recorded provenance contradicts itself is a bug in the artifact, not a stale
  comment — captured in `GLOSSARY.md` under *provenance*.
