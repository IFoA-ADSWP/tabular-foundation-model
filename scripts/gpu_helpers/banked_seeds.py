#!/usr/bin/env python3
"""Which seeds in a range are banked, and which are still missing (#430).

WHY THIS EXISTS. The 2026-11-04/05 campaign drove a fixed queue of batches. When a batch died
the queue moved on, so its range was never measured; when a batch wrote another range's seeds
the queue also moved on, and the range it *thought* it had covered stayed missing. Both were
invisible until someone diffed the run directories against the design, and a quarter of the
spend bought nothing.

The fix is to stop treating a plan as the queue: ask the run directories what is banked, and
launch what is missing. This is that question, in one place.

WHAT "BANKED" MEANS. A seed is banked when a `meta.json` under the runs tree records it for
EVERY expected `(dataset, arm)` pair. The reader is `verify_artifacts.written_seeds`, which
#429 already uses to prove a batch wrote the seeds it was asked for; a second walk of the tree
here would be a second definition of "written", and the two would drift the first time either
learned something (a string seed, a fold that writes several metas for one seed).

WHICH LAUNCHES COUNT. Each launch directory is accepted or skipped whole, by the manifest the
box wrote into it (`manifest_<run_id>.json`):

- `dry_run: true` -> skipped. A mock costs nothing, so it measured nothing, and counting one
  would let a smoke test report COMPLETE over a range nobody ran.
- `--train-size` / `--test-size`, when given, must match the manifest. A row count is part of
  the design: the campaign scans 2,000 -> 10,000 rows, and a seed measured at one size must not
  retire the other.

THE LIMIT, STATED. The model line, the commit and the config are NOT compared, and a launch
that returned no manifest is counted when no size was asked for (that is every run from before
the manifest was returned). So point `--runs-dir` at the campaign's own tree; this answers
"which seeds have I banked here", not "is this evidence commensurable with today's run".

Usage:
    banked_seeds.py --runs-dir runs/ --seeds 225-236 \
                    --dataset eudirectlapse --arms A_raw,B_ft30 \
                    [--train-size 10000 --test-size 10000]

Output (stable, one fact per line, so a shell caller does not have to parse prose):
    PAIRS eudirectlapse/A_raw,eudirectlapse/B_ft30
    SKIPPED 20261105T101500Z (dry run: zero cost, not evidence)
    BANKED 4/12
    MISSING 229-236
    GAP eudirectlapse/B_ft30: 237-240       # one line per pair that is behind

Exit codes:
    0  every requested seed is banked for every pair
    1  seeds are missing
    2  usage error
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from verify_artifacts import parse_seeds, seed_ranges, written_seeds  # noqa: E402


def csv_list(value: str) -> list[str]:
    """`a,b` -> `['a', 'b']`, refusing an empty or blank entry rather than dropping it."""
    items = [item.strip() for item in value.split(",")]
    if not items or any(not item for item in items):
        raise ValueError(f"empty entry in {value!r}")
    return items


def launch_manifest(path: str) -> dict | None:
    """The box's own manifest for one launch directory, if it came back."""
    try:
        names = sorted(
            name
            for name in os.listdir(path)
            if name.startswith("manifest_") and name.endswith(".json")
        )
    except OSError:
        return None
    for name in names:
        try:
            with open(os.path.join(path, name)) as f:
                return json.load(f)
        except (OSError, ValueError):
            continue
    return None


def skip_reason(manifest: dict | None, want: dict) -> str | None:
    """Why this launch's tree must not bank anything, or None if it counts."""
    if manifest is None:
        # Without a manifest there is nothing to attest, so a size filter cannot accept it --
        # but with no filter asked for, it counts, as every pre-manifest run does.
        return "no manifest returned: cannot attest the design" if want else None
    if manifest.get("dry_run") is True:
        return "dry run: zero cost, not evidence"
    for key, wanted in want.items():
        got = manifest.get(key)
        if got != wanted:
            return f"{key} {got!r} is not {wanted!r}"
    return None


def banked_groups(runs_dir: str, want: dict) -> tuple[
    dict[tuple[str, str], set[int]], list[tuple[str, str]]
]:
    """Every `(dataset, arm)` -> the seeds its accepted launches wrote, plus what was skipped."""
    groups: dict[tuple[str, str], set[int]] = {}
    skipped: list[tuple[str, str]] = []
    try:
        names = sorted(os.listdir(runs_dir))
    except OSError:
        return groups, skipped
    for name in names:
        path = os.path.join(runs_dir, name)
        if not os.path.isdir(path):
            continue
        reason = skip_reason(launch_manifest(path), want)
        if reason is not None:
            skipped.append((name, reason))
            continue
        for key, seeds in written_seeds(path).items():
            groups.setdefault(key, set()).update(seeds)
    return groups, skipped


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Report which seeds of a range are banked in a runs tree (#430)"
    )
    ap.add_argument("--runs-dir", required=True, help="directory holding one subdir per launch")
    ap.add_argument(
        "--seeds",
        required=True,
        help="the seed range under design, as a comma list and/or ranges (225-236)",
    )
    ap.add_argument("--dataset", required=True, help="dataset name, or a comma list of them")
    ap.add_argument("--arms", required=True, help="arm name, or a comma list of them")
    ap.add_argument(
        "--train-size",
        type=int,
        help="training rows the design uses; a launch at another size does not bank",
    )
    ap.add_argument(
        "--test-size",
        type=int,
        help="test rows the design uses; a launch at another size does not bank",
    )
    args = ap.parse_args()

    try:
        requested = parse_seeds(args.seeds)
        datasets = csv_list(args.dataset)
        arms = csv_list(args.arms)
    except ValueError as e:
        print(f"USAGE: {e}")
        return 2

    want = {
        key: value
        for key, value in (("train_size", args.train_size), ("test_size", args.test_size))
        if value is not None
    }
    pairs = [(dataset, arm) for dataset in datasets for arm in arms]
    groups, skipped = banked_groups(args.runs_dir, want)

    requested_set = set(requested)
    banked: set[int] = set(requested_set)
    gaps: list[tuple[str, str, list[int]]] = []
    for dataset, arm in pairs:
        present = groups.get((dataset, arm), set()) & requested_set
        banked &= present
        behind = sorted(requested_set - present)
        if behind:
            gaps.append((dataset, arm, behind))

    print("PAIRS " + ",".join(f"{dataset}/{arm}" for dataset, arm in pairs))
    for stamp, reason in skipped:
        print(f"SKIPPED {stamp} ({reason})")
    print(f"BANKED {len(banked)}/{len(requested)}")
    print(f"MISSING {seed_ranges(sorted(requested_set - banked))}")
    for dataset, arm, behind in gaps:
        print(f"GAP {dataset}/{arm}: {seed_ranges(behind)}")

    return 0 if banked == requested_set else 1


if __name__ == "__main__":
    sys.exit(main())
