#!/usr/bin/env bash
# Build the Movie Maker MCP server and its render worker into build/release/bin (beside mm-air).
#   mcp/build.sh            both programs
#   mcp/build.sh server     only the MCP server (seconds)
#   mcp/build.sh worker     only the render worker (minutes: it links the whole H3 runtime)
# AIR is found at $AIR_ROOT or ../AIR; its compiler at $AIRC. Builds run one at a time under the memory cap.
set -euo pipefail
app=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
air=$(cd -- "${AIR_ROOT:-$app/../AIR}" && pwd)
airc=${AIRC:-$air/build-release/bin/airc}
cap=${AIR_BUILD_CAP:-$HOME/h3-air/bin/capped.sh}
bin=$app/build/release/bin
mkdir -p "$bin"
export AIR_STDLIB=$air/stdlib
export CUDA_HOME=${CUDA_HOME:-$HOME/cuda/13.2}
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib:$HOME/cuda/cudnn-9.27/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
cd "$app"
what=${1:-all}
if [[ $what == all || $what == server ]]; then
  "$cap" 12G -- "$airc" build mcp/movie_server.ai -o "$bin/mm-air-movie-mcp" --mode release
fi
if [[ $what == all || $what == worker ]]; then
  "$cap" 24G -- "$airc" build mcp/movie_render.ai -o "$bin/mm-air-movie-render" --mode release
fi
echo "built in $bin"
