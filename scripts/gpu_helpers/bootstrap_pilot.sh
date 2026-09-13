#!/bin/bash
# Bootstrap the fine-tuning pilot on a plain GPU VM (Vast.ai, Lambda, EC2...).
#
# Usage:
#   export TABPFN_TOKEN="pk_..."
#   ssh -p <PORT> root@<IP> "TABPFN_TOKEN=$TABPFN_TOKEN bash -s" < scripts/gpu_helpers/bootstrap_pilot.sh
#
# or, already on the box:
#   TABPFN_TOKEN=pk_... bash bootstrap_pilot.sh
#
# Unlike the Colab launcher this does NOT detach: over SSH you keep the
# terminal, so blocking is correct and simpler. The per-arm subprocess
# isolation is kept -- on the 12 GB CPU runtime a fine-tuning OOM SIGKILLed
# the interpreter and took the whole batch with it.
#
# Deliberately does NOT use requirements.txt: it pins numpy>=1.24,<2, which
# has no cp313 wheels, so pip compiles numpy from source (~20 min).

set -uo pipefail

: "${TABPFN_TOKEN:?Set TABPFN_TOKEN before running}"

BRANCH="${BRANCH:-finetune-v2}"
REPO="https://github.com/IFoA-ADSWP/tabular-foundation-model.git"
WORKDIR="${WORKDIR:-/workspace/tfm}"
ARMS="${ARMS:-A_raw,B_in_domain,E_glm,F_catboost}"

TABPFN_PIN="tabpfn==8.5.0"

echo "============================================================"
echo "BOOTSTRAP — branch=$BRANCH arms=$ARMS workdir=$WORKDIR"
echo "============================================================"

# ---- 0. Always emit the completion marker, on EVERY exit path ----
# The runner polls the log for this exact string. Without it an aborted
# bootstrap is indistinguishable from a slow one, so the runner waits out its
# whole ceiling while the instance bills -- which is precisely how a 60-minute
# leak happened. A trap makes that structurally impossible.
_BOOTSTRAP_DONE=0
finish() {
    [ "$_BOOTSTRAP_DONE" -eq 1 ] && return 0
    _BOOTSTRAP_DONE=1
    echo
    echo "BOOTSTRAP FINISHED"
}
trap finish EXIT

# ---- 1. Verify the GPU BEFORE spending time or money ----
echo "--- GPU check ---"
if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi --query-gpu=name,memory.total,driver_version \
               --format=csv,noheader || true
else
    echo "FATAL: nvidia-smi not found — this is not a GPU box." >&2
    exit 2
fi

# ---- 2. Clone ----
mkdir -p "$(dirname "$WORKDIR")"
if [ -d "$WORKDIR/.git" ]; then
    echo "--- existing clone, fetching ---"
    git -C "$WORKDIR" fetch origin "$BRANCH"
    git -C "$WORKDIR" checkout "$BRANCH"
    git -C "$WORKDIR" reset --hard "origin/$BRANCH"
else
    echo "--- cloning ---"
    git clone --branch "$BRANCH" "$REPO" "$WORKDIR" || exit 2
fi
cd "$WORKDIR" || exit 2

# ---- 3. Dependencies ----
# torch is NOT listed: the PyTorch image ships a CUDA build and reinstalling
# risks swapping it for a CPU wheel.
echo "--- installing deps ($TABPFN_PIN) ---"
python3 -m pip install -q --upgrade "$TABPFN_PIN" scikit-learn pandas \
    pyarrow catboost || exit 2

echo "--- verifying torch sees the GPU ---"
if ! python3 -c "
import sys, torch
if not torch.cuda.is_available():
    sys.exit('FATAL: torch.cuda.is_available() is False — refusing to run on CPU.')
print('torch', torch.__version__, '| cuda', torch.version.cuda,
      '|', torch.cuda.get_device_name(0))
"; then
    echo "FATAL: CUDA unavailable to torch. Stopping before doing CPU work on a paid GPU." >&2
    exit 2
fi

# ---- 3b. Prove the TabPFN licence BEFORE running any arm ----
# A token being PRESENT is not the same as a token WORKING. With an un-accepted
# licence every arm dies in about a second, with a message that reads like a model
# problem ("requires a one-time license acceptance ... no interactive terminal"),
# so the batch burns GPU minutes to learn nothing. Force the gated weight download
# here, once, where the outcome is unambiguous. On failure, stop -- the arms would
# fail identically.
#
# NOTE: `python3 -c` and not a heredoc. The header still documents piping this
# script to `bash -s`, and a heredoc would swallow the rest of the script from stdin.
echo "--- TabPFN auth preflight (forces the gated weight download) ---"
# On failure this prints the DECISION INPUTS, not just the exception. The generic
# licence error is raised from a fall-through that has three distinct causes --
# token missing, token invalid (401), or the licence check returning False -- and
# the traceback cannot tell them apart. Three runs were spent guessing which.
# Diagnose in one.
python3 -c '
import os, sys, json
tok = os.environ.get("TABPFN_TOKEN") or ""
if not tok:
    sys.exit("no TABPFN_TOKEN in the environment at all")
print("  token present: %d chars, prefix %s..." % (len(tok), tok[:10]))
# The sha is the decisive comparison: compare it with the value on the local Mac.
# If it DIFFERS, the token was mangled on its way into the container (the onstart
# script embeds it via shell quoting) and no amount of server-side reasoning helps.
# If it MATCHES, the API is rejecting a correct token based on where the request
# comes from.
import hashlib as _h
print("  token sha256 :", _h.sha256(tok.encode()).hexdigest()[:12], "(compare with the local Mac)")
print("  token suffix :", "..." + tok[-6:])

# Proxy env vars matter here. The licence check makes an HTTP request that
# 307-redirects; a proxy that drops the Authorization header across the redirect
# yields 401 -> check_license_accepted returns False -> fall through to browser
# login -> the "no interactive terminal" error, with every input looking correct.
# A cloud container is a likely place to find one configured.
import os as _os
_proxies = {k: v for k, v in _os.environ.items() if "proxy" in k.lower()}
print("  proxy env    :", _proxies if _proxies else "(none set)")

try:
    from tabpfn.settings import settings
    api_url = settings.tabpfn.auth_api_url
    gui_url = settings.tabpfn.auth_gui_url
    print("  api_url      :", api_url)
    print("  gui_url      :", gui_url)
except Exception as e:
    print("  could not read tabpfn settings:", e)

try:
    from tabpfn.browser_auth import verify_token, check_license_accepted, _get_license_name
    v = verify_token(tok, api_url)
    print("  verify_token :", v, "(True ok / False invalid-401 / None unreachable)")

    repo = "tabpfn_3"
    try:
        lic = _get_license_name(repo)
        print("  licence name :", lic, "(read from the HF model card for Prior-Labs/%s)" % repo)
    except Exception as e:
        lic = None
        print("  licence name : EXCEPTION:", type(e).__name__, e)

    if lic:
        acc = check_license_accepted(tok, api_url, lic)
        print("  accepted?    :", acc, "(True ok / False not-accepted-or-401 / None unreachable)")
        print("  -> if verify_token is True and accepted? is False, the server is")
        print("     rejecting THIS licence name for THIS token on the box.")

        # Raw status and body, because the boolean collapses 401, 403 and a
        # malformed body into the same answer. Also report the egress IP: if the
        # token sha matches the local value and this still returns 401, the
        # rejection is origin-based and no local configuration will fix it.
        import subprocess as _sp
        import urllib.error as _ue
        import urllib.request as _u
        for _label, _url in (("protected", api_url.rstrip("/") + "/protected/"),
                             ("licence", api_url.rstrip("/") + "/account/license/?version=" + lic)):
            _req = _u.Request(_url, headers={"Authorization": "Bearer " + tok})
            try:
                with _u.urlopen(_req, timeout=15) as _r:
                    print("  raw %-9s: HTTP %s %s" % (_label, _r.status, _r.read()[:110]))
            except _ue.HTTPError as _e:
                print("  raw %-9s: HTTP %s %s" % (_label, _e.code, _e.read()[:160]))
            except Exception as _e:
                print("  raw %-9s: %s %s" % (_label, type(_e).__name__, _e))
        try:
            _ip = _sp.run(["curl", "-s", "--max-time", "10", "https://api.ipify.org"],
                          capture_output=True, text=True).stdout.strip()
            print("  egress IP    :", _ip or "(unknown)")
        except Exception:
            pass

        # One run should diagnose AND, if a proxy is the cause, confirm the cure.
        if v is not True or acc is not True:
            for k in [k for k in os.environ if "proxy" in k.lower()]:
                os.environ.pop(k, None)
            os.environ["NO_PROXY"] = "*"
            os.environ["no_proxy"] = "*"
            print("  --- retry with all *_proxy vars unset, NO_PROXY=* ---")
            print("  verify_token :", verify_token(tok, api_url))
            print("  accepted?    :", check_license_accepted(tok, api_url, lic))
            print("  -> if these flip to True, a PROXY was mangling the request and")
            print("     unsetting the proxy vars is the fix.")
except Exception as e:
    print("  auth introspection failed:", type(e).__name__, e)

import numpy as np
from tabpfn import TabPFNClassifier
rng = np.random.default_rng(0)
X = rng.random((24, 4))
y = (X[:, 0] > 0.5).astype(int)
TabPFNClassifier(n_estimators=1, device="cpu", random_state=0).fit(X, y)
print("  TABPFN_AUTH_OK - weights downloaded and a fit completed")
'
PREFLIGHT_RC=$?
if [ "$PREFLIGHT_RC" -ne 0 ]; then
    echo "########## PREFLIGHT FAILED (rc=$PREFLIGHT_RC) ##########" >&2
    echo "FATAL: the token/licence cannot download weights; refusing to run arms" >&2
    echo "       that would fail identically. Accept the licence at" >&2
    echo "       https://ux.priorlabs.ai (Licenses tab), then re-run." >&2
    exit 3
fi
echo "########## PREFLIGHT OK ##########"

# ---- 4. Run each arm in its own process ----
for arm in ${ARMS//,/ }; do
    echo
    echo "########## ARM $arm ##########"
    python3 scripts/run_pilot.py --arms "$arm"
    rc=$?
    if [ "$rc" -ne 0 ]; then
        # 137 => 128+9 SIGKILL, i.e. the OOM killer. Reported, not fatal.
        echo "########## ARM $arm EXITED rc=$rc (137 = OOM SIGKILL) ##########"
    fi
done

# ---- 5. Aggregate ----
echo
echo "########## AGGREGATE ##########"
python3 scripts/run_pilot.py --aggregate

echo
echo "########## ARTIFACTS ##########"
ls -lR outputs/finetune/pilot 2>/dev/null | head -40

# ---- 6. Emit results through the LOG STREAM ----
# This is the only return channel that always works:
#   * `vastai execute` is NOT a shell -- it runs only ls/rm/du, so it can neither
#     run a script nor read a file (a 400 "Invalid command given" otherwise).
#   * SSH needs a registered key, and a TEAM-context account refuses to create one.
#   * `vastai copy` wants --identity, i.e. a key again.
# So the container log is it. Keep the payload to the small essentials (metrics
# plus each run's meta.json) -- tens of KB, not the full 252 KB output tree.
cd outputs/finetune/pilot 2>/dev/null || { echo "__ARTIFACTS_B64_BEGIN__"; echo "__ARTIFACTS_B64_END__"; exit 0; }
PAYLOAD="pilot_metrics.parquet"
for f in */meta.json; do [ -f "$f" ] && PAYLOAD="$PAYLOAD $f"; done
# Predictions are useful but sizeable; include only if modest.
if [ -f pilot_predictions.parquet ] && [ "$(wc -c < pilot_predictions.parquet)" -lt 300000 ]; then
    PAYLOAD="$PAYLOAD pilot_predictions.parquet"
fi
# NOTE: the log caps each LINE at 500 characters (measured: our payload line came
# back exactly 500 chars, and the next-longest line in the whole log was 363). A
# single base64 line therefore truncates silently -- the payload decoded to a
# 375-byte gzip that tar rejected as "truncated gzip input", while every log
# message said the transfer had happened. So the payload is folded into lines well
# under the cap, each tagged, and reassembled on the client.
echo
echo "__ARTIFACTS_BEGIN__"
tar czf - $PAYLOAD 2>/dev/null | base64 -w0 2>/dev/null | fold -w 440 | sed 's/^/__ART__/'
echo "__ARTIFACTS_END__"
finish
