#!/usr/bin/env bash
# scripts/check.sh — the single definition of this repository's checks.
#
#   ./scripts/check.sh              # run every check
#   ./scripts/check.sh ruff         # run one
#
# CI invokes this script with a check name; a human runs it with no arguments.
# That shared definition is the point: the workflow must not restate a command,
# or the two drift and "passes locally" stops meaning anything.
#
# Exit codes: 0 all passed · 1 a check failed · 2 usage · 3 a tool is missing.
# With no argument every check runs, even when a tool is missing: one absent binary
# must not hide the checks after it. A real failure (1) outranks a missing tool (3).
#
# issue #257, spec #252.
set -uo pipefail

root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "$root" ]; then
  echo "check.sh: not inside a git repository" >&2
  exit 2
fi
cd "$root" || exit 2

# Deliberately pinned, and cited rather than silent. The GPU helpers carry four
# pre-existing SC2012/SC2016 findings that are intentional (arm names expanded
# into fixed glob paths, and a bootstrap decoded on the far side of a pipe).
# At default severity they fail every run on style, which is how a lint gate
# gets disabled. Raise this floor only after those four are fixed.
SHELLCHECK_SEVERITY="warning"

need() { # need <binary> <install hint>
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "check.sh: required tool '$1' is not installed — $2" >&2
    exit 3
  fi
}

run_ruff() {
  need ruff "pip install ruff"
  echo "== ruff"
  ruff check scripts/ src/ tests/
}

run_pytest() {
  need pytest "pip install pytest"
  echo "== pytest"
  pytest tests/ -q
}

run_shellcheck() {
  need shellcheck "brew install shellcheck, or apt-get install shellcheck"
  echo "== shellcheck (severity >= ${SHELLCHECK_SEVERITY})"
  # shellcheck disable=SC2086  # glob is deliberate: the paid-run scripts, by name
  shellcheck --severity="${SHELLCHECK_SEVERITY}" scripts/gpu_helpers/*.sh
}

usage() {
  echo "usage: $(basename "$0") [ruff|pytest|shellcheck|all]" >&2
  exit 2
}

run_check() { # run_check <ruff|pytest|shellcheck>
  case "$1" in
    ruff)       run_ruff ;;
    pytest)     run_pytest ;;
    shellcheck) run_shellcheck ;;
  esac
}

case "${1:-all}" in
  ruff|pytest|shellcheck) run_check "$1" ;;
  all)
    status=0
    missing=0
    for check in ruff pytest shellcheck; do
      # The subshell is load-bearing: need() exits 3 when a tool is absent, and without
      # it that exit would end the script and hide every check after this one.
      ( run_check "$check" )
      case $? in
        0) ;;
        3) missing=1 ;;
        *) status=1 ;;
      esac
    done
    [ "$status" -eq 0 ] || exit 1
    [ "$missing" -eq 0 ] || exit 3
    exit 0
    ;;
  *) usage ;;
esac
