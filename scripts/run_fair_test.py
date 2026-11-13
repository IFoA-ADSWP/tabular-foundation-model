#!/usr/bin/env python3
"""Produce a regressor fair-test run (#539).

    python scripts/run_fair_test.py --out-root results --device cuda

The sizes come from the pre-registration. `--smoke` shrinks them to a CPU-sized run that writes a
real capture — useful to prove the wiring, never a result to quote.

`--methods` selects the predictors. The default is the TabPFN fair test; the actuarial baseline
(#597) is `--methods E_glm,F_catboost,M_intercept`, which runs on CPU and spends nothing:

    python scripts/run_fair_test.py --methods E_glm,F_catboost,M_intercept \\
        --targets frequency_french --out-root /tmp/baseline

A TabPFN launch rents a machine on its own: a real run is a paid launch and a separate decision.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from baselines import BACKENDS  # noqa: E402
from fair_test_runner import (  # noqa: E402
    ARMS,
    DEFAULT_METHODS,
    METHODS,
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
    parser.add_argument(
        "--run-id-offset",
        type=int,
        default=0,
        help=(
            "seconds added to the run id. One process per target needs distinct ids, and this "
            "keeps the runner's own scheme (_run_ids offsets by one second per target) instead "
            "of doing date arithmetic in the launch script"
        ),
    )
    parser.add_argument("--device", default="cuda")
    parser.add_argument(
        "--train-rows",
        type=int,
        default=None,
        help=(
            "rows every arm trains on, overriding the 10,000-row budget in the Arm declaration. "
            "Applies to the control too: the fair test compares arms at a matched context (#572)"
        ),
    )
    parser.add_argument(
        "--targets",
        default=None,
        help=(
            "comma-separated target names (frequency_french, frequency_spanish, "
            "severity_french, severity_spanish); default all"
        ),
    )
    parser.add_argument(
        "--arms",
        default=None,
        help=(
            "comma-separated arms (A_raw, B_ft30, B_ft10, B_ft3); default every registered arm. "
            "The fair test is authorised for the primary pair only (#564), so a launch passes "
            "'A_raw,B_ft30' rather than editing the default"
        ),
    )
    parser.add_argument(
        "--methods",
        default=None,
        help=(
            "comma-separated methods (tabpfn, E_glm, F_catboost, M_intercept); default tabpfn. "
            "The actuarial baseline (#597) is 'E_glm,F_catboost,M_intercept': a baseline is a "
            "method, not an Arm, so it is never named with --arms"
        ),
    )
    parser.add_argument(
        "--folds",
        type=int,
        default=None,
        help=(
            "fold count; default 5. A timing measurement runs one fold per target before the "
            "matrix (#597), and one fold is a measurement, never a result"
        ),
    )
    parser.add_argument(
        "--seeds",
        default=None,
        help="comma-separated model seeds; default 0,1,2",
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
    if args.smoke and (args.folds is not None or args.seeds is not None):
        parser.error("--smoke fixes the fold count and seeds; do not pass --folds or --seeds")

    methods = DEFAULT_METHODS
    if args.methods:
        wanted_methods = tuple(name.strip() for name in args.methods.split(","))
        unknown_methods = [name for name in wanted_methods if name not in METHODS]
        if unknown_methods:
            parser.error(f"unknown method(s): {', '.join(unknown_methods)}")
        if not wanted_methods:
            parser.error("--methods is empty; omit it for the TabPFN fair test")
        methods = wanted_methods

    arms = tuple(ARMS)
    if args.arms:
        if "tabpfn" not in methods:
            parser.error(
                "--arms names the TabPFN ladder, but --methods selects no tabpfn method; "
                "name the baseline in --methods instead"
            )
        wanted_arms = tuple(name.strip() for name in args.arms.split(","))
        unknown_arms = [name for name in wanted_arms if name not in ARMS]
        if unknown_arms:
            parser.error(f"unknown arm(s): {', '.join(unknown_arms)}")
        if not wanted_arms:
            parser.error("--arms is empty; omit it for every registered arm")
        arms = wanted_arms

    caps: dict[str, int] = {}
    if args.gate:
        if "tabpfn" not in methods:
            parser.error(
                "--gate measures the TabPFN ladder against itself; select the tabpfn method"
            )
        # The gate matches the Run's statistic: five folds, both Arms, and the same three model
        # seeds per fold. That is 120 fits, and it is the only way `SD_fold(r)` predicts the fair
        # test's variance rather than a single-seed upper bound (#555).
        config = RunConfig(
            folds=5, seeds=(0, 1, 2), targets=selected, arms=("A_raw", "B_ft30")
        )
    elif args.smoke:
        config = RunConfig(
            folds=1, seeds=(0,), test_rows=64, targets=selected, arms=arms, methods=methods
        )
        caps = {"train_rows_cap": 128, "epochs_cap": 2}
    else:
        seeds = (0, 1, 2)
        if args.seeds:
            try:
                seeds = tuple(int(value) for value in args.seeds.split(","))
            except ValueError:
                parser.error(f"--seeds {args.seeds!r} is not a comma-separated list of integers")
            if not seeds:
                parser.error("--seeds is empty")
        folds = 5 if args.folds is None else args.folds
        if folds < 1:
            parser.error("--folds must be at least 1")
        config = RunConfig(folds=folds, seeds=seeds, targets=selected, arms=arms, methods=methods)

    backends = {
        name: TabPFNBackend(device=args.device) if name == "tabpfn" else BACKENDS[name]()
        for name in methods
    }
    base = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    try:
        base = (
            datetime.strptime(base, "%Y%m%dT%H%M%SZ")
            + timedelta(seconds=args.run_id_offset)
        ).strftime("%Y%m%dT%H%M%SZ")
    except ValueError:
        parser.error(
            f"--run-id {args.run_id!r} is not a run id (YYYYMMDDTHHMMSSZ); "
            "the capture's directory name is what the citation check resolves"
        )
    if args.train_rows is not None:
        caps["train_rows"] = args.train_rows
    runs = run(config, backends, args.out_root, run_id=base, **caps)
    for target, run_dir in runs.items():
        print(f"{target}: {run_dir}  ({run_dir / 'capture.json'})")
    if args.gate:
        summary = gate_summary(runs)
        base = next(iter(runs.values())).name
        gate_path = args.out_root / f"resolution_gate_{base}.json"
        gate_path.write_text(json.dumps(summary, indent=2) + "\n")
        print(f"gate -> {gate_path}")
        for target, row in summary.items():
            print(
                f"  {target:<18} r={row['mean_improvement']:+.2%} "
                f"sd={row['sd_r']:.4f} mde={row['mde']:.2%}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
