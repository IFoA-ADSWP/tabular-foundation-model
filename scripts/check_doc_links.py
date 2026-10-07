#!/usr/bin/env python3
"""Assert that every path a document references actually resolves.

Why this exists: moving or renaming documents is only safe if something checks the references
afterwards. Without it, a move is a leap of faith across ~50 links, a registry row and the cross-links,
and the failure is silent -- a reader clicks and finds nothing.

What it checks: markdown links, and backticked paths ending in a known file extension. Each candidate is
resolved against the document's own directory, then docs/, then the repository root, so any of the three
styles in use is accepted. Paths containing <placeholders> are skipped, as are URLs.

Usage:
  python3 scripts/check_doc_links.py            # list broken references; exit 1 if any
  python3 scripts/check_doc_links.py --warn     # list them, always exit 0
  python3 scripts/check_doc_links.py --dir docs --root .
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

EXTS = (".md", ".py", ".json", ".csv", ".npz", ".npy", ".png", ".parquet", ".sh", ".ipynb", ".txt", ".lock",
        ".toml", ".yaml", ".yml")
MD_LINK = re.compile(r"\]\(([^)\s#]+?)(?:#[^)]*)?\)")
BACKTICK = re.compile(r"`([^`\s]+?)`")


def candidates(text: str) -> list[str]:
    out = []
    for m in MD_LINK.finditer(text):
        out.append(m.group(1))
    for m in BACKTICK.finditer(text):
        tok = m.group(1)
        # A bare filename in prose ("meta.json", "the .npy file") is not a reference, and a glob or a
        # domain name only looks like a path. Require a separator, and rule out both.
        if not tok.endswith(EXTS) or "/" not in tok or "*" in tok:
            continue
        if re.match(r"^[\w.-]+\.[a-z]{2,}/", tok):  # docs.priorlabs.ai/...
            continue
        out.append(tok)
    return out


def resolves(doc: pathlib.Path, root: pathlib.Path, ref: str) -> bool:
    if ref.startswith(("http://", "https://", "mailto:")) or "<" in ref:
        return True
    for base in (doc.parent, root / "docs", root):
        if (base / ref).exists():
            return True
    return False


def check(docs: list[pathlib.Path], root: pathlib.Path) -> list[tuple[str, int, str]]:
    broken = []
    for doc in docs:
        for i, line in enumerate(doc.read_text(errors="replace").splitlines(), 1):
            for ref in candidates(line):
                if not resolves(doc, root, ref):
                    broken.append((str(doc), i, ref))
    return broken


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", default="docs")
    ap.add_argument("--root", default=".")
    ap.add_argument("--warn", action="store_true")
    args = ap.parse_args(argv)

    root = pathlib.Path(args.root).resolve()
    d = root / args.dir
    if not d.is_dir():
        print(f"  no such directory: {d}")
        return 2

    docs = sorted(d.rglob("*.md"))
    broken = check(docs, root)
    for path, line, ref in broken:
        rel = pathlib.Path(path).resolve().relative_to(root)
        print(f"  {rel}:{line}  ->  {ref}")
    print(f"  {len(docs)} documents checked, {len(broken)} broken reference(s)")

    if broken and not args.warn:
        print("  FAIL: a reference that does not resolve is a reader who finds nothing")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
