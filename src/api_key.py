"""TABPFN_API_KEY resolution shared by benchmark scripts.

Previously duplicated 4x. Order: env var → repo-root .env → TABPFN_ENV_FILE.
"""

from __future__ import annotations

import os
from pathlib import Path


def load_api_key() -> None:
    """TABPFN_API_KEY env, else the first TABPFN_API_KEY= line from the repo-root
    .env or the file pointed to by TABPFN_ENV_FILE (if set).

    The resolved key is exported as both TABPFN_API_KEY and TABPFN_TOKEN:
    tabpfn-client renamed the variable it reads after 0.3.3, and setting only the
    old name lets baselines run while every TabPFN fold fails auth."""
    key = os.environ.get("TABPFN_API_KEY")
    if not key:
        candidates = [
            Path.cwd() / ".env",
            Path(os.environ["TABPFN_ENV_FILE"]) if os.environ.get("TABPFN_ENV_FILE") else None,
        ]
        for p in candidates:
            if p and p.exists():
                for line in p.read_text().splitlines():
                    if line.startswith("TABPFN_API_KEY="):
                        key = line.split("=", 1)[1].strip()
                        break
            if key:
                break
    if key:
        os.environ["TABPFN_API_KEY"] = key
        os.environ["TABPFN_TOKEN"] = key
        return
    raise RuntimeError(
        "TABPFN_API_KEY not set: export TABPFN_API_KEY=... or add a "
        "TABPFN_API_KEY=... line to a .env file in the repo root "
        "(or set TABPFN_ENV_FILE to point at one)"
    )
