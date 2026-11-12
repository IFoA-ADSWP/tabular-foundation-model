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
#   __ARTIFACTS_INFO__ bytes=<n> sha256=<hex> lines=<n> files=<n> [payload=<id> chunks=<n> lines_per_chunk=<k>]
#   __ARTIFACTS_BEGIN__
#   [__ART_CHUNK__ seq=<i>/<n> lines=<k>]
#   __ART__<440-char base64 chunk>
#   ...
#   [__ART_CHUNK_END__]
#   __ARTIFACTS_END__
#
# The self-declared size is the point: the receiver REFUSES a short read instead of
# reporting a cryptic unpack failure, so a mis-sized --tail window fails loudly.
#
# CHUNKED MODE (#564). At ~120 MB a fair-test capture is far larger than the ~6.6 MB
# window (`--tail 20000` x 440 chars) that a single poll can read, and the log is the
# only transport this account has: `--transport ssh` needs a key the team context
# refuses. So a fair-test payload is emitted in sequence-numbered chunks with a pause
# between them, slower than the window scrolls, and `collect_chunks.py` merges the
# polls by `seq`. Set CHUNK_LINES (0 disables -- the pilot path's single block) and
# CHUNK_PAUSE (seconds between chunks, default 45) plus PAYLOAD_ID so two payloads in
# one log cannot mix.
#
# Usage: [PAYLOAD_ID=<run id> TFM_CHUNK_LINES=4500 TFM_CHUNK_PAUSE=45] emit_artifacts.sh [output_dir]
#
# The chunk knobs are TFM_-prefixed because the launcher forwards them by that name; one name,
# one default (0 = a single block, today's behaviour for a direct caller).
set -u

OUTDIR="${1:-outputs/finetune/pilot}"
LINE_WIDTH=440
CHUNK_LINES="${TFM_CHUNK_LINES:-0}"
CHUNK_PAUSE="${TFM_CHUNK_PAUSE:-45}"
PAYLOAD_ID="${PAYLOAD_ID:-}"

# The launcher reads `--tail 20000`, so a chunk at that size would leave no room for the
# lines that arrive while a poll is in flight, and the next poll could read past a chunk's
# start while still seeing its end. Refuse rather than emit a transfer that cannot seal.
if [ "$CHUNK_LINES" -gt 18000 ]; then
    echo "REFUSING: CHUNK_LINES=$CHUNK_LINES leaves no slack under the launcher's 20000-line" >&2
    echo "          window; a chunk would scroll out before its end marker was read." >&2
    exit 2
fi

emit_empty() {
    local extra=""
    [ -n "$PAYLOAD_ID" ] && extra=" payload=$PAYLOAD_ID chunks=0"
    echo "__ARTIFACTS_INFO__ bytes=0 sha256=- lines=0 files=0$extra"
    echo "__ARTIFACTS_BEGIN__"
    echo "__ARTIFACTS_END__"
}

cd "$OUTDIR" 2>/dev/null || { emit_empty; exit 0; }

FILE_LIST="$(mktemp)"
TARBALL="$(mktemp)"
B64FILE="$(mktemp)"
FOLDED="$(mktemp)"
trap 'rm -f "$FILE_LIST" "$TARBALL" "$B64FILE" "$FOLDED"' EXIT

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
# recompute the metrics. Includes the seed/fold-nested layout. The v3/v4 arrays are
# listed too (#564): a fair-test capture is nothing but these files plus its manifest,
# and shipping only predictions/truth would hand back a capture whose quantiles and
# severity weights the manifest hashes but the transfer never carried.
find . \( -name predictions.npy -o -name ground_truth.npy -o -name test_index.npy \
    -o -name quantiles.npy -o -name exposure.npy -o -name weights.npy \
    -o -name cluster_id.npy \) 2>/dev/null \
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
# Count the lines the emitter ACTUALLY produces, from the file it will send. Two earlier
# versions of this line were wrong in opposite directions, each in its own environment:
# dividing the base64 BYTE count by the width declared one line too many whenever the
# payload length was an exact multiple of it (base64's trailing newline pushed the ceiling
# over the boundary), and `fold | wc -l` declares one too FEW when the final base64 line has
# no trailing newline -- `wc -l` counts newlines, not lines. A short or over-long count is a
# refusal from the receiver, so both shapes threw away a good, paid-for batch. Materialising
# the folded file and counting its records removes the disagreement: the same bytes are
# counted and sent.
fold -w "$LINE_WIDTH" "$B64FILE" > "$FOLDED"
ART_LINES="$(awk 'END { print NR }' "$FOLDED")"

SPLIT_DIR="$(mktemp -d)"
NCHUNKS=1
CHUNKED=0
if [ "$CHUNK_LINES" -gt 0 ] && [ "$ART_LINES" -gt "$CHUNK_LINES" ]; then
    NCHUNKS=$(( (ART_LINES + CHUNK_LINES - 1) / CHUNK_LINES ))
    CHUNKED=1
fi

INFO="__ARTIFACTS_INFO__ bytes=$ART_BYTES sha256=$ART_SHA lines=$ART_LINES files=$FILE_COUNT"
[ -n "$PAYLOAD_ID" ] && INFO="$INFO payload=$PAYLOAD_ID"
if [ "$CHUNKED" -eq 1 ]; then
    INFO="$INFO chunks=$NCHUNKS lines_per_chunk=$CHUNK_LINES"
fi
echo "$INFO"
echo "__ARTIFACTS_BEGIN__"
if [ "$CHUNKED" -eq 0 ]; then
    # One block: the pilot and benchmark paths, unchanged. The window can carry it.
    sed 's/^/__ART__/' "$FOLDED"
    echo "__ARTIFACTS_END__"
    rm -rf "$SPLIT_DIR"
    exit 0
fi
# Chunked: each block is self-identifying, so a poll that lands mid-chunk leaves it
# unsealed rather than half-assembled, and a repeated poll cannot duplicate it.
split -l "$CHUNK_LINES" "$FOLDED" "$SPLIT_DIR/part-"
chunk_no=0
for part in "$SPLIT_DIR"/part-*; do
    chunk_no=$((chunk_no + 1))
    marker="__ART_CHUNK__ seq=$chunk_no/$NCHUNKS"
    [ -n "$PAYLOAD_ID" ] && marker="$marker payload=$PAYLOAD_ID"
    echo "$marker lines=$(awk 'END { print NR }' "$part")"
    sed 's/^/__ART__/' "$part"
    echo "__ART_CHUNK_END__"
    # Paced so the chunk outlives several polls: a window of 20,000 lines holds about
    # four of these, and the launcher reads one window every 20 seconds.
    if [ "$chunk_no" -lt "$NCHUNKS" ]; then sleep "$CHUNK_PAUSE"; fi
done
echo "__ARTIFACTS_END__"
rm -rf "$SPLIT_DIR"

