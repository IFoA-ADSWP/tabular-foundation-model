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
| Gap between two polls | **11 min 50 s** (13:10:51 → 13:22:41) |
| What the machine was doing in that gap | **asleep** — `pmset -g log`: `Sleep` 13:10:51, `Wake` 13:22:41 |
| Chunks sealed / declared, `frequency_french` | **2 / 9** |
| Longest polled line | 447 chars (`__ART__` + 440), except the last |
| The last polled line | **296 chars**, with `__ART_CHUNK_END__` glued onto it |

**The 13-minute "stall" was the laptop, not the API.** `pmset -g log` shows it sleeping at 13:10:51
and waking at 13:22:41, and repeatedly after that (13:32, 13:47, 13:58, 14:15, 14:24). While the
machine is suspended the poller does not run, the box keeps emitting, and every chunk emitted in the
gap scrolls out of the window. The first reading of this evidence — "the CLI retries internally for
minutes" — was wrong, and it matters: a timeout bounds a slow call, but nothing in the process can
bound a suspend.

Two independent defects follow. The receiver must not be asleep for the duration (the fix is to hold
the machine awake, and to say so loudly when a gap appears). And the window's edge truncates a payload
line and glues the end marker on, so a naive seal would hash a mangled archive.

## Design

1. **Hold the machine awake, and detect when it did not.** The launch runs under `caffeinate -dimsu`;
   a launch that starts without one is warned, and the poll loop compares wall-clock between
   iterations and reports every gap over 3 minutes as a suspension. A timeout is kept as well
   (`POLL_TIMEOUT`, 45 s) because a slow API call is a separate, real failure — but it is not the one
   that lost the run.
2. **Primary-mode defaults sized to the window.** 2,000-line chunks with a 20 s pause put ten chunks
   in a 20,000-line window, so one chunk stays visible for ~3 min across at least three bounded
   polls.
3. **Each chunk twice.** The channel is one-way: there is no acknowledgement to retry against, so a
   second copy is the only retry available. `TFM_CHUNK_REPEAT` is policy, set by the launcher, not a
   property of the emitter.
4. **A truncated tail is dropped, not sealed.** A line containing the end marker but not starting
   with it is the window's edge; the chunk is discarded unsealed so the next copy supplies a whole
   one. A marker glued to the *start* of a payload line is split, since base64 cannot contain `_`.
5. **The window is 8,000 lines, because the API will not serve more.** Measured on the canary's
   ~45,000-line log: `--tail 500` in 3 s, `2,100` in 4 s, `5,000` in 4 s, `8,000` in 4 s, `10,000` in
   5 s — and `12,000`, `16,000` and `20,000` all fail with `Result not ready after 9.0s`. The CLI
   gives the API nine seconds and no more, so 10,000 lines is the hard ceiling and 8,000 leaves
   margin. The default 20,000 was above it, which is why the canary sealed 2 chunks of 20 before
   every poll started returning nothing.
6. Transfer budget: ~27 chunks × 2 copies × 20 s ≈ 18 min per target, ~72 min of transfer against
   ~50 min of fits, so ~125 min inside the existing 180 min ceiling.

## Acceptance

- A window whose first chunk ends in a truncated, glued line leaves that chunk unsealed, and the
  intact repeat seals it — `test_a_chunk_whose_end_marker_is_glued_to_a_truncated_line_is_not_sealed`.
- `TFM_CHUNK_REPEAT=2` emits every chunk twice and still restores and cites the capture —
  `test_each_chunk_is_emitted_twice_when_repeat_is_two`.
- The launcher warns when nothing holds the machine awake, and reports each multi-minute gap between
  polls as a suspension; `shellcheck` covers the arithmetic. Neither is unit-tested — the mock cannot
  sleep on demand — so both are proven by the next launch, and only by it.
- `./scripts/check.sh` green.

## Not in this plan

- No change to a capture's contents, the registered matrix, the floors, or the fold/seed scheme.
- No change to the pilot or benchmark transport: their payloads fit one window and take the
  single-block path.
- The 3090 selection is a separate question (card choice should come from a measurement, not from
  `pick=value`); recorded here so it is not lost.
