#!/bin/bash
# Does a batch fit inside the launcher's poll window? Shared arithmetic, owned once.
#
# WHY THIS FILE EXISTS (#430). `vast_run.sh` refuses a batch whose estimated runtime exceeds
# its poll window (#414), because past that window the trap destroys the instance and the
# artifacts are never shipped -- the compute is discarded, not late. The multi-batch harness
# has to apply the SAME guard before it rents anything, and a second copy of the sum drifts:
# the harness would size batches by arithmetic the launcher does not agree with, which is the
# class of failure the guard exists to prevent.
#
# Sourced, not executed. The numbers are inputs, never policy: `vast_run.sh` defaults are
# EST_SEC_PER_SEED=170 and BOOT_EST_SECONDS=900 (rule 1 of the runbook); `batch_run.sh`
# mirrors those defaults and passes both to every launch, so the guard it applied and the
# guard the launcher applies are the same sum with the same operands.

batch_est_seconds() {  # SEED_COUNT EST_SEC_PER_SEED BOOT_SECONDS
    echo $(( $1 * $2 + $3 ))
}

batch_poll_seconds() {  # POLL_MINUTES
    echo $(( $1 * 60 ))
}

batch_capacity() {  # EST_SEC_PER_SEED BOOT_SECONDS POLL_MINUTES -> most seeds that still fit
    local window room
    window="$(batch_poll_seconds "$3")"
    room=$(( window - $2 ))
    # A poll window shorter than the startup allowance admits nothing; saying 0 rather than
    # a negative capacity keeps the caller's comparison honest.
    if [ "$room" -le 0 ]; then
        echo 0
    else
        echo $(( room / $1 ))
    fi
}

batch_fits() {  # SEED_COUNT EST_SEC_PER_SEED BOOT_SECONDS POLL_MINUTES -> 0 when it fits
    local est window
    est="$(batch_est_seconds "$1" "$2" "$3")"
    window="$(batch_poll_seconds "$4")"
    [ "$est" -le "$window" ]
}

batch_refuse() {  # SEED_COUNT EST_SEC_PER_SEED BOOT_SECONDS POLL_MINUTES -> the refusal text
    local est window
    est="$(batch_est_seconds "$1" "$2" "$3")"
    window="$(batch_poll_seconds "$4")"
    echo "REFUSING: this batch cannot finish inside the poll window." >&2
    echo "  ${1} seed(s) x ${2}s + ${3}s boot = ${est}s" >&2
    echo "  poll window is ${4} min = ${window}s" >&2
    echo "  Past that window the launcher destroys the instance and the artifacts are lost," >&2
    echo "  because the box ships its payload only on completion." >&2
    echo "  Fix one of: fewer seeds, --poll-minutes N, --estimate-sec-per-seed N." >&2
}
