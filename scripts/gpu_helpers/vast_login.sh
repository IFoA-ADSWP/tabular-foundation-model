#!/bin/bash
# Open a Vast.ai 2FA session for the CLI.
#
#   bash scripts/gpu_helpers/vast_login.sh
#
# Why this exists: every Vast API call is 2FA-gated. `tfa send-email` mints a
# one-time secret, and the emailed code is paired to THAT challenge -- so
# pairing a stale secret with a fresh code fails with
# "No 2FA challenge found", and each new send invalidates the previous secret.
# This script keeps the pairing in one shot and verifies the session at the end.
#
# If the account already has a TOTP app enrolled, use that instead:
#   vastai tfa login --method-type totp -c <CODE>

set -uo pipefail

export PATH="$HOME/.local/share/uv/tools/vastai/bin:$PATH"

if ! command -v vastai >/dev/null 2>&1; then
    echo "FATAL: vastai CLI not found. Install with: uv tool install vastai" >&2
    exit 2
fi

echo "--- checking for an existing session ---"
if vastai show user >/dev/null 2>&1; then
    echo "Already authenticated; nothing to do."
    exit 0
fi

echo "--- requesting an email code ---"
SEND_OUT="$(vastai tfa send-email 2>&1)"
echo "$SEND_OUT"

SECRET="$(printf '%s' "$SEND_OUT" | grep -oE '[0-9a-f]{32}' | head -1)"
if [ -z "$SECRET" ]; then
    echo "FATAL: could not parse a 32-hex secret from the send-email response." >&2
    exit 2
fi

printf 'Enter the 6-digit code from the Vast.ai email: '
read -r CODE

echo "--- completing 2FA login ---"
if ! vastai tfa login --method-type email --secret "$SECRET" -c "$CODE"; then
    echo
    echo "Login failed. Most likely causes:" >&2
    echo "  - the code expired (they are short-lived): re-run this script" >&2
    echo "  - typo in the 6-digit code" >&2
    exit 1
fi

echo
echo "--- verifying session ---"
if vastai show user >/dev/null 2>&1; then
    echo "OK: 2FA session active."
else
    echo "WARNING: login reported success but show user still fails." >&2
    exit 1
fi
