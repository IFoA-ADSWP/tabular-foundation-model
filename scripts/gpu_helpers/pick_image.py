#!/usr/bin/env python3
"""Pick a PyTorch image whose CUDA does not exceed the host's ceiling.

    python3 pick_image.py <host_cuda_max_good>

Prints the docker tag.

Two constraints, both learned the hard way:

1. **The image's CUDA must be <= the host's `cuda_max_good`.** A CUDA 12.8 image
   will not run on a driver that only supports 12.2.
2. **Every tier carries torch >= 2.5.** `tabpfn 8.5.0` requires torch>=2.5, so a
   2.4.0 image lets pip upgrade torch to a CUDA 12.4 wheel onto a 12.2-capped
   host -- a mid-run failure on a paid instance.

Tag matrix verified against Docker Hub (2026-09):
    pytorch 2.5.1 -> cuda12.1, cuda12.4      (torch 2.5.1)
    pytorch 2.6.0 -> cuda12.4, cuda12.6      (torch 2.6.0)
    pytorch 2.7.0 -> cuda12.6, cuda12.8      (torch 2.7.0)

Lives in its own file rather than a shell heredoc: see select_offer.py for why
(bash 3.2.57 on macOS mis-parses heredocs nested in substitutions).
"""
import sys

TIERS = [
    (12.8, "pytorch/pytorch:2.7.0-cuda12.8-cudnn9-runtime"),
    (12.6, "pytorch/pytorch:2.6.0-cuda12.6-cudnn9-runtime"),
    (12.4, "pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime"),
    (12.1, "pytorch/pytorch:2.5.1-cuda12.1-cudnn9-runtime"),
]


def main() -> int:
    try:
        host = float(sys.argv[1])
    except (IndexError, ValueError):
        print(f"usage: {sys.argv[0]} <host_cuda_max_good>", file=sys.stderr)
        return 2

    for ceiling, tag in TIERS:
        if host >= ceiling:
            print(tag)
            return 0

    # Below 12.1: still emit the oldest tier rather than nothing, so the caller
    # fails loudly at image pull instead of silently picking nothing.
    print(TIERS[-1][1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
