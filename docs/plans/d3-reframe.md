# Plan — D3's control, and the boundary of what is free (#304)

**Status:** Current — implementing 2026-10-30.
**Origin:** ticket #304 under campaign spec #300.
**Design:** `docs/current/FINETUNING_DIAGNOSTICS_DESIGN.md` §D3 · **Record shape:** ADR 0003.

## What this ticket can and cannot do for free

The design calls D3 "analysis only, $0". That is true for **`spanish_motor_freq`**, whose reframe is
already committed as §14.14 evidence. It is not true for the three untouched datasets: the reframe
runner fits nine methods per task through the **hosted TabPFN client**, so reframing a new dataset
spends money. The ticket's own instruction is to stop and report rather than spend, so this change
delivers the part that is free and refuses the part that is not.

## Delivered here

`scripts/diagnostics/d3_reframe.py`, in two modes:

1. **`--control`** reads the committed reframe evidence, computes per-method mean AUC over folds and
   seeds, ranks them, and writes one record per task. It asserts §14.14's claim — TabPFN at AUC rank
   #1 — and exits non-zero if the reading does not reproduce it. That is the ticket's first
   acceptance item, and it is the check every later flip depends on.
2. **`--dataset NAME`** refuses, before writing anything, and names the measured cost floor. A
   refusal that does not quote a number is a shrug, so the message carries `$0.0368` — the measured
   four-arm run — and says it is a floor, not an estimate.

## Why the control is built to fail

A control that cannot fail is decoration. The test suite includes a fixture where a rival beats
TabPFN; it must produce `reproduced: false`, rank 2, and a non-zero exit. The real evidence is then
a second data point for the same code path, not a special case.

## Not delivered — and why

The three untouched datasets (`freMTPL2freq`, `norauto`, `bemtl16`) need paid fits. Their cost has
not been measured, only floored, and the ticket says to stop rather than spend. Recorded on the
ticket with the estimate so the next session can decide with a number in front of it.

## Verification

- `./scripts/check.sh` green.
- A record per task from committed evidence, hash matching the evidence file.
- A flipped fixture yields `reproduced: false` and a non-zero exit.
- `--dataset` refuses without creating a directory.
