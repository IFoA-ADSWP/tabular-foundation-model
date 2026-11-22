"""The run ids a fair-test launch writes, one per target (#568).

`run_fair_test.py --run-id <stamp> --run-id-offset <i>` names a target's capture directory
`<stamp> + i seconds`: the runner's own `_run_ids` would have named them `<stamp>+0..3` inside one
process. Three places have to agree on that rule — the target loop that fits, the on-box check that
decides whether a target is already sealed, and the operator's `--fairtest reemit`. They share this
function so a change to the scheme cannot leave a sealed capture unrecognised.

    python3 scripts/gpu_helpers/fairtest_run_ids.py --stamp 20261121T120000Z --count 4
    python3 scripts/gpu_helpers/fairtest_run_ids.py --stamp 20261121T120000Z --offset 2
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta

STAMP_FORMAT = "%Y%m%dT%H%M%SZ"


def run_ids(stamp: str, count: int) -> list[str]:
    """`stamp`, then one per second after it, in target order."""
    start = datetime.strptime(stamp, STAMP_FORMAT)
    return [
        (start + timedelta(seconds=offset)).strftime(STAMP_FORMAT)
        for offset in range(count)
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--stamp", required=True, help="the launch's TFM_RUN_STAMP")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--count", type=int, help="how many target ids to print, one per line")
    group.add_argument("--offset", type=int, help="print only the id at this target offset")
    args = parser.parse_args()

    if args.offset is not None:
        print(run_ids(args.stamp, args.offset + 1)[args.offset])
        return 0
    for run_id in run_ids(args.stamp, args.count):
        print(run_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
