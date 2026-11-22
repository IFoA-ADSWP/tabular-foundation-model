# Plan — #708: the checks that would have caught tonight's three mistakes

**Status:** Current — issue #708.
**Scope:** `check_doc_status.py` and the launcher's spend gate.

## Why

Three findings from the 2026-11-21/22 ladder run were mechanical, not judgement:

- a result note shipped with **no model version** and **no registry row**, and `docstatus` passed;
- a launch run with `pause 5 / repeat 2 / one pass` lost **5 of 48 chunks** and needed a recovery;
- a launch projected **582 minutes** while the balance was **$3.70**.

## What changes

- `scripts/check_doc_status.py`: a **current** note under `docs/experiments/**` that cites a run id
  or a `results/` path must name a model version and have a `REPORT_REGISTRY.md` row. Measured on
  `main` before landing: 9 such notes, 1 missing a version, 1 missing a row — both fixed here.
- `vast_run.sh`: refuse `pause × repeat < 20 s`, and refuse `passes < 2`, for the fair-test
  transport, unless `TFM_ALLOW_FAST_CHUNKS=1` / `TFM_ALLOW_SINGLE_PASS=1` say so deliberately.
- `vast_run.sh`: at the spend gate, compare the projected ceiling cost with the available credit and
  warn with both numbers.

## Decisions

- **Mechanical over a rule.** Each of the three is deterministic; a review finding that can be a red
  check should be one.
- **Scope the version check to notes that cite evidence.** Notes that cite nothing are design,
  literature or runbooks; forcing a version on them would be noise. The registry check uses the same
  scope.
- **Warn, do not refuse, on the credit projection.** Credit may be topped up mid-run; the operator
  needs the numbers, not a block.

## Verification

```bash
.venv/bin/pytest tests/test_launch_ceilings.py -q
./scripts/check.sh
```
