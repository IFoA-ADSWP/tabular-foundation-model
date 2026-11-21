"""How long a paced chunk transfer needs (#701).

The container log is the transport, and its cost is the PACING, not the bandwidth: each chunk waits
`pause` seconds and is sent `repeat` times, and the payload goes round `passes` times. So the time
to complete is set by the chunk count.

Measured 2026-11-21 on the French severity capture: `__ARTIFACTS_INFO__ ... chunks=182`, sent at
20 s x 2 copies, took ~2 h to complete its first pass. A ceiling sized from the target count
(15 + 30 per target = 45 min) could not cover that; this function is what the re-emit driver uses
instead, once the box declares how many chunks it has.

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
    """Minutes until every chunk has been sent at least once.

    `passes` is accepted but does not multiply the answer: a pass repeats the whole payload, and
    the first pass already carries every chunk. It is validated so a caller cannot pass a value
    that would make the estimate quietly wrong.
    """
    if chunks < 1:
        raise ValueError("chunks must be positive")
    if pause < 0:
        raise ValueError("pause must not be negative")
    if repeat < 1:
        raise ValueError("repeat must be at least 1")
    if passes < 1:
        raise ValueError("passes must be at least 1")
    seconds = chunks * pause * repeat * slack
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
