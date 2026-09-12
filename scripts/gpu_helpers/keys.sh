#!/bin/bash
# Secrets for the TabPFN GPU work. ONE RULE: every secret is a mode-600 file
# under ~/.config. No keychain, no exceptions, nothing to remember.
#
#   bash scripts/gpu_helpers/keys.sh check              # what's stored, lengths only
#   bash scripts/gpu_helpers/keys.sh add   tabpfn|vast  # from the clipboard
#   bash scripts/gpu_helpers/keys.sh get   tabpfn|vast  # print the value
#   bash scripts/gpu_helpers/keys.sh env                # eval-able exports
#   bash scripts/gpu_helpers/keys.sh path  tabpfn|vast  # where the file lives
#
# THE TWO FILES (and why they are where they are)
#   TabPFN token : ~/.config/tfm/keys.env           -- ours; read by vast_run.sh and
#                                                      interpolated into the remote
#                                                      bootstrap.
#   Vast API key : ~/.config/vastai/vast_api_key    -- NOT our choice. The Vast CLI
#                                                      must read this file itself.
#
# WHY THE VAST KEY CANNOT MOVE (measured, three supply paths, one identical value):
#     CLI reads its own config file   -> SUCCESS
#     VAST_API_KEY=<same value>       -> 401 "requires ... Two Factor Authentication"
#     --api-key <same value>          -> 401
#   The 2FA session is bound to the key the CLI loads from its config file, so an
#   explicitly supplied key is a different auth context. Never export VAST_API_KEY;
#   that file IS the store. Do not "tidy" this into one file -- it cannot work.
#
# WHY FILES AND NOT THE KEYCHAIN
#   FileVault is on, so a 600 file is already encrypted at rest. The keychain added a
#   second mechanism (security(1) prompt quirks, an iCloud/synced store that scripts
#   cannot reach, a cron-vs-launchd access split) for very little extra protection.
#   One rule beats two mechanisms.
#
# WHY 'add' READS THE CLIPBOARD
#   Pasting into a terminal prompt is unreliable here and 'security add-generic-password'
#   with no value cannot be scripted at all (it needs a tty and asks twice). The
#   clipboard is the one input path that works from a GUI workflow.
#
# USAGE NOTE: keys.sh only reads and writes files. It never calls an API, and it
# never manages the Vast 2FA session -- 'vast_login.sh' does that.

set -uo pipefail

TABPFN_FILE="${TABPFN_FILE:-$HOME/.config/tfm/keys.env}"
VAST_KEY_FILE="${VAST_KEY_FILE:-$HOME/.config/vastai/vast_api_key}"

usage() { sed -n '2,12p' "$0"; exit "${1:-2}"; }

# --- TabPFN token: a small env file, so it is human-editable in any editor --------
tabpfn_get() {
    [ -f "$TABPFN_FILE" ] || return 1
    # NOTE: -E matters. BSD sed (macOS) has no GNU '\+' in basic mode, so the
    # optional 'export' group silently fails to match and this returns nothing --
    # which looks exactly like a missing key. Use extended regex.
    # take the last non-comment assignment; tolerate export/quotes/whitespace
    sed -nE 's/^[[:space:]]*(export[[:space:]]+)?TABPFN_TOKEN[[:space:]]*=[[:space:]]*//p' "$TABPFN_FILE" \
        | tail -1 | sed -E -e 's/^["'"'"']//' -e 's/["'"'"']$//' -e 's/[[:space:]]*$//'
}

tabpfn_set() {  # tabpfn_set <value>
    mkdir -p "$(dirname "$TABPFN_FILE")"
    ( umask 077; printf 'TABPFN_TOKEN=%s\n' "$1" > "$TABPFN_FILE" )
}

# --- Vast key: the CLI's own single-line file -----------------------------------
vast_get() { [ -s "$VAST_KEY_FILE" ] && tr -d '\r\n' < "$VAST_KEY_FILE"; }

vast_set() {  # vast_set <value>
    mkdir -p "$(dirname "$VAST_KEY_FILE")"
    ( umask 077; printf '%s' "$1" > "$VAST_KEY_FILE" )
}

path_for() {
    case "$1" in
        tabpfn) echo "$TABPFN_FILE" ;;
        vast)   echo "$VAST_KEY_FILE" ;;
        *) return 1 ;;
    esac
}

get_for() {
    case "$1" in
        tabpfn) tabpfn_get ;;
        vast)   vast_get ;;
        *) return 1 ;;
    esac
}

cmd_check() {
    local name file val ok=0
    for name in tabpfn vast; do
        file="$(path_for "$name")"; val="$(get_for "$name" || true)"
        if [ -n "$val" ]; then
            printf '  %-7s present (%3d chars)  %s  %s\n' \
                "$name" "${#val}" "$(stat -f '%Sp' "$file" 2>/dev/null)" "${file/#$HOME/~}"
        else
            printf '  %-7s MISSING              %s\n' "$name" "${file/#$HOME/~}"
            ok=1
        fi
    done
    for name in tabpfn vast; do
        file="$(path_for "$name")"
        if [ -f "$file" ]; then
            case "$(stat -f '%Sp' "$file")" in
                -rw-------) ;;
                *) echo "  WARNING: $name is not mode 600 -- run: chmod 600 ${file/#$HOME/~}" >&2; ok=1 ;;
            esac
        fi
    done

    # Remote verification, because a STORED key is not a WORKING key -- and the
    # distinction cost two GPU runs. The API answers two questions separately:
    #   /protected        -> which account the key belongs to (proves validity)
    #   /account/license  -> whether that account ACCEPTED the licence
    # A key can pass the first and fail the second, and only the second gates the
    # weight download. Both are one HTTPS request, so there is no excuse for not
    # asking before renting anything.
    local tok; tok="$(tabpfn_get 2>/dev/null || true)"
    if [ -n "$tok" ]; then
        local ver who lic
        ver="${TABPFN_VERSION:-8.5.0}"
        who="$(curl -sSL --max-time 20 -H "Authorization: Bearer $tok" \
               https://api.priorlabs.ai/protected 2>/dev/null || true)"
        lic="$(curl -sSL --max-time 20 -H "Authorization: Bearer $tok" \
               "https://api.priorlabs.ai/account/license/?version=${ver}" 2>/dev/null || true)"
        echo
        echo "  --- remote check (free, no GPU) ---"
        local acct
        acct="$(printf '%s' "$who" | sed -n 's/.*"message":"\([^"]*\)".*/\1/p')"
        if [ -n "$acct" ]; then
            echo "  key belongs to : ${acct##*,}"
        else
            echo "  key belongs to : UNKNOWN -- key did not authenticate" >&2; ok=1
        fi
        case "$lic" in
            *'"accepted":true'*)  echo "  licence ${ver}   : ACCEPTED" ;;
            *'"accepted":false'*) echo "  licence ${ver}   : NOT ACCEPTED" >&2
                                  echo "                   accept it at https://ux.priorlabs.ai" >&2
                                  echo "                   (Licenses tab) as the account shown above" >&2
                                  ok=1 ;;
            *) echo "  licence ${ver}   : could not read (${lic:-<no response>})" >&2 ;;
        esac
    fi
    return $ok
}

cmd_add() {
    local name="${1:-}"; path_for "$name" >/dev/null || usage
    local v; v="$(pbpaste 2>/dev/null | tr -d '\r\n')"
    [ -n "$v" ] || { echo "clipboard is empty -- copy the secret first" >&2; exit 2; }

    # Refuse anything that is obviously not a key. This guards a REAL failure:
    # copying the COMMAND TEXT ("bash scripts/gpu_helpers/keys.sh add tabpfn",
    # 43 chars) and storing it as the token -- it silently replaced a valid
    # 167-char key and nothing complained. Validate BEFORE writing, never after.
    case "$v" in
        *' '*|*'@'*|'('*|'$'*|'#'*|*'/'*)
            echo "refusing: that does not look like a key (space, @, \$, / or a leading ( or #)." >&2
            echo "Copy ONLY the key itself, then re-run." >&2; exit 2 ;;
    esac
    if [ "${#v}" -lt 24 ]; then
        echo "refusing: only ${#v} chars, too short for an API key." >&2
        echo "You probably copied a command or a partial value." >&2; exit 2
    fi

    if [ "$name" = tabpfn ]; then tabpfn_set "$v"; else vast_set "$v"; fi
    printf 'stored %s (%d chars) -> %s [%s]\n' \
        "$name" "${#v}" "$(path_for "$name")" "$(stat -f '%Sp' "$(path_for "$name")")"
}

cmd_env() {
    # Deliberately no VAST_API_KEY: exporting it 401s. The CLI reads its own file.
    local t; t="$(tabpfn_get || true)"
    [ -n "$t" ] && printf 'export TABPFN_TOKEN=%s\n' "$(printf '%q' "$t")"
    return 0
}

case "${1:-check}" in
    check) cmd_check ;;
    add)   shift; cmd_add "$@" ;;
    get)   shift; path_for "${1:-}" >/dev/null || usage; get_for "$1" ;;
    path)  shift; path_for "${1:-}" >/dev/null || usage; path_for "$1" ;;
    env)   cmd_env ;;
    -h|--help) usage 0 ;;
    *) usage ;;
esac
