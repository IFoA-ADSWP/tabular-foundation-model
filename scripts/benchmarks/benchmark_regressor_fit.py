#!/usr/bin/env python3
"""Benchmark one regressor fine-tune, then size the fair test from it (#526).

    # the paid step: one fit at 10,000 rows x 30 epochs on the target GPU
    python scripts/benchmarks/benchmark_regressor_fit.py --measure \\
        --out outputs/benchmark/regressor-fit-<date>.json

    # the free step: the full matrix in GPU-hours and dollars, against the ceiling
    python scripts/benchmarks/benchmark_regressor_fit.py --estimate \\
        --measurement outputs/benchmark/regressor-fit-<date>.json \\
        --rate-per-hour 0.29 --out outputs/benchmark/regressor-fair-test-cost.json

`--measure` rents a GPU and must be released explicitly; it is precondition 2 of the
pre-registration (#501), not a free local run. `--estimate` is free and refuses to run without a
measurement: a modelled default that looks measured is the failure the cost page warns about.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from benchmark_cost import (  # noqa: E402
    CEILING_USD,
    SCHEMA_VERSION,
    Measurement,
    estimate,
)

DEFAULT_DATASET = "freMTPL2freq"
DEFAULT_TARGET = "ClaimNb"
DEFAULT_ROWS = 10_000
DEFAULT_EPOCHS = 30
DROP_COLUMNS = ("IDpol", "Exposure")


def load_frame(dataset: str, target: str, rows: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """A representative training frame: the real columns, encoded, capped at `rows`.

    Timing is about shape, not values, but the shape should be the target's: the same columns the
    fair test will hand the trainer, with categoricals code-encoded.
    """
    path = REPO_ROOT / "data" / "raw" / f"{dataset}.csv"
    if not path.exists():
        raise FileNotFoundError(f"missing dataset: {path}")
    frame = pd.read_csv(path)
    if target not in frame.columns:
        raise KeyError(f"{dataset} has no target column {target!r}")
    frame = frame.sample(n=min(rows, len(frame)), random_state=seed)
    y = frame[target].to_numpy(dtype=float)
    X = frame.drop(columns=[c for c in (*DROP_COLUMNS, target) if c in frame.columns])
    for column in X.columns:
        if not np.issubdtype(X[column].dtype, np.number):
            X[column] = X[column].astype("category").cat.codes
    return X.to_numpy(dtype=float), y


def ensure_regressor_weights() -> dict:
    """Cache the regressor checkpoint BEFORE the timer runs.

    The bootstrap's licence preflight fetches the CLASSIFIER's checkpoint, and the regressor
    has its own file (`tabpfn-v3-regressor-v3_default.ckpt`). On a cold rented box the first
    `fit()` would therefore download the checkpoint -- inside the timed region -- and the
    "fit time" would be mostly network. This is the library's own download path, so the
    licence gate and the cache layout are the ones the fit will actually use; on a warm
    cache it returns without touching the network.
    """
    from tabpfn.constants import ModelVersion
    from tabpfn.model_loading import download_model, resolve_model_path

    paths, _dirs, _names, _which = resolve_model_path(
        None, "regressor", ModelVersion.V3.value
    )
    target = Path(paths[0])
    already_cached = target.exists()
    if not already_cached:
        result = download_model(target, version=ModelVersion.V3, which="regressor")
        if result != "ok":
            raise RuntimeError(f"could not fetch {target.name}: {result}")
    return {"checkpoint": target.name, "downloaded": not already_cached}


def build_record(
    *,
    wall_seconds: float,
    rows: int,
    n_features: int,
    epochs: int,
    device: str,
    frame: str,
    seed: int,
    tabpfn_version: str,
    weights: dict,
    gpu_name: str | None = None,
) -> dict:
    """The measurement record, as data rather than a side effect of a paid fit.

    Separate from `measure()` so the producer and the verifier can be held against each other
    without a GPU: a test builds a record here and feeds it to `verify_artifacts
    --expect-measurement`. Without that, a change to this shape would first be tested by the
    next paid run, at verification, after the spend.

    `run` binds the record to the launch it came from. The verifier does not enforce it (a
    direct run on a box has no launcher), but the stamp joins the record to the ledger row and
    the GPU name is the attribution `device: "cuda"` cannot give. It is a sibling of
    `measurement`, because the cost model's `Measurement` rejects unexpected fields.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "benchmark_fit",
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "measurement": {
            "wall_seconds": round(wall_seconds, 3),
            "rows": int(rows),
            "epochs": epochs,
            "device": device,
            "tabpfn_version": tabpfn_version,
            "frame": frame,
            "seed": seed,
        },
        "config": {
            "n_features": int(n_features),
            "n_estimators_finetune": 2,
            "n_estimators_validation": 2,
            "n_estimators_final_inference": 8,
            "validation_split_ratio": 0.0,
            "early_stopping": False,
            "model_version": "V3",
        },
        # The checkpoint was fetched before the clock started; say so, so a reader can tell a
        # clean timing from one that would have included a download.
        "weights": weights,
        "run": {
            "stamp": os.environ.get("TFM_RUN_STAMP") or None,
            "commit_sha": os.environ.get("TFM_COMMIT_SHA") or None,
            "gpu_name": gpu_name,
        },
    }


def measure(
    dataset: str,
    target: str,
    rows: int,
    epochs: int,
    device: str,
    seed: int,
) -> dict:
    """Time one fine-tune. This is the step that costs money."""
    from tabpfn import __version__ as tabpfn_version
    from tabpfn.constants import ModelVersion
    from tabpfn.finetuning.finetuned_regressor import FinetunedTabPFNRegressor

    # Untimed, and first: a cold checkpoint must not make the fit look slow.
    weights = ensure_regressor_weights()
    gpu_name = None
    if device.startswith("cuda"):
        try:
            import torch

            gpu_name = torch.cuda.get_device_name(0)
        except Exception:  # attribution is useful, not a reason to lose a paid fit
            gpu_name = None
    X, y = load_frame(dataset, target, rows, seed)
    model = FinetunedTabPFNRegressor(
        device=device,
        epochs=epochs,
        random_state=seed,
        validation_split_ratio=0.0,  # the fair test's choice: the epoch budget is the budget
        early_stopping=False,
        n_estimators_finetune=2,
        n_estimators_validation=2,
        n_estimators_final_inference=8,
        model_version=ModelVersion.V3,
    )
    started = time.monotonic()
    model.fit(X, y)
    wall_seconds = time.monotonic() - started

    return build_record(
        wall_seconds=wall_seconds,
        rows=X.shape[0],
        n_features=X.shape[1],
        epochs=epochs,
        device=device,
        frame=f"{dataset}:{target}",
        seed=seed,
        tabpfn_version=tabpfn_version,
        weights=weights,
        gpu_name=gpu_name,
    )


def load_measurement(path: Path) -> Measurement:
    payload = json.loads(path.read_text())
    if payload.get("kind") != "benchmark_fit":
        raise ValueError(f"{path} is not a benchmark_fit record")
    return Measurement(**payload["measurement"])


def _fmt_table(est) -> str:
    lines = [
        f"{'arm':<12}{'fits':>6}{'s/fit':>10}{'GPU-h':>10}{'USD':>10}",
    ]
    for arm in est.arms:
        lines.append(
            f"{arm.arm:<12}{arm.fits:>6}{arm.seconds_each:>10.1f}"
            f"{arm.gpu_hours:>10.2f}{arm.usd:>10.2f}"
        )
    lines.append(
        f"{'total':<12}{est.total_fits:>6}{'':>10}"
        f"{est.total_gpu_hours:>10.2f}{est.total_usd:>10.2f}"
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--measure", action="store_true", help="run the paid benchmark fit")
    mode.add_argument("--estimate", action="store_true", help="size the fair test from a measurement")

    parser.add_argument("--out", type=Path, required=True, help="where to write the JSON record")
    parser.add_argument("--measurement", type=Path, help="measurement record (required by --estimate)")
    parser.add_argument("--rate-per-hour", type=float, help="$/GPU-hour (required by --estimate)")
    parser.add_argument("--ceiling", type=float, default=CEILING_USD, help="ceiling in USD")
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--target", default=DEFAULT_TARGET)
    parser.add_argument("--rows", type=int, default=DEFAULT_ROWS)
    parser.add_argument("--epochs", type=int, default=DEFAULT_EPOCHS)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    if args.measure:
        payload = measure(
            args.dataset, args.target, args.rows, args.epochs, args.device, args.seed
        )
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2) + "\n")
        m = payload["measurement"]
        print(f"measured {m['wall_seconds']:.1f}s for {m['rows']} rows x {m['epochs']} epochs")
        print(f"  device={m['device']} tabpfn={m['tabpfn_version']} frame={m['frame']}")
        return 0

    if args.measurement is None or args.rate_per_hour is None:
        parser.error("--estimate requires --measurement and --rate-per-hour")

    est = estimate(
        load_measurement(args.measurement),
        args.rate_per_hour,
        ceiling_usd=args.ceiling,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(est.to_dict(), indent=2) + "\n")

    print(_fmt_table(est))
    print(
        f"ceiling ${est.ceiling_usd:.2f}: "
        f"{'within' if est.within_ceiling else 'OVER'} "
        f"(headroom ${est.headroom_usd:.2f})"
    )
    for assumption in est.assumptions:
        print(f"  assumption: {assumption}")
    return 0 if est.within_ceiling else 1


if __name__ == "__main__":
    sys.exit(main())
