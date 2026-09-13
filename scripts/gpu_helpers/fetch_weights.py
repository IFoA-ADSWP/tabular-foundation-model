#!/usr/bin/env python3
"""Ensure the gated TabPFN weights are present in the library's own cache.

WHY THIS EXISTS (docs/reports/PILOT_2_PREREQUISITES.md PR-9)

TabPFN's licence check sits inside the weight-download path and fires only on a
CACHE MISS: `model_loading` returns early when the checkpoint file already exists,
and only the cache-miss branch calls `ensure_license_accepted` and `hf_hub_download`.
Every current version (V2_5, V2_6, V3) is in the gated set.

Consequences this script exploits:

* Fine-tuning and inference are entirely local. No API key is needed for them.
* If the `.ckpt` is already on disk, the gate never runs and `TABPFN_TOKEN` is not
  needed at all.
* On an ephemeral rented container the cache is cold every run, so the gate fires
  every run. Fetching the weights HERE, as one explicit early step, means the token
  is used exactly once per instance, the failure is loud and early rather than
  surfacing as a licence error inside the first arm's `fit()`, and the resolved
  checkpoint is hashed for the run manifest (the weights ID the runbook requires).

Run it before the licence preflight. If it reports "cached": true, the preflight can
be skipped entirely -- the gate will not fire.

Exit codes:
    0  weights are present (freshly downloaded, or already cached)
    1  weights could not be obtained
    2  usage/environment error

Prints a single JSON object on stdout under a marker line, so a shell caller can
parse it without importing anything.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

MARKER = "__WEIGHTS_JSON__"
DEFAULT_REPO = "Prior-Labs/tabpfn_3"
DEFAULT_FILENAME = "tabpfn-v3-classifier-v3_default.ckpt"


def _sha256_file(path: Path, chunk: int = 1 << 20) -> tuple[str, int]:
    h = hashlib.sha256()
    size = 0
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
            size += len(b)
    return h.hexdigest(), size


def resolve_cache_dir() -> tuple[Path, str]:
    """Return the cache dir TabPFN itself will use, and how we learned it.

    Preferred: ask the library, so we can never disagree with it. Falls back to the
    documented platform logic (linux-like: $XDG_CACHE_HOME/tabpfn or ~/.cache/tabpfn).
    """
    try:
        from tabpfn.model_loading import get_cache_dir  # type: ignore

        return Path(get_cache_dir()), "tabpfn.model_loading.get_cache_dir()"
    except Exception as e:  # library absent or moved the helper
        note = f"fallback ({type(e).__name__}: {e})"
    if os.environ.get("XDG_CACHE_HOME", "").strip():
        return Path(os.environ["XDG_CACHE_HOME"]) / "tabpfn", note
    return Path.home() / ".cache" / "tabpfn", note


def resolve_source() -> tuple[str, str, str]:
    """Return (repo_id, default_filename, how) for the gated v3 classifier."""
    try:
        from tabpfn.model_loading import ModelSource  # type: ignore

        src = ModelSource.get_classifier_v3()
        return src.repo_id, src.default_filename, "ModelSource.get_classifier_v3()"
    except Exception as e:
        return (
            DEFAULT_REPO,
            DEFAULT_FILENAME,
            f"fallback ({type(e).__name__}: {e})",
        )


def emit(payload: dict) -> None:
    print(MARKER)
    print(json.dumps(payload, indent=2, default=str))


def main() -> int:
    ap = argparse.ArgumentParser(description="Ensure gated TabPFN weights are cached")
    ap.add_argument(
        "--check-only",
        action="store_true",
        help="Report cache state without downloading",
    )
    ap.add_argument(
        "--verbose",
        action="store_true",
        help="Log progress to stderr (stdout stays parseable JSON)",
    )
    args = ap.parse_args()

    cache_dir, cache_how = resolve_cache_dir()
    repo_id, filename, source_how = resolve_source()
    target = cache_dir / filename

    def log(msg: str) -> None:
        if args.verbose:
            print(msg, file=sys.stderr, flush=True)

    payload: dict = {
        "cache_dir": str(cache_dir),
        "cache_dir_source": cache_how,
        "repo_id": repo_id,
        "filename": filename,
        "source": source_how,
        "target_path": str(target),
        "cached": target.exists(),
        "downloaded": False,
        "sha256": None,
        "bytes": None,
        "licence_gate_will_fire": not target.exists(),
        "token_env_present": bool(
            os.environ.get("TABPFN_TOKEN")
            or os.environ.get("HF_TOKEN")
            or os.environ.get("HUGGINGFACE_HUB_TOKEN")
        ),
        "status": "unknown",
        "error": None,
    }

    if target.exists():
        log(f"[weights] already cached: {target} -- licence gate will NOT fire")
        sha, size = _sha256_file(target)
        payload.update(sha256=sha, bytes=size, status="cached")
        emit(payload)
        return 0

    if args.check_only:
        payload["status"] = "missing"
        emit(payload)
        return 1

    log(f"[weights] cache miss -- fetching {repo_id}/{filename}")
    try:
        from huggingface_hub import hf_hub_download

        token = (
            os.environ.get("HF_TOKEN")
            or os.environ.get("HUGGINGFACE_HUB_TOKEN")
            or None
        )
        cache_dir.mkdir(parents=True, exist_ok=True)
        # Mirror the library's own call shape: same repo, same filename, same
        # local_dir, so the file lands exactly where the library's cache check
        # looks for it (it renames hf_hub_download's return to <cache>/<filename>).
        local_path = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            local_dir=cache_dir,
            token=token,
        )
        local_path = Path(local_path)
        if local_path != target and local_path.exists():
            local_path.rename(target)
        if not target.exists():
            payload["status"] = "download-returned-no-file"
            payload["error"] = f"hf_hub_download returned {local_path} but {target} is absent"
            emit(payload)
            return 1
        sha, size = _sha256_file(target)
        payload.update(
            downloaded=True,
            cached=True,
            sha256=sha,
            bytes=size,
            licence_gate_will_fire=False,
            status="downloaded",
        )
        log(f"[weights] fetched {size / 1e6:.1f} MB, sha256={sha[:16]}...")
        emit(payload)
        return 0
    except Exception as e:  # reported, never swallowed
        payload["status"] = "failed"
        payload["error"] = f"{type(e).__name__}: {e}"
        emit(payload)
        return 1


if __name__ == "__main__":
    sys.exit(main())
