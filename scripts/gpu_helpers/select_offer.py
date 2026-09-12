#!/usr/bin/env python3
"""Select a Vast.ai offer from a candidate list.

    python3 select_offer.py <pick> <max_dph> <gpu_allow_csv> <min_vram> [candidates.json]

Prints 9 space-separated fields for `read -r`:

    OFFER_ID GPU_NAME DPH CUDA DLPERF CPU_RAM_GB GPU_RAM_GB DISK_GB RELIABILITY

or a single empty line if nothing matches.

This lives in its own file rather than a shell heredoc on purpose: on macOS the
shell is bash 3.2.57, which mis-parses a heredoc nested inside a process
substitution (`read ... < <(python3 - <<'PY' ... PY)`), failing at runtime with
`0: ambiguous redirect` -- and `bash -n` does NOT catch it. Keeping the Python
here removes the shell/Python boundary entirely and makes the logic testable.

Exits 0 either way; callers must treat empty output as "no offer".
"""
import json
import re
import sys

# Ampere / Ada / Hopper only. Deliberately excludes Volta (V100), Pascal
# (P40/P100) and Turing (T4, Q RTX 8000), whose kernels recent PyTorch builds
# no longer ship -- a run on those fails after the instance is already paid for.
EXCLUDED = {
    "Tesla V100", "Tesla P40", "Tesla P100", "Tesla T4",
    "Q RTX 8000", "Q RTX 6000", "RTX 2080 Ti",
}


def _norm(name) -> str:
    """Normalise a GPU name for matching.

    The marketplace and the allow-list disagree about the 'RTX ' prefix: the
    offers API reports 'RTX A6000'/'RTX A5000' while the list carried 'A6000'/
    'A5000'. Matching was exact, so a perfectly good 49 GB Ampere card was
    silently filtered out and the run aborted with 'no usable offer' -- with 20
    candidates sitting in the file. Normalise both sides so this class of
    mismatch cannot recur.
    """
    return re.sub(r"^RTX\s+", "", str(name or "").strip().upper())


def main() -> int:
    if len(sys.argv) < 5:
        print("usage: select_offer.py <pick> <max_dph> <gpu_allow_csv> <min_vram> [candidates.json]",
              file=sys.stderr)
        return 2

    pick = sys.argv[1]
    max_dph = float(sys.argv[2])
    allow = {a.strip() for a in sys.argv[3].split(",") if a.strip()}
    min_vram = float(sys.argv[4])
    path = sys.argv[5] if len(sys.argv) > 5 else "/tmp/vast_candidates.json"

    try:
        with open(path) as f:
            d = json.load(f)
    except Exception:
        print("")
        return 0

    offers = d if isinstance(d, list) else d.get("offers", [])
    allow_n = {_norm(a) for a in allow}
    excluded_n = {_norm(e) for e in EXCLUDED}
    offers = [
        x for x in offers
        if _norm(x.get("gpu_name")) in allow_n
        and _norm(x.get("gpu_name")) not in excluded_n
        and (x.get("dph_total") or 9e9) <= max_dph
        and (x.get("cuda_max_good") or 0) >= 12.0
        and (x.get("gpu_ram") or 0) / 1000.0 >= min_vram
    ]
    if not offers:
        print("")
        return 0

    # Reliability is the secondary key in every mode: two offers with identical
    # price or throughput must not be separated by API return order, or a
    # rel 0.978 host can beat a rel 0.998 one at the same price.
    if pick == "cheapest":
        offers.sort(key=lambda x: (x.get("dph_total") or 9e9,
                                   -(x.get("reliability") or 0)))
    elif pick == "fastest":
        offers.sort(key=lambda x: (-(x.get("dlperf") or 0),
                                   -(x.get("reliability") or 0)))
    else:
        offers.sort(key=lambda x: (-((x.get("dlperf") or 0) / (x.get("dph_total") or 1)),
                                   -(x.get("reliability") or 0)))

    x = offers[0]
    print(
        x.get("id"),
        str(x.get("gpu_name", "?")).replace(" ", "_"),
        f"{x.get('dph_total', 0):.4f}",
        x.get("cuda_max_good") or 0,
        f"{x.get('dlperf') or 0:.1f}",
        int((x.get("cpu_ram") or 0) / 1000),
        f"{(x.get('gpu_ram') or 0) / 1000:.1f}",
        int(x.get("disk_space") or 0),
        f"{x.get('reliability', 0):.4f}",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
