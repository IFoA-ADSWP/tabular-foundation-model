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

case "${1:-} ${2:-}" in
  "show user")        echo '{"credit": 10.0, "balance": 0, "total_spend": 0.0}' ;;
  "show instances")   echo '[]' ;;
  "show ssh-keys")    echo '[]' ;;
  "search offers")    cat /tmp/mock_offers.json 2>/dev/null || echo '[]' ;;
  "create ssh-key")   echo "Failed with error 400: Team SSH keys are not supported." ;;
  "create instance")  echo '{"success": true, "new_contract": 12345678}' ;;
  "show instance")
      cat <<'JSON'
{"actual_status": "running", "ssh_host": "203.0.113.9", "ssh_port": 41234,
 "gpu_name": "RTX PRO 5000", "dph_total": 0.6681, "gpu_ram": 48935,
 "cpu_ram": 64000, "reliability": 0.9876, "cuda_max_good": 13.0}
JSON
      ;;
  "destroy instance") echo "destroying instance $3." ;;
  "logs")             echo "  (mock logs)" ;;
  "execute "*)
      # $3 is the command. (An earlier version read $4, an off-by-one that
      # silently hid this whole branch.)
      if printf '%s' "${3:-}" | grep -q "VAST_B64_BEGIN"; then
          # Must echo the markers as well as the payload, or the extractor has
          # nothing to anchor on and artifact retrieval reports failure.
          echo "__VAST_B64_BEGIN__"
          (cd /tmp/mockstate && tar czf - . 2>/dev/null) | base64 | tr -d '\n'
          echo
          echo "__VAST_B64_END__"
      else
          echo "########## ARM B_in_domain ##########"
          echo "--- coil2000 (coil2000.csv) ---"
          echo "  B_in_domain... ROC=0.7701 Brier=0.0501 (18.2s)"
          echo "########## AGGREGATE ##########"
          echo "PILOT RESULTS SUMMARY"
          echo "BOOTSTRAP FINISHED"
      fi
      ;;
  *)
      echo "[mock vastai] unhandled: $*" >&2 ;;
esac
