# Plan — the checks that would have caught three mechanical mistakes

**Status:** Current — implemented with this change, 2026-11-23.
**Origin:** #708. The 2026-11-21/22 ladder run produced three findings that were mechanical, not
judgement.

## 1. A result note with no version and no registry row

`docstatus` checked the campaign index and passed while `REPORT_REGISTRY.md` had no row, and
nothing checked that a note citing captures names the model version it was measured on — though
`MODEL_VERSIONS.md` says a number without one is meaningless.

**The rule as written would have flagged 20 documents**, including design notes, runbooks and a
literature review the registry was never meant to carry. Measured before implementing: of 37
current notes under `docs/experiments/`, 17 cite a capture, and the tighter rule — *a current
note that cites a capture needs a version and a registry row* — flags 7. That is the rule
implemented: it matches the defect the ticket names, and it is measurable.

Two satisfiers, both explicit: a version token (`v3_default`, `v3.5_default`, …) **or** the
statement that no TabPFN arm is involved, because a baseline-only note cannot name a TabPFN
version and must not invent one.

**Grandfathering.** Three notes predate the rule and cannot name a version without asserting one
nobody recorded. They live in `docs/experiments/legacy_version_exempt.txt` — append-only, with
the same shape and the same reason as `docs/analyses/legacy_citations.txt`.

The four that could be fixed were:

| Note | Fix |
|---|---|
| `freq_sev_quantiles.md` | `v3_default`, from the campaign pre-registration's pin |
| `actuarial_baseline_summary.md` | `v3_default`, same campaign and captures |
| `row_curve_stage1.md` | registry row added; its status line already says "no TabPFN" |

## 2. Chunk pacing that outran the reader

`pause × repeat` is the seconds a chunk is visible, and the launcher polls every ~10–15 s.
Measured: `pause 5 / repeat 2 / passes 1` lost 5 of 48 chunks. `vast_run.sh` now refuses
`pause × repeat < 20` or `passes < 2` for the fair-test transport, naming the measured loss, with
`TFM_TRANSPORT_OVERRIDE=1` as the deliberate escape.

## 3. A run that could never be afforded

The floor bounded the balance and the ceiling bounded the rate; nothing compared them. The spend
gate now prints the projection (`poll_minutes / 60 × max-dph`) beside the balance and warns when
the ceiling exceeds it, naming both numbers.

## Verification

- `pytest tests/test_check_doc_status.py` — **27 passed**, including the four new acceptance cases.
- `python3 scripts/check_doc_status.py` — all three new lines pass on this tree.
- `bash -n` and `shellcheck --severity=warning` clean on `vast_run.sh`.
