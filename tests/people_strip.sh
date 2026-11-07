#!/usr/bin/env bash
# PNG strip of mask over frame: one row per mask in DIR (all.gray = everyone the text prompt finds,
# then person-N.gray = the person chosen by face), five frames across the clip each.
# usage: people_strip.sh SOURCE DIR WIDTH HEIGHT FRAMES OUT.png
set -euo pipefail
src=$1 dir=$2 w=$3 h=$4 frames=$5 out=$6
pick=""
for f in 0 1 2 3 4; do pick+="eq(n\,$(( (frames - 1) * f / 4 )))+"; done
pick=${pick%+}
rows=()
for g in "$dir"/all.gray $(ls "$dir"/person-*.gray 2>/dev/null | sort -V); do
  row="$dir/row-$(basename "$g" .gray).png"
  ffmpeg -nostdin -v error -y -i "$src" -f rawvideo -pixel_format gray -video_size "${w}x${h}" -framerate 24 -i "$g" \
    -filter_complex "[0:v]fps=24,scale=${w}:${h},format=gbrp,split[a][b];color=c=red:s=${w}x${h}:r=24:d=6,format=gbrp[r];[1:v]format=gray[m];[a][r][m]maskedmerge[red];[b][red]blend=all_mode=average,select='${pick}',scale=320:-1,tile=5x1" \
    -t 6 -frames:v 1 "$row"
  rows+=("$row")
done
inputs=(); for r in "${rows[@]}"; do inputs+=(-i "$r"); done
ffmpeg -nostdin -v error -y "${inputs[@]}" -filter_complex "vstack=inputs=${#rows[@]}" "$out"
rm -f "${rows[@]}"
