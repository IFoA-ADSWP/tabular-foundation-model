#!/usr/bin/env bash
# Create a worktree that actually contains the repository (#530).
#
#   ./scripts/new_worktree.sh feat/531-some-work          # branch from origin/main
#   ./scripts/new_worktree.sh fix/532-thing develop       # another base
#
# A harness-created worktree can arrive with an unrelated commit and almost no files: the first
# symptom is `ModuleNotFoundError` from a test, which reads as a missing module rather than a wrong
# tree. This script builds the tree in one command and refuses to print a path it has not checked.
#
# The worktree lands beside the repository as <repo>-worktrees/<branch-with-slashes-as-dashes>.

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: $(basename "$0") <branch> [base]" >&2
  exit 2
fi

BRANCH="$1"
BASE="${2:-main}"
ROOT="$(git rev-parse --show-toplevel)"
PARENT="$(dirname "$ROOT")"
SAFE_NAME="${BRANCH//\//-}"
PATH_OUT="$PARENT/$(basename "$ROOT")-worktrees/$SAFE_NAME"

if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  echo "error: branch $BRANCH already exists; pick another name or check it out instead" >&2
  exit 1
fi
if [ -e "$PATH_OUT" ]; then
  echo "error: $PATH_OUT already exists" >&2
  exit 1
fi

git -C "$ROOT" fetch origin "$BASE"
git -C "$ROOT" worktree add "$PATH_OUT" -b "$BRANCH" "origin/$BASE"

# Refuse a tree that cannot run this repository's tests. The check is the point of the script.
if [ ! -f "$PATH_OUT/tests/conftest.py" ] || [ ! -f "$PATH_OUT/AGENTS.md" ]; then
  echo "error: $PATH_OUT is incomplete; the worktree was not created from origin/$BASE" >&2
  exit 1
fi

echo "worktree ready: $PATH_OUT"
echo "  cd \"$PATH_OUT\""
echo "  ./scripts/bootstrap_dev.sh   # if .venv is absent in the new tree"
