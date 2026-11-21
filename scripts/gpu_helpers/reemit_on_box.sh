#!/usr/bin/env bash
# Re-emit an already-sealed launch from INSIDE the box (#568).
#
# Called by `bootstrap_pilot.sh` on every primary-mode boot. Exit 0 means "this launch's captures
# are now on the wire"; the caller then reports completion without fitting. Exit 1 means the launch
# is not fully sealed, so the normal path runs (which fits). Exit 2 means the emission itself
# failed -- the caller must NOT treat that as "not sealed", because a re-fit would be paid for
# something the box already has.
#
# "This launch" is load-bearing. `results/` in a fresh clone carries the repository's own committed
# captures (37 at #568), so counting `results/*/capture.json` would find a full set on a box that
# has fitted nothing and skip the launch entirely. The ids come from the launch's stamp, exactly
# as the target loop names them.
#
# WHY THIS IS A SEPARATE FILE. The bootstrap travels inside the onstart field, gzipped+base64, and
# that field is capped at 16,384 bytes by the API; the launcher refuses a payload over 16,000 and a
# real launch already runs at 15.7 KB. This file is in the clone the box checks out, so it costs
# the payload nothing. Do not move it back into bootstrap_pilot.sh.
#
# It does not fit, touch the data, or rewrite a capture. It only sends what is already sealed.
set -u

stamp="${TFM_RUN_STAMP:-}"
targets="${TFM_FAIRTEST_TARGETS:-}"

# A direct run on a box has neither: there is no launch identity, so there is nothing to re-emit.
if [ -z "$stamp" ] || [ -z "$targets" ]; then
    exit 1
fi

# A boot marker carrying this boot's clock. The container log ACCUMULATES across restarts, so a
# `PARTIAL` or dependency-install line from an earlier boot can still be in a tail and would stop a
# recovery that is going fine. The driver acts only on text after the newest marker whose timestamp
# is later than the one it read before rebooting, which is monotonic within the box's own clock.
echo "########## REEMIT CHECK $(date -u +%s) $stamp ##########"

count=0
for _target in $targets; do count=$(( count + 1 )); done

run_ids="$(python3 scripts/gpu_helpers/fairtest_run_ids.py --stamp "$stamp" --count "$count")" || {
    echo "FATAL: cannot derive this launch's run ids from $stamp" >&2
    exit 2
}
# An empty list would make "every id is sealed" vacuously true, and the caller would skip the fit.
if [ -z "$run_ids" ]; then
    echo "FATAL: the launch's run ids came back empty for $stamp ($count targets)" >&2
    exit 2
fi

missing=""
sealed=0
for _id in $run_ids; do
    if [ -f "results/$_id/capture.json" ]; then
        sealed=$(( sealed + 1 ))
    else
        missing="$missing $_id"
    fi
done

if [ -n "$missing" ]; then
    # Silent on a first boot (nothing sealed is the normal state); loud when a RESTART finds a
    # partial launch, because that boot will pay to fit everything again.
    if [ "$sealed" -gt 0 ]; then
        echo
        echo "########## PARTIAL: $sealed of $count capture(s) sealed for this launch ##########"
        echo "##########          missing:$missing ##########"
    fi
    exit 1
fi

echo
echo "########## REEMIT: $sealed sealed capture(s) for launch $stamp -- no fit ##########"
failed=0
for _id in $run_ids; do
    echo "########## EMIT $_id ($_id) ##########"
    # The same transport and the same chunk knobs as the normal per-target emit: the launcher's
    # collector merges by payload id and sequence number, and a re-emit must be indistinguishable
    # from the first emission to it.
    if ! PAYLOAD_ID="$_id" TFM_CHUNK_LINES="${TFM_CHUNK_LINES:-1500}" \
            TFM_CHUNK_PAUSE="${TFM_CHUNK_PAUSE:-20}" \
            TFM_CHUNK_REPEAT="${TFM_CHUNK_REPEAT:-2}" TFM_CHUNK_PASSES="${TFM_CHUNK_PASSES:-2}" \
            bash scripts/gpu_helpers/emit_artifacts.sh "results/$_id"; then
        echo "########## EMIT FAILED for $_id ##########" >&2
        failed=$(( failed + 1 ))
    fi
done

if [ "$failed" -gt 0 ]; then
    # Distinct from "not sealed": the caller must not respond by fitting.
    echo "########## REEMIT INCOMPLETE: $failed of $count emit(s) failed ##########" >&2
    exit 2
fi
exit 0
