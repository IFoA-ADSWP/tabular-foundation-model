#!/bin/bash
# One place for the secrets: the login keychain.
#
#   bash scripts/gpu_helpers/keys.sh check                 # what's stored, lengths only
#   bash scripts/gpu_helpers/keys.sh add tabpfn            # from the clipboard
#   bash scripts/gpu_helpers/keys.sh add vast              # from the clipboard
#   bash scripts/gpu_helpers/keys.sh env                   # eval-able exports
#   bash scripts/gpu_helpers/keys.sh get tabpfn            # prints the secret
#
# WHY THE KEYCHAIN
#   Encrypted at rest, unlocked by the login session, and readable by the CLI.
#   'security add-generic-password -w' with no value CANNOT be scripted: prompt
#   mode needs a tty and asks twice (password + retype), so a single paste never
#   satisfies it and a pipe fails with "passwords don't match". Passing the value
#   as an argument is the only workable form -- hence the clipboard route.
#
# CRON CANNOT READ THIS, LAUNCHD CAN -- and that decides the architecture.
#   Measured on this machine:
#     cron    -> search list is System.keychain only; lookup rc=44 (not found).
#                With an explicit keychain path: rc=36 (errSecInteractionNotAllowed,
#                locked, cannot prompt). Non-interactive unlock blocks on the password.
#     launchd -> LaunchAgent runs in the Aqua session; lookup rc=0, secret returned.
#   So anything that must run unattended needs a LaunchAgent, NOT a cron job.
#   scripts/gpu_helpers/vast_watchdog.sh is scheduled that way for exactly this reason.
#
# ACCOUNT NAME MUST BE $USER. The keychain lookup is case-sensitive on the account.

set -uo pipefail

KC_USER="${USER:-$(id -un)}"

svc_for() {
    case "$1" in
        tabpfn) echo "tabpfn-licence" ;;
        vast)   echo "vastai-api-key" ;;
        *) return 1 ;;
    esac
}

kc_get() {  # kc_get <service> -> prints secret, empty if absent
    security find-generic-password -s "$1" -a "$KC_USER" -w 2>/dev/null
}

cmd_check() {
    local ok=0
    for name in tabpfn vast; do
        local svc; svc="$(svc_for "$name")"
        local v; v="$(kc_get "$svc")"
        if [ -n "$v" ]; then
            printf '  %-7s %-16s present  (%d chars)\n' "$name" "$svc" "${#v}"
        else
            printf '  %-7s %-16s MISSING\n' "$name" "$svc"
            ok=1
        fi
    done
    # The Vast CLI also reads a plaintext file. Flag it, because two sources drift.
    if [ -f "$HOME/.config/vastai/vast_api_key" ]; then
        echo "  note: a plaintext vast_api_key file also exists"
        echo "        ($(stat -f '%Sp' "$HOME/.config/vastai/vast_api_key") $HOME/.config/vastai/vast_api_key)"
        echo "        the keychain wins when VAST_API_KEY is exported; see 'env'"
    fi
    return $ok
}

cmd_add() {
    local name="${1:-}"
    local svc; svc="$(svc_for "$name")" || { echo "usage: keys.sh add <tabpfn|vast>" >&2; exit 2; }
    local v; v="$(pbpaste 2>/dev/null | tr -d '\r\n')"
    if [ -z "$v" ]; then
        echo "clipboard is empty -- copy the secret first" >&2; exit 2
    fi
    # Guard against storing terminal output by accident (a very easy mistake).
    case "$v" in
        *'@'*|*' $ '*|'('*) 
            echo "clipboard does not look like a key (contains '@', spaces or a shell prompt)" >&2
            echo "copy ONLY the key, then re-run" >&2; exit 2 ;;
    esac
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
    local t v
    t="$(kc_get tabpfn-licence)"; v="$(kc_get vastai-api-key)"
    [ -n "$t" ] && printf 'export TABPFN_TOKEN=%s\n' "$(printf '%q' "$t")"
    [ -n "$v" ] && printf 'export VAST_API_KEY=%s\n' "$(printf '%q' "$v")"
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
