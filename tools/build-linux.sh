#!/usr/bin/env bash
# Build MM-Air on Linux with airproj (Windows: tools/build-windows-app.cmd).
#   tools/build-linux.sh            every declared program, release mode, into build/release/bin
# AIR is found at $AIR_ROOT or ../AIR; its built tools at $AIR_TOOLCHAIN or $AIR_ROOT/build-release.
# Building is heavy (the app alone is minutes of compiler time): run one build at a time.
set -euo pipefail
app=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
air=$(cd -- "${AIR_ROOT:-$app/../AIR}" && pwd)
tools=${AIR_TOOLCHAIN:-$air/build-release}
[[ -x $tools/bin/airproj ]] || { echo "no airproj in $tools/bin (set AIR_TOOLCHAIN)" >&2; exit 2; }

"$tools/bin/airproj" --project "$app" --toolchain "$tools" build --mode release

# The app reads its screens from <bin>/share/mm-air. Links, so an edited desktop.ui or
# desktop.css shows on the next start without a rebuild.
bin=$app/build/release/bin
share=$bin/share/mm-air
mkdir -p "$share"
ln -sfn "$app/desktop.ui" "$share/desktop.ui"
ln -sfn "$app/desktop.css" "$share/desktop.css"
ln -sfn "$app/presets/swap-masks.json" "$share/swap-masks.json"

# The window host (air-ui) is AIR's GTK adapter, built once by AIR:
#   AIR_BUILD_DIR=DIR $AIR_ROOT/toolkits/desktop/build.sh   ->  DIR/bin/air-ui
if [[ ! -x $bin/air-ui ]]; then
  for candidate in "$tools/bin/air-ui" "$air/build-dev/bin/air-ui"; do
    if [[ -x $candidate ]]; then cp "$candidate" "$bin/air-ui"; break; fi
  done
fi
[[ -x $bin/air-ui ]] || echo "note: $bin/air-ui is missing; build it with AIR's toolkits/desktop/build.sh and copy it there" >&2
echo "built $bin/mm-air"
