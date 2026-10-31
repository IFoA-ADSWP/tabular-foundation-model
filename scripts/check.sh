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

# The two trees that hold committed experiment evidence. A change here is not forbidden,
# but it must be deliberate: deleting a tracked log or rewriting a record is how evidence
# stops matching the claim that cites it. Raised by the 2026-10-30 retro, after a commit
# deleted seven tracked logs under outputs/ while its own plan asserted the diff was empty.
EVIDENCE_TREES=(outputs results)

run_evidence() {
  local base="${EVIDENCE_BASE:-origin/main}"
  echo "== evidence (${EVIDENCE_TREES[*]} unchanged vs ${base})"
  if ! git rev-parse --verify -q "${base}^{commit}" >/dev/null 2>&1; then
    # Not a missing tool (3): the comparison could not be made. A check that cannot run is a
    # failed check, not an absent binary.
    echo "check.sh: cannot compare evidence: '${base}' is not a commit here." >&2
    echo "  Fetch it (git fetch origin main) or set EVIDENCE_BASE." >&2
    return 1
  fi

  # Committed drift *and* pending drift. A staged `git add -A` of a deleted log is invisible to
  # a commit-range diff, which is exactly how one such deletion reached a commit. Untracked
  # files are excluded on purpose: mock runs write scratch under outputs/ every time.
  local changed pending
  changed="$(git diff --name-status "${base}"...HEAD -- "${EVIDENCE_TREES[@]}")"
  pending="$(git status --porcelain --untracked-files=no -- "${EVIDENCE_TREES[@]}")"
  if [ -z "$changed" ] && [ -z "$pending" ]; then
    echo "evidence trees unchanged"
    return 0
  fi

  if [ "${EVIDENCE_CHANGE_OK:-0}" = "1" ]; then
    echo "evidence trees CHANGED — allowed by EVIDENCE_CHANGE_OK=1:"
    [ -n "$changed" ] && printf '%s\n' "$changed"
    [ -n "$pending" ] && printf '%s\n' "$pending"
    return 0
  fi

  echo "evidence trees CHANGED — these hold committed experiment evidence:" >&2
  [ -n "$changed" ] && printf '%s\n' "$changed" >&2
  [ -n "$pending" ] && printf '%s\n' "$pending" >&2
  echo "  A deletion or rewrite here is evidence drift; a deliberate one is a decision." >&2
  echo "  Locally: EVIDENCE_CHANGE_OK=1 ./scripts/check.sh evidence" >&2
  echo "  CI: add the 'evidence-change' label to the pull request." >&2
  return 1
}

usage() {
  echo "usage: $(basename "$0") [ruff|pytest|shellcheck|evidence|all]" >&2
  exit 2
}

run_check() { # run_check <ruff|pytest|shellcheck|evidence>
  case "$1" in
    ruff)       run_ruff ;;
    pytest)     run_pytest ;;
    shellcheck) run_shellcheck ;;
    evidence)   run_evidence ;;
  esac
}

case "${1:-all}" in
  ruff|pytest|shellcheck|evidence) run_check "$1" ;;
  all)
    status=0
    missing=0
    for check in ruff pytest shellcheck evidence; do
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
