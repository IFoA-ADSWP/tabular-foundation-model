#!/bin/bash
# Test double for the vastai CLI, for dry-running vast_run.sh WITHOUT SPENDING.
#
# Usage:
#   mkdir -p /tmp/mockbin && cp scripts/gpu_helpers/mock_vastai.sh /tmp/mockbin/vastai
#   chmod +x /tmp/mockbin/vastai
#   cp <real offers json> /tmp/mock_offers.json
#   PATH="/tmp/mockbin:$PATH" TABPFN_TOKEN=pk_dummy \
#       bash scripts/gpu_helpers/vast_run.sh --yes --arms B_in_domain
#
# WHY THIS FILE EXISTS: a dry run that silently invokes the real CLI is worse
# than no dry run. Getting this wrong once created three real instances and the
# destroy hung on its confirmation prompt, leaving them billing (~$0.13).
# Two properties make it safe:
#   1. The interlock below refuses to run unless the resolved vastai IS this
#      file. vast_run.sh used to prepend the real CLI's directory to PATH
#      unconditionally, which shadowed any double; it now only extends PATH
#      when vastai is not already resolvable.
#   2. vast_run.sh must pass -y to `destroy instance`, or the trap aborts at the
#      prompt and leaks the instance.
set -uo pipefail

SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
RESOLVED="$(command -v vastai 2>/dev/null || true)"
if [ "$RESOLVED" != "$SELF" ]; then
    echo "[mock] REFUSING: 'vastai' resolves to '$RESOLVED', not this mock ('$SELF')." >&2
    echo "[mock] A dry run that silently calls the real CLI can create real, billing instances." >&2
    exit 99
fi

mkdir -p /tmp/mockstate

# Paths are overridable so a test can isolate itself from the real /tmp fixtures.
MOCK_OFFERS_FILE="${MOCK_OFFERS:-/tmp/mock_offers.json}"
MOCK_STATE_DIR="${MOCK_STATE_DIR:-/tmp/mockstate}"

case "${1:-} ${2:-}" in
  "show user")        echo '{"credit": 10.0, "balance": 0, "total_spend": 0.0}' ;;
  "show instances")   echo '[]' ;;
  "show ssh-keys")    echo '[]' ;;
  "search offers")    cat "$MOCK_OFFERS_FILE" 2>/dev/null || echo '[]' ;;
  "create ssh-key")   echo "Failed with error 400: Team SSH keys are not supported." ;;
  "create instance")
      # Record the create so a test can assert what was requested, not just that
      # something happened.
      echo '{"success": true, "new_contract": 12345678}'
      printf '%s\n' "${MOCK_INSTANCE_ID:-12345678}" >> "$MOCK_STATE_DIR/created.txt"
      ;;
  "show instance")
      # MOCK_SEQUENCE: comma-separated statuses consumed one per call, so a test
      # can reproduce the real provisioning order (unknown -> loading -> running).
      # MOCK_STATUS forces a single constant state. Add MOCK_DELAY to make the
      # grace period elapse quickly.
      if [ -n "${MOCK_SEQUENCE:-}" ]; then
          CNT_F="${MOCK_SEQ_FILE:-/tmp/mock_seq_count}"
          [ -n "${MOCK_DELAY:-}" ] && sleep "$MOCK_DELAY"
          n=$(cat "$CNT_F" 2>/dev/null || echo 0)
          IFS=',' read -ra SEQ <<< "$MOCK_SEQUENCE"
          idx=$n
          [ "$idx" -ge "${#SEQ[@]}" ] && idx=$(( ${#SEQ[@]} - 1 ))
          st="${SEQ[$idx]}"
          echo $(( n + 1 )) > "$CNT_F"
          echo "{\"actual_status\": \"$st\", \"ssh_host\": \"203.0.113.9\", \"ssh_port\": 41234, \"gpu_name\": \"RTX A6000\", \"dph_total\": 0.469, \"gpu_ram\": 49140, \"cpu_ram\": 128000, \"reliability\": 0.9951, \"cuda_max_good\": 13.0, \"intended_status\": \"running\", \"machine_id\": ${MOCK_MACHINE_ID:-424242}, \"host_id\": 909090}"
      elif [ -n "${MOCK_STATUS:-}" ]; then
          # ONE LINE, deliberately. This was previously split across three
          # adjacent double-quoted strings, which bash does NOT concatenate: the
          # newlines ended the command, so lines 2-3 were executed as commands
          # ("command not found") and only a truncated fragment of JSON reached
          # stdout. Callers run with 2>/dev/null, so the noise vanished and the
          # parse failed silently -- every field came back empty, which made the
          # runner report status=unknown forever. That is why a terminal-state
          # test appeared to pass: it was hitting the unknown-grace-timeout path,
          # not the 'exited' path it claimed to exercise.
          #
          # intended_status and machine_id are emitted because the runner now
          # DEPENDS on them: intended_status drives the early abort, machine_id is
          # what a retry excludes. A mock missing them silently disables both.
          echo "{\"actual_status\": \"$MOCK_STATUS\", \"gpu_name\": \"RTX A6000\", \"dph_total\": 0.469, \"gpu_ram\": 49140, \"cpu_ram\": 128000, \"reliability\": 0.9951, \"cuda_max_good\": 13.0, \"intended_status\": \"${MOCK_INTENDED:-running}\", \"machine_id\": ${MOCK_MACHINE_ID:-424242}, \"host_id\": 909090}"
      else
          cat <<'JSON'
{"actual_status": "running", "ssh_host": "203.0.113.9", "ssh_port": 41234,
 "gpu_name": "RTX A6000", "dph_total": 0.469, "gpu_ram": 49140,
 "cpu_ram": 128000, "reliability": 0.9951, "cuda_max_good": 13.0,
 "intended_status": "running", "machine_id": 424242, "host_id": 909090}
JSON
      fi
      ;;
  "destroy instance")
      echo "destroying instance $3."
      # Record the teardown. The acceptance test for PR-8 is that the destroy FIRED
      # -- a mock that only prints cannot prove the trap ran.
      printf '%s\n' "$3" >> "$MOCK_STATE_DIR/destroyed.txt"
      ;;
  "logs "*)
      # NOTE the trailing space: the dispatch is `case "$1 $2"`, so a bare
      # `"logs")` never matches `vastai logs <id> --tail N` and the branch is dead
      # -- which left the runner polling until its 60-minute ceiling.
      # The runner reads the LOG, not `execute`: `vastai execute` only runs
      # ls/rm/du, so it can neither launch a script nor read a file.
      echo "########## GPU check ##########"
      echo "  torch 2.7.0+cu128 | NVIDIA RTX A6000"
      echo "########## PREFLIGHT OK ##########"
      echo "########## ARM A_raw ##########"
      echo "    A_raw... logloss=0.2080 ROC=0.7679 ECE=0.0310 (21.0s)"
      echo "########## ARM B_in_domain ##########"
      echo "    B_in_domain... logloss=0.2050 ROC=0.7701 ECE=0.0288 (18.2s)"
      echo "########## AGGREGATE ##########"
      echo "PILOT RESULTS SUMMARY"
      echo "########## ARTIFACTS ##########"
      # DELEGATE TO THE REAL EMITTER. This branch previously emitted its own markers
      # (__ARTIFACTS_B64_BEGIN__/END__), which the verifier does not look for -- so
      # the mock happily validated a wire format that no longer existed. Calling the
      # real script means the mock cannot drift from what the box actually does.
      # A mock that invents its own format is how a transport that cannot exist got
      # validated once already.
      EMITTER="${MOCK_EMITTER:-scripts/gpu_helpers/emit_artifacts.sh}"
      TREE="${MOCK_OUTPUT_TREE:-$MOCK_STATE_DIR/finetune/pilot}"
      if [ -f "$EMITTER" ]; then
          bash "$EMITTER" "$TREE"
      else
          echo "[mock] WARNING: emitter not found at '$EMITTER' -- emitting an empty payload" >&2
          echo "__ARTIFACTS_INFO__ bytes=0 sha256=- lines=0 files=0"
          echo "__ARTIFACTS_BEGIN__"
          echo "__ARTIFACTS_END__"
      fi
      echo "BOOTSTRAP FINISHED"
      ;;
  "execute "*)
      # MODEL THE REAL CONSTRAINT. A previous mock accepted any shell command, so it
      # happily validated a transport that cannot exist -- and the real instance
      # answered "Failed with error 400: Invalid command given." Only ls/rm/du are
      # accepted by the real endpoint; anything else must fail here too.
      case "${3:-}" in
          ls|ls\ *|rm\ *|du|du\ *) echo "[mock] (ls/rm/du output)" ;;
          *) echo "Failed with error 400: Invalid command given." ;;
      esac
      ;;
  *)
      echo "[mock vastai] unhandled: $*" >&2 ;;
esac
