#!/usr/bin/env python3
"""Produce a regressor fair-test run (#539).

    python scripts/run_fair_test.py --out-root results --device cuda

The sizes come from the pre-registration. `--smoke` shrinks them to a CPU-sized run that writes a
real capture — useful to prove the wiring, never a result to quote.

This rents nothing on its own: a real run is a paid launch and a separate decision.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from fair_test_runner import (  # noqa: E402
    TARGETS,
    RunConfig,
    TabPFNBackend,
    gate_summary,
    run,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-root", type=Path, default=_REPO / "results")
    parser.add_argument("--run-id", default=None, help="default: the UTC start time")
    parser.add_argument("--device", default="cuda")
    parser.add_argument(
        "--targets",
        default=None,
        help=(
            "comma-separated target names (frequency_french, frequency_spanish, "
            "severity_french, severity_spanish); default all"
        ),
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="1 fold, 1 seed, 64 test rows, 128 train rows, at most 2 epochs (CPU, minutes)",
    )
    parser.add_argument(
        "--gate",
        action="store_true",
        help=(
            "resolution gate: A_raw on the five folds of every selected target, then the "
            "fold-level SD and the 80%-power MDE; writes resolution_gate_<run id>.json"
        ),
    )
    args = parser.parse_args(argv)

    selected = TARGETS
    if args.targets:
        wanted = {name.strip() for name in args.targets.split(",")}
        selected = tuple(target for target in TARGETS if target.name in wanted)
        unknown = wanted - {target.name for target in selected}
        if unknown:
            parser.error(f"unknown target(s): {', '.join(sorted(unknown))}")

    if args.gate and args.smoke:
        parser.error("--gate and --smoke describe different runs; pick one")

    caps: dict[str, int] = {}
    if args.gate:
        # The gate is A_raw alone on the real five folds and one seed: twenty in-context fits,
        # which is what the pre-registration prices as the pre-spend step (#552).
        config = RunConfig(folds=5, seeds=(0,), targets=selected, arms=("A_raw",))
    elif args.smoke:
        config = RunConfig(folds=1, seeds=(0,), test_rows=64, targets=selected)
        caps = {"train_rows_cap": 128, "epochs_cap": 2}
    else:
        config = RunConfig(targets=selected)

    backend = TabPFNBackend(device=args.device)
    runs = run(config, backend, args.out_root, run_id=args.run_id, **caps)
    for target, run_dir in runs.items():
        print(f"{target}: {run_dir}  ({run_dir / 'capture.json'})")
    if args.gate:
        summary = gate_summary(runs)
        base = next(iter(runs.values())).name
        gate_path = args.out_root / f"resolution_gate_{base}.json"
        gate_path.write_text(json.dumps(summary, indent=2) + "\n")
        print(f"gate -> {gate_path}")
        for target, row in summary.items():
            print(f"  {target:<18} mean={row['mean']:.4f} sd={row['sd']:.4f} mde={row['mde']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
