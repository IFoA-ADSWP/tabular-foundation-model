#!/usr/bin/env bash
# Emit the artifact payload through the log stream. (PR-2)
#
# WHY A SEPARATE SCRIPT
# The transfer channel is the container log, and getting it wrong has already cost
# real money twice: a single-line payload was silently truncated to the log's 500-char
# line cap (decoding to a partial gzip that tar rejected, while every message said
# success), and a zero-byte read looked identical to "not finished". Keeping the
# emitter beside its verifier (verify_artifacts.py) means the whole transport can be
# exercised locally, at zero spend, instead of only on a paid instance.
#
# WHAT IT EMITS
#   __ARTIFACTS_INFO__ bytes=<n> sha256=<hex> lines=<n> files=<n>
#   __ARTIFACTS_BEGIN__
#   __ART__<440-char base64 chunk>
#   ...
#   __ARTIFACTS_END__
#
# The self-declared size is the point: the receiver REFUSES a short read instead of
# reporting a cryptic unpack failure, so a mis-sized --tail window fails loudly.
#
# Usage: emit_artifacts.sh [output_dir]     (default: outputs/finetune/pilot)
set -u

OUTDIR="${1:-outputs/finetune/pilot}"
LINE_WIDTH=440

emit_empty() {
    echo "__ARTIFACTS_INFO__ bytes=0 sha256=- lines=0 files=0"
    echo "__ARTIFACTS_BEGIN__"
    echo "__ARTIFACTS_END__"
}

cd "$OUTDIR" 2>/dev/null || { emit_empty; exit 0; }

FILE_LIST="$(mktemp)"
TARBALL="$(mktemp)"
B64FILE="$(mktemp)"
trap 'rm -f "$FILE_LIST" "$TARBALL" "$B64FILE"' EXIT

# Small essentials: metrics, per-run metadata, optional combined predictions.
[ -f pilot_metrics.parquet ] && echo pilot_metrics.parquet >> "$FILE_LIST"
# Per-run metadata. NOTE: this was `for f in */meta.json`, which matches NOTHING --
# the runner writes <dataset>/<arm>/meta.json, one level deeper, plus
# <dataset>/<arm>/seed*/fold*/meta.json under multi-seed runs. So meta.json was never
# actually returned from the box, and the per-run config/provenance never came back.
# A `find` covers every layout instead of guessing the depth.
find . -name meta.json 2>/dev/null | sed 's|^\./||' >> "$FILE_LIST"
# Top-level run-level records, in particular manifest_<run_id>.json -- the audit
# record the whole PR-1 prerequisite exists to produce. Omitting it meant the manifest
# was written on the box and never returned, which a mock run caught.
find . -maxdepth 1 -name "*.json" 2>/dev/null | sed 's|^\./||' >> "$FILE_LIST"
if [ -f pilot_predictions.parquet ] && [ "$(wc -c < pilot_predictions.parquet)" -lt 300000 ]; then
    echo pilot_predictions.parquet >> "$FILE_LIST"
fi
# Per-arm predictions and ground truth -- the evidence a third party needs to
# recompute the metrics. Includes the seed/fold-nested layout.
find . -name predictions.npy -o -name ground_truth.npy 2>/dev/null \
    | sed 's|^\./||' >> "$FILE_LIST"

FILE_COUNT="$(awk 'NF' "$FILE_LIST" 2>/dev/null | wc -l | tr -d ' ')"
case "$FILE_COUNT" in ''|*[!0-9]*) FILE_COUNT=0 ;; esac
if [ "$FILE_COUNT" -eq 0 ]; then
    # Nothing to send. Declare it explicitly rather than shipping an empty archive:
    # the receiver must be able to tell "the box produced no outputs" from "the
    # transfer was truncated".
    emit_empty
    exit 0
fi
tar czf "$TARBALL" -T "$FILE_LIST" 2>/dev/null
if [ ! -s "$TARBALL" ]; then
    emit_empty
    exit 0
fi

base64 -w0 < "$TARBALL" > "$B64FILE" 2>/dev/null \
    || base64 < "$TARBALL" | tr -d '\n' > "$B64FILE"

ART_BYTES="$(wc -c < "$TARBALL" | tr -d ' ')"
# Portable checksum: sha256sum is GNU (the box), shasum -a 256 is macOS/BSD. If
# neither exists we emit "-" and the receiver skips the integrity check rather than
# failing -- but a checksum-less transfer is a weaker guarantee, so say so.
ART_SHA="$(sha256sum "$TARBALL" 2>/dev/null | cut -d' ' -f1)"
if [ -z "$ART_SHA" ]; then
    ART_SHA="$(shasum -a 256 "$TARBALL" 2>/dev/null | cut -d' ' -f1)"
fi
[ -n "$ART_SHA" ] || ART_SHA="-"
ART_B64="$(wc -c < "$B64FILE" | tr -d ' ')"
ART_LINES=$(( (ART_B64 + LINE_WIDTH - 1) / LINE_WIDTH ))

echo "__ARTIFACTS_INFO__ bytes=$ART_BYTES sha256=$ART_SHA lines=$ART_LINES files=$FILE_COUNT"
echo "__ARTIFACTS_BEGIN__"
fold -w "$LINE_WIDTH" "$B64FILE" | sed 's/^/__ART__/'
echo "__ARTIFACTS_END__"
