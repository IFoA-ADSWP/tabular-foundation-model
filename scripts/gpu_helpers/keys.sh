#!/bin/bash
# One place for the secrets: the login keychain.
#
#   bash scripts/gpu_helpers/keys.sh check                 # what's stored, lengths only
#   bash scripts/gpu_helpers/keys.sh add tabpfn            # from the clipboard
#   bash scripts/gpu_helpers/keys.sh add vast              # from the clipboard
#   bash scripts/gpu_helpers/keys.sh env                   # eval-able exports
#   bash scripts/gpu_helpers/keys.sh get tabpfn            # prints the secret
#
# WHY THE KEYCHAIN, AND WHERE IT DOES *NOT* APPLY
#   Encrypted at rest, unlocked by the login session, readable by the CLI and by a
#   LaunchAgent (cron cannot -- see below). 'security add-generic-password -w' with
#   no value CANNOT be scripted: prompt mode needs a tty and asks twice, so a single
#   paste never satisfies it and a pipe fails with "passwords don't match". Passing
#   the value as an argument is the only workable form -- hence the clipboard route.
#
#   THE VAST KEY IS THE EXCEPTION. It must live in the CLI's own config file
#   (~/.config/vastai/vast_api_key, mode 600), NOT in the keychain. Measured:
#   supplying the key explicitly -- via VAST_API_KEY *or* --api-key -- returns
#       401 "requires you to have logged in using Two Factor Authentication"
#   even when the value is byte-identical to that file (sha256-verified), while
#   letting the CLI read the file succeeds. The 2FA session is bound to the key the
#   CLI loads from its file, so an explicit key is a different auth context with no
#   session. Scripts must therefore NOT export VAST_API_KEY.
#   This one is a genuine constraint, not a preference -- do not "fix" it.
#
# CRON CANNOT READ THE KEYCHAIN, LAUNCHD CAN
#   cron    -> search list is System.keychain only; lookup rc=44 (not found). With
#              an explicit keychain path: rc=36 (errSecInteractionNotAllowed,
#              locked, cannot prompt). Non-interactive unlock blocks on the password.
#   launchd -> LaunchAgent runs in the Aqua session; lookup rc=0, secret returned.
#   So the leak watchdog runs as a LaunchAgent, not a cron job.
#
# ACCOUNT NAME MUST BE $USER. The keychain lookup is case-sensitive on the account.

set -uo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
KC_USER="${USER:-$(id -un)}"
KCGET_BIN="${KCGET_BIN:-$HOME/.cache/tabpfn-keys/kcget}"
VAST_KEY_FILE="${VAST_KEY_FILE:-$HOME/.config/vastai/vast_api_key}"

svc_for() {
    case "$1" in
        tabpfn) echo "tabpfn-licence" ;;
        vast)   echo "vastai-api-key" ;;
        *) return 1 ;;
    esac
}

_kcget_build() {
    # Compile the modern-API reader on first use and cache it. Needed because
    # Passwords.app writes to the iCloud keychain, which the legacy `security`
    # CLI cannot see at all (measured: rc=44 against its own DB file).
    [ -x "$KCGET_BIN" ] && return 0
    command -v swiftc >/dev/null 2>&1 || return 1
    mkdir -p "$(dirname "$KCGET_BIN")" 2>/dev/null || return 1
    swiftc -O -o "$KCGET_BIN" "$REPO_DIR/scripts/gpu_helpers/kcget.swift" >/dev/null 2>&1 || return 1
    [ -x "$KCGET_BIN" ]
}

kc_get() {  # kc_get <service> -> prints secret, empty if absent
    # 1. login keychain via the legacy CLI: fast, and the only path that works
    #    for an unattended LaunchAgent.
    local v
    v="$(security find-generic-password -s "$1" -a "$KC_USER" -w 2>/dev/null)"
    [ -n "$v" ] && { printf '%s' "$v"; return 0; }
    # 2. modern Security API: also reaches iCloud / Passwords.app items.
    if _kcget_build; then
        v="$("$KCGET_BIN" get "$1" "$KC_USER" 2>/dev/null)"
        [ -n "$v" ] && printf '%s' "$v"
    fi
}

cmd_check() {
    local ok=0

    # TabPFN token: the login keychain is the right home -- it is only ever read
    # interactively, so no headless access is needed.
    local t; t="$(kc_get tabpfn-licence)"
    if [ -n "$t" ]; then
        printf '  %-7s %-22s present (%d chars)   login keychain\n' tabpfn tabpfn-licence "${#t}"
    else
        printf '  %-7s %-22s MISSING\n' tabpfn tabpfn-licence; ok=1
    fi

    # Vast key: MUST be the CLI's config file, NOT the keychain (see header).
    if [ -s "$VAST_KEY_FILE" ]; then
        local n; n="$(tr -d '\r\n' < "$VAST_KEY_FILE" | wc -c | tr -d ' ')"
        printf '  %-7s %-22s present (%s chars)   %s %s\n' vast "$(basename "$VAST_KEY_FILE")" \
            "$n" "$(stat -f '%Sp' "$VAST_KEY_FILE")" "$(dirname "$VAST_KEY_FILE")"
    else
        printf '  %-7s %-22s MISSING\n' vast "$(basename "$VAST_KEY_FILE")"; ok=1
    fi

    # A keychain copy of the Vast key is worse than useless: it cannot authenticate
    # (the 2FA session binds to the file), and it is a second place to leak from.
    if security find-generic-password -s vastai-api-key -a "$KC_USER" -w >/dev/null 2>&1; then
        echo "  note: a keychain copy of the Vast key exists. It CANNOT authenticate"
        echo "        (exporting it 401s) -- delete it with:"
        echo "        security delete-generic-password -s vastai-api-key -a \"\$USER\""
    fi
    return $ok
}

cmd_add() {
    local name="${1:-}"
    local v; v="$(pbpaste 2>/dev/null | tr -d '\r\n')"
    if [ -z "$v" ]; then
        echo "clipboard is empty -- copy the secret first" >&2; exit 2
    fi
    # Guard against storing terminal output by accident (a very easy mistake).
    case "$v" in
        *'@'*|'('*)
            echo "clipboard does not look like a key (contains '@' or a shell prompt)" >&2
            echo "copy ONLY the key, then re-run" >&2; exit 2 ;;
    esac

    if [ "$name" = "vast" ]; then
        # The CLI's own file is the only store that authenticates for this key.
        mkdir -p "$(dirname "$VAST_KEY_FILE")"
        ( umask 077; printf '%s' "$v" > "$VAST_KEY_FILE" )
        echo "wrote the Vast key to $VAST_KEY_FILE (mode $(stat -f '%Sp' "$VAST_KEY_FILE"), ${#v} chars)"
        echo "note: do NOT also export VAST_API_KEY -- that 401s; let the CLI read this file"
        return 0
    fi

    local svc; svc="$(svc_for "$name")" || { echo "usage: keys.sh add <tabpfn|vast>" >&2; exit 2; }
    security add-generic-password -U -s "$svc" -a "$KC_USER" -w "$v" \
        && echo "stored '$name' as service '$svc' account '$KC_USER' (${#v} chars)"
}

cmd_get() {
    local name="${1:-}"
    local svc; svc="$(svc_for "$name")" || { echo "usage: keys.sh get <tabpfn|vast>" >&2; exit 2; }
    local v; v="$(kc_get "$svc")"
    [ -n "$v" ] || { echo "not found: $svc" >&2; exit 1; }
    printf '%s' "$v"
}

cmd_env() {  # eval "$(keys.sh env)" to populate a shell
    local t; t="$(kc_get tabpfn-licence)"
    [ -n "$t" ] && printf 'export TABPFN_TOKEN=%s\n' "$(printf '%q' "$t")"
    # Deliberately NO VAST_API_KEY: exporting it 401s (see header). The CLI reads
    # its own config file, which is where that key must live.
    return 0
}

case "${1:-check}" in
    check) cmd_check ;;
    add)   shift; cmd_add "$@" ;;
    get)   shift; cmd_get "$@" ;;
    env)   cmd_env ;;
    -h|--help) sed -n '2,30p' "$0" ;;
    *) echo "unknown command: $1 (try: check | add | get | env)" >&2; exit 2 ;;
esac
