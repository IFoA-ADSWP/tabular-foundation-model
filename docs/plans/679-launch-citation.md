# Plan — the citation gate accepts a committed launch tree

**Status:** Proposed — issue #679 (raises a rule change; needs a maintainer's sign-off).
**Scope:** `scripts/check_citations.py` and its tests, and one line in the plans index. It moves no
record, adds no capture, and changes no number.

## Why

The citation rule (#364) knows one evidence form: a run cited in `docs/` must have
`results/<id>/capture.json` covering every arm × seed, and an id from before 2026-10-31 may be
exempt in `docs/analyses/legacy_citations.txt`. That file is deliberately closed to newer ids,
because grandfathering a new citation is the failure the rule exists to prevent.

#678 makes the runs ledger read the 2026-11-21 ladder's launch records, and the ledger's `run_id`
column is the Run directory's name. Those 15 Runs were banked under
`outputs/gpu-pilot/runs/<id>/` in #677 and have no `results/` capture — they are `no-capture` rows,
cited by description, exactly as the ledger's older 2026-09-14 launch is. The older launch is
exempt only because it predates the rule. The ladder does not, so the ledger cannot be published
without either a rule that names this evidence form or a way around the gate, and there is no
honest way around it: the run id appears in the CSV's `run_id` and `source` columns whether the
gate likes it or not.

## What the rule was, and what it becomes

Was: a cited run must have `results/<id>/capture.json`, or predate 2026-10-31 and be listed in
`legacy_citations.txt`.

Becomes: a cited run must have `results/<id>/capture.json`, **or** its committed launch tree at
`outputs/gpu-pilot/runs/<id>/` with a `meta.json` per arm × seed, **or** be pre-rule exempt.

## The limits, which the tests pin

1. **No fallback when a capture exists but is broken.** A present `capture.json` is checked and its
   verdict stands; a good record tree beside it is not a licence to read the tree instead.
2. **Every record must name a seed.** The tree's records are read and each is refused if its
   `seed` is missing or it does not parse — a tree of unlabelled files is not evidence.
3. **An empty tree fails.** A directory with no `meta.json` under it is refused, as is a cited id
   with no tree at all.
4. **A launch tree is not a Capture.** The ledger still labels these rows `no-capture`, the check's
   wording never calls the tree a capture, and `DOCUMENT_AUTHORITY.md`'s rule stands: with no
   capture the number resolves to the document that owns the subject. The tree proves the citation
   is not a phantom id; it does not make the number a captured one.

Coverage across the whole launch stays the ledger's assertion, not this check's: one Run here is a
slice of a ladder, and the gate does not know the ladder's intended size.

## What changes

- `scripts/check_citations.py` — `check_run` tries the capture first, else a new
  `check_launch_tree`; `check_run_dir` is unchanged, so the paid path's verifier and the transport
  tests keep their interface.
- `tests/test_check_citations.py` — a launch-tree-only citation is accepted, a record with no seed
  is refused, and a broken capture beside a launch tree still fails.
- `docs/plans/README.md` — this plan listed in the index.

## Verification

```
.venv/bin/pytest tests/test_check_citations.py -q
PATH="$PWD/.venv/bin:$PATH" ./scripts/check.sh citation
```

On this branch alone the citation check is green and unchanged for every existing citation: no
committed document cites a launch-tree-only run yet. #678 is what makes the new form load-bearing,
and its PR depends on this one.
