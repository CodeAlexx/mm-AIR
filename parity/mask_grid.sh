#!/usr/bin/env bash
# DEV EVIDENCE ONLY: grid of source | edit mask | mannequin (motion reference,
# scaled to source height) for a few frames of a swap-mask job, plus single
# frames of the check-mask preview. usage: mask_grid.sh JOB_DIR OUT_DIR NAME "F1 F2 F3"
set -euo pipefail
job=$1; out=$2; name=$3; frames=$4
mkdir -p "$out"
h=$(python3 -c "import json;print(json.load(open('$job/manifest.json'))['height'])")
rows=()
for f in $frames; do
  sel="select=eq(n\\,$f)"
  ffmpeg -nostdin -v error -y -i "$job/part.mp4" -i "$job/edit-mask.mp4" -i "$job/mannequin.mp4" \
    -filter_complex "[0:v]$sel,format=rgb24[a];[1:v]$sel,format=rgb24[b];[2:v]$sel,scale=-2:$h:flags=neighbor,format=rgb24[c];[a][b][c]hstack=3" \
    -frames:v 1 "$out/$name-f$f.png"
  ffmpeg -nostdin -v error -y -i "$job/check.mp4" -vf "$sel" -frames:v 1 "$out/$name-check-f$f.png"
  rows+=("$out/$name-f$f.png")
done
args=(); filt=""; i=0
for r in "${rows[@]}"; do args+=(-i "$r"); filt+="[$i:v]"; i=$((i+1)); done
ffmpeg -nostdin -v error -y "${args[@]}" -filter_complex "${filt}vstack=$i" "$out/$name-grid.png"
echo "$out/$name-grid.png"
