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


# Records, not promises: plans state what was intended and archives what a superseded
# document said, so a path there is a citation even when the file has since moved or
# retired. Checking them would punish the history the documents exist to keep.
CITATION_TIERS = ("plans", "archive")

# Run output is git-ignored: a document that says "a run writes outputs/<dir>/manifest.json"
# describes a shape, and the file cannot resolve from a clean checkout by design.
UNCOMMITTED_TREES = ("outputs", "results")
BACKTICK = re.compile(r"`([^`\s]+?)`")


def candidates(text: str) -> list[str]:
    out = []
    for m in MD_LINK.finditer(text):
        ref = m.group(1)
        # A bare name in a link target is a wiki page or a section, not a repo path:
        # `[x](Benchmark-Summary)` cannot resolve against the tree by design.
        if "/" not in ref and not ref.endswith(EXTS):
            continue
        out.append(ref)
    for m in BACKTICK.finditer(text):
        tok = m.group(1)
        # A bare filename in prose ("meta.json", "the .npy file") is not a reference, and a glob or a
        # domain name only looks like a path. Require a separator, and rule out both.
        if not tok.endswith(EXTS) or "/" not in tok or "*" in tok:
            continue
        # `frontier_plot_{a,b}.png` is a shell illustration, not a path.
        if "{" in tok or "}" in tok:
            continue
        if re.match(r"^[\w.-]+\.[a-z]{2,}/", tok):  # docs.priorlabs.ai/...
            continue
        out.append(tok)
    return out


def resolves(doc: pathlib.Path, root: pathlib.Path, ref: str) -> bool:
    if ref.startswith(("http://", "https://", "mailto:")) or "<" in ref:
        return True
    if ref.split("/", 1)[0] in UNCOMMITTED_TREES:
        return True  # a described shape, not a committed file
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
    ap.add_argument("--include-citations", action="store_true",
                    help="also check docs/plans and docs/archive, where a path is a citation")
    args = ap.parse_args(argv)

    root = pathlib.Path(args.root).resolve()
    d = root / args.dir
    if not d.is_dir():
        print(f"  no such directory: {d}")
        return 2

    if args.include_citations:
        docs = sorted(d.rglob("*.md"))
    else:
        docs = sorted(p for p in d.rglob("*.md")
                      if not (p.relative_to(d).parts and p.relative_to(d).parts[0] in CITATION_TIERS))
    broken = check(docs, root)
    for path, line, ref in broken:
        rel = pathlib.Path(path).resolve().relative_to(root)
        print(f"  {rel}:{line}  ->  {ref}")
    print(f"  {len(docs)} documents checked, {len(broken)} broken reference(s)")
    if not args.include_citations:
        print(f"  (citation tiers skipped: {', '.join(CITATION_TIERS)}; "
              f"pass --include-citations to check them)")

    if broken and not args.warn:
        print("  FAIL: a reference that does not resolve is a reader who finds nothing")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
