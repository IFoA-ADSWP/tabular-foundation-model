"""TABPFN_MODEL_PATH resolution shared by benchmark scripts.

Two consumers want two different things, and conflating them broke the paid path once:

- **A label** (`v3_default`), for records and for the **hosted** client, whose
  `model_path` accepts a label. `resolve_model_path()` returns this, defaulting to the
  baseline every committed verdict is stamped to (docs/MODEL_VERSIONS.md).
- **A file name, a path, or `"auto"`**, for the **local** `tabpfn` package. It rejects a
  label outright: `Model v3_default not found in available models: [...]`. That is what
  failed every arm of the 2026-10-31 smoke in three seconds. `explicit_model_path()`
  returns this, or `None` when no operator set one.

So: `TABPFN_MODEL_PATH=v3.5_default` is a label and belongs with the hosted client;
a local run needs a `.ckpt` name or path.

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


def version_mismatch(declared: str | None, resolved: str) -> bool | None:
    """Whether the version a run declared is **not** the one execution resolved (#239).

    Three answers, because there are three facts. `None` means no experiment declared a
    version — an ad-hoc `--data` or filtered run can be neither matched nor mismatched, and
    `None` must never be read as a pass: a row with no declaration has been verified against
    nothing. Otherwise the answer is whether the two labels differ.

    Returns the mismatch rather than the agreement because that is the fact the artifact
    records and #233 must require to be exactly `False`. Inverting an agreement at each call
    site would turn the absent `None` into a false flag.

    This is a comparison, not a resolution. `resolve_model_path` above is still the only
    thing that decides `resolved`, and the registry's literal arrives as an argument, so
    declaration stays intent and execution stays env-first.
    """
    if declared is None:
        return None
    return declared != resolved


def explicit_model_path() -> str | None:
    """What an operator set for the LOCAL package: env, else .env.

    `None` means "nothing was chosen" -- and that is materially different from a baseline label.
    `TabPFNClassifier(model_path=...)` takes a **file name, a path, or "auto"**, never a label
    like `v3_default`: passing one is what failed every arm of the 2026-10-31 smoke in three
    seconds. So the launcher passes this only when it is not None, and the library uses its own
    default otherwise (#285).
    """
    value = os.environ.get(_ENV_KEY)
    if not value:
        candidates = [
            Path.cwd() / ".env",
            Path(os.environ["TABPFN_ENV_FILE"]) if os.environ.get("TABPFN_ENV_FILE") else None,
        ]
        for candidate in candidates:
            if candidate and candidate.exists():
                for line in candidate.read_text().splitlines():
                    if line.startswith(f"{_ENV_KEY}="):
                        value = line.split("=", 1)[1].strip()
                        break
            if value:
                break
    return (value or "").strip() or None


def resolve_model_path() -> str:
    """The version *label*: env, else .env, else the baseline label.

    Correct for hosted-client benchmarks and for records that name an era. **Not** a value the
    local `tabpfn` package accepts: it takes a file name, a path, or `"auto"` (#285).
    """
    return explicit_model_path() or BASELINE_MODEL_PATH


# ---------------------------------------------------------------------------
# Which weights a launch claims to run  (breadth, D16)
# ---------------------------------------------------------------------------
# The line the replication ran, and the one a breadth cell must share to be comparable with it
# (D15's record names this file; docs/MODEL_VERSIONS.md names v3_default as the classification line).
ANCHOR_CHECKPOINT = "tabpfn-v3-classifier-v3_default.ckpt"
EXPECTED_CHECKPOINT_ENV = "TFM_EXPECT_CHECKPOINT"


def expected_checkpoint() -> str:
    """The checkpoint file a launch claims to run, or "" when nobody asked.

    Empty is a distinct answer from "the anchor's": a local diagnostic that fits v2.5 must not be
    forced to carry v3, and a launch that asserts nothing should be visible as such in its record
    rather than indistinguishable from one that asserted and passed.
    """
    return (os.environ.get(EXPECTED_CHECKPOINT_ENV) or "").strip()


def checkpoint_mismatch(found, expected) -> str | None:
    """Why the cached checkpoints do not carry `expected`, or None when they do.

    Returns the reason rather than a flag so the refusal can name both the wanted file and what was
    actually on disk — the difference between "the pin moved" and "the weights were never fetched".

    An empty `found` is a refusal, not a pass: if an operator asked for the assertion, a cache with no
    weights has confirmed nothing.
    """
    if not expected:
        return None
    names = sorted({Path(p).name for p in found})
    if not names:
        return (
            f"no .ckpt in the cache, so {expected!r} cannot be confirmed: fetch the weights first, "
            "or the record would claim a model line nobody checked"
        )
    if expected in names:
        return None
    return f"{expected!r} is not among the cached checkpoints ({', '.join(names)})"
