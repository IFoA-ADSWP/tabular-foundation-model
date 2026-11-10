#!/usr/bin/env bash
# Create a worktree that actually contains the repository (#530).
#
#   ./scripts/new_worktree.sh feat/531-some-work          # branch from origin/main
#   ./scripts/new_worktree.sh fix/532-thing develop       # another base
#
# A harness-created worktree can arrive with an unrelated commit and almost no files: the first
# symptom is `ModuleNotFoundError` from a test, which reads as a missing module rather than a wrong
# tree. This script builds the tree in one command, checks that the new tree is at origin/<base>,
# and removes it (branch included) if the check fails, so a retry is not blocked by the leftovers.
#
# The worktree lands beside the repository as <repo>-worktrees/<branch-with-slashes-as-dashes>.

set -euo pipefail

usage() {
  echo "usage: $(basename "$0") <branch> [base]" >&2
}

if [ $# -lt 1 ] || [ $# -gt 2 ]; then
  usage
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

# Refuse a tree that is not what was asked for, and leave nothing behind that blocks a retry.
expected="$(git -C "$ROOT" rev-parse "origin/$BASE")"
actual="$(git -C "$PATH_OUT" rev-parse HEAD 2>/dev/null || true)"
if [ "$actual" != "$expected" ] || [ ! -f "$PATH_OUT/tests/conftest.py" ]; then
  echo "error: $PATH_OUT is not origin/$BASE (expected $expected, found ${actual:-nothing})" >&2
  echo "       removing the worktree and branch so the command can be retried" >&2
  git -C "$ROOT" worktree remove --force "$PATH_OUT" || true
  git -C "$ROOT" branch -D "$BRANCH" || true
  exit 1
fi

echo "worktree ready: $PATH_OUT"
echo "  cd \"$PATH_OUT\""
if [ ! -f "$PATH_OUT/.venv/bin/python" ]; then
  echo "  ./scripts/bootstrap_dev.sh   # this tree has no .venv yet (about 1.9 GB)"
fi
