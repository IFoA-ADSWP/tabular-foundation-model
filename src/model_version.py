"""TABPFN_MODEL_PATH resolution shared by benchmark scripts.

Defaults to the `v3_default` baseline that every committed verdict is stamped to
(docs/MODEL_VERSIONS.md), so an unconfigured run still reproduces the published
numbers. Set TABPFN_MODEL_PATH to re-test a newer model under the §15
Version-Drift Re-Test Policy, e.g. TABPFN_MODEL_PATH=v3.5_default.

Resolution order mirrors src.api_key: env var, then the repo-root .env, then
TABPFN_ENV_FILE. Reading .env matters because the server-side default moved to
v3.5 — a forgotten `export` must not silently score a different model than the
one the addendum claims.
"""

from __future__ import annotations

import os
from pathlib import Path

BASELINE_MODEL_PATH = "v3_default"
_ENV_KEY = "TABPFN_MODEL_PATH"


def resolve_model_path() -> str:
    """The `model_path` to pass to TabPFN estimators: env, else .env, else baseline."""
    value = os.environ.get(_ENV_KEY)
    if not value:
        candidates = [
            Path.cwd() / ".env",
            Path(os.environ["TABPFN_ENV_FILE"]) if os.environ.get("TABPFN_ENV_FILE") else None,
        ]
        for p in candidates:
            if p and p.exists():
                for line in p.read_text().splitlines():
                    if line.startswith(f"{_ENV_KEY}="):
                        value = line.split("=", 1)[1].strip()
                        break
            if value:
                break
    return (value or BASELINE_MODEL_PATH).strip() or BASELINE_MODEL_PATH
