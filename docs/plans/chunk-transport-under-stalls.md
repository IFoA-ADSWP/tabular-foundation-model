# Plan — the chunked transport under a stalling poll (#566)

> **Status:** proposed 2026-11-12, after the first two live attempts at the registered fair test.
> No spend of its own.

## What happened

The fair test launched twice on 2026-11-12 and neither launch could have produced a verdict, for a
reason that is entirely in the transport:

- **Attempt 1** (`instance 60356434`, RTX 3090) was killed after 1.3 min (\$0.0045) because the
  launcher's `pick=value` chose a card class no fit time has been measured on; the protocol's only
  timing measurement is the Blackwell's 41.7 s/fit.
- **Attempt 2** (`instance 60356672`, pinned RTX PRO 4000) ran the fits fine — the box reached
  `severity_spanish`, its fourth target — and the launcher could not read them back. Its accumulator
  held **2 of 9** chunks of `frequency_french` and never saw another payload. Killed at 70 min,
  ≈\$0.30.

The measurements behind the failure, from the launcher's own temporary state:

| Observation | Value |
|---|---|
| One `vastai logs --tail 20000` call in flight | **13 min** (13:10 → 13:23) |
| `$LAUNCH_TMP/log_next.txt` at 13:57 | **0 bytes** — the poll returned nothing |
| Chunks sealed / declared, `frequency_french` | **2 / 9** |
| Longest polled line | 447 chars (`__ART__` + 440), except the last |
| The last polled line | **296 chars**, with `__ART_CHUNK_END__` glued onto it |

Two independent defects follow. A poll can stall far longer than a chunk stays in the window, and
nothing bounded it — the CLI retries internally. And the window's edge truncates a payload line and
glues the end marker on, so a naive seal would hash a mangled archive.

## Design

1. **Bound every poll.** The CLI runs as a background child; after `POLL_TIMEOUT` (45 s) it is killed
   and the next poll starts. A stalled call costs 45 s instead of 13 min, and the count of timeouts is
   reported as it happens.
2. **Primary-mode defaults sized to the window.** 2,000-line chunks with a 20 s pause put ten chunks
   in a 20,000-line window, so one chunk stays visible for ~3 min across at least three bounded
   polls.
3. **Each chunk twice.** The channel is one-way: there is no acknowledgement to retry against, so a
   second copy is the only retry available. `TFM_CHUNK_REPEAT` is policy, set by the launcher, not a
   property of the emitter.
4. **A truncated tail is dropped, not sealed.** A line containing the end marker but not starting
   with it is the window's edge; the chunk is discarded unsealed so the next copy supplies a whole
   one. A marker glued to the *start* of a payload line is split, since base64 cannot contain `_`.
5. Transfer budget: ~20 chunks × 2 copies × 20 s ≈ 13 min per target, ~50 min of transfer against
   ~50 min of fits, so ~105 min inside the existing 180 min ceiling.

## Acceptance

- A window whose first chunk ends in a truncated, glued line leaves that chunk unsealed, and the
  intact repeat seals it — `test_a_chunk_whose_end_marker_is_glued_to_a_truncated_line_is_not_sealed`.
- `TFM_CHUNK_REPEAT=2` emits every chunk twice and still restores and cites the capture —
  `test_each_chunk_is_emitted_twice_when_repeat_is_two`.
- The launcher's poll is bounded in code and the timeout count is reported; `shellcheck` covers the
  arithmetic, and the bounds are exercised on the next launch rather than in a unit test — the mock's
  log cannot stall on demand.
- `./scripts/check.sh` green.

## Not in this plan

- No change to a capture's contents, the registered matrix, the floors, or the fold/seed scheme.
- No change to the pilot or benchmark transport: their payloads fit one window and take the
  single-block path.
- The 3090 selection is a separate question (card choice should come from a measurement, not from
  `pick=value`); recorded here so it is not lost.
