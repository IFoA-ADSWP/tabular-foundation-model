"""How long a paced chunk transfer needs (#701).

The container log is the transport, and its cost is the PACING, not the bandwidth: each chunk waits
`pause` seconds and is sent `repeat` times, and the payload goes round `passes` times. So the time
to complete is set by the chunk count.

Measured 2026-11-21 on the French severity capture: `__ARTIFACTS_INFO__ ... chunks=182`, sent at
20 s x 2 copies, took ~2 h to complete its first pass and ~4 h to finish both. The launcher needs
the full figure (the box reports BOOTSTRAP FINISHED only after the last pass); a re-emit needs the
first-pass figure, because the verifier is satisfied as soon as every chunk has arrived once. Pass
`--passes 1` for the latter.

    python3 scripts/gpu_helpers/transfer_minutes.py --chunks 182 --pause 20 --repeat 2 --passes 2

Prints one integer: whole minutes to complete the FIRST pass, because the verifier is satisfied as
soon as every chunk has arrived once.
"""

from __future__ import annotations

import argparse
import math


def minutes_to_complete(
    chunks: int, pause: float, repeat: int = 1, passes: int = 1, slack: float = 1.0
) -> int:
    """Minutes until the emitter has finished `passes` full sends of every chunk.

    Pass 1 alone is the completion time for a reader that needs the payload once (a re-emit);
    a launch waits for every pass, because the box reports completion only after the last one.
    """
    if chunks < 1:
        raise ValueError("chunks must be positive")
    if pause < 0:
        raise ValueError("pause must not be negative")
    if repeat < 1:
        raise ValueError("repeat must be at least 1")
    if passes < 1:
        raise ValueError("passes must be at least 1")
    seconds = chunks * pause * repeat * passes * slack
    return math.ceil(seconds / 60.0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--chunks", type=int, required=True)
    parser.add_argument("--pause", type=float, default=20)
    parser.add_argument("--repeat", type=int, default=2)
    parser.add_argument("--passes", type=int, default=2)
    parser.add_argument("--slack", type=float, default=1.0, help="multiplier for margin")
    args = parser.parse_args()
    print(minutes_to_complete(args.chunks, args.pause, args.repeat, args.passes, args.slack))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
