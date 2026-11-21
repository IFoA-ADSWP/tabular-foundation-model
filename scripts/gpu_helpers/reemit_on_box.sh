#!/usr/bin/env bash
# Re-emit an already-sealed launch from INSIDE the box (#568).
#
# Called by `bootstrap_pilot.sh` on every primary-mode boot. Exit 0 means "everything this launch
# had is now on the wire"; the caller then reports completion without fitting. Exit 1 means the box
# is not fully sealed, so the normal path runs.
#
# WHY THIS IS A SEPARATE FILE. The bootstrap travels inside the onstart field, gzipped+base64, and
# that field is capped at 16,384 bytes by the API. The launcher refuses a payload over 16,000. A
# real launch already came within a few hundred bytes of that ceiling, so the recovery path -- which
# an old box also has to be able to run -- lives in the clone the box checks out, not in the
# payload. Do not move this logic back into bootstrap_pilot.sh.
#
# It does not fit, touch the data, or rewrite a capture. It only sends what is already sealed.
set -u

EXPECTED=0
for _expected_target in ${TFM_FAIRTEST_TARGETS:-frequency_french frequency_spanish severity_french severity_spanish}; do
    EXPECTED=$(( EXPECTED + 1 ))
done

SEALED=0
for _cap in results/*/capture.json; do
    [ -f "$_cap" ] || continue
    SEALED=$(( SEALED + 1 ))
done

if [ "$SEALED" -lt "$EXPECTED" ]; then
    if [ "$SEALED" -gt 0 ]; then
        echo
        echo "########## PARTIAL: $SEALED of $EXPECTED capture(s) sealed; this boot fits ##########"
    fi
    exit 1
fi

echo
echo "########## REEMIT: $SEALED sealed capture(s) already on the box -- no fit ##########"
for _cap in results/*/capture.json; do
    [ -f "$_cap" ] || continue
    _dir="$(dirname "$_cap")"
    _id="$(basename "$_dir")"
    echo "########## EMIT $_id ($_id) ##########"
    # The same transport and the same chunk knobs as the normal per-target emit: the launcher's
    # collector merges by payload id and sequence number, and a re-emit must be indistinguishable
    # from the first emission to it.
    PAYLOAD_ID="$_id" TFM_CHUNK_LINES="${TFM_CHUNK_LINES:-1500}" \
        TFM_CHUNK_PAUSE="${TFM_CHUNK_PAUSE:-20}" \
        TFM_CHUNK_REPEAT="${TFM_CHUNK_REPEAT:-2}" TFM_CHUNK_PASSES="${TFM_CHUNK_PASSES:-2}" \
        bash scripts/gpu_helpers/emit_artifacts.sh "$_dir"
done
exit 0
